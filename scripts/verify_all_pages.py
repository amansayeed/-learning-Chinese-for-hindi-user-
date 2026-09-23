# -*- coding: utf-8 -*-
"""Audit every source and generated desktop/mobile HTML page."""
from __future__ import annotations

import re
import json
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "pages"

SOURCE_PAGES = [
    "app.html", "tocfl.html", "tocfl-8000.html", "categories.html", "characters.html", "character-diff.html", "pronunciation.html", "tones.html",
]
ROOT_PAGES = [
    "START.html", "index.html", "chinese.html", "tocfl.html", "tocfl-8000.html", "categories.html", "characters.html",
    "character-diff.html", "pronunciation.html", "tones.html",
]
MOBILE_PAGES = [
    "START.html", "index.html", "chinese.html",
    "tocfl.html", "tocfl-8000.html", "categories.html", "characters.html", "character-diff.html", "pronunciation.html", "tones.html",
]
# The retired table/study pages must stay gone so no link can reach them again.
REMOVED_PAGES = [
    "index.html", "hsk.html", "hsk2.html", "hsk3.html", "hsk4.html", "hsk5.html", "hsk6.html",
]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK:", message)


def local_refs(html: str, attribute: str) -> list[str]:
    values = re.findall(rf'\b{attribute}=["\']([^"\']+)["\']', html, flags=re.I)
    return [
        unquote(value)
        for value in values
        if not re.match(r"^(?:[a-z]+:|//|#)", value, flags=re.I)
    ]


def audit_source(path: Path) -> None:
    html = path.read_text(encoding="utf-8")
    ids = re.findall(r'\bid=["\']([^"\']+)', html)
    check(not [key for key, count in Counter(ids).items() if count > 1], f"{path.name}: unique IDs")
    for reference in local_refs(html, "src") + local_refs(html, "href"):
        clean = reference.split("#", 1)[0].split("?", 1)[0].removeprefix("./")
        if not clean or clean.endswith(".html"):
            continue
        target = (path.parent / clean).resolve() if reference.startswith("../") else ROOT / clean
        check(target.exists(), f"{path.name}: asset exists {clean}")
    check(
        "#categories" in html or "chinese.html#categories" in html or "#browse" in html,
        f"{path.name}: browse navigation is available",
    )


def audit_generated(path: Path) -> None:
    check(path.is_file(), f"generated page exists: {path.relative_to(ROOT)}")
    html = path.read_text(encoding="utf-8")
    ids = re.findall(r'\bid=["\']([^"\']+)', html)
    duplicates = [key for key, count in Counter(ids).items() if count > 1]
    check(not duplicates, f"{path.relative_to(ROOT)}: no duplicate IDs")
    check(
        not re.search(r'<script[^>]+\ssrc=["\']', html, flags=re.I),
        f"{path.relative_to(ROOT)}: scripts are bundled",
    )
    check(
        not re.search(r'<link[^>]+rel=["\']stylesheet', html, flags=re.I),
        f"{path.relative_to(ROOT)}: styles are bundled",
    )
    # A <base> makes even #fragment links resolve against the base URL, which on a
    # content:// document is a directory Android will not serve.
    check(
        "data-chinese-root" not in html,
        f"{path.relative_to(ROOT)}: installs no <base> that would break #links",
    )
    for reference in local_refs(html, "href"):
        clean = reference.split("#", 1)[0].split("?", 1)[0]
        if not clean or not clean.endswith(".html"):
            continue
        target = (path.parent / clean).resolve()
        check(target.is_file(), f"{path.relative_to(ROOT)}: link target exists {clean}")
    if path.name == "START.html":
        # The launcher carries its own guard: it has no bundled scripts.
        check(
            'id="sandbox-note"' in html and "content://" not in html.split("<script>")[0],
            f"{path.relative_to(ROOT)}: launcher explains one-file sharing",
        )
    else:
        check(
            "#categories" in html or "chinese.html#categories" in html or "#browse" in html,
            f"{path.relative_to(ROOT)}: browse navigation is available",
        )
        check(
            "window.__CHINESE_STORAGE_PATCHED__" in html,
            f"{path.relative_to(ROOT)}: safe storage is bundled",
        )
        # Without this guard a tap on any link ends on ERR_FILE_NOT_FOUND when the
        # page was shared with the browser as a lone content:// document.
        check(
            "sandboxed-nav-notice" in html,
            f"{path.relative_to(ROOT)}: content:// navigation guard is bundled",
        )


def main() -> None:
    characters = json.loads((ROOT / "data" / "characters.json").read_text(encoding="utf-8"))
    entries = characters["characters"]
    check(len(entries) == 3000, "character database contains exactly the top 3,000 characters")
    check(
        sorted(entry["rank"] for entry in entries) == list(range(1, 3001)),
        "MOE frequency ranks are unique, contiguous, and complete",
    )
    check(
        [entry["learningRank"] for entry in entries] == list(range(1, 3001)),
        "beginner learning ranks are unique and contiguous",
    )
    check(
        len({entry["traditional"] for entry in entries}) == 3000
        and all(len(entry["traditional"]) == 1 for entry in entries),
        "every character record is one unique character, never a word",
    )
    check(all(entry["pinyin"] and entry["english"] for entry in entries), "every character has pinyin and English")
    check(
        all(re.search(r"[\u0900-\u097f]", entry["hindi"]) for entry in entries),
        "every character has a Devanagari Hindi meaning",
    )
    check(all(entry["examples"] for entry in entries), "every character detail has an example word or expression")
    check(
        [level["limit"] for level in characters["levels"]] == [1000, 2000, 3000],
        "character learning levels use the requested 1,000/2,000/3,000 limits",
    )
    level_sets = [
        {entry["traditional"] for entry in entries[:limit]}
        for limit in (1000, 2000, 3000)
    ]
    check(
        [len(values) for values in level_sets] == [1000, 2000, 3000]
        and level_sets[0] < level_sets[1] < level_sets[2],
        "character levels contain exact, unique, strictly cumulative sets",
    )
    check(
        characters["meta"]["audit"]["duplicateCharacters"] == 0
        and characters["meta"]["audit"]["missingCharacters"] == 0,
        "generated character audit reports no duplicates or missing source characters",
    )

    cccc = json.loads((ROOT / "data" / "tocfl-cccc.json").read_text(encoding="utf-8"))
    check(cccc["meta"]["wordCount"] == 1197, "CCCC extraction contains all 1,197 workbook rows")
    check(
        [level["wordCount"] for level in cccc["levels"]] == [464, 377, 356],
        "CCCC level counts match all three workbook tabs",
    )
    check(
        len({(word["sourceSheet"], word["sourceRow"]) for word in cccc["words"]}) == 1197,
        "CCCC output retains every source row exactly once",
    )
    check(
        all(word["category"] and word["subcategory"] and word["categoryBasis"] for word in cccc["words"]),
        "CCCC words retain semantic and source categories",
    )
    check(all(word["english"] and word["hindi"] for word in cccc["words"]), "every CCCC word has English and Hindi")
    check(all(re.search(r"[\u0900-\u097f]", word["hindi"]) for word in cccc["words"]), "every CCCC Hindi meaning uses Devanagari")
    tocfl = json.loads((ROOT / "data" / "tocfl-8000.json").read_text(encoding="utf-8"))
    check(tocfl["meta"]["wordCount"] == 7517, "TOCFL extraction contains all 7,517 workbook rows")
    check(
        [level["wordCount"] for level in tocfl["levels"]] == [160, 234, 347, 485, 1173, 2342, 2776],
        "TOCFL counts match all seven official level tabs",
    )
    check(
        len({(word["sourceSheet"], word["sourceRow"]) for word in tocfl["words"]}) == 7517,
        "TOCFL output retains every source row exactly once",
    )
    check(all(word["category"] and word["categoryBasis"] for word in tocfl["words"]), "every TOCFL word has a semantic category")
    check(tocfl["meta"]["missingEnglish"] == 0, "every TOCFL word has an English meaning")
    check(tocfl["meta"]["missingHindi"] == 0, "every TOCFL word has a Hindi meaning")
    check(all(re.search(r"[\u0900-\u097f]", word["hindi"]) for word in tocfl["words"]), "every TOCFL Hindi meaning uses Devanagari")
    requested_taxonomy = tocfl["meta"]["taxonomy"]
    check(requested_taxonomy["count"] == 48, "TOCFL/CCCC taxonomy contains exactly 48 categories")
    labels = [item["label"] for item in requested_taxonomy["categories"]]
    check(len(labels) == len(set(labels)) == 48, "TOCFL/CCCC category labels are unique")
    check(
        cccc["meta"]["taxonomy"] == requested_taxonomy,
        "TOCFL and CCCC use the same ordered category taxonomy",
    )
    allowed_categories = set(labels)
    combined_source_words = tocfl["words"] + cccc["words"]
    check(
        all(
            word["category"] in allowed_categories
            and all(item in allowed_categories for item in word.get("secondaryCategories", []))
            for word in combined_source_words
        ),
        "every TOCFL and CCCC row uses only the requested category system",
    )
    check(
        {word["category"] for word in combined_source_words} == allowed_categories,
        "all 48 requested categories contain source vocabulary",
    )
    check(
        all(word["id"].startswith("tocfl8k-") for word in tocfl["words"])
        and all(word["id"].startswith("cccc-") for word in cccc["words"]),
        "Categories data contains only TOCFL and CCCC source rows",
    )
    for name in SOURCE_PAGES:
        audit_source(PAGES / name)
    for name in ROOT_PAGES:
        audit_generated(ROOT / name)
    for name in MOBILE_PAGES:
        audit_generated(ROOT / "mobile" / name)
    for name in REMOVED_PAGES:
        check(not (PAGES / name).exists(), f"retired source page is gone: pages/{name}")
    for name in REMOVED_PAGES[1:]:
        check(not (ROOT / name).exists(), f"retired desktop page is gone: {name}")
        check(not (ROOT / "mobile" / name).exists(), f"retired mobile page is gone: mobile/{name}")
    check(not (ROOT / "mobile" / "words.html").exists(), "retired mobile words table is gone")
    for name in ("js/app.js", "js/pronunciation.js", "data/vocabulary.js", "data/nhm-1000-common.js"):
        check(not (ROOT / name).exists(), f"retired script is gone: {name}")
    for label, page in (("desktop", ROOT / "index.html"), ("mobile", ROOT / "mobile" / "index.html")):
        html = page.read_text(encoding="utf-8")
        check("window.__UNIFIED_APP__" in html, f"{label} entry page is the unified app")
        check(
            "word-table" not in html and 'id="study-panel"' not in html,
            f"{label} entry page ships no legacy table or study view",
        )

    desktop_unified = (ROOT / "chinese.html").read_text(encoding="utf-8")
    mobile_unified = (ROOT / "mobile" / "index.html").read_text(encoding="utf-8")
    check("window.__VOCAB_MASTER__" in desktop_unified, "desktop unified app includes canonical categories")
    check("window.__VOCAB_MASTER__" in mobile_unified, "mobile default page is the unified category app")
    for label, html in (("desktop", desktop_unified), ("mobile", mobile_unified)):
        # A page can mention a dataset and still ship without it, and the all-in-one
        # file is the only one a phone can open from a content:// share.
        for global_name in (
            "__VOCAB_MASTER__", "__TOCFL_8000__", "__TOCFL_CCCC__", "__CHARACTERS__",
        ):
            check(
                re.search(rf"window\.{global_name}\s*=\s*\{{", html) is not None,
                f"{label} unified app embeds the {global_name} dataset",
            )
    for label, html in (("desktop", desktop_unified), ("mobile", mobile_unified)):
        check('data-content-tab="sentences"' in html, f"{label} unified app includes sentence browsing")
        check(
            all(f'data-hsk-tab="{level}"' in html for level in range(1, 7)),
            f"{label} unified app includes HSK 1–6 content tabs",
        )
        check("script-block--traditional" in html, f"{label} unified app includes Traditional display")
        check("script-block--simplified" in html, f"{label} unified app includes Simplified display")
        check('id="app-view-categories"' in html, f"{label} unified app includes Categories view")
        check("window.CategoriesUI" in html, f"{label} unified app includes Categories controller")
        check("window.TocflStore" in html, f"{label} unified app includes shared TOCFL/CCCC index")
    print(
        f"Verified {len(SOURCE_PAGES)} source pages, {len(ROOT_PAGES)} desktop outputs, "
        f"and {len(MOBILE_PAGES)} mobile outputs."
    )


if __name__ == "__main__":
    main()
