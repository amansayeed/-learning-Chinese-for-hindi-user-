# -*- coding: utf-8 -*-
"""Build data/nhm-1000-common.json from Ni Hao Ma markdown (all ~1000 entries)."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from deep_translator import GoogleTranslator
from opencc import OpenCC

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "data" / "source" / "1000-common-chinese-words.md"
OUT_JSON = ROOT / "data" / "nhm-1000-common.json"
OUT_JS = ROOT / "data" / "nhm-1000-common.js"

LESSON_SIZE = 50
HI_DELAY = 0.1

s2t = OpenCC("s2t")
translator = GoogleTranslator(source="en", target="hi")


def parse_table_rows(text: str) -> list[tuple[int, str, str, str]]:
    seen: set[int] = set()
    out: list[tuple[int, str, str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p]
        if len(parts) < 4:
            continue
        if parts[0].startswith("---") or parts[0].lower() == "no.":
            continue
        try:
            num = int(parts[0])
        except ValueError:
            continue
        ch, py, meaning = parts[1], parts[2], parts[3]
        if num in seen:
            continue
        seen.add(num)
        out.append((num, ch, py, meaning))
    out.sort(key=lambda x: x[0])
    return out


def to_hindi(english: str, cache: dict[str, str]) -> str:
    key = english.strip()
    if not key:
        return ""
    if key in cache:
        return cache[key]
    try:
        hi = translator.translate(key)
        time.sleep(HI_DELAY)
        cache[key] = hi
        return hi
    except Exception as e:
        print(f"translate fail: {e!r} :: {key[:50]}", file=sys.stderr)
        cache[key] = ""
        return ""


def split_lessons(words: list[dict], prefix: str) -> list[dict]:
    lessons = []
    for i in range(0, len(words), LESSON_SIZE):
        chunk = words[i : i + LESSON_SIZE]
        n = len(lessons) + 1
        lessons.append(
            {
                "id": f"{prefix}-{n:02d}",
                "title": f"Lesson {n}",
                "subtitle": f"Words {i + 1}–{i + len(chunk)}",
                "words": chunk,
            }
        )
    return lessons


def main() -> None:
    if not MD.exists():
        print(f"Missing {MD}", file=sys.stderr)
        sys.exit(1)

    text = MD.read_text(encoding="utf-8")
    rows = parse_table_rows(text)
    print(f"Parsed {len(rows)} unique numbered rows", file=sys.stderr)

    hi_cache: dict[str, str] = {}
    words: list[dict] = []
    for i, (num, simp, py, en) in enumerate(rows, start=1):
        if i % 100 == 0:
            print(f"  translating {i}/{len(rows)}…", file=sys.stderr)
        simp = re.sub(r"\s+", " ", simp).strip()
        trad = s2t.convert(simp)
        hindi = to_hindi(en, hi_cache)
        words.append(
            {
                "traditional": trad,
                "simplified": simp,
                "pinyin": py,
                "english": en,
                "hindi": hindi,
                "audioUrl": None,
                "sourceNo": num,
            }
        )

    lessons = split_lessons(words, "nhm")
    payload = {
        "meta": {
            "title": "Ni Hao Ma — 1000 Common Chinese Words",
            "sourceUrl": "https://nihaoma-mandarin.com/pedagogy-corner/1000-common-chinese-words/",
            "hindiNote": "Hindi glosses via machine translation from English",
            "audioNote": "Click Chinese for pronunciation (zh-TW)",
        },
        "levels": [
            {
                "id": "nhm-full",
                "code": "NHM1000",
                "label": "1000 common words (full list)",
                "wordCount": len(words),
                "lessons": lessons,
            }
        ],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_JS.write_text(
        "window.__VOCAB_NHM__ = " + json.dumps(payload, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(words)} words, {len(lessons)} lessons -> {OUT_JSON} and {OUT_JS}")


if __name__ == "__main__":
    main()
