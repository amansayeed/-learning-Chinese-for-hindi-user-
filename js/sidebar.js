(function () {
  "use strict";

  /* An Android file manager hands Chrome a content:// URI that grants access to
     the opened file alone. Re-requesting that URI fails, and Chrome re-requests it
     for every navigation — even a bare "#fragment" — so the page has to answer
     every internal link itself instead of letting the browser leave. */
  function sandboxed() {
    return !!(
      window.ChineseOffline &&
      typeof window.ChineseOffline.isSandboxed === "function" &&
      window.ChineseOffline.isSandboxed()
    );
  }

  if (!sandboxed()) return;

  var NOTICE_ID = "sandboxed-nav-notice";
  var ALL_IN_ONE = window.__MOBILE_PACK__ ? "index.html" : "chinese.html";

  /* http(s), mailto and tel leave the document on purpose and still work. */
  function kind(href) {
    if (!href) return "dead";
    if (href.charAt(0) === "#") return "fragment";
    if (/^[a-z][a-z0-9+.-]*:/i.test(href)) return "external";
    return "file";
  }

  function label(link) {
    return (link.textContent || "").replace(/\s+/g, " ").trim();
  }

  function banner(className, role, html) {
    var host = document.querySelector(".layout-main") || document.body;
    if (!host) return;
    var previous = document.getElementById(NOTICE_ID);
    if (previous && previous.parentNode) previous.parentNode.removeChild(previous);

    var notice = document.createElement("div");
    notice.id = NOTICE_ID;
    notice.className = className;
    notice.setAttribute("role", role);
    notice.innerHTML = html;
    host.insertBefore(notice, host.firstChild);
    return notice;
  }

  function sharedFileHelp() {
    return (
      " Your file manager shared this single file with the browser, so it cannot " +
      "reach the other pages stored beside it. Open <code>" +
      ALL_IN_ONE +
      "</code> instead — every page lives inside that one file — or open the folder " +
      "from device storage so the address starts with <code>file://</code>."
    );
  }

  function explain(name) {
    var notice = banner(
      "banner banner--error",
      "alert",
      "<strong>" +
        (name ? "“" + name + "” cannot open from here." : "That page cannot open from here.") +
        "</strong>" +
        sharedFileHelp()
    );
    if (notice && typeof notice.scrollIntoView === "function") {
      notice.scrollIntoView({ block: "nearest" });
    }
  }

  /* Fragments are resolved in memory: scrolling to the target is the whole job a
     browser would do, minus the navigation that would kill the access grant. */
  function jumpTo(href) {
    var id = href.slice(1);
    if (!id) return;
    var target = null;
    try {
      target = document.getElementById(id);
    } catch (e) {
      target = null;
    }
    if (!target) return;
    if (typeof target.scrollIntoView === "function") target.scrollIntoView({ block: "start" });
    if (typeof target.focus === "function") {
      if (!target.hasAttribute || !target.hasAttribute("tabindex")) {
        if (target.setAttribute) target.setAttribute("tabindex", "-1");
      }
      target.focus();
    }
  }

  document.addEventListener(
    "click",
    function (event) {
      var target = event.target;
      var link = target && target.closest ? target.closest("a[href]") : null;
      if (!link) return;
      var href = link.getAttribute("href") || "";
      var type = kind(href);
      if (type === "external") return;

      /* Nothing below may reach the browser: every remaining href would re-request
         the content:// URI and land on ERR_FILE_NOT_FOUND. Listeners bound to the
         link itself still run, so in-app routing keeps working. */
      event.preventDefault();

      if (type === "fragment") {
        jumpTo(href);
        return;
      }
      if (window.__closeSidebarDrawer) window.__closeSidebarDrawer();
      explain(label(link));
    },
    true
  );

  /* Say it before the tap, not after: links to sibling files are marked as
     unavailable as soon as the page loads. */
  function markUnavailable() {
    var links = document.querySelectorAll("a[href]");
    var dead = 0;
    Array.prototype.forEach.call(links, function (link) {
      if (kind(link.getAttribute("href")) !== "file") return;
      dead += 1;
      link.classList.add("is-unavailable");
      link.setAttribute("data-sandboxed-unavailable", "");
      link.setAttribute("aria-disabled", "true");
      link.setAttribute("title", "Not available — this file was shared on its own");
    });
    if (!dead) return;
    banner(
      "banner banner--warning",
      "status",
      "<strong>Single-file mode.</strong>" + sharedFileHelp()
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", markUnavailable);
  } else {
    markUnavailable();
  }
})();

(function () {
  "use strict";

  var shell = document.querySelector(".page-shell");
  var openBtn = document.getElementById("sidebar-open");
  var backdrop = document.getElementById("sidebar-backdrop");
  var lastFocused = null;
  var focusTimer = null;

  function currentPageFile() {
    var href = window.location.href.split("#")[0].split("?")[0];
    var slash = Math.max(href.lastIndexOf("/"), href.lastIndexOf("\\"));
    var file = slash >= 0 ? href.slice(slash + 1) : href;
    return file || "index.html";
  }

  function normalizeHref(href) {
    return String(href || "")
      .replace(/^\.\//, "")
      .split("#")[0]
      .split("?")[0];
  }

  function initSidebarNav() {
    if (window.__UNIFIED_APP__) return;

    var file = currentPageFile();
    var hskMenu = document.getElementById("sidebar-hsk-menu");
    var hskOpen = false;
    var bottomActive = false;

    document.querySelectorAll(".sidebar-nav .sidebar-link, .bottom-nav a").forEach(function (link) {
      var target = normalizeHref(link.getAttribute("href"));
      if (target !== file) return;
      link.classList.add("is-active");
      link.setAttribute("aria-current", "page");
      if (link.closest(".bottom-nav")) bottomActive = true;
      if (link.classList.contains("sidebar-link--sub")) {
        hskOpen = true;
      }
    });

    if (!bottomActive) {
      var browseFallback = document.querySelector('.bottom-nav a[href*="#browse"]');
      if (browseFallback) {
        browseFallback.classList.add("is-active");
        browseFallback.setAttribute("aria-current", "page");
      }
    }

    if (hskMenu && hskOpen) {
      hskMenu.open = true;
      hskMenu.classList.add("is-active-section");
      var toggle = hskMenu.querySelector(".sidebar-dropdown__toggle");
      if (toggle) toggle.classList.add("is-active");
    }
  }

  if (!shell || !openBtn) {
    initSidebarNav();
    return;
  }

  function setOpen(open, restoreFocus) {
    if (open) {
      lastFocused = document.activeElement;
      shell.classList.add("nav-open");
      openBtn.setAttribute("aria-expanded", "true");
      var sidebar = document.getElementById("sidebar");
      if (sidebar) sidebar.setAttribute("aria-hidden", "false");
      if (backdrop) {
        backdrop.removeAttribute("hidden");
        backdrop.setAttribute("aria-hidden", "false");
      }
      focusTimer = window.setTimeout(function () {
        var first = document.querySelector(
          "#sidebar .sidebar-link, #sidebar summary, #sidebar select, #sidebar input, #sidebar button"
        );
        if (first) first.focus();
      }, 230);
    } else {
      if (focusTimer) {
        window.clearTimeout(focusTimer);
        focusTimer = null;
      }
      shell.classList.remove("nav-open");
      openBtn.setAttribute("aria-expanded", "false");
      var closedSidebar = document.getElementById("sidebar");
      if (closedSidebar && window.innerWidth < 1024) {
        closedSidebar.setAttribute("aria-hidden", "true");
      }
      if (backdrop) {
        backdrop.setAttribute("hidden", "");
        backdrop.setAttribute("aria-hidden", "true");
      }
      if (restoreFocus && lastFocused && typeof lastFocused.focus === "function") {
        lastFocused.focus();
      }
    }
  }

  window.__closeSidebarDrawer = function () {
    setOpen(false);
  };

  function toggle() {
    setOpen(!shell.classList.contains("nav-open"), true);
  }

  openBtn.addEventListener("click", toggle);

  if (backdrop) {
    backdrop.addEventListener("click", function () {
      setOpen(false, true);
    });
  }

  document.querySelectorAll(".sidebar-nav a").forEach(function (link) {
    link.addEventListener("click", function () {
      if (window.__UNIFIED_APP__ && link.hasAttribute("data-app-view")) return;
      setOpen(false);
    });
  });

  ["dataset-select", "view-mode", "level-select", "lesson-select", "pronounce-dataset-select", "pronounce-level-select", "pronounce-lesson-select"].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("change", function () {
      setOpen(false);
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && shell.classList.contains("nav-open")) {
      setOpen(false, true);
      return;
    }
    if (e.key === "Tab" && shell.classList.contains("nav-open")) {
      var sidebar = document.getElementById("sidebar");
      if (!sidebar) return;
      var focusable = Array.prototype.slice.call(
        sidebar.querySelectorAll("a[href], summary, select, input, button:not([disabled])")
      ).filter(function (element) {
        return element.offsetParent !== null;
      });
      if (!focusable.length) return;
      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  });

  var resizeTimer;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      if (shell.classList.contains("nav-open")) setOpen(false);
      var sidebar = document.getElementById("sidebar");
      if (sidebar) sidebar.setAttribute("aria-hidden", window.innerWidth < 1024 ? "true" : "false");
    }, 120);
  });

  initSidebarNav();
  var sidebar = document.getElementById("sidebar");
  if (sidebar) sidebar.setAttribute("aria-hidden", window.innerWidth < 1024 ? "true" : "false");
})();

/* The theme button lives in the sidebar (and a floating control on smaller
   screens). It used to be wired by the retired table page, so clicks did nothing. */
(function () {
  "use strict";

  var THEME_KEY = "chinese-vocab-theme";

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function paintTheme() {
    var dark = currentTheme() === "dark";
    var toggle = document.getElementById("theme-toggle");
    if (toggle) {
      toggle.textContent = dark ? "Light mode" : "Dark mode";
      toggle.setAttribute("aria-pressed", dark ? "true" : "false");
      toggle.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    }
    var floating = document.getElementById("theme-float-toggle");
    if (floating) {
      floating.textContent = dark ? "☀️" : "🌙";
      floating.setAttribute("aria-pressed", dark ? "true" : "false");
      floating.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    }
  }

  function setTheme(mode) {
    if (mode !== "light" && mode !== "dark") return;
    document.documentElement.setAttribute("data-theme", mode);
    try {
      localStorage.setItem(THEME_KEY, mode);
    } catch (e) {}
    paintTheme();
  }

  function ensureFloatingToggle() {
    if (document.getElementById("theme-float-toggle") || !document.body) return;
    var button = document.createElement("button");
    button.type = "button";
    button.id = "theme-float-toggle";
    button.className = "theme-float-toggle";
    document.body.appendChild(button);
  }

  function bindTheme() {
    ensureFloatingToggle();
    paintTheme();
    document.addEventListener("click", function (event) {
      var hit = event.target && event.target.closest
        ? event.target.closest("#theme-toggle, #theme-float-toggle")
        : null;
      if (!hit) return;
      setTheme(currentTheme() === "dark" ? "light" : "dark");
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bindTheme);
  else bindTheme();
})();
