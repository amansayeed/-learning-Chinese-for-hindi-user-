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
  console.log("Phone folder: mobile/ — open mobile/START.html on your device.");
}
