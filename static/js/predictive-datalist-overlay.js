(function () {
  function buildOverlay(input) {
    const overlayPref = (
      input.getAttribute("data-overlay") || ""
    ).toLowerCase();
    if (
      overlayPref === "native" ||
      input.hasAttribute("data-overlay-disabled")
    ) {
      return null;
    }
    const listId = input.getAttribute("list");
    const datalist = listId && document.getElementById(listId);
    if (!datalist) return null;

    if (input._overlay) return input._overlay;

    const overlay = document.createElement("div");
    overlay.className =
      "predictive-overlay fixed left-0 right-0 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto hidden z-[70]";
    overlay.setAttribute("role", "listbox");

    function position() {
      const rect = input.getBoundingClientRect();
      overlay.style.position = "fixed";
      overlay.style.minWidth = rect.width + "px";
      overlay.style.width = rect.width + "px";
      overlay.style.top = rect.bottom + "px";
      overlay.style.left = rect.left + "px";
    }

    let activeIndex = -1;
    async function render(filter) {
      const q = (filter || "").toLowerCase();
      // If this input has an hx-get for suggestions, proactively refresh the datalist
      // Some environments don't reliably send the event to HTMX when typing inside
      // overlays; refreshing here guarantees options are current.
      try {
        const suggestUrl =
          input.getAttribute("hx-get") ||
          input.getAttribute("data-suggest-url");
        if (suggestUrl) {
          const lastQ = datalist.getAttribute("data-last-q") || "";
          if (q !== lastQ) {
            datalist.setAttribute("data-last-q", q);
            const url = new URL(suggestUrl, window.location.origin);
            if (q) url.searchParams.set("q", q);
            // Also include the field's name form for servers expecting *-item
            if (input.name && q) url.searchParams.set(input.name, q);
            const depHidden = document.getElementById("id_department");
            const depUI = document.getElementById("department-ui");
            const depVal =
              (depHidden && depHidden.value) || (depUI && depUI.value) || "";
            if (depVal) url.searchParams.set("department", depVal);
            const html = await fetch(url.toString(), {
              headers: { "X-Requested-With": "fetch" },
            }).then((r) => (r.ok ? r.text() : ""));
            if (html) {
              datalist.innerHTML = html;
            }
          }
        }
      } catch (e) {
        /* non-fatal */
      }

      const options = Array.from(datalist.querySelectorAll("option"));
      const items = options.filter(
        (o) => !q || (o.value || o.textContent || "").toLowerCase().includes(q),
      );
      overlay.innerHTML = "";
      activeIndex = -1;
      items.forEach((o, idx) => {
        const row = document.createElement("div");
        row.className = "px-3 py-2 cursor-pointer hover:bg-blue-50";
        const label = o.textContent || o.value || "";
        row.textContent = label;
        row.setAttribute("role", "option");
        row.addEventListener("mousedown", (e) => {
          e.preventDefault();
          // Display the label (e.g., "123 - Name")
          input.value = label;
          input.dispatchEvent(new Event("input", { bubbles: true }));
          input.dispatchEvent(new Event("change", { bubbles: true }));
          hide();
        });
        overlay.appendChild(row);
      });
      if (items.length === 0) {
        const msg = document.createElement("div");
        msg.className = "px-3 py-2 text-gray-500";
        msg.textContent = q ? "No matches" : "Type to search...";
        overlay.appendChild(msg);
      }
    }

    let originalListAttr = null;
    function show() {
      position();
      render(input.value);
      overlay.classList.remove("hidden");
      // Append to modal content when inside a modal/drawer to ensure proper stacking
      const modalContent = document.getElementById("modal-content");
      if (modalContent && modalContent.contains(input)) {
        modalContent.appendChild(overlay);
      } else {
        document.body.appendChild(overlay);
      }
      // Temporarily remove native datalist binding to suppress UA tooltip/popover
      try {
        if (originalListAttr === null) {
          originalListAttr = input.getAttribute("list");
        }
        if (input.hasAttribute("list")) {
          input.removeAttribute("list");
        }
      } catch (e) {}
      window.addEventListener("scroll", position, true);
      window.addEventListener("resize", position);
      document.addEventListener("mousedown", onDocDown);
      try {
        // Best-effort: prevent native popups by stopping pointer default
        input.addEventListener("pointerdown", preventOnce, {
          capture: true,
          once: true,
        });
      } catch (e) {}
    }
    function preventOnce(e) {
      e.preventDefault && e.preventDefault();
    }
    function hide() {
      overlay.classList.add("hidden");
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      // Restore native datalist binding after overlay hides
      try {
        if (originalListAttr !== null && !input.hasAttribute("list")) {
          input.setAttribute("list", originalListAttr);
        }
      } catch (e) {}
      window.removeEventListener("scroll", position, true);
      window.removeEventListener("resize", position);
      document.removeEventListener("mousedown", onDocDown);
    }
    function onDocDown(e) {
      if (e.target === input || overlay.contains(e.target)) return;
      hide();
    }

    function suppressNativeAutocomplete() {
      try {
        input.setAttribute(
          "autocomplete",
          "nope-" + Math.random().toString(36).slice(2),
        );
        input.setAttribute("autocorrect", "off");
        input.setAttribute("autocapitalize", "none");
        input.setAttribute("spellcheck", "false");
      } catch (e) {}
    }
    input.addEventListener("focus", () => {
      suppressNativeAutocomplete();
      show();
    });
    input.addEventListener("input", () => render(input.value));
    input.addEventListener("mousedown", suppressNativeAutocomplete);
    input.addEventListener("keydown", suppressNativeAutocomplete, true);
    input.addEventListener("keydown", (e) => {
      const rows = overlay.querySelectorAll('[role="option"]');
      if (e.key === "Escape") {
        hide();
        return;
      }
      if (!rows.length) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        activeIndex = Math.min(activeIndex + 1, rows.length - 1);
        rows.forEach((r) => r.classList.remove("bg-blue-50"));
        rows[activeIndex].classList.add("bg-blue-50");
        rows[activeIndex].scrollIntoView({ block: "nearest" });
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeIndex = Math.max(activeIndex - 1, 0);
        rows.forEach((r) => r.classList.remove("bg-blue-50"));
        rows[activeIndex].classList.add("bg-blue-50");
        rows[activeIndex].scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter" && activeIndex >= 0) {
        e.preventDefault();
        rows[activeIndex].dispatchEvent(
          new Event("mousedown", { bubbles: true }),
        );
      }
    });

    input._overlay = { show, hide, element: overlay };
    return input._overlay;
  }

  function init(root) {
    const scope = root || document;
    scope
      .querySelectorAll(
        "input[list]:not([data-overlay='native']):not([data-overlay-disabled])",
      )
      .forEach(buildOverlay);
  }

  document.addEventListener("DOMContentLoaded", () => {
    init();
  });
  // Expose initializer so other components (modal/drawer) can init overlays for injected HTML
  window.initPredictiveDatalistOverlay = init;
  document.body.addEventListener("htmx:afterSwap", (e) => {
    init(e.target);
    // If a datalist was updated, refresh any open overlay using it
    const target = e.target;
    if (target && target.tagName === "DATALIST" && target.id) {
      document.querySelectorAll(`input[list='${target.id}']`).forEach((inp) => {
        if (inp._overlay) {
          // Rebuild or re-render content to match new options
          const val = inp.value;
          inp._overlay.hide();
          const ol = buildOverlay(inp);
          if (document.activeElement === inp) {
            ol.show();
          }
        }
      });
    }
  });

  // Allow overlays to re-render on demand
  document.addEventListener("force-render", function (e) {
    /* noop root handler */
  });
})();
