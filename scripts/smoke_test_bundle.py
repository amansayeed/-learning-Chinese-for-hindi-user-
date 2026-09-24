# -*- coding: utf-8 -*-
"""Execute the shipped mobile/index.html bundle so a broken artifact fails the build."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import dukpy

from smoke_test_ui import DOM_SHIM, EXPECTED_SPELLING, PROBE, SYLLABLE_SET, syllable_key

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "mobile" / "index.html"
SCRIPT_RE = re.compile(r"<script(?![^>]*\ssrc=)[^>]*>(.*?)</script>", re.DOTALL | re.IGNORECASE)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    if not BUNDLE.is_file():
        print("FAIL: mobile/index.html missing — run the build first")
        sys.exit(1)

    html = BUNDLE.read_text(encoding="utf-8")
    blocks = [block for block in SCRIPT_RE.findall(html) if block.strip()]
    print(f"Found {len(blocks)} inline script blocks in mobile/index.html")

    # The bundle's own boot scripts touch a real document; the shim replaces them.
    payload = [DOM_SHIM] + blocks + [PROBE]

    try:
        report = json.loads(dukpy.evaljs("\n;\n".join(payload)))
    except dukpy.JSRuntimeError as error:
        print("FAIL: the shipped bundle throws while booting")
        print(error)
        sys.exit(1)

    failures: list[str] = list(report.get("errors", []))

    def check(condition: bool, message: str) -> None:
        if condition:
            print("OK:", message)
        else:
            failures.append(message)
            print("FAIL:", message)

    check(report["storeLoaded"], "bundle: VocabStore initialised")
    check(report["tocflUiLoaded"], "bundle: TocflUI initialised")
    check(report["charactersUiLoaded"], "bundle: CharactersUI initialised")
    check(report["characterCount"] == 3000, "bundle: exactly 3,000 individual characters loaded")
    check(report["characterRender"]["levels"] == 3, "bundle: all three character levels render")
    check(report["characterRender"]["tiles"] == 50, "bundle: character table renders 50 rows per page")
    check(report["characterRender"]["count"] == "1,000 individual characters", "bundle: Basic Reading has 1,000 characters")
    check(report["characterRender"]["details"] > 0, "bundle: character details render")
    check(report["characterRender"]["traditionalAudio"], "bundle: Traditional characters are audio controls")
    check(report["characterRender"]["simplifiedDetails"], "bundle: Simplified characters open details")
    check(report["characterRender"]["exactSpeech"], "bundle: speech receives the exact clicked character")
    check(report["characterRender"]["taiwanVoice"], "bundle: character speech selects zh-TW")
    check(report["characterRender"]["levelCounts"] == [1000, 2000, 3000], "bundle: character levels filter to 1,000/2,000/3,000")
    check(
        report["characterRender"]["clickCounts"] == ["2,000 individual characters", "3,000 individual characters"],
        "bundle: clicking character levels changes the rendered set",
    )
    check(
        report["characterRender"]["pinyinLevelSorted"] == [True, True, True],
        "bundle: all character categories are alphabetical by pinyin",
    )
    check(
        report["characterRender"]["renderedPinyinSorted"],
        "bundle: rendered character rows are alphabetical by pinyin",
    )
    check(
        report["characterDiff"]["title"] == "Traditional and Simplified difference",
        "bundle: difference page title is Traditional and Simplified difference",
    )
    check(
        report["characterDiff"]["count"] > 0 and report["characterDiff"]["count"] < 3000,
        "bundle: difference page is a subset of the 3,000 characters",
    )
    check(report["characterDiff"]["allDifferent"], "bundle: every listed character differs between scripts")
    check(report["characterDiff"]["levelsHidden"], "bundle: difference page hides the level switch")
    check(
        report.get("spellingOrder") == EXPECTED_SPELLING,
        "bundle: full Pinyin spelling puts āngzāng before ángguì",
    )
    tocfl_sequence = report.get("tocflPinyinSequence") or []
    resorted = sorted(tocfl_sequence, key=syllable_key)
    check(
        len(tocfl_sequence) > 1000 and tocfl_sequence == resorted,
        "bundle: second full sort confirms every TOCFL word is in Pinyin order",
    )
    check(report.get("browseTraditionalAudio"), "bundle: Traditional words play exact displayed text")
    check(report.get("browseSimplifiedDetails"), "bundle: Simplified words open details")
    check(report.get("wordDetailsComplete"), "bundle: word details include meanings, example, and pronunciation")
    check(report["columnControls"]["hideButtons"] == 0, "bundle: column headers have no Hide buttons")
    check(report["columnControls"]["mobileButtons"] == 3, "bundle: one bar hides or shows each column")
    check(report["columnControls"]["labelledCells"], "bundle: optional columns keep responsive labels")
    check(report["columnControls"]["pinyinHidden"], "bundle: Pinyin column can be hidden")
    check(report["columnControls"]["restoreControl"], "bundle: hidden columns expose Show controls")
    check(report["columnControls"]["independent"], "bundle: column visibility is independent")
    check(report["columnControls"]["persisted"], "bundle: column visibility persists")
    check(report["columnControls"]["restored"], "bundle: hidden columns can be restored")
    check(report["columnControls"]["rowToggles"] == 0, "bundle: word rows have no Hide button")
    check(report["columnControls"]["rowShows"] == 6, "bundle: hidden columns offer Show on every row")
    check(report["columnControls"]["rowShowsOnRight"], "bundle: Show buttons sit on the right of the row")
    check(report["columnControls"]["rowWordOnly"], "bundle: Show Word reveals one row only")
    check(report["columnControls"]["rowCollapsed"], "bundle: a word click can leave only that word")
    check(report["columnControls"]["rowIsolated"], "bundle: one row stays independent")
    check(report["columnControls"]["rowRestored"], "bundle: clicking the word again restores the row")
    check(report["mobilePack"], "bundle: mobile pack mode is enabled")
    check(report["localStoragePersists"], "bundle: learning state persists in localStorage")
    check(report["tocfl8000Words"] == 7517, "bundle: all 7,517 TOCFL workbook rows loaded")
    check(report["ccccWords"] == 1197, "bundle: all 1,197 CCCC workbook rows loaded")
    check(report["tocflCombinedLevels"] == 10, "bundle: all ten workbook levels loaded")
    check(report["tocflLevelSizes"]["novice-1"] == 160, "bundle: Novice 1 keeps 160 first-occurrence words")
    check(report["tocflLevelSizes"]["novice-2"] == 234, "bundle: Novice 2 keeps 234 first-occurrence words")
    check(report["tocflLevelSizes"]["level-1"] < 347, "bundle: Level 1 drops later repeats of the same word")
    check(report["tocflUniqueDuplicates"] == 0, "bundle: no unique Chinese+pinyin word is shown twice")
    check(
        report["categoriesRender"]["uniqueWords"] + report["categoriesRender"]["duplicatesMerged"] == 8714,
        "bundle: deduplication accounts for all 8,714 source rows",
    )
    check(report["tocflAllLevelsSorted"], "bundle: every TOCFL and CCCC level is alphabetical by pinyin")
    check(report["tocflLevelAssignmentCorrect"], "bundle: every TOCFL and CCCC word keeps its level")
    check(
        sum(report["tocflLevelSizes"].values()) == report["tocflUniqueTotal"],
        "bundle: level counts account for every deduplicated TOCFL/CCCC word",
    )
    check(report["tocflRender"]["levelWordCount"] == 160, "bundle: Novice 1 stays at exactly 160 words")
    check(report["tocflEntryLevel"]["buttons"] == 5, "bundle: TOCFL switch shows five bands")
    check(report["tocflEntryLevel"]["titled"], "bundle: merged band is titled 入門級 · Level 1")
    check(report["tocflEntryLevel"]["onlyEntry"] and report["tocflEntryLevel"]["coversEach"], "bundle: 入門級 · Level 1 contains the six merged bands")
    check(report["tocflRender"]["categoryCountMatches"], "bundle: category count matches exact filtered words")
    check(report["tocflRender"]["categoryExact"], "bundle: category filter cannot leak levels or categories")
    check(report["tocflRender"]["subcategoryCountMatches"], "bundle: subcategory count matches exact filtered words")
    check(report["tocflRender"]["subcategoryExact"], "bundle: subcategory uses level AND category AND subcategory")
    check(report["tocflClickFlow"]["level"] == "level-3", "bundle: clicking a category keeps the chosen level")
    check(report["tocflClickFlow"]["countText"] != "160 words", "bundle: Level 3 does not fall back to Novice 1 words")
    check(report["tocflClickFlow"]["categoryExact"], "bundle: category clicked in Level 3 shows only Level 3 words")
    check(report["tocflClickFlow"]["subcategoryExact"], "bundle: subcategory clicked in Level 3 stays in that category")
    check(
        report["tocfl8000"]["count"] == sum(
            report["tocflLevelSizes"][level]
            for level in ("novice-1", "novice-2", "level-1", "level-2", "level-3", "level-4", "level-5")
        ),
        "bundle: Official TOCFL vocabulary shows every TOCFL 8000 word",
    )
    check(report["tocfl8000"]["title"] == "TOCFL 8000", "bundle: Official TOCFL vocabulary is titled TOCFL 8000")
    check("arranged by pinyin" in report["tocfl8000"]["subtitle"], "bundle: Official TOCFL vocabulary is arranged by pinyin")
    check(report["tocfl8000"]["levelsHidden"], "bundle: Official TOCFL vocabulary has no level switcher")
    check(report["tocfl8000"]["pinyinSorted"], "bundle: Official TOCFL vocabulary list is in pinyin order")
    check(report["tocfl8000"]["onlyTocfl"], "bundle: Official TOCFL vocabulary leaves out CCCC-only levels")
    check(report["tocfl8000"]["largeBands"]["sized"]["min"] >= 300, "bundle: noun, action-verb, and adjective topics each have at least 300 words")
    check(report["tocfl8000"]["largeBands"]["adverbs"]["count"] == 1, "bundle: adverbs stay in one topic")
    check(report["tocflRender"]["results"] > 0, f"bundle: TOCFL category page renders ({report['tocflRender']['count']})")
    check(report["categoriesRender"]["taxonomy"] == 61, "bundle: split topic taxonomy loaded")
    check(report["categoriesRender"]["cards"] == 61, "bundle: Categories landing renders every topic card")
    check(report["categoriesRender"]["dynamicCounts"], "bundle: category counts are dynamic")
    check(report["categoriesRender"]["duplicatesMerged"] > 0, "bundle: duplicate source rows are merged")
    check(report["categoriesRender"]["strictSources"], "bundle: Categories uses only TOCFL and CCCC")
    check(report["categoriesRender"]["categoryExact"], "bundle: detail is restricted to one primary category")
    check(report["categoriesRender"]["prioritySorted"], "bundle: category words use learning-priority order")
    check(report["categoriesRender"]["traditionalSearch"], "bundle: Traditional search works")
    check(report["categoriesRender"]["pinyinSearch"], "bundle: Pinyin search works")
    check(report["categoriesRender"]["englishSearch"], "bundle: English search works")
    check(report["categoriesRender"]["sourceMetadata"], "bundle: category rows show source metadata")
    check(report["categoriesRender"]["mergedSource"], "bundle: shared words show TOCFL + CCCC")
    check(report["categoriesRender"]["pagination"], "bundle: large categories paginate")
    check(report["categoriesRender"]["detailVisible"], "bundle: category card opens detail")
    check(report["categoriesRender"]["routeVisible"], "bundle: category route opens Categories panel")
    check(report["totalWords"] > 5900, f"bundle: deduplicated corpus loaded ({report['totalWords']} words)")
    check(report["tocflA1Words"] > 300, f"bundle: TOCFL A1 filter returns words ({report['tocflA1Words']})")
    check(report["tocflCounts"].get("A2", 0) > 300, "bundle: TOCFL A2 count is populated")
    check(report.get("tocflRouteVisible"), "bundle: TOCFL category route opens")
    check(report.get("pronounceRouteVisible"), "bundle: TOCFL pronunciation route opens")
    check(report.get("charactersRouteVisible"), "bundle: Chinese Characters route opens")
    check(report["tocflGroups"]["heads"] == 0, "bundle: TOCFL/CCCC is one level-wide list")
    check(report["tocflGroups"]["pinyinSorted"], "bundle: TOCFL/CCCC level is alphabetical by pinyin")
    check(report["tocflGroups"]["numberingContinuous"], "bundle: TOCFL/CCCC numbering is continuous")
    check(
        report["toneOrder"] == ["bā", "bá", "bǎ", "bà", "ba"],
        "bundle: pinyin sorting keeps tone order 1→4 before the neutral tone",
    )
    check(report.get("browsePinyinSorted"), "bundle: Browse lists words alphabetically by pinyin")
    check(report["sandboxedNav"]["detected"], "bundle: content:// documents are detected as sandboxed")
    check(report["sandboxedNav"]["hashUntouched"], "bundle: sandboxed navigation leaves the URL alone")
    check(report["sandboxedNav"]["viewSwitched"], "bundle: sandboxed navigation still switches the view")
    check(report["duplicatesRemoved"] > 0, f"bundle: removed {report['duplicatesRemoved']} duplicate HSK entries")
    check(report["hskDuplicateExtras"] == 0, "bundle: no duplicate entries remain across HSK 1–6")
    check(report["hskAllLevelsSorted"], "bundle: every HSK level is alphabetical by pinyin")
    check(report["hskLevelAssignmentCorrect"], "bundle: every HSK word keeps its assigned level")
    hai = [str(value).lower() for value in report["haiFamily"]]
    try:
        root = hai.index("hái")
        shi = hai.index("hái shi")
        you = hai.index("hái yǒu")
        related_order = root < shi < you
    except ValueError:
        related_order = False
    check(related_order, "bundle: related words are root-first (hái → hái shi → hái yǒu)")
    check(report["browseHtml"] > 0, f"bundle: Browse renders ({report['browseHtml']} chars)")
    check(report["browseSerials"] == 50, "bundle: Browse shows exactly 50 numbered words per page")
    check("Page 1 of" in report["browsePagination"], "bundle: Browse pagination is visible")
    for view, data in report["levels"].items():
        check(data["results"] > 0, f"bundle: {view} renders words ({data['count']})")
        check(data["serials"] == 50, f"bundle: {view} shows 50 numbered words per page")
        check("Page 1 of" in data["pagination"], f"bundle: {view} has page navigation")
        check(data["groupHeads"] == 0, f"bundle: {view} remains one level-wide list")
        check(data["pinyinSorted"], f"bundle: {view} is globally alphabetical by pinyin")
        check(data["numberingContinuous"], f"bundle: {view} numbering is continuous")

    for message in report.get("errors", []):
        print("FAIL:", message)

    if failures:
        print(f"\n{len(failures)} bundle check(s) FAILED.")
        sys.exit(1)
    print("\nShipped bundle renders words correctly.")


if __name__ == "__main__":
    main()
