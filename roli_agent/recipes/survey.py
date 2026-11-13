"""USDA Survey (FNDDS) records in Roli (Julius, 2026-11-05: "Use survey records"). Two narrow uses, both Python, no model calls.

D25, same-food measure: when a recipe line is a volume ("1 1/2 cups olives") and the matched SR Legacy or Foundation record has no usable measure
for it, a record of the SAME food in any USDA table (12.12.4: SR Legacy's walnut record before "Nuts, NFS") may lend its cup, tablespoon or teaspoon
weight. A class-level record (NFS, a whole category) lends only when no same-food record has the measure, and the line is labelled
`class_level_cup_weight`. The nutrients stay with the matched record; only the gram weight of the measure is borrowed, and the line says so.
12.14.8b: a same-food record may also lend whole-item sizes and slices; a size no record has is never stretched from another size, and a substitute
record's foods keep D21 (its item sizes describe a different food).

Fried-dish record: a menu dish that is fried (fish and chips, calamari, schnitzel) has no complete recipe, because the frying oil is never listed with
a quantity and Roli never invents one. USDA's Survey table describes the finished fried food ("Fish, cod, fried": 65 g raw fish, 25 g batter, 10 g oil
per 100 g) with per-100 g values. Each fried component named by the menu is matched to one such record by a fixed table, given a plate amount from
the existing portion rules (raw-flesh rules converted by USDA's own raw share; a proposed cooked range for chips), and the Phase 2A calculator adds
them up. The result is one more scenario interval beside the recipe-based ones, tier `survey_dish_record`, always treated as assumption-driven, so a
ranking that rests on it is tentative. Every choice (record, query, amount, rule, oil per 100 g) is recorded.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from roli_nutrition import ErrorResult
from roli_nutrition.recipe import RecipeCalculator, RecipeResult
from roli_nutrition.recipe.preparation import is_flesh_food, record_state

from .adapt import WeightsTable, _state_for
from .convert import VOLUME_LABEL_WORDS, _label_tokens, convert_with_portions, is_sized_label
from .equivalence import class_level, same_food
from .inference import is_herb_or_spice
from .models import MatchDecision, MenuItem, ParsedIngredient, ScenarioInterval
from .relevance import MENU_NOTE

SURVEY = "Survey (FNDDS)"
SAME_FOOD_TABLES = ["Foundation", "SR Legacy"]
NUTRIENTS = ("saturated_fat_g", "cholesterol_mg")


# -- D25: a measure from a Survey record of the same food --------------------------------------------------------------------------------


class SurveyMeasurePolicy:
    def __init__(self, service: Any, *, enabled: bool = True) -> None:
        self._service, self.enabled, self.log = service, enabled, []

    def find(self, parsed: ParsedIngredient, match: MatchDecision) -> ParsedIngredient | None:
        counted = parsed.unit_kind == "count"
        if not self.enabled or parsed.grams is not None or parsed.quantity is None or parsed.unit_kind not in ("volume", "count") or (counted and match.match_type == "proxy"):
            return None
        if match.fdc_id is None or not match.description or match.data_type == SURVEY:
            return None
        parts = [p.strip() for p in match.description.split(",")]
        variety = " ".join(parts[:2])
        candidates: dict[int, Any] = {}
        # the variety first ("Cheese parmesan"), in every table; the head alone returns cottage cheese and cheese spreads, so it comes last and only the Survey table has class records
        for query, tables in ((variety, SAME_FOOD_TABLES), (variety, [SURVEY]), (parts[0], [SURVEY])):
            found = self._service.search_foods(query, 10, data_types=tables)
            if isinstance(found, ErrorResult):
                return None
            candidates.update({c.fdc_id: c for c in found.candidates if c.fdc_id != match.fdc_id})
        want = {t for t in re.findall(r"[a-z]+", match.description.lower())}
        same = [c for c in candidates.values() if same_food(c.description, match.description) and not (counted and class_level(c.description))]
        # same-food records before class-level ones, and within each the record sharing most words with the matched record ("Yogurt, Greek" before "Yogurt, liquid" for a Greek-yogurt line)
        same.sort(key=lambda c: (class_level(c.description), -len(want & set(re.findall(r"[a-z]+", c.description.lower())))))
        for cand in same:
            portions = self._service.get_portions(cand.fdc_id)
            if isinstance(portions, ErrorResult):
                continue
            if counted:     # an item the line names ("1 stalk", "1 Roma") or a size of the food; a lone "1 fillet" says nothing about a "saku" of tuna
                said = _label_tokens(f"{parsed.name} {parsed.unit or ''} {' '.join(parsed.preparation_words)}")
                usable = [p for p in portions.portions if (_label_tokens(p.label) - {"1"}) & said or is_sized_label(p.label)]
            else:
                usable = [p for p in portions.portions if _label_tokens(p.label) & VOLUME_LABEL_WORDS]
            if not usable:
                continue
            converted = convert_with_portions(parsed, usable, cand.fdc_id, record=cand.description)
            if converted.grams is None:
                continue
            table = cand.data_type.split(" (")[0]
            wide = class_level(cand.description)
            kind = "a class-level record: no same-food record has this measure; 12.12.4" if wide else "the same food; D25, 12.12.4"
            note = f" (measure lent by USDA {table} record {cand.fdc_id} '{cand.description}', {kind}; nutrients stay from record {match.fdc_id})"
            converted = converted.model_copy(update={"flags": converted.flags + ["survey_measure"] + (["class_level_cup_weight"] if wide else []), "grams_reference": (converted.grams_reference or "") + note})
            self.log.append({"line": parsed.line, "from": match.fdc_id, "measure_from": cand.fdc_id, "description": cand.description, "table": table, "class_level": wide, "grams": str(converted.grams)})
            return converted
        return None


# -- the fried-dish record ---------------------------------------------------------------------------------------------------------------

FRIED_ITEM = re.compile(r"\b(deep[- ]?fr(?:y|ied|ying)|fr(?:y|ied|ying)|fritto|fritti|fritters?|tempura|battered|crumbed|breaded|crispy|crisp|schnitzel|katsu|"
                        r"calamari|frites|fries|chips|shoestring|scampi|goujons?|fish ?cakes?|croquettes?|arancini|crackling|onion rings?|popcorn (?:chicken|shrimp))\b", re.I)
# (component pattern, Survey search query, preferred description, family). `{w}` is the matched species word. Order matters: species before "fish".
COMPONENTS: list[tuple[re.Pattern, str, str, str]] = [
    (re.compile(r"\b(cod|haddock|whiting|catfish|tilapia|flounder|trout|perch|salmon|mackerel|pollock|pompano|bass)\b", re.I), "fish {w} fried", r"^Fish, {w}, fried$", "fish"),
    (re.compile(r"\b(fish|goujons?|fish ?cakes?)\b", re.I), "fish NS as to type fried", r"^Fish, NS as to type, fried$", "fish"),
    (re.compile(r"\b(squid|calamari)\b", re.I), "calamari fried", r"^Calamari, fried$", "shellfish"),
    (re.compile(r"\b(prawns?|shrimps?|scampi)\b", re.I), "shrimp fried", r"^Shrimp, fried$", "shellfish"),
    (re.compile(r"\b(scallops?)\b", re.I), "scallops fried", r"^Scallops, fried$", "shellfish"),
    (re.compile(r"\b(oysters?)\b", re.I), "oysters fried", r"^Oysters, fried$", "shellfish"),
    (re.compile(r"\b(clams?)\b", re.I), "clams fried", r"^Clams, fried$", "shellfish"),
    (re.compile(r"\b(chicken|schnitzel|katsu|poussin|popcorn chicken)\b", re.I), "chicken breast fried coated", r"^Chicken breast, fried, coated, prepared skinless, coating eaten", "poultry"),
    (re.compile(r"\b(chips|fries|frites|shoestring potatoes?|shoestring)\b", re.I), "potato french fries restaurant", r"^Potato, french fries, restaurant$", "potato"),
    (re.compile(r"\bonion rings?\b", re.I), "onion rings fried", r"^Fried onion rings$", "vegetable"),
    (re.compile(r"\b(aubergines?|eggplant)\b", re.I), "fried eggplant", r"^Fried eggplant$", "vegetable"),
    (re.compile(r"\b(zucchini|courgettes?|summer squash)\b", re.I), "fried summer squash", r"^Fried summer squash", "vegetable"),
]
RULE_FOR_FAMILY = {("fish", "fish_main"): "PR02", ("fish", "fish_starter"): "PR11", ("fish", "crudo_starter"): "PR11", ("shellfish", "fish_main"): "PR02", ("shellfish", "fish_starter"): "PR11",
                   ("shellfish", "vegetable_starter"): "PR11", ("shellfish", "crudo_starter"): "PR11", ("poultry", "meat_main"): "PR07", ("poultry", "fish_main"): "PR07", ("potato", "*"): "PR12",
                   ("vegetable", "vegetable_starter"): "PR10", ("fish", "fish_and_chips"): "PR15", ("shellfish", "fish_and_chips"): "PR15"}   # PR15: the 3D fish_and_chips card
CHOICE_INPUT = {"fish": lambda d: bool(FLESH_INPUT.match(d)), "oil": lambda d: bool(OIL_INPUT.search(d))}   # which of a record's inputs a card's choice group replaces; other groups name records
SERVING_LABEL = re.compile(r"\b(fillet|breast|piece|steak|whole|order|serving|quantity not specified|patty|ring)\b", re.I)
SPLIT = re.compile(r"\s*(?:,|;|/|&|\band\b|\bwith\b|\bplus\b)\s*", re.I)
FLESH_INPUT = re.compile(r"^(fish|chicken|turkey|beef|pork|lamb|veal|mollusks|crustaceans|duck)\b", re.I)
OIL_INPUT = re.compile(r"\b(oil|shortening|lard|butter|margarine|fat)\b", re.I)


def is_fried_item(item: MenuItem) -> bool:
    return bool(FRIED_ITEM.search(f"{item.name} {item.description}"))


def fried_record_covers(item: MenuItem) -> bool:
    """12.14.2: a deep-fried dish a USDA fried-food record answers for; its recipes' frying oil stays open, because the record carries USDA's own oil."""
    text = f"{item.name} {item.description}"
    return is_fried_item(item) and any(pat.search(text) for pat, _, _, _ in COMPONENTS)


class SurveyComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str                                   # the menu words this component came from
    family: str
    query: str
    fdc_id: int | None = None
    description: str | None = None
    choice: str = ""                            # how the record was chosen among the search results
    preparation_state: str = "cooked"
    grams_low: Decimal | None = None
    grams_high: Decimal | None = None
    amount_basis: str = ""                      # rule and conversion, in words
    rule_id: str | None = None
    raw_share: Decimal | None = None            # grams of raw flesh per 100 g of the finished food, from USDA's inputs
    oil_g_per_100g: Decimal | None = None       # USDA's own frying fat per 100 g of the finished food
    inputs: list[str] = Field(default_factory=list)
    problem: str | None = None
    rebuilt: dict[str, Any] | None = None       # 3D (12.2.3): the record rebuilt from its inputs with the card's low and high choices swapped in


class SurveyDishEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    applicable: bool
    reason: str = ""
    components: list[SurveyComponent] = Field(default_factory=list)
    additions: list[dict[str, Any]] = Field(default_factory=list)       # description words filled from the weights table (sauce, side), per plate
    uncovered: list[str] = Field(default_factory=list)
    totals: dict[str, dict[str, str | None]] = Field(default_factory=dict)   # nutrient -> {"low": .., "high": ..}
    calculations: dict[str, Any] = Field(default_factory=dict)          # Phase 2A results per bound (provenance)
    limitations: list[str] = Field(default_factory=list)
    served_mass: dict[str, str] = Field(default_factory=dict)           # grams on the plate per bound (components plus additions), for the reference check
    # 3E (12.9.7-8): one fat per plate. Each entry is the plate at both ends with that one fat in every rebuilt component: {label: {nutrient: {"low", "high"}}}
    choice_ranges: dict[str, dict[str, dict[str, str]]] = Field(default_factory=dict)
    fat_note: str = ""                          # what the plate's fat choice could and could not reach

    def interval(self, nutrient: str) -> ScenarioInterval | None:
        t = self.totals.get(nutrient)
        if not self.applicable or t is None or t.get("low") is None or t.get("high") is None:
            return None
        f = lambda d: format(Decimal(d).normalize(), "f")
        drivers = [f"USDA Survey record(s): " + "; ".join(f"{c.description} ({c.fdc_id}) {f(c.grams_low)}-{f(c.grams_high)} g, {c.amount_basis}" for c in self.components if c.fdc_id)]
        drivers += [f"USDA's own frying fat: {f(c.oil_g_per_100g)} g per 100 g of {c.description}" for c in self.components if c.oil_g_per_100g]
        drivers += [f"{c.description}: USDA lists it as a finished fried product, so its frying fat is inside its per-100 g values" for c in self.components if c.oil_g_per_100g == 0 and c.inputs]
        drivers += [f"assumed {a['name']}: {a['grams_low']}-{a['grams_high']} g per plate ({a['row_id']})" for a in self.additions]
        drivers += [f"{c.description} rebuilt from USDA's inputs with the card's choices (moisture change {c.rebuilt['moisture_change_pct']}%)" for c in self.components if c.rebuilt]
        if self.fat_note:
            drivers.append(self.fat_note)
        from .models import SamplingInputs   # local import: survey.py is imported by models' users
        sampling = SamplingInputs(kind="survey", model="P2", per_plate_low=Decimal(t["low"]), per_plate_high=Decimal(t["high"]),
                                  served_mass_low=Decimal(self.served_mass["low"]) if self.served_mass.get("low") else None,
                                  served_mass_high=Decimal(self.served_mass["high"]) if self.served_mass.get("high") else None,
                                  choice_ranges={label: {b: Decimal(v) for b, v in r[nutrient].items()} for label, r in self.choice_ranges.items() if nutrient in r})
        return ScenarioInterval(scenario_id=self.scenario_id, nutrient=nutrient, tier="survey_dish_record", low=Decimal(t["low"]), high=Decimal(t["high"]),
                                portion_model="P2", assumption_driven=True, drivers=drivers[:8],
                                served_mass_low=Decimal(self.served_mass["low"]) if self.served_mass.get("low") else None,
                                served_mass_high=Decimal(self.served_mass["high"]) if self.served_mass.get("high") else None, sampling=sampling)


def _components_of(item: MenuItem) -> list[str]:
    parts = [p.strip() for p in SPLIT.split(item.name) if p.strip()]
    return parts or [item.name.strip()]


def _choose(service: Any, query: str, preferred: str, word: str | None) -> tuple[Any | None, str]:
    found = service.search_foods(query, 10, data_types=[SURVEY])          # 10 is the service's maximum; the queries are written so the wanted record ranks first
    if isinstance(found, ErrorResult):
        return None, f"search failed: {found.error_code}"
    pat = re.compile(preferred.replace("{w}", re.escape(word or "")), re.I)
    for c in found.candidates:
        if pat.search(c.description):
            return c, f"preferred record '{c.description}' for query '{query}'"
    fried = [c for c in found.candidates if re.search(r"\b(fried|fries)\b", c.description, re.I) and "sandwich" not in c.description.lower()]
    if fried:
        return fried[0], f"first fried record '{fried[0].description}' for query '{query}' (preferred description not found)"
    return None, f"no fried Survey record for query '{query}'"


def _amount(comp: SurveyComponent, dish_type: str | None, rules: Any, inputs: list, portions: list, scale: float | None = None) -> None:
    """``scale`` turns USDA's input weights (the recipe before cooking) into grams per 100 g of the finished food (12.10.1)."""
    rule_id = RULE_FOR_FAMILY.get((comp.family, dish_type or "")) or RULE_FOR_FAMILY.get((comp.family, "*"))
    rule = next((r for r in rules.rows if r.id == rule_id), None) if rule_id else None
    if rule is not None and rule.review_status.startswith("unsourced"):
        # 12.16.8: a family whose row has no measured source is not portioned by any route, the USDA serving measures included
        comp.problem = f"no plate amount: rule {rule.id} for family '{comp.family}' with dish type '{dish_type}' has no measured source (unsourced, 12.16.8); the dish is not portioned"
        return
    raw_flesh = [i for i in inputs if FLESH_INPUT.match(i.description) and record_state(i.description) == "raw"]
    if rule is not None and comp.family in ("fish", "shellfish", "poultry") and raw_flesh:
        before = sum((Decimal(str(i.grams_per_100g)) for i in raw_flesh), Decimal(0))
        share = before * Decimal(str(scale)) if scale else before
        comp.raw_share = share.quantize(Decimal("0.01"))
        comp.rule_id, comp.grams_low, comp.grams_high = rule.id, (rule.low * 100 / share).quantize(Decimal("0.1")), (rule.high * 100 / share).quantize(Decimal("0.1"))
        how = f"{before} g in the recipe before cooking, scaled by USDA's moisture change" if scale else f"USDA states no moisture change for this record, so the share is the unscaled {before} g"
        comp.amount_basis = f"rule {rule.id} {rule.low}-{rule.high} {rule.unit} / USDA raw share {comp.raw_share} g per 100 g of the fried food ({how})"
        return
    if rule is not None and comp.family in ("potato", "vegetable"):
        comp.rule_id, comp.grams_low, comp.grams_high = rule.id, rule.low, rule.high
        comp.amount_basis = f"rule {rule.id} {rule.low}-{rule.high} {rule.unit} (cooked weight, direct)"
        return
    serving = [p for p in portions if SERVING_LABEL.search(p.label) and not re.search(r"\b(oz|cubic|slice|cup|tablespoon)\b", p.label, re.I)]
    if serving:
        lo, hi = min(p.gram_weight for p in serving), max(p.gram_weight for p in serving)
        comp.grams_low, comp.grams_high = Decimal(str(lo)), Decimal(str(hi))
        comp.amount_basis = f"USDA's own serving measures of the record: {', '.join(sorted({p.label for p in serving}))} ({lo}-{hi} g); no rule applied"
        return
    comp.problem = f"no plate amount: no rule for family '{comp.family}' with dish type '{dish_type}' and no serving measure on the record"


def resolve_input(service: Any, description: str) -> Any | None:
    """A Survey record's input ("Fish, cod, Pacific, raw (may have been previously frozen)", "Vegetable oil, NFS") resolved to a USDA record by EXACT
    description match in USDA's own search results: the default tables first, then Survey; SR Legacy preferred when two tables carry the same food.
    Deterministic, no model; read live 2026-11-05 for every input of the fried-fish records."""
    want = description.strip().lower()
    for types in (None, [SURVEY]):
        found = service.search_foods(description[:200], 10, data_types=types) if types else service.search_foods(description[:200], 10)
        if isinstance(found, ErrorResult):
            continue
        exact = sorted((c for c in found.candidates if c.description.strip().lower() == want), key=lambda c: 0 if c.data_type == "SR Legacy" else 1)
        if exact:
            return exact[0]
    return None


def _carded_record(choice: Any, service: Any, card: Any, groups: dict) -> tuple[Any | None, str]:
    """The record the card names for a family, when the plate has a fat choice for it to follow."""
    if "oil" not in groups:
        return None, ""
    nut = service.get_nutrition(choice.fdc_id)
    if isinstance(nut, ErrorResult):
        return None, f"card {card.id} names record {choice.fdc_id}, which could not be read ({nut.error_code})"
    return type("Named", (), {"fdc_id": nut.fdc_id, "description": nut.description})(), f"record named by card {card.id}: '{nut.description}', whose inputs include the frying oil"


def plate_choices(card: Any, menu_text: str, service: Any) -> tuple[dict[str, dict[str, Any]], str | None]:
    """The card's choice groups priced once per plate, lowest saturated fat first: 12.9.8 says all fried components take the same choice at each end of the
    range. A choice the menu names is the only option. Returns (groups, problem)."""
    groups: dict[str, dict[str, Any]] = {}
    for name, choices in card.choices.items():
        if name not in CHOICE_INPUT:
            continue
        named = [c for c in choices if c.named_in(menu_text)]
        priced = []
        for c in named or choices:
            nut = service.get_nutrition(c.fdc_id)
            if isinstance(nut, ErrorResult) or nut.saturated_fat_g is None or nut.cholesterol_mg is None:
                return {}, f"choice {c.fdc_id} '{c.description}' does not report both nutrients"
            priced.append((Decimal(str(nut.saturated_fat_g)), c, nut.description))
        priced.sort(key=lambda t: t[0])
        groups[name] = {"options": priced, "named_on_menu": [c.description for c in named]}
    return groups, None


def rebuild_from_inputs(comp: SurveyComponent, inputs_result: Any, groups: dict[str, dict[str, Any]], card: Any, service: Any) -> tuple[dict[str, Any] | None, str | None]:
    """12.2.3: the record's inputs are kept at USDA's own weights, and the inputs of each choice group (the fish mix, the frying oil) are replaced by the plate's
    choice. USDA's input weights are the recipe BEFORE cooking (corrected 2026-11-06), so each is converted to grams in 100 g of the finished food with USDA's own
    moisture change. Returns (the record's plan, None), or (None, the reason), in which case the record's own values stay in use."""
    scale = inputs_result.grams_per_100g_scale
    if scale is None:
        return None, "the record lists no inputs or no moisture change"
    scale = Decimal(str(scale))
    inputs = list(inputs_result.inputs)
    replaced: dict[str, Decimal] = {}
    used: dict[str, list[str]] = {}
    for name in groups:
        matched = [i for i in inputs if CHOICE_INPUT[name](i.description)]
        if matched:
            replaced[name] = sum((Decimal(str(i.grams_per_100g)) for i in matched), Decimal(0)) * scale
            used[name] = [i.description for i in matched]
    if not replaced:
        return None, "none of the card's choice groups matches an input of the record"
    taken = {d for names in used.values() for d in names}
    kept: list[dict[str, Any]] = []
    for i in inputs:
        if i.description in taken:
            continue
        rec = resolve_input(service, i.description)
        if rec is None:
            return None, f"input '{i.description}' could not be resolved to a USDA record by exact description"
        kept.append({"name": i.description[:200], "fdc_id": rec.fdc_id, "grams_per_100g": Decimal(str(i.grams_per_100g)) * scale, "preparation_state": _state_for(rec.description),
                     "assumption": f"USDA input of {comp.description}: {i.grams_per_100g} g before cooking; record {rec.fdc_id} by exact description"})
    return {"kept": kept, "replaced": replaced, "card": card, "scale": scale, "moisture_change_pct": inputs_result.moisture_change_pct, "used": used}, None


def _plan_lines(comp: SurveyComponent, k: int, plan: dict[str, Any], plate: Decimal, picks: dict[str, tuple], bound: str) -> list[dict[str, Any]]:
    """The calculator lines of one rebuilt component on one plate: every line a real USDA record at USDA's own share of the finished food."""
    lines = []
    for j, l in enumerate(plan["kept"], start=1):
        lines.append({"name": l["name"], "fdc_id": l["fdc_id"], "grams": str((l["grams_per_100g"] * plate / 100).quantize(Decimal("0.001"))), "preparation_state": l["preparation_state"],
                      "ingredient_id": f"svy_{k:02d}_k{j:02d}", "assumption": f"{l['assumption']}; plate {plate} g of {comp.description} ({comp.amount_basis})"})
    for name, grams in plan["replaced"].items():
        _, choice, desc = picks[name]
        lines.append({"name": f"{comp.text}: {'frying fat' if name == 'oil' else name}, {desc}"[:200], "fdc_id": choice.fdc_id, "grams": str((grams * plate / 100).quantize(Decimal("0.001"))),
                      "preparation_state": _state_for(desc), "ingredient_id": f"svy_{k:02d}_{name}",
                      "assumption": f"CARD CHOICE ({plan['card'].id}, {bound}): {desc} replaces USDA's {', '.join(plan['used'][name])}; plate {plate} g ({comp.amount_basis})"})
    return lines


def estimate_survey_dish(item: MenuItem, dish_type: str | None, *, service: Any, rules: Any, weights: WeightsTable | None = None, slug: str = "") -> SurveyDishEstimate:
    est = SurveyDishEstimate(scenario_id=f"usda-survey:{slug or re.sub(r'[^a-z0-9]+', '-', item.name.lower()).strip('-')}", applicable=False)
    if not is_fried_item(item):
        est.reason = "the menu does not say the dish is fried"
        return est
    # 1. the components named by the dish name (and any fried component named in the description)
    texts = _components_of(item) + [s.strip() for s in SPLIT.split(item.description) if s.strip() and not MENU_NOTE.search(s)]
    seen: set[str] = set()
    card = rules.plate_card(dish_type) if hasattr(rules, "plate_card") else None
    menu_text = f"{item.name} {item.description}"
    groups, group_problem = plate_choices(card, menu_text, service) if card is not None else ({}, None)
    plans: dict[int, dict[str, Any]] = {}
    for text in texts:
        hit = next(((pat, q, pref, fam) for pat, q, pref, fam in COMPONENTS if pat.search(text)), None)
        if hit is None:
            if text in _components_of(item):
                est.uncovered.append(text)
            continue
        pat, query, preferred, family = hit
        word = pat.search(text).group(1).lower() if pat.search(text) and pat.groups else None
        q = query.replace("{w}", word or "")
        if q in seen:
            continue
        seen.add(q)
        comp = SurveyComponent(text=text, family=family, query=q)
        cand, why = None, ""
        carded = (card.choices.get(family) or [None])[0] if card is not None and family not in CHOICE_INPUT else None   # the card may name a family's record (chips with the oil among its inputs)
        if carded is not None:
            cand, why = _carded_record(carded, service, card, groups)
        if cand is None:
            cand, chosen = _choose(service, q, preferred, word)
            why = (why + "; " if why else "") + chosen
        comp.choice = why
        if cand is None:
            comp.problem = why
            est.components.append(comp)
            continue
        comp.fdc_id, comp.description = cand.fdc_id, cand.description
        inputs_r = service.get_inputs(cand.fdc_id)
        inputs = [] if isinstance(inputs_r, ErrorResult) else list(inputs_r.inputs)
        comp.inputs = [f"{i.description} {i.grams_per_100g} g" for i in inputs]
        oil = sum((Decimal(str(i.grams_per_100g)) for i in inputs if OIL_INPUT.search(i.description)), Decimal(0))
        comp.oil_g_per_100g = oil if inputs else None
        portions_r = service.get_portions(cand.fdc_id)
        portions = [] if isinstance(portions_r, ErrorResult) else list(portions_r.portions)
        state = record_state(cand.description)
        if state == "cooked":
            comp.preparation_state = "cooked"
        elif not is_flesh_food(cand.description):
            comp.preparation_state = "as_used"
        else:
            comp.problem = f"record '{cand.description}' does not state a cooked state and is a flesh food"
        _amount(comp, dish_type, rules, inputs, portions, None if isinstance(inputs_r, ErrorResult) else inputs_r.grams_per_100g_scale)
        if groups and inputs and not isinstance(inputs_r, ErrorResult):
            plan, why = rebuild_from_inputs(comp, inputs_r, groups, card, service)
            if plan is None:
                comp.choice += f"; rebuild from inputs not possible ({why}): the record's own values are used"
            else:
                plans[len(est.components)] = plan
                comp.rebuilt = {"card": card.id, "moisture_change_pct": plan["moisture_change_pct"], "scale": str(plan["scale"].quantize(Decimal("0.0001"))), "inputs_kept": [k["name"] for k in plan["kept"]],
                                "groups": {n: {"replaces": plan["used"][n], "grams_per_100g": str(g.quantize(Decimal("0.01"))), "named_on_menu": groups[n]["named_on_menu"],
                                               "options": [f"{d} ({c.fdc_id}): {sat} g saturated fat per 100 g" for sat, c, d in groups[n]["options"]]} for n, g in plan["replaced"].items()}}
        elif card is not None and group_problem:
            comp.choice += f"; rebuild from inputs not possible ({group_problem}): the record's own values are used"
        elif card is not None and groups:
            comp.choice += "; rebuild from inputs not possible (the record lists no inputs): the record's own values are used"
        est.components.append(comp)
    # 2. description words that are not fried components: a weights row (sauce, side), a herb (left out), or uncovered
    for seg in [s.strip() for s in SPLIT.split(item.description) if s.strip() and not MENU_NOTE.search(s)]:
        if any(c.text == seg for c in est.components) or is_herb_or_spice(seg):
            continue
        if any(pat.search(seg) for pat, _, _, _ in COMPONENTS):
            continue                                        # "Panko Crumbed Chicken" restates the fried component already counted from the dish name
        if card is not None and any(c.named_in(seg) for options in card.choices.values() for c in options):
            continue                                        # "fried in beef dripping" names the card's choice, already used; it is no extra food
        row = weights.find(seg, dish_type) if weights is not None else None
        ok = row.usable("experimental")[0] if row is not None else False
        if row is None or not ok:
            est.uncovered.append(seg)
            continue
        nut = service.get_nutrition(row.fdc_id)
        if isinstance(nut, ErrorResult):
            est.uncovered.append(seg)
            continue
        est.additions.append({"name": seg, "row_id": row.id, "fdc_id": row.fdc_id, "description": nut.description, "grams_low": str(row.low), "grams_high": str(row.high),
                              "preparation_state": _state_for(nut.description), "review_status": row.review_status})
    # two fried components of the same family on one plate ("crispy squid & prawns") share the family's plate rule instead of each taking all of it
    by_rule: dict[str, list[SurveyComponent]] = {}
    for c in est.components:
        if c.rule_id and c.grams_low is not None and c.family in ("fish", "shellfish", "poultry"):
            by_rule.setdefault(c.rule_id, []).append(c)
    for rule_id, group in by_rule.items():
        if len(group) > 1:
            n = Decimal(len(group))
            for c in group:
                c.grams_low, c.grams_high = (c.grams_low / n).quantize(Decimal("0.1")), (c.grams_high / n).quantize(Decimal("0.1"))
                c.amount_basis += f"; rule {rule_id} shared equally by {len(group)} components of the same family on this plate"
    good = [c for c in est.components if c.problem is None and c.fdc_id is not None and c.grams_low is not None]
    if not good or len(good) != len(est.components):
        est.reason = "; ".join(c.problem or "no record" for c in est.components if c.problem) or "no fried component recognised in the dish name"
        return est
    if est.uncovered:
        est.reason = f"the menu names {', '.join(est.uncovered[:4])} and no USDA record or weights row covers it"
        return est
    # 3. the Phase 2A calculator adds the components and the plate additions, per bound, one plate. One fat per plate (12.9.8): `picks` is the same for every component.
    calc = RecipeCalculator(service)
    first = {n: g["options"][0] for n, g in groups.items()}
    last = {n: g["options"][-1] for n, g in groups.items()}

    def plate(bound: str, picks: dict[str, tuple]) -> tuple[Any, Decimal]:
        lines: list[dict[str, Any]] = []
        mass = Decimal(0)
        for k, c in enumerate(est.components, start=1):
            grams = c.grams_low if bound == "low" else c.grams_high
            mass += grams
            if k - 1 in plans:
                lines += _plan_lines(c, k, plans[k - 1], grams, picks, bound)
            else:
                lines.append({"name": c.text[:200], "fdc_id": c.fdc_id, "grams": str(grams), "preparation_state": c.preparation_state,
                              "ingredient_id": f"svy_{k:02d}", "assumption": f"USDA Survey fried-food record; {c.amount_basis}"})
        for k, a in enumerate(est.additions, start=1):
            g = a["grams_low"] if bound == "low" else a["grams_high"]
            mass += Decimal(g)
            lines.append({"name": a["name"][:200], "fdc_id": a["fdc_id"], "grams": g, "preparation_state": a["preparation_state"],
                          "ingredient_id": f"add_{k:02d}", "assumption": f"ASSUMED ({a['row_id']}, {bound}): weights row, per plate"})
        return calc.calculate({"recipe_name": f"{est.scenario_id}::{bound}", "servings": "1", "ingredients": lines}), mass

    for bound, picks in (("low", first), ("high", last)):
        result, mass = plate(bound, picks)
        est.served_mass[bound] = str(mass)
        if not isinstance(result, RecipeResult):
            est.reason = f"calculator refused the {bound} plate: {'; '.join(result.problems)[:200]}"
            return est
        est.calculations[bound] = result.model_dump(mode="json")
        for n in NUTRIENTS:
            tot = result.totals[n]
            est.totals.setdefault(n, {})[bound] = str(tot.total) if tot.complete and tot.total is not None else None
    if any(est.totals[n].get("low") is None or est.totals[n].get("high") is None for n in NUTRIENTS):
        est.reason = "a USDA Survey record used here does not report both nutrients"
        return est
    # the plate at both ends with each fat in turn (12.9.7): a reference figure labelled with a fat is compared with that fat's range only
    if plans and "oil" in groups:
        for sat, choice, _ in groups["oil"]["options"]:
            ends = {}
            for bound, picks in (("low", {**first, "oil": (sat, choice, _)}), ("high", {**last, "oil": (sat, choice, _)})):
                result, _mass = plate(bound, picks)
                if isinstance(result, RecipeResult):
                    ends[bound] = result
            if len(ends) == 2 and all(r.totals[n].complete for r in ends.values() for n in NUTRIENTS):
                est.choice_ranges[choice.label] = {n: {b: str(ends[b].totals[n].total) for b in ("low", "high")} for n in NUTRIENTS}
        apart = [c.text for k, c in enumerate(est.components) if k not in plans]
        est.fat_note = (f"one fat per plate: {', '.join(est.choice_ranges) or 'no complete choice'} in {', '.join(c.text for k, c in enumerate(est.components) if k in plans)}"
                        + (f"; {', '.join(apart)} cannot follow the fat choice: USDA's record has no oil among its inputs" if apart else ""))
    est.applicable = True
    est.limitations = ["USDA Survey (FNDDS) records describe a typical US preparation: generic vegetable oil at USDA's amount, not this kitchen's fat or method"
                       if not any(c.rebuilt for c in est.components) else
                       "the fried-food records were rebuilt from USDA's own inputs with the card's species and frying-fat choices at USDA's amounts, one fat per plate; the kitchen's actual fat is not known",
                       "plate amounts come from unreviewed portion rules (or the record's own serving measures); the restaurant serving is not verified",
                       "an estimate from one USDA dish record, not from this restaurant's recipe; ranked as assumption-driven, so any order resting on it is tentative"]
    return est
