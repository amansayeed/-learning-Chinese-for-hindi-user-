#!/usr/bin/env node
/**
 * Build one self-contained HTML file for phones (content://, Google Drive).
 * All pages switch inside the file — no sibling .html links needed.
 *
 *   node scripts/build-offline-app.js
 */
"use strict";

const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
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
  h = h.replace(/<script>\s*window\.__UNIFIED_APP__\s*=\s*true;\s*<\/script>\s*/i, "");
  return h;
}

const scripts = [
  "js/offline.js",
  "data/vocabulary.js",
  "data/nhm-1000-common.js",
  "data/hsk-1.js",
  "data/hsk-2.js",
  "data/hsk-3.js",
  "data/hsk-4.js",
  "data/hsk-5.js",
  "data/hsk-6.js",
  "data/tone-page.data.js",
  "js/sidebar.js",
  "js/app.js",
  "js/pronunciation.js",
  "js/tones.js",
  "js/app-router.js",
];

for (const rel of scripts) {
  if (!fs.existsSync(path.join(root, rel))) {
    console.error("Missing dependency:", rel);
    console.error("Run: node scripts/build-offline-bundles.js --with-tones");
    console.error("And: python scripts/build_hsk.py 1 2 3 4 5 6");
    process.exit(1);
  }
}

let html = stripExternalAssets(read("pages/app.html"));
const css = read("css/styles.css");
const storageSafe = escapeForScript(read("js/storage-safe.js"));
const scriptBlocks = scripts
  .map(function (rel) {
    return "<script>\n" + escapeForScript(read(rel)) + "\n</script>";
  })
  .join("\n");

const headInject =
  "<style>\n" +
  css +
  "\n</style>\n" +
  "<script>window.__OFFLINE_FILE__=true;window.__MOBILE_PACK__=true;window.__UNIFIED_APP__=true;</script>";

html = html.replace("<head>", "<head>\n<script>\n" + storageSafe + "\n</script>\n");
html = html.replace("</head>", headInject + "\n</head>");
html = html.replace("</body>", scriptBlocks + "\n</body>");

fs.mkdirSync(mobileDir, { recursive: true });

["chinese.html", "mobile/chinese.html", "mobile/index.html"].forEach(function (outName) {
  const outPath = path.join(root, outName);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, html, "utf8");
  const kb = Math.round(fs.statSync(outPath).size / 1024);
  console.log("Wrote", outName, "(" + kb + " KB)");
});

const startRedirect = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>Chinese study</title>
  <meta http-equiv="refresh" content="0;url=index.html" />
  <style>
    body{font-family:system-ui,sans-serif;margin:0;padding:2rem;background:#0f172a;color:#e2e8f0;text-align:center}
    a{color:#5eead4;font-weight:700}
  </style>
</head>
<body>
  <p>Opening Chinese study app…</p>
  <p><a href="index.html">Tap here if not redirected</a></p>
  <p style="color:#94a3b8;font-size:0.9rem;margin-top:2rem">Use <strong>index.html</strong> only (one file, all pages inside).</p>
</body>
</html>
`;

fs.writeFileSync(path.join(mobileDir, "START.html"), startRedirect, "utf8");
fs.writeFileSync(path.join(root, "START.html"), startRedirect.replace(/url=index\.html/g, "url=mobile/index.html").replace(/href="index\.html"/g, 'href="mobile/index.html"'), "utf8");
console.log("Wrote START.html (redirects to unified app)");

console.log("\nOn phone: copy mobile/index.html (or whole mobile/ folder) and open index.html in Chrome.");
