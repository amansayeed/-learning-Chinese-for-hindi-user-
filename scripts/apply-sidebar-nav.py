#!/usr/bin/env python3
"""Replace sidebar nav in all pages/*.html with shared HSK dropdown snippet."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "pages"
SNIPPET = (PAGES / "_sidebar-nav.snippet.html").read_text(encoding="utf-8").rstrip() + "\n"
APP_SNIPPET = (
    (PAGES / "_sidebar-nav-app.snippet.html").read_text(encoding="utf-8").rstrip() + "\n"
)
PAT = re.compile(
    r'    <nav class="sidebar-nav" aria-label="Pages">.*?</nav>\n',
    re.DOTALL,
)


def main() -> None:
    for path in sorted(PAGES.glob("*.html")):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")
        snippet = APP_SNIPPET if path.name == "app.html" else SNIPPET
        new, n = PAT.subn(snippet, text, count=1)
        if n != 1:
            print(f"skip {path.name} (matches={n})")
            continue
        path.write_text(new, encoding="utf-8")
        print(f"updated {path.name}")


if __name__ == "__main__":
    main()
