# -*- coding: utf-8 -*-
"""Run the real browser modules against a minimal DOM so blank screens fail the build."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import dukpy

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "vocabulary-master.json"
MODULES = [
    "js/learning-state.js",
    "js/vocab-store.js",
    "js/tocfl-store.js",
    "js/vocabulary-ui.js",
    "js/tocfl-ui.js",
    "js/categories-ui.js",
    "js/characters-ui.js",
    "js/app-router.js",
]
SAMPLE_PER_LEVEL = 40

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

failures: list[str] = []


MARKED_LETTER = {
    "ā": "a1", "á": "a2", "ǎ": "a3", "à": "a4",
    "ē": "e1", "é": "e2", "ě": "e3", "è": "e4",
    "ī": "i1", "í": "i2", "ǐ": "i3", "ì": "i4",
    "ō": "o1", "ó": "o2", "ǒ": "o3", "ò": "o4",
    "ū": "u1", "ú": "u2", "ǔ": "u3", "ù": "u4",
    "ǖ": "u1", "ǘ": "u2", "ǚ": "u3", "ǜ": "u4", "ü": "u5",
    "ń": "n2", "ň": "n3", "ǹ": "n4", "ḿ": "m2",
}
SYLLABLE_LIST = (
    "a ai an ang ao ba bai ban bang bao bei ben beng bi bian biao bie bin bing bo bu "
    "ca cai can cang cao ce cen ceng cha chai chan chang chao che chen cheng chi chong chou chu chua chuai chuan chuang chui chun chuo ci cong cou cu cuan cui cun cuo "
    "da dai dan dang dao de dei den deng di dia dian diao die ding diu dong dou du duan dui dun duo "
    "e ei en eng er fa fan fang fei fen feng fo fou fu "
    "ga gai gan gang gao ge gei gen geng gong gou gu gua guai guan guang gui gun guo "
    "ha hai han hang hao he hei hen heng hm hng hong hou hu hua huai huan huang hui hun huo "
    "ji jia jian jiang jiao jie jin jing jiong jiu ju juan jue jun "
    "ka kai kan kang kao ke kei ken keng kong kou ku kua kuai kuan kuang kui kun kuo "
    "la lai lan lang lao le lei leng li lia lian liang liao lie lin ling liu lo long lou lu luan lue lun luo "
    "m ma mai man mang mao me mei men meng mi mian miao mie min ming miu mo mou mu "
    "n na nai nan nang nao ne nei nen neng ng ni nian niang niao nie nin ning niu nong nou nu nuan nue nun nuo "
    "o ou pa pai pan pang pao pei pen peng pi pian piao pie pin ping po pou pu "
    "qi qia qian qiang qiao qie qin qing qiong qiu qu quan que qun "
    "ran rang rao re ren reng ri rong rou ru rua ruan rui run ruo "
    "sa sai san sang sao se sen seng sha shai shan shang shao she shei shen sheng shi shou shu shua shuai shuan shuang shui shun shuo si song sou su suan sui sun suo "
    "ta tai tan tang tao te teng ti tian tiao tie ting tong tou tu tuan tui tun tuo "
    "wa wai wan wang wei wen weng wo wu "
    "xi xia xian xiang xiao xie xin xing xiong xiu xu xuan xue xun "
    "ya yai yan yang yao ye yi yin ying yo yong you yu yuan yue yun "
    "za zai zan zang zao ze zei zen zeng zha zhai zhan zhang zhao zhe zhei zhen zheng zhi zhong zhou zhu zhua zhuai zhuan zhuang zhui zhun zhuo zi zong zou zu zuan zui zun zuo"
).split()
SYLLABLE_SET = set(SYLLABLE_LIST)
EXPECTED_SPELLING = [
    "安定\t安定\tāndìng",
    "安頓\t安顿\tāndùn",
    "安撫\t安抚\tānfǔ",
    "骯髒\t肮脏\tāngzāng",
    "昂貴\t昂贵\tángguì",
]


def read_chunk(chunk: str) -> tuple[str, list[str]]:
    letters = []
    tones: list[str] = []
    value = chunk.strip().lower().replace("u:", "u")
    for ch in value:
        marked = MARKED_LETTER.get(ch)
        if marked:
            letters.append(marked[0])
            tones.append(marked[1])
            continue
        if ch == "v":
            letters.append("u")
            tones.append("5")
            continue
        if "a" <= ch <= "z":
            letters.append(ch)
            tones.append("5")
            continue
        if ch in "12345" and tones:
            tones[-1] = ch
    return "".join(letters), tones


def erhua_count(items: list[tuple[str, str]]) -> int:
    count = 0
    for part, _tone in items:
        stem = part[:-1]
        if part.endswith("r") and stem in SYLLABLE_SET and part not in SYLLABLE_SET:
            count += 1
    return count


def segment_syllables(letters: str, tones: list[str]) -> list[tuple[str, str]]:
    limit = len(letters)
    seen = [False] * (limit + 1)
    memo: list[list[tuple[str, str]] | None] = [None] * (limit + 1)

    def solve(index: int) -> list[tuple[str, str]] | None:
        if index == limit:
            return []
        if seen[index]:
            return memo[index]
        seen[index] = True
        best: list[tuple[str, str]] | None = None
        best_erhua = 0
        for length in range(min(6, limit - index), 0, -1):
            part = letters[index:index + length]
            stem = part[:-1] if part.endswith("r") else ""
            if part not in SYLLABLE_SET and stem not in SYLLABLE_SET:
                continue
            tone = "5"
            tone_count = 0
            for cursor in range(index, index + length):
                if tones[cursor] != "5":
                    tone_count += 1
                    if tone == "5":
                        tone = tones[cursor]
            if tone_count > 1:
                continue
            rest = solve(index + length)
            if rest is None:
                continue
            candidate = [(part, tone), *rest]
            candidate_erhua = erhua_count(candidate)
            if (
                best is None
                or len(candidate) < len(best)
                or (len(candidate) == len(best) and candidate_erhua < best_erhua)
            ):
                best = candidate
                best_erhua = candidate_erhua
        memo[index] = best
        return best

    parsed = solve(0)
    if parsed is not None:
        return parsed
    tone = next((item for item in tones if item != "5"), "5")
    return [(letters, tone)]


def syllable_key(pinyin: str) -> tuple[tuple[str, str], ...]:
    primary = (pinyin or "").split("/")[0].strip()
    syllables: list[tuple[str, str]] = []
    for chunk in [part for part in re.split(r"[\s'’·]+", primary) if part]:
        letters, tones = read_chunk(chunk)
        if letters:
            syllables.extend(segment_syllables(letters, tones))
    return tuple(syllables)


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
window.__spokenUtterances = [];
window.speechSynthesis = {
  cancel: function () {},
  getVoices: function () { return [{ lang: "zh-TW", name: "Taiwan Mandarin" }]; },
  speak: function (utterance) { window.__spokenUtterances.push(utterance); }
};
function SpeechSynthesisUtterance(text) { this.text = text; }
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
report.charactersUiLoaded = !!window.CharactersUI;
report.characterCount = window.CharactersUI ? window.CharactersUI.count : 0;
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
report.tocflVariantMerge = { sameWord: false, differentReading: false };
report.tocflUniqueTotal = 0;
report.tocflUniqueDuplicates = 0;
report.tocflAllLevelsSorted = true;
report.tocflLevelAssignmentCorrect = true;
report.totalWords = report.storeLoaded ? window.VocabStore.all().length : 0;
report.duplicatesRemoved = report.storeLoaded ? window.VocabStore.duplicateCount : 0;
report.tocflCounts = report.storeLoaded ? window.VocabStore.tocflCounts() : {};
report.tocflA1Words = report.storeLoaded ? window.VocabStore.filter({ tocfl: "A1" }).length : 0;
report.tocflEntryLevel = {
  buttons: 0, titled: false, hidesMergedButtons: false, keepsLater: false,
  onlyEntry: false, coversEach: false
};
report.tocflRender = {
  levels: 0, categories: 0, subcategories: 0, results: 0, count: "",
  levelWordCount: 0, categoryCountMatches: false, categoryExact: false,
  subcategoryCountMatches: false, subcategoryExact: false
};
report.tocflClickFlow = {
  level: "", category: "", countText: "",
  categoryExact: false, subcategoryExact: false, countMatches: false
};
report.tocflGroups = {
  heads: 0, pinyinSorted: false, numberingContinuous: false
};
report.categoriesRender = {
  taxonomy: 0, cards: 0, dynamicCounts: false, uniqueWords: 0,
  duplicatesMerged: 0, strictSources: false, categoryExact: false,
  prioritySorted: false, traditionalSearch: false, pinyinSearch: false,
  englishSearch: false, sourceMetadata: false, mergedSource: false,
  pagination: false, detailVisible: false, routeVisible: false
};
report.characterRender = {
  levels: 0, tiles: 0, count: "", details: 0,
  traditionalAudio: false, simplifiedDetails: false, exactSpeech: false, taiwanVoice: false,
  levelCounts: [], clickCounts: [], pinyinLevelSorted: [], renderedPinyinSorted: false
};
report.characterDiff = {
  title: "", subtitle: "", count: 0, expected: 0, allDifferent: false,
  levelsHidden: false, pinyinSorted: false, sampleDifferent: false
};
report.characterColumns = { controls: false, hides: false, rowShows: false, rowReveal: false };
if (window.CharactersUI && window.CharactersUI.mount) {
  var characterRoles = {};
  ["title", "subtitle", "levels", "search", "count", "grid", "pagination", "details", "details-content", "details-close"]
    .forEach(function (role) { characterRoles[role] = makeEl("character-" + role); });
  characterRoles.details.classList.add("hidden");
  var characterRoot = makeEl("character-smoke-root");
  characterRoot.getAttribute = function (name) { return name === "data-character-level" ? "1000" : null; };
  characterRoot.querySelector = function (selector) {
    var match = selector.match(/data-character-role="([^"]+)"/);
    return match ? characterRoles[match[1]] : null;
  };
  var characterClick = null;
  characterRoot.addEventListener = function (type, handler) {
    if (type === "click") characterClick = handler;
  };
  try {
    var characterController = window.CharactersUI.mount(characterRoot);
    characterController.openDetails(window.__CHARACTERS__.characters[0]);
    var initialCharacterCount = characterRoles.count.textContent;
    var initialCharacterGrid = characterRoles.grid.innerHTML;
    window.CharactersUI.speak(window.__CHARACTERS__.characters[0].traditional);
    var spokenCharacter = window.__spokenUtterances[window.__spokenUtterances.length - 1] || {};
    var characterPinyinSorted = [];
    var characterLevelCounts = ["1000", "2000", "3000"].map(function (level) {
      characterController.level = level;
      var levelCharacters = characterController.filtered();
      characterPinyinSorted.push(pinyinAscending(levelCharacters.map(function (item) {
        return item.pinyin;
      })));
      return levelCharacters.length;
    });
    var renderedCharacterPinyin = [];
    var characterPinyinPattern = /class="character-list__pinyin"[^>]*>([\s\S]*?)<\/td>/g;
    var characterPinyinMatch;
    while ((characterPinyinMatch = characterPinyinPattern.exec(initialCharacterGrid))) {
      renderedCharacterPinyin.push(characterPinyinMatch[1].replace(/<[^>]*>/g, "").trim());
    }
    characterController.level = "1000";
    var characterClickCounts = [];
    ["2000", "3000"].forEach(function (levelId) {
      var chip = {
        getAttribute: function (name) { return name === "data-character-level" ? levelId : null; },
        closest: function (selector) { return selector === "[data-character-level]" ? this : null; }
      };
      characterClick({ target: chip });
      characterClickCounts.push(characterRoles.count.textContent);
    });
    report.characterRender = {
      levels: (characterRoles.levels.innerHTML.match(/data-character-level=/g) || []).length,
      tiles: (characterRoles.grid.innerHTML.match(/character-list__rank/g) || []).length,
      count: initialCharacterCount,
      details: characterRoles["details-content"].innerHTML.length,
      traditionalAudio: characterRoles.grid.innerHTML.indexOf("character-list__han--traditional") !== -1 &&
        characterRoles.grid.innerHTML.indexOf("data-character-speak=") !== -1,
      simplifiedDetails: characterRoles.grid.innerHTML.indexOf("character-list__han--simplified") !== -1 &&
        characterRoles.grid.innerHTML.indexOf("data-character-details=") !== -1,
      exactSpeech: spokenCharacter.text === window.__CHARACTERS__.characters[0].traditional,
      taiwanVoice: spokenCharacter.lang === "zh-TW" && spokenCharacter.voice &&
        spokenCharacter.voice.lang === "zh-TW",
      levelCounts: characterLevelCounts,
      clickCounts: characterClickCounts,
      pinyinLevelSorted: characterPinyinSorted,
      renderedPinyinSorted: renderedCharacterPinyin.length === 50 &&
        pinyinAscending(renderedCharacterPinyin) &&
        /character-list__rank"[^>]*>1</.test(initialCharacterGrid)
    };
    var expectedDiff = window.__CHARACTERS__.characters.filter(function (item) {
      return String(item.traditional || "") !== String(item.simplified || "");
    }).length;
    var diffRoles = {};
    ["title", "subtitle", "levels", "search", "count", "grid", "pagination", "details", "details-content", "details-close"]
      .forEach(function (role) { diffRoles[role] = makeEl("character-diff-" + role); });
    var diffRoot = makeEl("character-diff-root");
    diffRoot.hasAttribute = function (name) { return name === "data-character-diff"; };
    diffRoot.getAttribute = function () { return null; };
    diffRoot.querySelector = function (selector) {
      var match = selector.match(/data-character-role="([^"]+)"/);
      return match ? diffRoles[match[1]] : null;
    };
    var diffController = window.CharactersUI.mount(diffRoot);
    var diffList = diffController.filtered();
    report.characterDiff = {
      title: diffRoles.title.textContent,
      subtitle: diffRoles.subtitle.textContent,
      count: diffList.length,
      expected: expectedDiff,
      allDifferent: diffList.every(function (item) {
        return item.traditional !== item.simplified;
      }),
      levelsHidden: diffRoles.levels.classList.contains("hidden") && diffRoles.levels.innerHTML === "",
      pinyinSorted: pinyinAscending(diffList.map(function (item) { return item.pinyin; })),
      sampleDifferent: diffList.length > 0 &&
        diffRoles.grid.innerHTML.indexOf("character-list__han--traditional") !== -1 &&
        diffRoles.grid.innerHTML.indexOf("character-list__han--simplified") !== -1
    };
    window.CharactersUI.setColumn("pinyin", false);
    window.CharactersUI.setColumn("meaning", false);
    var firstCharacterId = (characterRoles.grid.innerHTML.match(/data-character-id="([^"]+)"/) || [])[1];
    report.characterColumns = {
      controls: characterRoles.grid.innerHTML.indexOf(">Hide Word<") !== -1 &&
        characterRoles.grid.innerHTML.indexOf(">Show Pinyin<") !== -1 &&
        characterRoles.grid.innerHTML.indexOf(">Show Meaning<") !== -1,
      hides: characterRoles.grid.innerHTML.indexOf("is-col-pinyin-hidden") !== -1 &&
        characterRoles.grid.innerHTML.indexOf("is-col-meaning-hidden") !== -1,
      rowShows: (characterRoles.grid.innerHTML.match(/data-character-row-show="pinyin"/g) || []).length === 50 &&
        characterRoles.grid.innerHTML.indexOf("vocab-list__row-actions") !== -1,
      rowReveal: false
    };
    window.CharactersUI.setColumn("word", false);
    firstCharacterId = (characterRoles.grid.innerHTML.match(/data-character-id="([^"]+)"/) || [])[1];
    if (firstCharacterId) {
      characterClick({
        target: {
          closest: function (selector) {
            if (selector === "[data-character-row-show]") {
              return {
                getAttribute: function (name) {
                  if (name === "data-character-id") return firstCharacterId;
                  if (name === "data-character-row-show") return "word";
                  return null;
                }
              };
            }
            return null;
          }
        }
      });
      report.characterColumns.rowReveal =
        characterRoles.grid.innerHTML.indexOf("is-showing-word") !== -1 &&
        characterRoles.grid.innerHTML.indexOf('data-character-row="' + firstCharacterId + '"') !== -1;
    }
    window.CharactersUI.setColumn("word", true);
    window.CharactersUI.setColumn("pinyin", true);
    window.CharactersUI.setColumn("meaning", true);
  } catch (e) {
    report.errors.push("character renderer: " + e);
  }
}
if (window.CategoriesUI && window.CategoriesUI.mount && window.TocflStore) {
  var categoryRoles = {};
  ["title", "subtitle", "landing", "detail", "grid", "detail-title", "detail-icon",
    "search", "source", "level", "count", "results", "pagination"]
    .forEach(function (role) { categoryRoles[role] = makeEl("categories-" + role); });
  categoryRoles.detail.classList.add("hidden");
  categoryRoles.source.value = "all";
  categoryRoles.level.value = "all";
  var categoriesRoot = makeEl("categories-smoke-root");
  categoriesRoot.getAttribute = function () { return null; };
  categoriesRoot.querySelector = function (selector) {
    var match = selector.match(/data-categories-role="([^"]+)"/);
    return match ? categoryRoles[match[1]] : null;
  };
  try {
    var categoriesController = window.CategoriesUI.mount(categoriesRoot);
    var categoryCounts = window.TocflStore.categoryCounts();
    var countTotal = Object.keys(categoryCounts).reduce(function (sum, key) {
      return sum + categoryCounts[key];
    }, 0);
    var biggest = window.CategoriesUI.taxonomy.slice().sort(function (a, b) {
      return (categoryCounts[b.label] || 0) - (categoryCounts[a.label] || 0);
    })[0];
    categoriesController.open(biggest.slug, { fromRouter: true });
    var categoryWords = categoriesController.filtered();
    var firstCategoryWord = categoryWords[0];
    var prioritySorted = true;
    for (var categoryIndex = 1; categoryIndex < categoryWords.length; categoryIndex += 1) {
      if (window.TocflStore.comparePriority(categoryWords[categoryIndex - 1], categoryWords[categoryIndex]) > 0) {
        prioritySorted = false;
        break;
      }
    }
    categoryRoles.search.value = firstCategoryWord.traditional;
    var traditionalSearch = categoriesController.filtered().some(function (word) {
      return word.id === firstCategoryWord.id;
    });
    categoryRoles.search.value = firstCategoryWord.pinyin;
    var pinyinSearch = categoriesController.filtered().some(function (word) {
      return word.id === firstCategoryWord.id;
    });
    categoryRoles.search.value = firstCategoryWord.english;
    var englishSearch = categoriesController.filtered().some(function (word) {
      return word.id === firstCategoryWord.id;
    });
    categoryRoles.search.value = "";
    categoriesController.renderResults();
    var allCategoryWords = window.TocflStore.all();
    if (window.AppRouter && window.AppRouter.goCategory) {
      window.AppRouter.goCategory(biggest.slug, true);
    }
    report.categoriesRender = {
      taxonomy: window.CategoriesUI.taxonomy.length,
      cards: (categoryRoles.grid.innerHTML.match(/data-category-slug=/g) || []).length,
      dynamicCounts: countTotal === allCategoryWords.length,
      uniqueWords: allCategoryWords.length,
      duplicatesMerged: window.TocflStore.duplicateCount,
      strictSources: allCategoryWords.every(function (word) {
        return (word.sources || []).length > 0 &&
          (word.sources || []).every(function (source) {
            return source === "TOCFL" || source === "CCCC";
          });
      }),
      categoryExact: categoryWords.every(function (word) { return word.category === biggest.label; }),
      prioritySorted: prioritySorted,
      traditionalSearch: traditionalSearch,
      pinyinSearch: pinyinSearch,
      englishSearch: englishSearch,
      sourceMetadata: categoryRoles.results.innerHTML.indexOf("source-badge") >= 0,
      mergedSource: allCategoryWords.some(function (word) {
        return word.sourceLabel === "TOCFL + CCCC";
      }),
      pagination: categoryRoles.pagination.innerHTML.indexOf("Page 1 of") >= 0,
      detailVisible: !categoryRoles.detail.classList.contains("hidden") &&
        categoryRoles.landing.classList.contains("hidden"),
      routeVisible: !document.getElementById("app-view-categories").classList.contains("hidden")
    };
  } catch (e) {
    report.errors.push("categories renderer: " + e);
  }
}
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
    var tocflCatalog = window.TocflStore.all();
    ["novice-1", "novice-2", "level-1", "level-2", "level-3", "level-4", "level-5", "sprouting", "growing", "thriving"].forEach(function (level) {
      var levelWords = window.VocabStore.pinyinOrder(tocflCatalog.filter(function (word) { return word.level === level; }));
      report.tocflLevelSizes[level] = levelWords.length;
      if (!pinyinAscending(levelWords.map(function (word) { return word.pinyin; }))) {
        report.tocflAllLevelsSorted = false;
      }
      if (!levelWords.every(function (word) { return word.level === level; })) {
        report.tocflLevelAssignmentCorrect = false;
      }
    });
    var troubleLow = window.TocflStore.byId("cccc-thriving-0885");
    var troubleHigh = window.TocflStore.byId("tocfl8k-level-3-01793");
    var haoLow = window.TocflStore.byId("tocfl8k-novice-1-00070");
    var haoHigh = window.TocflStore.byId("tocfl8k-level-3-01559");
    var entryBand = { "novice-1": 1, "novice-2": 1, "level-1": 1, sprouting: 1, growing: 1, thriving: 1 };
    report.tocflVariantMerge = {
      sameWord: !!(troubleLow && troubleHigh && troubleLow.id === troubleHigh.id && entryBand[troubleLow.level]),
      differentReading: !!(haoLow && haoHigh && haoLow.id !== haoHigh.id)
    };
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
    var entryIds = ["novice-1", "novice-2", "level-1", "sprouting", "growing", "thriving"];
    tocflController.level = "entry-level";
    var entryWords = tocflController.wordsForLevel();
    report.tocflEntryLevel = {
      buttons: (tocflRoles.levels.innerHTML.match(/data-tocfl-level=/g) || []).length,
      titled: tocflRoles.levels.innerHTML.indexOf("入門級 · Level 1") !== -1,
      hidesMergedButtons: entryIds.every(function (id) {
        return tocflRoles.levels.innerHTML.indexOf('data-tocfl-level="' + id + '"') === -1;
      }),
      keepsLater: ["level-2", "level-3", "level-4", "level-5"].every(function (id) {
        return tocflRoles.levels.innerHTML.indexOf('data-tocfl-level="' + id + '"') !== -1;
      }),
      onlyEntry: entryWords.length > 0 && entryWords.every(function (word) {
        return entryIds.indexOf(word.level) >= 0;
      }),
      coversEach: entryIds.every(function (id) {
        return entryWords.some(function (word) { return word.level === id; });
      })
    };
    tocflController.level = "novice-1";
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
      pinyinSorted: pinyinAscending(renderedPinyin(groupedHtml)),
      numberingContinuous: serialsContinuous(groupedHtml)
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
    var flatRoles = {};
    ["title", "subtitle", "levels", "categories", "search", "status", "count", "results", "pagination"]
      .forEach(function (role) { flatRoles[role] = makeEl("tocfl8000-" + role); });
    flatRoles.status.value = "all";
    var flatRoot = makeEl("tocfl-8000-root");
    flatRoot.hasAttribute = function (name) { return name === "data-tocfl-8000"; };
    flatRoot.getAttribute = function () { return null; };
    flatRoot.querySelector = function (selector) {
      var match = selector.match(/data-tocfl-role="([^"]+)"/);
      return match ? flatRoles[match[1]] : null;
    };
    flatRoot.addEventListener = function () {};
    var flatController = window.TocflUI.mount(flatRoot);
    var flatWords = flatController.wordsForLevel();
    report.tocfl8000 = {
      title: flatRoles.title.textContent,
      subtitle: flatRoles.subtitle.textContent,
      count: flatWords.length,
      levelsHidden: flatRoles.levels.innerHTML.length === 0,
      pinyinSorted: pinyinAscending(flatWords.map(function (word) { return word.pinyin; })),
      onlyTocfl: flatWords.every(function (word) {
        return /^(novice-[12]|level-[1-5])$/.test(word.level);
      }),
      largeBands: (function () {
        var counts = flatController.categoryCounts();
        function stats(prefixes) {
          var bands = Object.keys(counts).filter(function (label) {
            return prefixes.some(function (prefix) { return label.indexOf(prefix) === 0; });
          });
          return {
            count: bands.length,
            min: bands.reduce(function (min, label) {
              return Math.min(min, counts[label] || 0);
            }, bands.length ? Infinity : 0)
          };
        }
        return {
          sized: stats(["Nouns · ", "Action Verbs · ", "Adjectives · "]),
          adverbs: stats(["Adverbs · "])
        };
      })()
    };
  } catch (e) {
    report.errors.push("TOCFL renderer: " + e);
  }
}
report.hskDuplicateExtras = 0;
report.hskAllLevelsSorted = true;
report.hskLevelAssignmentCorrect = true;
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
  ["1", "2", "3", "4", "5", "6", "outside-hsk"].forEach(function (level) {
    var levelWords = window.VocabStore.filter({ hsk: level, sort: "pinyin" });
    if (!pinyinAscending(levelWords.map(function (word) { return word.pinyin; }))) {
      report.hskAllLevelsSorted = false;
    }
    if (!levelWords.every(function (word) {
      return window.VocabStore.hskValue(word) === level;
    })) {
      report.hskLevelAssignmentCorrect = false;
    }
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
report.browseSerials = (html("browse-results").match(/class="vocab-list__serial"/g) || []).length;
report.browsePagination = html("browse-pagination");
report.browseHasLevelCol = html("browse-results").indexOf("Level & category") !== -1;
report.browseHasScriptCaption = html("browse-results").indexOf("script-block__label") !== -1;
report.browseHasActionsCol = html("browse-results").indexOf("vocab-list__actions") !== -1;
report.browseWordButtons = (html("browse-results").match(/vocab-list__word /g) || []).length;
report.browseTraditionalAudio =
  html("browse-results").indexOf('data-word-action="listen"') !== -1 &&
  html("browse-results").indexOf("data-speak-text=") !== -1;
report.browseSimplifiedDetails = html("browse-results").indexOf('data-word-action="details"') !== -1;
report.columnControls = {
  hideButtons: (html("browse-results").match(/data-vocab-column-hide=/g) || []).length,
  mobileButtons: (html("browse-results").match(/data-vocab-column-toggle=/g) || []).length,
  labelledCells:
    html("browse-results").indexOf('data-vocab-col="word"') !== -1 &&
    html("browse-results").indexOf('data-vocab-col="pinyin"') !== -1 &&
    html("browse-results").indexOf('data-vocab-col="meaning"') !== -1,
  rowToggles: (html("browse-results").match(/data-word-row-toggle=/g) || []).length,
  rowSerials: (html("browse-results").match(/class="vocab-list__serial"/g) || []).length,
  rowCollapsed: false,
  rowRestored: false,
  rowIsolated: false,
  rowShows: 0,
  rowShowsOnRight: false,
  rowWordOnly: false,
  pinyinHidden: false,
  restoreControl: false,
  independent: false,
  persisted: false,
  restored: false
};
if (window.VocabularyUI.setTableColumn) {
  var columnProbeWord = window.VocabStore.all()[0];
  window.VocabularyUI.setTableColumn("pinyin", false);
  var pinyinHiddenMarkup = window.VocabularyUI.renderWordList([columnProbeWord], 0);
  report.columnControls.pinyinHidden =
    pinyinHiddenMarkup.indexOf("is-col-pinyin-hidden") !== -1;
  report.columnControls.restoreControl =
    pinyinHiddenMarkup.indexOf(">Show Pinyin</button>") !== -1 &&
    pinyinHiddenMarkup.indexOf(">Hide Word</button>") !== -1 &&
    pinyinHiddenMarkup.indexOf(">Hide Meaning</button>") !== -1;
  report.columnControls.persisted =
    (localStorage.getItem("chinese-vocab-table-columns-v1") || "").indexOf('"pinyin":false') !== -1;
  window.VocabularyUI.setTableColumn("pinyin", true);
  window.VocabularyUI.setTableColumn("word", false);
  var independentlyHiddenMarkup = window.VocabularyUI.renderWordList([columnProbeWord], 0);
  report.columnControls.independent =
    independentlyHiddenMarkup.indexOf("is-col-word-hidden") !== -1 &&
    independentlyHiddenMarkup.indexOf("is-col-pinyin-hidden") === -1;
  window.VocabularyUI.setTableColumn("word", true);
  var restoredColumnMarkup = window.VocabularyUI.renderWordList([columnProbeWord], 0);
  report.columnControls.restored =
    restoredColumnMarkup.indexOf("is-col-word-hidden") === -1 &&
    restoredColumnMarkup.indexOf("is-col-pinyin-hidden") === -1 &&
    restoredColumnMarkup.indexOf("is-col-meaning-hidden") === -1;

  /* Collapsing one row must leave its Chinese word readable and leave every
     other row untouched, which is what makes it usable for self-testing. */
  var rowPair = window.VocabStore.all().slice(0, 2);
  if (window.VocabularyUI.setRowCollapsed && rowPair.length === 2) {
    function rowMarkup(word) {
      var markup = window.VocabularyUI.renderWordList([word], 0);
      return markup.slice(markup.indexOf("<tbody>"));
    }
    window.VocabularyUI.setRowCollapsed(rowPair[0].id, true);
    var collapsedMarkup = rowMarkup(rowPair[0]);
    report.columnControls.rowCollapsed =
      collapsedMarkup.indexOf("is-row-collapsed") !== -1 &&
      collapsedMarkup.indexOf("data-word-row-toggle=") === -1 &&
      collapsedMarkup.indexOf('data-vocab-col="word"') !== -1 &&
      collapsedMarkup.indexOf(rowPair[0].traditional) !== -1;
    var neighbourMarkup = rowMarkup(rowPair[1]);
    report.columnControls.rowIsolated =
      neighbourMarkup.indexOf("is-row-collapsed") === -1 &&
      window.VocabularyUI.isRowCollapsed(rowPair[1].id) === false;
    window.VocabularyUI.setRowCollapsed(rowPair[0].id, false);
    var restoredRowMarkup = rowMarkup(rowPair[0]);
    report.columnControls.rowRestored =
      restoredRowMarkup.indexOf("is-row-collapsed") === -1;
    window.VocabularyUI.setTableColumn("word", false);
    window.VocabularyUI.setTableColumn("pinyin", false);
    window.VocabularyUI.setTableColumn("meaning", false);
    var hiddenRows = window.VocabularyUI.renderWordList(rowPair, 0);
    var hiddenBody = hiddenRows.slice(hiddenRows.indexOf("<tbody>"));
    report.columnControls.rowShows = (hiddenBody.match(/data-vocab-row-show="/g) || []).length;
    report.columnControls.rowShowsOnRight =
      hiddenBody.indexOf("vocab-list__row-shows") > hiddenBody.indexOf('data-vocab-col="meaning"') &&
      hiddenBody.indexOf('class="vocab-list__serial"') < hiddenBody.indexOf("vocab-list__row-shows") &&
      hiddenBody.slice(0, hiddenBody.indexOf("</td>")).indexOf("vocab-list__row-shows") === -1;
    window.VocabularyUI.showRowColumn(rowPair[0].id, "word");
    var oneWord = window.VocabularyUI.renderWordList(rowPair, 0);
    var oneBody = oneWord.slice(oneWord.indexOf("<tbody>"));
    var firstRow = oneBody.slice(0, oneBody.indexOf("</tr>"));
    var secondRow = oneBody.slice(oneBody.indexOf("</tr>") + 5);
    report.columnControls.rowWordOnly =
      firstRow.indexOf("is-showing-word") !== -1 &&
      firstRow.indexOf('data-vocab-row-show="word"') === -1 &&
      secondRow.indexOf("is-showing-word") === -1 &&
      secondRow.indexOf('data-vocab-row-show="word"') !== -1;
    window.VocabularyUI.setTableColumn("word", true);
    window.VocabularyUI.setTableColumn("pinyin", true);
    window.VocabularyUI.setTableColumn("meaning", true);
  }
}
var detailWord = window.VocabStore.all().filter(function (word) {
  return !!window.VocabStore.sentence(word);
})[0] || window.VocabStore.all()[0];
var detailMarkup = detailWord ? window.VocabularyUI.detailsMarkup(detailWord.id) : "";
report.wordDetailsComplete =
  detailMarkup.indexOf("Traditional") !== -1 &&
  detailMarkup.indexOf("Simplified") !== -1 &&
  detailMarkup.indexOf("Pinyin") !== -1 &&
  detailMarkup.indexOf("English") !== -1 &&
  detailMarkup.indexOf("हिन्दी") !== -1 &&
  detailMarkup.indexOf("Play Taiwan Mandarin") !== -1 &&
  detailMarkup.indexOf("Example sentence") !== -1;

/* Pinyin order is verified on the rendered markup, so a renderer that ignores
   the store's ordering cannot pass. */
function renderedPinyin(markup) {
  var cells = [];
  var pattern = /class="vocab-list__pinyin"[^>]*>([\s\S]*?)<\/td>/g;
  var match;
  while ((match = pattern.exec(markup))) {
    cells.push(match[1].replace(/<[^>]*>/g, "").trim());
  }
  return cells;
}
function pinyinAscending(values) {
  for (var index = 1; index < values.length; index += 1) {
    if (window.VocabStore.comparePinyin(
      { pinyin: values[index - 1] },
      { pinyin: values[index] }
    ) > 0) return false;
  }
  return true;
}
/* Each category band restarts the alphabet, so bands are checked separately. */
function groupedPinyinAscending(markup) {
  var segments = markup.split("vocab-group__head");
  var checked = 0;
  for (var index = 0; index < segments.length; index += 1) {
    var cells = renderedPinyin(segments[index]);
    if (cells.length < 2) continue;
    checked += 1;
    if (!pinyinAscending(cells)) return { sorted: false, checked: checked };
  }
  return { sorted: checked > 0, checked: checked };
}
function serialsContinuous(markup) {
  var values = [];
  var pattern = /class="vocab-list__serial-num">\s*(\d+)\s*</g;
  var match;
  while ((match = pattern.exec(markup))) values.push(Number(match[1]));
  if (!values.length) return false;
  for (var index = 0; index < values.length; index += 1) {
    if (values[index] !== index + 1) return false;
  }
  return true;
}
report.browsePinyinSorted = pinyinAscending(renderedPinyin(html("browse-results")));
report.browsePinyinCells = renderedPinyin(html("browse-results")).length;
var toneProbe = [{ pinyin: "ba" }, { pinyin: "bà" }, { pinyin: "bā" }, { pinyin: "bǎ" }, { pinyin: "bá" }];
report.toneOrder = window.VocabStore.pinyinOrder(toneProbe).map(function (word) { return word.pinyin; });
var spellingProbe = [
  { traditional: "安定", simplified: "安定", pinyin: "āndìng" },
  { traditional: "安頓", simplified: "安顿", pinyin: "āndùn" },
  { traditional: "安撫", simplified: "安抚", pinyin: "ānfǔ" },
  { traditional: "昂貴", simplified: "昂贵", pinyin: "ángguì" },
  { traditional: "骯髒", simplified: "肮脏", pinyin: "āngzāng" }
];
report.spellingOrder = window.VocabStore.pinyinOrder(spellingProbe).map(function (word) {
  return word.traditional + "\t" + word.simplified + "\t" + word.pinyin;
});
report.tocflPinyinSequence = window.TocflStore
  ? window.VocabStore.pinyinOrder(window.TocflStore.all()).map(function (word) { return word.pinyin; })
  : [];

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
      serials: (levelHtml.match(/class="vocab-list__serial"/g) || []).length,
      pagination: html("level-pagination"),
      categories: html("level-categories").length,
      categoriesHtml: html("level-categories").slice(0, 180),
      switcher: html("level-switch").length,
      groupHeads: (levelHtml.match(/vocab-group__head/g) || []).length,
      pinyinSorted: pinyinAscending(renderedPinyin(levelHtml)),
      numberingContinuous: serialsContinuous(levelHtml)
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
  window.AppRouter.go("characters", true);
  report.charactersRouteVisible = !document.getElementById("app-view-characters").classList.contains("hidden");
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
        (ROOT / "data" / "characters.js").read_text(encoding="utf-8"),
        (ROOT / "js" / "category-taxonomy.js").read_text(encoding="utf-8"),
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
    check(report["charactersUiLoaded"], "CharactersUI initialised")
    check(report["characterCount"] == 3000, "CharactersUI exposes exactly 3,000 individual characters")
    check(report["characterRender"]["levels"] == 3, "CharactersUI renders all three learning levels")
    check(report["characterRender"]["tiles"] == 50, "CharactersUI renders 50 individual character rows per page")
    check(report["characterColumns"]["controls"], "character list can hide or show Word, Pinyin, and Meaning")
    check(report["characterColumns"]["hides"], "hiding Pinyin and Meaning marks those character columns hidden")
    check(report["characterColumns"]["rowShows"], "each character row offers Show Pinyin and Show Meaning on the right")
    check(report["characterColumns"]["rowReveal"], "Show Word on one character row reveals only that row's word")
    check(report["characterRender"]["count"] == "1,000 individual characters", "Basic Reading contains exactly 1,000 characters")
    check(report["characterRender"]["details"] > 0, "clicking a character renders its multilingual details")
    check(report["characterRender"]["traditionalAudio"], "Traditional character buttons are audio-only controls")
    check(report["characterRender"]["simplifiedDetails"], "Simplified character buttons open details")
    check(report["characterRender"]["exactSpeech"], "character speech receives the exact clicked character")
    check(report["characterRender"]["taiwanVoice"], "character speech selects a zh-TW voice")
    check(report["characterRender"]["levelCounts"] == [1000, 2000, 3000], "UI filtering returns exact cumulative character counts")
    check(
        report["characterRender"]["clickCounts"] == ["2,000 individual characters", "3,000 individual characters"],
        "clicking each character level changes the rendered set and count",
    )
    check(
        report["characterRender"]["pinyinLevelSorted"] == [True, True, True],
        "all 1,000/2,000/3,000 character sets are sorted alphabetically by pinyin",
    )
    check(
        report["characterRender"]["renderedPinyinSorted"],
        "rendered character rows are sorted alphabetically by pinyin",
    )
    check(
        report["characterDiff"]["title"] == "Traditional and Simplified difference",
        "difference page title is Traditional and Simplified difference",
    )
    check(
        report["characterDiff"]["count"] > 0 and report["characterDiff"]["count"] < 3000,
        "difference page is a subset of the 3,000 characters",
    )
    check(
        report["characterDiff"]["count"] == report["characterDiff"]["expected"],
        "difference page includes every character whose forms differ",
    )
    check(report["characterDiff"]["allDifferent"], "every difference-page character has different Traditional and Simplified forms")
    check("3,000" in report["characterDiff"]["subtitle"], "difference page says the list comes from the 3,000 characters")
    check(report["characterDiff"]["levelsHidden"], "difference page hides the 1,000/2,000/3,000 level switch")
    check(report["characterDiff"]["pinyinSorted"], "difference-page characters are sorted by pinyin")
    check(report["characterDiff"]["sampleDifferent"], "difference page still shows Traditional and Simplified buttons")
    check(report["localStoragePersists"], "learning state persists in localStorage")
    check(report["totalWords"] > 0, f"store exposes words ({report['totalWords']})")
    check(report["tocflA1Words"] > 0, f"store filters TOCFL A1 words ({report['tocflA1Words']})")
    check(report["tocflCounts"].get("A2", 0) > 0, "store counts TOCFL A2 words")
    check(report["tocfl8000Words"] == 7517, "all 7,517 TOCFL workbook rows are loaded")
    check(report["ccccWords"] == 1197, "all 1,197 CCCC workbook rows are loaded")
    check(report["tocflCombinedLevels"] == 10, "TOCFL renders all ten workbook levels")
    check(report["tocflLevelSizes"]["novice-1"] == 160, "Novice 1 keeps its first-occurrence 160 words")
    check(report["tocflLevelSizes"]["novice-2"] == 234, "Novice 2 keeps its first-occurrence 234 words")
    check(report["tocflLevelSizes"]["level-1"] < 347, "Level 1 drops later repeats of the same word")
    check(report["tocflUniqueDuplicates"] == 0, "no unique Chinese+pinyin word is shown twice")
    check(report["tocflVariantMerge"]["sameWord"], "same-word variants such as 麻煩 stay in the lower level")
    check(report["tocflVariantMerge"]["differentReading"], "different readings such as 好 hǎo and 好 hào stay separate")
    check(
        report["categoriesRender"]["uniqueWords"] + report["categoriesRender"]["duplicatesMerged"] == 8714,
        "deduplication accounts for all 8,714 TOCFL and CCCC source rows",
    )
    check(len(report["tocflLevelSizes"]) == 10, "all ten levels still have unique words")
    check(report["tocflAllLevelsSorted"], "all TOCFL and CCCC levels are alphabetically sorted by pinyin")
    check(report["tocflLevelAssignmentCorrect"], "every TOCFL and CCCC word remains in its assigned level")
    check(
        sum(report["tocflLevelSizes"].values()) == report["tocflUniqueTotal"],
        "TOCFL and CCCC level counts account for every deduplicated word exactly once",
    )
    check(report["tocflRender"]["levelWordCount"] == 160, "selected Novice 1 remains limited to 160 words")
    check(report["tocflEntryLevel"]["buttons"] == 5, "TOCFL switch shows 入門級 · Level 1 plus Levels 2–5")
    check(report["tocflEntryLevel"]["titled"], "merged band is titled 入門級 · Level 1")
    check(report["tocflEntryLevel"]["hidesMergedButtons"], "Novice, Sprouting, Growing, Thriving, and Level 1 are not separate buttons")
    check(report["tocflEntryLevel"]["keepsLater"], "Level 2, Level 3, Level 4, and Level 5 stay separate")
    check(report["tocflEntryLevel"]["onlyEntry"] and report["tocflEntryLevel"]["coversEach"], "入門級 · Level 1 contains the six merged bands")
    check(report["tocflRender"]["categoryCountMatches"], "selected category count matches its actual words")
    check(report["tocflRender"]["categoryExact"], "selected category contains no other level or category")
    check(report["tocflRender"]["subcategories"] > 0, "selected category renders only its subcategories")
    check(report["tocflRender"]["subcategoryCountMatches"], "selected subcategory count matches displayed words")
    check(report["tocflRender"]["subcategoryExact"], "subcategory filter applies level AND category AND subcategory")
    check(report["tocflClickFlow"]["level"] == "level-3", "clicking a category keeps the chosen level (Level 3)")
    check(report["tocflClickFlow"]["countText"] != "160 words", "Level 3 no longer falls back to the 160 Novice 1 words")
    check(report["tocflClickFlow"]["categoryExact"], "category clicked inside Level 3 shows only Level 3 words")
    check(report["tocflClickFlow"]["subcategoryExact"], "subcategory clicked inside Level 3 stays in that category")
    check(
        report["tocfl8000"]["count"] == sum(
            report["tocflLevelSizes"][level]
            for level in ("novice-1", "novice-2", "level-1", "level-2", "level-3", "level-4", "level-5")
        ),
        "Official TOCFL vocabulary shows every TOCFL 8000 word",
    )
    check(report["tocfl8000"]["title"] == "TOCFL 8000", "Official TOCFL vocabulary is titled TOCFL 8000")
    check("arranged by pinyin" in report["tocfl8000"]["subtitle"], "Official TOCFL vocabulary is arranged by pinyin")
    check(report["tocfl8000"]["levelsHidden"], "Official TOCFL vocabulary has no level switcher")
    check(report["tocfl8000"]["pinyinSorted"], "Official TOCFL vocabulary list is in pinyin order")
    check(report["tocfl8000"]["onlyTocfl"], "Official TOCFL vocabulary leaves out CCCC-only levels")
    check(report["tocfl8000"]["largeBands"]["sized"]["min"] >= 300, "TOCFL 8000 noun, action-verb, and adjective topics each have at least 300 words")
    check(report["tocfl8000"]["largeBands"]["adverbs"]["count"] == 1, "TOCFL 8000 adverbs stay in one topic")
    check(report["tocflClickFlow"]["countMatches"], "displayed count matches the clicked category selection")
    check(report["tocflRender"]["categories"] > 0, "TOCFL renders category chips")
    check(report["tocflRender"]["results"] > 0, f"TOCFL renders words ({report['tocflRender']['count']})")
    check(report["categoriesRender"]["taxonomy"] == 61, "CategoriesUI exposes the split topic taxonomy")
    check(report["categoriesRender"]["cards"] == 61, "Categories landing renders every topic card")
    check(report["categoriesRender"]["dynamicCounts"], "category counts are computed from deduplicated source words")
    check(report["categoriesRender"]["duplicatesMerged"] > 0, "TOCFL/CCCC duplicate rows are merged")
    check(report["categoriesRender"]["strictSources"], "Categories contains only TOCFL and CCCC words")
    check(report["categoriesRender"]["categoryExact"], "category detail contains only its selected primary category")
    check(report["categoriesRender"]["prioritySorted"], "category detail uses official learning-priority order")
    check(report["categoriesRender"]["traditionalSearch"], "category search finds Traditional Chinese")
    check(report["categoriesRender"]["pinyinSearch"], "category search finds Pinyin")
    check(report["categoriesRender"]["englishSearch"], "category search finds English meanings")
    check(report["categoriesRender"]["sourceMetadata"], "every rendered category word shows source metadata")
    check(report["categoriesRender"]["mergedSource"], "overlap words are labelled TOCFL + CCCC")
    check(report["categoriesRender"]["pagination"], "large categories render pagination")
    check(report["categoriesRender"]["detailVisible"], "opening a category switches landing to detail")
    check(report["categoriesRender"]["routeVisible"], "category detail route opens the Categories panel")
    check(report["hskDuplicateExtras"] == 0, "HSK 1–6 contains no duplicate Chinese+pinyin entries")
    check(report["hskAllLevelsSorted"], "all HSK levels are alphabetically sorted by pinyin")
    check(report["hskLevelAssignmentCorrect"], "every HSK word remains in its assigned level")
    check(report["browseHtml"] > 0, f"Browse renders markup ({report['browseHtml']} chars)")
    check(not report["browseCount"].startswith("0 "), f"Browse word count: {report['browseCount']}")
    check(report["browseSerials"] <= 50, f"Browse limits each page to 50 words ({report['browseSerials']})")
    check("Page 1 of" in report["browsePagination"], "Browse renders page navigation")
    check(not report.get("browseHasLevelCol"), "Browse word list does not include Level & category")
    check(not report.get("browseHasScriptCaption"), "word list drops the 繁體/简体 captions")
    check(not report.get("browseHasActionsCol"), "word list does not include an Actions column")
    check(report.get("browseWordButtons", 0) > 0, "word list still renders tappable script buttons")
    check(report["columnControls"]["hideButtons"] == 0, "column headers have no Hide buttons")
    check(report["columnControls"]["mobileButtons"] == 3, "one bar hides or shows Word, Pinyin, and Meaning")
    check(report["columnControls"]["labelledCells"], "all optional columns use stable responsive column labels")
    check(report["columnControls"]["pinyinHidden"], "Pinyin can be hidden in every shared word list")
    check(report["columnControls"]["restoreControl"], "a hidden column renders a clear Show control")
    check(report["columnControls"]["independent"], "Word, Pinyin, and Meaning visibility is independent")
    check(report["columnControls"]["persisted"], "column visibility persists in localStorage")
    check(report["columnControls"]["restored"], "all hidden columns can be restored")
    check(report["columnControls"]["rowToggles"] == 0, "word rows have no Hide button")
    check(report["columnControls"]["rowShows"] == 6, "every hidden column offers Show Word, Show Pinyin, and Show Meaning on each row")
    check(report["columnControls"]["rowShowsOnRight"], "Show Word, Show Pinyin, and Show Meaning sit on the right of the row")
    check(report["columnControls"]["rowWordOnly"], "Show Word on one row reveals only that row's word")
    check(report["columnControls"]["rowCollapsed"], "clicking a word can leave only that Chinese word")
    check(report["columnControls"]["rowIsolated"], "one row's word-only state leaves the other rows alone")
    check(report["columnControls"]["rowRestored"], "clicking that word again restores its pinyin and meaning")
    check(report.get("browseTraditionalAudio"), "Traditional word buttons play their exact displayed text")
    check(report.get("browseSimplifiedDetails"), "Simplified word buttons open details")
    check(report.get("wordDetailsComplete"), "word details include scripts, meanings, example, and pronunciation")
    check(
        report["toneOrder"] == ["bā", "bá", "bǎ", "bà", "ba"],
        f"pinyin sorting keeps tone order 1→4 before the neutral tone ({' '.join(report['toneOrder'])})",
    )
    check(
        report.get("spellingOrder") == EXPECTED_SPELLING,
        "full Pinyin spelling puts āngzāng before ángguì: " + " | ".join(report.get("spellingOrder") or []),
    )
    tocfl_sequence = report.get("tocflPinyinSequence") or []
    unsplittable = [
        reading for reading in tocfl_sequence
        if any(
            part not in SYLLABLE_SET and not (part.endswith("r") and part[:-1] in SYLLABLE_SET)
            for part, _tone in syllable_key(reading)
        )
    ]
    check(
        len(tocfl_sequence) > 1000 and all(len(syllable_key(reading)) == 1 for reading in unsplittable),
        "unsplittable readings stay one spelling"
        + ("" if not unsplittable else " — " + ", ".join(unsplittable[:6])),
    )
    resorted = sorted(tocfl_sequence, key=syllable_key)
    mismatch = next(
        (
            f"{tocfl_sequence[index - 1]} before {tocfl_sequence[index]}"
            for index in range(1, len(tocfl_sequence))
            if syllable_key(tocfl_sequence[index - 1]) > syllable_key(tocfl_sequence[index])
        ),
        "",
    )
    check(
        tocfl_sequence == resorted and not mismatch,
        "second full sort confirms every TOCFL word is in Pinyin order"
        + ("" if not mismatch else " — " + mismatch),
    )
    check(report.get("browsePinyinCells", 0) > 0, "Browse renders a pinyin column to sort on")
    check(report.get("browsePinyinSorted"), "Browse lists words alphabetically by pinyin")

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
        check(data["groupHeads"] == 0, f"{view} remains one level-wide list")
        check(data["pinyinSorted"], f"{view} is globally alphabetical by pinyin")
        check(data["numberingContinuous"], f"{view} numbering is continuous")

    check(report.get("tocflRouteVisible"), "Router opens the TOCFL category page")
    check(report.get("pronounceRouteVisible"), "Router opens TOCFL pronunciation")
    check(report.get("charactersRouteVisible"), "Router opens the Chinese Characters page")
    check(report["tocflGroups"]["heads"] == 0, "TOCFL/CCCC remains one level-wide list")
    check(report["tocflGroups"]["pinyinSorted"], "TOCFL/CCCC level is globally alphabetical by pinyin")
    check(report["tocflGroups"]["numberingContinuous"], "TOCFL/CCCC numbering is continuous")
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
