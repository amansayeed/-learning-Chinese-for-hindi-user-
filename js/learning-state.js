(function () {
  "use strict";

  var STORAGE_KEY = "chinese-vocab-learning-v1";
  var VERSION = 1;
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
      if (!parsed || parsed.version !== VERSION) return emptyState();
      var base = emptyState();
      Object.keys(base).forEach(function (key) {
        if (parsed[key] !== undefined) base[key] = parsed[key];
      });
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

  function count(obj) {
    return Object.keys(obj || {}).length;
  }

  window.LearningState = {
    get: function () { return state; },
    isLearned: function (id) { return !!state.learned[id]; },
    isFavorite: function (id) { return !!state.favorites[id]; },
    isDifficult: function (id) { return !!state.difficult[id]; },
    toggleFavorite: function (id) { return setFlag(state.favorites, id); },
    toggleDifficult: function (id) { return setFlag(state.difficult, id); },
    markLearned: markLearned,
    markReviewed: markReviewed,
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
