# -*- coding: utf-8 -*-
"""Verify the unified app and canonical vocabulary without Node.js."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "mobile" / "index.html"
MASTER = ROOT / "data" / "vocabulary-master.json"
REPORT = ROOT / "data" / "vocabulary-master-report.json"
OVERRIDES = ROOT / "data" / "vocabulary-linguistic-overrides.json"
REVIEW = ROOT / "data" / "vocabulary-linguistic-review.json"
DEVANAGARI_RE = re.compile(r"[\u0900-\u097f]")
PINYIN_RE = re.compile(
    r"^[A-Za-züÜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜńňǹḿĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛ\s'’/-]+$"
)
DICTIONARY_ARTIFACT_RE = re.compile(r"\bCL\s*:|[|｜]|\b(?:sb|sth)\b", re.IGNORECASE)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK:", message)


def check_javascript_syntax() -> None:
    """Parse every shipped script. Without this, a stray quote silently blanks the app."""
    try:
        import esprima
    except ImportError:
        raise AssertionError(
            "esprima is required to syntax-check JavaScript — run: pip install -r requirements.txt"
        )
    scripts = sorted((ROOT / "js").glob("*.js"))
    check(bool(scripts), "app JavaScript files found")
    for path in scripts:
        try:
            esprima.parseScript(path.read_text(encoding="utf-8"))
        except Exception as error:
            raise AssertionError(f"{path.relative_to(ROOT)} has a syntax error: {error}")
    print(f"OK: {len(scripts)} JavaScript files parse cleanly")


def fold(value: object) -> str:
    normalized = unicodedata.normalize("NFD", str(value or "").lower())
    return (
        "".join(char for char in normalized if not unicodedata.combining(char))
        .replace("u:", "u")
        .replace("v", "u")
    )


def main() -> None:
    check_javascript_syntax()
    check(HTML.is_file(), "mobile/index.html exists")
    html = HTML.read_text(encoding="utf-8")
    check(HTML.stat().st_size > 6_000_000, "unified bundle includes canonical data")
    for marker in (
        "window.__CHINESE_STORAGE_PATCHED__",
        "window.__UNIFIED_APP__=true",
        "window.__VOCAB_MASTER__",
        "window.__TOCFL_8000__",
        "window.__TOCFL_CCCC__",
        "window.__CHARACTERS__",
        "window.LearningState",
        "window.VocabStore",
        "window.VocabularyUI",
        "window.TocflStore",
        "window.CategoriesUI",
        "window.__CATEGORY_TAXONOMY__",
        'id="app-view-dashboard"',
        'id="app-view-browse"',
        'id="app-view-categories"',
        'id="app-view-learn"',
        'id="app-view-favorites"',
        'id="app-view-progress"',
        'id="browse-search"',
        'id="browse-hsk"',
        'id="browse-category"',
        'data-content-tab="vocabulary"',
        'data-content-tab="sentences"',
        'data-hsk-tab="1"',
        'data-hsk-tab="2"',
        'data-hsk-tab="3"',
        'data-hsk-tab="4"',
        'data-hsk-tab="5"',
        'data-hsk-tab="6"',
        'data-app-view="home"',
        'data-app-view="learn"',
        'data-app-view="browse"',
        'data-app-view="progress"',
        'id="start-today"',
        'id="app-view-level"',
        'id="app-view-tocfl"',
        'data-app-view="tocfl"',
        'id="app-view-tocfl8000"',
        'data-tocfl-8000',
        'data-app-view="tocfl8000"',
        'id="app-view-characters"',
        'data-app-view="characters"',
        'id="app-view-script-diff"',
        'data-character-diff',
        'data-app-view="script-diff"',
        "data-character-browser",
        "data-tocfl-browser",
        "data-tocfl-pronunciation",
        'id="level-switch"',
        'id="level-categories"',
        "topic-chip-row",
        'id="level-search"',
        'id="level-results"',
        'id="browse-pagination"',
        'id="level-pagination"',
        'data-app-view="favorites"',
        'data-app-view="pronounce"',
        'data-app-view="tones"',
        'data-app-view="hsk1"',
        'data-app-view="hsk6"',
        'data-app-view="hsk-other"',
        'data-srs-answer="know"',
        'data-srs-answer="forgot"',
        "answerReview",
        "todayQueue",
        "sentence-card__script--traditional",
        "sentence-card__script--simplified",
        "data-vocab-column-toggle=",
    ):
        check(marker in html, f"bundle marker {marker}")

    for retired in (
        'id="app-view-words"', 'class="word-table"', 'id="study-panel"',
        "ChineseVocabApp", "data-vocab-column-hide=",
    ):
        check(retired not in html, f"bundle drops retired markup {retired}")

    payload = json.loads(MASTER.read_text(encoding="utf-8"))
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
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
    ids = {word["id"] for word in words}
    override_ids = set(overrides["overrides"])
    review_ids = {record["id"] for record in review["records"]}
    check(overrides["recordCount"] == len(words), "linguistic override count covers every word")
    check(override_ids == ids, "linguistic override IDs exactly match canonical IDs")
    check(len(review_ids) == len(review["records"]) == len(words), "review manifest IDs are complete and unique")
    check(review_ids == ids, "review manifest exactly accounts for canonical IDs")
    check(review["unresolvedRecords"] == 0, "review manifest has no unresolved records")
    check(report["linguisticReview"]["unresolvedCount"] == 0, "canonical report has no unresolved linguistic records")
    check(
        all(word.get("review", {}).get("status") == "reviewed" for word in words),
        "every vocabulary record is marked reviewed",
    )
    check(
        all(
            word["example"].get("generated") is False
            and word["example"].get("needsReview") is False
            for word in words
        ),
        "every example is contextual and reviewed",
    )
    check(
        all(PINYIN_RE.fullmatch(word["pinyin"]) for word in words),
        "all headword Pinyin uses valid Hanyu Pinyin characters",
    )
    check(
        all(DEVANAGARI_RE.search(word["hindi"]) for word in words),
        "every Hindi meaning contains Devanagari text",
    )
    check(
        not any(
            DICTIONARY_ARTIFACT_RE.search(word["english"] + " " + word["hindi"])
            for word in words
        ),
        "learner meanings contain no dictionary metadata artifacts",
    )
    check(
        all(
            word.get("example", {}).get("traditional")
            and word.get("example", {}).get("simplified")
            and word.get("example", {}).get("topic") == word["primaryCategory"]
            and word.get("example", {}).get("sentenceCategory")
            for word in words
        ),
        "every sentence has both Chinese forms and HSK-plus-topic classification",
    )
    for level in (1, 2, 3, 4, 5):
        level_sentences = [
            word["example"]
            for word in words
            if word["hsk"]["level"] == level
            and word.get("example", {}).get("hskLevel") == level
        ]
        check(bool(level_sentences), f"HSK {level} sentence category has results")

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
    sentence_combined = [
        word["example"]
        for word in combined
        if word["example"]["sentenceCategory"] == "HSK 3 · Transportation"
    ]
    check(bool(sentence_combined), "combined HSK 3 + Transportation sentence category has results")
    print(
        f"Verified {len(words)} canonical words, {report['totalCategories']} taxonomy "
        f"categories, and {report['usedCategoryCount']} categories in use."
    )


if __name__ == "__main__":
    main()
