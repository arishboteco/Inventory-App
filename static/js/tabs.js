function initTabs(root) {
  (root || document).querySelectorAll("[data-tabs]").forEach((container) => {
    if (container._tabsInitialized) return;
    container._tabsInitialized = true;
    const tabs = container.querySelectorAll("[data-tab-target]");
    const panels = container.querySelectorAll('[role="tabpanel"]');
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const target = tab.getAttribute("data-tab-target");
        tabs.forEach((t) => {
          t.classList.remove("border-primary", "text-primary");
          t.setAttribute("aria-selected", "false");
        });
        panels.forEach((p) => p.classList.add("hidden"));
        tab.classList.add("border-primary", "text-primary");
        tab.setAttribute("aria-selected", "true");
        const panel = container.querySelector(`#${target}`);
        if (panel) {
          panel.classList.remove("hidden");
          // Trigger resize so Chart.js redraws on newly-visible canvas
          window.dispatchEvent(new Event("resize"));
        }
      });
    });
  });
}

document.addEventListener("DOMContentLoaded", () => initTabs(document));
// Re-initialize after any HTMX content swap so injected tabs also work
document.body.addEventListener("htmx:afterSwap", (e) => initTabs(e.target));
