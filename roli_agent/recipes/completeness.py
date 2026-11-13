"""D24 (proposed, Phase 2C.1 requirement B): completeness-aware selection among same-food candidates.

The chosen USDA record sometimes lacks one of the two tracked nutrients (the Foundation "Oil, olive, extra virgin" record has no
cholesterol row). D23 forbids borrowing the missing value from another record. This policy instead asks whether the *selection*
could have picked, from the same USDA candidate list, a record that names the same food in the same state and form and reports
both nutrients, without giving up saturated-fat accuracy. The whole line then uses that one record (same-record provenance kept).

Safeguards, all deterministic:
1. the replacement comes from the same search's candidate list (never from memory);
2. same food: identical first two comma-separated words of the description ("Oil, olive");
3. same preparation state and the same physical-form words (shared with D22);
4. the replacement reports BOTH tracked nutrients;
5. saturated-fat accuracy: when the original reports saturated fat, the replacement's value must be within the tolerance
   (|difference| <= max(0.1 g, `tolerance` x the larger value)); the difference is recorded on the decision either way;
   when the original reports neither nutrient there is nothing to compare and the replacement is accepted on rules 1-4;
6. the replacement must weigh the line: a weight-unit line is fine as is; a household measure must convert on the replacement.

Default `enabled=False, observe=False`: nothing runs and nothing changes until Julius decides the tolerance; `observe=True` evaluates and
logs what the policy would do without applying it. The evaluation reports what each tolerance admits.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from roli_nutrition import ErrorResult, NutritionResult
from roli_nutrition.recipe.preparation import record_state

from .convert import convert_with_portions
from .equivalence import form_words, same_food_head
from .models import MatchDecision, ParsedIngredient

ABS_TOLERANCE_SAT_FAT = Decimal("0.1")
D22_TOLERANCE = Decimal("0.05")


def reports_both(n: NutritionResult) -> bool:
    return n.saturated_fat_g is not None and n.cholesterol_mg is not None


class CompleteRecordPolicy:
    def __init__(self, service: Any, *, enabled: bool = False, observe: bool = False, tolerance: Decimal = D22_TOLERANCE) -> None:
        self._service = service
        self.enabled = enabled
        self.observe = observe or enabled           # observe: evaluate and log without applying (costs one nutrient lookup per matched line)
        self.tolerance = Decimal(str(tolerance))
        self.log: list[dict] = []

    def find(self, parsed: ParsedIngredient, match: MatchDecision, converted: ParsedIngredient | None = None) -> tuple[MatchDecision, ParsedIngredient] | None:
        """(replacement decision, line converted on it) when a same-food candidate reports both nutrients within tolerance; else None.
        `parsed` is the line before any USDA-portion conversion: a household measure is re-weighed on the replacement record, so the
        grams and the nutrients of the line always come from the same record. `converted` is the line as converted on the original
        record; it is kept only when its grams came from the page (a weight unit, an embedded weight) and not from the original record.
        Runs when observing or enabled, so the evaluation can report what the policy *would* do; only an enabled policy's result is applied."""
        if not self.observe or match.fdc_id is None or match.description is None or not match.candidates:
            return None
        original = self._service.get_nutrition(match.fdc_id)
        if isinstance(original, ErrorResult) or reports_both(original):
            return None
        state = record_state(match.description)
        for cand in match.candidates:
            if cand["fdc_id"] == match.fdc_id or not same_food_head(cand["description"], match.description):
                continue
            if record_state(cand["description"]) != state or form_words(cand["description"]) != form_words(match.description):
                self.log.append({"line": parsed.line, "rejected": cand["fdc_id"], "why": "state or physical form differs"})
                continue
            other = self._service.get_nutrition(cand["fdc_id"])
            if isinstance(other, ErrorResult) or not reports_both(other):
                self.log.append({"line": parsed.line, "rejected": cand["fdc_id"], "why": "does not report both nutrients"})
                continue
            delta = None
            if original.saturated_fat_g is not None:
                a, b = Decimal(str(original.saturated_fat_g)), Decimal(str(other.saturated_fat_g))
                delta = b - a
                if abs(delta) > max(ABS_TOLERANCE_SAT_FAT, self.tolerance * max(a, b)):
                    self.log.append({"line": parsed.line, "rejected": cand["fdc_id"], "why": f"saturated fat differs by {delta} g/100 g (tolerance {self.tolerance})",
                                     "delta": str(delta)})
                    continue
            if parsed.grams is not None:
                result_line = converted if converted is not None and "usda_portion" not in converted.flags else parsed
            elif parsed.quantity is not None and parsed.unit_kind in ("volume", "count"):
                portions = self._service.get_portions(cand["fdc_id"])
                if isinstance(portions, ErrorResult):
                    continue
                result_line = convert_with_portions(parsed, portions.portions, cand["fdc_id"], proxy=(match.match_type == "proxy"))
                if result_line.grams is None:
                    self.log.append({"line": parsed.line, "rejected": cand["fdc_id"], "why": "cannot weigh the line's measure"})
                    continue
            else:
                result_line = parsed
            missing = [n for n in ("saturated_fat_g", "cholesterol_mg") if getattr(original, n) is None]
            replacement = match.model_copy(update={
                "fdc_id": cand["fdc_id"], "description": cand["description"], "data_type": cand["data_type"],
                "record_state": record_state(cand["description"]), "substituted_for": match.fdc_id, "source": "d24",
                "saturated_fat_delta_per_100g": delta,
                "reason": f"D24: {match.description} ({match.fdc_id}) reports no {', '.join(missing)}; {cand['description']} ({cand['fdc_id']}) names the same "
                          f"food, state and form and reports both" + (f"; saturated fat {delta:+} g/100 g" if delta is not None else ""),
            })
            result_line = result_line.model_copy(update={"flags": result_line.flags + ["d24_complete_record"]})
            self.log.append({"line": parsed.line, "from": match.fdc_id, "to": cand["fdc_id"], "delta": str(delta) if delta is not None else None,
                             "applied": self.enabled})
            return replacement, result_line
        return None
