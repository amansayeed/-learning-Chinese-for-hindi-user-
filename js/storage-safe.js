(function () {
  "use strict";

  if (window.__CHINESE_STORAGE_PATCHED__) return;
  window.__CHINESE_STORAGE_PATCHED__ = true;

  function makeStore(bucket) {
    return {
      getItem: function (k) {
        return Object.prototype.hasOwnProperty.call(bucket, k) ? bucket[k] : null;
      },
      setItem: function (k, v) {
        bucket[k] = String(v);
      },
      removeItem: function (k) {
        delete bucket[k];
      },
      clear: function () {
        for (var key in bucket) {
          if (Object.prototype.hasOwnProperty.call(bucket, key)) delete bucket[key];
        }
      },
      key: function (i) {
        var ks = Object.keys(bucket);
        return ks[i] != null ? ks[i] : null;
      },
      get length() {
        return Object.keys(bucket).length;
      },
    };
  }

  function patch(name, nativeStore, bucket) {
    if (!nativeStore || typeof nativeStore.setItem !== "function") {
      window[name] = makeStore(bucket);
      return false;
    }
    try {
      var probe = "__chinese_storage_probe__";
      nativeStore.setItem(probe, "1");
      nativeStore.removeItem(probe);
      return true;
    } catch (e) {
      window[name] = makeStore(bucket);
      return false;
    }
  }

  var localBucket = {};
  var sessionBucket = {};
  var localOk = patch("localStorage", window.localStorage, localBucket);
  var sessionOk = patch("sessionStorage", window.sessionStorage, sessionBucket);

  window.__CHINESE_STORAGE_MEMORY__ = !localOk || !sessionOk;
})();
