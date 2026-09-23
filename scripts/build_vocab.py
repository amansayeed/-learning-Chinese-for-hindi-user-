# -*- coding: utf-8 -*-
"""Build data/vocabulary.json from TOCFL xlsx (English + Hindi + simplified)."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
from opencc import OpenCC
from deep_translator import GoogleTranslator

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "data" / "source" / "TOCFL_14425_word_list.xlsx"
# JSON only: this list feeds the canonical master build, never a browser page.
OUT = ROOT / "data" / "vocabulary.json"

LESSON_SIZE = 50
HI_DELAY = 0.12

t2s = OpenCC("t2s")
translator = GoogleTranslator(source="en", target="hi")


def clean_english(s: str) -> str:
    if not isinstance(s, str) or not s.strip():
        return ""
    s = s.replace("\n", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def first_gloss(english: str) -> str:
    """Use first comma-separated gloss for shorter Hindi translation."""
    if not english:
        return ""
    # Prefer first segment before comma if very long
    parts = [p.strip() for p in english.split(",")]
    if len(english) > 120 and parts:
        return parts[0]
    return english


def to_hindi(english: str, cache: dict[str, str]) -> str:
    key = english.strip()
    if not key:
        return ""
    if key in cache:
        return cache[key]
    try:
        g = first_gloss(key)
        hi = translator.translate(g)
        time.sleep(HI_DELAY)
        cache[key] = hi
        return hi
    except Exception as e:
        print(f"translate fail: {e!r} :: {key[:60]}", file=sys.stderr)
        cache[key] = ""
        return ""


def level_rows(df: pd.DataFrame, levels: list[str]) -> pd.DataFrame:
    sub = df[df["級別"].isin(levels)].copy()
    sub = sub.sort_values(by=["序號"], kind="stable")
    return sub


def split_lessons(words: list[dict], prefix: str) -> list[dict]:
    lessons = []
    n = LESSON_SIZE
    for i in range(0, len(words), n):
        chunk = words[i : i + n]
        num = len(lessons) + 1
        lessons.append(
            {
                "id": f"{prefix}-{num:02d}",
                "title": f"Lesson {num}",
                "subtitle": f"Words {i + 1}–{i + len(chunk)}",
                "words": chunk,
            }
        )
    return lessons


def main() -> None:
    if not XLSX.exists():
        print(f"Missing {XLSX}; download TOCFL_14425_word_list.xlsx first.", file=sys.stderr)
        sys.exit(1)

    df = pd.read_excel(XLSX, "out")
    hi_cache: dict[str, str] = {}

    levels_spec = [
        {
            "id": "1",
            "code": "A1",
            "label": "Level 1 (A1)",
            "tocfl_levels": ["第1級", "第1*級"],
        },
        {
            "id": "2",
            "code": "A2",
            "label": "Level 2 (A2)",
            "tocfl_levels": ["第2級", "第2*級"],
        },
    ]

    out_levels = []
    for spec in levels_spec:
        rows = level_rows(df, spec["tocfl_levels"])
        words: list[dict] = []
        for _, r in rows.iterrows():
            trad = str(r["詞語"]).strip()
            py = str(r["參考漢語拼音"]).strip() if pd.notna(r["參考漢語拼音"]) else ""
            en = clean_english(r["definition"])
            simp = t2s.convert(trad)
            hi = to_hindi(en, hi_cache)
            words.append(
                {
                    "traditional": trad,
                    "simplified": simp,
                    "pinyin": py,
                    "english": en,
                    "hindi": hi,
                    "audioUrl": None,
                }
            )
        lessons = split_lessons(words, f"l{spec['id']}")
        out_levels.append(
            {
                "id": spec["id"],
                "code": spec["code"],
                "label": spec["label"],
                "wordCount": len(words),
                "lessons": lessons,
            }
        )
        print(f"{spec['label']}: {len(words)} words, {len(lessons)} lessons")

    payload = {
        "meta": {
            "title": "TOCFL Vocabulary (Hindi + English)",
            "source": "TOCFL official list via nutchanonj/TOCFL_14425_vocab_list; Hindi via Google Translate",
            "audioNote": "Click Traditional: Web Speech (zh-TW) or optional audioUrl",
        },
        "levels": out_levels,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
