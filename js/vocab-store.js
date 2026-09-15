(function () {
  "use strict";

  var payload = window.__VOCAB_MASTER__ || { words: [] };
  var sourceWords = payload.words || payload.entries || payload.vocabulary || [];
  var words = sourceWords;
  var duplicateAliases = {};
  var duplicateCount = 0;

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

  function compactChinese(value) {
    return text(value)
      .normalize("NFKC")
      .toLowerCase()
      .replace(/\s+/g, "")
      .trim();
  }

  function duplicateKey(word) {
    return [
      compactChinese(word.traditional),
      compactChinese(word.simplified),
      fold(word.pinyin).replace(/\s+/g, ""),
    ].join("\u001f");
  }

  function dedupeHskWords(list) {
    var seen = {};
    var result = [];
    list.forEach(function (word) {
      var level = hskValue(word);
      if (!/^[1-6]$/.test(level)) {
        result.push(word);
        return;
      }
      var key = duplicateKey(word);
      var kept = seen[key];
      if (!kept) {
        seen[key] = word;
        result.push(word);
        return;
      }
      duplicateCount += 1;
      if (word.id && kept.id) duplicateAliases[word.id] = kept.id;
      secondaryCategories(word).forEach(function (category) {
        var current = secondaryCategories(kept);
        if (category !== primaryCategory(kept) && current.indexOf(category) < 0) {
          if (!Array.isArray(kept.secondaryCategories)) kept.secondaryCategories = current;
          kept.secondaryCategories.push(category);
        }
      });
      tocflLevels(word).forEach(function (level) {
        var currentLevels = tocflLevels(kept);
        if (currentLevels.indexOf(level) < 0) {
          if (!Array.isArray(kept.tocflLevels)) kept.tocflLevels = currentLevels;
          kept.tocflLevels.push(level);
        }
      });
    });
    return result;
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

  function tocflLevels(word) {
    var raw = word.tocflLevels || word.tocflLevel || [];
    if (!Array.isArray(raw)) raw = raw ? [raw] : [];
    return raw
      .map(function (value) {
        var match = text(value).toUpperCase().match(/A[12]/);
        return match ? match[0] : "";
      })
      .filter(Boolean);
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
      traditional: ["traditional", "chinese", "sentence"],
      simplified: ["simplified", "chinese", "sentence"],
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
      example(word, "traditional"),
      example(word, "simplified"),
      example(word, "pinyin"),
      example(word, "english"),
      example(word, "hindi"),
      "hsk " + hskValue(word),
      hskValue(word) === "outside-hsk" ? "outside hsk other" : "",
      tocflLevels(word).join(" "),
      categories(word).join(" "),
    ];
    word.__searchText = fold(values.join(" "));
    return word.__searchText;
  }

  /* Dictionary order: letters first, then tone 1–4 before the neutral tone, so
     bā → bá → bǎ → bà → ba stay in the order a learner expects. */
  function syllableTone(syllable) {
    var decomposed = text(syllable).normalize("NFD");
    if (decomposed.indexOf("\u0304") >= 0) return "1";
    if (decomposed.indexOf("\u0301") >= 0) return "2";
    if (decomposed.indexOf("\u030c") >= 0) return "3";
    if (decomposed.indexOf("\u0300") >= 0) return "4";
    var numbered = decomposed.match(/[1-5]/);
    return numbered ? numbered[0] : "5";
  }

  function pinyinKey(word) {
    if (word.__pinyinKey) return word.__pinyinKey;
    var raw = text(word.pinyin).split("/")[0];
    var han = text(word.traditional || word.simplified).split("/")[0];
    word.__pinyinKey = {
      letters: fold(raw).replace(/[^a-z]/g, "") || fold(han),
      tones: raw.split(/\s+/).filter(Boolean).map(syllableTone).join(""),
      han: han,
    };
    return word.__pinyinKey;
  }

  function comparePinyin(a, b) {
    var ka = pinyinKey(a);
    var kb = pinyinKey(b);
    if (ka.letters !== kb.letters) return ka.letters < kb.letters ? -1 : 1;
    if (ka.tones !== kb.tones) return ka.tones < kb.tones ? -1 : 1;
    if (ka.han !== kb.han) return ka.han < kb.han ? -1 : 1;
    return 0;
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
    if (sort === "smart") {
      var ash = hskValue(a) === "outside-hsk" ? 99 : Number(hskValue(a));
      var bsh = hskValue(b) === "outside-hsk" ? 99 : Number(hskValue(b));
      if (ash !== bsh) return ash - bsh;
      var aWord = text(a.traditional || a.simplified).split("/")[0];
      var bWord = text(b.traditional || b.simplified).split("/")[0];
      var aFirstPinyin = fold(a.pinyin).split(" ")[0];
      var bFirstPinyin = fold(b.pinyin).split(" ")[0];
      var pinyinGroupDiff = aFirstPinyin.localeCompare(bFirstPinyin);
      if (pinyinGroupDiff) return pinyinGroupDiff;
      var rootDiff = aWord.charAt(0).localeCompare(bWord.charAt(0));
      if (rootDiff) return rootDiff;
      if (aWord.length !== bWord.length) return aWord.length - bWord.length;
      var pinyinDiff = fold(a.pinyin).localeCompare(fold(b.pinyin));
      if (pinyinDiff) return pinyinDiff;
      return aWord.localeCompare(bWord);
    }
    return comparePinyin(a, b);
  }

  function filter(options) {
    options = options || {};
    var query = fold(options.query || "");
    var hsk = text(options.hsk || "all");
    var tocfl = text(options.tocfl || "all").toUpperCase();
    var category = text(options.category || "all");
    var status = text(options.status || "all");
    var state = window.LearningState;
    return words
      .filter(function (word) {
        if (query && searchText(word).indexOf(query) < 0) return false;
        if (hsk !== "all" && hskValue(word) !== hsk) return false;
        if (tocfl !== "ALL" && tocflLevels(word).indexOf(tocfl) < 0) return false;
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

  function tocflCounts(list) {
    var counts = { A1: 0, A2: 0 };
    (list || words).forEach(function (word) {
      tocflLevels(word).forEach(function (level) {
        counts[level] = (counts[level] || 0) + 1;
      });
    });
    return counts;
  }

  function sentence(word) {
    if (!word || !example(word, "chinese")) return null;
    var ex = word.example || word.examples || {};
    var level = hskValue(word);
    var topic = text(ex.topic || primaryCategory(word));
    return {
      id: "sentence-" + word.id,
      wordId: word.id,
      traditional: example(word, "traditional"),
      simplified: example(word, "simplified"),
      pinyin: example(word, "pinyin"),
      english: example(word, "english"),
      hindi: example(word, "hindi"),
      hskLevel: level,
      topic: topic,
      category: text(
        ex.sentenceCategory ||
          (level === "outside-hsk" ? "Outside HSK" : "HSK " + level) + " · " + topic
      ),
      generated: Boolean(ex.generated),
      needsReview: Boolean(ex.needsReview),
      word: word,
    };
  }

  function sentences(options) {
    return filter(options)
      .map(sentence)
      .filter(Boolean);
  }

  words = dedupeHskWords(sourceWords);

  var byId = {};
  words.forEach(function (word, index) {
    if (!word.id) word.id = "legacy-" + index + "-" + fold(word.traditional + "-" + word.pinyin).replace(/[^a-z0-9\u3400-\u9fff]+/g, "-");
    byId[word.id] = word;
  });
  Object.keys(duplicateAliases).forEach(function (duplicateId) {
    byId[duplicateId] = byId[duplicateAliases[duplicateId]] || null;
  });

  window.VocabStore = {
    meta: payload.meta || {},
    all: function () { return words.slice(); },
    byId: function (id) { return byId[id] || null; },
    registerSupplemental: function (list) {
      (list || []).forEach(function (word) {
        if (word && word.id) byId[word.id] = word;
      });
    },
    filter: filter,
    fold: fold,
    hskValue: hskValue,
    tocflLevels: tocflLevels,
    primaryCategory: primaryCategory,
    secondaryCategories: secondaryCategories,
    categories: categories,
    categoryCounts: categoryCounts,
    hskCounts: hskCounts,
    tocflCounts: tocflCounts,
    difficulty: difficulty,
    example: example,
    sentence: sentence,
    sentences: sentences,
    duplicateCount: duplicateCount,
    smartOrder: function (list) {
      return (list || words).slice().sort(function (a, b) {
        return compareWords(a, b, "smart");
      });
    },
    pinyinOrder: function (list) {
      return (list || words).slice().sort(comparePinyin);
    },
    comparePinyin: comparePinyin,
  };
})();
