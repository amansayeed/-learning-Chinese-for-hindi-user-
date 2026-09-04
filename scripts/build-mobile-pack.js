#!/usr/bin/env node
/**
 * Build self-contained HTML (CSS + JS + data inlined) for phones, Google Drive, file://.
 * Writes to project root AND mobile/ so index.html works when opened from Drive.
 *
 *   node scripts/build-mobile-pack.js
 *
 * Edit pages/*.html, css/, js/ — then run this script.
 */
"use strict";

const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const pagesDir = path.join(root, "pages");
const mobileDir = path.join(root, "mobile");

function read(rel) {
  const p = path.join(root, rel);
  if (!fs.existsSync(p)) {
    console.error("Missing:", rel);
    process.exit(1);
  }
  return fs.readFileSync(p, "utf8");
}

function escapeForScript(js) {
  return js.replace(/<\/script/gi, "<\\/script");
}

function stripExternalAssets(html) {
  let h = html;
  h = h.replace(/<link[^>]*fonts\.googleapis[^>]*>\s*/gi, "");
  h = h.replace(/<link[^>]*fonts\.gstatic[^>]*>\s*/gi, "");
  h = h.replace(/<link[^>]*rel=["']stylesheet["'][^>]*>\s*/gi, "");
  h = h.replace(/<script[^>]*\ssrc=["'][^"']+["'][^>]*>\s*<\/script>\s*/gi, "");
  h = h.replace(
    /<script>\s*document\.addEventListener\("DOMContentLoaded"[\s\S]*?<\/script>\s*/gi,
    ""
  );
  h = h.replace(
    /<script>\s*\(function \(\) \{\s*var loc = window\.location;[\s\S]*?window\.__OFFLINE_FILE__ = false;\s*\}\)\(\);\s*<\/script>\s*/i,
    ""
  );
  return h;
}

function fixNavLinks(html) {
  return html
    .replace(/href="\.\/index\.html"/g, 'href="index.html"')
    .replace(/href="\.\/hsk6\.html"/g, 'href="hsk6.html"')
    .replace(/href="\.\/hsk5\.html"/g, 'href="hsk5.html"')
    .replace(/href="\.\/hsk4\.html"/g, 'href="hsk4.html"')
    .replace(/href="\.\/hsk3\.html"/g, 'href="hsk3.html"')
    .replace(/href="\.\/hsk2\.html"/g, 'href="hsk2.html"')
    .replace(/href="\.\/hsk\.html"/g, 'href="hsk.html"')
    .replace(/href="\.\/pronunciation\.html"/g, 'href="pronunciation.html"')
    .replace(/href="\.\/tones\.html"/g, 'href="tones.html"')
    .replace(/href="mobile\/START\.html"/g, 'href="START.html"')
    .replace(/href="\.\/mobile\/START\.html"/g, 'href="START.html"');
}

function bundlePage({ srcHtml, outNames, scripts, titleNote }) {
  const srcPath = path.join(pagesDir, srcHtml);
  if (!fs.existsSync(srcPath)) {
    console.error("Missing page source:", srcPath);
    process.exit(1);
  }

  let html = stripExternalAssets(fs.readFileSync(srcPath, "utf8"));
  html = fixNavLinks(html);

  const css = read("css/styles.css");
  const scriptBlocks = ["js/storage-safe.js"].concat(scripts)
    .map(function (rel) {
      return "<script>\n" + escapeForScript(read(rel)) + "\n</script>";
    })
    .join("\n");

  const headInject =
    "<style>\n" +
    css +
    "\n</style>\n" +
    "<script>window.__OFFLINE_FILE__=true;window.__MOBILE_PACK__=true;</script>";

  html = html.replace("</head>", headInject + "\n</head>");

  const boot =
    '<script>(function(){var v=(window.__VOCAB__&&window.__VOCAB__.levels)||(window.__VOCAB_NHM__&&window.__VOCAB_NHM__.levels)||(window.__VOCAB_HSK1__&&window.__VOCAB_HSK1__.levels)||(window.__VOCAB_HSK2__&&window.__VOCAB_HSK2__.levels)||(window.__VOCAB_HSK3__&&window.__VOCAB_HSK3__.levels)||(window.__VOCAB_HSK4__&&window.__VOCAB_HSK4__.levels)||(window.__VOCAB_HSK5__&&window.__VOCAB_HSK5__.levels)||(window.__VOCAB_HSK6__&&window.__VOCAB_HSK6__.levels);var t=window.__TONE_PAGE_DATA__&&window.__TONE_PAGE_DATA__.quartets;if(v||t)return;var m=document.querySelector(".layout-main");if(!m)return;var b=document.createElement("div");b.setAttribute("role","alert");b.style.cssText="margin:0 0 1rem;padding:0.75rem;background:#991b1b;color:#fff;border-radius:8px;font-size:0.9rem;font-weight:600";b.textContent="Word data did not load. Download this HTML again from git (large file, not a few KB).";m.insertBefore(b,m.firstChild);})();</script>';

  html = html.replace("</body>", scriptBlocks + "\n" + boot + "\n</body>");

  if (titleNote) {
    html = html.replace(
      /<span class="mobile-bar__hint">[^<]*<\/span>/,
      '<span class="mobile-bar__hint">' + titleNote + "</span>"
    );
  }

  html = html.replace(
    /<strong>On your phone:<\/strong>[\s\S]*?<\/p>/,
    "<strong>Offline:</strong> this file includes all styles and data (works from Google Drive / phone storage).</p>"
  );

  outNames.forEach(function (outName) {
    const outPath = path.join(root, outName);
    const outputHtml = outName.startsWith("mobile/")
      ? html.replace(/href="index\.html"/g, 'href="words.html"')
      : html;
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, outputHtml, "utf8");
    const kb = Math.round(fs.statSync(outPath).size / 1024);
    console.log("Wrote", outName, "(" + kb + " KB)");
  });

  return html;
}

if (!fs.existsSync(path.join(root, "data", "vocabulary.js"))) {
  console.error("Run first: node scripts/build-offline-bundles.js");
  process.exit(1);
}
if (!fs.existsSync(path.join(root, "data", "tone-page.data.js"))) {
  console.error("Run first: node scripts/build-offline-bundles.js --with-tones");
  process.exit(1);
}

fs.mkdirSync(mobileDir, { recursive: true });

bundlePage({
  srcHtml: "index.html",
  outNames: ["index.html", "mobile/words.html"],
  titleNote: "Tap ☰ for menu & filters",
  scripts: [
    "js/offline.js",
    "data/vocabulary.js",
    "data/nhm-1000-common.js",
    "js/sidebar.js",
    "js/app.js",
  ],
});

bundlePage({
  srcHtml: "pronunciation.html",
  outNames: ["pronunciation.html", "mobile/pronunciation.html"],
  titleNote: "Tap ☰ for menu & filters",
  scripts: [
    "js/offline.js",
    "data/vocabulary.js",
    "data/nhm-1000-common.js",
    "js/sidebar.js",
    "js/pronunciation.js",
  ],
});

bundlePage({
  srcHtml: "hsk6.html",
  outNames: ["hsk6.html", "mobile/hsk6.html"],
  titleNote: "Tap ☰ for menu & filters",
  scripts: ["js/offline.js", "data/hsk-6.js", "js/sidebar.js", "js/app.js"],
});

bundlePage({
  srcHtml: "hsk5.html",
  outNames: ["hsk5.html", "mobile/hsk5.html"],
  titleNote: "Tap ☰ for menu & filters",
  scripts: ["js/offline.js", "data/hsk-5.js", "js/sidebar.js", "js/app.js"],
});

bundlePage({
  srcHtml: "hsk4.html",
  outNames: ["hsk4.html", "mobile/hsk4.html"],
  titleNote: "Tap ☰ for menu & filters",
  scripts: ["js/offline.js", "data/hsk-4.js", "js/sidebar.js", "js/app.js"],
});

bundlePage({
  srcHtml: "hsk3.html",
  outNames: ["hsk3.html", "mobile/hsk3.html"],
  titleNote: "Tap ☰ for menu & filters",
  scripts: ["js/offline.js", "data/hsk-3.js", "js/sidebar.js", "js/app.js"],
});

bundlePage({
  srcHtml: "hsk2.html",
  outNames: ["hsk2.html", "mobile/hsk2.html"],
  titleNote: "Tap ☰ for menu & filters",
  scripts: ["js/offline.js", "data/hsk-2.js", "js/sidebar.js", "js/app.js"],
});

bundlePage({
  srcHtml: "hsk.html",
  outNames: ["hsk.html", "mobile/hsk.html"],
  titleNote: "Tap ☰ for menu & filters",
  scripts: ["js/offline.js", "data/hsk-1.js", "js/sidebar.js", "js/app.js"],
});

bundlePage({
  srcHtml: "tones.html",
  outNames: ["tones.html", "mobile/tones.html"],
  titleNote: "Tap ☰ for menu",
  scripts: ["js/offline.js", "data/tone-page.data.js", "js/sidebar.js", "js/tones.js"],
});

const launcher = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>Taiwan Chinese Learning</title>
  <style>
    *{box-sizing:border-box}body{font-family:"Segoe UI",system-ui,sans-serif;margin:0;min-height:100vh;padding:max(1rem,env(safe-area-inset-top)) max(1rem,env(safe-area-inset-right)) max(1rem,env(safe-area-inset-bottom)) max(1rem,env(safe-area-inset-left));background:linear-gradient(135deg,#667eea,#764ba2);color:#2d3748;line-height:1.5}
    .container{width:min(1180px,100%);margin:auto}.hero{padding:clamp(2rem,7vw,5rem) 1.25rem;margin-bottom:1.5rem;border-radius:22px;background:rgba(255,255,255,.96);box-shadow:0 12px 42px rgba(25,28,48,.25);text-align:center}
    h1{margin:0;font-size:clamp(2rem,7vw,4rem);line-height:1.08;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;background-clip:text;color:transparent}.hero p{color:#667085;font-size:clamp(1rem,2vw,1.25rem)}
    .stats{display:flex;justify-content:center;gap:clamp(.6rem,3vw,2.5rem);flex-wrap:wrap;margin-top:2rem}.stat{min-width:120px;padding:.9rem 1.2rem;border-radius:14px;background:rgba(102,126,234,.1)}.stat strong{display:block;color:#667eea;font-size:1.7rem}.stat span{color:#667085;font-size:.82rem;font-weight:700}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1rem}.card{display:flex;min-height:180px;flex-direction:column;align-items:center;justify-content:center;gap:.5rem;padding:1.25rem;border:2px solid transparent;border-radius:18px;background:rgba(255,255,255,.96);color:#2d3748;text-align:center;text-decoration:none;box-shadow:0 8px 28px rgba(25,28,48,.2);transition:transform .25s,box-shadow .25s,border-color .25s}.card:hover{transform:translateY(-7px);border-color:#667eea;box-shadow:0 16px 40px rgba(25,28,48,.3)}.card .icon{font-size:2.8rem}.card strong{color:#5b6fd6;font-size:1.08rem}.card small{color:#667085}.card.primary{grid-column:1/-1;min-height:145px;background:linear-gradient(135deg,rgba(255,255,255,.98),#eef0ff)}.note{margin:1.25rem 0;color:rgba(255,255,255,.9);text-align:center}
    @media(max-width:520px){.grid{grid-template-columns:1fr}.card{min-height:140px}.stats{display:grid;grid-template-columns:repeat(3,1fr)}.stat{min-width:0;padding:.7rem .35rem}.stat strong{font-size:1.3rem}}
    @media(prefers-reduced-motion:reduce){*{transition:none!important}}
  </style>
</head>
<body>
  <main class="container"><section class="hero"><h1>🇹🇼 Taiwan Chinese Learning</h1>
  <p>Traditional Chinese · Pinyin · English · हिन्दी</p><div class="stats"><div class="stat"><strong>6,070</strong><span>Words</span></div><div class="stat"><strong>69</strong><span>Categories</span></div><div class="stat"><strong>6</strong><span>HSK Levels</span></div></div></section>
  <p class="note"><strong>Phone:</strong> choose the all-in-one app. Separate pages require the complete folder.</p>
  <section class="grid" aria-label="Learning modules">
  <a href="chinese.html" class="card primary"><span class="icon" aria-hidden="true">🚀</span><strong>Open all-in-one app</strong><small>Dashboard, categories, search, learn and progress</small></a>
  <a href="words.html" class="card"><span class="icon" aria-hidden="true">📖</span><strong>Words · table &amp; study</strong><small>Browse TOCFL and common vocabulary</small></a>
  <a href="hsk.html" class="card"><span class="icon" aria-hidden="true">1️⃣</span><strong>HSK 1 · 500 words</strong><small>Start with essential beginner vocabulary</small></a>
  <a href="hsk2.html" class="card"><span class="icon" aria-hidden="true">2️⃣</span><strong>HSK 2 · 772 words</strong><small>Build everyday communication skills</small></a>
  <a href="hsk3.html" class="card"><span class="icon" aria-hidden="true">3️⃣</span><strong>HSK 3 · 973 words</strong><small>Grow practical intermediate vocabulary</small></a>
  <a href="hsk4.html" class="card"><span class="icon" aria-hidden="true">4️⃣</span><strong>HSK 4 · 1000 words</strong><small>Strengthen confident communication</small></a>
  <a href="hsk5.html" class="card"><span class="icon" aria-hidden="true">5️⃣</span><strong>HSK 5 · 1071 words</strong><small>Study advanced words and expressions</small></a>
  <a href="hsk6.html" class="card"><span class="icon" aria-hidden="true">6️⃣</span><strong>HSK 6 · 1140 words</strong><small>Master high-level vocabulary</small></a>
  <a href="pronunciation.html" class="card"><span class="icon" aria-hidden="true">🗣️</span><strong>Pronunciation</strong><small>Practice Chinese sounds and clusters</small></a>
  <a href="tones.html" class="card"><span class="icon" aria-hidden="true">🎵</span><strong>Four tones</strong><small>Train Mandarin tone recognition</small></a>
  </section></main>
</body>
</html>
`;

fs.writeFileSync(path.join(mobileDir, "START.html"), launcher, "utf8");
fs.writeFileSync(
  path.join(root, "START.html"),
  launcher.replace('href="words.html"', 'href="index.html"'),
  "utf8"
);
console.log("Wrote START.html (root + mobile/)");

console.log("\nDone. On phone: open mobile/chinese.html (one file, ~7–8 MB) or copy the whole mobile/ folder.");
