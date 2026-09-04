# -*- coding: utf-8 -*-
"""Execute the shipped mobile/index.html bundle so a broken artifact fails the build."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import dukpy

from smoke_test_ui import DOM_SHIM, PROBE

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
    check(report["mobilePack"], "bundle: mobile pack mode is enabled")
    check(report["localStoragePersists"], "bundle: learning state persists in localStorage")
    check(report["tocfl8000Words"] == 7517, "bundle: all 7,517 TOCFL workbook rows loaded")
    check(report["ccccWords"] == 1197, "bundle: all 1,197 CCCC workbook rows loaded")
    check(report["tocflCombinedLevels"] == 10, "bundle: all ten workbook levels loaded")
    check(report["tocflLevelSizes"]["novice-1"] == 160, "bundle: Novice 1 keeps 160 first-occurrence words")
    check(report["tocflLevelSizes"]["novice-2"] == 234, "bundle: Novice 2 keeps 234 first-occurrence words")
    check(report["tocflLevelSizes"]["level-1"] == 345, "bundle: Level 1 drops later repeats of the same word")
    check(report["tocflUniqueDuplicates"] == 0, "bundle: no unique Chinese+pinyin word is shown twice")
    check(report["tocflUniqueTotal"] == 7477, "bundle: TOCFL+CCCC display 7,477 unique words")
    check(report["tocflRender"]["levelWordCount"] == 160, "bundle: Novice 1 stays at exactly 160 words")
    check(report["tocflRender"]["categoryCountMatches"], "bundle: category count matches exact filtered words")
    check(report["tocflRender"]["categoryExact"], "bundle: category filter cannot leak levels or categories")
    check(report["tocflRender"]["subcategoryCountMatches"], "bundle: subcategory count matches exact filtered words")
    check(report["tocflRender"]["subcategoryExact"], "bundle: subcategory uses level AND category AND subcategory")
    check(report["tocflClickFlow"]["level"] == "level-3", "bundle: clicking a category keeps the chosen level")
    check(report["tocflClickFlow"]["countText"] != "160 words", "bundle: Level 3 does not fall back to Novice 1 words")
    check(report["tocflClickFlow"]["categoryExact"], "bundle: category clicked in Level 3 shows only Level 3 words")
    check(report["tocflClickFlow"]["subcategoryExact"], "bundle: subcategory clicked in Level 3 stays in that category")
    check(report["tocflRender"]["results"] > 0, f"bundle: TOCFL category page renders ({report['tocflRender']['count']})")
    check(report["totalWords"] > 5900, f"bundle: deduplicated corpus loaded ({report['totalWords']} words)")
    check(report["tocflA1Words"] > 300, f"bundle: TOCFL A1 filter returns words ({report['tocflA1Words']})")
    check(report["tocflCounts"].get("A2", 0) > 300, "bundle: TOCFL A2 count is populated")
    check(report.get("tocflRouteVisible"), "bundle: TOCFL category route opens")
    check(report.get("pronounceRouteVisible"), "bundle: TOCFL pronunciation route opens")
    check(report["duplicatesRemoved"] > 0, f"bundle: removed {report['duplicatesRemoved']} duplicate HSK entries")
    check(report["hskDuplicateExtras"] == 0, "bundle: no duplicate entries remain across HSK 1–6")
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

    for message in report.get("errors", []):
        print("FAIL:", message)

    if failures:
        print(f"\n{len(failures)} bundle check(s) FAILED.")
        sys.exit(1)
    print("\nShipped bundle renders words correctly.")


if __name__ == "__main__":
    main()
