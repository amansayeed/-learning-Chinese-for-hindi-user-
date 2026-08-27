# -*- coding: utf-8 -*-
"""Verify the unified app and canonical vocabulary without Node.js."""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "mobile" / "index.html"
MASTER = ROOT / "data" / "vocabulary-master.json"
REPORT = ROOT / "data" / "vocabulary-master-report.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK:", message)


def fold(value: object) -> str:
    normalized = unicodedata.normalize("NFD", str(value or "").lower())
    return (
        "".join(char for char in normalized if not unicodedata.combining(char))
        .replace("u:", "u")
        .replace("v", "u")
    )


def main() -> None:
    check(HTML.is_file(), "mobile/index.html exists")
    html = HTML.read_text(encoding="utf-8")
    check(HTML.stat().st_size > 6_000_000, "unified bundle includes canonical data")
    for marker in (
        "window.__CHINESE_STORAGE_PATCHED__",
        "window.__UNIFIED_APP__=true",
        "window.__VOCAB_MASTER__",
        "window.LearningState",
        "window.VocabStore",
        "window.VocabularyUI",
        'id="app-view-dashboard"',
        'id="app-view-browse"',
        'id="app-view-learn"',
        'id="app-view-favorites"',
        'id="app-view-progress"',
        'id="browse-search"',
        'id="browse-hsk"',
        'id="browse-category"',
    ):
        check(marker in html, f"bundle marker {marker}")

    payload = json.loads(MASTER.read_text(encoding="utf-8"))
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    words = payload["words"]
    check(len(words) == payload["meta"]["wordCount"], "master word count matches metadata")
    check(len(words) == report["totalUniqueWords"], "report unique count matches master")
    check(
        report["sourceAccounting"]["totalInputRows"]
        == report["sourceAccounting"]["totalAccountedRows"],
        "every source row is accounted for",
    )
    check(not report["sourceAccounting"]["unaccountedRows"], "no unaccounted source rows")
    check(report["missingRequiredFieldCount"] == 0, "no required fields are missing")
    check(report["stableIdCollisionCount"] == 0, "stable IDs are unique")
    check(len({word["id"] for word in words}) == len(words), "word IDs are unique in payload")
    check(
        all(
            word.get(field)
            for word in words
            for field in ("traditional", "simplified", "pinyin", "english", "hindi", "primaryCategory")
        ),
        "every word has required multilingual and category fields",
    )
    check(
        all(
            word["hsk"]["level"] in (None, 1, 2, 3, 4, 5, 6)
            and len(word["hsk"]["levels"]) <= 1
            for word in words
        ),
        "HSK levels are authoritative and unambiguous",
    )
    check(report["totalCategories"] >= 60, "requested category taxonomy is represented")
    check(report["multipleCategoryWordCount"] > 0, "secondary category tags are present")

    def searchable(word: dict) -> str:
        return fold(
            " ".join(
                [
                    word["traditional"],
                    word["simplified"],
                    word["pinyin"],
                    word["english"],
                    word["hindi"],
                    word["primaryCategory"],
                    " ".join(word["secondaryCategories"]),
                ]
            )
        )

    for query in ("水", "shuǐ", "shui", "water", "पानी"):
        results = [word for word in words if fold(query) in searchable(word)]
        check(any(word["traditional"] == "水" for word in results), f"search finds 水 using {query}")
    for query in ("nv", "nu:"):
        results = [word for word in words if fold(query) in searchable(word)]
        check(any(word["traditional"] == "女" for word in results), f"pinyin alias search finds 女 using {query}")

    combined = [
        word
        for word in words
        if word["hsk"]["level"] == 3
        and "Transportation" in [word["primaryCategory"], *word["secondaryCategories"]]
    ]
    check(bool(combined), "combined HSK 3 + Transportation filter has results")
    print(
        f"Verified {len(words)} canonical words, {report['totalCategories']} taxonomy "
        f"categories, and {report['usedCategoryCount']} categories in use."
    )


if __name__ == "__main__":
    main()
