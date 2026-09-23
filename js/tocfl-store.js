(function () {
  "use strict";

  var vocabStore = window.VocabStore;
  var datasets = [
    { name: "TOCFL", payload: window.__TOCFL_8000__ },
    { name: "CCCC", payload: window.__TOCFL_CCCC__ },
  ].filter(function (item) {
    return item.payload && Array.isArray(item.payload.words);
  });

  var LEVEL_ORDER = {
    "novice-1": 1,
    "novice-2": 2,
    "level-1": 3,
    "level-2": 4,
    "level-3": 5,
    "level-4": 6,
    "level-5": 7,
    sprouting: 8,
    growing: 9,
    thriving: 10,
  };
  var SOURCE_ORDER = { TOCFL: 1, CCCC: 2 };
  var levelMeta = {};
  var rows = [];

  function text(value) {
    return value == null ? "" : String(value);
  }

  function normalizeForm(value) {
    return text(value).normalize("NFKC").replace(/\s+/g, "").trim();
  }

  function normalizePinyin(value) {
    return text(value)
      .normalize("NFC")
      .toLowerCase()
      .replace(/\s+/g, "")
      .replace(/u:/g, "ü")
      .replace(/v/g, "ü")
      .trim();
  }

  function forms(word) {
    var result = [];
    [word.traditional, word.simplified].forEach(function (value) {
      text(value).split(/[/／]/).forEach(function (form) {
        form = normalizeForm(form);
        if (form && result.indexOf(form) < 0) result.push(form);
      });
    });
    return result;
  }

  function keys(word) {
    var reading = normalizePinyin(word.pinyin);
    return forms(word).map(function (form) {
      return form + "\u001f" + reading;
    });
  }

  datasets.forEach(function (dataset) {
    (dataset.payload.levels || []).forEach(function (level) {
      levelMeta[level.id] = {
        id: level.id,
        code: level.code,
        label: level.label,
        source: dataset.name,
      };
    });
    dataset.payload.words.forEach(function (word) {
      rows.push({ source: dataset.name, word: word });
    });
  });

  /* Union duplicate rows rather than just dropping the later row. This handles
     slash variants transitively and preserves every workbook occurrence. */
  var parent = rows.map(function (_row, index) { return index; });
  var owner = {};

  function root(index) {
    while (parent[index] !== index) {
      parent[index] = parent[parent[index]];
      index = parent[index];
    }
    return index;
  }

  function unite(a, b) {
    a = root(a);
    b = root(b);
    if (a !== b) parent[b] = a;
  }

  rows.forEach(function (row, index) {
    keys(row.word).forEach(function (key) {
      if (owner[key] !== undefined) unite(index, owner[key]);
      else owner[key] = index;
    });
  });

  var groups = {};
  rows.forEach(function (row, index) {
    var key = root(index);
    if (!groups[key]) groups[key] = [];
    groups[key].push(row);
  });

  function priority(row) {
    return [
      LEVEL_ORDER[row.word.level] || 99,
      SOURCE_ORDER[row.source] || 99,
      Number(row.word.sourceRow) || 999999,
      text(row.word.id),
    ];
  }

  function compareTuple(a, b) {
    for (var index = 0; index < Math.max(a.length, b.length); index += 1) {
      if (a[index] === b[index]) continue;
      return a[index] < b[index] ? -1 : 1;
    }
    return 0;
  }

  function unique(values) {
    var seen = {};
    return values.filter(function (value) {
      value = text(value);
      if (!value || seen[value]) return false;
      seen[value] = true;
      return true;
    });
  }

  function copy(value) {
    var result = {};
    Object.keys(value || {}).forEach(function (key) { result[key] = value[key]; });
    return result;
  }

  var aliases = {};
  var words = Object.keys(groups).map(function (groupKey) {
    var occurrences = groups[groupKey].slice().sort(function (a, b) {
      return compareTuple(priority(a), priority(b));
    });
    var canonical = copy(occurrences[0].word);
    var sources = unique(occurrences.map(function (item) { return item.source; }))
      .sort(function (a, b) { return (SOURCE_ORDER[a] || 9) - (SOURCE_ORDER[b] || 9); });
    var categories = [];
    occurrences.forEach(function (item) {
      [item.word.category].concat(item.word.secondaryCategories || []).forEach(function (category) {
        if (category && categories.indexOf(category) < 0) categories.push(category);
      });
      if (item.word.id !== canonical.id) aliases[item.word.id] = canonical.id;
    });
    canonical.secondaryCategories = categories.filter(function (category) {
      return category !== canonical.category;
    }).slice(0, 6);
    canonical.sources = sources;
    canonical.sourceLabel = sources.join(" + ");
    canonical.sourceRecords = occurrences.map(function (item) {
      var meta = levelMeta[item.word.level] || {};
      return {
        source: item.source,
        id: item.word.id,
        level: item.word.level,
        levelCode: item.word.levelCode || meta.code || "",
        levelLabel: meta.label || item.word.level,
        sourceSheet: item.word.sourceSheet || "",
        sourceRow: item.word.sourceRow || 0,
      };
    });
    canonical.allIds = unique(occurrences.map(function (item) { return item.word.id; }));
    canonical.priorityRank = LEVEL_ORDER[canonical.level] || 99;
    return canonical;
  });

  function pinyinCompare(a, b) {
    if (vocabStore && vocabStore.comparePinyin) return vocabStore.comparePinyin(a, b);
    return text(a.pinyin).localeCompare(text(b.pinyin));
  }

  function comparePriority(a, b) {
    var level = (LEVEL_ORDER[a.level] || 99) - (LEVEL_ORDER[b.level] || 99);
    if (level) return level;
    var source = (SOURCE_ORDER[(a.sources || [])[0]] || 99) -
      (SOURCE_ORDER[(b.sources || [])[0]] || 99);
    if (source) return source;
    var row = (Number(a.sourceRow) || 999999) - (Number(b.sourceRow) || 999999);
    if (row) return row;
    return pinyinCompare(a, b);
  }

  words.sort(comparePriority);
  var byId = {};
  words.forEach(function (word) {
    byId[word.id] = word;
    (word.allIds || []).forEach(function (id) { byId[id] = word; });
  });
  if (vocabStore && vocabStore.registerSupplemental) {
    vocabStore.registerSupplemental(words, aliases);
  }

  function fold(value) {
    if (vocabStore && vocabStore.fold) return vocabStore.fold(value);
    return text(value).toLowerCase();
  }

  function filter(options) {
    options = options || {};
    var query = fold(options.query || "");
    var category = text(options.category || "all");
    var source = text(options.source || "all").toUpperCase();
    var level = text(options.level || "all");
    return words.filter(function (word) {
      if (category !== "all" && word.category !== category) return false;
      if (source !== "ALL" && (word.sources || []).indexOf(source) < 0) return false;
      if (
        level !== "all" &&
        !(word.sourceRecords || []).some(function (record) { return record.level === level; })
      ) return false;
      if (query) {
        var searchable = fold([
          word.traditional,
          word.simplified,
          word.pinyin,
          word.english,
        ].join(" "));
        if (searchable.indexOf(query) < 0) return false;
      }
      return true;
    }).sort(comparePriority);
  }

  function categories() {
    var counts = {};
    words.forEach(function (word) {
      counts[word.category] = (counts[word.category] || 0) + 1;
    });
    return counts;
  }

  function levels() {
    return Object.keys(levelMeta).map(function (id) {
      var meta = copy(levelMeta[id]);
      meta.wordCount = words.filter(function (word) { return word.level === id; }).length;
      return meta;
    }).sort(function (a, b) {
      var rank = (LEVEL_ORDER[a.id] || 99) - (LEVEL_ORDER[b.id] || 99);
      if (rank) return rank;
      return (SOURCE_ORDER[a.source] || 9) - (SOURCE_ORDER[b.source] || 9);
    });
  }

  window.TocflStore = {
    all: function () { return words.slice(); },
    byId: function (id) { return byId[id] || null; },
    filter: filter,
    categoryCounts: categories,
    levels: levels,
    levelInfo: function (id) { return levelMeta[id] || null; },
    comparePriority: comparePriority,
    priorityOrder: function (list) { return (list || words).slice().sort(comparePriority); },
    duplicateCount: rows.length - words.length,
    rawCount: rows.length,
    sourceCounts: datasets.reduce(function (result, item) {
      result[item.name] = item.payload.words.length;
      return result;
    }, {}),
  };
})();
