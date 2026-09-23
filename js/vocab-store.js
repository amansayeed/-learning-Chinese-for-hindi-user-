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

  /* Full-spelling order, one syllable at a time. Letters are compared with tone
     marks removed; the tone (1→4, then neutral) breaks a tie only inside that
     syllable, before the next syllable is considered. āngzāng therefore comes
     before ángguì, and the Chinese characters are never a sort key. */
  var MARKED_LETTER = {
    "ā": "a1", "á": "a2", "ǎ": "a3", "à": "a4",
    "ē": "e1", "é": "e2", "ě": "e3", "è": "e4",
    "ī": "i1", "í": "i2", "ǐ": "i3", "ì": "i4",
    "ō": "o1", "ó": "o2", "ǒ": "o3", "ò": "o4",
    "ū": "u1", "ú": "u2", "ǔ": "u3", "ù": "u4",
    "ǖ": "u1", "ǘ": "u2", "ǚ": "u3", "ǜ": "u4", "ü": "u5",
    "ń": "n2", "ň": "n3", "ǹ": "n4", "ḿ": "m2",
  };
  var SYLLABLE_LIST = (
    "a ai an ang ao ba bai ban bang bao bei ben beng bi bian biao bie bin bing bo bu " +
    "ca cai can cang cao ce cen ceng cha chai chan chang chao che chen cheng chi chong chou chu chua chuai chuan chuang chui chun chuo ci cong cou cu cuan cui cun cuo " +
    "da dai dan dang dao de dei den deng di dia dian diao die ding diu dong dou du duan dui dun duo " +
    "e ei en eng er fa fan fang fei fen feng fo fou fu " +
    "ga gai gan gang gao ge gei gen geng gong gou gu gua guai guan guang gui gun guo " +
    "ha hai han hang hao he hei hen heng hm hng hong hou hu hua huai huan huang hui hun huo " +
    "ji jia jian jiang jiao jie jin jing jiong jiu ju juan jue jun " +
    "ka kai kan kang kao ke kei ken keng kong kou ku kua kuai kuan kuang kui kun kuo " +
    "la lai lan lang lao le lei leng li lia lian liang liao lie lin ling liu lo long lou lu luan lue lun luo " +
    "m ma mai man mang mao me mei men meng mi mian miao mie min ming miu mo mou mu " +
    "n na nai nan nang nao ne nei nen neng ng ni nian niang niao nie nin ning niu nong nou nu nuan nue nun nuo " +
    "o ou pa pai pan pang pao pei pen peng pi pian piao pie pin ping po pou pu " +
    "qi qia qian qiang qiao qie qin qing qiong qiu qu quan que qun " +
    "ran rang rao re ren reng ri rong rou ru rua ruan rui run ruo " +
    "sa sai san sang sao se sen seng sha shai shan shang shao she shei shen sheng shi shou shu shua shuai shuan shuang shui shun shuo si song sou su suan sui sun suo " +
    "ta tai tan tang tao te teng ti tian tiao tie ting tong tou tu tuan tui tun tuo " +
    "wa wai wan wang wei wen weng wo wu " +
    "xi xia xian xiang xiao xie xin xing xiong xiu xu xuan xue xun " +
    "ya yai yan yang yao ye yi yin ying yo yong you yu yuan yue yun " +
    "za zai zan zang zao ze zei zen zeng zha zhai zhan zhang zhao zhe zhei zhen zheng zhi zhong zhou zhu zhua zhuai zhuan zhuang zhui zhun zhuo zi zong zou zu zuan zui zun zuo"
  ).split(" ");
  var SYLLABLE_SET = {};
  SYLLABLE_LIST.forEach(function (syllable) { SYLLABLE_SET[syllable] = true; });

  function readChunk(chunk) {
    var letters = "";
    var tones = [];
    var value = text(chunk).normalize("NFC").toLowerCase().replace(/u:/g, "u");
    for (var i = 0; i < value.length; i++) {
      var ch = value.charAt(i);
      var marked = MARKED_LETTER[ch];
      if (marked) {
        letters += marked.charAt(0);
        tones.push(marked.charAt(1));
        continue;
      }
      if (ch === "v") {
        letters += "u";
        tones.push("5");
        continue;
      }
      if (ch >= "a" && ch <= "z") {
        letters += ch;
        tones.push("5");
        continue;
      }
      if (ch >= "1" && ch <= "5" && tones.length) tones[tones.length - 1] = ch;
    }
    return { letters: letters, tones: tones };
  }

  function erhuaCount(items) {
    var count = 0;
    items.forEach(function (item) {
      var stem = item.letters.slice(0, -1);
      if (
        item.letters.charAt(item.letters.length - 1) === "r" &&
        stem &&
        SYLLABLE_SET[stem] &&
        !SYLLABLE_SET[item.letters]
      ) {
        count += 1;
      }
    });
    return count;
  }

  function segmentSyllables(letters, tones) {
    var limit = letters.length;
    var seen = [];
    var memo = [];
    function solve(index) {
      if (index === limit) return [];
      if (seen[index]) return memo[index];
      seen[index] = true;
      var best = null;
      var bestErhua = 0;
      var max = Math.min(6, limit - index);
      for (var len = max; len >= 1; len--) {
        var part = letters.substr(index, len);
        var stem = part.charAt(part.length - 1) === "r" ? part.slice(0, -1) : "";
        if (!SYLLABLE_SET[part] && !(stem && SYLLABLE_SET[stem])) continue;
        var tone = "5";
        var toneCount = 0;
        for (var cursor = index; cursor < index + len; cursor++) {
          if (tones[cursor] !== "5") {
            toneCount += 1;
            if (tone === "5") tone = tones[cursor];
          }
        }
        if (toneCount > 1) continue;
        var rest = solve(index + len);
        if (!rest) continue;
        var candidate = [{ letters: part, tone: tone }].concat(rest);
        var candidateErhua = erhuaCount(candidate);
        if (
          !best ||
          candidate.length < best.length ||
          (candidate.length === best.length && candidateErhua < bestErhua)
        ) {
          best = candidate;
          bestErhua = candidateErhua;
        }
      }
      memo[index] = best;
      return best;
    }
    var parsed = solve(0);
    if (parsed) return parsed;
    var tone = "5";
    for (var index = 0; index < tones.length; index++) {
      if (tones[index] !== "5") {
        tone = tones[index];
        break;
      }
    }
    return [{ letters: letters, tone: tone }];
  }

  function pinyinSyllables(word) {
    if (word.__pinyinSyllables) return word.__pinyinSyllables;
    var primary = text(word.pinyin).split("/")[0].trim();
    var chunks = primary.split(/[\s'’·]+/).filter(Boolean);
    var syllables = [];
    chunks.forEach(function (chunk) {
      var read = readChunk(chunk);
      if (!read.letters) return;
      segmentSyllables(read.letters, read.tones).forEach(function (syllable) {
        syllables.push(syllable);
      });
    });
    word.__pinyinSyllables = syllables;
    return syllables;
  }

  function comparePinyin(a, b) {
    var left = pinyinSyllables(a);
    var right = pinyinSyllables(b);
    var count = Math.max(left.length, right.length);
    for (var index = 0; index < count; index++) {
      if (!left[index]) return -1;
      if (!right[index]) return 1;
      if (left[index].letters !== right[index].letters) {
        return left[index].letters < right[index].letters ? -1 : 1;
      }
      if (left[index].tone !== right[index].tone) {
        return left[index].tone < right[index].tone ? -1 : 1;
      }
    }
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
    registerSupplemental: function (list, aliases) {
      (list || []).forEach(function (word) {
        if (word && word.id) byId[word.id] = word;
      });
      Object.keys(aliases || {}).forEach(function (duplicateId) {
        byId[duplicateId] = byId[aliases[duplicateId]] || null;
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
