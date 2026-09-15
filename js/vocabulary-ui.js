(function () {
  "use strict";

  var store = window.VocabStore;
  var learning = window.LearningState;
  if (!store || !learning) return;

  var browseMode = "hsk";
  var browseContent = "vocabulary";
  var browseDisplay = "list";
  var PAGE_SIZE = 50;
  var browsePage = 1;
  var LEVELS = ["1", "2", "3", "4", "5", "6", "outside-hsk"];
  var currentLevel = "1";
  var levelPage = 1;
  var learnPool = [];
  var learnIndex = 0;
  var learnAnswered = 0;
  var currentQuiz = null;
  var quizLocked = false;
  var wordDetailOverlay = null;
  var wordDetailLastFocus = null;
  var DISPLAY_KEY = "chinese-vocab-display-v1";
  var displayOptions = readDisplayOptions();
  var audioElement = null;

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

  /* Variant forms such as 公共汽車/公共汽车 carry no space, so the browser has
     nowhere to wrap them. Offer a break after each separator instead. */
  function escapeWrappable(value) {
    return escapeHtml(value).replace(/([\/｜|])/g, "$1<wbr>");
  }

  function shortPinyin(value) {
    return String(value || "").split("/")[0].replace(/\s+/g, "");
  }

  function readDisplayOptions() {
    var defaults = { traditional: true, simplified: true, english: true, hindi: true };
    try {
      var saved = JSON.parse(localStorage.getItem(DISPLAY_KEY) || "null");
      Object.keys(defaults).forEach(function (key) {
        if (saved && saved[key] === false) defaults[key] = false;
      });
    } catch (e) {}
    return defaults;
  }

  function saveDisplayOptions() {
    try { localStorage.setItem(DISPLAY_KEY, JSON.stringify(displayOptions)); } catch (e) {}
  }

  function shown(key) {
    return displayOptions[key] ? "" : " study-field--hidden";
  }

  function hskLabel(word) {
    var value = store.hskValue(word);
    return value === "outside-hsk" ? "Outside HSK" : "HSK " + value;
  }

  function speak(text, word) {
    var audioUrl = word && (word.audioUrl || (word.audio && word.audio.url));
    if (audioUrl) {
      if (!audioElement) audioElement = new Audio();
      audioElement.src = audioUrl;
      audioElement.play().catch(function () { speak(text); });
      return;
    }
    if (!text || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    var utterance = new SpeechSynthesisUtterance(text.split("/")[0]);
    utterance.lang = "zh-TW";
    utterance.rate = 0.86;
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

  /* hideLabel drops the 繁體/简体 caption where the colour coding and the
     column legend already say which script is which. */
  function scriptBlock(label, value, modifier, wordId, largeClass, hideLabel) {
    var isTraditional = modifier === "traditional";
    var action = isTraditional ? "listen" : "details";
    var actionLabel = isTraditional ? "Listen to " : "Open details for ";
    return (
      '<div class="script-block script-block--' +
      modifier +
      shown(modifier) +
      '">' +
      (hideLabel
        ? ""
        : '<span class="script-block__label">' + escapeHtml(label) + "</span>") +
      '<button type="button" class="' +
      largeClass +
      " " +
      largeClass +
      "--" +
      modifier +
      '" data-word-action="' +
      action +
      '" data-word-id="' +
      escapeHtml(wordId) +
      (isTraditional ? '" data-speak-text="' + escapeHtml(value) : "") +
      '" title="' +
      escapeHtml(label + (isTraditional ? " · play Taiwan Mandarin" : " · open details")) +
      '" aria-label="' +
      actionLabel +
      escapeHtml(label + " " + value) +
      '">' +
      escapeWrappable(value) +
      "</button></div>"
    );
  }

  function wordCard(word, compact, serial) {
    var secondaries = store.secondaryCategories(word);
    var exTrad = store.example(word, "traditional");
    var exSimp = store.example(word, "simplified");
    var exPy = store.example(word, "pinyin");
    var exEn = store.example(word, "english");
    var exHi = store.example(word, "hindi");
    return (
      '<article class="vocab-card' +
      (compact ? " vocab-card--compact" : "") +
      '" data-word-card="' +
      escapeHtml(word.id) +
      '">' +
      (serial ? '<span class="word-serial">#' + serial + "</span>" : "") +
      '<div class="vocab-card__top"><div class="vocab-card__language">' +
      '<div class="script-pair">' +
      scriptBlock("繁體中文", word.traditional, "traditional", word.id, "vocab-card__han") +
      scriptBlock("简体中文", word.simplified, "simplified", word.id, "vocab-card__han") +
      "</div>" +
      '<p class="vocab-card__pinyin">' +
      escapeHtml(word.pinyin) +
      "</p></div>" +
      '<div class="vocab-card__badges"><span class="tag tag--hsk">' +
      escapeHtml(hskLabel(word)) +
      '</span><span class="tag">' +
      escapeHtml(store.difficulty(word)) +
      "</span></div></div>" +
      '<div class="vocab-card__meanings"><p class="' + shown("english").trim() + '"><span>English</span>' +
      escapeHtml(word.english) +
      '</p><p lang="hi" class="' + shown("hindi").trim() + '"><span>हिन्दी</span>' +
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
      (!compact && exTrad
        ? '<div class="vocab-card__example"><span>Example sentence</span><div class="example-script example-script--traditional"><strong>繁體中文</strong><button type="button" class="example-zh" data-word-action="listen" data-word-id="' +
          escapeHtml(word.id) +
          '" data-speak-text="' +
          escapeHtml(exTrad) +
          '">' +
          escapeHtml(exTrad) +
          '</button></div><div class="example-script example-script--simplified"><strong>简体中文</strong><button type="button" class="example-zh" data-word-action="details" data-word-id="' +
          escapeHtml(word.id) +
          '">' +
          escapeHtml(exSimp || exTrad) +
          "</button></div>" +
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

  function ensureWordDetail() {
    if (wordDetailOverlay) return wordDetailOverlay;
    wordDetailOverlay = document.createElement("div");
    wordDetailOverlay.className = "word-detail-overlay hidden";
    wordDetailOverlay.setAttribute("aria-hidden", "true");
    wordDetailOverlay.innerHTML =
      '<section class="word-detail" role="dialog" aria-modal="true" aria-labelledby="word-detail-title">' +
      '<button type="button" class="word-detail__close" data-word-detail-close aria-label="Close word details">×</button>' +
      '<div data-word-detail-content></div></section>';
    document.body.appendChild(wordDetailOverlay);
    return wordDetailOverlay;
  }

  function wordDetailHtml(word) {
    var sentence = store.sentence(word);
    var secondaries = store.secondaryCategories(word);
    var tocfl = store.tocflLevels(word);
    return (
      '<div class="word-detail__heading"><p class="eyebrow">Vocabulary details</p>' +
      '<h2 id="word-detail-title">' +
      escapeHtml(word.pinyin) +
      "</h2></div>" +
      '<div class="word-detail__scripts">' +
      '<button type="button" class="word-detail__script word-detail__script--traditional" data-word-action="listen" data-word-id="' +
      escapeHtml(word.id) +
      '" data-speak-text="' +
      escapeHtml(word.traditional) +
      '" aria-label="Play Taiwan Mandarin for ' +
      escapeHtml(word.traditional) +
      '"><small>Traditional · tap to listen</small><strong lang="zh-Hant">' +
      escapeWrappable(word.traditional) +
      "</strong></button>" +
      '<div class="word-detail__script word-detail__script--simplified"><small>Simplified</small><strong lang="zh-Hans">' +
      escapeWrappable(word.simplified) +
      "</strong></div></div>" +
      '<button type="button" class="primary-button word-detail__listen" data-word-action="listen" data-word-id="' +
      escapeHtml(word.id) +
      '" data-speak-text="' +
      escapeHtml(word.traditional) +
      '">🔊 Play Taiwan Mandarin pronunciation</button>' +
      '<dl class="word-detail__facts"><div><dt>Pinyin</dt><dd>' +
      escapeHtml(word.pinyin) +
      "</dd></div><div><dt>English</dt><dd>" +
      escapeHtml(word.english) +
      '</dd></div><div><dt>हिन्दी</dt><dd lang="hi">' +
      escapeHtml(word.hindi) +
      "</dd></div><div><dt>Learning information</dt><dd>" +
      escapeHtml(hskLabel(word)) +
      (tocfl.length ? " · TOCFL " + escapeHtml(tocfl.join(", ")) : "") +
      " · " +
      escapeHtml(store.difficulty(word)) +
      "</dd></div></dl>" +
      '<div class="word-detail__categories"><span class="tag tag--category">' +
      escapeHtml(store.primaryCategory(word)) +
      "</span>" +
      secondaries
        .map(function (category) {
          return '<span class="tag tag--secondary">' + escapeHtml(category) + "</span>";
        })
        .join("") +
      "</div>" +
      (sentence
        ? '<section class="word-detail__example"><h3>Example sentence</h3>' +
          '<button type="button" data-word-action="listen" data-word-id="' +
          escapeHtml(word.id) +
          '" data-speak-text="' +
          escapeHtml(sentence.traditional) +
          '" class="word-detail__example-traditional" aria-label="Play example pronunciation">' +
          escapeHtml(sentence.traditional) +
          '</button><p lang="zh-Hans">' +
          escapeHtml(sentence.simplified) +
          '</p><p class="word-detail__example-pinyin">' +
          escapeHtml(sentence.pinyin) +
          "</p><p>" +
          escapeHtml(sentence.english) +
          '</p><p lang="hi">' +
          escapeHtml(sentence.hindi) +
          "</p></section>"
        : "") +
      '<div class="word-detail__actions">' +
      actionButton("favorite", word.id, learning.isFavorite(word.id), "★", "Favorite") +
      actionButton("learned", word.id, learning.isLearned(word.id), "✓", "Learned") +
      actionButton("difficult", word.id, learning.isDifficult(word.id), "?", "Difficult") +
      "</div>"
    );
  }

  function openWordDetails(word, trigger) {
    if (!word) return;
    var overlay = ensureWordDetail();
    var content = overlay.querySelector("[data-word-detail-content]");
    if (!content) return;
    wordDetailLastFocus = trigger || document.activeElement;
    content.innerHTML = wordDetailHtml(word);
    overlay.classList.remove("hidden");
    overlay.setAttribute("aria-hidden", "false");
    document.body.classList.add("word-detail-open");
    var close = overlay.querySelector("[data-word-detail-close]");
    if (close) close.focus();
  }

  function closeWordDetails() {
    if (!wordDetailOverlay) return;
    wordDetailOverlay.classList.add("hidden");
    wordDetailOverlay.setAttribute("aria-hidden", "true");
    document.body.classList.remove("word-detail-open");
    if (wordDetailLastFocus && typeof wordDetailLastFocus.focus === "function") {
      wordDetailLastFocus.focus();
    }
    wordDetailLastFocus = null;
  }

  function statCard(label, value, note) {
    var icons = {
      "Total words": "📚",
      Learned: "✅",
      Remaining: "🧭",
      Favorites: "⭐",
      Difficult: "💪",
      Streak: "🔥",
      Completion: "🏆",
      "Current streak": "🔥",
      XP: "⚡",
      "Difficult words": "💪",
    };
    return (
      '<article class="stat-card"><span class="stat-card__icon" aria-hidden="true">' +
      (icons[label] || "📌") +
      '</span><span class="stat-card__label">' +
      escapeHtml(label) +
      "</span><strong>" +
      escapeHtml(value) +
      "</strong>" +
      (note ? "<small>" + escapeHtml(note) + "</small>" : "") +
      "</article>"
    );
  }

  function categoryIcon(category) {
    var value = String(category || "").toLowerCase();
    if (/food|cook|restaurant/.test(value)) return "🍜";
    if (/drink/.test(value)) return "🥤";
    if (/family|people|friend|relationship|pronoun/.test(value)) return "👨‍👩‍👧";
    if (/home|household/.test(value)) return "🏠";
    if (/work|office|business|professional/.test(value)) return "💼";
    if (/school|education|academic/.test(value)) return "🎓";
    if (/shop|money|bank|price|economy|finance/.test(value)) return "🛍️";
    if (/transport|travel|airport|flight|direction/.test(value)) return "🚇";
    if (/health|body|hospital|medicine|care/.test(value)) return "🏥";
    if (/technology|computer/.test(value)) return "💻";
    if (/weather|nature|environment|animal/.test(value)) return "🌿";
    if (/time|date|calendar|frequency|number/.test(value)) return "🕐";
    if (/taiwan/.test(value)) return "🇹🇼";
    if (/grammar|verb|adjective|adverb|preposition|conjunction|measure|question/.test(value)) return "📝";
    if (/government|politic|society|culture|community/.test(value)) return "🏛️";
    if (/emotion|personality/.test(value)) return "❤️";
    return "💬";
  }

  function wordListRow(word, index) {
    return (
      "<tr>" +
      '<td class="vocab-list__serial" data-label="No.">' +
      (index + 1) +
      "</td>" +
      '<td data-label="Word"><div class="script-pair script-pair--list">' +
      scriptBlock("繁體", word.traditional, "traditional", word.id, "vocab-list__word", true) +
      scriptBlock("简体", word.simplified, "simplified", word.id, "vocab-list__word", true) +
      "</div>" +
      "</td>" +
      '<td class="vocab-list__pinyin" data-label="Pinyin">' +
      escapeHtml(shortPinyin(word.pinyin)) +
      "</td>" +
      '<td data-label="Meaning"><strong>' +
      escapeHtml(word.english) +
      '</strong><small lang="hi">' +
      escapeHtml(word.hindi) +
      "</small></td></tr>"
    );
  }

  function wordList(words, startIndex) {
    startIndex = Number(startIndex) || 0;
    return (
      '<div class="vocab-list-wrap"><table class="vocab-list"><thead><tr>' +
      '<th scope="col">#</th><th scope="col">Word</th><th scope="col">Pinyin</th><th scope="col">Meaning</th>' +
      "</tr></thead><tbody>" +
      words.map(function (word, index) { return wordListRow(word, startIndex + index); }).join("") +
      "</tbody></table></div>"
    );
  }

  function pageCount(total) {
    return Math.max(1, Math.ceil(total / PAGE_SIZE));
  }

  function renderPagination(id, target, page, total) {
    var wrap = $(id);
    if (!wrap) return;
    var pages = pageCount(total);
    var disabledFirst = page <= 1 ? " disabled" : "";
    var disabledLast = page >= pages ? " disabled" : "";
    wrap.classList.toggle("hidden", total <= PAGE_SIZE);
    wrap.innerHTML =
      '<button type="button" class="btn-page" data-page-target="' + target + '" data-page-action="first"' + disabledFirst + '>First</button>' +
      '<button type="button" class="btn-page" data-page-target="' + target + '" data-page-action="prev"' + disabledFirst + '>Previous</button>' +
      '<span class="words-page-info">Page ' + page + " of " + pages + " · " + total + " total</span>" +
      '<button type="button" class="btn-page" data-page-target="' + target + '" data-page-action="next"' + disabledLast + '>Next</button>' +
      '<button type="button" class="btn-page" data-page-target="' + target + '" data-page-action="last"' + disabledLast + '>Last</button>';
  }

  function sentenceCard(item) {
    var simplified = item.simplified || item.traditional;
    return (
      '<article class="sentence-card" data-sentence-card="' +
      escapeHtml(item.id) +
      '">' +
      '<div class="sentence-card__badges"><span class="tag tag--hsk">' +
      escapeHtml(item.hskLevel === "outside-hsk" ? "Outside HSK" : "HSK " + item.hskLevel) +
      '</span><span class="tag tag--category">' +
      escapeHtml(item.topic) +
      "</span></div>" +
      '<div class="sentence-card__script sentence-card__script--traditional"><span>繁體中文</span><button type="button" data-word-action="listen" data-word-id="' +
      escapeHtml(item.wordId) +
      '" data-speak-text="' +
      escapeHtml(item.traditional) +
      '">' +
      escapeHtml(item.traditional) +
      "</button></div>" +
      '<div class="sentence-card__script sentence-card__script--simplified"><span>简体中文</span><button type="button" data-word-action="details" data-word-id="' +
      escapeHtml(item.wordId) +
      '">' +
      escapeHtml(simplified) +
      "</button></div>" +
      (item.pinyin ? '<p class="sentence-card__pinyin">' + escapeHtml(item.pinyin) + "</p>" : "") +
      '<div class="sentence-card__translations"><p><span>English</span>' +
      escapeHtml(item.english) +
      '</p><p lang="hi"><span>हिन्दी</span>' +
      escapeHtml(item.hindi) +
      "</p></div>" +
      '<small class="sentence-card__category">' +
      escapeHtml(item.category) +
      "</small></article>"
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
    var goal = $("daily-goal-progress");
    var goalText = $("daily-goal-text");
    var todayCount = stats.today.unique;
    if (goal) {
      goal.value = Math.min(todayCount, stats.dailyGoal);
      goal.max = stats.dailyGoal;
    }
    if (goalText) {
      goalText.textContent =
        todayCount >= stats.dailyGoal
          ? "Daily goal complete — review more whenever you like."
          : stats.due + " due · " + stats.difficult + " difficult · new words added automatically";
    }
    var simple = $("dashboard-simple-stats");
    if (simple) {
      simple.textContent =
        stats.streak + " day streak · " + stats.xp + " XP · " + stats.learned + " words started";
    }

    var preview = $("dashboard-preview");
    if (preview) {
      var queue = learning.todayQueue(store.filter({ sort: "smart" }), 6);
      preview.innerHTML = queue.length
        ? wordList(queue)
        : '<div class="empty-state"><strong>All caught up</strong><p>No reviews are due right now.</p></div>';
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
    var sentenceMode = browseContent === "sentences";
    var results = sentenceMode ? store.sentences(options) : store.filter(options);
    var list = $("browse-results");
    var count = $("browse-result-count");
    var noun = sentenceMode ? "sentence" : "word";
    if (count) count.textContent = results.length + " " + noun + (results.length === 1 ? "" : "s");
    browsePage = Math.min(Math.max(1, browsePage), pageCount(results.length));
    var start = (browsePage - 1) * PAGE_SIZE;
    var description = $("browse-result-description");
    if (description) {
      description.textContent = sentenceMode
        ? "HSK level + practical topic · 繁體中文 · 简体中文 · English · हिन्दी"
        : "繁體中文 · 简体中文 · Pinyin · English · हिन्दी";
    }
    var resultToolbar = document.querySelector(".browse-result-toolbar");
    if (resultToolbar) resultToolbar.classList.toggle("hidden", sentenceMode);
    if (list) {
      var visible = results.slice(start, start + PAGE_SIZE);
      list.classList.toggle("vocab-grid", !sentenceMode && browseDisplay === "grid");
      list.classList.toggle("vocab-results--list", !sentenceMode && browseDisplay === "list");
      list.classList.toggle("sentence-grid", sentenceMode);
      list.innerHTML = results.length
        ? sentenceMode
          ? visible.map(sentenceCard).join("")
          : browseDisplay === "list"
          ? wordList(visible, start)
          : visible.map(function (word, index) { return wordCard(word, false, start + index + 1); }).join("")
        : '<div class="empty-state"><strong>No matching words</strong><p>Try removing a filter or searching another language.</p></div>';
    }
    renderPagination("browse-pagination", "browse", browsePage, results.length);
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
    document.querySelectorAll("[data-content-tab]").forEach(function (button) {
      var active = button.getAttribute("data-content-tab") === browseContent;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
    var selectedHsk = $("browse-hsk") ? $("browse-hsk").value : "all";
    document.querySelectorAll("[data-hsk-tab]").forEach(function (button) {
      var active = button.getAttribute("data-hsk-tab") === selectedHsk;
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
            '"><span class="category-card__icon" aria-hidden="true">' +
            categoryIcon(category) +
            '</span><span class="category-card__title">' +
            escapeHtml(category) +
            "</span><strong>" +
            categoryCounts[category] +
            " " +
            (browseContent === "sentences" ? "sentences" : "tagged words") +
            "</strong></button>"
          );
        })
        .join("");
      return;
    }
    var hskCounts = store.hskCounts();
    wrap.innerHTML = ["1", "2", "3", "4", "5", "6", "outside-hsk"]
      .map(function (level) {
        return (
          '<button type="button" class="category-card' +
          (["1", "2", "3"].indexOf(level) >= 0 ? " category-card--beginner" : "") +
          '" data-open-hsk="' +
          level +
          '"><span>' +
          (level === "outside-hsk" ? "Outside HSK" : "HSK " + level) +
          "</span><strong>" +
          (hskCounts[level] || 0) +
          " " +
          (browseContent === "sentences" ? "sentences" : "words") +
          "</strong></button>"
        );
      })
      .join("");
  }

  function levelLabel(level) {
    return level === "outside-hsk" ? "Outside HSK" : "HSK " + level;
  }

  function openLevel(level) {
    if (LEVELS.indexOf(level) < 0) return;
    renderLevel(level);
    if (window.AppRouter) window.AppRouter.go(window.AppRouter.viewForLevel(level));
  }

  function levelWords(level) {
    return store.filter({ hsk: level, sort: "pinyin" });
  }

  /* Categories are scoped to one level so each page only shows its own topics. */
  function levelCategoryCounts(level) {
    return store.categoryCounts(levelWords(level));
  }

  function sortedLevelCategories(level) {
    var counts = levelCategoryCounts(level);
    return Object.keys(counts).sort(function (a, b) {
      return counts[b] - counts[a] || a.localeCompare(b);
    });
  }

  function renderLevelSwitch() {
    var wrap = $("level-switch");
    if (!wrap) return;
    var counts = store.hskCounts();
    wrap.innerHTML = LEVELS.map(function (level) {
      var active = level === currentLevel;
      return (
        '<button type="button" class="level-switch__button' +
        (active ? " is-active" : "") +
        '" data-open-level="' +
        escapeHtml(level) +
        '" aria-pressed="' +
        (active ? "true" : "false") +
        '"><span>' +
        escapeHtml(levelLabel(level)) +
        "</span><small>" +
        (counts[level] || 0) +
        " words</small></button>"
      );
    }).join("");
  }

  function renderLevelCategories() {
    var wrap = $("level-categories");
    if (!wrap) return;
    var counts = levelCategoryCounts(currentLevel);
    var selected = $("level-category") ? $("level-category").value : "all";
    var categories = sortedLevelCategories(currentLevel);
    wrap.innerHTML = categories.length
      ? '<button type="button" class="topic-chip' +
        (selected === "all" ? " is-active" : "") +
        '" data-open-level-category="all"><span aria-hidden="true">📚</span> All (' +
        (store.hskCounts()[currentLevel] || 0) +
        ")</button>" +
        categories
          .map(function (category) {
            return (
              '<button type="button" class="topic-chip' +
              (category === selected ? " is-active" : "") +
              '" data-open-level-category="' +
              escapeHtml(category) +
              '"><span aria-hidden="true">' +
              categoryIcon(category) +
              "</span> " +
              escapeHtml(category) +
              " (" +
              counts[category] +
              ")</button>"
            );
          })
          .join("")
      : "";
    var clear = $("level-clear-category");
    if (clear) clear.classList.toggle("hidden", selected === "all");
  }

  function populateLevelCategorySelect() {
    var select = $("level-category");
    if (!select) return;
    var previous = select.value;
    var counts = levelCategoryCounts(currentLevel);
    var items = [{ value: "all", label: "All topics in this level" }].concat(
      sortedLevelCategories(currentLevel).map(function (category) {
        return { value: category, label: category + " (" + counts[category] + ")" };
      })
    );
    var keep = items.some(function (item) { return item.value === previous; }) ? previous : "all";
    fillSelect(select, items, keep);
    select.value = keep;
  }

  function groupKey(word) {
    return store.primaryCategory(word) || "Other / Miscellaneous";
  }

  /* Smart order interleaves topics, so the list is re-ordered into one block per
     topic. A heading then covers a contiguous run and survives pagination. */
  function groupedByCategory(list) {
    var buckets = {};
    (list || []).forEach(function (word) {
      var key = groupKey(word);
      if (!buckets[key]) buckets[key] = [];
      buckets[key].push(word);
    });
    var keys = Object.keys(buckets).sort(function (a, b) {
      return buckets[b].length - buckets[a].length || a.localeCompare(b);
    });
    var words = [];
    var totals = {};
    keys.forEach(function (key) {
      totals[key] = buckets[key].length;
      words = words.concat(buckets[key]);
    });
    return { words: words, totals: totals };
  }

  function groupHead(run, total) {
    var shown = run.words.length;
    var label =
      shown === total
        ? total + " word" + (total === 1 ? "" : "s")
        : shown + " of " + total + " words";
    return (
      '<button type="button" class="vocab-group__head" data-open-level-category="' +
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
  }

  function renderGroupedWordList(visible, start, totals) {
    var runs = [];
    visible.forEach(function (word, index) {
      var key = groupKey(word);
      var open = runs[runs.length - 1];
      if (open && open.key === key) {
        open.words.push(word);
        return;
      }
      runs.push({ key: key, words: [word], start: start + index });
    });
    return runs
      .map(function (run) {
        return (
          '<section class="vocab-group">' +
          groupHead(run, totals[run.key]) +
          wordList(run.words, run.start) +
          "</section>"
        );
      })
      .join("");
  }

  function renderLevelResults() {
    var results = store.filter({
      query: $("level-search") ? $("level-search").value : "",
      hsk: currentLevel,
      category: $("level-category") ? $("level-category").value : "all",
      status: $("level-status") ? $("level-status").value : "all",
      sort: "pinyin",
    });
    var count = $("level-result-count");
    if (count) count.textContent = results.length + " word" + (results.length === 1 ? "" : "s");
    levelPage = Math.min(Math.max(1, levelPage), pageCount(results.length));
    var start = (levelPage - 1) * PAGE_SIZE;
    var list = $("level-results");
    if (list) {
      var visible = results.slice(start, start + PAGE_SIZE);
      list.innerHTML = results.length
        ? wordList(visible, start)
        : '<div class="empty-state"><strong>No matching words</strong><p>Try another topic or clear the search.</p></div>';
    }
    renderPagination("level-pagination", "level", levelPage, results.length);
  }

  function renderLevel(level) {
    if (level && LEVELS.indexOf(level) >= 0 && level !== currentLevel) {
      currentLevel = level;
      levelPage = 1;
      if ($("level-category")) $("level-category").value = "all";
      if ($("level-search")) $("level-search").value = "";
    }
    var total = store.hskCounts()[currentLevel] || 0;
    var title = $("level-title");
    var subtitle = $("level-subtitle");
    if (title) title.textContent = levelLabel(currentLevel);
    if (subtitle) {
      subtitle.textContent =
        total + " words · " + sortedLevelCategories(currentLevel).length + " topics in this level";
    }
    renderLevelSwitch();
    populateLevelCategorySelect();
    renderLevelCategories();
    renderLevelResults();
  }

  function updateLearnPool(reset) {
    var reviewMode = $("learn-review") ? $("learn-review").value : "today";
    var candidates = store.filter({
      hsk: $("learn-hsk") ? $("learn-hsk").value : "all",
      category: $("learn-category") ? $("learn-category").value : "all",
      status: reviewMode === "today" ? "all" : reviewMode,
      sort: "smart",
    });
    learnPool =
      reviewMode === "today"
        ? learning.todayQueue(candidates, learning.get().dailyGoal || 20)
        : candidates;
    if (reset || learnIndex >= learnPool.length) learnIndex = 0;
    if (reset) {
      learnAnswered = 0;
      currentQuiz = null;
    }
    renderLearn();
  }

  function exampleMarkup(word) {
    var exTrad = store.example(word, "traditional");
    if (!exTrad) return "";
    return (
      '<div class="learn-example"><span>Example sentence</span>' +
      '<p class="learn-example__zh' + shown("traditional") + '"><b>繁體</b> ' + escapeHtml(exTrad) + "</p>" +
      '<p class="learn-example__zh' + shown("simplified") + '"><b>简体</b> ' +
      escapeHtml(store.example(word, "simplified") || exTrad) + "</p>" +
      (store.example(word, "pinyin")
        ? '<p class="learn-example__pinyin">' + escapeHtml(store.example(word, "pinyin")) + "</p>"
        : "") +
      (store.example(word, "english")
        ? '<p class="' + shown("english").trim() + '">' + escapeHtml(store.example(word, "english")) + "</p>"
        : "") +
      (store.example(word, "hindi")
        ? '<p lang="hi" class="' + shown("hindi").trim() + '">' + escapeHtml(store.example(word, "hindi")) + "</p>"
        : "") +
      '<button type="button" class="learn-example__audio" data-word-action="listen" data-word-id="' +
      escapeHtml(word.id) + '">🔊 Sentence audio</button></div>'
    );
  }

  function toneNumber(pinyin) {
    var value = String(pinyin || "").toLowerCase();
    if (/[āēīōūǖ]/.test(value)) return "1";
    if (/[áéíóúǘ]/.test(value)) return "2";
    if (/[ǎěǐǒǔǚ]/.test(value)) return "3";
    if (/[àèìòùǜ]/.test(value)) return "4";
    var numbered = value.match(/[1-4]/);
    return numbered ? numbered[0] : "5";
  }

  function quizChoices(correct, field) {
    var choices = [correct];
    var offset = 1;
    while (choices.length < 4 && offset < learnPool.length + 4) {
      var candidate = learnPool[(learnIndex + offset) % learnPool.length];
      var value = candidate && candidate[field];
      var duplicate = choices.some(function (item) {
        return (typeof item === "object" ? item[field] : item) === value;
      });
      if (value && !duplicate) choices.push(typeof correct === "object" ? candidate : value);
      offset += 1;
    }
    return choices.sort(function (a, b) {
      return String(a).localeCompare(String(b));
    });
  }

  function makeQuiz() {
    var word = learnPool[learnIndex];
    if (!word) return null;
    var type = (Math.floor(learnAnswered / 5) - 1) % 5;
    var quiz = { word: word, type: type, correct: "", prompt: "", choices: [], listen: false };
    if (type === 0) {
      quiz.prompt = word.traditional + " means…";
      quiz.correct = word.english + " · " + word.hindi;
      quiz.choices = quizChoices(word, "english").map(function (item) {
        return item.english + " · " + item.hindi;
      });
    } else if (type === 1) {
      quiz.prompt = word.english + " · " + word.hindi;
      quiz.correct = word.traditional;
      quiz.choices = quizChoices(word.traditional, "traditional");
    } else if (type === 2) {
      quiz.prompt = word.pinyin;
      quiz.correct = word.traditional;
      quiz.choices = quizChoices(word.traditional, "traditional");
    } else if (type === 3) {
      quiz.prompt = "Listen and choose the word";
      quiz.correct = word.traditional;
      quiz.choices = quizChoices(word.traditional, "traditional");
      quiz.listen = true;
    } else {
      quiz.prompt = "What is the first tone in “" + word.pinyin + "”?";
      quiz.correct = toneNumber(word.pinyin);
      quiz.choices = ["1", "2", "3", "4", "5"];
    }
    return quiz;
  }

  function renderQuiz() {
    var wrap = $("learn-card");
    if (!wrap || !currentQuiz) return;
    wrap.innerHTML =
      '<article class="quiz-card"><p class="eyebrow">Quick check</p><h2>' +
      escapeHtml(currentQuiz.prompt) +
      "</h2>" +
      (currentQuiz.listen
        ? '<button type="button" class="quiz-listen" data-quiz-listen="true">🔊 Listen again</button>'
        : "") +
      '<div class="quiz-choices">' +
      currentQuiz.choices.map(function (choice) {
        return '<button type="button" data-quiz-choice="' + escapeHtml(choice) + '">' + escapeHtml(choice) + "</button>";
      }).join("") +
      "</div></article>";
    if (currentQuiz.listen) speak(currentQuiz.word.traditional, currentQuiz.word);
  }

  function renderLearn() {
    if (currentQuiz) {
      renderQuiz();
      return;
    }
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
      wrap.innerHTML = '<div class="empty-state"><strong>Today\u2019s lesson is complete!</strong><p>Great work. Come back tomorrow for your scheduled reviews.</p></div>';
      return;
    }
    wrap.innerHTML =
      '<article class="learn-card">' +
      '<button type="button" class="learn-card__main" data-word-action="listen" data-word-id="' +
      escapeHtml(word.id) +
      '" data-speak-text="' +
      escapeHtml(word.traditional) +
      '">' +
      escapeHtml(word.traditional) +
      "</button>" +
      '<div class="script-pair script-pair--learn">' +
      '<div class="script-block script-block--traditional' + shown("traditional") + '"><span class="script-block__label">繁體 Traditional</span><button type="button" class="learn-card__han" data-word-action="listen" data-word-id="' +
      escapeHtml(word.id) +
      '" data-speak-text="' +
      escapeHtml(word.traditional) +
      '">' +
      escapeHtml(word.traditional) +
      "</button></div>" +
      '<div class="script-block script-block--simplified' + shown("simplified") + '"><span class="script-block__label">简体 Simplified</span><button type="button" class="learn-card__han" data-word-action="details" data-word-id="' +
      escapeHtml(word.id) +
      '">' +
      escapeHtml(word.simplified) +
      "</button></div></div>" +
      '<p class="learn-card__pinyin">' +
      escapeHtml(word.pinyin) +
      "</p>" +
      '<div class="learn-card__answer"><p class="' + shown("english").trim() + '"><span>English</span>' +
      escapeHtml(word.english) +
      '</p><p lang="hi" class="' + shown("hindi").trim() + '"><span>हिन्दी</span>' +
      escapeHtml(word.hindi) +
      "</p>" + exampleMarkup(word) + "</div>" +
      '<div class="learn-rating" aria-label="Answer for this word">' +
      '<button type="button" data-word-action="listen" data-word-id="' + escapeHtml(word.id) + '">🔊<span>Listen</span></button>' +
      '<button type="button" data-srs-answer="know">✅<span>I Know</span></button>' +
      '<button type="button" data-srs-answer="forgot">❌<span>Forgot</span></button>' +
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
        statCard("Difficult words", stats.difficult, stats.due + " reviews due");
    }
    var hskCounts = store.hskCounts();
    var bars = $("progress-hsk");
    if (bars) {
      bars.innerHTML = ["1", "2", "3", "4", "5", "6", "outside-hsk"]
        .map(function (level) {
          var total = hskCounts[level] || 0;
          var levelWords = store.filter({ hsk: level, sort: "smart" });
          var learned = 0;
          var reviewing = 0;
          var difficult = 0;
          levelWords.forEach(function (word) {
            var review = learning.get().reviews[word.id];
            if (learning.isDifficult(word.id)) difficult += 1;
            else if (review && review.stage < 2) reviewing += 1;
            else if (learning.isLearned(word.id)) learned += 1;
          });
          var remaining = Math.max(0, total - learned - reviewing - difficult);
          var percent = total ? Math.round((learned / total) * 100) : 0;
          return (
            '<div class="progress-row"><div class="progress-row__heading"><strong>' +
            (level === "outside-hsk" ? "Outside HSK" : "HSK " + level) +
            "</strong><span>" + percent + "%</span></div><progress max=\"100\" value=\"" +
            percent +
            '\"></progress><p class="progress-row__detail"><span>✅ ' + learned + " learned</span>" +
            "<span>🔁 " + reviewing + " reviewing</span>" +
            "<span>❗ " + difficult + " difficult</span>" +
            "<span>○ " + remaining + " remaining</span></p></div>"
          );
        })
        .join("");
    }
  }

  function refreshAll() {
    renderDashboard();
    renderBrowse();
    renderLevel();
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
      speak(button.getAttribute("data-speak-text") || word.traditional, word);
      return;
    }
    if (action === "details") {
      openWordDetails(word, button);
      return;
    }
    if (action === "favorite") learning.toggleFavorite(id);
    if (action === "learned") learning.markLearned(id);
    if (action === "difficult") learning.toggleDifficult(id);
  }

  function bind() {
    document.addEventListener("click", function (event) {
      if (event.target.closest("[data-word-detail-close]")) {
        closeWordDetails();
        return;
      }
      if (event.target === wordDetailOverlay) {
        closeWordDetails();
        return;
      }
      var action = event.target.closest("[data-word-action]");
      if (action) {
        handleAction(action);
        return;
      }
      var srs = event.target.closest("[data-srs-answer]");
      if (srs) {
        var studiedWord = learnPool[learnIndex];
        if (!studiedWord) return;
        var correct = srs.getAttribute("data-srs-answer") === "know";
        learning.answerReview(studiedWord.id, correct);
        learnAnswered += 1;
        var feedback = $("learn-feedback");
        if (feedback) feedback.textContent = correct ? "✅ Scheduled for review" : "❌ No problem — we’ll show it again soon";
        if (learnAnswered % 5 === 0) currentQuiz = makeQuiz();
        learnIndex += 1;
        window.setTimeout(function () {
          if (feedback) feedback.textContent = "";
          renderLearn();
        }, 350);
        return;
      }
      var quizListen = event.target.closest("[data-quiz-listen]");
      if (quizListen && currentQuiz) {
        speak(currentQuiz.word.traditional, currentQuiz.word);
        return;
      }
      var quizChoice = event.target.closest("[data-quiz-choice]");
      if (quizChoice && currentQuiz && !quizLocked) {
        var picked = quizChoice.getAttribute("data-quiz-choice");
        var quizFeedback = $("learn-feedback");
        if (picked !== currentQuiz.correct) {
          quizChoice.classList.add("is-wrong");
          if (quizFeedback) quizFeedback.textContent = "❌ Try again";
          return;
        }
        quizLocked = true;
        quizChoice.classList.add("is-correct");
        if (quizFeedback) quizFeedback.textContent = "✅ Correct!";
        window.setTimeout(function () {
          currentQuiz = null;
          quizLocked = false;
          if (quizFeedback) quizFeedback.textContent = "";
          renderLearn();
        }, 650);
        return;
      }
      var pager = event.target.closest("[data-page-action]");
      if (pager) {
        var target = pager.getAttribute("data-page-target");
        var pageAction = pager.getAttribute("data-page-action");
        if (target === "browse") {
          if (pageAction === "first") browsePage = 1;
          if (pageAction === "prev") browsePage = Math.max(1, browsePage - 1);
          if (pageAction === "next") browsePage += 1;
          if (pageAction === "last") browsePage = Number.MAX_SAFE_INTEGER || 9007199254740991;
          renderBrowse();
        }
        if (target === "level") {
          if (pageAction === "first") levelPage = 1;
          if (pageAction === "prev") levelPage = Math.max(1, levelPage - 1);
          if (pageAction === "next") levelPage += 1;
          if (pageAction === "last") levelPage = Number.MAX_SAFE_INTEGER || 9007199254740991;
          renderLevelResults();
        }
        return;
      }
      var category = event.target.closest("[data-open-category]");
      if (category) {
        var select = $("browse-category");
        if (select) select.value = category.getAttribute("data-open-category");
        browsePage = 1;
        setBrowseMode("category");
        if (window.AppRouter) window.AppRouter.go("categories");
        renderBrowse();
        return;
      }
      var hsk = event.target.closest("[data-open-hsk]");
      if (hsk) {
        openLevel(hsk.getAttribute("data-open-hsk"));
        return;
      }
      var levelButton = event.target.closest("[data-open-level]");
      if (levelButton) {
        openLevel(levelButton.getAttribute("data-open-level"));
        return;
      }
      var levelCategory = event.target.closest("[data-open-level-category]");
      if (levelCategory) {
        var picked = levelCategory.getAttribute("data-open-level-category");
        var levelSelect2 = $("level-category");
        if (levelSelect2) {
          levelSelect2.value = picked === "all" || levelSelect2.value === picked ? "all" : picked;
        }
        levelPage = 1;
        renderLevelCategories();
        renderLevelResults();
        return;
      }
      var tab = event.target.closest("[data-browse-tab]");
      if (tab) {
        browsePage = 1;
        setBrowseMode(tab.getAttribute("data-browse-tab"));
        renderBrowse();
        return;
      }
      var contentTab = event.target.closest("[data-content-tab]");
      if (contentTab) {
        browseContent = contentTab.getAttribute("data-content-tab") === "sentences" ? "sentences" : "vocabulary";
        browsePage = 1;
        renderBrowseOverview();
        renderBrowse();
        return;
      }
      var levelTab = event.target.closest("[data-hsk-tab]");
      if (levelTab) {
        /* Vocabulary opens the dedicated level page; sentences stay an in-place filter. */
        if (browseContent !== "sentences") {
          openLevel(levelTab.getAttribute("data-hsk-tab"));
          return;
        }
        var levelSelect = $("browse-hsk");
        if (levelSelect) levelSelect.value = levelTab.getAttribute("data-hsk-tab");
        browsePage = 1;
        setBrowseMode("hsk");
        renderBrowse();
        return;
      }
      var resultView = event.target.closest("[data-result-view]");
      if (resultView) {
        browseDisplay = resultView.getAttribute("data-result-view") === "grid" ? "grid" : "list";
        renderBrowse();
      }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && wordDetailOverlay && !wordDetailOverlay.classList.contains("hidden")) {
        closeWordDetails();
      }
    });

    ["browse-search", "browse-hsk", "browse-category", "browse-status", "browse-sort"].forEach(function (id) {
      var element = $(id);
      if (!element) return;
      element.addEventListener(id === "browse-search" ? "input" : "change", function () {
        browsePage = 1;
        renderBrowse();
      });
    });
    ["learn-hsk", "learn-category", "learn-review"].forEach(function (id) {
      var element = $(id);
      if (element) element.addEventListener("change", function () { updateLearnPool(true); });
    });

    ["level-search", "level-category", "level-status"].forEach(function (id) {
      var element = $(id);
      if (!element) return;
      element.addEventListener(id === "level-search" ? "input" : "change", function () {
        levelPage = 1;
        if (id === "level-category") renderLevelCategories();
        renderLevelResults();
      });
    });
    var clearCategory = $("level-clear-category");
    if (clearCategory) clearCategory.addEventListener("click", function () {
      if ($("level-category")) $("level-category").value = "all";
      levelPage = 1;
      renderLevelCategories();
      renderLevelResults();
    });
    var goal = $("daily-goal-input");
    if (goal) goal.addEventListener("change", function () { learning.setDailyGoal(goal.value); });
    var startToday = $("start-today");
    if (startToday) startToday.addEventListener("click", function () {
      if ($("learn-review")) $("learn-review").value = "today";
      updateLearnPool(true);
      if (window.AppRouter) window.AppRouter.go("learn");
    });

    document.querySelectorAll("[data-display-option]").forEach(function (input) {
      var key = input.getAttribute("data-display-option");
      input.checked = displayOptions[key] !== false;
      input.addEventListener("change", function () {
        displayOptions[key] = input.checked;
        saveDisplayOptions();
        renderLearn();
        renderBrowse();
      });
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
      if (view === "home") renderDashboard();
      if (view === "browse") renderBrowse();
      if (view === "learn") renderLearn();
      if (view === "favorites") renderFavorites();
      if (view === "progress") renderProgress();
      var level = window.AppRouter && window.AppRouter.levelForView(view);
      if (level) renderLevel(level);
    },
    setBrowseMode: setBrowseMode,
    openLevel: openLevel,
    renderWordList: wordList,
    categoryIcon: categoryIcon,
    detailsMarkup: function (id) {
      var word = store.byId(id);
      return word ? wordDetailHtml(word) : "";
    },
    speak: speak,
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
