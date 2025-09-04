(function () {

  function enhance(container) {
    if (!container || container.dataset.enhanced === "1") return;
    let list = container.querySelector("ul");
    // Fallback: Some renderers may output raw checkboxes without a UL
    if (!list) {
      const checkboxes = container.querySelectorAll(
        'input[type="checkbox"].department-checkbox, input[type="checkbox"][name*="departments"]',
      );
      if (checkboxes.length) {
        list = document.createElement("ul");
        checkboxes.forEach((cb) => {
          const li = document.createElement("li");
          const label = cb.closest("label");
          if (label) {
            // Move the entire label into the LI for proper semantics
            li.appendChild(label);
          } else {
            // As a fallback, append the checkbox and its following text node
            li.appendChild(cb);
            if (cb.nextSibling) li.appendChild(cb.nextSibling);
          }
          list.appendChild(li);
        });
        container.appendChild(list);
      }
    }
    if (!list) return;

    container.dataset.enhanced = "1";
    container.classList.add("relative");

    // Ensure the list spans full width and lays out items responsively
    // This prevents the UL from squeezing into a single grid column when the container uses grid
  list.classList.add(
      "col-span-full",
      "w-full",
      "flex",
      "flex-wrap",
      "gap-2",
      "max-h-52",
      "overflow-y-auto",
      "pr-1",
    );

    // Build chips area
    const chips = document.createElement("div");
    chips.className = "chips col-span-full w-full flex flex-wrap gap-2";

  container.prepend(chips);

    function updateChips() {
      chips.innerHTML = "";
      const checked = list.querySelectorAll('input[type="checkbox"]:checked');
      checked.forEach((cb) => {
        const li = cb.closest("li");
        const labelNode = li ? li.querySelector("label") : null;
        const label = labelNode ? labelNode.textContent.trim() : (li ? li.textContent.trim() : cb.value);
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = [
          "inline-flex",
          "items-center",
          "gap-2",
          "px-3",
          "py-1.5",
          "text-sm",
          "font-medium",
          "rounded-full",
          "bg-blue-600",
          "text-white",
          "hover:bg-blue-700",
          "transition",
          "focus:outline-none",
          "focus:ring-2",
          "focus:ring-primary",
          "disabled:opacity-50",
          "disabled:cursor-not-allowed",
        ].join(" ");
        chip.setAttribute("aria-label", `Remove ${label}`);

        // Display label and an "×" icon that's hidden from assistive tech
    chip.append(label + " ");
        const removeIcon = document.createElement("span");
        removeIcon.setAttribute("aria-hidden", "true");
        removeIcon.textContent = "×";
        chip.appendChild(removeIcon);

        chip.addEventListener("click", () => {
          cb.click();
        });
        chip.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            cb.click();
          }
        });
        chips.appendChild(chip);
      });
    }

  // Search removed per design: all options remain visible

    // Layout now uses Tailwind utility classes applied directly; no extra sizing here.

    function styleOptions() {
      list.querySelectorAll("li").forEach((li) => {
        li.classList.add("p-0", "border-0", "rounded");
        const label = li.querySelector("label");
        const cb = li.querySelector('input[type="checkbox"]');
        if (!label || !cb) return;

        // Make label look like a chip-like toggle sized to its text
        label.classList.add(
          "inline-flex",
          "items-center",
          "gap-2",
          "px-3",
          "py-2",
          "rounded-full",
          "border",
          "transition",
          "cursor-pointer",
          "select-none",
          "whitespace-nowrap",
        );

        // Hide the native checkbox visually but keep it accessible
        cb.classList.add("sr-only");

        const selectedClasses = [
          "bg-blue-600",
          "text-white",
          "border-blue-600",
        ];
        const unselectedClasses = [
          "bg-blue-50",
          "text-blue-700",
          "border-blue-200",
        ];

        if (cb.checked) {
          label.classList.remove(...unselectedClasses);
          label.classList.add(...selectedClasses);
          label.setAttribute("aria-checked", "true");
        } else {
          label.classList.remove(...selectedClasses);
          label.classList.add(...unselectedClasses);
          label.setAttribute("aria-checked", "false");
        }

        // Keyboard toggle support on label
        label.tabIndex = 0;
        label.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            cb.click();
          }
        });
      });
    }

    // Initial styling
    styleOptions();

    // Hook events
  list.addEventListener("change", () => {
      updateChips();
      styleOptions();
    });

    // Initialize
    updateChips();
  }

  function init(root = document) {
    root.querySelectorAll('[data-multiselect="chips"]').forEach(enhance);
  }

  window.initMultiselectChips = init;

  document.addEventListener("DOMContentLoaded", function () {
    init();
  });
})();
