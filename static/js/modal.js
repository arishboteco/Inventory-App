(function () {
  function openModal(html) {
    const root = document.getElementById('modal-root');
    const content = document.getElementById('modal-content');
    if (!root || !content) return;
    content.innerHTML = html;
    root.classList.remove('hidden');
  }
  function openDrawer(html, side = 'right') {
    const root = document.getElementById('modal-root');
    const content = document.getElementById('modal-content');
    if (!root || !content) return;
    content.innerHTML = `<div class="drawer ${side}">${html}</div>`;
    root.classList.remove('hidden');
  }
  function closeModal() {
    const root = document.getElementById('modal-root');
    const content = document.getElementById('modal-content');
    if (!root || !content) return;
    root.classList.add('hidden');
    content.innerHTML = '';
  }

  // public API
  window.modal = { open: openModal, openDrawer, close: closeModal };

  // delegation for close events
  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-modal-close]')) {
      closeModal();
    }
  });

  // Intercept modal form submits for partial saves
  document.addEventListener('submit', function (e) {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (!form.hasAttribute('data-modal-form')) return;
    e.preventDefault();
    const csrf = form.querySelector('input[name="csrfmiddlewaretoken"])?.value;
    const fd = new FormData(form);
    fd.set('partial', '1');
    const url = form.getAttribute('action') || window.location.href;
    fetch(url, { method: 'POST', headers: csrf ? { 'X-CSRFToken': csrf } : {}, body: fd })
      .then(r => r.json().catch(() => ({})))
      .then(data => {
        if (data && data.ok) {
          if (window.notifications) window.notifications.showToast(data.message || 'Saved', 'success');
          closeModal();
          window.location.reload();
        } else {
          if (window.notifications) window.notifications.showToast((data && data.message) || 'Save failed', 'error');
        }
      })
      .catch(() => {
        if (window.notifications) window.notifications.showToast('Network error', 'error');
      });
  });
})();
