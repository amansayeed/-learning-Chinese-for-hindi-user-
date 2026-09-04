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
BOTTOM_SNIPPET = (
    (PAGES / "_bottom-nav.snippet.html").read_text(encoding="utf-8").rstrip() + "\n"
)
PAT = re.compile(
    r'    <nav class="sidebar-nav" aria-label="Pages">.*?</nav>\n',
    re.DOTALL,
)
BOTTOM_PAT = re.compile(
    r'  <nav class="bottom-nav" aria-label="Primary navigation">.*?</nav>\n',
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
            new = text
        if path.name != "app.html":
            new, bottom_n = BOTTOM_PAT.subn(BOTTOM_SNIPPET, new, count=1)
            if bottom_n == 0:
                new = new.replace("</body>", BOTTOM_SNIPPET + "</body>", 1)
        path.write_text(new, encoding="utf-8")
        print(f"updated {path.name}")


if __name__ == "__main__":
    main()
