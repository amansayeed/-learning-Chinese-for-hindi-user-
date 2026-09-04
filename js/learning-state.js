(function () {
  "use strict";

  var STORAGE_KEY = "chinese-vocab-learning-v1";
  var VERSION = 2;
  var REVIEW_DAYS = [1, 3, 7, 14, 30, 60, 120, 240];
  var listeners = [];

  function today() {
    var d = new Date();
    return [
      d.getFullYear(),
      String(d.getMonth() + 1).padStart(2, "0"),
      String(d.getDate()).padStart(2, "0"),
    ].join("-");
  }

  function emptyState() {
    return {
      version: VERSION,
      learned: {},
      favorites: {},
      difficult: {},
      reviews: {},
      recent: [],
      daily: {},
      dailyGoal: 20,
      xp: 0,
      streak: { current: 0, lastDate: "" },
    };
  }

  function read() {
    try {
      var parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      if (!parsed) return emptyState();
      var base = emptyState();
      Object.keys(base).forEach(function (key) {
        if (parsed[key] !== undefined) base[key] = parsed[key];
      });
      base.version = VERSION;
      return base;
    } catch (e) {
      return emptyState();
    }
  }

  var state = read();

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {}
    listeners.forEach(function (fn) {
      fn(state);
    });
  }

  function dateBefore(dateString) {
    var d = new Date(dateString + "T12:00:00");
    d.setDate(d.getDate() - 1);
    return [
      d.getFullYear(),
      String(d.getMonth() + 1).padStart(2, "0"),
      String(d.getDate()).padStart(2, "0"),
    ].join("-");
  }

  function touchDay() {
    var key = today();
    if (!state.daily[key]) state.daily[key] = { learned: 0, reviewed: 0, xp: 0, wordIds: [] };
    if (!Array.isArray(state.daily[key].wordIds)) state.daily[key].wordIds = [];
    if (state.streak.lastDate !== key) {
      state.streak.current =
        state.streak.lastDate === dateBefore(key) ? state.streak.current + 1 : 1;
      state.streak.lastDate = key;
    }
    return state.daily[key];
  }

  function setFlag(bucket, id, on) {
    if (!id) return false;
    if (on === undefined) on = !bucket[id];
    if (on) bucket[id] = true;
    else delete bucket[id];
    save();
    return !!on;
  }

  function markLearned(id, on) {
    if (!id) return false;
    if (on === undefined) on = !state.learned[id];
    var wasLearned = !!state.learned[id];
    if (on) {
      state.learned[id] = { learnedAt: new Date().toISOString() };
      state.recent = [id]
        .concat(state.recent.filter(function (x) { return x !== id; }))
        .slice(0, 20);
      if (!wasLearned) {
        var day = touchDay();
        day.learned += 1;
        if (day.wordIds.indexOf(id) < 0) day.wordIds.push(id);
        day.xp += 10;
        state.xp += 10;
      }
    } else {
      delete state.learned[id];
      state.recent = state.recent.filter(function (item) { return item !== id; });
    }
    save();
    return !!on;
  }

  function markReviewed(id, correct) {
    if (!id) return;
    var day = touchDay();
    day.reviewed += 1;
    if (day.wordIds.indexOf(id) < 0) day.wordIds.push(id);
    var points = correct ? 5 : 1;
    day.xp += points;
    state.xp += points;
    if (!correct) state.difficult[id] = true;
    save();
  }

  function dayStamp(date) {
    var d = date || new Date();
    return [
      d.getFullYear(),
      String(d.getMonth() + 1).padStart(2, "0"),
      String(d.getDate()).padStart(2, "0"),
    ].join("-");
  }

  function addDays(days) {
    var d = new Date();
    d.setHours(12, 0, 0, 0);
    d.setDate(d.getDate() + days);
    return dayStamp(d);
  }

  function reviewStatus(id) {
    var review = state.reviews[id];
    if (!review) return state.learned[id] ? "reviewing" : "new";
    if (review.due <= today()) return "due";
    return "reviewing";
  }

  function answerReview(id, correct) {
    if (!id) return null;
    var wasLearned = !!state.learned[id];
    var previous = state.reviews[id] || { stage: -1, lapses: 0 };
    var stage = correct ? Math.min(previous.stage + 1, REVIEW_DAYS.length - 1) : 0;
    var interval = correct ? REVIEW_DAYS[stage] : 0;
    var review = {
      stage: stage,
      due: addDays(interval),
      lastReviewed: new Date().toISOString(),
      correct: (previous.correct || 0) + (correct ? 1 : 0),
      lapses: (previous.lapses || 0) + (correct ? 0 : 1),
    };
    state.reviews[id] = review;

    if (correct) {
      if (!state.learned[id]) {
        state.learned[id] = { learnedAt: new Date().toISOString() };
        state.recent = [id]
          .concat(state.recent.filter(function (x) { return x !== id; }))
          .slice(0, 20);
      }
      if (stage >= 2) delete state.difficult[id];
    } else {
      state.difficult[id] = true;
    }

    var day = touchDay();
    if (correct && !wasLearned) day.learned += 1;
    day.reviewed += 1;
    if (day.wordIds.indexOf(id) < 0) day.wordIds.push(id);
    var points = correct ? (wasLearned ? 5 : 10) : 1;
    day.xp += points;
    state.xp += points;
    save();
    return review;
  }

  function todayQueue(words, limit) {
    var now = today();
    var max = Math.max(1, Number(limit) || state.dailyGoal || 20);
    var due = [];
    var difficult = [];
    var fresh = [];
    (words || []).forEach(function (word, index) {
      var id = word && word.id;
      if (!id) return;
      var review = state.reviews[id];
      var item = { word: word, index: index, due: review && review.due };
      if (review && review.due <= now) due.push(item);
      else if (state.difficult[id]) difficult.push(item);
      else if (!state.learned[id] && !review) fresh.push(item);
    });
    due.sort(function (a, b) { return a.due.localeCompare(b.due) || a.index - b.index; });
    return due
      .concat(difficult, fresh)
      .filter(function (item, index, all) {
        return all.findIndex(function (other) { return other.word.id === item.word.id; }) === index;
      })
      .slice(0, max)
      .map(function (item) { return item.word; });
  }

  function count(obj) {
    return Object.keys(obj || {}).length;
  }

  window.LearningState = {
    get: function () { return state; },
    isLearned: function (id) { return !!state.learned[id]; },
    isFavorite: function (id) { return !!state.favorites[id]; },
    isDifficult: function (id) { return !!state.difficult[id]; },
    reviewStatus: reviewStatus,
    isDue: function (id) { return reviewStatus(id) === "due"; },
    toggleFavorite: function (id) { return setFlag(state.favorites, id); },
    toggleDifficult: function (id) { return setFlag(state.difficult, id); },
    markLearned: markLearned,
    markReviewed: markReviewed,
    answerReview: answerReview,
    todayQueue: todayQueue,
    reviewIntervals: REVIEW_DAYS.slice(),
    setDailyGoal: function (goal) {
      state.dailyGoal = Math.max(1, Math.min(200, Number(goal) || 20));
      save();
    },
    stats: function (total) {
      var day = state.daily[today()] || { learned: 0, reviewed: 0, xp: 0 };
      day.unique = Array.isArray(day.wordIds) ? day.wordIds.length : day.learned + day.reviewed;
      var learned = count(state.learned);
      return {
        total: total || 0,
        learned: learned,
        remaining: Math.max(0, (total || 0) - learned),
        progress: total ? Math.round((learned / total) * 100) : 0,
        favorites: count(state.favorites),
        difficult: count(state.difficult),
        reviewing: count(state.reviews),
        due: Object.keys(state.reviews).filter(function (id) {
          return state.reviews[id].due <= today();
        }).length,
        today: day,
        dailyGoal: state.dailyGoal,
        streak: state.streak.current,
        xp: state.xp,
        level: Math.floor(state.xp / 250) + 1,
      };
    },
    subscribe: function (fn) {
      listeners.push(fn);
      return function () {
        listeners = listeners.filter(function (item) { return item !== fn; });
      };
    },
    storageKey: STORAGE_KEY,
  };
})();
