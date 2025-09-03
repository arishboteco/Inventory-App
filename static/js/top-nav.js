// Accessible grouped navigation menu
function initTopNav(doc = document) {
  const container = doc.querySelector("[data-top-nav]");
  if (!container) return;
  const groups = container.querySelectorAll("[data-nav-group]");
  groups.forEach((group) => {
    const button = group.querySelector("button");
    const panel = group.querySelector("[data-nav-panel]");
    if (!button || !panel) return;
    button.setAttribute("aria-expanded", "false");
    panel.classList.add("hidden");
    button.addEventListener("click", () => toggle(panel, button));
    button.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        close(panel, button);
      }
    });
  });
}

function toggle(panel, button) {
  const expanded = button.getAttribute("aria-expanded") === "true";
  if (expanded) {
    close(panel, button);
  } else {
    open(panel, button);
  }
}

function open(panel, button) {
  button.setAttribute("aria-expanded", "true");
  panel.classList.remove("hidden");
}

function close(panel, button) {
  button.setAttribute("aria-expanded", "false");
  panel.classList.add("hidden");
  button.focus();
}

if (typeof window !== "undefined") {
  window.addEventListener("DOMContentLoaded", () => initTopNav());
  window.topNav = { initTopNav, open, close, toggle };
}

module.exports = { initTopNav, open, close, toggle };
