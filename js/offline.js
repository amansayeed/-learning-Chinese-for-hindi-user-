(function () {
  "use strict";

  function isOfflineFile() {
    return !!window.__OFFLINE_FILE__;
  }

  function isMobilePack() {
    return !!window.__MOBILE_PACK__;
  }

  function protocolLabel() {
    try {
      return window.location.protocol;
    } catch (e) {
      return "";
    }
  }

  /* An Android file manager hands Chrome a content:// URI that grants access to
     the opened file alone. Any navigation re-requests that URI, so even a bare
     fragment change dies with ERR_FILE_NOT_FOUND, and sibling pages were never
     reachable to begin with. Such a document has to route purely in memory. */
  function isSandboxedDocument() {
    var protocol = protocolLabel();
    if (!protocol) return true;
    return protocol !== "http:" && protocol !== "https:" && protocol !== "file:";
  }

  function offlineFetchHint(jsonPath, jsPath) {
    if (isMobilePack()) {
      return "Mobile pack failed to load embedded data. Re-copy the mobile/ folder from git or rebuild with: node scripts/build-mobile-pack.js";
    }
    return (
      "Offline mode (" +
      protocolLabel() +
      "): cannot load " +
      jsonPath +
      ". On your phone, open the mobile/ folder: use mobile/START.html (one file per page, no separate css/js). " +
      "Or copy the full project and ensure " +
      jsPath +
      " exists (run node scripts/build-offline-bundles.js on a PC)."
    );
  }

  function hasGlobal(name) {
    var g = window[name];
    return g && typeof g === "object" && (g.levels || g.quartets);
  }

  window.ChineseOffline = {
    isOfflineFile: isOfflineFile,
    isMobilePack: isMobilePack,
    isSandboxed: isSandboxedDocument,
    offlineFetchHint: offlineFetchHint,
    hasGlobal: hasGlobal,
    vocabPayload: function (key) {
      if (key === "nhm") {
        return hasGlobal("__VOCAB_NHM__") ? window.__VOCAB_NHM__ : null;
      }
      if (key === "hsk6") {
        return hasGlobal("__VOCAB_HSK6__") ? window.__VOCAB_HSK6__ : null;
      }
      if (key === "hsk5") {
        return hasGlobal("__VOCAB_HSK5__") ? window.__VOCAB_HSK5__ : null;
      }
      if (key === "hsk4") {
        return hasGlobal("__VOCAB_HSK4__") ? window.__VOCAB_HSK4__ : null;
      }
      if (key === "hsk3") {
        return hasGlobal("__VOCAB_HSK3__") ? window.__VOCAB_HSK3__ : null;
      }
      if (key === "hsk2") {
        return hasGlobal("__VOCAB_HSK2__") ? window.__VOCAB_HSK2__ : null;
      }
      if (key === "hsk1") {
        return hasGlobal("__VOCAB_HSK1__") ? window.__VOCAB_HSK1__ : null;
      }
      if (key === "tocfl") {
        return hasGlobal("__VOCAB__") ? window.__VOCAB__ : null;
      }
      return null;
    },
    tonePayload: function () {
      if (window.__TONE_PAGE_DATA__ && window.__TONE_PAGE_DATA__.quartets) {
        return window.__TONE_PAGE_DATA__;
      }
      if (window.__TONE_DATA__ && window.__TONE_DATA__.quartets) {
        return window.__TONE_DATA__;
      }
      return null;
    },
    toneLoadError: function () {
      return (
        "Could not load tone data offline. Keep the full folder (css/, js/, data/) and ensure " +
        "data/tone-page.data.js exists (run node scripts/build-offline-bundles.js on a PC, then copy data/ to your phone)."
      );
    },
    showSetupBanner: function (issues) {
      if (!issues || !issues.length) return;
      var main = document.querySelector(".layout-main");
      if (!main || document.getElementById("offline-setup-banner")) return;
      var el = document.createElement("div");
      el.id = "offline-setup-banner";
      el.className = "banner banner--error";
      el.setAttribute("role", "alert");
      el.innerHTML =
        "<strong>Files not loaded correctly.</strong><ul style=\"margin:0.5rem 0 0 1rem;padding:0\">" +
        issues
          .map(function (item) {
            return "<li>" + item + "</li>";
          })
          .join("") +
        "</ul><p style=\"margin:0.65rem 0 0;font-size:0.9rem\">" +
        (isMobilePack()
          ? window.__UNIFIED_APP__
            ? "Re-copy <code>chinese.html</code> from git or rebuild: node scripts/build-offline-app.js"
            : "Re-copy the <code>mobile/</code> folder from git or rebuild on a PC."
          : "On phone, copy <code>mobile/chinese.html</code> and open it in Chrome—not separate page links from Drive.") +
        "</p>";
      main.insertBefore(el, main.firstChild);
    },
  };
})();
