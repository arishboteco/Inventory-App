/**
 * Theme preference: localStorage key inventory-theme — light | dark | system (default system).
 * Blocking script in <head> sets html.dark before paint; this module wires listeners and UI.
 */
(function () {
  var STORAGE_KEY = "inventory-theme";
  var VALID = ["light", "dark", "system"];

  function getStored() {
    try {
      var v = localStorage.getItem(STORAGE_KEY);
      if (v && VALID.indexOf(v) !== -1) return v;
    } catch (e) {
      /* ignore */
    }
    return "system";
  }

  function prefersDark() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function resolveEffective(stored) {
    if (stored === "dark") return true;
    if (stored === "light") return false;
    return prefersDark();
  }

  function applyClass(isDark) {
    var root = document.documentElement;
    if (isDark) root.classList.add("dark");
    else root.classList.remove("dark");
    root.style.colorScheme = isDark ? "dark" : "light";
  }

  function set(mode) {
    if (VALID.indexOf(mode) === -1) return;
    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch (e) {
      /* ignore */
    }
    var effective = resolveEffective(mode);
    applyClass(effective);
    window.dispatchEvent(
      new CustomEvent("themechange", {
        detail: { mode: mode, dark: effective },
      })
    );
  }

  function syncFromStorage() {
    applyClass(resolveEffective(getStored()));
  }

  window.inventoryTheme = {
    get: getStored,
    set: set,
    prefersDark: prefersDark,
    isDark: function () {
      return resolveEffective(getStored());
    },
    init: function () {
      syncFromStorage();
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      mq.addEventListener("change", function () {
        if (getStored() === "system") {
          applyClass(prefersDark());
          window.dispatchEvent(
            new CustomEvent("themechange", {
              detail: { mode: "system", dark: prefersDark() },
            })
          );
        }
      });
      window.addEventListener("storage", function (e) {
        if (e.key === STORAGE_KEY) syncFromStorage();
      });
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      window.inventoryTheme.init();
    });
  } else {
    window.inventoryTheme.init();
  }
})();
