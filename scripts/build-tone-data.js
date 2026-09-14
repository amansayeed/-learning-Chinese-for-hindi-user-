/**
 * Merges NHM 1000-word list into data/tone-quartets.json with difficulty levels.
 * Run: node scripts/build-tone-data.js
 */
"use strict";

const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const tonePath = path.join(root, "data", "tone-quartets.json");
const tonePageBundlePath = path.join(root, "data", "tone-page.data.js");
const nhmPath = path.join(root, "data", "nhm-1000-common.json");
const tocflPath = path.join(root, "data", "vocabulary.json");
const cedictPath = path.join(root, "data", "external", "cedict_ts.u8");
const hskPath = path.join(root, "data", "external", "hsk-complete.json");

const raw = JSON.parse(fs.readFileSync(tonePath, "utf8"));
const nhm = JSON.parse(fs.readFileSync(nhmPath, "utf8"));
const tocfl = JSON.parse(fs.readFileSync(tocflPath, "utf8"));
const cedictText = fs.existsSync(cedictPath) ? fs.readFileSync(cedictPath, "utf8") : "";
const hsk = fs.existsSync(hskPath) ? JSON.parse(fs.readFileSync(hskPath, "utf8")) : [];

function normalizeKey(s) {
  return String(s || "").trim();
}

function isNonEmpty(s) {
  return String(s || "").trim().length > 0;
}

function buildHindiMap() {
  const map = new Map();
  const add = (simp, hi) => {
    simp = normalizeKey(simp);
    hi = String(hi || "").trim();
    if (!simp || !hi) return;
    if (!map.has(simp)) map.set(simp, hi);
  };

  // NHM + TOCFL have Hindi already
  for (const w of collectWordsFromJson(nhm)) add(w.simplified, w.hindi);
  for (const w of collectWordsFromJson(tocfl)) add(w.simplified, w.hindi);

  // Existing quartets/words in the tone file may also contain Hindi
  for (const q of raw.quartets || []) {
    for (const t of q.tones || []) add(t.simplified, t.hindi);
  }
  for (const w of raw.words || []) add(w.simplified, w.hindi);

  return map;
}

const hindiBySimp = buildHindiMap();

/** @param {string} lessonId */
function lessonNum(lessonId) {
  const m = String(lessonId || "").match(/(\d+)/);
  return m ? parseInt(m[1], 10) : 0;
}

/** NHM has 20 lessons × 50 words; map to four difficulty bands. */
function difficultyFromLesson(n) {
  if (n <= 0) return "beginner";
  if (n <= 5) return "beginner";
  if (n <= 10) return "elementary";
  if (n <= 15) return "intermediate";
  return "advanced";
}

const quartetDifficulty = {
  ma: "beginner",
  ba: "beginner",
  yi: "beginner",
  shi: "beginner",
  zhu: "beginner",
  ji: "beginner",
  wen: "beginner",
  fang: "beginner",
  liu: "beginner",
  chang: "intermediate",
  xing: "intermediate",
  qing: "intermediate",
  xiang: "intermediate",
  jiao: "intermediate",
  shu: "intermediate",
};

const quartets = (raw.quartets || []).map(function (q) {
  const out = Object.assign({}, q);
  out.difficulty = quartetDifficulty[q.id] || "beginner";
  return out;
});

// Auto-extract additional four-tone quartets from the NHM 1000-word list.
const TONE = {
  "ā": [1, "a"],
  "á": [2, "a"],
  "ǎ": [3, "a"],
  "à": [4, "a"],
  "ē": [1, "e"],
  "é": [2, "e"],
  "ě": [3, "e"],
  "è": [4, "e"],
  "ī": [1, "i"],
  "í": [2, "i"],
  "ǐ": [3, "i"],
  "ì": [4, "i"],
  "ō": [1, "o"],
  "ó": [2, "o"],
  "ǒ": [3, "o"],
  "ò": [4, "o"],
  "ū": [1, "u"],
  "ú": [2, "u"],
  "ǔ": [3, "u"],
  "ù": [4, "u"],
  "ǖ": [1, "ü"],
  "ǘ": [2, "ü"],
  "ǚ": [3, "ü"],
  "ǜ": [4, "ü"],
};

function parseFirstSyllable(py) {
  py = String(py || "").trim().toLowerCase();
  if (!py) return null;
  // Cedict can use numbered pinyin; NHM/TOCFL uses tone marks.
  // Only use the first syllable token for grouping.
  py = py.split(/\s+/)[0];

  // Numbered pinyin: e.g. wan4, lü4, nv3
  const num = py.match(/^([a-züv:]+)([1-4])$/);
  if (num) {
    const base = num[1].replace(/v|u:/g, "ü");
    const tone = parseInt(num[2], 10);
    return { tone, base };
  }

  // Tone marks
  let tone = 0;
  let base = "";
  for (const ch of py) {
    if (TONE[ch]) {
      tone = TONE[ch][0];
      base += TONE[ch][1];
    } else {
      base += ch;
    }
  }
  if (!tone) return null;
  return { tone, base };
}

function collectWordsFromJson(json) {
  const out = [];
  for (const level of json.levels || []) {
    for (const lesson of level.lessons || []) {
      for (const w of lesson.words || []) out.push(w);
    }
  }
  return out;
}

function isHsk1to5(entry) {
  const levels = Array.isArray(entry.level) ? entry.level : [];
  for (const l of levels) {
    const m = String(l).match(/^(old|new|newest)-([1-9]\d*)$/);
    if (!m) continue;
    const n = parseInt(m[2], 10);
    if (n >= 1 && n <= 5) return true;
  }
  return false;
}

function collectWordsFromHsk1to5() {
  const out = [];
  for (const e of Array.isArray(hsk) ? hsk : []) {
    if (!isHsk1to5(e)) continue;
    const simp = String(e.simplified || "").trim();
    if (!simp) continue;
    const form = Array.isArray(e.forms) && e.forms.length ? e.forms[0] : null;
    const trad = form && form.traditional ? String(form.traditional).trim() : "";
    const pinyin = form && form.transcriptions && form.transcriptions.pinyin ? form.transcriptions.pinyin : "";
    const meanings = form && Array.isArray(form.meanings) ? form.meanings : [];
    const english = meanings.length ? meanings[0] : "";
    const hindi = hindiBySimp.get(simp) || "";
    out.push({
      traditional: trad || simp,
      simplified: simp,
      pinyin,
      english,
      hindi,
    });
  }
  return out;
}

function parseCedictLine(line) {
  // format: 傳統 簡體 [pin1 yin1] /def/def/
  if (!line || line[0] === "#") return null;
  const m = line.match(/^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+\/(.+)\/\s*$/);
  if (!m) return null;
  const traditional = m[1];
  const simplified = m[2];
  const pinyinNumbered = m[3];
  const defs = m[4]
    .split("/")
    .map((s) => s.trim())
    .filter(Boolean);
  const english = defs[0] || "";
  const hindi = hindiBySimp.get(simplified) || "";
  return { traditional, simplified, pinyin: pinyinNumbered, english, hindi };
}

function autoQuartetsFromSources() {
  const nhmWords = collectWordsFromJson(nhm);
  const tocflWords = collectWordsFromJson(tocfl);
  const hskWords = collectWordsFromHsk1to5();

  // Use NHM+TOCFL as a "useful word" filter.
  const usefulSimp = new Set(
    [...nhmWords, ...tocflWords, ...hskWords]
      .map((w) => String(w.simplified || "").trim())
      .filter(Boolean)
  );

  const all = [...nhmWords, ...tocflWords, ...hskWords];
  // Add CC-CEDICT entries for extra coverage (English only, Hindi left blank).
  if (cedictText) {
    for (const line of cedictText.split(/\r?\n/)) {
      const e = parseCedictLine(line);
      if (!e) continue;
      if (!usefulSimp.has(e.simplified)) continue;
      all.push({
        traditional: e.traditional,
        simplified: e.simplified,
        pinyin: e.pinyin,
        english: e.english,
        hindi: e.hindi || "",
      });
    }
  }

  const byBase = new Map();
  for (const w of all) {
    const simp = String(w.simplified || "").trim();
    const trad = String(w.traditional || "").trim();
    if (!simp) continue;
    const p = parseFirstSyllable(w.pinyin);
    if (!p) continue;
    if (!byBase.has(p.base)) byBase.set(p.base, new Map());
    const m = byBase.get(p.base);
    if (!m.has(p.tone)) m.set(p.tone, []);
    m.get(p.tone).push({
      tone: p.tone,
      pinyin: String(w.pinyin || "").trim(),
      traditional: trad,
      simplified: simp,
      english: w.english,
      hindi: isNonEmpty(w.hindi) ? w.hindi : (hindiBySimp.get(simp) || ""),
      sourceNo: w.sourceNo != null ? w.sourceNo : null,
    });
  }

  const out = [];
  for (const [base, m] of byBase.entries()) {
    if (!(m.has(1) && m.has(2) && m.has(3) && m.has(4))) continue;
    // Greedy pick: for each tone pick a word with unique simplified + unique English gloss.
    const usedSimp = new Set();
    const usedEn = new Set();
    /** @type {any[]} */
    const pick = [];
    for (const tone of [1, 2, 3, 4]) {
      const candidates = m.get(tone) || [];
      let chosen = null;
      for (const c of candidates) {
        const en = String(c.english || "").trim().toLowerCase();
        if (!c.simplified) continue;
        if (usedSimp.has(c.simplified)) continue;
        if (en && usedEn.has(en)) continue;
        chosen = c;
        break;
      }
      if (!chosen) {
        // fallback to first candidate
        chosen = candidates[0];
      }
      if (!chosen) break;
      // Teacher-mode: if Hindi is missing but we have a known mapping, fill it.
      if (!isNonEmpty(chosen.hindi)) {
        chosen.hindi = hindiBySimp.get(chosen.simplified) || chosen.hindi || "";
      }
      usedSimp.add(chosen.simplified);
      const en = String(chosen.english || "").trim().toLowerCase();
      if (en) usedEn.add(en);
      pick.push(chosen);
    }
    if (pick.length !== 4) continue;
    const uniqChars = new Set(pick.map((x) => x.simplified));
    if (uniqChars.size < 4) continue;
    // Skip quartets that still have empty English or Hindi glosses.
    if (pick.some((x) => !isNonEmpty(x.english) || !isNonEmpty(x.hindi))) continue;
    out.push({
      id: ("nhm-" + (base.replace(/[^a-z0-9]/g, "") || base)),
      label: base,
      tones: pick,
      difficulty: "beginner",
      source: "auto-nhm",
    });
  }
  out.sort((a, b) => a.label.localeCompare(b.label));
  return out;
}

const autoQuartets = autoQuartetsFromSources();
const mergedQuartets = (() => {
  const seen = new Set();
  const out = [];
  [...quartets, ...autoQuartets].forEach((q) => {
    const key = String(q.label || q.id || "").toLowerCase();
    if (!key || seen.has(key)) return;
    seen.add(key);
    // Backfill Hindi from known map when possible.
    const qq = Object.assign({}, q);
    qq.tones = (q.tones || []).map((t) => {
      const tt = Object.assign({}, t);
      if (!isNonEmpty(tt.hindi)) {
        tt.hindi = hindiBySimp.get(tt.simplified) || "";
      }
      return tt;
    });
    out.push(qq);
  });
  // Teacher-mode: keep only quartets that have full glosses.
  return out.filter((q) => (q.tones || []).length === 4 && !(q.tones || []).some((t) => !isNonEmpty(t.english) || !isNonEmpty(t.hindi)));
})();

const words = [];
for (const level of nhm.levels || []) {
  for (const lesson of level.lessons || []) {
    const n = lessonNum(lesson.id);
    const difficulty = difficultyFromLesson(n);
    for (const w of lesson.words || []) {
      words.push({
        traditional: w.traditional,
        simplified: w.simplified,
        pinyin: w.pinyin,
        english: w.english,
        hindi: w.hindi,
        difficulty,
        lessonId: lesson.id,
        lessonTitle: lesson.title || null,
        sourceNo: w.sourceNo != null ? w.sourceNo : null,
        audioUrl: w.audioUrl != null ? w.audioUrl : null,
      });
    }
  }
}

if (words.length !== 1000) {
  console.warn("Expected 1000 words, got", words.length);
}

const meta = Object.assign({}, raw.meta, {
  title: "Mandarin learning data: four-tone sets + 1000-word vocabulary",
  corpusFile: "nhm-1000-common.json",
  corpusWordCount: 1000,
  wordsInThisFile: words.length,
  difficultyLevels: {
    beginner: "NHM lessons 1–5 (approx. first 250 words)",
    elementary: "NHM lessons 6–10",
    intermediate: "NHM lessons 11–15",
    advanced: "NHM lessons 16–20",
  },
  quartetDifficultyNote:
    "Each item in `quartets` has `difficulty` for the tone-drill set (curated; not from NHM ordering).",
  wordsDifficultyNote:
    "Each item in `words` has `difficulty` from lesson number in the Ni Hao Ma list.",
  note:
    "The `words` array is the full Ni Hao Ma 1000-word list with `difficulty`. The `quartets` array is a separate curated list of syllables that have four tones with four different meanings (for the tones practice page).",
});

const out = {
  meta,
  quartets: mergedQuartets,
  words,
};

fs.writeFileSync(tonePath, JSON.stringify(out, null, 2), "utf8");
console.log("Wrote", tonePath, "— words:", words.length, "quartets:", mergedQuartets.length);

const pagePayload = {
  meta: {
    title: meta.title,
    tts: meta.tts,
    quartetCount: mergedQuartets.length,
    wordsCount: words.length,
  },
  quartets: mergedQuartets,
  words,
};
const pageBundle =
  "// Auto-generated — quartets + 1000 words for tones.html (file:// safe)\n" +
  "window.__TONE_PAGE_DATA__ = " +
  JSON.stringify(pagePayload) +
  ";\n";
fs.writeFileSync(tonePageBundlePath, pageBundle, "utf8");
console.log("Wrote", tonePageBundlePath, "— bytes ~", Math.round(pageBundle.length / 1024), "KB");
