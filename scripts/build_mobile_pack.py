# -*- coding: utf-8 -*-
"""Build every standalone desktop/mobile page when Node.js is unavailable."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "pages"
MOBILE = ROOT / "mobile"
CSS = (ROOT / "css" / "styles.css").read_text(encoding="utf-8")

PAGE_CONFIG = [
    ("index.html", ["index.html", "mobile/words.html"], [
        "js/offline.js", "data/vocabulary.js", "data/nhm-1000-common.js",
        "js/sidebar.js", "js/app.js",
    ]),
    ("pronunciation.html", ["pronunciation.html", "mobile/pronunciation.html"], [
        "js/offline.js", "data/vocabulary.js", "data/nhm-1000-common.js",
        "js/sidebar.js", "js/pronunciation.js",
    ]),
    *[
        (
            "hsk.html" if level == 1 else f"hsk{level}.html",
            [
                "hsk.html" if level == 1 else f"hsk{level}.html",
                f"mobile/{'hsk' if level == 1 else f'hsk{level}'}.html",
            ],
            [
                "js/offline.js", f"data/hsk-{level}.js",
                "js/sidebar.js", "js/app.js",
            ],
        )
        for level in range(1, 7)
    ],
    ("tones.html", ["tones.html", "mobile/tones.html"], [
        "js/offline.js", "data/tone-page.data.js", "js/sidebar.js", "js/tones.js",
    ]),
]


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(f"Missing dependency: {relative}")
    return path.read_text(encoding="utf-8")


def escape_script(value: str) -> str:
    return re.sub(r"</script", r"<\\/script", value, flags=re.IGNORECASE)


def strip_assets(html: str) -> str:
    html = re.sub(r'<link[^>]*fonts\.googleapis[^>]*>\s*', "", html, flags=re.I)
    html = re.sub(r'<link[^>]*fonts\.gstatic[^>]*>\s*', "", html, flags=re.I)
    html = re.sub(r'<link[^>]*rel=["\']stylesheet["\'][^>]*>\s*', "", html, flags=re.I)
    html = re.sub(
        r'<script[^>]*\ssrc=["\'][^"\']+["\'][^>]*>\s*</script>\s*',
        "",
        html,
        flags=re.I,
    )
    html = re.sub(
        r'<script>\s*document\.addEventListener\("DOMContentLoaded"[\s\S]*?</script>\s*',
        "",
        html,
        flags=re.I,
    )
    return re.sub(
        r'<script>\s*\(function \(\) \{\s*var loc = window\.location;'
        r'[\s\S]*?window\.__OFFLINE_FILE__ = false;\s*\}\)\(\);\s*</script>\s*',
        "",
        html,
        count=1,
        flags=re.I,
    )


def fix_nav(html: str, mobile: bool) -> str:
    html = re.sub(r'href="\./([^"]+\.html(?:#[^"]*)?)"', r'href="\1"', html)
    if mobile:
        html = html.replace('href="index.html"', 'href="words.html"')
    return html


def bundle(source: str, outputs: list[str], scripts: list[str]) -> None:
    html = strip_assets((PAGES / source).read_text(encoding="utf-8"))
    script_files = ["js/storage-safe.js", *scripts]
    blocks = "\n".join(
        f"<script>\n{escape_script(read(relative))}\n</script>"
        for relative in script_files
    )
    head = (
        f"<style>\n{CSS}\n</style>\n"
        "<script>window.__OFFLINE_FILE__=true;window.__MOBILE_PACK__=true;</script>"
    )
    boot = (
        '<script>(function(){var v=(window.__VOCAB__&&window.__VOCAB__.levels)||'
        '(window.__VOCAB_NHM__&&window.__VOCAB_NHM__.levels)||'
        '(window.__VOCAB_HSK1__&&window.__VOCAB_HSK1__.levels)||'
        '(window.__VOCAB_HSK2__&&window.__VOCAB_HSK2__.levels)||'
        '(window.__VOCAB_HSK3__&&window.__VOCAB_HSK3__.levels)||'
        '(window.__VOCAB_HSK4__&&window.__VOCAB_HSK4__.levels)||'
        '(window.__VOCAB_HSK5__&&window.__VOCAB_HSK5__.levels)||'
        '(window.__VOCAB_HSK6__&&window.__VOCAB_HSK6__.levels);'
        'var t=window.__TONE_PAGE_DATA__&&window.__TONE_PAGE_DATA__.quartets;'
        'if(v||t)return;var m=document.querySelector(".layout-main");if(!m)return;'
        'var b=document.createElement("div");b.setAttribute("role","alert");'
        'b.style.cssText="margin:0 0 1rem;padding:.75rem;background:#991b1b;color:#fff;'
        'border-radius:8px;font-size:.9rem;font-weight:600";'
        'b.textContent="Word data did not load. Download this HTML again from git '
        '(large file, not a few KB).";m.insertBefore(b,m.firstChild);})();</script>'
    )
    html = html.replace("</head>", f"{head}\n</head>", 1)
    html = html.replace("</body>", f"{blocks}\n{boot}\n</body>", 1)
    for relative in outputs:
        output = ROOT / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output_html = fix_nav(html, relative.startswith("mobile/"))
        output.write_text(output_html, encoding="utf-8")
        print(f"Wrote {relative} ({output.stat().st_size // 1024} KB)")


def write_launchers() -> None:
    links = [
        ("chinese.html", "Open all-in-one app (recommended for phone)"),
        ("words.html", "Words · table & study"),
        ("hsk.html", "HSK 1 · 500 words"), ("hsk2.html", "HSK 2 · 772 words"),
        ("hsk3.html", "HSK 3 · 973 words"), ("hsk4.html", "HSK 4 · 1000 words"),
        ("hsk5.html", "HSK 5 · 1071 words"), ("hsk6.html", "HSK 6 · 1140 words"),
        ("pronunciation.html", "Pronunciation"), ("tones.html", "Four tones"),
    ]
    body = "\n".join(
        '<a href="{}"{}>{}</a>'.format(
            href, ' class="primary"' if index == 0 else "", label
        )
        for index, (href, label) in enumerate(links)
    )
    template = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>Chinese study</title><style>
body{{font-family:system-ui,sans-serif;margin:0;padding:max(1rem,env(safe-area-inset-top)) max(1rem,env(safe-area-inset-right)) max(1rem,env(safe-area-inset-bottom)) max(1rem,env(safe-area-inset-left));background:#0f172a;color:#e2e8f0;line-height:1.5}}
h1{{font-size:1.25rem}}p{{color:#94a3b8;font-size:.9rem}}
a{{display:block;padding:1rem;margin:.5rem 0;background:#1e293b;border:1px solid #334155;border-radius:12px;color:#5eead4;text-decoration:none;font-weight:700}}
a.primary{{background:#134e4a;border-color:#0d9488}}
</style></head><body><h1>臺灣華語 · Chinese study</h1>
<p><strong>On phone:</strong> open the all-in-one app. Separate pages require the complete folder.</p>
{body}</body></html>"""
    MOBILE.mkdir(parents=True, exist_ok=True)
    (MOBILE / "START.html").write_text(template, encoding="utf-8")
    (ROOT / "START.html").write_text(
        template.replace('href="words.html"', 'href="index.html"'),
        encoding="utf-8",
    )


def main() -> None:
    MOBILE.mkdir(parents=True, exist_ok=True)
    for source, outputs, scripts in PAGE_CONFIG:
        bundle(source, outputs, scripts)
    write_launchers()


if __name__ == "__main__":
    main()
