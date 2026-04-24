# -*- coding: utf-8 -*-
"""Resplit vocabulary JSON/JS into fixed lesson sizes (no translation)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON_SIZE = 50


def split_lessons(words: list[dict], prefix: str, subtitles: bool) -> list[dict]:
    lessons = []
    for i in range(0, len(words), LESSON_SIZE):
        chunk = words[i : i + LESSON_SIZE]
        num = len(lessons) + 1
        row: dict = {
            "id": f"{prefix}-{num:02d}",
            "title": f"Lesson {num}",
            "words": chunk,
        }
        if subtitles:
            row["subtitle"] = f"Words {i + 1}–{i + len(chunk)}"
        lessons.append(row)
    return lessons


def resplit_file(json_path: Path, js_path: Path, global_name: str, subtitle: bool) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    for lvl in data["levels"]:
        words: list[dict] = []
        for les in lvl["lessons"]:
            words.extend(les["words"])
        prefix = "nhm" if lvl.get("code") == "NHM1000" else f"l{lvl['id']}"
        lvl["lessons"] = split_lessons(words, prefix, subtitle)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    js_path.write_text(
        f"window.{global_name} = " + json.dumps(data, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    nless = sum(len(lvl["lessons"]) for lvl in data["levels"])
    print(f"{json_path.name}: {nless} lessons total", file=sys.stderr)


def main() -> None:
    resplit_file(
        ROOT / "data" / "vocabulary.json",
        ROOT / "data" / "vocabulary.js",
        "__VOCAB__",
        True,
    )
    resplit_file(
        ROOT / "data" / "nhm-1000-common.json",
        ROOT / "data" / "nhm-1000-common.js",
        "__VOCAB_NHM__",
        True,
    )


if __name__ == "__main__":
    main()
