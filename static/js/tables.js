(function () {
  function getKey(container) {
    return (
      container.getAttribute("data-table-key") ||
      container.querySelector("table[id]")?.id ||
      "default"
    );
  }

  function applyHidden(container, key) {
    let hidden = [];
    try {
      hidden = JSON.parse(localStorage.getItem("tableHidden:" + key) || "[]");
    } catch (_) {}
    if (hidden.length) {
      hidden.forEach((col) => {
        container
          .querySelectorAll(`[data-col='${CSS.escape(col)}']`)
          .forEach((el) => el.classList.add("hidden"));
        container
          .querySelectorAll(`[data-col-toggle][value='${CSS.escape(col)}']`)
          .forEach((cb) => (cb.checked = false));
      });
    }
  }

  function applyDensity(container, key) {
    try {
      const val = localStorage.getItem("tableDensity:" + key);
      if (val === "compact" || val === "comfortable") {
        container.setAttribute("data-density", val);
      }
    } catch (_) {}
  }

  function bindToggles(container, key) {
    container.querySelectorAll("[data-col-toggle]").forEach((ctl) => {
      if (ctl._boundToggle) return;
      ctl._boundToggle = true;
      ctl.addEventListener("change", () => {
        const col = ctl.value;
        const on = ctl.checked;
        container
          .querySelectorAll(`[data-col='${CSS.escape(col)}']`)
          .forEach((el) =>
            on ? el.classList.remove("hidden") : el.classList.add("hidden"),
          );
        let hidden = [];
        try {
          hidden = JSON.parse(
            localStorage.getItem("tableHidden:" + key) || "[]",
          );
        } catch (_) {}
        const idx = hidden.indexOf(col);
        if (!on && idx === -1) hidden.push(col);
        if (on && idx !== -1) hidden.splice(idx, 1);
        localStorage.setItem("tableHidden:" + key, JSON.stringify(hidden));
      });
    });
  }

  function updateAnnouncer(container) {
    const announcer = container.querySelector("[data-table-announcer]");
    if (!announcer) return;
    const tbody = container.querySelector("tbody");
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll("tr"));
    const count = rows.length;
    announcer.textContent = `List updated. ${count} rows displayed.`;
  }

  function bindStickyShadow(container) {
    if (container._shadowBound) return;
    container._shadowBound = true;
    const scroller = container.closest(".table-scroll") || container;
    const onScroll = () => {
      const top = scroller.scrollTop || 0;
      if (top > 0) container.dataset.shadow = "true";
      else delete container.dataset.shadow;
    };
    scroller.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  function bindOptimisticSort(container) {
    if (container.getAttribute("data-optimistic-sort") !== "true") return;
    if (container._optSortBound) return;
    container._optSortBound = true;
    container.addEventListener("click", (e) => {
      const a = e.target.closest("[data-sort-link]");
      if (!a || !container.contains(a)) return;
      const table = container.querySelector("table");
      const tbody = table && table.querySelector("tbody");
      if (!tbody) return;
      // Determine column index
      const th = a.closest("th");
      const ths = Array.from(a.closest("tr").children);
      const colIdx = th ? ths.indexOf(th) : -1;
      if (colIdx < 0) return;
      // Determine direction from href if present
      let dir = "asc";
      try {
        const url = new URL(a.getAttribute("href"), window.location.origin);
        dir = (url.searchParams.get("direction") || "asc").toLowerCase();
      } catch (_) {}
      // Collect and sort rows
      const rows = Array.from(tbody.querySelectorAll("tr"));
      const getVal = (row) => {
        const cell = row.children[colIdx];
        if (!cell) return "";
        const numEl = cell.querySelector(".tabular-nums");
        const txt = (numEl || cell).textContent.trim();
        const n = Number(txt.replace(/[^0-9.+-]/g, ""));
        if (!Number.isNaN(n) && txt.match(/[0-9]/)) return n;
        return txt.toLowerCase();
      };
      const sorted = rows.slice().sort((r1, r2) => {
        const v1 = getVal(r1);
        const v2 = getVal(r2);
        let cmp = 0;
        if (typeof v1 === "number" && typeof v2 === "number") cmp = v1 - v2;
        else cmp = String(v1).localeCompare(String(v2));
        return dir === "desc" ? -cmp : cmp;
      });
      // Visual feedback while waiting for server
      table.classList.add("opacity-60");
      sorted.forEach((r) => tbody.appendChild(r));
      // Remove feedback after swap or timeout
      const clear = () => table.classList.remove("opacity-60");
      const once = (evt) => {
        container.removeEventListener("htmx:afterSwap", once);
        clear();
      };
      container.addEventListener("htmx:afterSwap", once, { once: true });
      setTimeout(clear, 1500);
    });
  }

  function initBulk(container) {
    const topBar = container.querySelector("#bulk-actions-top");
    if (!topBar || topBar._bulkBound) return;
    topBar._bulkBound = true;
    const topLabel = container.querySelector("#bulk-count-top");
    const checkboxes = () =>
      Array.from(container.querySelectorAll("[data-bulk-checkbox]"));
    const update = () => {
      const count = checkboxes().filter((c) => c.checked).length;
      if (topLabel) topLabel.textContent = `${count} selected`;
      if (count > 0) topBar.classList.remove("hidden");
      else topBar.classList.add("hidden");
    };
    container.addEventListener("change", (e) => {
      const el = e.target;
      if (!(el instanceof Element)) return;
      if (el.matches("[data-bulk-select-all]")) {
        const checked = el.checked;
        checkboxes().forEach((cb) => (cb.checked = checked));
        update();
      } else if (el.matches("[data-bulk-checkbox]")) {
        update();
      }
    });
    update();
  }

  function bindDensityControls(container, key) {
    if (container._densityBound) return;
    container._densityBound = true;
    const sync = () => {
      const val = container.getAttribute("data-density") || "";
      container.querySelectorAll("[data-density-btn]").forEach((b) => {
        const v =
          b.getAttribute("data-value") || b.getAttribute("data-density");
        const on = v === val;
        b.setAttribute("aria-pressed", on ? "true" : "false");
        b.classList.toggle("bg-primary", on);
        b.classList.toggle("text-white", on);
      });
    };
    container.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-density-btn]");
      if (!btn || !container.contains(btn)) return;
      const val =
        btn.getAttribute("data-value") ||
        btn.getAttribute("data-density") ||
        "";
      if (val === "compact" || val === "comfortable") {
        container.setAttribute("data-density", val);
        try {
          localStorage.setItem("tableDensity:" + key, val);
        } catch (_) {}
        sync();
      }
    });
    // Initial sync
    sync();
  }

  function initTable(root) {
    const containers = (root || document).querySelectorAll(
      "[data-table-container]",
    );
    containers.forEach((container) => {
      const key = getKey(container);
      applyHidden(container, key);
      applyDensity(container, key);
      bindToggles(container, key);
      bindStickyShadow(container);
      bindOptimisticSort(container);
      updateAnnouncer(container);
      initBulk(container);
      bindDensityControls(container, key);
    });
  }

  document.addEventListener("DOMContentLoaded", () => initTable(document));
  document.body.addEventListener("htmx:afterSwap", (e) => initTable(e.target));
})();
