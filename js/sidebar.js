(function () {
  "use strict";

  var shell = document.querySelector(".page-shell");
  var openBtn = document.getElementById("sidebar-open");
  var backdrop = document.getElementById("sidebar-backdrop");

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
    var file = currentPageFile();
    var hskMenu = document.getElementById("sidebar-hsk-menu");
    var hskOpen = false;

    document.querySelectorAll(".sidebar-nav .sidebar-link").forEach(function (link) {
      var target = normalizeHref(link.getAttribute("href"));
      if (target !== file) return;
      link.classList.add("is-active");
      link.setAttribute("aria-current", "page");
      if (link.classList.contains("sidebar-link--sub")) {
        hskOpen = true;
      }
    });

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

  function setOpen(open) {
    if (open) {
      shell.classList.add("nav-open");
      openBtn.setAttribute("aria-expanded", "true");
      if (backdrop) {
        backdrop.removeAttribute("hidden");
        backdrop.setAttribute("aria-hidden", "false");
      }
    } else {
      shell.classList.remove("nav-open");
      openBtn.setAttribute("aria-expanded", "false");
      if (backdrop) {
        backdrop.setAttribute("hidden", "");
        backdrop.setAttribute("aria-hidden", "true");
      }
    }
  }

  function toggle() {
    setOpen(!shell.classList.contains("nav-open"));
  }

  openBtn.addEventListener("click", toggle);

  if (backdrop) {
    backdrop.addEventListener("click", function () {
      setOpen(false);
    });
  }

  document.querySelectorAll(".sidebar-nav a").forEach(function (link) {
    link.addEventListener("click", function () {
      setOpen(false);
    });
  });

  ["dataset-select", "view-mode", "level-select", "lesson-select"].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("change", function () {
      setOpen(false);
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && shell.classList.contains("nav-open")) {
      setOpen(false);
      openBtn.focus();
    }
  });

  var resizeTimer;
  window.addEventListener("resize", function () {
    if (!shell.classList.contains("nav-open")) return;
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      setOpen(false);
    }, 120);
  });

  initSidebarNav();
})();
