(function () {
  "use strict";

  var store = window.VocabStore;
  var payloads = [window.__TOCFL_8000__, window.__TOCFL_CCCC__].filter(Boolean);
  var payload = payloads.reduce(function (combined, item) {
    combined.levels = combined.levels.concat(item.levels || []);
    combined.words = combined.words.concat(item.words || []);
    return combined;
  }, { levels: [], words: [] });

  var LEVEL_ORDER = [
    "novice-1", "novice-2", "level-1", "level-2", "level-3", "level-4", "level-5",
    "sprouting", "growing", "thriving",
  ];

  function uniqueKeyParts(word) {
    var pinyin = String(word.pinyin || "").replace(/\s+/g, "");
    var parts = [];
    [word.traditional, word.simplified].forEach(function (value) {
      String(value || "").split(/[/／]/).forEach(function (form) {
        form = form.replace(/\s+/g, "");
        if (form) parts.push(form + "\u001f" + pinyin);
      });
    });
    return parts;
  }

  function uniqueWords(list) {
    var rank = {};
    LEVEL_ORDER.forEach(function (id, index) { rank[id] = index; });
    var ordered = (list || []).slice().sort(function (a, b) {
      var ra = rank[a.level];
      var rb = rank[b.level];
      if (ra == null) ra = 99;
      if (rb == null) rb = 99;
      if (ra !== rb) return ra - rb;
      return 0;
    });
    var seen = {};
    var kept = [];
    ordered.forEach(function (word) {
      var keys = uniqueKeyParts(word);
      var duplicate = keys.some(function (key) { return seen[key]; });
      if (duplicate) return;
      keys.forEach(function (key) { seen[key] = true; });
      kept.push(word);
    });
    return kept;
  }

  var sourceWords = uniqueWords(payload.words || []);
  payload.levels = payload.levels.map(function (level) {
    var count = sourceWords.filter(function (word) { return word.level === level.id; }).length;
    return {
      id: level.id,
      code: level.code,
      label: level.label,
      wordCount: count,
    };
  }).filter(function (level) {
    return level.wordCount > 0;
  });
  if (!store || !sourceWords.length) return;
  if (store.registerSupplemental) store.registerSupplemental(sourceWords);

  var PAGE_SIZE = 50;
  var controllers = [];

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function one(root, role) {
    return root.querySelector('[data-tocfl-role="' + role + '"]');
  }

  function categoryIcon(category) {
    if (window.VocabularyUI && window.VocabularyUI.categoryIcon) {
      return window.VocabularyUI.categoryIcon(category);
    }
    return "📘";
  }

  function Controller(root) {
    this.root = root;
    this.mode = root.hasAttribute("data-tocfl-pronunciation") ? "pronunciation" : "browser";
    this.level =
      root.getAttribute("data-tocfl-level") ||
      (payload.levels[0] && payload.levels[0].id) ||
      "novice-1";
    this.category = "all";
    this.subcategory = "all";
    this.page = 1;
    this.bind();
    this.render();
  }

  Controller.prototype.wordsForLevel = function () {
    return store.pinyinOrder(sourceWords.filter(function (word) {
      return word.level === this.level;
    }, this));
  };

  Controller.prototype.categoryCounts = function () {
    var counts = {};
    this.wordsForLevel().forEach(function (word) {
      counts[word.category] = (counts[word.category] || 0) + 1;
    });
    return counts;
  };

  Controller.prototype.subcategoryCounts = function () {
    var counts = {};
    var selectedCategory = this.category;
    if (selectedCategory === "all") return counts;
    this.wordsForLevel().forEach(function (word) {
      if (word.category !== selectedCategory) return;
      var subcategory = word.subcategory || word.category;
      counts[subcategory] = (counts[subcategory] || 0) + 1;
    });
    return counts;
  };

  Controller.prototype.filteredWords = function () {
    var search = one(this.root, "search");
    var status = one(this.root, "status");
    var query = store.fold(search ? search.value : "");
    var selectedCategory = this.category;
    var selectedSubcategory = this.subcategory;
    var selectedStatus = status ? status.value : "all";
    var learning = window.LearningState;
    return store.pinyinOrder(this.wordsForLevel().filter(function (word) {
      if (selectedCategory !== "all" && word.category !== selectedCategory) return false;
      if (
        selectedSubcategory !== "all" &&
        (word.subcategory || word.category) !== selectedSubcategory
      ) return false;
      if (
        query &&
        store.fold([
          word.traditional,
          word.simplified,
          word.pinyin,
          word.english,
          word.hindi,
          word.category,
          word.subcategory,
          word.partOfSpeech,
        ].join(" ")).indexOf(query) < 0
      ) return false;
      if (learning && selectedStatus === "learned" && !learning.isLearned(word.id)) return false;
      if (learning && selectedStatus === "unlearned" && learning.isLearned(word.id)) return false;
      if (learning && selectedStatus === "favorite" && !learning.isFavorite(word.id)) return false;
      if (learning && selectedStatus === "difficult" && !learning.isDifficult(word.id)) return false;
      return true;
    }));
  };

  Controller.prototype.levelInfo = function () {
    var current = this.level;
    return payload.levels.filter(function (level) {
      return level.id === current;
    })[0] || payload.levels[0] || {
      id: current,
      code: current,
      label: current,
      wordCount: 0,
    };
  };

  Controller.prototype.levelCounts = function () {
    var counts = {};
    payload.levels.forEach(function (level) {
      counts[level.id] = level.wordCount;
    });
    return counts;
  };

  Controller.prototype.renderLevels = function () {
    var wrap = one(this.root, "levels");
    if (!wrap) return;
    var counts = this.levelCounts();
    var self = this;
    wrap.innerHTML = payload.levels.map(function (level) {
      return (
        '<button type="button" class="level-switch__button' +
        (self.level === level.id ? " is-active" : "") +
        '" data-tocfl-level="' +
        escapeHtml(level.id) +
        '" aria-pressed="' +
        (self.level === level.id ? "true" : "false") +
        '"><span>' +
        escapeHtml(level.label) +
        "</span><small>" +
        (counts[level.id] || 0) +
        " words</small></button>"
      );
    }).join("");
  };

  Controller.prototype.renderCategories = function () {
    var wrap = one(this.root, "categories");
    if (!wrap) return;
    var counts = this.categoryCounts();
    var categories = Object.keys(counts).sort(function (a, b) {
      return counts[b] - counts[a] || a.localeCompare(b);
    });
    var self = this;
    wrap.innerHTML =
      '<button type="button" class="topic-chip' +
      (this.category === "all" ? " is-active" : "") +
      '" data-tocfl-category="all"><span aria-hidden="true">📚</span> All (' +
      this.wordsForLevel().length +
      ")</button>" +
      categories.map(function (category) {
        return (
          '<button type="button" class="topic-chip' +
          (self.category === category ? " is-active" : "") +
          '" data-tocfl-category="' +
          escapeHtml(category) +
          '"><span aria-hidden="true">' +
          categoryIcon(category) +
          "</span> " +
          escapeHtml(category) +
          " (" +
          counts[category] +
          ")</button>"
        );
      }).join("");
  };

  Controller.prototype.renderSubcategories = function () {
    var wrap = one(this.root, "subcategories");
    if (!wrap) return;
    var counts = this.subcategoryCounts();
    var subcategories = Object.keys(counts).sort(function (a, b) {
      return counts[b] - counts[a] || a.localeCompare(b);
    });
    var self = this;
    wrap.classList.toggle("hidden", this.category === "all" || !subcategories.length);
    if (this.category === "all" || !subcategories.length) {
      wrap.innerHTML = "";
      return;
    }
    wrap.innerHTML =
      '<button type="button" class="topic-chip' +
      (this.subcategory === "all" ? " is-active" : "") +
      '" data-tocfl-subcategory="all">All ' +
      escapeHtml(this.category) +
      " (" +
      this.categoryCounts()[this.category] +
      ")</button>" +
      subcategories.map(function (subcategory) {
        return (
          '<button type="button" class="topic-chip' +
          (self.subcategory === subcategory ? " is-active" : "") +
          '" data-tocfl-subcategory="' +
          escapeHtml(subcategory) +
          '">' +
          escapeHtml(subcategory) +
          " (" +
          counts[subcategory] +
          ")</button>"
        );
      }).join("");
  };

  Controller.prototype.groupOf = function (word, byCategory) {
    return (byCategory ? word.category : word.subcategory || word.category) || "Other";
  };

  /* Smart order interleaves topics, so the list is re-ordered into one block per
     topic. A heading then covers a contiguous run and survives pagination. */
  Controller.prototype.groupedWords = function () {
    var byCategory = this.category === "all";
    var self = this;
    var buckets = {};
    this.filteredWords().forEach(function (word) {
      var key = self.groupOf(word, byCategory);
      if (!buckets[key]) buckets[key] = [];
      buckets[key].push(word);
    });
    /* Largest topic first, matching the order of the chips above the list. */
    var keys = Object.keys(buckets).sort(function (a, b) {
      return buckets[b].length - buckets[a].length || a.localeCompare(b);
    });
    var words = [];
    var totals = {};
    keys.forEach(function (key) {
      totals[key] = buckets[key].length;
      words = words.concat(buckets[key]);
    });
    return { words: words, totals: totals, byCategory: byCategory };
  };

  Controller.prototype.groupHead = function (run, total, attribute) {
    var shown = run.words.length;
    /* A topic split across pages says so rather than promising words that the
       current page does not actually show. */
    var label =
      shown === total
        ? total + " word" + (total === 1 ? "" : "s")
        : shown + " of " + total + " words";
    return (
      '<button type="button" class="vocab-group__head" ' +
      attribute +
      '="' +
      escapeHtml(run.key) +
      '" aria-label="Show only ' +
      escapeHtml(run.key) +
      '"><span class="vocab-group__icon" aria-hidden="true">' +
      categoryIcon(run.key) +
      '</span><span class="vocab-group__name">' +
      escapeHtml(run.key) +
      '</span><span class="vocab-group__count">' +
      label +
      "</span></button>"
    );
  };

  Controller.prototype.renderGroups = function (results, visible, start, grouped) {
    var self = this;
    var runs = [];
    visible.forEach(function (word, index) {
      var key = self.groupOf(word, grouped.byCategory);
      var open = runs[runs.length - 1];
      if (open && open.key === key) {
        open.words.push(word);
        return;
      }
      runs.push({ key: key, words: [word], start: start + index });
    });

    var attribute = grouped.byCategory ? "data-tocfl-category" : "data-tocfl-subcategory";
    if (
      this.mode === "pronunciation" &&
      window.ChinesePronunciation &&
      window.ChinesePronunciation.renderWords
    ) {
      results.textContent = "";
      runs.forEach(function (run) {
        var section = document.createElement("section");
        section.className = "vocab-group";
        section.innerHTML =
          self.groupHead(run, grouped.totals[run.key], attribute) +
          '<div class="vocab-group__body"></div>';
        results.appendChild(section);
        var body = section.querySelector(".vocab-group__body");
        if (body) window.ChinesePronunciation.renderWords(body, run.words);
      });
      return;
    }

    if (!window.VocabularyUI || !window.VocabularyUI.renderWordList) return;
    results.innerHTML = runs
      .map(function (run) {
        return (
          '<section class="vocab-group">' +
          self.groupHead(run, grouped.totals[run.key], attribute) +
          window.VocabularyUI.renderWordList(run.words, run.start) +
          "</section>"
        );
      })
      .join("");
  };

  Controller.prototype.renderResults = function () {
    var words = this.filteredWords();
    var pages = Math.max(1, Math.ceil(words.length / PAGE_SIZE));
    this.page = Math.min(Math.max(1, this.page), pages);
    var start = (this.page - 1) * PAGE_SIZE;
    var visible = words.slice(start, start + PAGE_SIZE);
    var count = one(this.root, "count");
    var results = one(this.root, "results");
    var pager = one(this.root, "pagination");

    if (count) count.textContent = words.length + " word" + (words.length === 1 ? "" : "s");
    if (results) {
      if (!words.length) {
        results.innerHTML = '<div class="empty-state"><strong>No matching words</strong><p>Try another topic or clear the search.</p></div>';
      } else if (
        this.mode === "pronunciation" &&
        window.ChinesePronunciation &&
        window.ChinesePronunciation.renderWords
      ) {
        results.textContent = "";
        window.ChinesePronunciation.renderWords(results, visible);
      } else {
        results.innerHTML = window.VocabularyUI && window.VocabularyUI.renderWordList
          ? window.VocabularyUI.renderWordList(visible, start)
          : "";
      }
    }

    if (!pager) return;
    pager.classList.toggle("hidden", words.length <= PAGE_SIZE);
    pager.innerHTML =
      '<button type="button" class="btn-page" data-tocfl-page="first"' +
      (this.page <= 1 ? " disabled" : "") +
      ">First</button>" +
      '<button type="button" class="btn-page" data-tocfl-page="prev"' +
      (this.page <= 1 ? " disabled" : "") +
      ">Prev</button>" +
      '<span class="words-page-info">Page ' +
      this.page +
      " of " +
      pages +
      "</span>" +
      '<button type="button" class="btn-page" data-tocfl-page="next"' +
      (this.page >= pages ? " disabled" : "") +
      ">Next</button>" +
      '<button type="button" class="btn-page" data-tocfl-page="last"' +
      (this.page >= pages ? " disabled" : "") +
      ">Last</button>";
  };

  Controller.prototype.render = function () {
    var title = one(this.root, "title");
    var subtitle = one(this.root, "subtitle");
    var level = this.levelInfo();
    var total = level.wordCount || this.wordsForLevel().length;
    if (title) title.textContent = level.label;
    if (subtitle) {
      subtitle.textContent =
        total + " words · " + Object.keys(this.categoryCounts()).length + " topics in this level";
    }
    this.renderLevels();
    this.renderCategories();
    this.renderSubcategories();
    this.renderResults();
  };

  Controller.prototype.bind = function () {
    var self = this;
    /* The container carries data-tocfl-level as its starting level, so a
       control lookup must never resolve to the container itself. */
    function control(target, attribute) {
      var element = target.closest("[" + attribute + "]");
      return element && element !== self.root ? element : null;
    }
    this.root.addEventListener("click", function (event) {
      var levelButton = control(event.target, "data-tocfl-level");
      if (levelButton) {
        self.level = levelButton.getAttribute("data-tocfl-level");
        self.category = "all";
        self.subcategory = "all";
        self.page = 1;
        var search = one(self.root, "search");
        if (search) search.value = "";
        self.render();
        return;
      }
      var categoryButton = control(event.target, "data-tocfl-category");
      if (categoryButton) {
        var picked = categoryButton.getAttribute("data-tocfl-category");
        self.category = picked === "all" || self.category === picked ? "all" : picked;
        self.subcategory = "all";
        self.page = 1;
        self.renderCategories();
        self.renderSubcategories();
        self.renderResults();
        return;
      }
      var subcategoryButton = control(event.target, "data-tocfl-subcategory");
      if (subcategoryButton) {
        var pickedSubcategory = subcategoryButton.getAttribute("data-tocfl-subcategory");
        self.subcategory =
          pickedSubcategory === "all" || self.subcategory === pickedSubcategory
            ? "all"
            : pickedSubcategory;
        self.page = 1;
        self.renderSubcategories();
        self.renderResults();
        return;
      }
      var pageButton = control(event.target, "data-tocfl-page");
      if (pageButton && !pageButton.disabled) {
        var action = pageButton.getAttribute("data-tocfl-page");
        var pages = Math.max(1, Math.ceil(self.filteredWords().length / PAGE_SIZE));
        if (action === "first") self.page = 1;
        if (action === "prev") self.page = Math.max(1, self.page - 1);
        if (action === "next") self.page = Math.min(pages, self.page + 1);
        if (action === "last") self.page = pages;
        self.renderResults();
      }
    });

    ["search", "status"].forEach(function (role) {
      var element = one(self.root, role);
      if (!element) return;
      element.addEventListener(role === "search" ? "input" : "change", function () {
        self.page = 1;
        self.renderResults();
      });
    });
  };

  function init() {
    document.querySelectorAll("[data-tocfl-browser], [data-tocfl-pronunciation]").forEach(function (root) {
      controllers.push(new Controller(root));
    });
    if (window.LearningState && window.LearningState.subscribe) {
      window.LearningState.subscribe(function () {
        controllers.forEach(function (controller) {
          controller.renderResults();
        });
      });
    }
  }

  window.TocflUI = {
    allWords: function () {
      return sourceWords.slice();
    },
    mount: function (root) {
      var controller = new Controller(root);
      controllers.push(controller);
      return controller;
    },
    refresh: function (mode) {
      controllers.forEach(function (controller) {
        if (!mode || controller.mode === mode) controller.render();
      });
    },
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
