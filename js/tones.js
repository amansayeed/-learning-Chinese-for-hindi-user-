(function () {
  "use strict";

  var THEME_KEY = "chinese-vocab-theme";
  var themeToggle = document.getElementById("theme-toggle");
  var loadError = document.getElementById("tone-load-error");

  function getTheme() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function syncThemeToggle() {
    if (!themeToggle) return;
    var dark = getTheme() === "dark";
    themeToggle.textContent = dark ? "Light mode" : "Dark mode";
    themeToggle.setAttribute("aria-pressed", dark ? "true" : "false");
    themeToggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  }

  function setTheme(mode) {
    if (mode !== "light" && mode !== "dark") return;
    document.documentElement.setAttribute("data-theme", mode);
    try {
      localStorage.setItem(THEME_KEY, mode);
    } catch (e) {}
    syncThemeToggle();
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      setTheme(getTheme() === "dark" ? "light" : "dark");
    });
    syncThemeToggle();
  }

  function showLoadError(msg) {
    if (loadError) {
      loadError.textContent = msg;
      loadError.classList.remove("hidden");
    }
  }

  function speak(text, lang, rate) {
    if (!window.speechSynthesis || !text) return;
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.lang = lang;
    u.rate = rate != null ? rate : lang.indexOf("zh") === 0 ? 0.88 : 0.92;
    window.speechSynthesis.speak(u);
  }

  function speakZhTrad(s) {
    speak(s, "zh-TW", 0.88);
  }

  function speakZhSimp(s) {
    speak(s, "zh-TW", 0.88);
  }

  function speakEn(s) {
    speak(s, "en-US", 0.92);
  }

  function speakHi(s) {
    speak(s, "hi-IN", 0.9);
  }

  function charButton(text, langAttr, title, onSpeak, extraClass) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "tone-char-tap" + (extraClass ? " " + extraClass : "");
    b.textContent = text;
    b.setAttribute("lang", langAttr);
    b.setAttribute("title", title);
    b.setAttribute("aria-label", title + ": " + text);
    b.addEventListener("click", function () {
      onSpeak();
    });
    return b;
  }

  function meanButton(className, label, text, lang, speakFn) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "tone-mean-tap " + className;
    b.setAttribute("lang", lang || "");
    b.setAttribute("title", "Hear " + label);
    var small = document.createElement("span");
    small.className = "tone-mean-tap__label";
    small.textContent = label;
    var body = document.createElement("span");
    body.className = "tone-mean-tap__text";
    body.textContent = text;
    b.appendChild(small);
    b.appendChild(body);
    b.setAttribute("aria-label", label + ": " + text);
    b.addEventListener("click", function () {
      speakFn(text);
    });
    return b;
  }

  function runApp(payload) {
    var quartets = payload && payload.quartets ? payload.quartets : [];
    var listEl = document.getElementById("tone-quartet-list");
    var tFirst = document.getElementById("tones-first");
    var tPrev = document.getElementById("tones-prev");
    var tNext = document.getElementById("tones-next");
    var tLast = document.getElementById("tones-last");
    var tFirst2 = document.getElementById("tones-first2");
    var tPrev2 = document.getElementById("tones-prev2");
    var tNext2 = document.getElementById("tones-next2");
    var tLast2 = document.getElementById("tones-last2");
    var tInfo = document.getElementById("tones-page-info");
    var tInfo2 = document.getElementById("tones-page-info2");

    if (!quartets || !quartets.length) {
      showLoadError("No four-tone syllable sets to display.");
      return;
    }

    var qstate = {
      page: 0,
      pageSize: 6
    };

    function getPageCount() {
      return Math.max(1, Math.ceil(quartets.length / qstate.pageSize));
    }

    function clampPage() {
      var pc = getPageCount();
      if (qstate.page < 0) qstate.page = 0;
      if (qstate.page > pc - 1) qstate.page = pc - 1;
    }

    function updatePager() {
      var pc = getPageCount();
      clampPage();
      var start = qstate.page * qstate.pageSize;
      var end = Math.min(quartets.length, start + qstate.pageSize);
      var msg =
        "Syllables " +
        (start + 1) +
        "–" +
        end +
        " of " +
        quartets.length +
        " · Page " +
        (qstate.page + 1) +
        " / " +
        pc;
      if (tInfo) tInfo.textContent = msg;
      if (tInfo2) tInfo2.textContent = msg;

      var atFirst = qstate.page === 0;
      var atLast = qstate.page >= pc - 1;
      [tFirst, tPrev, tFirst2, tPrev2].forEach(function (b) {
        if (b) b.disabled = atFirst;
      });
      [tNext, tLast, tNext2, tLast2].forEach(function (b) {
        if (b) b.disabled = atLast;
      });
    }

    function renderQuartets() {
      if (!listEl) return;
      listEl.innerHTML = "";
      clampPage();
      var start = qstate.page * qstate.pageSize;
      var slice = quartets.slice(start, start + qstate.pageSize);
      slice.forEach(function (q) {
        var article = document.createElement("article");
        article.className = "tone-card";
        article.id = "syllable-" + q.id;

        var h = document.createElement("h2");
        h.className = "tone-card__title";
        h.textContent = "Syllable · " + q.label;
        article.appendChild(h);

        var grid = document.createElement("div");
        grid.className = "tone-card__grid tone-card__grid--row";

        q.tones.forEach(function (row) {
          var cell = document.createElement("div");
          cell.className = "tone-cell tone-cell--t" + row.tone;

          var py = document.createElement("div");
          py.className = "tone-cell__py tone-t" + row.tone;
          py.textContent = row.pinyin;

          var han = document.createElement("div");
          han.className = "tone-cell__han";
          var same = row.traditional === row.simplified;
          if (same) {
            han.appendChild(
              charButton(
                row.traditional,
                "zh-Hant",
                "Chinese (tap for Mandarin audio)",
                function () {
                  speakZhTrad(row.traditional);
                },
                "tone-char-tap--han tone-char-tap--trad"
              )
            );
          } else {
            han.appendChild(
              charButton(
                row.traditional,
                "zh-Hant",
                "Traditional — Mandarin audio",
                function () {
                  speakZhTrad(row.traditional);
                },
                "tone-char-tap--han tone-char-tap--trad"
              )
            );
            var sep = document.createElement("span");
            sep.className = "tone-cell__sep";
            sep.setAttribute("aria-hidden", "true");
            sep.textContent = "·";
            han.appendChild(sep);
            han.appendChild(
              charButton(
                row.simplified,
                "zh-Hans",
                "Simplified — Mandarin audio",
                function () {
                  speakZhSimp(row.simplified);
                },
                "tone-char-tap--han tone-char-tap--simp"
              )
            );
          }

          var mean = document.createElement("div");
          mean.className = "tone-cell__mean";
          mean.appendChild(meanButton("tone-mean-tap--en", "English", row.english, "en", speakEn));
          mean.appendChild(meanButton("tone-mean-tap--hi", "हिन्दी", row.hindi, "hi", speakHi));

          cell.appendChild(py);
          cell.appendChild(han);
          cell.appendChild(mean);
          grid.appendChild(cell);
        });

        article.appendChild(grid);
        listEl.appendChild(article);
      });
    }

    function bindQuartetPager() {
      function goFirst() {
        qstate.page = 0;
        renderQuartets();
        updatePager();
      }
      function goPrev() {
        qstate.page -= 1;
        renderQuartets();
        updatePager();
      }
      function goNext() {
        qstate.page += 1;
        renderQuartets();
        updatePager();
      }
      function goLast() {
        qstate.page = getPageCount() - 1;
        renderQuartets();
        updatePager();
      }

      [
        [tFirst, goFirst],
        [tFirst2, goFirst],
        [tPrev, goPrev],
        [tPrev2, goPrev],
        [tNext, goNext],
        [tNext2, goNext],
        [tLast, goLast],
        [tLast2, goLast],
      ].forEach(function (pair) {
        if (!pair[0]) return;
        pair[0].addEventListener("click", pair[1]);
      });
    }

    renderQuartets();
    bindQuartetPager();
    updatePager();
  }

  function payloadFromGlobals() {
    var O = window.ChineseOffline;
    if (O) {
      var p = O.tonePayload();
      if (p) return p;
    }
    if (window.__TONE_PAGE_DATA__ && window.__TONE_PAGE_DATA__.quartets) {
      return window.__TONE_PAGE_DATA__;
    }
    if (window.__TONE_DATA__ && window.__TONE_DATA__.quartets) {
      return window.__TONE_DATA__;
    }
    return null;
  }

  var pre = payloadFromGlobals();
  if (pre) {
    runApp(pre);
  } else if (window.ChineseOffline && window.ChineseOffline.isOfflineFile()) {
    showLoadError(window.ChineseOffline.toneLoadError());
  } else {
    fetch("./data/tone-quartets.json")
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (json) {
        runApp({
          quartets: (json && json.quartets) || [],
        });
      })
      .catch(function () {
        showLoadError(
          "Could not load tone data. Run node scripts/build-offline-bundles.js and copy the full folder to your device, or use a local web server."
        );
      });
  }
})();
