(function () {
  "use strict";

  var store = window.TocflStore;
  var taxonomyPayload = window.__CATEGORY_TAXONOMY__ || { categories: [] };
  var taxonomy = taxonomyPayload.categories || [];
  var PAGE_SIZE = 50;
  var controllers = [];

  if (!store || !taxonomy.length) return;

  function text(value) {
    return value == null ? "" : String(value);
  }

  function escapeHtml(value) {
    return text(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function one(root, role) {
    return root.querySelector('[data-categories-role="' + role + '"]');
  }

  function categoryBySlug(slug) {
    for (var index = 0; index < taxonomy.length; index += 1) {
      if (taxonomy[index].slug === slug) return taxonomy[index];
    }
    return null;
  }

  function sandboxed() {
    return !!(
      window.ChineseOffline &&
      typeof window.ChineseOffline.isSandboxed === "function" &&
      window.ChineseOffline.isSandboxed()
    );
  }

  function setStandaloneHash(slug) {
    if (window.__UNIFIED_APP__ || sandboxed()) return;
    var value = slug ? "#categories/" + slug : "#categories";
    try {
      if (window.location.hash !== value) window.location.hash = value;
    } catch (error) {}
  }

  function Controller(root) {
    this.root = root;
    this.selected = null;
    this.page = 1;
    this.bind();
    var initial = root.getAttribute("data-category-slug") || "";
    if (!initial && !window.__UNIFIED_APP__) {
      initial = text(window.location.hash).replace(/^#(?:categories|category)\/?/, "");
    }
    if (initial) this.selected = categoryBySlug(initial);
    this.render();
  }

  Controller.prototype.filtered = function () {
    if (!this.selected) return [];
    var search = one(this.root, "search");
    var source = one(this.root, "source");
    var level = one(this.root, "level");
    var sourceValue = source ? source.value : "all";
    var words = store.filter({
      category: this.selected.label,
      query: search ? search.value : "",
      source: sourceValue === "both" ? "all" : sourceValue,
      level: level ? level.value : "all",
    });
    if (sourceValue === "both") {
      words = words.filter(function (word) {
        return (word.sources || []).indexOf("TOCFL") >= 0 &&
          (word.sources || []).indexOf("CCCC") >= 0;
      });
    }
    return store.priorityOrder(words);
  };

  Controller.prototype.renderLanding = function () {
    var grid = one(this.root, "grid");
    if (!grid) return;
    var counts = store.categoryCounts();
    grid.innerHTML = taxonomy.map(function (category) {
      var count = counts[category.label] || 0;
      return (
        '<button type="button" class="category-card categories-card" data-category-slug="' +
        escapeHtml(category.slug) +
        '" aria-label="Open ' +
        escapeHtml(category.label) +
        ', ' +
        count +
        ' words"><span class="category-card__icon" aria-hidden="true">' +
        escapeHtml(category.icon) +
        '</span><span class="category-card__title">' +
        escapeHtml(category.label) +
        "</span><strong>" +
        count +
        " word" +
        (count === 1 ? "" : "s") +
        "</strong></button>"
      );
    }).join("");
  };

  Controller.prototype.renderLevelOptions = function () {
    var select = one(this.root, "level");
    if (!select || select.getAttribute("data-populated") === "true") return;
    select.innerHTML =
      '<option value="all">All official levels</option>' +
      store.levels().map(function (level) {
        return (
          '<option value="' +
          escapeHtml(level.id) +
          '">' +
          escapeHtml(level.label) +
          " · " +
          escapeHtml(level.source) +
          "</option>"
        );
      }).join("");
    select.setAttribute("data-populated", "true");
  };

  Controller.prototype.renderResults = function () {
    if (!this.selected) return;
    var words = this.filtered();
    var pages = Math.max(1, Math.ceil(words.length / PAGE_SIZE));
    this.page = Math.min(Math.max(1, this.page), pages);
    var start = (this.page - 1) * PAGE_SIZE;
    var visible = words.slice(start, start + PAGE_SIZE);
    var count = one(this.root, "count");
    var results = one(this.root, "results");
    var pager = one(this.root, "pagination");

    if (count) {
      count.textContent =
        words.length +
        " unique word" +
        (words.length === 1 ? "" : "s") +
        " · sorted by official learning priority";
    }
    if (results) {
      results.innerHTML = words.length
        ? window.VocabularyUI && window.VocabularyUI.renderWordList
          ? window.VocabularyUI.renderWordList(visible, start, { showMetadata: true })
          : ""
        : '<div class="empty-state"><strong>No matching words</strong><p>Clear a filter or try another search.</p></div>';
    }
    if (!pager) return;
    pager.classList.toggle("hidden", words.length <= PAGE_SIZE);
    pager.innerHTML =
      '<button type="button" class="btn-page" data-category-page="first"' +
      (this.page <= 1 ? " disabled" : "") +
      ">First</button>" +
      '<button type="button" class="btn-page" data-category-page="prev"' +
      (this.page <= 1 ? " disabled" : "") +
      ">Prev</button>" +
      '<span class="words-page-info">Page ' +
      this.page +
      " of " +
      pages +
      "</span>" +
      '<button type="button" class="btn-page" data-category-page="next"' +
      (this.page >= pages ? " disabled" : "") +
      ">Next</button>" +
      '<button type="button" class="btn-page" data-category-page="last"' +
      (this.page >= pages ? " disabled" : "") +
      ">Last</button>";
  };

  Controller.prototype.render = function () {
    var landing = one(this.root, "landing");
    var detail = one(this.root, "detail");
    var title = one(this.root, "title");
    var subtitle = one(this.root, "subtitle");
    if (landing) landing.classList.toggle("hidden", !!this.selected);
    if (detail) detail.classList.toggle("hidden", !this.selected);

    if (!this.selected) {
      if (title) title.textContent = "Categories";
      if (subtitle) {
        subtitle.textContent =
          store.all().length +
          " unique TOCFL and CCCC words · choose one of " +
          taxonomy.length +
          " learning categories";
      }
      this.renderLanding();
      return;
    }

    if (title) title.textContent = this.selected.label;
    if (subtitle) {
      subtitle.textContent =
        "Official TOCFL and CCCC vocabulary only · duplicate source rows are merged";
    }
    var detailTitle = one(this.root, "detail-title");
    var detailIcon = one(this.root, "detail-icon");
    if (detailTitle) detailTitle.textContent = this.selected.label;
    if (detailIcon) detailIcon.textContent = this.selected.icon;
    this.renderLevelOptions();
    this.renderResults();
  };

  Controller.prototype.open = function (slug, options) {
    var category = categoryBySlug(slug);
    if (!category) return false;
    this.selected = category;
    this.page = 1;
    var search = one(this.root, "search");
    var source = one(this.root, "source");
    var level = one(this.root, "level");
    if (!options || !options.preserveFilters) {
      if (search) search.value = "";
      if (source) source.value = "all";
      if (level) level.value = "all";
    }
    this.render();
    if (!options || !options.fromRouter) setStandaloneHash(category.slug);
    return true;
  };

  Controller.prototype.close = function (options) {
    this.selected = null;
    this.page = 1;
    this.render();
    if (!options || !options.fromRouter) setStandaloneHash("");
  };

  Controller.prototype.bind = function () {
    var self = this;
    this.root.addEventListener("click", function (event) {
      var category = event.target.closest("[data-category-slug]");
      if (category) {
        var slug = category.getAttribute("data-category-slug");
        if (window.__UNIFIED_APP__ && window.AppRouter && window.AppRouter.goCategory) {
          window.AppRouter.goCategory(slug);
        } else {
          self.open(slug);
        }
        return;
      }
      var back = event.target.closest("[data-category-back]");
      if (back) {
        if (window.__UNIFIED_APP__ && window.AppRouter) window.AppRouter.go("categories");
        else self.close();
        return;
      }
      var pageButton = event.target.closest("[data-category-page]");
      if (!pageButton || pageButton.disabled) return;
      var action = pageButton.getAttribute("data-category-page");
      var pages = Math.max(1, Math.ceil(self.filtered().length / PAGE_SIZE));
      if (action === "first") self.page = 1;
      if (action === "prev") self.page = Math.max(1, self.page - 1);
      if (action === "next") self.page = Math.min(pages, self.page + 1);
      if (action === "last") self.page = pages;
      self.renderResults();
    });
    ["search", "source", "level"].forEach(function (role) {
      var control = one(self.root, role);
      if (!control) return;
      control.addEventListener(role === "search" ? "input" : "change", function () {
        self.page = 1;
        self.renderResults();
      });
    });
  };

  function init() {
    document.querySelectorAll("[data-categories-browser]").forEach(function (root) {
      controllers.push(new Controller(root));
    });
  }

  window.CategoriesUI = {
    taxonomy: taxonomy.slice(),
    count: store.all().length,
    mount: function (root) {
      var controller = new Controller(root);
      controllers.push(controller);
      return controller;
    },
    open: function (slug, options) {
      var opened = false;
      controllers.forEach(function (controller) {
        if (controller.open(slug, options)) opened = true;
      });
      return opened;
    },
    close: function (options) {
      controllers.forEach(function (controller) { controller.close(options); });
    },
    refresh: function () {
      controllers.forEach(function (controller) { controller.render(); });
    },
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
