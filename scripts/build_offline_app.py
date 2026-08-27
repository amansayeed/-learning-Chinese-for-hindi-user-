# -*- coding: utf-8 -*-
"""Build the unified single-file app when Node.js is unavailable."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / "mobile"

SCRIPTS = [
    "js/offline.js",
    "data/vocabulary.js",
    "data/nhm-1000-common.js",
    "data/hsk-1.js",
    "data/hsk-2.js",
    "data/hsk-3.js",
    "data/hsk-4.js",
    "data/hsk-5.js",
    "data/hsk-6.js",
    "data/vocabulary-master.js",
    "data/tone-page.data.js",
    "js/sidebar.js",
    "js/learning-state.js",
    "js/vocab-store.js",
    "js/vocabulary-ui.js",
    "js/app.js",
    "js/pronunciation.js",
    "js/tones.js",
    "js/app-router.js",
]


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(f"Missing dependency: {relative}")
    return path.read_text(encoding="utf-8")


def escape_script(value: str) -> str:
    return re.sub(r"</script", r"<\\/script", value, flags=re.IGNORECASE)


def strip_external_assets(html: str) -> str:
    html = re.sub(r'<link[^>]*fonts\.googleapis[^>]*>\s*', "", html, flags=re.IGNORECASE)
    html = re.sub(r'<link[^>]*fonts\.gstatic[^>]*>\s*', "", html, flags=re.IGNORECASE)
    html = re.sub(
        r'<link[^>]*rel=["\']stylesheet["\'][^>]*>\s*',
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'<script[^>]*\ssrc=["\'][^"\']+["\'][^>]*>\s*</script>\s*',
        "",
        html,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"<script>\s*window\.__UNIFIED_APP__\s*=\s*true;\s*</script>\s*",
        "",
        html,
        flags=re.IGNORECASE,
    )


def main() -> None:
    html = strip_external_assets(read("pages/app.html"))
    storage = escape_script(read("js/storage-safe.js"))
    css = read("css/styles.css")
    blocks = "\n".join(
        f"<script>\n{escape_script(read(relative))}\n</script>" for relative in SCRIPTS
    )
    html = html.replace("<head>", f"<head>\n<script>\n{storage}\n</script>\n", 1)
    head = (
        f"<style>\n{css}\n</style>\n"
        "<script>window.__OFFLINE_FILE__=true;"
        "window.__MOBILE_PACK__=true;window.__UNIFIED_APP__=true;</script>"
    )
    html = html.replace("</head>", f"{head}\n</head>", 1)
    html = html.replace("</body>", f"{blocks}\n</body>", 1)

    MOBILE.mkdir(parents=True, exist_ok=True)
    for relative in ("chinese.html", "mobile/chinese.html", "mobile/index.html"):
        output = ROOT / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html, encoding="utf-8")
        print(f"Wrote {relative} ({output.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
