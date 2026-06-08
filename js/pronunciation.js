(function () {
  "use strict";

  var NAV_DATASET = "chinese-vocab-nav-dataset";
  var NAV_LEVEL = "chinese-vocab-nav-level";
  var NAV_LESSON = "chinese-vocab-nav-lesson";
  var THEME_KEY = "chinese-vocab-theme";

  function appEl(id) {
    if (window.__UNIFIED_APP__) {
      return document.getElementById("pronounce-" + id);
    }
    return document.getElementById(id);
  }

  var datasetSelect = appEl("dataset-select");
  var levelSelect = appEl("level-select");
  var lessonSelect = appEl("lesson-select");
  var searchInput = appEl("search");
  var listRoot = document.getElementById("pronounce-list");
  var loadError = document.getElementById(
    window.__UNIFIED_APP__ ? "pronounce-load-error" : "load-error"
  );
  var themeToggle = document.getElementById("theme-toggle");

  var data = null;

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

  /** Han + extension A/B common in textbook lists */
  function isHanChar(ch) {
    if (!ch || ch.length === 0) return false;
    var cp = ch.codePointAt(0);
    if (cp >= 0x4e00 && cp <= 0x9fff) return true;
    if (cp >= 0x3400 && cp <= 0x4dbf) return true;
    if (cp >= 0x20000 && cp <= 0x2ceaf) return true;
    return false;
  }

  /**
   * Split on "/" for alternates (e.g. 爸爸/爸), then each segment → ordered 汉字 cluster.
   * @returns {string[][]}
   */
  function clusterChinese(phrase) {
    if (!phrase) return [];
    var raw = String(phrase).trim();
    var segments = raw.split(/\s*\/\s*/);
    var groups = [];
    segments.forEach(function (seg) {
      var chars = [];
      for (var i = 0; i < seg.length; i++) {
        var ch = seg[i];
        if (isHanChar(ch)) chars.push(ch);
      }
      if (chars.length) groups.push(chars);
    });
    if (groups.length === 0 && raw.length) {
      var fallback = [];
      for (var i = 0; i < raw.length; i++) {
        var c = raw[i];
        if (isHanChar(c)) fallback.push(c);
      }
      if (fallback.length) groups.push(fallback);
    }
    return groups;
  }

  /** Strip bracket noise for clearer English TTS */
  function englishForSpeech(s) {
    if (!s) return "";
    return String(s)
      .replace(/\[[^\]]*\]/g, " ")
      .replace(/\([^)]{0,80}\)/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, 600);
  }

  function speakEnglish(text, lang) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(englishForSpeech(text));
    u.lang = lang || "en-US";
    u.rate = 0.88;
    window.speechSynthesis.speak(u);
  }

  function speakChinese(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.lang = "zh-TW";
    u.rate = 0.88;
    window.speechSynthesis.speak(u);
  }

  function normalize(s) {
    return (s || "").toLowerCase();
  }

  function filterWords(words, q) {
    if (!q.trim()) return words;
    var n = normalize(q);
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
    var lvl = data.levels[levelSelect.selectedIndex];
    if (!lvl) return [];
    var les = lvl.lessons[lessonSelect.selectedIndex];
    return les ? les.words : [];
  }

  function getFilteredWords() {
    return filterWords(currentLessonWords(), searchInput.value);
  }

  function getPayloadForDataset(key) {
    var O = window.ChineseOffline;
    if (O) {
      var embedded = O.vocabPayload(key);
      if (embedded) return Promise.resolve(embedded);
      if (O.isOfflineFile()) {
        var js =
          key === "nhm" ? "data/nhm-1000-common.js" : "data/vocabulary.js";
        var json =
          key === "nhm" ? "data/nhm-1000-common.json" : "data/vocabulary.json";
        return Promise.reject(new Error(O.offlineFetchHint(json, js, "")));
      }
    }
    if (key === "nhm") {
      if (window.__VOCAB_NHM__ && window.__VOCAB_NHM__.levels) {
        return Promise.resolve(window.__VOCAB_NHM__);
      }
      return fetch("./data/nhm-1000-common.json").then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
    }
    if (key === "tocfl") {
      if (window.__VOCAB__ && window.__VOCAB__.levels) {
        return Promise.resolve(window.__VOCAB__);
      }
      return fetch("./data/vocabulary.json").then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
    }
    return Promise.reject(new Error("Unknown dataset"));
  }

  function readStoredNav() {
    try {
      return {
        dataset: sessionStorage.getItem(NAV_DATASET),
        level: sessionStorage.getItem(NAV_LEVEL),
        lesson: sessionStorage.getItem(NAV_LESSON),
      };
    } catch (e) {
      return {};
    }
  }

  function applyStoredNav() {
    var nav = readStoredNav();
    if (nav.dataset === "tocfl" || nav.dataset === "nhm") {
      datasetSelect.value = nav.dataset;
    }
    getPayloadForDataset(datasetSelect.value)
      .then(function (json) {
        data = json;
        loadError.classList.add("hidden");
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
        renderList();
        persistNav();
      })
      .catch(function (err) {
        loadError.textContent =
          err && err.message
            ? err.message
            : "Could not load vocabulary. Keep data/*.js next to this page or use a local server.";
        loadError.classList.remove("hidden");
      });
  }

  function populateLevels() {
    levelSelect.innerHTML = "";
    data.levels.forEach(function (lvl) {
      var opt = document.createElement("option");
      opt.value = lvl.id;
      opt.textContent = lvl.label + " — " + lvl.wordCount + " words";
      levelSelect.appendChild(opt);
    });
  }

  function populateLessons() {
    var lvl = data.levels[levelSelect.selectedIndex];
    lessonSelect.innerHTML = "";
    if (!lvl) return;
    lvl.lessons.forEach(function (les, i) {
      var opt = document.createElement("option");
      opt.value = String(i);
      var t = les.title;
      if (les.subtitle) t += " — " + les.subtitle;
      t += " (" + les.words.length + " words)";
      opt.textContent = t;
      lessonSelect.appendChild(opt);
    });
  }

  function persistNav() {
    try {
      sessionStorage.setItem(NAV_DATASET, datasetSelect.value);
      sessionStorage.setItem(NAV_LEVEL, String(levelSelect.selectedIndex));
      sessionStorage.setItem(NAV_LESSON, String(lessonSelect.selectedIndex));
    } catch (e) {}
  }

  function renderList() {
    listRoot.textContent = "";
    var words = getFilteredWords();
    if (words.length === 0) {
      var empty = document.createElement("p");
      empty.className = "pronounce-empty";
      empty.textContent = "No words in this lesson, or nothing matches your search.";
      listRoot.appendChild(empty);
      return;
    }

    words.forEach(function (w, idx) {
      var card = document.createElement("article");
      card.className = "pronounce-card";

      var top = document.createElement("div");
      top.className = "pronounce-card-top";

      var tradBtn = document.createElement("button");
      tradBtn.type = "button";
      tradBtn.className = "pronounce-trad";
      tradBtn.textContent = w.traditional;
      tradBtn.title = "Play Chinese";
      tradBtn.addEventListener("click", function () {
        speakChinese(w.traditional);
      });

      var simp = document.createElement("span");
      simp.className = "pronounce-simp";
      simp.textContent = w.simplified !== w.traditional ? " · " + w.simplified : "";

      var py = document.createElement("p");
      py.className = "pronounce-py";
      py.textContent = w.pinyin;

      top.appendChild(tradBtn);
      top.appendChild(simp);
      card.appendChild(top);
      card.appendChild(py);

      var clusterWrap = document.createElement("div");
      clusterWrap.className = "pronounce-cluster-wrap";
      var clusterTitle = document.createElement("span");
      clusterTitle.className = "pronounce-cluster-label";
      clusterTitle.textContent = "Character clusters";
      clusterWrap.appendChild(clusterTitle);

      var groups = clusterChinese(w.traditional || w.simplified);
      if (groups.length === 0) {
        var none = document.createElement("span");
        none.className = "pronounce-cluster-none";
        none.textContent = "—";
        clusterWrap.appendChild(none);
      } else {
        var row = document.createElement("div");
        row.className = "pronounce-cluster-row";
        groups.forEach(function (grp, gi) {
          if (gi > 0) {
            var orEl = document.createElement("span");
            orEl.className = "pronounce-or";
            orEl.textContent = "or";
            row.appendChild(orEl);
          }
          grp.forEach(function (ch) {
            var pill = document.createElement("button");
            pill.type = "button";
            pill.className = "cluster-pill";
            pill.textContent = ch;
            pill.title = "Play: " + ch;
            pill.addEventListener("click", function () {
              speakChinese(ch);
            });
            row.appendChild(pill);
          });
        });
        clusterWrap.appendChild(row);
      }
      card.appendChild(clusterWrap);

      var enBlock = document.createElement("div");
      enBlock.className = "pronounce-en-block";
      var enLabel = document.createElement("span");
      enLabel.className = "pronounce-en-label";
      enLabel.textContent = "English";
      var enText = document.createElement("p");
      enText.className = "pronounce-en-text";
      enText.textContent = w.english;

      var enBtns = document.createElement("div");
      enBtns.className = "pronounce-en-btns";
      var bUs = document.createElement("button");
      bUs.type = "button";
      bUs.className = "btn-en-speak";
      bUs.textContent = "Play English (US)";
      bUs.addEventListener("click", function () {
        speakEnglish(w.english, "en-US");
      });
      var bIn = document.createElement("button");
      bIn.type = "button";
      bIn.className = "btn-en-speak btn-en-speak--ghost";
      bIn.textContent = "Play English (India)";
      bIn.addEventListener("click", function () {
        speakEnglish(w.english, "en-IN");
      });

      enBtns.appendChild(bUs);
      enBtns.appendChild(bIn);
      enBlock.appendChild(enLabel);
      enBlock.appendChild(enText);
      enBlock.appendChild(enBtns);
      card.appendChild(enBlock);

      var hi = document.createElement("p");
      hi.className = "pronounce-hi";
      hi.textContent = w.hindi;

      card.appendChild(hi);
      listRoot.appendChild(card);
    });
  }

  function bind() {
    if (!datasetSelect || !levelSelect || !lessonSelect || !searchInput || !listRoot) return;

    if (themeToggle && !window.__UNIFIED_APP__) {
      themeToggle.addEventListener("click", function () {
        setTheme(getTheme() === "dark" ? "light" : "dark");
      });
      syncThemeToggle();
    }

    datasetSelect.addEventListener("change", function () {
      searchInput.value = "";
      getPayloadForDataset(datasetSelect.value)
        .then(function (json) {
          data = json;
          populateLevels();
          populateLessons();
          renderList();
          persistNav();
        })
        .catch(function () {
          loadError.classList.remove("hidden");
        });
    });

    levelSelect.addEventListener("change", function () {
      searchInput.value = "";
      populateLessons();
      persistNav();
      renderList();
    });

    lessonSelect.addEventListener("change", function () {
      searchInput.value = "";
      persistNav();
      renderList();
    });

    searchInput.addEventListener("input", function () {
      renderList();
    });
  }

  bind();
  applyStoredNav();
})();
