# -*- coding: utf-8 -*-
"""Audit every source and generated desktop/mobile HTML page."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "pages"

SOURCE_PAGES = [
    "app.html", "index.html", "pronunciation.html", "tones.html",
    "hsk.html", "hsk2.html", "hsk3.html", "hsk4.html", "hsk5.html", "hsk6.html",
]
ROOT_PAGES = [
    "START.html", "chinese.html", "index.html", "pronunciation.html", "tones.html",
    "hsk.html", "hsk2.html", "hsk3.html", "hsk4.html", "hsk5.html", "hsk6.html",
]
MOBILE_PAGES = [
    "START.html", "index.html", "chinese.html", "words.html",
    "pronunciation.html", "tones.html", "hsk.html", "hsk2.html", "hsk3.html",
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
        "#categories" in html or "chinese.html#categories" in html,
        f"{path.name}: category navigation is available",
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
    for reference in local_refs(html, "href"):
        clean = reference.split("#", 1)[0].split("?", 1)[0]
        if not clean or not clean.endswith(".html"):
            continue
        target = (path.parent / clean).resolve()
        check(target.is_file(), f"{path.relative_to(ROOT)}: link target exists {clean}")
    if path.name not in {"START.html"}:
        check(
            "#categories" in html or "chinese.html#categories" in html,
            f"{path.relative_to(ROOT)}: category navigation is available",
        )
        check(
            "window.__CHINESE_STORAGE_PATCHED__" in html,
            f"{path.relative_to(ROOT)}: safe storage is bundled",
        )


def main() -> None:
    for name in SOURCE_PAGES:
        audit_source(PAGES / name)
    for name in ROOT_PAGES:
        audit_generated(ROOT / name)
    for name in MOBILE_PAGES:
        audit_generated(ROOT / "mobile" / name)

    check(
        "window.__VOCAB_MASTER__" in (ROOT / "chinese.html").read_text(encoding="utf-8"),
        "desktop unified app includes canonical categories",
    )
    check(
        "window.__VOCAB_MASTER__" in (ROOT / "mobile" / "index.html").read_text(encoding="utf-8"),
        "mobile default page is the unified category app",
    )
    print(
        f"Verified {len(SOURCE_PAGES)} source pages, {len(ROOT_PAGES)} desktop outputs, "
        f"and {len(MOBILE_PAGES)} mobile outputs."
    )


if __name__ == "__main__":
    main()
