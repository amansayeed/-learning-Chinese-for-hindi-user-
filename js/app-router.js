(function () {
  "use strict";

  /* Legacy lesson tables keep their own dataset and saved lesson position. */
  var HSK_NAV = {
    lessons1: "hsk1",
    lessons2: "hsk2",
    lessons3: "hsk3",
    lessons4: "hsk4",
    lessons5: "hsk5",
    lessons6: "hsk6",
  };

  /* Each HSK band is its own page built from the canonical vocabulary. */
  var LEVEL_VIEWS = {
    hsk1: "1",
    hsk2: "2",
    hsk3: "3",
    hsk4: "4",
    hsk5: "5",
    hsk6: "6",
    "hsk-other": "outside-hsk",
  };

  var VIEWS = [
    "home",
    "browse",
    "learn",
    "favorites",
    "progress",
    "tocfl",
    "characters",
    "words",
    "pronounce",
    "tones",
  ]
    .concat(Object.keys(LEVEL_VIEWS))
    .concat(Object.keys(HSK_NAV));

  function normalizeView(id) {
    if (!id || id === "dashboard") return "home";
    if (id === "hsk" || id === "categories") return "browse";
    if (id === "outside-hsk") return "hsk-other";
    return id;
  }

  function viewPanelId(view) {
    if (view === "home") return "app-view-dashboard";
    if (view === "browse") return "app-view-browse";
    if (LEVEL_VIEWS[view]) return "app-view-level";
    if (view === "learn") return "app-view-learn";
    if (view === "favorites") return "app-view-favorites";
    if (view === "progress") return "app-view-progress";
    if (view === "tocfl") return "app-view-tocfl";
    if (view === "characters") return "app-view-characters";
    if (view === "words" || HSK_NAV[view]) return "app-view-words";
    if (view === "pronounce") return "app-view-pronounce";
    if (view === "tones") return "app-view-tones";
    return "app-view-words";
  }

  function setToolbar(view) {
    var wordsTb = document.getElementById("toolbar-words");
    var isVocab = view === "words" || !!HSK_NAV[view];
    if (wordsTb) wordsTb.classList.toggle("hidden", !isVocab);
  }

  function updateMobileTitle(view) {
    var title = document.getElementById("mobile-view-title");
    var hint = document.getElementById("mobile-view-hint");
    var labels = {
      home: ["Home", "Today's lesson and progress"],
      learn: ["Learn", "Listen · I Know · Forgot"],
      browse: ["Browse", "Search all Chinese vocabulary"],
      favorites: ["Favorites", "Your saved vocabulary"],
      progress: ["Progress", "HSK completion and XP"],
      tocfl: ["TOCFL 8,000", "Seven official levels grouped by category"],
      characters: ["Chinese Characters", "Learn 1,000–3,000 characters by frequency"],
      words: ["All words", "Table and study modes"],
      pronounce: ["Pronunciation", "Hear and practise each word"],
      tones: ["Four tones", "Mandarin tone practice"],
    };
    var value = labels[view];
    if (LEVEL_VIEWS[view]) value = [view === "hsk-other" ? "Outside HSK" : "HSK " + LEVEL_VIEWS[view], "Words grouped by useful topic"];
    if (HSK_NAV[view]) value = ["HSK lesson table", "Browse words by lesson"];
    value = value || ["臺灣華語", "Chinese learning"];
    if (title) title.textContent = value[0];
    if (hint) hint.textContent = value[1];
  }

  function markNavActive(view) {
    var hskMenu = document.getElementById("sidebar-hsk-menu");
    var hskOpen = !!LEVEL_VIEWS[view];

    document.querySelectorAll("[data-app-view]").forEach(function (el) {
      var v = el.getAttribute("data-app-view");
      var activeView = view;
      if (view === "words" || view === "tones" || HSK_NAV[view]) activeView = "browse";
      if (view === "favorites" && el.closest(".bottom-nav")) activeView = "browse";
      /* Level pages stay highlighted themselves, and also light up Browse in the bottom bar. */
      if (LEVEL_VIEWS[view] && el.closest(".bottom-nav")) activeView = "browse";
      var on = v === activeView;
      el.classList.toggle("is-active", on);
      if (on) {
        el.setAttribute("aria-current", "page");
        var parentMenu = el.closest(".sidebar-dropdown");
        if (parentMenu) parentMenu.open = true;
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

  function isSandboxed() {
    if (window.ChineseOffline && typeof window.ChineseOffline.isSandboxed === "function") {
      return window.ChineseOffline.isSandboxed();
    }
    var p = "";
    try {
      p = window.location.protocol || "";
    } catch (e) {
      return true;
    }
    return !p || (p !== "http:" && p !== "https:" && p !== "file:");
  }

  function updateUrlHash(view, replace) {
    /* A content:// document loses its one-file access grant as soon as the URL
       changes, so there the address bar is left exactly as Chrome opened it. */
    if (isSandboxed()) return;
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
    if (VIEWS.indexOf(view) < 0 && !HSK_NAV[view]) view = "home";

    showPanel(view);
    setToolbar(view);
    markNavActive(view);
    updateMobileTitle(view);

    if (HSK_NAV[view] && window.ChineseVocabApp) {
      window.ChineseVocabApp.switchTo(HSK_NAV[view]);
    } else if (view === "words" && window.ChineseVocabApp) {
      window.ChineseVocabApp.switchTo("words");
    }
    if (window.TocflUI && (view === "tocfl" || view === "pronounce")) {
      window.TocflUI.refresh(view === "pronounce" ? "pronunciation" : "browser");
    }
    if (view === "characters" && window.CharactersUI) {
      window.CharactersUI.refresh();
    }
    if (window.VocabularyUI && typeof window.VocabularyUI.onView === "function") {
      window.VocabularyUI.onView(view);
    }

    updateUrlHash(view, replace);

    window.scrollTo(0, 0);
  }

  window.AppRouter = {
    go: go,
    levelForView: function (view) {
      return LEVEL_VIEWS[view] || null;
    },
    viewForLevel: function (level) {
      return level === "outside-hsk" ? "hsk-other" : "hsk" + level;
    },
    init: function () {
      var fromHash = normalizeView((location.hash || "").replace(/^#/, ""));
      if (fromHash && VIEWS.indexOf(fromHash) >= 0) {
        go(fromHash, true);
      } else {
        go("home", true);
      }

      document.querySelectorAll("[data-app-view]").forEach(function (el) {
        el.addEventListener("click", function (e) {
          var v = el.getAttribute("data-app-view");
          if (!v) return;
          /* Blocked first: a content:// document loses its access grant on any
             navigation, so the browser must not act even if routing throws. */
          if (isSandboxed() || !isHashOnlyNav()) e.preventDefault();
          if (window.__closeSidebarDrawer) window.__closeSidebarDrawer();
          go(v, false);
        });
      });

      window.addEventListener("hashchange", function () {
        var v = normalizeView((location.hash || "").replace(/^#/, ""));
        go(v, true);
      });

      window.addEventListener("popstate", function () {
        var v = normalizeView((location.hash || "").replace(/^#/, ""));
        go(v || "home", true);
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
