#!/usr/bin/env python3
"""Click every kind of internal link in a simulated content:// document.

An Android file manager shares one file with the browser. Chrome re-requests that
URI on any navigation and the grant is already spent, so a link that reaches the
browser ends on ERR_FILE_NOT_FOUND. These checks fail the build if a link type can
still escape the page.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import dukpy

ROOT = Path(__file__).resolve().parents[1]

DOM_SHIM = """
function makeClassList() {
  var set = {};
  return {
    add: function (c) { set[c] = true; },
    remove: function (c) { delete set[c]; },
    contains: function (c) { return !!set[c]; },
    toggle: function (c, on) {
      if (on === undefined) on = !set[c];
      if (on) set[c] = true; else delete set[c];
      return !!on;
    }
  };
}

function matches(el, selector) {
  if (!el || !el.tagName) return false;
  if (selector === "a[href]") return el.tagName === "a" && el.getAttribute("href") !== null;
  if (selector.charAt(0) === ".") return el.classList.contains(selector.slice(1));
  return el.tagName === selector;
}

function makeEl(tag) {
  var el = {
    tagName: tag, id: "", innerHTML: "", textContent: "", style: {}, hidden: false,
    attributes: {}, childNodes: [], parentNode: null, listeners: {},
    scrolledIntoView: false, focused: false
  };
  el.classList = makeClassList();
  el.setAttribute = function (k, v) { el.attributes[k] = String(v); if (k === "id") el.id = String(v); };
  el.getAttribute = function (k) { return k in el.attributes ? el.attributes[k] : null; };
  el.removeAttribute = function (k) { delete el.attributes[k]; };
  el.hasAttribute = function (k) { return k in el.attributes; };
  el.addEventListener = function (type, handler) {
    if (!el.listeners[type]) el.listeners[type] = [];
    el.listeners[type].push(handler);
  };
  el.appendChild = function (child) {
    child.parentNode = el;
    el.childNodes.push(child);
    el.firstChild = el.childNodes[0];
    track(child);
    return child;
  };
  el.insertBefore = function (child) {
    child.parentNode = el;
    el.childNodes.unshift(child);
    el.firstChild = el.childNodes[0];
    track(child);
    return child;
  };
  el.removeChild = function (child) {
    for (var i = 0; i < el.childNodes.length; i += 1) {
      if (el.childNodes[i] === child) { el.childNodes.splice(i, 1); break; }
    }
    el.firstChild = el.childNodes[0] || null;
    if (child.id && byId[child.id] === child) delete byId[child.id];
    return child;
  };
  el.querySelector = function () { return null; };
  el.querySelectorAll = function () { return []; };
  el.closest = function (selector) {
    var node = el;
    while (node) {
      if (matches(node, selector)) return node;
      node = node.parentNode;
    }
    return null;
  };
  el.scrollIntoView = function () { el.scrolledIntoView = true; };
  el.focus = function () { el.focused = true; };
  el.firstChild = null;
  return el;
}

var anchors = [];
var byId = {};

/* Nodes the page builds at runtime have to be findable by id, like in a browser. */
function track(node) {
  if (node && node.id) byId[node.id] = node;
}

function anchor(href, text, view) {
  var el = makeEl("a");
  el.setAttribute("href", href);
  el.textContent = text;
  if (view) el.setAttribute("data-app-view", view);
  anchors.push(el);
  return el;
}

function element(id) {
  if (!byId[id]) {
    var el = makeEl("div");
    el.setAttribute("id", id);
    byId[id] = el;
  }
  return byId[id];
}

var main = makeEl("div");
main.classList.add("layout-main");

var document = {
  readyState: "complete",
  documentElement: makeEl("html"),
  head: makeEl("head"),
  body: makeEl("body"),
  listeners: {},
  getElementById: function (id) { return byId[id] || null; },
  querySelector: function (selector) {
    if (selector === ".layout-main") return main;
    return null;
  },
  querySelectorAll: function (selector) {
    if (selector === "a[href]") return anchors.slice();
    if (selector === "[data-app-view]") {
      return anchors.filter(function (el) { return el.getAttribute("data-app-view"); });
    }
    return [];
  },
  addEventListener: function (type, handler) {
    if (!document.listeners[type]) document.listeners[type] = [];
    document.listeners[type].push(handler);
  },
  createElement: function (tag) { return makeEl(tag); }
};

/* Capture listeners on document run first, then listeners bound to the link. */
function click(link) {
  var event = {
    target: link,
    defaultPrevented: false,
    preventDefault: function () { event.defaultPrevented = true; }
  };
  (document.listeners.click || []).forEach(function (handler) { handler(event); });
  (link.listeners.click || []).forEach(function (handler) { handler(event); });
  return event;
}

var storage = {};
var localStorage = {
  getItem: function (k) { return k in storage ? storage[k] : null; },
  setItem: function (k, v) { storage[k] = String(v); },
  removeItem: function (k) { delete storage[k]; }
};
var window = this;
window.window = window;
window.document = document;
window.localStorage = localStorage;
window.sessionStorage = localStorage;
window.history = {
  pushed: 0, replaced: 0,
  pushState: function () { window.history.pushed += 1; },
  replaceState: function () { window.history.replaced += 1; }
};
window.scrollTo = function () {};
window.addEventListener = function () {};
window.setTimeout = function (fn) { if (typeof fn === "function") fn(); return 0; };
window.clearTimeout = function () {};
"""


def module(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def scenario(setup: str, probe: str, modules: list[str]) -> dict:
    source = [DOM_SHIM, setup, *[module(name) for name in modules], probe]
    try:
        return json.loads(dukpy.evaljs("\n;\n".join(source)))
    except dukpy.JSRuntimeError as error:  # pragma: no cover - surfaced as a failure
        return {"crash": str(error)}


STANDALONE_SETUP = """
window.location = {
  protocol: "content:",
  hash: "",
  href: "content://com.android.providers.media.documents/document/1234"
};
window.__MOBILE_PACK__ = true;
window.__UNIFIED_APP__ = false;
var skipTarget = element("page-top");
var sidebarLink = anchor("./tocfl.html", "TOCFL + CCCC");
var bottomLink = anchor("./chinese.html#home", "Home");
var inPageLink = anchor("#page-top", "Back to top");
var outsideLink = anchor("https://example.com/docs", "Open docs");
"""

STANDALONE_PROBE = """
var report = {};
report.markedUnavailable = sidebarLink.classList.contains("is-unavailable") &&
  bottomLink.classList.contains("is-unavailable");
report.inPageLinkLeftEnabled = !inPageLink.classList.contains("is-unavailable");
report.outsideLinkLeftEnabled = !outsideLink.classList.contains("is-unavailable");
report.loadBanner = !!document.getElementById("sandboxed-nav-notice");

report.siblingPageBlocked = click(sidebarLink).defaultPrevented;
var notice = document.getElementById("sandboxed-nav-notice");
report.siblingPageExplained = !!notice && notice.innerHTML.indexOf("TOCFL + CCCC") !== -1 &&
  notice.innerHTML.indexOf("index.html") !== -1;

report.crossPageFragmentBlocked = click(bottomLink).defaultPrevented;
report.fragmentBlocked = click(inPageLink).defaultPrevented;
report.fragmentScrolled = skipTarget.scrolledIntoView;
report.externalLinkAllowed = !click(outsideLink).defaultPrevented;
JSON.stringify(report);
"""

UNIFIED_SETUP = """
window.location = {
  protocol: "content:",
  hash: "",
  href: "content://com.google.android.apps.nbu.files.provider/1/file/42"
};
window.__MOBILE_PACK__ = true;
window.__UNIFIED_APP__ = true;
element("app-view-dashboard");
element("app-view-characters");
element("app-view-tocfl");
var skipLink = anchor("#app-content", "Skip to content");
element("app-content");
var charactersLink = anchor("#characters", "Chinese Characters", "characters");
var tocflLink = anchor("#tocfl", "TOCFL + CCCC", "tocfl");
"""

UNIFIED_PROBE = """
var report = {};
var charactersEvent = click(charactersLink);
report.routedLinkBlocked = charactersEvent.defaultPrevented;
report.routedLinkSwitchedView =
  !document.getElementById("app-view-characters").classList.contains("hidden") &&
  document.getElementById("app-view-dashboard").classList.contains("hidden");
report.hashLeftAlone = window.location.hash === "";
report.historyLeftAlone = window.history.pushed === 0 && window.history.replaced === 0;
report.skipLinkBlocked = click(skipLink).defaultPrevented;
report.skipLinkScrolled = document.getElementById("app-content").scrolledIntoView;
report.tocflLinkBlocked = click(tocflLink).defaultPrevented;
report.noDeadLinkBanner = !document.getElementById("sandboxed-nav-notice");
JSON.stringify(report);
"""

FILE_SETUP = """
window.location = { protocol: "file:", hash: "", href: "file:///D:/chinese/mobile/tocfl.html" };
window.__MOBILE_PACK__ = true;
window.__UNIFIED_APP__ = false;
var sidebarLink = anchor("./characters.html", "Chinese Characters");
"""

FILE_PROBE = """
var report = {};
report.linkStillNavigates = !click(sidebarLink).defaultPrevented;
report.notMarked = !sidebarLink.classList.contains("is-unavailable");
report.noBanner = !document.getElementById("sandboxed-nav-notice");
JSON.stringify(report);
"""


def main() -> None:
    standalone = scenario(STANDALONE_SETUP, STANDALONE_PROBE, ["js/offline.js", "js/sidebar.js"])
    unified = scenario(
        UNIFIED_SETUP, UNIFIED_PROBE, ["js/offline.js", "js/sidebar.js", "js/app-router.js"]
    )
    on_file = scenario(FILE_SETUP, FILE_PROBE, ["js/offline.js", "js/sidebar.js"])

    checks = [
        ("standalone page did not crash", "crash" not in standalone),
        ("unified app did not crash", "crash" not in unified),
        ("file:// page did not crash", "crash" not in on_file),
        ("sibling-page links are marked unavailable on load", standalone.get("markedUnavailable")),
        ("same-page links stay usable", standalone.get("inPageLinkLeftEnabled")),
        ("outside links stay usable", standalone.get("outsideLinkLeftEnabled")),
        ("single-file mode is explained before any tap", standalone.get("loadBanner")),
        ("tapping a sibling page never reaches the browser", standalone.get("siblingPageBlocked")),
        ("tapping a sibling page explains the way out", standalone.get("siblingPageExplained")),
        ("cross-page fragment links are blocked", standalone.get("crossPageFragmentBlocked")),
        ("same-page fragment links are blocked", standalone.get("fragmentBlocked")),
        ("same-page fragment links scroll in memory", standalone.get("fragmentScrolled")),
        ("external links keep working", standalone.get("externalLinkAllowed")),
        ("app navigation never reaches the browser", unified.get("routedLinkBlocked")),
        ("app navigation still switches view", unified.get("routedLinkSwitchedView")),
        ("app navigation leaves the address bar alone", unified.get("hashLeftAlone")),
        ("app navigation writes no history entry", unified.get("historyLeftAlone")),
        ("skip link is blocked", unified.get("skipLinkBlocked")),
        ("skip link scrolls in memory", unified.get("skipLinkScrolled")),
        ("second app link is blocked too", unified.get("tocflLinkBlocked")),
        ("all-in-one app shows no dead-link warning", unified.get("noDeadLinkBanner")),
        ("file:// navigation is untouched", on_file.get("linkStillNavigates")),
        ("file:// links are not marked unavailable", on_file.get("notMarked")),
        ("file:// pages show no warning", on_file.get("noBanner")),
    ]

    failures = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS  " if ok else "FAIL  ") + name)
    for report, title in ((standalone, "standalone"), (unified, "unified"), (on_file, "file")):
        if "crash" in report:
            print(f"\n{title} scenario crashed: {report['crash']}")

    if failures:
        print(f"\n{len(failures)} sandbox navigation check(s) failed.")
        sys.exit(1)
    print("\nAll sandbox navigation checks passed.")


if __name__ == "__main__":
    main()
