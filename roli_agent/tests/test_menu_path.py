"""Menu photo path: dishes and listed ingredients, no nutrition numbers, no USDA calls."""

from __future__ import annotations

import json
import re

from conftest import ROOT, make_graph, menu_expected, run

PHOTO_03 = ROOT / "menu_test_set" / "telegram_1280" / "menu_03_own_IMG_5185.jpg"


def test_menu_photo_lists_dishes_without_totals():
    expected = menu_expected(3)                          # the answer key for the Flour + Water photo
    graph, llm, rec = make_graph([json.dumps(expected)])  # the scripted reader answers with the key
    state = run(graph, "Hey, what should I order?", photo_path=str(PHOTO_03))

    assert state["intent"] == "menu"
    assert state["menu_error"] is None
    assert len(state["menu"]["items"]) == len(expected["items"]) == 19
    assert rec.requests == []                             # no USDA call on this path in Phase 1E
    assert llm.prompts == ['["text", "image_url"]']       # one call: prompt text + the photo
    reply = state["response"]
    assert "Items found: 18" in reply                     # the cookbook line is category "other"
    assert "- BLUEFIN CRUDO — bottarga, muscat grape, chive — 22" in reply
    assert "- LITTLE GEM LETTUCES — tahini vinaigrette, pecorino sardo, toasted sesame — 18" in reply
    assert "KING SALMON" in reply and "FLOUR+WATER PASTA COOKBOOK" not in reply
    assert "Nutrition for whole dishes is not available yet" in reply
    assert not re.search(r"\d+(\.\d+)?\s?(g|mg)\b", reply), "a nutrition-looking number in the menu reply"
    assert state.get("numbers_allowed") is not True


def test_menu_reply_preserves_readability_problems():
    expected = menu_expected(3)
    partly = dict(expected, readable="partly", problems="right edge cut off")
    graph, _, _ = make_graph([json.dumps(partly)])
    state = run(graph, "", photo_path=str(PHOTO_03))
    assert state["response"].startswith("Menu read: partly (right edge cut off)")


def test_unreadable_reader_output_is_reported_not_invented():
    graph, _, rec = make_graph(["I cannot read this image, sorry."])
    state = run(graph, "", photo_path=str(PHOTO_03))
    assert state["menu"] is None and state["menu_error"]
    assert "could not read the menu photo" in state["response"]
    assert rec.requests == []


def test_missing_photo_file_is_reported():
    graph, llm, _ = make_graph([])                        # the LLM must not even be called
    state = run(graph, "", photo_path="/nowhere/menu.jpg")
    assert "photo could not be opened" in state["menu_error"]
    assert llm.prompts == []
    assert "could not read the menu photo" in state["response"]
