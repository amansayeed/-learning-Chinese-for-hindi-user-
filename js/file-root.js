/* Same logic is inlined at the top of each .html <head> (must run before css/js links). */
(function () {
  "use strict";

  var loc = window.location;
  var protocol = loc.protocol;

  if (protocol !== "file:" && protocol !== "content:") {
    window.__OFFLINE_FILE__ = false;
    return;
  }

  window.__OFFLINE_FILE__ = true;

  var href = loc.href.split("#")[0].split("?")[0];
  var root = "./";

  if (protocol === "file:") {
    var slash = Math.max(href.lastIndexOf("/"), href.lastIndexOf("\\"));
    if (slash >= 0) {
      root = href.slice(0, slash + 1);
    }
  }

  window.__SITE_ROOT__ = root;

  if (!document.querySelector("base[data-chinese-root]")) {
    var base = document.createElement("base");
    base.setAttribute("data-chinese-root", "1");
    base.href = root;
    var head = document.head || document.getElementsByTagName("head")[0];
    if (head.firstChild) {
      head.insertBefore(base, head.firstChild);
    } else {
      head.appendChild(base);
    }
  }
})();
