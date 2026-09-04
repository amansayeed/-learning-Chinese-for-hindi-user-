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
