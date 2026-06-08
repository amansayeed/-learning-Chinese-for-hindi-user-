#!/usr/bin/env node
/**
 * Build .js bundles for phone / file:// use (fetch for JSON is blocked there).
 * Run from repo root: node scripts/build-offline-bundles.js
 */
"use strict";

const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");

function writeBundle(jsonRel, jsRel, globalName) {
  const jsonPath = path.join(root, jsonRel);
  const jsPath = path.join(root, jsRel);
  if (!fs.existsSync(jsonPath)) {
    console.error("Missing:", jsonPath);
    process.exit(1);
  }
  const data = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
  const body =
    "// Auto-generated for offline / file:// — do not edit by hand\n" +
    "// Source: " +
    jsonRel +
    "\n" +
    "window." +
    globalName +
    " = " +
    JSON.stringify(data) +
    ";\n";
  fs.writeFileSync(jsPath, body, "utf8");
  console.log("Wrote", jsRel, "(" + Math.round(body.length / 1024) + " KB)");
}

writeBundle("data/vocabulary.json", "data/vocabulary.js", "__VOCAB__");
writeBundle("data/nhm-1000-common.json", "data/nhm-1000-common.js", "__VOCAB_NHM__");
if (fs.existsSync(path.join(root, "data", "hsk-1.json"))) {
  writeBundle("data/hsk-1.json", "data/hsk-1.js", "__VOCAB_HSK1__");
} else {
  console.log("Skipped hsk-1.js (run: python scripts/build_hsk.py 1)");
}
if (fs.existsSync(path.join(root, "data", "hsk-2.json"))) {
  writeBundle("data/hsk-2.json", "data/hsk-2.js", "__VOCAB_HSK2__");
} else {
  console.log("Skipped hsk-2.js (run: python scripts/build_hsk.py 2)");
}
if (fs.existsSync(path.join(root, "data", "hsk-3.json"))) {
  writeBundle("data/hsk-3.json", "data/hsk-3.js", "__VOCAB_HSK3__");
} else {
  console.log("Skipped hsk-3.js (run: python scripts/build_hsk.py 3)");
}
if (fs.existsSync(path.join(root, "data", "hsk-4.json"))) {
  writeBundle("data/hsk-4.json", "data/hsk-4.js", "__VOCAB_HSK4__");
} else {
  console.log("Skipped hsk-4.js (run: python scripts/build_hsk.py 4)");
}
if (fs.existsSync(path.join(root, "data", "hsk-5.json"))) {
  writeBundle("data/hsk-5.json", "data/hsk-5.js", "__VOCAB_HSK5__");
} else {
  console.log("Skipped hsk-5.js (run: python scripts/build_hsk.py 5)");
}
if (fs.existsSync(path.join(root, "data", "hsk-6.json"))) {
  writeBundle("data/hsk-6.json", "data/hsk-6.js", "__VOCAB_HSK6__");
} else {
  console.log("Skipped hsk-6.js (run: python scripts/build_hsk.py 6)");
}

if (process.argv.includes("--with-tones")) {
  const { spawnSync } = require("child_process");
  const toneBuild = spawnSync(process.execPath, [path.join(__dirname, "build-tone-data.js")], {
    cwd: root,
    stdio: "inherit",
  });
  if (toneBuild.status !== 0) {
    console.warn("Tone bundles not rebuilt. Run: node scripts/build-tone-data.js");
  }
} else {
  console.log("Skipped tone rebuild (pass --with-tones to regenerate tone-page.data.js).");
}

console.log("Offline bundles ready.");

const { spawnSync } = require("child_process");
const pack = spawnSync(process.execPath, [path.join(__dirname, "build-mobile-pack.js")], {
  cwd: root,
  stdio: "inherit",
});
if (pack.status !== 0) {
  console.warn("Mobile pack not built. Run: node scripts/build-mobile-pack.js");
} else {
  console.log("Phone folder: mobile/ — open mobile/chinese.html on your device.");
}

const unified = spawnSync(process.execPath, [path.join(__dirname, "build-offline-app.js")], {
  cwd: root,
  stdio: "inherit",
});
if (unified.status !== 0) {
  console.warn("Unified app not built. Run: node scripts/build-offline-app.js");
}
