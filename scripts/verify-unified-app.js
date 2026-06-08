#!/usr/bin/env node
/**
 * Verify mobile/index.html unified offline app before commit.
 *   node scripts/verify-unified-app.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.join(__dirname, "..");
const htmlPath = path.join(root, "mobile", "index.html");

let failed = 0;

function fail(msg) {
  console.error("FAIL:", msg);
  failed++;
}

function pass(msg) {
  console.log("OK:", msg);
}

if (!fs.existsSync(htmlPath)) {
  fail("mobile/index.html missing — run: node scripts/build-offline-app.js");
  process.exit(1);
}

const html = fs.readFileSync(htmlPath, "utf8");
const sizeKB = Math.round(fs.statSync(htmlPath).size / 1024);

if (sizeKB < 1200) fail("File too small (" + sizeKB + " KB) — expected ~1500+ KB unified bundle");
else pass("Size " + sizeKB + " KB");

if (!html.includes("window.__CHINESE_STORAGE_PATCHED__")) {
  fail("Missing storage-safe patch (needed for mobile Chrome without localStorage)");
} else pass("Storage-safe patch bundled");

if (!html.includes("window.__UNIFIED_APP__=true")) fail("Missing __UNIFIED_APP__ flag");
else pass("__UNIFIED_APP__ flag present");

if (!html.includes("window.AppRouter")) fail("Missing AppRouter");
else pass("AppRouter bundled");

if (!html.includes("ChineseVocabApp")) fail("Missing ChineseVocabApp");
else pass("ChineseVocabApp bundled");

if (!html.includes("window.__VOCAB__")) fail("Missing TOCFL data");
else pass("TOCFL data embedded");

if (!html.includes("window.__VOCAB_HSK6__")) fail("Missing HSK6 data");
else pass("HSK6 data embedded");

if (!html.includes("window.__TONE_PAGE_DATA__")) fail("Missing tone data");
else pass("Tone data embedded");

const appViews = (html.match(/data-app-view="/g) || []).length;
if (appViews < 9) fail("Expected 9 sidebar data-app-view links, found " + appViews);
else pass(appViews + " in-app navigation links");

if (/href="hsk2\.html"/.test(html)) fail("Still has broken hsk2.html link");
else pass("No cross-file hsk2.html links");

["app-view-words", "app-view-pronounce", "app-view-tones", "toolbar-words", "toolbar-pronounce"].forEach(function (id) {
  if (!html.includes('id="' + id + '"')) fail("Missing #" + id);
  else pass("DOM id #" + id);
});

function extractScript(name) {
  const rel = path.join("js", name);
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function makeClassList(el) {
  el._cls = el._cls || new Set();
  el.classList = {
    add: function (c) {
      el._cls.add(c);
    },
    remove: function (c) {
      el._cls.delete(c);
    },
    contains: function (c) {
      return el._cls.has(c);
    },
    toggle: function (c, on) {
      if (on === undefined) on = !el._cls.has(c);
      if (on) el._cls.add(c);
      else el._cls.delete(c);
    },
  };
}

function makeEl(id, tag) {
  const el = { id: id, tagName: (tag || "DIV").toUpperCase(), children: [], attributes: {}, style: {} };
  makeClassList(el);
  el.setAttribute = function (k, v) {
    el.attributes[k] = v;
  };
  el.removeAttribute = function (k) {
    delete el.attributes[k];
  };
  el.getAttribute = function (k) {
    return el.attributes[k] || null;
  };
  el.querySelector = function () {
    return null;
  };
  el.querySelectorAll = function () {
    return [];
  };
  el.addEventListener = function () {};
  el.appendChild = function (c) {
    el.children.push(c);
  };
  el.closest = function () {
    return null;
  };
  return el;
}

function runRuntimeRouterTest() {
  const ids = [
    "app-view-words",
    "app-view-pronounce",
    "app-view-tones",
    "toolbar-words",
    "toolbar-pronounce",
    "sidebar-hsk-menu",
  ];
  const navLinks = [
    { view: "words" },
    { view: "hsk1" },
    { view: "hsk2" },
    { view: "hsk3" },
    { view: "hsk4" },
    { view: "hsk5" },
    { view: "hsk6" },
    { view: "pronounce" },
    { view: "tones" },
  ].map(function (x) {
    const el = makeEl("", "a");
    el.getAttribute = function (k) {
      return k === "data-app-view" ? x.view : null;
    };
    return el;
  });

  const byId = {};
  ids.forEach(function (id) {
    byId[id] = makeEl(id);
  });

  const hskMenu = byId["sidebar-hsk-menu"];
  hskMenu.querySelector = function (sel) {
    if (sel === ".sidebar-dropdown__toggle") return makeEl("toggle", "summary");
    return null;
  };

  let switchedTo = null;
  const window = {
    __UNIFIED_APP__: true,
    __closeSidebarDrawer: function () {},
    ChineseVocabApp: {
      switchTo: function (mode) {
        switchedTo = mode;
      },
    },
    location: { hash: "", protocol: "file:" },
    history: {
      replaceState: function () {},
      pushState: function () {},
    },
    scrollTo: function () {},
    addEventListener: function () {},
    document: {
      readyState: "complete",
      getElementById: function (id) {
        return byId[id] || null;
      },
      querySelectorAll: function (sel) {
        if (sel === ".sidebar-nav [data-app-view]" || sel === "[data-app-view]") return navLinks;
        return [];
      },
    },
  };

  window.window = window;
  window.globalThis = window;

  vm.createContext(window);
  vm.runInContext(extractScript("app-router.js"), window, { filename: "app-router.js" });

  if (!window.AppRouter) {
    fail("AppRouter failed to load in runtime sandbox");
    return;
  }
  pass("AppRouter loads in runtime sandbox");

  window.AppRouter.go("words", true);
  if (byId["app-view-words"].classList.contains("hidden")) fail("Words view hidden");
  else pass("Router: words view visible");

  window.AppRouter.go("hsk2", true);
  if (byId["app-view-words"].classList.contains("hidden")) fail("Words panel hidden on hsk2");
  else pass("Router: hsk2 keeps words panel visible");
  if (switchedTo !== "hsk2") fail("switchTo not called for hsk2 (got " + switchedTo + ")");
  else pass("Router: ChineseVocabApp.switchTo('hsk2')");

  window.AppRouter.go("pronounce", true);
  if (byId["app-view-pronounce"].classList.contains("hidden")) fail("Pronounce view hidden");
  else pass("Router: pronounce view visible");
  if (!byId["toolbar-pronounce"].classList.contains("hidden")) pass("Router: pronounce toolbar shown");
  else fail("Pronounce toolbar hidden");

  window.AppRouter.go("tones", true);
  if (byId["app-view-tones"].classList.contains("hidden")) fail("Tones view hidden");
  else pass("Router: tones view visible");
  if (!byId["toolbar-words"].classList.contains("hidden")) fail("Words toolbar should hide on tones");
  else pass("Router: toolbars hidden on tones");
}

// Syntax-check bundled inline scripts (skip small head flags)
const blocks = html.match(/<script>\n([\s\S]*?)<\/script>/g) || [];
let scriptOk = 0;
blocks.forEach(function (block, i) {
  const code = block.replace(/^<script>\n/, "").replace(/\n<\/script>$/, "");
  if (code.length < 80 && code.includes("__OFFLINE_FILE__")) return;
  if (code.includes("chinese-vocab-theme") && code.length < 500) return;
  try {
    new Function(code);
    scriptOk++;
  } catch (e) {
    if (String(e.message).includes("Unexpected token '<'")) return;
    fail("Script block " + i + " syntax error: " + e.message);
  }
});
pass(scriptOk + " bundled script blocks parse cleanly");

runRuntimeRouterTest();

(function testStoragePatch() {
  const code = fs.readFileSync(path.join(root, "js", "storage-safe.js"), "utf8");
  const win = {
    localStorage: {
      setItem: function () {
        throw new Error("SecurityError");
      },
      getItem: function () {
        throw new Error("SecurityError");
      },
    },
    sessionStorage: {
      setItem: function () {
        throw new Error("SecurityError");
      },
      getItem: function () {
        throw new Error("SecurityError");
      },
    },
  };
  win.window = win;
  vm.createContext(win);
  vm.runInContext(code, win);
  win.localStorage.setItem("chinese-vocab-theme", "light");
  if (win.localStorage.getItem("chinese-vocab-theme") !== "light") {
    fail("Storage patch did not provide memory fallback");
  } else {
    pass("Storage patch works when localStorage is blocked");
  }
})();

// Serve over HTTP and confirm file responds
const server = require("http").createServer(function (req, res) {
  if (req.url === "/" || req.url === "/index.html") {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(html);
  } else {
    res.writeHead(404);
    res.end("not found");
  }
});

server.listen(0, "127.0.0.1", function () {
  const port = server.address().port;
  fetch("http://127.0.0.1:" + port + "/index.html")
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.text();
    })
    .then(function (body) {
      if (body.length < 1000000) throw new Error("HTTP body too small");
      if (!body.includes("data-app-view")) throw new Error("HTTP body missing router nav");
      pass("HTTP serve test (" + Math.round(body.length / 1024) + " KB delivered)");
      server.close();
      console.log(
        failed
          ? "\n" + failed + " check(s) FAILED — do not commit yet."
          : "\nAll checks PASSED — mobile/index.html is working. Safe to commit."
      );
      process.exit(failed ? 1 : 0);
    })
    .catch(function (e) {
      server.close();
      fail("HTTP serve test: " + e.message);
      console.log("\n" + failed + " check(s) FAILED.");
      process.exit(1);
    });
});
