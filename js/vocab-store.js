(function () {
  "use strict";

  var payload = window.__VOCAB_MASTER__ || { words: [] };
  var words = payload.words || payload.entries || payload.vocabulary || [];

  function text(value) {
    return value == null ? "" : String(value);
  }

  function fold(value) {
    return text(value)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/ü/g, "u")
      .replace(/Ü/g, "u")
      .toLowerCase()
      .replace(/u:/g, "u")
      .replace(/v/g, "u")
      .replace(/\s+/g, " ")
      .trim();
  }

  function hskValue(word) {
    var raw =
      word.hskLevel !== undefined
        ? word.hskLevel
        : word.hsk && word.hsk.level !== undefined
          ? word.hsk.level
          : word.hsk;
    if (raw === null || raw === undefined || raw === "") return "outside-hsk";
    var match = text(raw).match(/[1-6]/);
    return match ? match[0] : "outside-hsk";
  }

  function primaryCategory(word) {
    return text(
      word.primaryCategory ||
        word.categoryPrimary ||
        (word.categories && word.categories.primary) ||
        "Other / Miscellaneous"
    );
  }

  function secondaryCategories(word) {
    var value =
      word.secondaryCategories ||
      word.categorySecondary ||
      (word.categories && word.categories.secondary) ||
      [];
    return Array.isArray(value) ? value.map(text) : value ? [text(value)] : [];
  }

  function categories(word) {
    return [primaryCategory(word)].concat(secondaryCategories(word));
  }

  function example(word, key) {
    var ex = word.example || word.examples || {};
    if (typeof ex === "string") return key === "chinese" ? ex : "";
    var aliases = {
      chinese: ["chinese", "traditional", "sentence"],
      pinyin: ["pinyin"],
      english: ["english", "englishExample"],
      hindi: ["hindi", "hindiExample"],
    };
    var keys = aliases[key] || [key];
    for (var i = 0; i < keys.length; i++) {
      if (ex[keys[i]]) return text(ex[keys[i]]);
      if (word[keys[i] + "Example"]) return text(word[keys[i] + "Example"]);
    }
    return "";
  }

  function difficulty(word) {
    var raw = word.difficulty;
    if (raw && typeof raw === "object") raw = raw.label;
    raw =
      raw ||
      (hskValue(word) === "outside-hsk"
        ? "Advanced"
        : Number(hskValue(word)) <= 2
          ? "Beginner"
          : Number(hskValue(word)) <= 4
            ? "Intermediate"
            : "Advanced");
    raw = text(raw);
    return raw ? raw.charAt(0).toUpperCase() + raw.slice(1) : "Advanced";
  }

  function searchText(word) {
    if (word.__searchText) return word.__searchText;
    var values = [
      word.traditional,
      word.simplified,
      word.pinyin,
      word.english,
      word.hindi,
      "hsk " + hskValue(word),
      hskValue(word) === "outside-hsk" ? "outside hsk other" : "",
      categories(word).join(" "),
    ];
    word.__searchText = fold(values.join(" "));
    return word.__searchText;
  }

  function compareWords(a, b, sort) {
    if (sort === "difficulty") {
      var order = { Beginner: 1, Intermediate: 2, Advanced: 3 };
      var diff = (order[difficulty(a)] || 9) - (order[difficulty(b)] || 9);
      if (diff) return diff;
    }
    if (sort === "hsk") {
      var ah = hskValue(a) === "outside-hsk" ? 99 : Number(hskValue(a));
      var bh = hskValue(b) === "outside-hsk" ? 99 : Number(hskValue(b));
      if (ah !== bh) return ah - bh;
    }
    return text(a.pinyin || a.traditional).localeCompare(
      text(b.pinyin || b.traditional),
      undefined,
      { sensitivity: "base" }
    );
  }

  function filter(options) {
    options = options || {};
    var query = fold(options.query || "");
    var hsk = text(options.hsk || "all");
    var category = text(options.category || "all");
    var status = text(options.status || "all");
    var state = window.LearningState;
    return words
      .filter(function (word) {
        if (query && searchText(word).indexOf(query) < 0) return false;
        if (hsk !== "all" && hskValue(word) !== hsk) return false;
        if (category !== "all" && categories(word).indexOf(category) < 0) return false;
        if (state && status === "learned" && !state.isLearned(word.id)) return false;
        if (state && status === "unlearned" && state.isLearned(word.id)) return false;
        if (state && status === "favorite" && !state.isFavorite(word.id)) return false;
        if (state && status === "difficult" && !state.isDifficult(word.id)) return false;
        return true;
      })
      .sort(function (a, b) { return compareWords(a, b, options.sort || "pinyin"); });
  }

  function categoryCounts(list) {
    var counts = {};
    (list || words).forEach(function (word) {
      categories(word).forEach(function (category) {
        counts[category] = (counts[category] || 0) + 1;
      });
    });
    return counts;
  }

  function hskCounts(list) {
    var counts = { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "outside-hsk": 0 };
    (list || words).forEach(function (word) {
      var value = hskValue(word);
      counts[value] = (counts[value] || 0) + 1;
    });
    return counts;
  }

  var byId = {};
  words.forEach(function (word, index) {
    if (!word.id) word.id = "legacy-" + index + "-" + fold(word.traditional + "-" + word.pinyin).replace(/[^a-z0-9\u3400-\u9fff]+/g, "-");
    byId[word.id] = word;
  });

  window.VocabStore = {
    meta: payload.meta || {},
    all: function () { return words.slice(); },
    byId: function (id) { return byId[id] || null; },
    filter: filter,
    fold: fold,
    hskValue: hskValue,
    primaryCategory: primaryCategory,
    secondaryCategories: secondaryCategories,
    categories: categories,
    categoryCounts: categoryCounts,
    hskCounts: hskCounts,
    difficulty: difficulty,
    example: example,
  };
})();
