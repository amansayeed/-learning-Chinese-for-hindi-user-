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
  <title>Chinese study</title>
  <style>
    body{font-family:system-ui,sans-serif;margin:0;padding:max(1rem,env(safe-area-inset-top)) max(1rem,env(safe-area-inset-right)) max(1rem,env(safe-area-inset-bottom)) max(1rem,env(safe-area-inset-left));background:#0f172a;color:#e2e8f0;line-height:1.5}
    h1{font-size:1.25rem}
    a{display:block;padding:1rem;margin:0.5rem 0;background:#1e293b;border:1px solid #334155;border-radius:12px;color:#5eead4;text-decoration:none;font-weight:700;font-size:1.05rem}
    a.primary{background:#134e4a;border-color:#0d9488}
    p{color:#94a3b8;font-size:0.9rem}
  </style>
</head>
<body>
  <h1>中文 · Chinese study</h1>
  <p><strong>On phone (Google Drive / one file):</strong> open <code>chinese.html</code> only — sidebar works inside that file.</p>
  <a href="chinese.html" class="primary">Open all-in-one app (recommended for phone)</a>
  <p>Or open separate pages (needs every .html file in the same folder):</p>
  <a href="words.html">Words · table &amp; study</a>
  <a href="hsk.html">HSK 1 · 500 words</a>
  <a href="hsk2.html">HSK 2 · 772 words</a>
  <a href="hsk3.html">HSK 3 · 973 words</a>
  <a href="hsk4.html">HSK 4 · 1000 words</a>
  <a href="hsk5.html">HSK 5 · 1071 words</a>
  <a href="hsk6.html">HSK 6 · 1140 words</a>
  <a href="pronunciation.html">English · clusters</a>
  <a href="tones.html">Four tones</a>
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

console.log("\nDone. On phone: open mobile/chinese.html (one file, ~2–3 MB) or copy the whole mobile/ folder.");
