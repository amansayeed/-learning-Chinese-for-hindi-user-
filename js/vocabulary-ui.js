(function () {
  "use strict";

  var store = window.VocabStore;
  var learning = window.LearningState;
  if (!store || !learning) return;

  var browseMode = "hsk";
  var browseDisplay = "list";
  var browseLimit = 60;
  var learnPool = [];
  var learnIndex = 0;
  var learnRevealed = false;

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function hskLabel(word) {
    var value = store.hskValue(word);
    return value === "outside-hsk" ? "Outside HSK" : "HSK " + value;
  }

  function speak(text) {
    if (!text || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    var utterance = new SpeechSynthesisUtterance(text.split("/")[0]);
    utterance.lang = "zh-TW";
    utterance.rate = 0.86;
    window.speechSynthesis.speak(utterance);
  }

  function actionButton(action, id, active, icon, label) {
    return (
      '<button type="button" class="word-action' +
      (active ? " is-active" : "") +
      '" data-word-action="' +
      action +
      '" data-word-id="' +
      escapeHtml(id) +
      '" aria-pressed="' +
      (active ? "true" : "false") +
      '" aria-label="' +
      escapeHtml(label) +
      '">' +
      icon +
      "<span>" +
      escapeHtml(label) +
      "</span></button>"
    );
  }

  function wordCard(word, compact) {
    var secondaries = store.secondaryCategories(word);
    var exZh = store.example(word, "chinese");
    var exPy = store.example(word, "pinyin");
    var exEn = store.example(word, "english");
    var exHi = store.example(word, "hindi");
    return (
      '<article class="vocab-card' +
      (compact ? " vocab-card--compact" : "") +
      '" data-word-card="' +
      escapeHtml(word.id) +
      '">' +
      '<div class="vocab-card__top"><div>' +
      '<button type="button" class="vocab-card__han" data-word-action="listen" data-word-id="' +
      escapeHtml(word.id) +
      '" aria-label="Listen to ' +
      escapeHtml(word.traditional) +
      '">' +
      escapeHtml(word.traditional) +
      "</button>" +
      '<p class="vocab-card__pinyin">' +
      escapeHtml(word.pinyin) +
      "</p></div>" +
      '<div class="vocab-card__badges"><span class="tag tag--hsk">' +
      escapeHtml(hskLabel(word)) +
      '</span><span class="tag">' +
      escapeHtml(store.difficulty(word)) +
      "</span></div></div>" +
      '<div class="vocab-card__meanings"><p><span>English</span>' +
      escapeHtml(word.english) +
      '</p><p lang="hi"><span>हिन्दी</span>' +
      escapeHtml(word.hindi) +
      "</p></div>" +
      '<div class="vocab-card__categories"><span class="tag tag--category">' +
      escapeHtml(store.primaryCategory(word)) +
      "</span>" +
      secondaries
        .slice(0, 2)
        .map(function (category) {
          return '<span class="tag tag--secondary">' + escapeHtml(category) + "</span>";
        })
        .join("") +
      "</div>" +
      (!compact && exZh
        ? '<div class="vocab-card__example"><span>Example</span><p class="example-zh">' +
          escapeHtml(exZh) +
          "</p>" +
          (exPy ? "<p>" + escapeHtml(exPy) + "</p>" : "") +
          (exEn ? "<p>" + escapeHtml(exEn) + "</p>" : "") +
          (exHi ? '<p lang="hi">' + escapeHtml(exHi) + "</p>" : "") +
          "</div>"
        : "") +
      '<div class="vocab-card__actions">' +
      actionButton("listen", word.id, false, "🔊", "Listen") +
      actionButton("favorite", word.id, learning.isFavorite(word.id), "★", "Favorite") +
      actionButton("learned", word.id, learning.isLearned(word.id), "✓", "Learned") +
      actionButton("difficult", word.id, learning.isDifficult(word.id), "?", "Difficult") +
      "</div></article>"
    );
  }

  function statCard(label, value, note) {
    return (
      '<article class="stat-card"><span>' +
      escapeHtml(label) +
      "</span><strong>" +
      escapeHtml(value) +
      "</strong>" +
      (note ? "<small>" + escapeHtml(note) + "</small>" : "") +
      "</article>"
    );
  }

  function wordListRow(word) {
    var simplified =
      word.simplified && word.simplified !== word.traditional
        ? '<small class="vocab-list__simplified">' + escapeHtml(word.simplified) + "</small>"
        : "";
    return (
      "<tr>" +
      '<td><button type="button" class="vocab-list__word" data-word-action="listen" data-word-id="' +
      escapeHtml(word.id) +
      '" aria-label="Listen to ' +
      escapeHtml(word.traditional) +
      '">' +
      escapeHtml(word.traditional) +
      "</button>" +
      simplified +
      "</td>" +
      '<td class="vocab-list__pinyin">' +
      escapeHtml(word.pinyin) +
      "</td>" +
      "<td><strong>" +
      escapeHtml(word.english) +
      '</strong><small lang="hi">' +
      escapeHtml(word.hindi) +
      "</small></td>" +
      '<td><span class="tag tag--hsk">' +
      escapeHtml(hskLabel(word)) +
      '</span><small class="vocab-list__category">' +
      escapeHtml(store.primaryCategory(word)) +
      "</small></td>" +
      '<td class="vocab-list__actions">' +
      actionButton("listen", word.id, false, "🔊", "Listen") +
      actionButton("favorite", word.id, learning.isFavorite(word.id), "★", "Favorite") +
      actionButton("learned", word.id, learning.isLearned(word.id), "✓", "Learned") +
      "</td></tr>"
    );
  }

  function wordList(words) {
    return (
      '<div class="vocab-list-wrap"><table class="vocab-list"><thead><tr>' +
      "<th>Word</th><th>Pinyin</th><th>Meaning</th><th>Level &amp; category</th>" +
      '<th aria-label="Actions"></th></tr></thead><tbody>' +
      words.map(wordListRow).join("") +
      "</tbody></table></div>"
    );
  }

  function sortedCategories() {
    var counts = store.categoryCounts();
    return Object.keys(counts).sort(function (a, b) {
      return counts[b] - counts[a] || a.localeCompare(b);
    });
  }

  function fillSelect(select, items, current) {
    if (!select) return;
    select.innerHTML = items
      .map(function (item) {
        return (
          '<option value="' +
          escapeHtml(item.value) +
          '"' +
          (item.value === current ? " selected" : "") +
          ">" +
          escapeHtml(item.label) +
          "</option>"
        );
      })
      .join("");
  }

  function populateFilters() {
    var categoryItems = [{ value: "all", label: "All categories" }].concat(
      sortedCategories().map(function (category) {
        return { value: category, label: category };
      })
    );
    fillSelect($("browse-category"), categoryItems, $("browse-category") && $("browse-category").value);
    fillSelect($("learn-category"), categoryItems, $("learn-category") && $("learn-category").value);
  }

  function renderDashboard() {
    var stats = learning.stats(store.all().length);
    var statWrap = $("dashboard-stats");
    if (statWrap) {
      statWrap.innerHTML =
        statCard("Total words", stats.total, "All preserved sources") +
        statCard("Learned", stats.learned, stats.progress + "% complete") +
        statCard("Remaining", stats.remaining, "Keep going") +
        statCard("Favorites", stats.favorites, "Saved words") +
        statCard("Difficult", stats.difficult, "Ready to review") +
        statCard("Streak", stats.streak + " days", "Level " + stats.level + " · " + stats.xp + " XP");
    }

    var goal = $("daily-goal-progress");
    var goalText = $("daily-goal-text");
    var todayCount = stats.today.unique;
    if (goal) {
      goal.value = Math.min(todayCount, stats.dailyGoal);
      goal.max = stats.dailyGoal;
    }
    if (goalText) goalText.textContent = todayCount + " / " + stats.dailyGoal + " words today";
    var goalInput = $("daily-goal-input");
    if (goalInput) goalInput.value = stats.dailyGoal;

    var counts = store.categoryCounts();
    var categoryWrap = $("dashboard-categories");
    if (categoryWrap) {
      categoryWrap.innerHTML = sortedCategories()
        .slice(0, 12)
        .map(function (category) {
          return (
            '<button type="button" class="category-card" data-open-category="' +
            escapeHtml(category) +
            '"><span>' +
            escapeHtml(category) +
            "</span><strong>" +
            counts[category] +
            " tagged words</strong></button>"
          );
        })
        .join("");
    }

    var recentWrap = $("dashboard-recent");
    if (recentWrap) {
      var recent = learning
        .get()
        .recent.map(store.byId)
        .filter(Boolean)
        .slice(0, 4);
      recentWrap.innerHTML = recent.length
        ? recent.map(function (word) { return wordCard(word, true); }).join("")
        : '<div class="empty-state"><strong>No learned words yet</strong><p>Start a learning session to build your history.</p></div>';
    }
  }

  function browseOptions() {
    return {
      query: $("browse-search") ? $("browse-search").value : "",
      hsk: $("browse-hsk") ? $("browse-hsk").value : "all",
      category: $("browse-category") ? $("browse-category").value : "all",
      status: $("browse-status") ? $("browse-status").value : "all",
      sort: $("browse-sort") ? $("browse-sort").value : "pinyin",
    };
  }

  function renderBrowse() {
    var options = browseOptions();
    var results = store.filter(options);
    var list = $("browse-results");
    var count = $("browse-result-count");
    if (count) count.textContent = results.length + (results.length === 1 ? " word" : " words");
    if (list) {
      var visible = results.slice(0, browseLimit);
      list.classList.toggle("vocab-grid", browseDisplay === "grid");
      list.classList.toggle("vocab-results--list", browseDisplay === "list");
      list.innerHTML = results.length
        ? browseDisplay === "list"
          ? wordList(visible)
          : visible.map(function (word) { return wordCard(word, false); }).join("")
        : '<div class="empty-state"><strong>No matching words</strong><p>Try removing a filter or searching another language.</p></div>';
    }
    var more = $("browse-more");
    if (more) {
      more.classList.toggle("hidden", results.length <= browseLimit);
      more.textContent = "Show more (" + Math.max(0, results.length - browseLimit) + " remaining)";
    }
    document.querySelectorAll("[data-browse-tab]").forEach(function (button) {
      var active = button.getAttribute("data-browse-tab") === browseMode;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
    document.querySelectorAll("[data-result-view]").forEach(function (button) {
      var active = button.getAttribute("data-result-view") === browseDisplay;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function setBrowseMode(mode) {
    browseMode = mode === "category" ? "category" : "hsk";
    var hskField = $("browse-hsk-field");
    var categoryField = $("browse-category-field");
    if (hskField) hskField.classList.toggle("filter-emphasis", browseMode === "hsk");
    if (categoryField) categoryField.classList.toggle("filter-emphasis", browseMode === "category");
    renderBrowseOverview();
  }

  function renderBrowseOverview() {
    var wrap = $("browse-overview");
    if (!wrap) return;
    wrap.classList.toggle("browse-overview--levels", browseMode === "hsk");
    if (browseMode === "category") {
      var categoryCounts = store.categoryCounts();
      wrap.innerHTML = sortedCategories()
        .map(function (category) {
          return (
            '<button type="button" class="category-card" data-open-category="' +
            escapeHtml(category) +
            '"><span>' +
            escapeHtml(category) +
            "</span><strong>" +
            categoryCounts[category] +
            " tagged words</strong></button>"
          );
        })
        .join("");
      return;
    }
    var hskCounts = store.hskCounts();
    wrap.innerHTML = ["1", "2", "3", "4", "5", "6", "outside-hsk"]
      .map(function (level) {
        return (
          '<button type="button" class="category-card" data-open-hsk="' +
          level +
          '"><span>' +
          (level === "outside-hsk" ? "Outside HSK" : "HSK " + level) +
          "</span><strong>" +
          (hskCounts[level] || 0) +
          " words</strong></button>"
        );
      })
      .join("");
  }

  function updateLearnPool(reset) {
    learnPool = store.filter({
      hsk: $("learn-hsk") ? $("learn-hsk").value : "all",
      category: $("learn-category") ? $("learn-category").value : "all",
      status: $("learn-review") ? $("learn-review").value : "all",
      sort: "pinyin",
    });
    if (reset || learnIndex >= learnPool.length) learnIndex = 0;
    learnRevealed = false;
    renderLearn();
  }

  function renderLearn() {
    var word = learnPool[learnIndex];
    var wrap = $("learn-card");
    var progress = $("learn-progress");
    var progressText = $("learn-progress-text");
    if (progress) {
      progress.max = Math.max(1, learnPool.length);
      progress.value = word ? learnIndex + 1 : 0;
    }
    if (progressText) progressText.textContent = word ? learnIndex + 1 + " / " + learnPool.length + " words" : "0 / 0 words";
    if (!wrap) return;
    if (!word) {
      wrap.innerHTML = '<div class="empty-state"><strong>No words in this session</strong><p>Change the HSK, category, or review filter.</p></div>';
      return;
    }
    var exZh = store.example(word, "chinese");
    wrap.innerHTML =
      '<article class="learn-card">' +
      '<div class="vocab-card__badges"><span class="tag tag--hsk">' +
      escapeHtml(hskLabel(word)) +
      '</span><span class="tag tag--category">' +
      escapeHtml(store.primaryCategory(word)) +
      "</span></div>" +
      '<button type="button" class="learn-card__han" data-word-action="listen" data-word-id="' +
      escapeHtml(word.id) +
      '" aria-label="Listen to word">' +
      escapeHtml(word.traditional) +
      "</button>" +
      '<p class="learn-card__pinyin">' +
      escapeHtml(word.pinyin) +
      "</p>" +
      '<div class="learn-card__answer' +
      (learnRevealed ? "" : " is-hidden") +
      '"><p><span>English</span>' +
      escapeHtml(word.english) +
      '</p><p lang="hi"><span>हिन्दी</span>' +
      escapeHtml(word.hindi) +
      "</p>" +
      (exZh ? '<div class="vocab-card__example"><span>Example</span><p class="example-zh">' + escapeHtml(exZh) + "</p></div>" : "") +
      "</div>" +
      (!learnRevealed ? '<button type="button" class="primary-button" id="learn-reveal">Show meaning</button>' : "") +
      '<div class="vocab-card__actions">' +
      actionButton("favorite", word.id, learning.isFavorite(word.id), "★", "Favorite") +
      actionButton("learned", word.id, learning.isLearned(word.id), "✓", "Learned") +
      actionButton("difficult", word.id, learning.isDifficult(word.id), "?", "Difficult") +
      "</div></article>";
  }

  function renderFavorites() {
    var results = store.filter({ status: "favorite", sort: "pinyin" });
    var count = $("favorites-count");
    var wrap = $("favorites-results");
    if (count) count.textContent = results.length + " favorite words";
    if (wrap) {
      wrap.innerHTML = results.length
        ? results.map(function (word) { return wordCard(word, false); }).join("")
        : '<div class="empty-state"><strong>No favorites yet</strong><p>Tap Favorite on any vocabulary card.</p></div>';
    }
  }

  function renderProgress() {
    var stats = learning.stats(store.all().length);
    var wrap = $("progress-summary");
    if (wrap) {
      wrap.innerHTML =
        statCard("Completion", stats.progress + "%", stats.learned + " of " + stats.total) +
        statCard("Current streak", stats.streak + " days", "Practice daily") +
        statCard("XP", stats.xp, "Level " + stats.level) +
        statCard("Difficult words", stats.difficult, "Review them in Learn");
    }
    var hskCounts = store.hskCounts();
    var bars = $("progress-hsk");
    if (bars) {
      bars.innerHTML = ["1", "2", "3", "4", "5", "6", "outside-hsk"]
        .map(function (level) {
          var total = hskCounts[level] || 0;
          var learned = store.filter({ hsk: level, status: "learned" }).length;
          var percent = total ? Math.round((learned / total) * 100) : 0;
          return (
            '<div class="progress-row"><div><strong>' +
            (level === "outside-hsk" ? "Outside HSK" : "HSK " + level) +
            "</strong><span>" +
            learned +
            " / " +
            total +
            '</span></div><progress max="100" value="' +
            percent +
            '"></progress><span>' +
            percent +
            "%</span></div>"
          );
        })
        .join("");
    }
  }

  function refreshAll() {
    renderDashboard();
    renderBrowse();
    renderLearn();
    renderFavorites();
    renderProgress();
  }

  function handleAction(button) {
    var action = button.getAttribute("data-word-action");
    var id = button.getAttribute("data-word-id");
    var word = store.byId(id);
    if (!word) return;
    if (action === "listen") {
      speak(word.traditional);
      return;
    }
    if (action === "favorite") learning.toggleFavorite(id);
    if (action === "learned") learning.markLearned(id);
    if (action === "difficult") learning.toggleDifficult(id);
  }

  function bind() {
    document.addEventListener("click", function (event) {
      var action = event.target.closest("[data-word-action]");
      if (action) {
        handleAction(action);
        return;
      }
      var category = event.target.closest("[data-open-category]");
      if (category) {
        var select = $("browse-category");
        if (select) select.value = category.getAttribute("data-open-category");
        setBrowseMode("category");
        if (window.AppRouter) window.AppRouter.go("categories");
        renderBrowse();
        return;
      }
      var hsk = event.target.closest("[data-open-hsk]");
      if (hsk) {
        var hskSelect = $("browse-hsk");
        if (hskSelect) hskSelect.value = hsk.getAttribute("data-open-hsk");
        setBrowseMode("hsk");
        if (window.AppRouter) window.AppRouter.go("hsk");
        renderBrowse();
        return;
      }
      var tab = event.target.closest("[data-browse-tab]");
      if (tab) {
        setBrowseMode(tab.getAttribute("data-browse-tab"));
        renderBrowse();
        return;
      }
      var resultView = event.target.closest("[data-result-view]");
      if (resultView) {
        browseDisplay = resultView.getAttribute("data-result-view") === "grid" ? "grid" : "list";
        renderBrowse();
      }
    });

    ["browse-search", "browse-hsk", "browse-category", "browse-status", "browse-sort"].forEach(function (id) {
      var element = $(id);
      if (!element) return;
      element.addEventListener(id === "browse-search" ? "input" : "change", function () {
        browseLimit = 60;
        renderBrowse();
      });
    });
    ["learn-hsk", "learn-category", "learn-review"].forEach(function (id) {
      var element = $(id);
      if (element) element.addEventListener("change", function () { updateLearnPool(true); });
    });

    var more = $("browse-more");
    if (more) more.addEventListener("click", function () { browseLimit += 60; renderBrowse(); });
    var goal = $("daily-goal-input");
    if (goal) goal.addEventListener("change", function () { learning.setDailyGoal(goal.value); });

    var prev = $("learn-prev");
    var next = $("learn-next");
    var random = $("learn-random");
    if (prev) prev.addEventListener("click", function () {
      if (!learnPool.length) return;
      learnIndex = (learnIndex - 1 + learnPool.length) % learnPool.length;
      learnRevealed = false;
      renderLearn();
    });
    if (next) next.addEventListener("click", function () {
      if (!learnPool.length) return;
      learnIndex = (learnIndex + 1) % learnPool.length;
      learnRevealed = false;
      renderLearn();
    });
    if (random) random.addEventListener("click", function () {
      if (!learnPool.length) return;
      learnIndex = Math.floor(Math.random() * learnPool.length);
      learnRevealed = false;
      renderLearn();
    });
    document.addEventListener("click", function (event) {
      if (event.target.id === "learn-reveal") {
        learnRevealed = true;
        learning.markReviewed(learnPool[learnIndex] && learnPool[learnIndex].id, true);
        renderLearn();
      }
    });
  }

  function init() {
    populateFilters();
    bind();
    setBrowseMode("hsk");
    updateLearnPool(true);
    refreshAll();
    learning.subscribe(refreshAll);
  }

  window.VocabularyUI = {
    onView: function (view) {
      if (view === "hsk") setBrowseMode("hsk");
      if (view === "categories") setBrowseMode("category");
      if (view === "dashboard") renderDashboard();
      if (view === "hsk" || view === "categories") renderBrowse();
      if (view === "learn") renderLearn();
      if (view === "favorites") renderFavorites();
      if (view === "progress") renderProgress();
    },
    setBrowseMode: setBrowseMode,
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
