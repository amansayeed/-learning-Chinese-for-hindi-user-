(function () {
  "use strict";

  const CFG = window.__VOCAB_APP_CONFIG__ || {};
  const FIXED_DATASET = CFG.dataset || null;

  const datasetSelect = document.getElementById("dataset-select");
  const viewModeSelect = document.getElementById("view-mode");
  const levelSelect = document.getElementById("level-select");
  const lessonSelect = document.getElementById("lesson-select");
  const searchInput = document.getElementById("search");
  const wordBody = document.getElementById("word-body");
  const loadError = document.getElementById("load-error");
  const metaLine = document.getElementById("meta-line");
  const tablePanel = document.getElementById("table-panel");
  const studyPanel = document.getElementById("study-panel");
  const studyProgress = document.getElementById("study-progress");
  const studyMeta = document.getElementById("study-meta");
  const studyHan = document.getElementById("study-han");
  const studyPy = document.getElementById("study-py");
  const studyEn = document.getElementById("study-en");
  const studyHi = document.getElementById("study-hi");
  const studyMeaningWrap = document.getElementById("study-meaning-wrap");
  const studyRevealBtn = document.getElementById("study-reveal");
  const studyPrev = document.getElementById("study-prev");
  const studyNext = document.getElementById("study-next");
  const studyRand = document.getElementById("study-rand");
  const themeToggle = document.getElementById("theme-toggle");

  const THEME_KEY = "chinese-vocab-theme";
  const NAV_DATASET = CFG.navDatasetKey || "chinese-vocab-nav-dataset";
  const NAV_LEVEL = CFG.navLevelKey || "chinese-vocab-nav-level";
  const NAV_LESSON = CFG.navLessonKey || "chinese-vocab-nav-lesson";

  let listenersBound = false;

  function persistNav() {
    try {
      if (datasetSelect && !FIXED_DATASET) {
        sessionStorage.setItem(NAV_DATASET, datasetSelect.value);
      }
      sessionStorage.setItem(NAV_LEVEL, String(levelSelect.selectedIndex));
      sessionStorage.setItem(NAV_LESSON, String(lessonSelect.selectedIndex));
    } catch (e) {}
  }

  function getTheme() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function syncThemeToggle() {
    if (!themeToggle) return;
    var dark = getTheme() === "dark";
    themeToggle.textContent = dark ? "Light mode" : "Dark mode";
    themeToggle.setAttribute("aria-pressed", dark ? "true" : "false");
    themeToggle.setAttribute(
      "aria-label",
      dark ? "Switch to light theme" : "Switch to dark theme"
    );
  }

  function setTheme(mode) {
    if (mode !== "light" && mode !== "dark") return;
    document.documentElement.setAttribute("data-theme", mode);
    try {
      localStorage.setItem(THEME_KEY, mode);
    } catch (e) {}
    syncThemeToggle();
  }

  function initTheme() {
    if (!themeToggle) return;
    themeToggle.addEventListener("click", function () {
      setTheme(getTheme() === "dark" ? "light" : "dark");
    });
    syncThemeToggle();
  }

  /** @type {{ meta?: object, levels: Array<{ id: string, label: string, wordCount: number, lessons: Array<{ id: string, title: string, subtitle?: string, words: Word[] }> }> } | null} */
  let data = null;

  /** @typedef {{ traditional: string, simplified: string, pinyin: string, english: string, hindi: string, audioUrl: string | null, sourceNo?: number }} Word */

  let studyIndex = 0;
  let studyRevealed = false;

  let audioEl = null;

  function getAudioElement() {
    if (!audioEl) {
      audioEl = new Audio();
      audioEl.preload = "auto";
    }
    return audioEl;
  }

  function speakTraditional(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "zh-TW";
    u.rate = 0.88;
    window.speechSynthesis.speak(u);
  }

  function playWord(word) {
    if (word.audioUrl) {
      const a = getAudioElement();
      a.src = word.audioUrl;
      a.play().catch(function () {
        speakTraditional(word.traditional);
      });
    } else {
      speakTraditional(word.traditional);
    }
  }

  function normalize(s) {
    return (s || "").toLowerCase();
  }

  function filterWords(words, q) {
    if (!q.trim()) return words;
    const n = normalize(q);
    return words.filter(function (w) {
      return (
        normalize(w.traditional).includes(n) ||
        normalize(w.simplified).includes(n) ||
        normalize(w.pinyin).includes(n) ||
        normalize(w.english).includes(n) ||
        normalize(w.hindi).includes(n)
      );
    });
  }

  function currentLessonWords() {
    const lvl = data.levels[levelSelect.selectedIndex];
    if (!lvl) return [];
    const les = lvl.lessons[lessonSelect.selectedIndex];
    return les ? les.words : [];
  }

  function getFilteredWords() {
    return filterWords(currentLessonWords(), searchInput.value);
  }

  function clampStudyIndex(max) {
    if (max <= 0) {
      studyIndex = 0;
      return;
    }
    if (studyIndex >= max) studyIndex = max - 1;
    if (studyIndex < 0) studyIndex = 0;
  }

  function renderTable(words) {
    wordBody.textContent = "";
    const frag = document.createDocumentFragment();
    words.forEach(function (w, i) {
      const tr = document.createElement("tr");

      const tdNum = document.createElement("td");
      tdNum.className = "col-num";
      tdNum.textContent =
        typeof w.sourceNo === "number" ? String(w.sourceNo) : String(i + 1);

      const tdTrad = document.createElement("td");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "trad-cell";
      btn.textContent = w.traditional;
      btn.setAttribute("aria-label", "Play pronunciation: " + w.traditional);
      btn.addEventListener("click", function () {
        playWord(w);
      });
      tdTrad.appendChild(btn);

      const tdSimp = document.createElement("td");
      tdSimp.className = "simp-cell";
      tdSimp.textContent = w.simplified;

      const tdPy = document.createElement("td");
      tdPy.className = "pinyin-cell";
      tdPy.textContent = w.pinyin;

      const tdEn = document.createElement("td");
      tdEn.textContent = w.english;

      const tdHi = document.createElement("td");
      tdHi.textContent = w.hindi;

      tr.appendChild(tdNum);
      tr.appendChild(tdTrad);
      tr.appendChild(tdSimp);
      tr.appendChild(tdPy);
      tr.appendChild(tdEn);
      tr.appendChild(tdHi);
      frag.appendChild(tr);
    });
    wordBody.appendChild(frag);
  }

  function setStudyReveal(on) {
    studyRevealed = on;
    if (on) {
      studyMeaningWrap.classList.remove("is-hidden");
      studyRevealBtn.classList.add("is-hidden");
    } else {
      studyMeaningWrap.classList.add("is-hidden");
      studyRevealBtn.classList.remove("is-hidden");
    }
  }

  function renderStudy() {
    const words = getFilteredWords();
    clampStudyIndex(words.length);
    const total = words.length;
    const w = words[studyIndex];

    if (!w) {
      studyHan.textContent = "—";
      studyPy.textContent = "";
      studyEn.textContent = "";
      studyHi.textContent = "";
      studyMeta.textContent =
        total === 0 ? "No words match your search." : "No word selected.";
      studyProgress.style.width = "0%";
      return;
    }

    studyHan.textContent = w.traditional;
    studyPy.textContent = w.pinyin;
    studyEn.textContent = w.english;
    studyHi.textContent = w.hindi;

    const les = data.levels[levelSelect.selectedIndex].lessons[lessonSelect.selectedIndex];
    const lessonLabel = les.title + (les.subtitle ? " · " + les.subtitle : "");
    const numLabel =
      typeof w.sourceNo === "number" ? "#" + w.sourceNo + " · " : "";
    studyMeta.textContent =
      numLabel +
      "Word " +
      (studyIndex + 1) +
      " of " +
      total +
      " · " +
      lessonLabel;

    studyProgress.style.width = total ? ((studyIndex + 1) / total) * 100 + "%" : "0%";

    setStudyReveal(studyRevealed);

    studyHan.onclick = function () {
      playWord(w);
    };
  }

  function isStudyMode() {
    return viewModeSelect.value === "study";
  }

  function updateViewLayout() {
    if (isStudyMode()) {
      tablePanel.classList.add("hidden");
      studyPanel.classList.remove("hidden");
      renderStudy();
    } else {
      studyPanel.classList.add("hidden");
      tablePanel.classList.remove("hidden");
      renderTable(getFilteredWords());
    }
  }

  function refresh() {
    clampStudyIndex(getFilteredWords().length);
    if (isStudyMode()) {
      renderStudy();
    } else {
      renderTable(getFilteredWords());
    }
  }

  function populateLessons() {
    const lvl = data.levels[levelSelect.selectedIndex];
    lessonSelect.innerHTML = "";
    if (!lvl) return;
    lvl.lessons.forEach(function (les, i) {
      const opt = document.createElement("option");
      opt.value = String(i);
      var t = les.title;
      if (les.subtitle) t += " — " + les.subtitle;
      t += " (" + les.words.length + " words)";
      opt.textContent = t;
      lessonSelect.appendChild(opt);
    });
  }

  function populateLevels() {
    levelSelect.innerHTML = "";
    data.levels.forEach(function (lvl) {
      const opt = document.createElement("option");
      opt.value = lvl.id;
      opt.textContent = lvl.label + " — " + lvl.wordCount + " words";
      levelSelect.appendChild(opt);
    });
  }

  function bindListenersOnce() {
    if (listenersBound) return;
    listenersBound = true;

    if (datasetSelect) {
      datasetSelect.addEventListener("change", function () {
        searchInput.value = "";
        studyIndex = 0;
        studyRevealed = false;
        applyDataset(datasetSelect.value);
      });
    }

    viewModeSelect.addEventListener("change", function () {
      studyIndex = 0;
      studyRevealed = false;
      updateViewLayout();
    });

    levelSelect.addEventListener("change", function () {
      populateLessons();
      searchInput.value = "";
      studyIndex = 0;
      studyRevealed = false;
      refresh();
      persistNav();
    });

    lessonSelect.addEventListener("change", function () {
      searchInput.value = "";
      studyIndex = 0;
      studyRevealed = false;
      refresh();
      persistNav();
    });

    searchInput.addEventListener("input", function () {
      studyIndex = 0;
      studyRevealed = false;
      refresh();
    });

    studyRevealBtn.addEventListener("click", function () {
      setStudyReveal(true);
    });

    studyPrev.addEventListener("click", function () {
      const words = getFilteredWords();
      if (words.length === 0) return;
      studyIndex = (studyIndex - 1 + words.length) % words.length;
      studyRevealed = false;
      renderStudy();
    });

    studyNext.addEventListener("click", function () {
      const words = getFilteredWords();
      if (words.length === 0) return;
      studyIndex = (studyIndex + 1) % words.length;
      studyRevealed = false;
      renderStudy();
    });

    studyRand.addEventListener("click", function () {
      const words = getFilteredWords();
      if (words.length <= 1) return;
      var j = studyIndex;
      while (j === studyIndex) {
        j = Math.floor(Math.random() * words.length);
      }
      studyIndex = j;
      studyRevealed = false;
      renderStudy();
    });

    document.addEventListener("keydown", function (e) {
      if (!isStudyMode() || !studyPanel || studyPanel.classList.contains("hidden")) {
        return;
      }
      const t = e.target;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) {
        return;
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        studyPrev.click();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        studyNext.click();
      } else if (e.key === " " || e.key === "Spacebar") {
        e.preventDefault();
        if (!studyRevealed) setStudyReveal(true);
      } else if (e.key === "p" || e.key === "P") {
        e.preventDefault();
        const words = getFilteredWords();
        const w = words[studyIndex];
        if (w) playWord(w);
      }
    });
  }

  function hideLoadError() {
    loadError.classList.add("hidden");
  }

  function showLoadError(msg) {
    loadError.textContent = msg;
    loadError.classList.remove("hidden");
  }

  function getPayloadForDataset(key) {
    var O = window.ChineseOffline;
    if (O) {
      var embedded = O.vocabPayload(key);
      if (embedded) return Promise.resolve(embedded);
      if (O.isOfflineFile()) {
        var jsMap = {
          nhm: "data/nhm-1000-common.js",
          tocfl: "data/vocabulary.js",
          hsk1: "data/hsk-1.js",
          hsk2: "data/hsk-2.js",
          hsk3: "data/hsk-3.js",
          hsk4: "data/hsk-4.js",
          hsk5: "data/hsk-5.js",
        };
        var jsonMap = {
          nhm: "data/nhm-1000-common.json",
          tocfl: "data/vocabulary.json",
          hsk1: "data/hsk-1.json",
          hsk2: "data/hsk-2.json",
          hsk3: "data/hsk-3.json",
          hsk4: "data/hsk-4.json",
          hsk5: "data/hsk-5.json",
        };
        var js = jsMap[key] || "data/vocabulary.js";
        var json = jsonMap[key] || "data/vocabulary.json";
        return Promise.reject(new Error(O.offlineFetchHint(json, js, "")));
      }
    }
    if (key === "hsk5") {
      if (
        typeof window.__VOCAB_HSK5__ !== "undefined" &&
        window.__VOCAB_HSK5__ &&
        window.__VOCAB_HSK5__.levels
      ) {
        return Promise.resolve(window.__VOCAB_HSK5__);
      }
      return fetch("./data/hsk-5.json").then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
    }
    if (key === "hsk4") {
      if (
        typeof window.__VOCAB_HSK4__ !== "undefined" &&
        window.__VOCAB_HSK4__ &&
        window.__VOCAB_HSK4__.levels
      ) {
        return Promise.resolve(window.__VOCAB_HSK4__);
      }
      return fetch("./data/hsk-4.json").then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
    }
    if (key === "hsk3") {
      if (
        typeof window.__VOCAB_HSK3__ !== "undefined" &&
        window.__VOCAB_HSK3__ &&
        window.__VOCAB_HSK3__.levels
      ) {
        return Promise.resolve(window.__VOCAB_HSK3__);
      }
      return fetch("./data/hsk-3.json").then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
    }
    if (key === "hsk2") {
      if (
        typeof window.__VOCAB_HSK2__ !== "undefined" &&
        window.__VOCAB_HSK2__ &&
        window.__VOCAB_HSK2__.levels
      ) {
        return Promise.resolve(window.__VOCAB_HSK2__);
      }
      return fetch("./data/hsk-2.json").then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
    }
    if (key === "hsk1") {
      if (
        typeof window.__VOCAB_HSK1__ !== "undefined" &&
        window.__VOCAB_HSK1__ &&
        window.__VOCAB_HSK1__.levels
      ) {
        return Promise.resolve(window.__VOCAB_HSK1__);
      }
      return fetch("./data/hsk-1.json").then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
    }
    if (key === "nhm") {
      if (
        typeof window.__VOCAB_NHM__ !== "undefined" &&
        window.__VOCAB_NHM__ &&
        window.__VOCAB_NHM__.levels
      ) {
        return Promise.resolve(window.__VOCAB_NHM__);
      }
      return fetch("./data/nhm-1000-common.json").then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
    }
    if (key === "tocfl") {
      if (
        typeof window.__VOCAB__ !== "undefined" &&
        window.__VOCAB__ &&
        window.__VOCAB__.levels
      ) {
        return Promise.resolve(window.__VOCAB__);
      }
      return fetch("./data/vocabulary.json").then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
    }
    return Promise.reject(new Error("Unknown dataset"));
  }

  function setMetaLine(json) {
    if (!json.meta || !json.meta.title) {
      metaLine.textContent = "";
      return;
    }
    var line = json.meta.title;
    if (json.meta.sourceUrl) {
      line += " · " + json.meta.sourceUrl;
    }
    metaLine.textContent = line;
  }

  function applyDataset(key) {
    if (!key) key = "tocfl";
    getPayloadForDataset(key)
      .then(function (json) {
        data = json;
        hideLoadError();
        setMetaLine(json);
        populateLevels();
        populateLessons();
        refresh();
        updateViewLayout();
        persistNav();
      })
      .catch(function (err) {
        showLoadError(err && err.message ? err.message : "Could not load vocabulary data.");
      });
  }

  function readStoredNav() {
    try {
      var nav = {
        level: sessionStorage.getItem(NAV_LEVEL),
        lesson: sessionStorage.getItem(NAV_LESSON),
      };
      if (datasetSelect && !FIXED_DATASET) {
        nav.dataset = sessionStorage.getItem(NAV_DATASET);
      }
      return nav;
    } catch (e) {
      return {};
    }
  }

  function applyStoredNav() {
    var nav = readStoredNav();
    if (datasetSelect && !FIXED_DATASET && (nav.dataset === "tocfl" || nav.dataset === "nhm")) {
      datasetSelect.value = nav.dataset;
    }
    var key = FIXED_DATASET || (datasetSelect && datasetSelect.value) || "tocfl";
    getPayloadForDataset(key)
      .then(function (json) {
        data = json;
        hideLoadError();
        setMetaLine(json);
        populateLevels();
        var li = parseInt(nav.level, 10);
        var lo = parseInt(nav.lesson, 10);
        if (!isNaN(li) && li >= 0 && li < levelSelect.options.length) {
          levelSelect.selectedIndex = li;
        }
        populateLessons();
        if (!isNaN(lo) && lo >= 0 && lo < lessonSelect.options.length) {
          lessonSelect.selectedIndex = lo;
        }
        refresh();
        updateViewLayout();
        persistNav();
      })
      .catch(function (err) {
        showLoadError(err && err.message ? err.message : "Could not load vocabulary data.");
      });
  }

  bindListenersOnce();
  initTheme();
  if (FIXED_DATASET) {
    applyStoredNav();
  } else {
    applyDataset((datasetSelect && datasetSelect.value) || "tocfl");
  }
})();
