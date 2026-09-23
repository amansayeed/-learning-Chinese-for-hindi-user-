(function () {
  "use strict";

  var payload = window.__CHARACTERS__;
  if (!payload || !Array.isArray(payload.characters)) return;

  var PAGE_SIZE = 50;
  var controllers = [];
  var byId = {};
  payload.characters.forEach(function (item) {
    byId[item.id] = item;
  });

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fold(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  }

  function syllableTone(syllable) {
    var decomposed = String(syllable || "").normalize("NFD");
    if (decomposed.indexOf("\u0304") >= 0) return "1";
    if (decomposed.indexOf("\u0301") >= 0) return "2";
    if (decomposed.indexOf("\u030c") >= 0) return "3";
    if (decomposed.indexOf("\u0300") >= 0) return "4";
    var numbered = decomposed.match(/[1-5]/);
    return numbered ? numbered[0] : "5";
  }

  function shortPinyin(value) {
    return String(value || "").split("/")[0].replace(/\s+/g, "");
  }

  function pinyinKey(item) {
    var raw = String(item.pinyin || "").split("/")[0];
    return {
      letters: fold(raw).replace(/[^a-z]/g, ""),
      tones: raw.split(/\s+/).filter(Boolean).map(syllableTone).join(""),
      traditional: String(item.traditional || ""),
    };
  }

  function comparePinyin(a, b) {
    var ka = pinyinKey(a);
    var kb = pinyinKey(b);
    if (ka.letters !== kb.letters) return ka.letters < kb.letters ? -1 : 1;
    if (ka.tones !== kb.tones) return ka.tones < kb.tones ? -1 : 1;
    if (ka.traditional !== kb.traditional) {
      return ka.traditional < kb.traditional ? -1 : 1;
    }
    return 0;
  }

  function formatNumber(value) {
    return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function one(root, role) {
    return root.querySelector('[data-character-role="' + role + '"]');
  }

  function speak(text) {
    if (!text || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    var utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "zh-TW";
    utterance.rate = 0.78;
    var voices =
      typeof window.speechSynthesis.getVoices === "function"
        ? window.speechSynthesis.getVoices()
        : [];
    var taiwanVoice = voices.filter(function (voice) {
      return /^zh[-_]TW$/i.test(voice.lang || "");
    })[0];
    if (taiwanVoice) utterance.voice = taiwanVoice;
    window.speechSynthesis.speak(utterance);
  }

  function formsDiffer(item) {
    return String(item.traditional || "") !== String(item.simplified || "");
  }

  function Controller(root) {
    this.root = root;
    this.diff = !!(root.hasAttribute && root.hasAttribute("data-character-diff"));
    this.level = root.getAttribute("data-character-level") || "1000";
    this.page = 1;
    this.selected = null;
    this.bind();
    this.render();
  }

  Controller.prototype.levelInfo = function () {
    var selected = this.level;
    return payload.levels.filter(function (level) {
      return level.id === selected;
    })[0] || payload.levels[0];
  };

  Controller.prototype.filtered = function () {
    var search = one(this.root, "search");
    var query = fold(search ? search.value : "");
    var limit = this.levelInfo().limit;
    var pool = this.diff
      ? payload.characters.filter(formsDiffer)
      : payload.characters.slice(0, limit);
    return pool
      .filter(function (item) {
        if (!query) return true;
        return fold([
          item.traditional,
          item.simplified,
          item.pinyin,
          item.english,
          item.hindi,
          String(item.rank),
          String(item.learningRank),
        ].join(" ")).indexOf(query) >= 0;
      })
      .sort(comparePinyin);
  };

  Controller.prototype.renderLevels = function () {
    var wrap = one(this.root, "levels");
    if (!wrap) return;
    var self = this;
    wrap.innerHTML = payload.levels.map(function (level) {
      return (
        '<button type="button" class="character-level' +
        (self.level === level.id ? " is-active" : "") +
        '" data-character-level="' +
        level.id +
        '" aria-pressed="' +
        (self.level === level.id ? "true" : "false") +
        '"><strong>' +
        escapeHtml(level.label) +
        "</strong><span>" +
        escapeHtml(level.description) +
        "</span></button>"
      );
    }).join("");
  };

  Controller.prototype.renderGrid = function () {
    var list = this.filtered();
    var pages = Math.max(1, Math.ceil(list.length / PAGE_SIZE));
    this.page = Math.min(Math.max(1, this.page), pages);
    var start = (this.page - 1) * PAGE_SIZE;
    var visible = list.slice(start, start + PAGE_SIZE);
    var count = one(this.root, "count");
    var grid = one(this.root, "grid");
    var pager = one(this.root, "pagination");
    if (count) {
      count.textContent =
        formatNumber(list.length) +
        " individual character" +
        (list.length === 1 ? "" : "s");
    }
    if (grid) {
      grid.innerHTML = visible.length
        ? '<div class="character-list-wrap"><table class="character-list">' +
          '<thead><tr><th scope="col">#</th><th scope="col">Character</th>' +
          '<th scope="col">Pinyin</th><th scope="col">Meaning</th></tr></thead><tbody>' +
          visible.map(function (item, index) {
            return (
              '<tr><td class="character-list__rank" data-label="#">' +
              (start + index + 1) +
              '</td><td data-label="Character"><div class="character-list__scripts">' +
              '<button type="button" class="character-list__han character-list__han--traditional" ' +
              'data-character-speak="' +
              escapeHtml(item.traditional) +
              '" aria-label="Listen to Traditional ' +
              escapeHtml(item.traditional) +
              '" title="Traditional · play Taiwan Mandarin">' +
              escapeHtml(item.traditional) +
              "</button>" +
              '<button type="button" class="character-list__han character-list__han--simplified" ' +
              'data-character-details="' +
              escapeHtml(item.id) +
              '" aria-label="Open details for Simplified ' +
              escapeHtml(item.simplified) +
              '" title="Simplified · click for details">' +
              escapeHtml(item.simplified) +
              '</button></div></td>' +
              '<td class="character-list__pinyin" data-label="Pinyin">' +
              escapeHtml(shortPinyin(item.pinyin)) +
              '</td><td class="character-list__meaning" data-label="Meaning"><strong>' +
              escapeHtml(item.english) +
              '</strong><small lang="hi">' +
              escapeHtml(item.hindi) +
              "</small></td></tr>"
            );
          }).join("") +
          "</tbody></table></div>"
        : '<div class="empty-state character-empty"><strong>No matching characters</strong><p>Try another character, pinyin or meaning.</p></div>';
    }
    if (!pager) return;
    pager.classList.toggle("hidden", list.length <= PAGE_SIZE);
    pager.innerHTML =
      '<button type="button" class="btn-page" data-character-page="first"' +
      (this.page === 1 ? " disabled" : "") +
      ">First</button>" +
      '<button type="button" class="btn-page" data-character-page="prev"' +
      (this.page === 1 ? " disabled" : "") +
      ">Prev</button>" +
      '<span class="words-page-info">Page ' +
      this.page +
      " of " +
      pages +
      "</span>" +
      '<button type="button" class="btn-page" data-character-page="next"' +
      (this.page === pages ? " disabled" : "") +
      ">Next</button>" +
      '<button type="button" class="btn-page" data-character-page="last"' +
      (this.page === pages ? " disabled" : "") +
      ">Last</button>";
  };

  Controller.prototype.exampleHtml = function (example) {
    return (
      '<article class="character-example">' +
      '<button type="button" class="character-example__word" data-character-speak="' +
      escapeHtml(example.traditional) +
      '" aria-label="Listen to ' +
      escapeHtml(example.traditional) +
      '">' +
      escapeHtml(example.traditional) +
      (example.simplified && example.simplified !== example.traditional
        ? '<small lang="zh-Hans">' + escapeHtml(example.simplified) + "</small>"
        : "") +
      "</button>" +
      '<div><strong>' +
      escapeHtml(example.pinyin) +
      "</strong><span>" +
      escapeHtml(example.english) +
      "</span>" +
      (example.hindi ? '<small lang="hi">' + escapeHtml(example.hindi) + "</small>" : "") +
      "</div></article>"
    );
  };

  Controller.prototype.openDetails = function (item) {
    var overlay = one(this.root, "details");
    var content = one(this.root, "details-content");
    if (!overlay || !content) return;
    this.selected = item;
    content.innerHTML =
      '<div class="character-detail__hero">' +
      '<button type="button" class="character-detail__han" data-character-speak="' +
      escapeHtml(item.traditional) +
      '" aria-label="Listen to ' +
      escapeHtml(item.traditional) +
      '">' +
      escapeHtml(item.traditional) +
      "</button>" +
      '<div><p class="eyebrow">' +
      escapeHtml(item.learningBand) +
      " · learning order #" +
      formatNumber(item.learningRank) +
      '</p><h2 id="character-detail-title">' +
      escapeHtml(item.pinyin || item.traditional) +
      "</h2><p>" +
      "MOE frequency rank #" +
      formatNumber(item.rank) +
      " · " +
      formatNumber(item.frequency) +
      " occurrences · " +
      item.percentage +
      "% of the MOE corpus</p></div></div>" +
      '<button type="button" class="primary-button character-detail__listen" data-character-speak="' +
      escapeHtml(item.traditional) +
      '">🔊 Play Taiwan Mandarin pronunciation</button>' +
      '<dl class="character-facts">' +
      "<div><dt>Traditional</dt><dd lang=\"zh-Hant\">" +
      escapeHtml(item.traditional) +
      "</dd></div><div><dt>Simplified</dt><dd lang=\"zh-Hans\">" +
      escapeHtml(item.simplified) +
      "</dd></div><div><dt>Pinyin</dt><dd>" +
      escapeHtml(item.pinyin) +
      "</dd></div><div><dt>English</dt><dd>" +
      escapeHtml(item.english) +
      '</dd></div><div><dt>हिन्दी</dt><dd lang="hi">' +
      escapeHtml(item.hindi) +
      "</dd></div></dl>" +
      '<section class="character-examples"><h3>Example words</h3>' +
      (item.examples && item.examples.length
        ? item.examples.map(this.exampleHtml).join("")
        : "<p>No example word is available in the current vocabulary database.</p>") +
      "</section>";
    overlay.classList.remove("hidden");
    overlay.setAttribute("aria-hidden", "false");
    document.body.classList.add("character-dialog-open");
    var close = one(this.root, "details-close");
    if (close) close.focus();
  };

  Controller.prototype.closeDetails = function () {
    var overlay = one(this.root, "details");
    if (!overlay) return;
    overlay.classList.add("hidden");
    overlay.setAttribute("aria-hidden", "true");
    document.body.classList.remove("character-dialog-open");
    var selected = this.selected;
    this.selected = null;
    if (selected) {
      var tile = this.root.querySelector('[data-character-details="' + selected.id + '"]');
      if (tile) tile.focus();
    }
  };

  Controller.prototype.render = function () {
    var title = one(this.root, "title");
    var subtitle = one(this.root, "subtitle");
    if (this.diff) {
      var different = payload.characters.filter(formsDiffer).length;
      if (title) title.textContent = "Traditional and Simplified difference";
      if (subtitle) {
        subtitle.textContent =
          formatNumber(different) +
          " characters from the 3,000 list whose Traditional and Simplified forms are different, sorted A–Z by Pinyin.";
      }
      var levels = one(this.root, "levels");
      if (levels) {
        levels.innerHTML = "";
        levels.classList.add("hidden");
      }
    } else {
      var level = this.levelInfo();
      if (title) title.textContent = level.label + " · " + level.description;
      if (subtitle) {
        subtitle.textContent =
          "The first " +
          formatNumber(level.limit) +
          " characters in the cumulative learning set, sorted A–Z by Pinyin. Each row represents one character, never a word.";
      }
      this.renderLevels();
    }
    this.renderGrid();
  };

  Controller.prototype.bind = function () {
    var self = this;
    this.root.addEventListener("click", function (event) {
      var target = event.target;
      var level = target.closest("[data-character-level]");
      if (level && level !== self.root && !self.diff) {
        self.level = level.getAttribute("data-character-level");
        self.page = 1;
        var search = one(self.root, "search");
        if (search) search.value = "";
        self.render();
        return;
      }
      var speech = target.closest("[data-character-speak]");
      if (speech) {
        speak(speech.getAttribute("data-character-speak"));
        return;
      }
      var detailButton = target.closest("[data-character-details]");
      if (detailButton) {
        self.openDetails(byId[detailButton.getAttribute("data-character-details")]);
        return;
      }
      if (target.closest("[data-character-close]")) {
        self.closeDetails();
        return;
      }
      var overlay = one(self.root, "details");
      if (target === overlay) {
        self.closeDetails();
        return;
      }
      var page = target.closest("[data-character-page]");
      if (page && !page.disabled) {
        var pages = Math.max(1, Math.ceil(self.filtered().length / PAGE_SIZE));
        var action = page.getAttribute("data-character-page");
        if (action === "first") self.page = 1;
        if (action === "prev") self.page = Math.max(1, self.page - 1);
        if (action === "next") self.page = Math.min(pages, self.page + 1);
        if (action === "last") self.page = pages;
        self.renderGrid();
        window.scrollTo(0, 0);
      }
    });
    var search = one(this.root, "search");
    if (search) {
      search.addEventListener("input", function () {
        self.page = 1;
        self.renderGrid();
      });
    }
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && self.selected) self.closeDetails();
    });
  };

  function init() {
    document.querySelectorAll("[data-character-browser], [data-character-diff]").forEach(function (root) {
      controllers.push(new Controller(root));
    });
  }

  window.CharactersUI = {
    count: payload.characters.length,
    comparePinyin: comparePinyin,
    speak: speak,
    mount: function (root) {
      var controller = new Controller(root);
      controllers.push(controller);
      return controller;
    },
    refresh: function () {
      controllers.forEach(function (controller) {
        controller.render();
      });
    },
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
