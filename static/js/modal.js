(function () {
  let lastFocused = null;
  let trapHandler = null;
  function trapFocus(container) {
    if (trapHandler) container.removeEventListener("keydown", trapHandler);
    const focusable = container.querySelectorAll(
      'a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])',
    );
    if (!focusable.length) {
      container.focus();
      trapHandler = null;
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    trapHandler = function (e) {
      if (e.key !== "Tab") return;
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    container.addEventListener("keydown", trapHandler);
    first.focus();
  }
  function setAria(root, content) {
    const heading = content.querySelector("h1, h2, h3, h4, h5, h6");
    if (heading) {
      const id = heading.id || "modal-heading";
      heading.id = id;
      root.setAttribute("aria-labelledby", id);
    } else {
      root.removeAttribute("aria-labelledby");
    }
  }
  function openModal(html) {
    const root = document.getElementById("modal-root");
    const content = document.getElementById("modal-content");
    if (!root || !content) return;
    lastFocused = document.activeElement;
    content.innerHTML = html;
    setAria(root, content);
    root.classList.remove("hidden");
    trapFocus(root);
  }
  function openDrawer(html, side = "right") {
    const root = document.getElementById("modal-root");
    const content = document.getElementById("modal-content");
    if (!root || !content) return;
    lastFocused = document.activeElement;
    content.innerHTML = `<div class="drawer ${side}">${html}</div>`;
    setAria(root, content);
    root.classList.remove("hidden");
    trapFocus(root);
  }
  function closeModal() {
    const root = document.getElementById("modal-root");
    const content = document.getElementById("modal-content");
    if (!root || !content) return;
    root.classList.add("hidden");
    root.removeAttribute("aria-labelledby");
    content.innerHTML = "";
    if (lastFocused && typeof lastFocused.focus === "function") {
      lastFocused.focus();
      lastFocused = null;
    }
  }

  // public API
  window.modal = { open: openModal, openDrawer, close: closeModal };

  // delegation for close and open events
  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-modal-close]")) {
      closeModal();
      return;
    }
    const opener = e.target.closest("[data-modal-url]");
    if (opener) {
      e.preventDefault();
      const url = opener.getAttribute("data-modal-url");
      const type = opener.getAttribute("data-modal-type") || "modal";
      fetch(url)
        .then((r) => r.text())
        .then((html) => {
          if (type === "drawer") openDrawer(html, "right");
          else openModal(html);
        })
        .catch(() => {
          if (window.notifications)
            window.notifications.showToast("Failed to load content", "error");
        });
    }
  });

  // Intercept modal form submits for partial saves
  document.addEventListener("submit", function (e) {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (!form.hasAttribute("data-modal-form")) return;
    e.preventDefault();
    const csrf = form.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
    const fd = new FormData(form);
    fd.set("partial", "1");
    const url = form.getAttribute("action") || window.location.href;
    fetch(url, {
      method: "POST",
      headers: csrf ? { "X-CSRFToken": csrf } : {},
      body: fd,
    })
      .then((r) => r.json().catch(() => ({})))
      .then((data) => {
        if (data && data.ok) {
          if (window.notifications)
            window.notifications.showToast(data.message || "Saved", "success");
          closeModal();
          window.location.reload();
        } else {
          if (window.notifications)
            window.notifications.showToast(
              (data && data.message) || "Save failed",
              "error",
            );
        }
      })
      .catch(() => {
        if (window.notifications)
          window.notifications.showToast("Network error", "error");
      });
  });
})();
