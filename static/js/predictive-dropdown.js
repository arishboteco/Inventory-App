(function () {
  function normalizeLabel(txt) {
    if (!txt) return txt;
    // Handle tuple-like strings: ("Admin", "Admin") → Admin (second element)
    const tuple = txt.match(
      /^\s*\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]\s*\)\s*$/,
    );
    if (tuple) return tuple[2];
    // Collapse duplicate labels joined by comma: "X,X" → "X"
    const parts = txt.split(",");
    if (parts.length === 2 && parts[0].trim() === parts[1].trim()) {
      return parts[0].trim();
    }
    return txt;
  }

  function collapseWhitespace(s) {
    return String(s || "")
      .trim()
      .replace(/\s+/g, " ");
  }

  /**
   * Match typed text to an option value (for syncing hidden select with visible label).
   * Tries exact (case-insensitive), collapsed-whitespace exact, single includes-match,
   * then unique prefix match.
   */
  function resolveOptionValueFromTyped(typed, options) {
    const raw = String(typed || "").trim();
    if (!raw || !options.length) return "";
    const q = raw.toLowerCase();
    const qCollapsed = collapseWhitespace(raw).toLowerCase();

    let exact = options.find((o) => o.text.toLowerCase() === q);
    if (exact) return exact.value;

    exact = options.find(
      (o) => collapseWhitespace(o.text).toLowerCase() === qCollapsed,
    );
    if (exact) return exact.value;

    const includes = options.filter((o) =>
      o.text.toLowerCase().includes(q),
    );
    if (includes.length === 1) return includes[0].value;

    const prefixes = options.filter((o) =>
      o.text.toLowerCase().startsWith(q),
    );
    if (prefixes.length === 1) return prefixes[0].value;

    return "";
  }

  function applyResolvedValue(originalSelect, textInput, options, newVal) {
    const prev = originalSelect.value;
    originalSelect.value = newVal;
    const match = options.find((o) => o.value === originalSelect.value);
    if (match) {
      textInput.value = match.text;
    } else if (!newVal) {
      textInput.value = "";
    }
    if (originalSelect.value !== prev) {
      originalSelect.dispatchEvent(new Event("input", { bubbles: true }));
      originalSelect.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  function upgradeSelect(originalSelect) {
    // Only enhance selects explicitly marked as predictive
    if (!originalSelect.classList.contains("predictive")) return;
    // Skip multi-selects; those are handled by predictive-multiselect.js
    if (originalSelect.multiple) return;
    if (originalSelect.dataset.predictiveUpgraded === "1") return;
    originalSelect.dataset.predictiveUpgraded = "1";

    // Build container and visible text input
    const container = document.createElement("div");
    container.className = "predictive-dropdown-container relative";
    container.style.overflow = "visible";

    const textInput = document.createElement("input");
    textInput.type = "text";
    textInput.className = originalSelect.className
      .replace(/\bpredictive\b/, "")
      .replace(/\bpr-\d+\b/g, "")
      .trim();

    // Options snapshot (normalize the display text)
    const rawOptions = Array.from(originalSelect.options).map((opt) => ({
      text: normalizeLabel(opt.text),
      value: opt.value,
      selected: opt.selected,
      disabled: opt.disabled,
      ingredientKind:
        opt.dataset.ingredientKind ||
        opt.getAttribute("data-ingredient-kind") ||
        "",
    }));

    const emptyOption = rawOptions.find((o) => !o.value && !o.disabled);
    const options = rawOptions.filter((o) => o.value && !o.disabled);

    // Placeholder
    const attrPlaceholder =
      originalSelect.getAttribute("placeholder") ||
      originalSelect.getAttribute("data-placeholder");
    const resolvedPlaceholder =
      attrPlaceholder ||
      (emptyOption && emptyOption.text) ||
      "Type to search...";
    textInput.placeholder = resolvedPlaceholder;

    // If original has an id, mirror it for the visible control
    if (originalSelect.id) textInput.id = originalSelect.id + "_text";

    // Dropdown list (portal)
    const dropdown = document.createElement("div");
    dropdown.className =
      "predictive-dropdown-list fixed z-[60] bg-surface border border-border rounded-md shadow-lg max-h-60 overflow-y-auto hidden";
    dropdown.style.minWidth = container.offsetWidth + "px";

    // Initialize visible value from the original select
    const selected = rawOptions.find((o) => o.selected && o.value);
    if (selected) textInput.value = selected.text;

    // Render dropdown options
    function renderOptions(list) {
      dropdown.innerHTML = "";
      list.forEach((opt) => {
        const el = document.createElement("div");
        el.className =
          "predictive-dropdown-option flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-surfaceSubtle border-b border-border last:border-b-0 text-bodyText";
        if (opt.ingredientKind === "sub") {
          el.classList.add("predictive-dropdown-option--sub");
          const badge = document.createElement("span");
          badge.className = "predictive-dropdown-option-badge shrink-0";
          badge.textContent = "Sub";
          el.appendChild(badge);
        }
        const label = document.createElement("span");
        label.className = "min-w-0 truncate";
        label.textContent = opt.text;
        el.appendChild(label);
        el.addEventListener("click", () => {
          dropdown.classList.add("hidden");
          textInput.blur();
          applyResolvedValue(originalSelect, textInput, options, opt.value);
        });
        dropdown.appendChild(el);
      });
      // Position dropdown under input
      const rect = textInput.getBoundingClientRect();
      dropdown.style.left = rect.left + "px";
      dropdown.style.top = rect.bottom + "px";
      dropdown.style.width = rect.width + "px";
    }

    // Input typing behavior
    textInput.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      const filtered = options.filter((o) => o.text.toLowerCase().includes(q));
      renderOptions(filtered);
      dropdown.classList.remove("hidden");

      const newVal = resolveOptionValueFromTyped(e.target.value, filtered);
      const prev = originalSelect.value;
      originalSelect.value = newVal;
      if (originalSelect.value !== prev) {
        originalSelect.dispatchEvent(new Event("input", { bubbles: true }));
        originalSelect.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });

    // Keyboard navigation
    textInput.addEventListener("keydown", (e) => {
      const rows = dropdown.querySelectorAll(".predictive-dropdown-option");
      let idx = Array.from(rows).findIndex((n) =>
        n.classList.contains("bg-blue-100"),
      );
      if (e.key === "ArrowDown") {
        e.preventDefault();
        rows[idx]?.classList.remove("bg-blue-100");
        idx = Math.min(idx + 1, rows.length - 1);
        rows[idx]?.classList.add("bg-blue-100");
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        rows[idx]?.classList.remove("bg-blue-100");
        idx = Math.max(idx - 1, 0);
        rows[idx]?.classList.add("bg-blue-100");
      } else if (e.key === "Enter") {
        e.preventDefault();
        rows[idx]?.click();
      } else if (e.key === "Escape") {
        dropdown.classList.add("hidden");
        textInput.blur();
      }
    });

    textInput.addEventListener("focus", () => {
      renderOptions(options);
      dropdown.classList.remove("hidden");
      document.body.appendChild(dropdown);
      // Reposition on scroll/resize
      function updateDropdownPosition() {
        const rect = textInput.getBoundingClientRect();
        dropdown.style.left = rect.left + "px";
        dropdown.style.top = rect.bottom + "px";
        dropdown.style.width = rect.width + "px";
      }
      window.addEventListener("scroll", updateDropdownPosition, true);
      window.addEventListener("resize", updateDropdownPosition);
      updateDropdownPosition();
      // Close on outside click
      function handleOutside(e) {
        if (!dropdown.contains(e.target) && e.target !== textInput) {
          dropdown.classList.add("hidden");
          textInput.blur();
        }
      }
      document.addEventListener("mousedown", handleOutside);
      dropdown._cleanup = () => {
        window.removeEventListener("scroll", updateDropdownPosition, true);
        window.removeEventListener("resize", updateDropdownPosition);
        document.removeEventListener("mousedown", handleOutside);
        if (dropdown.parentNode === document.body)
          document.body.removeChild(dropdown);
      };
    });

    textInput.addEventListener("blur", () => {
      setTimeout(() => {
        dropdown.classList.add("hidden");
        if (dropdown._cleanup) dropdown._cleanup();
        const newVal = resolveOptionValueFromTyped(textInput.value, options);
        applyResolvedValue(originalSelect, textInput, options, newVal);
      }, 150);
    });

    // Move original select into the container and hide it visually (but keep it alive for HTMX)
    const parent = originalSelect.parentNode;
    parent.insertBefore(container, originalSelect);
    container.appendChild(textInput);
    container.appendChild(dropdown);
    container.appendChild(originalSelect);

    // Visually hide original select while keeping it in DOM for events/HTMX
    originalSelect.style.display = "none";
    originalSelect.style.position = "absolute";
    originalSelect.style.width = "1px";
    originalSelect.style.height = "1px";
    originalSelect.style.padding = "0";
    originalSelect.style.margin = "-1px";
    originalSelect.style.overflow = "hidden";
    originalSelect.style.clip = "rect(0, 0, 0, 0)";
    originalSelect.style.whiteSpace = "nowrap";
    originalSelect.style.border = "0";
    originalSelect.tabIndex = -1; // keep out of tab order

    originalSelect.addEventListener("input", () => {
      const match = options.find((o) => o.value === originalSelect.value);
      textInput.value = match ? match.text : "";
    });
  }

  window.initPredictiveDropdowns = function (root) {
    const scope = root || document;
    scope.querySelectorAll("select.predictive").forEach((sel) => {
      // Skip hidden template rows like the empty form row used for cloning
      const row = sel.closest("tr");
      if (row && (row.id === "items-empty-row" || /empty-row$/.test(row.id)))
        return;
      upgradeSelect(sel);
    });
  };

  document.addEventListener("DOMContentLoaded", function () {
    window.initPredictiveDropdowns();
    // No extra padding; dropdowns are absolute with high z-index and should overlay table headers
  });

  document.body.addEventListener("htmx:afterSwap", (e) => {
    window.initPredictiveDropdowns(e.target);
  });
})();
