"""Phase 2D: the documented-inference layer (Julius, 2026-11-03).

Two kinds of inference, both reported BESIDE the Phase 2A calculation, never inside it:

1. `assumed_size_median` (D20 revised): a bare count weighed at the median of the record's comparable whole-item sizes. The converter
   flags the line; this module only collects it as an inference, so a scenario whose Phase 2A result is "complete" can still be told
   apart from one whose every weight the source stated (`basis: documented_inferences` vs `source_reported`).

2. `inferred_zero_nutrient` and `saturated_fat_ceiling`: a USDA record lacks a tracked nutrient and one of the two facts of 12.14.7 answers for it: a plain plant food has
   no cholesterol, and saturated fat lies between 0 and total fat. The record is not changed, the calculator is not told a value, the Phase 2A exclusion stays in `calculation`;
   this module computes `InferredTotal` = known subtotal + inferred contributions and says whether the nutrient is complete *with* the inference.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

from roli_nutrition.recipe import RecipeResult

from .models import Inference, InferredTotal

NUTRIENTS = ("saturated_fat_g", "cholesterol_mg")
PER_SERVING_PLACES = Decimal("0.000001")

# -- 12.14.7: two facts about a missing nutrient (they replace I01 and I02; D23 stands: a missing value is not zero) ------------------------------------------
# USDA lists a nutrient only when it was measured. Each fact is reported as an inference beside the calculation, which stays as it is.

PLANT_CATEGORIES = {"Vegetables and Vegetable Products", "Fruits and Fruit Juices", "Cereal Grains and Pasta", "Legumes and Legume Products", "Nut and Seed Products", "Spices and Herbs"}
PLANT_OIL = re.compile(r"^Oil, ", re.I)         # USDA's "Fats and Oils" also holds butter, lard, tallow and dressings; its plant oils are named "Oil, ..."
LOW_FAT_G_PER_100G = Decimal(3)                 # EU "low fat": no more than 3 g of fat per 100 g of a solid food (Regulation (EC) 1924/2006, Annex, legislation.gov.uk/eur/2006/1924/annex, read 2026-11-06)
PLANT_CHOLESTEROL_REFERENCE = ("Only animals make cholesterol. Applied to a line tagged plain_food whose USDA record is in a plant category (vegetables, fruits, cereal grains and pasta, legumes, nuts and "
                               "seeds, spices and herbs, plant oils); never to animal fats or prepared products.")
PLANT_CHOLESTEROL_REVIEW = "SPEC_3_mvp.md 12.14.7(a), Julius 2026-11-06: replaces I01 and I02"
FAT_CEILING_REFERENCE = "Saturated fat is part of total fat, so it lies between 0 and the record's total fat. A fatty food stays missing: the fact applies at or under the EU 'low fat' limit of 3 g per 100 g."
FAT_CEILING_REVIEW = "SPEC_3_mvp.md 12.14.7(b), Julius 2026-11-06; the 3 g limit is the build's reading of 'a fatty food stays missing' (12.15)"


def is_plant_record(nut: Any) -> bool:
    category = getattr(nut, "food_category", None) or ""
    return category in PLANT_CATEGORIES or (category == "Fats and Oils" and bool(PLANT_OIL.match(nut.description or "")))


def saturated_fat_ceiling(nut: Any, low_fat: Decimal = LOW_FAT_G_PER_100G) -> Decimal | None:
    """12.14.7(b): the record's total fat, when saturated fat is unreported and the food is not a fatty one (12.16.2: `low_fat` is `MvpConfig.low_fat_g_per_100g`)."""
    fat = getattr(nut, "total_fat_g", None)
    if nut.saturated_fat_g is not None or fat is None or Decimal(str(fat)) > low_fat:
        return None
    return Decimal(str(fat))


def near_zero(nut: Any, threshold: Decimal, low_fat: Decimal = LOW_FAT_G_PER_100G) -> bool:
    """12.14.12: at most `threshold` g saturated fat per 100 g and 0 mg cholesterol, reported or by the two facts."""
    sat = Decimal(str(nut.saturated_fat_g)) if nut.saturated_fat_g is not None else saturated_fat_ceiling(nut, low_fat)
    no_cholesterol = nut.cholesterol_mg == 0 or (nut.cholesterol_mg is None and is_plant_record(nut))
    return sat is not None and sat <= threshold and no_cholesterol


class NutrientFacts:
    """What the two facts need about one recipe's lines: the USDA record of each and which lines are plain foods."""

    def __init__(self, service: Any, plain_ids: set[str], low_fat: Decimal = LOW_FAT_G_PER_100G) -> None:
        self._service, self.plain_ids, self.low_fat = service, plain_ids, low_fat

    def rule(self, ing: Any, nutrient: str, bound: str) -> dict | None:
        nut = self._service.get_nutrition(ing.usda.fdc_id)
        if not hasattr(nut, "food_category"):
            return None
        if nutrient == "cholesterol_mg":
            if ing.ingredient_id in self.plain_ids and is_plant_record(nut):
                return {"id": "F7a", "kind": "inferred_zero_nutrient", "value_per_100g": Decimal(0), "reference": PLANT_CHOLESTEROL_REFERENCE, "review_status": PLANT_CHOLESTEROL_REVIEW}
            return None
        ceiling = saturated_fat_ceiling(nut, self.low_fat)
        if ceiling is None:
            return None
        return {"id": "F7b", "kind": "saturated_fat_ceiling", "value_per_100g": Decimal(0) if bound == "low" else ceiling, "reference": FAT_CEILING_REFERENCE, "review_status": FAT_CEILING_REVIEW}


# -- I03: herbs and spices left out of the calculation (Julius, 2026-11-05) ------------------------------------------------------------------

HERB_SPICE_RULE_ID = "I03"
HERB_SPICE_REASON = "herb_or_spice_negligible"
HERB_SPICE_REVIEW = "decided by Julius 2026-11-05: culinary herbs and spices carry trace saturated fat and no cholesterol at typical amounts"
HERB_RECORD_HEADS = {"basil", "chives", "coriander (cilantro) leaves", "dill weed", "parsley", "peppermint", "rosemary", "spearmint", "thyme"}
# one word of a herb or spice; the WHOLE name must be these plus descriptors, so "mint almond", "bay scallops" and "mustard greens" stay in the calculation
HERB_SPICE_WORDS = {"basil", "thyme", "rosemary", "oregano", "parsley", "cilantro", "coriander", "dill", "mint", "spearmint", "peppermint", "sage", "tarragon", "chive", "chives",
                    "marjoram", "chervil", "bay", "shiso", "perilla", "lovage", "herb", "herbs", "cumin", "paprika", "turmeric", "cinnamon", "nutmeg", "cardamom", "saffron", "allspice",
                    "mace", "cayenne", "sumac", "caraway", "anise", "fenugreek", "juniper", "peppercorn", "peppercorns", "seasoning", "seasonings", "spice", "spices", "masala"}
HERB_SPICE_PHRASES = re.compile(r"\b(black pepper|white pepper|pink pepper|pepper flakes|chil[ie] flakes|chilli flakes|chil[ie] powder|chilli powder|curry powder|curry leaves|garlic powder|onion powder|"
                                r"fennel seeds?|fennel pollen|aleppo pepper|mustard seeds?|celery seeds?|coriander seeds?|cumin seeds?|herbes de provence|five spice|ras el hanout|dry rub|spice rub|za'?atar)\b", re.I)
SALT_AND_PEPPER = re.compile(r"\bsalt\b.*\bpepper\b|\bpepper\b.*\bsalt\b", re.I)
DESCRIPTOR_WORDS = {"fresh", "freshly", "dried", "dry", "ground", "whole", "chopped", "minced", "crushed", "cracked", "toasted", "smoked", "sweet", "hot", "flat", "leaf", "leaves", "italian",
                    "curly", "thai", "genovese", "micro", "baby", "organic", "sprig", "sprigs", "stem", "stems", "bunch", "handful", "pinch", "of", "and", "or", "the", "a", "to", "taste", "for",
                    "garnish", "finely", "coarsely", "roughly", "torn", "picked", "mixed", "soft", "tender", "extra", "fine", "seed", "seeds", "powder", "flakes", "optional", "ea", "each",
                    "from", "mill", "salt", "kosher", "sea", "flaky", "pepper", "black", "white", "red", "pink", "yellow", "star", "lemon", "garam", "spanish", "berries", "mesquite",
                    "cajun", "creole", "old", "store", "bought", "homemade", "szechuan", "sichuan", "choice", "spicy"}
MIXTURE_WORDS = re.compile(r"\b(butter|oil|sauce|pesto|paste|cream|mayo|mayonnaise|aioli|salsa|dressing|vinaigrette|marinade|yogh?urt|cheese|bread|crust|crumbs?|sugar|syrup|chimichurri|broth|stock|gravy)\b", re.I)


def is_herb_or_spice(name: str, description: str | None = None, match_type: str | None = None) -> bool:
    """True for a culinary herb or spice used as itself. A directly matched USDA spice or fresh-herb record decides; otherwise the name must consist only of
    herb or spice words and descriptors. A mixture (herb butter, basil pesto, chili oil) is never one, and poppy seeds are not treated as a trace spice."""
    text = (name or "").lower().replace("\u2019", "'")
    if not text.strip() or MIXTURE_WORDS.search(text) or "poppy" in text or "poppy" in (description or "").lower():
        return False
    head = (description or "").split(",", 1)[0].strip().lower()
    if match_type == "direct" and (head == "spices" or head in HERB_RECORD_HEADS):
        return True
    words = re.findall(r"[a-zà-ü']+", text)
    if SALT_AND_PEPPER.search(text):                      # "kosher salt and freshly ground black pepper": salt reports zero, pepper is a spice; "salt and red bell pepper" is not this
        return all(w in DESCRIPTOR_WORDS or w in ("coarse", "plenty", "more", "some") for w in words)
    if not (HERB_SPICE_PHRASES.search(text) or any(w in HERB_SPICE_WORDS for w in words)):
        return False
    phrase_words = {w for m in HERB_SPICE_PHRASES.finditer(text) for w in re.findall(r"[a-zà-ü']+", m.group(0))}
    return all(w in HERB_SPICE_WORDS or w in DESCRIPTOR_WORDS or w in phrase_words for w in words)


# -- 3D (SPEC_3_mvp.md 12.3-12.4): lines that are not eaten, and lines that cannot move the result ---------------------------------------------

REMOVED_REASON = "removed_not_eaten"                     # 12.3.3: lifted out before serving (bay leaf, sprigs, rind, bones)
MEDIUM_NEGLIGIBLE_REASON = "cooking_medium_negligible"   # 12.3.2 with a near-zero record: a brine, water or stock bath; nothing to count
NEGLIGIBLE_COMPOSITION_REASON = "negligible_composition" # 12.4(b): a plain food whose record reports at most the threshold of saturated fat and 0 cholesterol
NEGLIGIBLE_RULE_ID = "I04"
# 3D (12.4.4): a plain food left out of the calculation by the near-zero composition rule still has mass on the plate and stops P2, unless it is one
# of these, which count as zero weight: salt, zest, peel and citrus juice.
ZERO_WEIGHT_WORDS = re.compile(r"\b(salt|zest|peel|rind|lemon juice|lime juice|orange juice|citrus juice|juice of)\b", re.I)
NEGLIGIBLE_REVIEW = ("SPEC_3_mvp.md 12.14.12, Julius 2026-11-06: a plain food (line tag) whose USDA record shows saturated fat at or under the threshold and cholesterol 0, reported or by the "
                     "facts of 12.14.7, never holds up a recipe; prepared products never pass; the rule sets the line's nutrients only")


def not_eaten_inference(ingredient_id: str, name: str, grams: Decimal | None, role: str, reason: str) -> Inference:
    detail = ("lifted out before serving (line tag 'removed'); left out of the calculation and the recipe weight" if role == "removed" else
              "a cooking medium (bath, brine or liquid) whose record reports no saturated fat or cholesterol to speak of; left out of the calculation and the served mass")
    return Inference(kind="excluded_not_eaten", rule_id="T-removed" if role == "removed" else "T-medium", ingredient_id=ingredient_id, name=name, grams=grams,
                     contribution=Decimal(0), detail=detail, reference=f"line tag by the model, checked by code: {reason}"[:400],
                     review_status="SPEC_3_mvp.md 12.3, Julius 2026-11-05: tags decide what is eaten; the model never writes a number")


def composition_inference(ingredient_id: str, name: str, *, fdc_id: int, description: str, match_type: str, sat: float | None, chol: float | None, threshold: Decimal) -> Inference:
    return Inference(kind="excluded_negligible", rule_id=NEGLIGIBLE_RULE_ID, ingredient_id=ingredient_id, name=name, grams=None, value_per_100g=Decimal(str(sat or 0)),
                     contribution=Decimal(0), detail=f"amount missing; USDA {fdc_id} '{description}' ({match_type}) shows {sat} g saturated fat and {chol} mg cholesterol per 100 g (reported, or by the facts of 12.14.7), "
                                                     f"at or under the {threshold} g threshold: counted as zero for both nutrients (12.14.12); its weight is still looked for",
                     reference="USDA record values, read by code; the threshold is MvpConfig.negligible_sat_fat_per_100g", review_status=NEGLIGIBLE_REVIEW)


def herb_spice_inference(ingredient_id: str, name: str, grams: Decimal | None) -> Inference:
    return Inference(kind="excluded_negligible", rule_id=HERB_SPICE_RULE_ID, ingredient_id=ingredient_id, name=name, grams=grams, contribution=Decimal(0),
                     detail="herb or spice left out of the calculation and of the recipe weight; treated as contributing no saturated fat or cholesterol",
                     reference="Julius's decision of 2026-11-05; a labelled simplification, not a USDA value", review_status=HERB_SPICE_REVIEW)


def size_inferences(result: RecipeResult, median_ids: dict[str, str], class_ids: dict[str, str] | None = None) -> list[Inference]:
    """`median_ids`: ingredient_id -> grams_reference of lines the converter weighed at an assumed median size; `class_ids`: of lines weighed by a class-level record's cup (12.12.4)."""
    out = []
    for ing in result.ingredients:
        if ing.ingredient_id in median_ids:
            out.append(Inference(kind="assumed_size_median", ingredient_id=ing.ingredient_id, name=ing.name, grams=ing.grams_in_recipe,
                                 detail=f"the line names a count but no size; weighed at the median of the record's comparable whole-item sizes ({ing.grams_in_recipe} g)",
                                 reference=median_ids[ing.ingredient_id][:400], review_status="D20 revised (Julius, 2026-11-03): median of comparable USDA whole-item weights"))
        if ing.ingredient_id in (class_ids or {}):
            out.append(Inference(kind="class_level_cup_weight", ingredient_id=ing.ingredient_id, name=ing.name, grams=ing.grams_in_recipe,
                                 detail=f"no record of this food has the line's measure; weighed by the cup of a record that names the whole class ({ing.grams_in_recipe} g)",
                                 reference=class_ids[ing.ingredient_id][:400], review_status="SPEC_3_mvp.md 12.12.4, Julius 2026-11-06: a class-level record lends only when no same-food record has the measure"))
    return out


def apply_inference_layer(result: RecipeResult, median_ids: dict[str, str] | None = None, class_ids: dict[str, str] | None = None, facts: NutrientFacts | None = None,
                          bound: str = "high") -> tuple[list[Inference], dict[str, InferredTotal]]:
    """The documented inferences for a Phase 2A result and, per nutrient, the total they would give. Pure Decimal; the result is untouched."""
    inferences = size_inferences(result, median_ids or {}, class_ids)
    totals: dict[str, InferredTotal] = {}
    by_id = {i.ingredient_id: i for i in result.ingredients}
    for nutrient in NUTRIENTS:
        block = result.totals[nutrient]
        inferred_sum = Decimal(0)
        inferred_lines, remaining, remaining_ids = [], [], []
        for ex in block.excludes:
            ing = by_id.get(ex.ingredient_id)
            rule = None
            if facts is not None and ing is not None and ex.reason == f"nutrient_not_reported:{nutrient}" and ing.usda is not None and ing.grams_in_recipe is not None:
                rule = facts.rule(ing, nutrient, bound)
            if rule is None:
                # the calculator lists a line's issues with the state check first, so an unquantified line can read "preparation_unresolved";
                # for the reader the missing quantity is the fact that matters (Phase 3)
                reason = "missing_grams" if ing is not None and ing.grams_in_recipe is None and ex.reason.startswith("preparation") else ex.reason
                remaining.append(f"{ex.name} ({reason})")
                remaining_ids.append(ex.ingredient_id)
                continue
            contribution = ing.grams_in_recipe * rule["value_per_100g"] / Decimal(100)
            inferred_sum += contribution
            inferred_lines.append(ex.ingredient_id)
            inferences.append(Inference(kind=rule["kind"], rule_id=rule["id"], ingredient_id=ing.ingredient_id, name=ing.name, nutrient=nutrient,
                                        value_per_100g=rule["value_per_100g"], grams=ing.grams_in_recipe, contribution=contribution,
                                        detail=f"USDA record {ing.usda.fdc_id} '{ing.usda.description}' has no {nutrient} row (field absent); the record is kept for "
                                               f"what it reports; {nutrient} taken as {rule['value_per_100g']} per 100 g at this bound by fact {rule['id']}",
                                        reference=rule["reference"], review_status=rule["review_status"]))
        complete = block.complete or (not remaining and bool(inferred_lines))
        total = (block.known_subtotal + inferred_sum) if complete else None
        per_serving = (total / result.servings).quantize(PER_SERVING_PLACES, rounding=ROUND_HALF_EVEN) if total is not None else None
        totals[nutrient] = InferredTotal(nutrient=nutrient, source_complete=block.complete, complete_with_inferences=complete, known_subtotal=block.known_subtotal,
                                         inferred_contribution=inferred_sum, total=total, per_serving_total=per_serving, inferred_lines=inferred_lines,
                                         remaining_excludes=remaining, remaining_ids=remaining_ids)
    return inferences, totals


def completeness_basis(totals: dict[str, InferredTotal], has_size_inferences: bool) -> dict[str, str]:
    out = {}
    for n, t in totals.items():
        if t.source_complete and not has_size_inferences:
            out[n] = "complete_source_reported"
        elif t.complete_with_inferences:
            out[n] = "complete_with_inferences"
        else:
            out[n] = "incomplete"
    return out
