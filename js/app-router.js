(function () {
  "use strict";

  var HSK_NAV = {
    hsk1: { navLevelKey: "chinese-hsk-nav-level", navLessonKey: "chinese-hsk-nav-lesson" },
    hsk2: { navLevelKey: "chinese-hsk2-nav-level", navLessonKey: "chinese-hsk2-nav-lesson" },
    hsk3: { navLevelKey: "chinese-hsk3-nav-level", navLessonKey: "chinese-hsk3-nav-lesson" },
    hsk4: { navLevelKey: "chinese-hsk4-nav-level", navLessonKey: "chinese-hsk4-nav-lesson" },
    hsk5: { navLevelKey: "chinese-hsk5-nav-level", navLessonKey: "chinese-hsk5-nav-lesson" },
    hsk6: { navLevelKey: "chinese-hsk6-nav-level", navLessonKey: "chinese-hsk6-nav-lesson" },
  };

  var VIEWS = [
    "dashboard",
    "hsk",
    "categories",
    "learn",
    "favorites",
    "progress",
    "words",
    "pronounce",
    "tones",
  ].concat(Object.keys(HSK_NAV));

  function normalizeView(id) {
    if (!id) return "dashboard";
    return id;
  }

  function viewPanelId(view) {
    if (view === "dashboard") return "app-view-dashboard";
    if (view === "hsk" || view === "categories") return "app-view-browse";
    if (view === "learn") return "app-view-learn";
    if (view === "favorites") return "app-view-favorites";
    if (view === "progress") return "app-view-progress";
    if (view === "words" || HSK_NAV[view]) return "app-view-words";
    if (view === "pronounce") return "app-view-pronounce";
    if (view === "tones") return "app-view-tones";
    return "app-view-words";
  }

  function setToolbar(view) {
    var wordsTb = document.getElementById("toolbar-words");
    var pronTb = document.getElementById("toolbar-pronounce");
    var isVocab = view === "words" || !!HSK_NAV[view];
    if (wordsTb) wordsTb.classList.toggle("hidden", !isVocab);
    if (pronTb) pronTb.classList.toggle("hidden", view !== "pronounce");
  }

  function markNavActive(view) {
    var hskMenu = document.getElementById("sidebar-hsk-menu");
    var hskOpen = !!HSK_NAV[view];

    document.querySelectorAll("[data-app-view]").forEach(function (el) {
      var v = el.getAttribute("data-app-view");
      var activeView = view;
      if (el.closest(".bottom-nav")) {
        if (view === "hsk") activeView = "categories";
        if (view === "words" || view === "pronounce" || view === "tones" || HSK_NAV[view]) {
          activeView = "learn";
        }
      }
      var on = v === activeView;
      el.classList.toggle("is-active", on);
      if (on) {
        el.setAttribute("aria-current", "page");
      } else {
        el.removeAttribute("aria-current");
      }
    });

    if (hskMenu) {
      hskMenu.open = hskOpen;
      hskMenu.classList.toggle("is-active-section", hskOpen);
      var toggle = hskMenu.querySelector(".sidebar-dropdown__toggle");
      if (toggle) toggle.classList.toggle("is-active", hskOpen);
    }
  }

  function showPanel(view) {
    VIEWS.forEach(function (v) {
      var panel = viewPanelId(v);
      var el = document.getElementById(panel);
      if (!el) return;
      var show = viewPanelId(view) === panel;
      el.classList.toggle("hidden", !show);
    });
  }

  function isHashOnlyNav() {
    try {
      var p = window.location.protocol || "";
      return p === "file:" || p === "content:" || p.indexOf("content") === 0;
    } catch (e) {
      return true;
    }
  }

  function updateUrlHash(view, replace) {
    var want = "#" + view;
    if (location.hash === want) return;
    try {
      if (isHashOnlyNav()) {
        location.hash = view;
        return;
      }
      if (replace) {
        history.replaceState({ view: view }, "", want);
      } else {
        history.pushState({ view: view }, "", want);
      }
    } catch (e) {
      try {
        location.hash = view;
      } catch (e2) {}
    }
  }

  function go(view, replace) {
    view = normalizeView(view);
    if (VIEWS.indexOf(view) < 0 && !HSK_NAV[view]) view = "dashboard";

    showPanel(view);
    setToolbar(view);
    markNavActive(view);

    if (HSK_NAV[view] && window.ChineseVocabApp) {
      window.ChineseVocabApp.switchTo(view);
    } else if (view === "words" && window.ChineseVocabApp) {
      window.ChineseVocabApp.switchTo("words");
    }
    if (
      view === "pronounce" &&
      window.ChinesePronunciation &&
      typeof window.ChinesePronunciation.refreshFromStoredNav === "function"
    ) {
      window.ChinesePronunciation.refreshFromStoredNav();
    }
    if (window.VocabularyUI && typeof window.VocabularyUI.onView === "function") {
      window.VocabularyUI.onView(view);
    }

    updateUrlHash(view, replace);

    window.scrollTo(0, 0);
  }

  window.AppRouter = {
    go: go,
    init: function () {
      var fromHash = normalizeView((location.hash || "").replace(/^#/, ""));
      if (fromHash && VIEWS.indexOf(fromHash) >= 0) {
        go(fromHash, true);
      } else {
        go("dashboard", true);
      }

      document.querySelectorAll("[data-app-view]").forEach(function (el) {
        el.addEventListener("click", function (e) {
          var v = el.getAttribute("data-app-view");
          if (!v) return;
          go(v, false);
          if (window.__closeSidebarDrawer) window.__closeSidebarDrawer();
          if (!isHashOnlyNav()) e.preventDefault();
        });
      });

      window.addEventListener("hashchange", function () {
        var v = normalizeView((location.hash || "").replace(/^#/, ""));
        go(v, true);
      });

      window.addEventListener("popstate", function () {
        var v = normalizeView((location.hash || "").replace(/^#/, ""));
        go(v || "dashboard", true);
      });
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      window.AppRouter.init();
    });
  } else {
    window.AppRouter.init();
  }
})();
