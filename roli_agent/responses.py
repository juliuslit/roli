"""Deterministic reply text. Every number here comes from a validated `roli_nutrition` result.

The LLM never writes these replies, so a fabricated or substituted figure has no path in.
Failure replies contain no nutrition numbers at all (the only digits allowed are FDC IDs).
"""

from __future__ import annotations

from typing import Any

from .state import RoliState

SOURCE = "USDA FoodData Central"

# Plain-language reasons for each error code of the nutrition library. Owned by this file.
ERROR_REASONS = {
    "invalid_input": "the search request was invalid",
    "not_found": "USDA has no record with that FDC ID",
    "unsupported_data_type": "the USDA record is of a type Roli does not use",
    "id_mismatch": "USDA returned a different record than the one requested, so its values were discarded",
    "validation_failed": "the USDA record failed Roli's consistency checks, so its values were discarded",
    "malformed_response": "USDA returned a reply Roli could not read",
    "rate_limited": "USDA's hourly request limit was reached",
    "usda_auth_failed": "USDA rejected Roli's access key",
    "usda_unavailable": "USDA FoodData Central could not be reached",
}

NO_VALUES = "No nutrition values are given; Roli does not estimate them from other sources."
MENU_NOTE = (
    "Nutrition for whole dishes is not available yet: Roli does not estimate ingredient weights, "
    "and USDA values describe single foods, not restaurant dishes. Ask about one food for verified USDA values."
)


def format_amount(value: float) -> str:
    """3.214 -> '3.214', 85.0 -> '85', 0.02 -> '0.02'. No rounding of USDA's figures."""
    return f"{value:.10g}"


def nutrition_reply(nutrition: dict[str, Any]) -> str:
    """complete or partial result -> the reply. A null value is said to be unreported, never zero."""
    lines = [
        f"Food: {nutrition['description']}",
        f"{SOURCE} record {nutrition['fdc_id']} ({nutrition['data_type']}), values per 100 g:",
    ]
    for field, label, unit in (("saturated_fat_g", "Saturated fat", "g"), ("cholesterol_mg", "Cholesterol", "mg")):
        value = nutrition.get(field)
        if value is None:
            lines.append(f"- {label}: not reported by USDA for this record")
        else:
            lines.append(f"- {label}: {format_amount(value)} {unit}")
    if nutrition.get("missing_nutrients"):
        lines.append("A value USDA does not report is unknown, not zero.")
    lines.append(f"Source: {SOURCE}.")
    return "\n".join(lines)


def unavailable_reply(food: str, error: dict[str, Any]) -> str:
    reason = ERROR_REASONS.get(error.get("error_code", ""), "the USDA lookup failed")
    return f"Verified nutrition information for {food} is unavailable: {reason}. {NO_VALUES}"


def no_match_reply(food: str, search: dict[str, Any] | None, note: str) -> str:
    candidates = (search or {}).get("candidates") or []
    if not candidates:
        return f"{SOURCE} has no entry matching \"{food}\". {NO_VALUES}"
    shown = "\n".join(f"- {c['fdc_id']}: {c['description']}" for c in candidates[:5])
    return (
        f"{SOURCE} returned entries for \"{food}\", but none matches it ({note}). "
        f"The closest entries were:\n{shown}\n{NO_VALUES} Try naming the food the way USDA does, "
        "for example the species and whether it is cooked or raw."
    )


def other_reply() -> str:
    return (
        "Roli can report verified USDA saturated fat and cholesterol for one specific food "
        "(for example \"cooked chinook salmon\"), or read a menu photo and list its dishes. "
        "Please name one food or send a menu photo."
    )


def unclear_reply() -> str:
    return "Roli could not work out which food you are asking about. " + other_reply()


def menu_reply(menu: dict[str, Any]) -> str:
    items = [i for i in menu.get("items", []) if isinstance(i, dict)]
    dishes = [i for i in items if i.get("category") in ("food", "drink", "add-on")]
    lines = [f"Menu read: {menu.get('readable', 'unknown')}" + (f" ({menu['problems']})" if menu.get("problems") else "")]
    lines.append(f"Items found: {len(dishes)}")
    section = object()
    for item in dishes:
        if item.get("section", "") != section:
            section = item.get("section", "")
            lines.append(f"\n{section or '(no section)'}")
        desc = f" — {item['description']}" if item.get("description") else ""
        price = f" — {item['price']}" if item.get("price") else ""
        lines.append(f"- {item.get('name', '?')}{desc}{price}")
    lines.append("")
    lines.append(MENU_NOTE)
    return "\n".join(lines)


def menu_failed_reply(error: str) -> str:
    return f"Roli could not read the menu photo ({error}). {MENU_NOTE}"


def recipe_reply(result: dict[str, Any]) -> str:
    """Deterministic rendering of a RecipeResult (spec 2A, section 10). Every number is copied from
    the calculator's output; nothing is recomputed here."""
    lines = [f"Recipe: {result['recipe_name']} ({result['servings']} serving(s)); calculation {result['status']}."]
    lines.append("Ingredients:")
    for ing in result["ingredients"]:
        grams = ing["grams_in_recipe"] if ing["grams_in_recipe"] is not None else "unknown amount"
        grams_text = f"{grams} g" if ing["grams_in_recipe"] is not None else grams
        if ing["usda"]:
            ref = f"USDA {ing['usda']['fdc_id']} \"{ing['usda']['description']}\""
        elif ing["usda_error"]:
            ref = f"USDA {ing['usda_error'].get('fdc_id')}: lookup failed ({ing['usda_error'].get('error_code')})"
        else:
            ref = "no USDA record"
        c = ing["contribution"]
        if c["saturated_fat_g"] is None and c["cholesterol_mg"] is None:
            contrib = "not included: " + ", ".join(i for i in ing["issues"] if i not in ("per_serving_quantity_converted", "duplicate_fdc_id"))
        else:
            sat = f"{c['saturated_fat_g']} g saturated fat" if c["saturated_fat_g"] is not None else "saturated fat not reported by USDA"
            chol = f"{c['cholesterol_mg']} mg cholesterol" if c["cholesterol_mg"] is not None else "cholesterol not reported by USDA"
            contrib = f"{sat}, {chol}"
        assumption = f" [{ing['assumption']}]" if ing.get("assumption") else ""
        lines.append(f"- {ing['name']}: {grams_text}; {ref}; {contrib}{assumption}")
    lines.append("Per serving:")
    for nutrient, label in (("saturated_fat_g", "Saturated fat"), ("cholesterol_mg", "Cholesterol")):
        lines.append(f"- {label}: {result['display'][nutrient]}")
    if result["status"] == "incomplete":
        lines.append("These are known subtotals from the ingredients that could be calculated, not totals for the dish.")
    lines.append(f"Basis: {SOURCE} values per 100 g; {result['completeness_note']}.")
    return "\n".join(lines)


def recipe_invalid_reply(error: dict[str, Any]) -> str:
    problems = "; ".join(error.get("problems", [])) or "unknown problem"
    return f"The recipe could not be calculated because its description is invalid: {problems}. {NO_VALUES}"


def dish_reply(estimate: dict[str, Any]) -> str:
    """Deterministic rendering of a DishEstimate (spec 2B, sections 9-10). Every number is copied from the Phase 2A
    objects inside it (per-serving display strings, comparison min/median/max) or is a count of recipes."""
    item, summary = estimate["menu_item"], estimate["summary"]
    lines = [f"Dish: {item['name']}" + (f" ({item['description']})" if item.get("description") else "")]
    lines.append(summary["statement"])
    lines.append(f"Recipes: {summary['n_distinct']} read, {summary['n_relevant']} comparable, {summary['n_calculated']} calculated, "
                 f"{summary['n_complete']} complete, {summary['n_eligible']} in the range.")
    shown = [s for s in estimate["scenarios"] if s["status"] == "calculated"]
    if shown:
        lines.append("Modeled recipes (per serving, USDA FoodData Central values):")
    for s in shown:
        d = s["calculation"]["display"]
        rel = s["relevance"]
        tag = "in range" if s["eligible_for_range"] else f"not in range ({s['ineligible_reason']})"
        lines.append(f"- {s['source']['title']} ({s['source']['host']}, {s['source']['servings']} servings; relevance {rel['grade']}, "
                     f"representativeness {s['representativeness']}; {tag})")
        lines.append(f"  saturated fat: {d['saturated_fat_g']}; cholesterol: {d['cholesterol_mg']}")
        if rel["menu_missing"]:
            lines.append(f"  menu ingredients not in this recipe: {', '.join(rel['menu_missing'])}")
        if s["proxies"]:
            labels = {"saturated_fat_g": "saturated fat", "cholesterol_mg": "cholesterol"}
            shares = ", ".join(f"{labels[n]} {v}%" for n, v in s["proxy_share_percent"].items())
            basis = "of the known subtotal" if s["calculation_status"] == "incomplete" else "of the total"
            lines.append(f"  substitute USDA records: {'; '.join(s['proxies'])} (their share {basis}: {shares or 'none'})")
    rejected = [s for s in estimate["scenarios"] if s["status"] == "rejected"]
    if rejected:
        lines.append("Not comparable: " + "; ".join(f"{s['source']['title']} ({(s['status_reason'] or '').split(':')[0]})" for s in rejected[:6])
                     + ("" if len(rejected) <= 6 else f"; and {len(rejected) - 6} more"))
    if shown:
        lines.append(f"Basis: {SOURCE} values per 100 g through the Phase 2A calculator; ranges describe the published recipes only.")
    return "\n".join(lines)


def dish_failed_reply(error: str) -> str:
    return f"Roli could not build recipe scenarios for this dish ({error}). {NO_VALUES}"


def compose(state: RoliState) -> str:
    """The one place a reply is built. Order matters: failures first, numbers last."""
    food = (state.get("interpretation") or {}).get("food") or state.get("text", "this food")
    intent = state.get("intent")
    if intent == "dish":
        if state.get("dish_error") or not state.get("dish_estimate"):
            return dish_failed_reply(state.get("dish_error") or "no result")
        return dish_reply(state["dish_estimate"])
    if intent == "recipe":
        if state.get("recipe_error") or not state.get("recipe_result"):
            return recipe_invalid_reply(state.get("recipe_error") or {"problems": ["no result"]})
        return recipe_reply(state["recipe_result"])
    if intent == "menu":
        if state.get("menu_error") or not state.get("menu"):
            return menu_failed_reply(state.get("menu_error") or "no readable result")
        return menu_reply(state["menu"])
    if intent == "unclear":
        return unclear_reply()
    if intent == "other":
        return other_reply()
    if state.get("search_error"):
        return unavailable_reply(food, state["search_error"])
    if state.get("selected_fdc_id") is None:
        return no_match_reply(food, state.get("search"), state.get("selection_note", "no matching record"))
    if state.get("nutrition_error"):
        return unavailable_reply(food, state["nutrition_error"])
    if state.get("numbers_allowed") and state.get("nutrition"):
        return nutrition_reply(state["nutrition"])
    return unavailable_reply(food, {"error_code": "usda_unavailable"})
