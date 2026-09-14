# -*- coding: utf-8 -*-
"""Run the real browser modules against a minimal DOM so blank screens fail the build."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import dukpy

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "vocabulary-master.json"
MODULES = [
    "js/learning-state.js",
    "js/vocab-store.js",
    "js/app-router.js",
    "js/vocabulary-ui.js",
    "js/tocfl-ui.js",
]
SAMPLE_PER_LEVEL = 40

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if condition:
        print("OK:", message)
    else:
        failures.append(message)
        print("FAIL:", message)


def sample_payload() -> dict:
    """Keep the real record shape but a small slice, so duktape stays fast."""
    payload = json.loads(MASTER.read_text(encoding="utf-8"))
    buckets: dict[str, list] = {}
    for word in payload["words"]:
        level = word["hsk"]["level"]
        key = str(level) if level else "outside-hsk"
        bucket = buckets.setdefault(key, [])
        if len(bucket) < SAMPLE_PER_LEVEL:
            bucket.append(word)
    words = [w for key in ["1", "2", "3", "4", "5", "6", "outside-hsk"] for w in buckets.get(key, [])]
    return {"meta": payload["meta"], "words": words}


DOM_SHIM = """
var elements = {};
function makeClassList(el) {
  var set = {};
  return {
    add: function (c) { set[c] = true; },
    remove: function (c) { delete set[c]; },
    contains: function (c) { return !!set[c]; },
    toggle: function (c, on) {
      if (on === undefined) on = !set[c];
      if (on) set[c] = true; else delete set[c];
      return !!on;
    }
  };
}
function makeEl(id) {
  var el = {
    id: id, innerHTML: "", textContent: "", value: "", checked: true,
    max: 0, open: false, attributes: {}, style: {}
  };
  el.classList = makeClassList(el);
  el.setAttribute = function (k, v) { el.attributes[k] = v; };
  el.getAttribute = function (k) { return k in el.attributes ? el.attributes[k] : null; };
  el.removeAttribute = function (k) { delete el.attributes[k]; };
  el.addEventListener = function () {};
  el.appendChild = function () {};
  el.querySelector = function () { return null; };
  el.querySelectorAll = function () { return []; };
  el.closest = function () { return null; };
  el.focus = function () {};
  return el;
}
var document = {
  readyState: "complete",
  documentElement: makeEl("html"),
  head: makeEl("head"),
  body: makeEl("body"),
  getElementById: function (id) {
    if (!elements[id]) elements[id] = makeEl(id);
    return elements[id];
  },
  querySelector: function () { return null; },
  querySelectorAll: function () { return []; },
  addEventListener: function () {},
  createElement: function (tag) { return makeEl(tag); }
};
var storage = {};
var localStorage = {
  getItem: function (k) { return k in storage ? storage[k] : null; },
  setItem: function (k, v) { storage[k] = String(v); },
  removeItem: function (k) { delete storage[k]; }
};
var sessionStorage = localStorage;
var window = this;
window.window = window;
window.document = document;
window.localStorage = localStorage;
window.sessionStorage = sessionStorage;
window.location = { hash: "", protocol: "file:", href: "file:///app.html" };
window.history = { pushState: function () {}, replaceState: function () {} };
window.scrollTo = function () {};
window.addEventListener = function () {};
window.setTimeout = function (fn) { if (typeof fn === "function") fn(); return 0; };
window.clearTimeout = function () {};
window.__UNIFIED_APP__ = true;
window.speechSynthesis = { cancel: function () {}, speak: function () {} };
function SpeechSynthesisUtterance() {}
function Audio() { return { play: function () { return { catch: function () {} }; } }; }
window.SpeechSynthesisUtterance = SpeechSynthesisUtterance;
window.Audio = Audio;
"""

PROBE = r"""
var report = { errors: [] };
function html(id) { return document.getElementById(id).innerHTML || ""; }
function text(id) { return document.getElementById(id).textContent || ""; }

report.storeLoaded = !!(window.VocabStore && window.VocabStore.all);
report.uiLoaded = !!window.VocabularyUI;
report.tocflUiLoaded = !!window.TocflUI;
report.mobilePack = !!window.__MOBILE_PACK__;
report.localStoragePersists = false;
if (window.LearningState && window.LearningState.toggleFavorite) {
  window.LearningState.toggleFavorite("__local_storage_probe__");
  var savedLearning = localStorage.getItem("chinese-vocab-learning-v1");
  report.localStoragePersists =
    !!savedLearning && savedLearning.indexOf("__local_storage_probe__") !== -1;
  window.LearningState.toggleFavorite("__local_storage_probe__");
}
report.tocfl8000Words = window.__TOCFL_8000__ ? window.__TOCFL_8000__.words.length : 0;
report.ccccWords = window.__TOCFL_CCCC__ ? window.__TOCFL_CCCC__.words.length : 0;
report.tocflCombinedLevels =
  (window.__TOCFL_8000__ ? window.__TOCFL_8000__.levels.length : 0) +
  (window.__TOCFL_CCCC__ ? window.__TOCFL_CCCC__.levels.length : 0);
report.tocflLevelSizes = {};
report.tocflUniqueTotal = 0;
report.tocflUniqueDuplicates = 0;
report.totalWords = report.storeLoaded ? window.VocabStore.all().length : 0;
report.duplicatesRemoved = report.storeLoaded ? window.VocabStore.duplicateCount : 0;
report.tocflCounts = report.storeLoaded ? window.VocabStore.tocflCounts() : {};
report.tocflA1Words = report.storeLoaded ? window.VocabStore.filter({ tocfl: "A1" }).length : 0;
report.tocflRender = {
  levels: 0, categories: 0, subcategories: 0, results: 0, count: "",
  levelWordCount: 0, categoryCountMatches: false, categoryExact: false,
  subcategoryCountMatches: false, subcategoryExact: false
};
report.tocflClickFlow = {
  level: "", category: "", countText: "",
  categoryExact: false, subcategoryExact: false, countMatches: false
};
report.tocflGroups = { heads: 0, counted: false, knownCategories: false, contiguous: false };
if (window.TocflUI && window.TocflUI.mount) {
  var tocflRoles = {};
  ["title", "subtitle", "levels", "categories", "subcategories", "search", "status", "count", "results", "pagination"]
    .forEach(function (role) { tocflRoles[role] = makeEl("tocfl-" + role); });
  tocflRoles.status.value = "all";
  var tocflRoot = makeEl("tocfl-smoke-root");
  tocflRoot.hasAttribute = function (name) { return name === "data-tocfl-browser"; };
  tocflRoot.getAttribute = function (name) { return name === "data-tocfl-level" ? "novice-1" : null; };
  tocflRoot.querySelector = function (selector) {
    var match = selector.match(/data-tocfl-role="([^"]+)"/);
    return match ? tocflRoles[match[1]] : null;
  };
  var tocflClick = null;
  tocflRoot.addEventListener = function (type, handler) {
    if (type === "click") tocflClick = handler;
  };
  // Chips live inside the container, which itself declares data-tocfl-level,
  // so closest() must resolve to the container exactly like a real browser.
  function tocflChip(attribute, value) {
    var chip = makeEl("tocfl-chip");
    chip.attributes[attribute] = value;
    chip.closest = function (selector) {
      var wanted = selector.replace(/^\[|\]$/g, "");
      if (wanted === attribute) return chip;
      return wanted === "data-tocfl-level" ? tocflRoot : null;
    };
    return chip;
  }
  try {
    var tocflController = window.TocflUI.mount(tocflRoot);
    ["novice-1", "novice-2", "level-1", "level-2", "level-3", "level-4", "level-5", "sprouting", "growing", "thriving"].forEach(function (level) {
      tocflController.level = level;
      report.tocflLevelSizes[level] = tocflController.wordsForLevel().length;
    });
    var uniqueSeen = {};
    report.tocflUniqueTotal = 0;
    report.tocflUniqueDuplicates = 0;
    (window.TocflUI.allWords ? window.TocflUI.allWords() : []).forEach(function (word) {
      report.tocflUniqueTotal += 1;
      var pinyin = String(word.pinyin || "").replace(/\s+/g, "");
      [word.traditional, word.simplified].forEach(function (value) {
        String(value || "").split(/[/／]/).forEach(function (form) {
          form = form.replace(/\s+/g, "");
          if (!form) return;
          var key = form + "\u001f" + pinyin;
          if (uniqueSeen[key] && uniqueSeen[key] !== word.id) report.tocflUniqueDuplicates += 1;
          uniqueSeen[key] = word.id;
        });
      });
    });
    tocflController.level = "novice-1";
    var categoryCounts = tocflController.categoryCounts();
    var selectedCategory = Object.keys(categoryCounts)[0];
    tocflController.category = selectedCategory;
    tocflController.subcategory = "all";
    var categoryWords = tocflController.filteredWords();
    var subcategoryCounts = tocflController.subcategoryCounts();
    var selectedSubcategory = Object.keys(subcategoryCounts)[0];
    tocflController.subcategory = selectedSubcategory;
    var subcategoryWords = tocflController.filteredWords();
    tocflController.render();
    report.tocflRender = {
      levels: tocflRoles.levels.innerHTML.length,
      categories: tocflRoles.categories.innerHTML.length,
      subcategories: tocflRoles.subcategories.innerHTML.length,
      results: tocflRoles.results.innerHTML.length,
      count: tocflRoles.count.textContent,
      levelWordCount: tocflController.wordsForLevel().length,
      categoryCountMatches: categoryWords.length === categoryCounts[selectedCategory],
      categoryExact: categoryWords.every(function (word) {
        return word.level === "novice-1" && word.category === selectedCategory;
      }),
      subcategoryCountMatches:
        subcategoryWords.length === subcategoryCounts[selectedSubcategory] &&
        tocflRoles.count.textContent ===
          subcategoryWords.length + " word" + (subcategoryWords.length === 1 ? "" : "s"),
      subcategoryExact: subcategoryWords.every(function (word) {
        return word.level === "novice-1" &&
          word.category === selectedCategory &&
          (word.subcategory || word.category) === selectedSubcategory;
      })
    };
    tocflController.category = "all";
    tocflController.subcategory = "all";
    tocflController.page = 1;
    tocflController.render();
    var groupedHtml = tocflRoles.results.innerHTML;
    var headKeys = [];
    var headPattern = /data-tocfl-category="([^"]+)"/g;
    var headMatch;
    while ((headMatch = headPattern.exec(groupedHtml))) headKeys.push(headMatch[1]);
    var headSeen = {};
    var headContiguous = headKeys.length > 0;
    headKeys.forEach(function (key) {
      if (headSeen[key]) headContiguous = false;
      headSeen[key] = true;
    });
    report.tocflGroups = {
      heads: (groupedHtml.match(/vocab-group__head/g) || []).length,
      counted: groupedHtml.indexOf("vocab-group__count") !== -1,
      knownCategories: headKeys.length > 0 && headKeys.every(function (key) {
        return key in categoryCounts;
      }),
      contiguous: headContiguous
    };
    if (tocflClick) {
      tocflClick({ target: tocflChip("data-tocfl-level", "level-3") });
      var pickedLevel3Category = Object.keys(tocflController.categoryCounts())[0];
      tocflClick({ target: tocflChip("data-tocfl-category", pickedLevel3Category) });
      var level3Shown = tocflController.filteredWords();
      var pickedLevel3Subcategory = Object.keys(tocflController.subcategoryCounts())[0];
      tocflClick({ target: tocflChip("data-tocfl-subcategory", pickedLevel3Subcategory) });
      var level3Subset = tocflController.filteredWords();
      report.tocflClickFlow = {
        level: tocflController.level,
        category: tocflController.category,
        countText: tocflRoles.count.textContent,
        categoryExact: level3Shown.length > 0 && level3Shown.every(function (word) {
          return word.level === "level-3" && word.category === pickedLevel3Category;
        }),
        subcategoryExact: level3Subset.length > 0 && level3Subset.every(function (word) {
          return word.level === "level-3" &&
            word.category === pickedLevel3Category &&
            (word.subcategory || word.category) === pickedLevel3Subcategory;
        }),
        countMatches: tocflRoles.count.textContent ===
          level3Subset.length + " word" + (level3Subset.length === 1 ? "" : "s")
      };
    }
  } catch (e) {
    report.errors.push("TOCFL renderer: " + e);
  }
}
report.hskDuplicateExtras = 0;
report.haiFamily = [];
if (report.storeLoaded) {
  var seenWords = {};
  window.VocabStore.all().forEach(function (word) {
    var level = window.VocabStore.hskValue(word);
    if (!/^[1-6]$/.test(level)) return;
    var key = String(word.traditional || "").replace(/\s+/g, "") + "\u001f" +
      String(word.simplified || "").replace(/\s+/g, "") + "\u001f" +
      window.VocabStore.fold(word.pinyin).replace(/\s+/g, "");
    if (seenWords[key]) report.hskDuplicateExtras += 1;
    else seenWords[key] = true;
  });
  report.haiFamily = window.VocabStore.filter({ hsk: "1", sort: "smart" })
    .filter(function (word) {
      return word.traditional === "還" || word.traditional.indexOf("還") === 0;
    })
    .map(function (word) { return word.pinyin; });
}

try { window.VocabularyUI.onView("browse"); } catch (e) { report.errors.push("browse: " + e); }
report.browseHtml = html("browse-results").length;
report.browseCount = text("browse-result-count");
report.browseSerials = (html("browse-results").match(/vocab-list__serial/g) || []).length;
report.browsePagination = html("browse-pagination");
report.browseHasLevelCol = html("browse-results").indexOf("Level & category") !== -1;
report.browseHasScriptCaption = html("browse-results").indexOf("script-block__label") !== -1;
report.browseHasActionsCol = html("browse-results").indexOf("vocab-list__actions") !== -1;
report.browseWordButtons = (html("browse-results").match(/vocab-list__word /g) || []).length;

report.levels = {};
var views = ["hsk1", "hsk2", "hsk3", "hsk4", "hsk5", "hsk6", "hsk-other"];
for (var i = 0; i < views.length; i++) {
  try {
    window.VocabularyUI.onView(views[i]);
    var levelHtml = html("level-results");
    var headKeys = [];
    var headPattern = /data-open-level-category="([^"]+)"/g;
    var headMatch;
    while ((headMatch = headPattern.exec(levelHtml))) headKeys.push(headMatch[1]);
    var headSeen = {};
    var headContiguous = headKeys.length > 0;
    headKeys.forEach(function (key) {
      if (headSeen[key]) headContiguous = false;
      headSeen[key] = true;
    });
    report.levels[views[i]] = {
      title: text("level-title"),
      subtitle: text("level-subtitle"),
      count: text("level-result-count"),
      results: levelHtml.length,
      resultsHtml: levelHtml.slice(0, 400),
      serials: (levelHtml.match(/vocab-list__serial/g) || []).length,
      pagination: html("level-pagination"),
      categories: html("level-categories").length,
      categoriesHtml: html("level-categories").slice(0, 180),
      switcher: html("level-switch").length,
      groupHeads: (levelHtml.match(/vocab-group__head/g) || []).length,
      groupCounted: levelHtml.indexOf("vocab-group__count") !== -1,
      groupContiguous: headContiguous
    };
  } catch (e) {
    report.errors.push(views[i] + ": " + e);
  }
}

try {
  window.AppRouter.go("tocfl", true);
  report.tocflRouteVisible = !document.getElementById("app-view-tocfl").classList.contains("hidden");
  window.AppRouter.go("pronounce", true);
  report.pronounceRouteVisible = !document.getElementById("app-view-pronounce").classList.contains("hidden");
} catch (e) {
  report.errors.push("TOCFL routes: " + e);
}

/* An Android file manager serves the page from a content:// URI whose access
   grant dies with the first URL change, so views must switch in place there. */
report.sandboxedNav = { detected: false, hashUntouched: false, viewSwitched: false };
try {
  var savedProtocol = window.location.protocol;
  var savedHash = window.location.hash;
  window.location.protocol = "content:";
  window.location.hash = "#sentinel";
  report.sandboxedNav.detected = window.ChineseOffline
    ? window.ChineseOffline.isSandboxed()
    : true;
  window.AppRouter.go("tocfl", false);
  report.sandboxedNav.hashUntouched = window.location.hash === "#sentinel";
  report.sandboxedNav.viewSwitched =
    !document.getElementById("app-view-tocfl").classList.contains("hidden");
  window.location.protocol = savedProtocol;
  window.location.hash = savedHash;
  if (window.ChineseOffline && window.ChineseOffline.isSandboxed()) {
    report.errors.push("file:// documents must not be treated as sandboxed");
  }
} catch (e) {
  report.errors.push("sandboxed navigation: " + e);
}

try { window.VocabularyUI.onView("learn"); } catch (e) { report.errors.push("learn: " + e); }
report.learnHtml = html("learn-card").length;

try { window.VocabularyUI.onView("progress"); } catch (e) { report.errors.push("progress: " + e); }
report.progressHtml = html("progress-hsk").length;

try { window.VocabularyUI.onView("home"); } catch (e) { report.errors.push("home: " + e); }
report.homeStats = text("dashboard-simple-stats");

JSON.stringify(report);
"""


def main() -> None:
    payload = sample_payload()
    source = [
        DOM_SHIM,
        "window.__VOCAB_MASTER__ = " + json.dumps(payload, ensure_ascii=False) + ";",
        (ROOT / "data" / "tocfl-8000.js").read_text(encoding="utf-8"),
        (ROOT / "data" / "tocfl-cccc.js").read_text(encoding="utf-8"),
    ]
    for module in MODULES:
        source.append(f"/* {module} */\n" + (ROOT / module).read_text(encoding="utf-8"))
    source.append(PROBE)

    try:
        report = json.loads(dukpy.evaljs("\n;\n".join(source)))
    except dukpy.JSRuntimeError as error:
        print("FAIL: JavaScript threw while loading the app modules")
        print(error)
        sys.exit(1)

    for message in report.get("errors", []):
        failures.append(message)
        print("FAIL:", message)

    check(report["storeLoaded"], "VocabStore initialised")
    check(report["uiLoaded"], "VocabularyUI initialised")
    check(report["tocflUiLoaded"], "TocflUI initialised")
    check(report["localStoragePersists"], "learning state persists in localStorage")
    check(report["totalWords"] > 0, f"store exposes words ({report['totalWords']})")
    check(report["tocflA1Words"] > 0, f"store filters TOCFL A1 words ({report['tocflA1Words']})")
    check(report["tocflCounts"].get("A2", 0) > 0, "store counts TOCFL A2 words")
    check(report["tocfl8000Words"] == 7517, "all 7,517 TOCFL workbook rows are loaded")
    check(report["ccccWords"] == 1197, "all 1,197 CCCC workbook rows are loaded")
    check(report["tocflCombinedLevels"] == 10, "TOCFL renders all ten workbook levels")
    check(report["tocflLevelSizes"]["novice-1"] == 160, "Novice 1 keeps its first-occurrence 160 words")
    check(report["tocflLevelSizes"]["novice-2"] == 234, "Novice 2 keeps its first-occurrence 234 words")
    check(report["tocflLevelSizes"]["level-1"] == 345, "Level 1 drops later repeats of the same word")
    check(report["tocflUniqueDuplicates"] == 0, "no unique Chinese+pinyin word is shown twice")
    check(report["tocflUniqueTotal"] == 7477, f"deduplicated TOCFL+CCCC list has 7,477 unique words ({report['tocflUniqueTotal']})")
    check(len(report["tocflLevelSizes"]) == 10, "all ten levels still have unique words")
    check(report["tocflRender"]["levelWordCount"] == 160, "selected Novice 1 remains limited to 160 words")
    check(report["tocflRender"]["categoryCountMatches"], "selected category count matches its actual words")
    check(report["tocflRender"]["categoryExact"], "selected category contains no other level or category")
    check(report["tocflRender"]["subcategories"] > 0, "selected category renders only its subcategories")
    check(report["tocflRender"]["subcategoryCountMatches"], "selected subcategory count matches displayed words")
    check(report["tocflRender"]["subcategoryExact"], "subcategory filter applies level AND category AND subcategory")
    check(report["tocflClickFlow"]["level"] == "level-3", "clicking a category keeps the chosen level (Level 3)")
    check(report["tocflClickFlow"]["countText"] != "160 words", "Level 3 no longer falls back to the 160 Novice 1 words")
    check(report["tocflClickFlow"]["categoryExact"], "category clicked inside Level 3 shows only Level 3 words")
    check(report["tocflClickFlow"]["subcategoryExact"], "subcategory clicked inside Level 3 stays in that category")
    check(report["tocflClickFlow"]["countMatches"], "displayed count matches the clicked category selection")
    check(report["tocflRender"]["categories"] > 0, "TOCFL renders category chips")
    check(report["tocflRender"]["results"] > 0, f"TOCFL renders words ({report['tocflRender']['count']})")
    check(report["hskDuplicateExtras"] == 0, "HSK 1–6 contains no duplicate Chinese+pinyin entries")
    check(report["browseHtml"] > 0, f"Browse renders markup ({report['browseHtml']} chars)")
    check(not report["browseCount"].startswith("0 "), f"Browse word count: {report['browseCount']}")
    check(report["browseSerials"] <= 50, f"Browse limits each page to 50 words ({report['browseSerials']})")
    check("Page 1 of" in report["browsePagination"], "Browse renders page navigation")
    check(not report.get("browseHasLevelCol"), "Browse word list does not include Level & category")
    check(not report.get("browseHasScriptCaption"), "word list drops the 繁體/简体 captions")
    check(not report.get("browseHasActionsCol"), "word list does not include an Actions column")
    check(report.get("browseWordButtons", 0) > 0, "word list still renders tappable script buttons")

    for view, data in report["levels"].items():
        check(data["results"] > 0, f"{view} renders words ({data['count']})")
        check(data["categories"] > 0, f"{view} renders its own categories")
        check("topic-chip" in data.get("categoriesHtml", ""), f"{view} uses compact topic chips")
        check(data["switcher"] > 0, f"{view} renders the level switcher")
        check(data["serials"] <= 50, f"{view} limits each page to 50 numbered words")
        check(
            not data["count"].startswith("0 "),
            f"{view} title '{data['title']}' — {data['subtitle']}",
        )
        check("empty-state" not in data["resultsHtml"], f"{view} shows real words, not an empty state")
        check(data["groupHeads"] > 0, f"{view} groups words under category headings ({data['groupHeads']})")
        check(data["groupCounted"], f"{view} category headings show a word count")
        check(data["groupContiguous"], f"{view} each category heading appears once per page")

    check(report.get("tocflRouteVisible"), "Router opens the TOCFL category page")
    check(report.get("pronounceRouteVisible"), "Router opens TOCFL pronunciation")
    check(report["tocflGroups"]["heads"] > 0, f"TOCFL groups words under category headings ({report['tocflGroups']['heads']})")
    check(report["tocflGroups"]["knownCategories"], "each TOCFL heading names a real category of the level")
    check(report["tocflGroups"]["contiguous"], "each TOCFL category heading appears once per page")
    check(report["tocflGroups"]["counted"], "each TOCFL heading shows its word count")
    check(report["sandboxedNav"]["detected"], "content:// documents are detected as sandboxed")
    check(report["sandboxedNav"]["hashUntouched"], "sandboxed navigation leaves the URL alone")
    check(report["sandboxedNav"]["viewSwitched"], "sandboxed navigation still switches the view")
    check(report["learnHtml"] > 0, "Learn renders a card")
    check(report["progressHtml"] > 0, "Progress renders HSK rows")
    check(bool(report["homeStats"]), f"Home stats: {report['homeStats']}")

    if failures:
        print(f"\n{len(failures)} check(s) FAILED.")
        sys.exit(1)
    print("\nAll UI smoke checks PASSED.")


if __name__ == "__main__":
    main()
