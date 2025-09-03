(function () {
  function enhance(container) {
    if (!container || container.dataset.enhanced === "1") return;
    const list = container.querySelector("ul");
    if (!list) return;

    container.dataset.enhanced = "1";
    container.classList.add("relative");

    // Build search input
    const searchWrap = document.createElement("div");
    searchWrap.className =
      "chips-search col-span-full w-full flex flex-wrap gap-2";
    const search = document.createElement("input");
    search.type = "text";
    search.placeholder = "Search departments…";
    search.className =
      "block w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary";
    searchWrap.appendChild(search);

    // Build chips area
    const chips = document.createElement("div");
    chips.className = "chips col-span-full w-full flex flex-wrap gap-2";

    container.prepend(chips);
    container.prepend(searchWrap);

    function updateChips() {
      chips.innerHTML = "";
      const checked = list.querySelectorAll('input[type="checkbox"]:checked');
      checked.forEach((cb) => {
        const li = cb.closest("li");
        const label = li ? li.textContent.trim() : cb.value;
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "dept-chip";
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

    function filterList(q) {
      const items = list.querySelectorAll("li");
      const qq = q.toLowerCase();
      items.forEach((li) => {
        const text = li.textContent.toLowerCase();
        li.style.display = text.includes(qq) ? "" : "none";
      });
    }

    // Layout now uses Tailwind utility classes applied directly; no extra sizing here.

    list.querySelectorAll("li").forEach((li) => {
      li.classList.add(
        "flex",
        "items-center",
        "gap-2",
        "p-2",
        "border",
        "rounded",
      );
    });

    // Hook events
    list.addEventListener("change", updateChips);
    search.addEventListener("input", (e) => filterList(e.target.value));

    // Initialize
    updateChips();
    // Focus search for quick keyboard access
    search.focus();
  }

  function init(root = document) {
    root.querySelectorAll('[data-multiselect="chips"]').forEach(enhance);
  }

  window.initMultiselectChips = init;

  document.addEventListener("DOMContentLoaded", function () {
    init();
  });
})();
