(function () {
  function enhanceMultiSelect(sel) {
    if (!(sel instanceof HTMLSelectElement)) return;
    if (!sel.multiple) return;
    if (!sel.classList.contains("predictive")) return;
    if (sel.dataset.predMultiUpgraded === "1") return;
    sel.dataset.predMultiUpgraded = "1";

    const container = document.createElement("div");
    container.className = "predictive-multiselect relative";
    container.style.position = "relative";

    const chipBar = document.createElement("div");
    chipBar.className = "flex flex-wrap gap-1 mb-1";

    const trigger = document.createElement("input");
    trigger.type = "text";
    trigger.readOnly = false; // allow typing for filtering
    // Clone classes but remove predictive token
    trigger.className = (sel.className || "")
      .replace(/\bpredictive\b/, "")
      .trim();
    const placeholder =
      sel.getAttribute("data-placeholder") ||
      sel.getAttribute("placeholder") ||
      "Filter options...";
    trigger.placeholder = placeholder;

    const dropdown = document.createElement("div");
    dropdown.className =
      "absolute z-[60] mt-1 bg-surface border border-border rounded-md shadow-lg max-h-60 overflow-y-auto w-full hidden";

    // Build option list snapshot
    let options = Array.from(sel.options).map((o) => ({
      value: o.value,
      label: o.text,
      disabled: o.disabled,
      selected: o.selected,
    }));

    function dispatchChange() {
      sel.dispatchEvent(new Event("input", { bubbles: true }));
      sel.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function appliedText() {
      const selected = options.filter((o) => o.selected && o.value);
      if (selected.length === 0) {
        return "";
      }
      if (selected.length <= 2) {
        return selected.map((o) => o.label).join(", ");
      }
      return selected.length + " selected";
    }

    function renderChips() {
      chipBar.innerHTML = "";
      const selected = options.filter((o) => o.selected && o.value);
      selected.forEach((o) => {
        const pill = document.createElement("span");
        pill.className =
          "inline-flex items-center gap-1 bg-info-soft text-info-text border border-border rounded-full px-2 py-0.5 text-xs";
        const lab = document.createElement("span");
        lab.textContent = o.label;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "ml-1 text-bodyText hover:text-danger";
        btn.setAttribute("aria-label", `Remove ${o.label}`);
        btn.textContent = "×";
        btn.addEventListener("click", () => {
          o.selected = false;
          const opt = Array.from(sel.options).find(
            (so) => so.value === o.value,
          );
          if (opt) opt.selected = false;
          renderChips();
          trigger.value = "";
          trigger.setAttribute("aria-label", "Filter options");
          dispatchChange();
          if (!dropdown.classList.contains("hidden"))
            rebuildList(trigger.value);
        });
        pill.appendChild(lab);
        pill.appendChild(btn);
        chipBar.appendChild(pill);
      });
    }

    function syncTrigger() {
      const summary = appliedText();
      // Prefer chips for visual state; keep input empty for typing
      trigger.value = "";
      trigger.setAttribute(
        "aria-label",
        summary ? `Selected: ${summary}` : "Filter options",
      );
      renderChips();
    }

    function rebuildList(filter) {
      dropdown.innerHTML = "";
      const q = (filter || "").toLowerCase();
      // Toolbar for bulk actions
      const toolbar = document.createElement("div");
      toolbar.className =
        "sticky top-0 bg-surface p-2 border-b border-border flex items-center gap-2";
      const btnSelectAll = document.createElement("button");
      btnSelectAll.type = "button";
      btnSelectAll.className =
        "text-xs px-2 py-1 rounded border border-border text-bodyText hover:bg-surfaceSubtle";
      btnSelectAll.textContent = "Select all";
      const btnClearAll = document.createElement("button");
      btnClearAll.type = "button";
      btnClearAll.className =
        "text-xs px-2 py-1 rounded border border-border text-bodyText hover:bg-surfaceSubtle";
      btnClearAll.textContent = "Clear";
      toolbar.appendChild(btnSelectAll);
      toolbar.appendChild(btnClearAll);

      const list = document.createElement("div");
      list.role = "listbox";
      const visible = options.filter(
        (o) =>
          o.value &&
          !o.disabled &&
          (q ? String(o.label).toLowerCase().includes(q) : true),
      );
      visible.forEach((o) => {
        const row = document.createElement("label");
        row.className =
          "flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-surfaceSubtle border-b border-border text-bodyText last:border-b-0";
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.checked = !!o.selected;
        cb.addEventListener("change", () => {
          // update original select option
          const opt = Array.from(sel.options).find(
            (so) => so.value === o.value,
          );
          if (opt) {
            opt.selected = cb.checked;
          }
          o.selected = cb.checked;
          syncTrigger();
          dispatchChange();
        });
        const span = document.createElement("span");
        span.textContent = o.label;
        row.appendChild(cb);
        row.appendChild(span);
        list.appendChild(row);
      });
      // Wire toolbar actions
      btnSelectAll.addEventListener("click", () => {
        visible.forEach((o) => {
          if (!o.selected) {
            o.selected = true;
            const opt = Array.from(sel.options).find(
              (so) => so.value === o.value,
            );
            if (opt) {
              opt.selected = true;
            }
          }
        });
        syncTrigger();
        dispatchChange();
        rebuildList(trigger.value);
      });
      btnClearAll.addEventListener("click", () => {
        options.forEach((o) => {
          o.selected = false;
        });
        Array.from(sel.options).forEach((so) => {
          if (so.value) so.selected = false;
        });
        // ensure the empty placeholder remains the only unselected/default
        syncTrigger();
        dispatchChange();
        rebuildList(trigger.value);
      });

      dropdown.appendChild(toolbar);
      dropdown.appendChild(list);
    }

    function refreshOptions() {
      options = Array.from(sel.options).map((o) => ({
        value: o.value,
        label: o.text,
        disabled: o.disabled,
        selected: o.selected,
      }));
      syncTrigger();
      // If dropdown is visible, re-render with current filter
      if (!dropdown.classList.contains("hidden")) {
        rebuildList(trigger.value);
      }
    }

    // Events
    trigger.addEventListener("focus", () => {
      rebuildList(trigger.value);
      dropdown.classList.remove("hidden");
    });
    trigger.addEventListener("input", () => {
      rebuildList(trigger.value);
      dropdown.classList.remove("hidden");
    });

    // Backspace to remove last selection when query empty
    trigger.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        dropdown.classList.add("hidden");
        return;
      }
      if (e.key === "Backspace" && (trigger.value || "").length === 0) {
        const selected = options.filter((o) => o.selected && o.value);
        const last = selected[selected.length - 1];
        if (last) {
          last.selected = false;
          const opt = Array.from(sel.options).find(
            (so) => so.value === last.value,
          );
          if (opt) opt.selected = false;
          syncTrigger();
          dispatchChange();
          rebuildList("");
          e.preventDefault();
        }
      }
    });

    function outside(e) {
      if (!container.contains(e.target)) {
        dropdown.classList.add("hidden");
      }
    }
    document.addEventListener("mousedown", outside);

    // Observe option list changes on original select and refresh snapshot
    const mo = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === "childList") {
          refreshOptions();
          break;
        }
      }
    });
    mo.observe(sel, { childList: true });

    sel.addEventListener("predMulti:refresh", refreshOptions);

    // Insert elements
    const parent = sel.parentNode;
    parent.insertBefore(container, sel);
    container.appendChild(chipBar);
    container.appendChild(trigger);
    container.appendChild(dropdown);

    // hide original select visually
    sel.style.display = "none";
    sel.tabIndex = -1;

    // Accessibility: link input to original label if present
    const selId = sel.getAttribute("id");
    if (selId) {
      const label = document.querySelector(`label[for='${selId}']`);
      if (label) {
        let lid = label.getAttribute("id");
        if (!lid) {
          lid = selId + "-label";
          label.setAttribute("id", lid);
        }
        trigger.setAttribute("aria-labelledby", lid);
      }
    }

    // initialize
    syncTrigger();
  }

  function init(root) {
    const scope = root || document;
    scope
      .querySelectorAll("select.predictive[multiple]")
      .forEach(enhanceMultiSelect);
  }

  window.initPredictiveMultiSelects = init;
  document.addEventListener("DOMContentLoaded", () => init());
  document.body.addEventListener("htmx:afterSwap", (e) => init(e.target));
})();
