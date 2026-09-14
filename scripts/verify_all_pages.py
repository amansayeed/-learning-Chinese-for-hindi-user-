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
    "app.html", "index.html", "tocfl.html", "pronunciation.html", "tones.html",
    "hsk.html", "hsk2.html", "hsk3.html", "hsk4.html", "hsk5.html", "hsk6.html",
]
ROOT_PAGES = [
    "START.html", "chinese.html", "index.html", "tocfl.html", "pronunciation.html", "tones.html",
    "hsk.html", "hsk2.html", "hsk3.html", "hsk4.html", "hsk5.html", "hsk6.html",
]
MOBILE_PAGES = [
    "START.html", "index.html", "chinese.html", "words.html",
    "tocfl.html", "pronunciation.html", "tones.html", "hsk.html", "hsk2.html", "hsk3.html",
    "hsk4.html", "hsk5.html", "hsk6.html",
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
    if path.name not in {"START.html"}:
        check(
            "#categories" in html or "chinese.html#categories" in html or "#browse" in html,
            f"{path.relative_to(ROOT)}: browse navigation is available",
        )
        check(
            "window.__CHINESE_STORAGE_PATCHED__" in html,
            f"{path.relative_to(ROOT)}: safe storage is bundled",
        )


def main() -> None:
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
    for name in SOURCE_PAGES:
        audit_source(PAGES / name)
    for name in ROOT_PAGES:
        audit_generated(ROOT / name)
    for name in MOBILE_PAGES:
        audit_generated(ROOT / "mobile" / name)

    desktop_unified = (ROOT / "chinese.html").read_text(encoding="utf-8")
    mobile_unified = (ROOT / "mobile" / "index.html").read_text(encoding="utf-8")
    check("window.__VOCAB_MASTER__" in desktop_unified, "desktop unified app includes canonical categories")
    check("window.__VOCAB_MASTER__" in mobile_unified, "mobile default page is the unified category app")
    for label, html in (("desktop", desktop_unified), ("mobile", mobile_unified)):
        check('data-content-tab="sentences"' in html, f"{label} unified app includes sentence browsing")
        check(
            all(f'data-hsk-tab="{level}"' in html for level in range(1, 7)),
            f"{label} unified app includes HSK 1–6 content tabs",
        )
        check("script-block--traditional" in html, f"{label} unified app includes Traditional display")
        check("script-block--simplified" in html, f"{label} unified app includes Simplified display")
    print(
        f"Verified {len(SOURCE_PAGES)} source pages, {len(ROOT_PAGES)} desktop outputs, "
        f"and {len(MOBILE_PAGES)} mobile outputs."
    )


if __name__ == "__main__":
    main()
