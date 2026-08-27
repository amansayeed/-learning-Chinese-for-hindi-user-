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

console.log("\nOn phone: copy mobile/index.html (or whole mobile/ folder) and open index.html in Chrome.");
