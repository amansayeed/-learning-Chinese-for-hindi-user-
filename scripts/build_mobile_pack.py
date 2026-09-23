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
    ("pronunciation.html", ["pronunciation.html", "mobile/pronunciation.html"], [
        "js/offline.js", "data/tocfl-8000.js", "data/tocfl-cccc.js", "data/vocabulary-master.js",
        "js/category-taxonomy.js", "js/sidebar.js", "js/learning-state.js", "js/vocab-store.js",
        "js/tocfl-store.js", "js/vocabulary-ui.js", "js/tocfl-ui.js",
    ]),
    ("tocfl.html", ["tocfl.html", "mobile/tocfl.html"], [
        "js/offline.js", "data/tocfl-8000.js", "data/tocfl-cccc.js", "data/vocabulary-master.js",
        "js/category-taxonomy.js", "js/sidebar.js", "js/learning-state.js", "js/vocab-store.js",
        "js/tocfl-store.js", "js/vocabulary-ui.js", "js/tocfl-ui.js",
    ]),
    ("tocfl-8000.html", ["tocfl-8000.html", "mobile/tocfl-8000.html"], [
        "js/offline.js", "data/tocfl-8000.js", "data/tocfl-cccc.js", "data/vocabulary-master.js",
        "js/category-taxonomy.js", "js/sidebar.js", "js/learning-state.js", "js/vocab-store.js",
        "js/tocfl-store.js", "js/vocabulary-ui.js", "js/tocfl-ui.js",
    ]),
    ("categories.html", ["categories.html", "mobile/categories.html"], [
        "js/offline.js", "data/tocfl-8000.js", "data/tocfl-cccc.js", "data/vocabulary-master.js",
        "js/category-taxonomy.js", "js/sidebar.js", "js/learning-state.js", "js/vocab-store.js",
        "js/tocfl-store.js", "js/vocabulary-ui.js", "js/categories-ui.js",
    ]),
    ("characters.html", ["characters.html", "mobile/characters.html"], [
        "js/offline.js", "data/characters.js", "js/sidebar.js", "js/characters-ui.js",
    ]),
    ("character-diff.html", ["character-diff.html", "mobile/character-diff.html"], [
        "js/offline.js", "data/characters.js", "js/sidebar.js", "js/characters-ui.js",
    ]),
    ("tones.html", ["tones.html", "mobile/tones.html"], [
        "js/offline.js", "data/tone-page.data.js", "js/sidebar.js", "js/tones.js",
    ]),
]

UNIFIED_SCRIPTS = [
    "js/offline.js",
    "data/tocfl-8000.js",
    "data/tocfl-cccc.js",
    "data/vocabulary-master.js",
    "data/characters.js",
    "data/tone-page.data.js",
    "js/category-taxonomy.js",
    "js/sidebar.js",
    "js/learning-state.js",
    "js/vocab-store.js",
    "js/tocfl-store.js",
    "js/vocabulary-ui.js",
    "js/categories-ui.js",
    "js/tocfl-ui.js",
    "js/characters-ui.js",
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
    # A bundled page inlines every asset, so the <base> that this snippet installs
    # has nothing left to resolve and only breaks links on content:// documents.
    return re.sub(
        r"<script>\s*\(function \(\) \{\s*var loc = window\.location;"
        r"[\s\S]*?</script>\s*",
        "",
        html,
        count=1,
        flags=re.I,
    )


def fix_nav(html: str, mobile: bool) -> str:
    return re.sub(r'href="\./([^"]+\.html(?:#[^"]*)?)"', r'href="\1"', html)


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
        '<script>(function(){var v=(window.__VOCAB_MASTER__&&window.__VOCAB_MASTER__.words)||'
        '(window.__TOCFL_8000__&&window.__TOCFL_8000__.words)||'
        '(window.__TOCFL_CCCC__&&window.__TOCFL_CCCC__.words)||'
        '(window.__CHARACTERS__&&window.__CHARACTERS__.characters);'
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


def bundle_unified() -> None:
    html = strip_assets((PAGES / "app.html").read_text(encoding="utf-8"))
    html = re.sub(
        r"<script>\s*window\.__UNIFIED_APP__\s*=\s*true;\s*</script>\s*",
        "",
        html,
        flags=re.I,
    )
    blocks = "\n".join(
        f"<script>\n{escape_script(read(relative))}\n</script>"
        for relative in ["js/storage-safe.js", *UNIFIED_SCRIPTS]
    )
    head = (
        f"<style>\n{CSS}\n</style>\n"
        "<script>window.__OFFLINE_FILE__=true;window.__MOBILE_PACK__=true;"
        "window.__UNIFIED_APP__=true;</script>"
    )
    html = html.replace("</head>", f"{head}\n</head>", 1)
    html = html.replace("</body>", f"{blocks}\n</body>", 1)
    for relative in ("index.html", "chinese.html", "mobile/chinese.html", "mobile/index.html"):
        output = ROOT / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html, encoding="utf-8")
        print(f"Wrote {relative} ({output.stat().st_size // 1024} KB)")


def write_launchers() -> None:
    links = [
        ("chinese.html", "🚀", "Open all-in-one app", "Dashboard, categories, search, learn and progress"),
        ("chinese.html#browse", "📖", "Browse all words", "Search every word by level, topic and meaning"),
        ("chinese.html#hsk1", "🧩", "HSK levels 1–6", "Each band as one alphabetical word list"),
        ("pronunciation.html", "🗣️", "Pronunciation", "Practice Chinese sounds and clusters"),
        ("tocfl.html", "📘", "TOCFL + CCCC", "Browse all seven official vocabulary levels"),
        ("tocfl-8000.html", "📗", "Official TOCFL vocabulary", "TOCFL 8000, all words arranged by pinyin"),
        ("categories.html", "🗂️", "Categories", "Browse official TOCFL and CCCC words by topic"),
        ("characters.html", "字", "Chinese Characters", "Learn 1,000–3,000 characters by frequency"),
        ("character-diff.html", "繁", "Traditional and Simplified difference", "Characters from the 3,000 list that differ"),
        ("tones.html", "🎵", "Four tones", "Train Mandarin tone recognition"),
    ]
    body = "\n".join(
        '<a href="{}" class="card{}"><span class="icon" aria-hidden="true">{}</span>'
        "<strong>{}</strong><small>{}</small></a>".format(
            href, " primary" if index == 0 else "", icon, label, description
        )
        for index, (href, icon, label, description) in enumerate(links)
    )
    all_in_one = links[0][0]
    template = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>Taiwan Chinese Learning</title><style>
*{{box-sizing:border-box}}body{{font-family:"Segoe UI",system-ui,sans-serif;margin:0;min-height:100vh;padding:max(1rem,env(safe-area-inset-top)) max(1rem,env(safe-area-inset-right)) max(1rem,env(safe-area-inset-bottom)) max(1rem,env(safe-area-inset-left));background:linear-gradient(135deg,#667eea,#764ba2);color:#2d3748;line-height:1.5}}
.container{{width:min(1180px,100%);margin:auto}}.hero{{padding:clamp(2rem,7vw,5rem) 1.25rem;margin-bottom:1.5rem;border-radius:22px;background:rgba(255,255,255,.96);box-shadow:0 12px 42px rgba(25,28,48,.25);text-align:center}}
h1{{margin:0;font-size:clamp(2rem,7vw,4rem);line-height:1.08;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;background-clip:text;color:transparent}}.hero p{{color:#667085;font-size:clamp(1rem,2vw,1.25rem)}}
.stats{{display:flex;justify-content:center;gap:clamp(.6rem,3vw,2.5rem);flex-wrap:wrap;margin-top:2rem}}.stat{{min-width:120px;padding:.9rem 1.2rem;border-radius:14px;background:rgba(102,126,234,.1)}}.stat strong{{display:block;color:#667eea;font-size:1.7rem}}.stat span{{color:#667085;font-size:.82rem;font-weight:700}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1rem}}.card{{display:flex;min-height:180px;flex-direction:column;align-items:center;justify-content:center;gap:.5rem;padding:1.25rem;border:2px solid transparent;border-radius:18px;background:rgba(255,255,255,.96);color:#2d3748;text-align:center;text-decoration:none;box-shadow:0 8px 28px rgba(25,28,48,.2);transition:transform .25s,box-shadow .25s,border-color .25s}}.card:hover{{transform:translateY(-7px);border-color:#667eea;box-shadow:0 16px 40px rgba(25,28,48,.3)}}.card .icon{{font-size:2.8rem}}.card strong{{color:#5b6fd6;font-size:1.08rem}}.card small{{color:#667085}}.card.primary{{grid-column:1/-1;min-height:145px;background:linear-gradient(135deg,rgba(255,255,255,.98),#eef0ff)}}.note{{margin:1.25rem 0;color:rgba(255,255,255,.9);text-align:center}}
@media(max-width:520px){{.grid{{grid-template-columns:1fr}}.card{{min-height:140px}}.stats{{display:grid;grid-template-columns:repeat(3,1fr)}}.stat{{min-width:0;padding:.7rem .35rem}}.stat strong{{font-size:1.3rem}}}}
@media(prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style></head><body><main class="container"><section class="hero"><h1>🇹🇼 Taiwan Chinese Learning</h1>
<p>Traditional Chinese · Pinyin · English · हिन्दी</p><div class="stats"><div class="stat"><strong>6,070</strong><span>Words</span></div><div class="stat"><strong>69</strong><span>Categories</span></div><div class="stat"><strong>6</strong><span>HSK Levels</span></div></div></section>
<p class="note"><strong>Phone:</strong> choose the all-in-one app. Separate pages require the complete folder.</p>
<p class="note" id="sandbox-note" hidden></p>
<section class="grid" aria-label="Learning modules">{body}</section></main>
<script>
(function(){{
  /* A file manager can share this launcher with the browser as a one-file
     content:// grant, which cannot reach the pages stored beside it. Saying so
     up front beats letting every tap end on ERR_FILE_NOT_FOUND. */
  var protocol=location.protocol;
  if(protocol==="http:"||protocol==="https:"||protocol==="file:")return;
  var note=document.getElementById("sandbox-note");
  if(note){{
    note.hidden=false;
    note.innerHTML="<strong>Your file manager shared only this launcher with the browser.</strong> It cannot open the pages stored beside it. Open <code>{all_in_one}</code> from the same folder instead \u2014 that single file holds every page.";
  }}
  Array.prototype.forEach.call(document.querySelectorAll("a.card"),function(card){{
    card.setAttribute("aria-disabled","true");
    card.style.opacity=".55";
  }});
  document.addEventListener("click",function(event){{
    var link=event.target&&event.target.closest?event.target.closest("a[href]"):null;
    if(!link)return;
    event.preventDefault();
    if(note&&note.scrollIntoView)note.scrollIntoView({{block:"nearest"}});
  }},true);
}})();
</script>
</body></html>"""
    MOBILE.mkdir(parents=True, exist_ok=True)
    (MOBILE / "START.html").write_text(template, encoding="utf-8")
    (ROOT / "START.html").write_text(template, encoding="utf-8")


def main() -> None:
    MOBILE.mkdir(parents=True, exist_ok=True)
    for source, outputs, scripts in PAGE_CONFIG:
        bundle(source, outputs, scripts)
    bundle_unified()
    write_launchers()


if __name__ == "__main__":
    main()
