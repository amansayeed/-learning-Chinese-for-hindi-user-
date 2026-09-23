(function () {
  "use strict";

  /* Retired lesson-table and all-words routes still live in old bookmarks and
     in links saved to a phone home screen, so they resolve to the page that
     replaced them instead of dropping the reader on the dashboard. */
  var RETIRED_VIEWS = {
    words: "browse",
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
    "categories",
    "learn",
    "favorites",
    "progress",
    "tocfl",
    "tocfl8000",
    "characters",
    "script-diff",
    "pronounce",
    "tones",
  ].concat(Object.keys(LEVEL_VIEWS));

  function normalizeView(id) {
    if (!id || id === "dashboard") return "home";
    if (id === "hsk") return "browse";
    if (id === "outside-hsk") return "hsk-other";
    if (RETIRED_VIEWS[id]) return RETIRED_VIEWS[id];
    return id;
  }

  function parseRoute(value) {
    var raw = String(value || "").replace(/^#/, "");
    var match = raw.match(/^categories\/([a-z0-9-]+)$/);
    if (match) return { view: "categories", slug: match[1], path: raw };
    var view = normalizeView(raw);
    return { view: view, slug: "", path: view };
  }

  function viewPanelId(view) {
    if (view === "home") return "app-view-dashboard";
    if (view === "browse") return "app-view-browse";
    if (view === "categories") return "app-view-categories";
    if (LEVEL_VIEWS[view]) return "app-view-level";
    if (view === "learn") return "app-view-learn";
    if (view === "favorites") return "app-view-favorites";
    if (view === "progress") return "app-view-progress";
    if (view === "tocfl") return "app-view-tocfl";
    if (view === "tocfl8000") return "app-view-tocfl8000";
    if (view === "characters") return "app-view-characters";
    if (view === "script-diff") return "app-view-script-diff";
    if (view === "pronounce") return "app-view-pronounce";
    if (view === "tones") return "app-view-tones";
    return "app-view-dashboard";
  }

  function updateMobileTitle(view) {
    var title = document.getElementById("mobile-view-title");
    var hint = document.getElementById("mobile-view-hint");
    var labels = {
      home: ["Home", "Today's lesson and progress"],
      learn: ["Learn", "Listen · I Know · Forgot"],
      browse: ["Browse", "Search all Chinese vocabulary"],
      categories: ["Categories", "Official TOCFL and CCCC vocabulary"],
      favorites: ["Favorites", "Your saved vocabulary"],
      progress: ["Progress", "HSK completion and XP"],
      tocfl: ["TOCFL + CCCC", "Seven official levels grouped by category"],
      tocfl8000: ["Official TOCFL vocabulary", "TOCFL 8000 · arranged by pinyin"],
      characters: ["Chinese Characters", "Learn 1,000–3,000 characters by frequency"],
      "script-diff": ["Traditional and Simplified difference", "Characters from the 3,000 list that differ"],
      pronounce: ["Pronunciation", "Hear and practise each word"],
      tones: ["Four tones", "Mandarin tone practice"],
    };
    var value = labels[view];
    if (LEVEL_VIEWS[view]) value = [view === "hsk-other" ? "Outside HSK" : "HSK " + LEVEL_VIEWS[view], "Words grouped by useful topic"];
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
      if (view === "tones") activeView = "browse";
      if (view === "favorites" && el.closest(".bottom-nav")) activeView = "browse";
      if (view === "categories" && el.closest(".bottom-nav")) activeView = "browse";
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
    var route = parseRoute(view);
    view = route.view;
    if (VIEWS.indexOf(view) < 0) view = "home";

    showPanel(view);
    markNavActive(view);
    updateMobileTitle(view);

    if (window.TocflUI && (view === "tocfl" || view === "tocfl8000" || view === "pronounce")) {
      window.TocflUI.refresh(view === "pronounce" ? "pronunciation" : view === "tocfl8000" ? "tocfl8000" : "browser");
    }
    if ((view === "characters" || view === "script-diff") && window.CharactersUI) {
      window.CharactersUI.refresh();
    }
    if (view === "categories" && window.CategoriesUI) {
      if (route.slug) window.CategoriesUI.open(route.slug, { fromRouter: true });
      else window.CategoriesUI.close({ fromRouter: true });
    }
    if (window.VocabularyUI && typeof window.VocabularyUI.onView === "function") {
      window.VocabularyUI.onView(view);
    }

    updateUrlHash(view === "categories" && route.slug ? route.path : view, replace);

    window.scrollTo(0, 0);
  }

  window.AppRouter = {
    go: go,
    goCategory: function (slug, replace) {
      go("categories/" + String(slug || ""), replace);
    },
    levelForView: function (view) {
      return LEVEL_VIEWS[view] || null;
    },
    viewForLevel: function (level) {
      return level === "outside-hsk" ? "hsk-other" : "hsk" + level;
    },
    init: function () {
      var fromHash = parseRoute(location.hash || "");
      if (fromHash.view && VIEWS.indexOf(fromHash.view) >= 0) {
        go(fromHash.path, true);
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
        var route = parseRoute(location.hash || "");
        go(route.path, true);
      });

      window.addEventListener("popstate", function () {
        var route = parseRoute(location.hash || "");
        go(route.path || "home", true);
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
