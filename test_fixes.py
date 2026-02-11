#!/usr/bin/env python3
"""
Test script for the DraCor MCP server.

Tests the 6 bug fixes applied during code review, plus basic smoke tests
for resources and tools. Uses the live DraCor API.
"""

import sys
import importlib

# ---------------------------------------------------------------------------
# Import the server module
# ---------------------------------------------------------------------------
mod = importlib.import_module("dracor_mcp_fastmcp")

# Expose module-level names for convenience
validate_name = mod.validate_name
validate_wikidata_id = mod.validate_wikidata_id
get_corpora = mod.get_corpora
get_plays = mod.get_plays
get_play = mod.get_play
get_characters = mod.get_characters
get_plays_with_character = mod.get_plays_with_character
search_plays = mod.search_plays
analyze_character_relations = mod.analyze_character_relations
analyze_full_text = mod.analyze_full_text
compare_plays = mod.compare_plays
analyze_play_structure = mod.analyze_play_structure

passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


# ===== Fix #2: Wikidata ID validation ======================================
print("\n--- Fix #2: Wikidata ID validation ---")

# Valid IDs
test("valid Q42", validate_wikidata_id("Q42") == "Q42")
test("valid Q131578", validate_wikidata_id("Q131578") == "Q131578")

# Invalid IDs should raise
for bad_id, label in [("", "empty"), ("42", "no Q prefix"), ("Q", "Q alone"),
                       ("Q42abc", "letters after digits"), ("../etc", "path traversal"),
                       ("Q42/../../admin", "nested traversal")]:
    try:
        validate_wikidata_id(bad_id)
        test(f"reject {label}", False, f"should have raised for {bad_id!r}")
    except ValueError:
        test(f"reject {label}", True)

# The resource should return an error dict (not crash) for bad input
result = get_plays_with_character("../../admin")
test("resource returns error for bad wikidata_id", "error" in result)


# ===== Fix #1: Variable shadowing in search_plays ==========================
print("\n--- Fix #1: Variable shadowing in search_plays ---")

# Search within a specific corpus and verify filters_applied still reports
# the original corpus_name filter, not the last iterated corpus name.
result = search_plays(corpus_name="shake")
test("search_plays returns results", result.get("count", 0) > 0,
     f"count={result.get('count')}")
test("filters_applied.corpus_name preserved",
     result.get("filters_applied", {}).get("corpus_name") == "shake",
     f"got {result.get('filters_applied', {}).get('corpus_name')!r}")

# All returned plays should belong to the requested corpus
if result.get("results"):
    all_shake = all("shake" in r.get("corpus", "").lower()
                     for r in result["results"])
    test("all results from 'shake' corpus", all_shake)
else:
    test("all results from 'shake' corpus", False, "no results returned")


# ===== Fix #4: Year filter with unknown years ==============================
print("\n--- Fix #4: Year filter with unknown years ---")

# Search for plays in a narrow year range
result = search_plays(corpus_name="shake", year_from=1595, year_to=1600)
test("year-filtered search returns results", result.get("count", 0) > 0)

# None of the returned plays should have year=0 (the old bug)
for r in result.get("results", []):
    play = r.get("play", {})
    year = play.get("yearNormalized") or play.get("yearWritten") or play.get("yearPrinted")
    if year is not None and year == 0:
        test("no play with year=0 in filtered results", False, f"play={play.get('name')}")
        break
else:
    test("no play with year=0 in filtered results", True)


# ===== Fix #3: get_play() return value in analyze_full_text ================
print("\n--- Fix #3: get_play() return value handled correctly ---")

# get_play should return the play data directly (has "title" key, not "play" key)
play_data = get_play("shake", "hamlet")
test("get_play returns play data directly",
     "title" in play_data and "play" not in play_data,
     f"keys: {list(play_data.keys())[:5]}")

# analyze_full_text should include play metadata (title) in the result
result = analyze_full_text("shake", "hamlet")
if "error" in result:
    test("analyze_full_text play metadata present", False, result["error"])
else:
    play_section = result.get("play", {})
    test("analyze_full_text play metadata present",
         play_section.get("title") is not None,
         f"play keys: {list(play_section.keys())[:5]}")


# ===== Fix #5: O(n²) → O(n) character lookup ==============================
print("\n--- Fix #5: Character relation lookup uses dict ---")

result = analyze_character_relations("shake", "hamlet")
if "error" in result:
    test("analyze_character_relations succeeds", False, result["error"])
else:
    test("analyze_character_relations succeeds", True)
    # Check that character names were resolved (not just IDs)
    top = result.get("strongestRelations", [])
    if top:
        has_name = any(not r["source"].startswith("#") for r in top)
        test("character names resolved in relations", has_name,
             f"first source={top[0]['source']}")
    else:
        test("character names resolved in relations", False, "no relations returned")


# ===== Fix #6: Division by zero in analyze_full_text =======================
print("\n--- Fix #6: dialogue_to_direction_ratio ---")

if "error" not in result:
    # Re-use the analyze_full_text result from Fix #3 test
    aft_result = analyze_full_text("shake", "hamlet")
    analysis = aft_result.get("analysis", {})
    ratio = analysis.get("dialogue_to_direction_ratio")
    # ratio should be None or a float, never a misleading fallback
    test("ratio is None or float",
         ratio is None or isinstance(ratio, (int, float)),
         f"ratio={ratio!r} type={type(ratio)}")
    test("text_length > 0", analysis.get("text_length", 0) > 0)


# ===== Smoke tests: basic resources ========================================
print("\n--- Smoke tests: resources ---")

corpora = get_corpora()
test("get_corpora returns list", len(corpora.get("corpora", [])) > 0)

plays = get_plays("shake")
test("get_plays(shake) returns plays", len(plays.get("plays", [])) > 0)

chars = get_characters("shake", "hamlet")
test("get_characters returns characters", len(chars.get("characters", [])) > 0)


# ===== Smoke test: compare_plays ==========================================
print("\n--- Smoke tests: tools ---")

cmp = compare_plays("shake", "hamlet", "shake", "romeo-and-juliet")
test("compare_plays succeeds", "error" not in cmp and "plays" in cmp)

structure = analyze_play_structure("shake", "hamlet")
test("analyze_play_structure succeeds", "error" not in structure and "title" in structure)


# ===== Summary =============================================================
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
print(f"{'='*50}")
sys.exit(1 if failed else 0)
