# -*- coding: utf-8 -*-
"""Patch embedded window.__VOCAB__ in HTML files from data/vocabulary.js."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
js = (ROOT / "data" / "vocabulary.js").read_text(encoding="utf-8")
# ensure trailing newline
if not js.endswith("\n"):
    js += "\n"

pat = re.compile(r"window\.__VOCAB__\s*=\s*\{.*?\};\s*", re.S)

targets = [
    ROOT / "index.html",
    ROOT / "mobile" / "words.html",
]

for p in targets:
    if not p.exists():
        print("skip missing", p)
        continue
    text = p.read_text(encoding="utf-8")
    n = len(pat.findall(text))
    if n == 0:
        print("no embed", p)
        continue
    new, k = pat.subn(js, text, count=1)
    if k != 1:
        print("unexpected replace count", k, p)
        continue
    p.write_text(new, encoding="utf-8")
    print("updated", p.name, "matches_found", n)
