(function () {
  "use strict";

  var shell = document.querySelector(".page-shell");
  var openBtn = document.getElementById("sidebar-open");
  var backdrop = document.getElementById("sidebar-backdrop");

  if (!shell || !openBtn) return;

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
      if (window.matchMedia("(max-width: 768px)").matches) {
        setOpen(false);
      }
    });
  });

  ["dataset-select", "view-mode", "level-select", "lesson-select"].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("change", function () {
      if (window.matchMedia("(max-width: 768px)").matches) {
        setOpen(false);
      }
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && shell.classList.contains("nav-open")) {
      setOpen(false);
      openBtn.focus();
    }
  });

  window.addEventListener("resize", function () {
    if (window.matchMedia("(min-width: 769px)").matches) {
      setOpen(false);
    }
  });
})();
