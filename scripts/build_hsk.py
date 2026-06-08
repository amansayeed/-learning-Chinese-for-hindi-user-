# -*- coding: utf-8 -*-
"""Build data/hsk-N.json from New HSK word lists (txt source)."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from deep_translator import GoogleTranslator
from opencc import OpenCC

ROOT = Path(__file__).resolve().parents[1]
TXT_DIR = ROOT / "data" / "new-hsk-csv-master" / "new-hsk-csv-master" / "data" / "txt"

LESSON_SIZE = 50
HI_DELAY = 0.08

s2t = OpenCC("s2t")
translator = GoogleTranslator(source="en", target="hi")

LINE_RE = re.compile(r"^(\d+)\[-\](.+)\[-\](.+)\[-\](.+)$")
ANNOT_RE = re.compile(r"（[^）]*）")

LEVELS = {
    1: {
        "global": "__VOCAB_HSK1__",
        "code": "HSK1",
        "label": "HSK Level 1",
        "title": "New HSK 1 — 500 words",
    },
    2: {
        "global": "__VOCAB_HSK2__",
        "code": "HSK2",
        "label": "HSK Level 2",
        "title": "New HSK 2 — 772 words",
    },
    3: {
        "global": "__VOCAB_HSK3__",
        "code": "HSK3",
        "label": "HSK Level 3",
        "title": "New HSK 3 — 973 words",
    },
    4: {
        "global": "__VOCAB_HSK4__",
        "code": "HSK4",
        "label": "HSK Level 4",
        "title": "New HSK 4 — 1000 words",
    },
    5: {
        "global": "__VOCAB_HSK5__",
        "code": "HSK5",
        "label": "HSK Level 5",
        "title": "New HSK 5 — 1071 words",
    },
    6: {
        "global": "__VOCAB_HSK6__",
        "code": "HSK6",
        "label": "HSK Level 6",
        "title": "New HSK 6 — 1140 words",
    },
}


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_hindi_lookup() -> tuple[dict[str, str], dict[str, str]]:
    by_simp: dict[str, str] = {}
    by_en: dict[str, str] = {}

    def ingest(payload: dict) -> None:
        for lvl in payload.get("levels", []):
            for les in lvl.get("lessons", []):
                for w in les.get("words", []):
                    simp = (w.get("simplified") or "").strip()
                    hi = (w.get("hindi") or "").strip()
                    en = (w.get("english") or "").strip()
                    if simp and hi and simp not in by_simp:
                        by_simp[simp] = hi
                    if en and hi:
                        key = en.lower()
                        if key not in by_en:
                            by_en[key] = hi

    ingest(load_json(ROOT / "data" / "nhm-1000-common.json"))
    ingest(load_json(ROOT / "data" / "vocabulary.json"))
    ingest(load_json(ROOT / "data" / "hsk-1.json"))
    ingest(load_json(ROOT / "data" / "hsk-2.json"))
    ingest(load_json(ROOT / "data" / "hsk-3.json"))
    ingest(load_json(ROOT / "data" / "hsk-4.json"))
    ingest(load_json(ROOT / "data" / "hsk-5.json"))
    return by_simp, by_en


def clean_chinese(raw: str) -> str:
    s = ANNOT_RE.sub("", raw or "")
    s = s.replace("｜", "/").replace("|", "/")
    s = re.sub(r"\s+", "", s)
    return s.strip()


def split_variants(raw: str) -> list[str]:
    s = clean_chinese(raw)
    parts = [p for p in s.split("/") if p]
    return parts or [s]


def to_traditional(parts: list[str]) -> str:
    return "/".join(s2t.convert(p) for p in parts)


def normalize_pinyin(raw: str) -> str:
    s = (raw or "").replace("｜", "/").replace("|", "/")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def lookup_hindi(
    parts: list[str],
    english: str,
    by_simp: dict[str, str],
    by_en: dict[str, str],
    cache: dict[str, str],
) -> str:
    for p in parts:
        if p in by_simp:
            return by_simp[p]
    key = english.strip().lower()
    if key in by_en:
        return by_en[key]
    if key in cache:
        return cache[key]
    if not english.strip():
        return ""
    try:
        hi = translator.translate(english.strip())
        time.sleep(HI_DELAY)
        cache[key] = hi
        return hi
    except Exception as e:
        print(f"translate fail: {e!r} :: {english[:60]}", file=sys.stderr)
        cache[key] = ""
        return ""


def parse_txt(text: str) -> list[tuple[int, str, str, str]]:
    rows: list[tuple[int, str, str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = LINE_RE.match(line)
        if not m:
            print(f"skip line: {line[:60]}", file=sys.stderr)
            continue
        num = int(m.group(1))
        rows.append((num, m.group(2), m.group(3), m.group(4)))
    rows.sort(key=lambda x: x[0])
    return rows


def split_lessons(words: list[dict], level: int) -> list[dict]:
    lessons = []
    for i in range(0, len(words), LESSON_SIZE):
        chunk = words[i : i + LESSON_SIZE]
        n = len(lessons) + 1
        lessons.append(
            {
                "id": f"hsk{level}-{n:02d}",
                "title": f"Lesson {n}",
                "subtitle": f"Words {i + 1}–{i + len(chunk)}",
                "words": chunk,
            }
        )
    return lessons


def build_level(level: int) -> None:
    if level not in LEVELS:
        print(f"Unsupported level: {level}", file=sys.stderr)
        sys.exit(1)

    cfg = LEVELS[level]
    txt_path = TXT_DIR / f"New-HSK-{level}-Word-List.txt"
    out_json = ROOT / "data" / f"hsk-{level}.json"
    out_js = ROOT / "data" / f"hsk-{level}.js"
    hi_cache_path = ROOT / "data" / f"hsk-{level}-hindi-cache.json"

    if not txt_path.is_file():
        print(f"Missing source: {txt_path}", file=sys.stderr)
        sys.exit(1)

    by_simp, by_en = build_hindi_lookup()
    hi_cache: dict[str, str] = {}
    if hi_cache_path.is_file():
        hi_cache = json.loads(hi_cache_path.read_text(encoding="utf-8"))

    rows = parse_txt(txt_path.read_text(encoding="utf-8"))
    words: list[dict] = []

    for num, zh_raw, py_raw, en in rows:
        parts = split_variants(zh_raw)
        simp = "/".join(parts)
        trad = to_traditional(parts)
        hindi = lookup_hindi(parts, en, by_simp, by_en, hi_cache)
        words.append(
            {
                "traditional": trad,
                "simplified": simp,
                "pinyin": normalize_pinyin(py_raw),
                "english": en.strip(),
                "hindi": hindi,
                "audioUrl": None,
                "sourceNo": num,
            }
        )

    hi_cache_path.write_text(json.dumps(hi_cache, ensure_ascii=False, indent=2), encoding="utf-8")

    rel_txt = f"data/new-hsk-csv-master/new-hsk-csv-master/data/txt/New-HSK-{level}-Word-List.txt"
    title = cfg["title"].replace("500", str(len(words))).replace("772", str(len(words)))
    payload = {
        "meta": {
            "title": title,
            "sourceUrl": "https://github.com/oetia/new-hsk-csv",
            "sourceFile": rel_txt,
            "hindiNote": "Hindi from existing word lists where matched; otherwise machine translation from English",
            "audioNote": "Tap Traditional for pronunciation (zh-TW)",
        },
        "levels": [
            {
                "id": f"hsk{level}",
                "code": cfg["code"],
                "label": cfg["label"],
                "wordCount": len(words),
                "lessons": split_lessons(words, level),
            }
        ],
    }

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out_js.write_text(
        f"window.{cfg['global']} = " + json.dumps(payload, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    missing_hi = sum(1 for w in words if not w["hindi"])
    print(f"Wrote {out_json.name}: {len(words)} words, {missing_hi} without Hindi", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build HSK vocabulary JSON/JS bundles")
    parser.add_argument(
        "levels",
        nargs="*",
        type=int,
        default=[1, 2],
        help="HSK levels to build (default: 1 2)",
    )
    args = parser.parse_args()
    for level in args.levels:
        build_level(level)


if __name__ == "__main__":
    main()
