// Items Table interactions: accessible expand/collapse and inline edit
// Uses event delegation to avoid inline handlers in templates.

(function () {
  function findRow(el) {
    return el.closest('.item-row');
  }

  function toggleDetails(row) {
    const itemId = row?.dataset.itemId;
    if (!itemId) return;
    const details = document.getElementById(`details-${itemId}`);
    const toggleBtn = row.querySelector('[data-action="toggle-details"]');
    if (!details || !toggleBtn) return;

    const expanded = toggleBtn.getAttribute('aria-expanded') === 'true';
    if (expanded) {
      details.classList.add('hidden');
      toggleBtn.setAttribute('aria-expanded', 'false');
      // reset chevron rotation
      const svg = toggleBtn.querySelector('svg');
      if (svg) svg.style.transform = 'rotate(0deg)';
    } else {
      details.classList.remove('hidden');
      toggleBtn.setAttribute('aria-expanded', 'true');
      const svg = toggleBtn.querySelector('svg');
      if (svg) svg.style.transform = 'rotate(90deg)';
    }
  }

  function enableInlineEdit(row) {
    const itemId = row?.dataset.itemId;
    if (!itemId) return;
    const editForm = document.getElementById(`edit-form-${itemId}`);
    const detailsView = document.getElementById(`details-view-${itemId}`);
    const detailsPanel = document.getElementById(`details-${itemId}`);
    if (!editForm || !detailsPanel) return;
    if (detailsPanel.classList.contains('hidden')) toggleDetails(row);
    editForm.classList.remove('hidden');
    if (detailsView) detailsView.classList.add('hidden');
  }

  function cancelInlineEdit(row) {
    const itemId = row?.dataset.itemId;
    if (!itemId) return;
    const editForm = document.getElementById(`edit-form-${itemId}`);
    const detailsView = document.getElementById(`details-view-${itemId}`);
    if (editForm) editForm.classList.add('hidden');
    if (detailsView) detailsView.classList.remove('hidden');
  }

  function saveInlineEdit(row, form) {
    const itemId = row?.dataset.itemId;
    if (!itemId) return;
    const formData = new FormData(form);
    // TODO: wire to backend via fetch POST to inline update endpoint
    // For now, optimistic UX
    setTimeout(() => {
      cancelInlineEdit(row);
      if (window.notifications && window.notifications.showToast) {
        window.notifications.showToast('Item updated successfully!', 'success');
      }
    }, 300);
  }

  function deleteItem(row) {
    const itemId = row?.dataset.itemId;
    if (!itemId) return;
    if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) return;
    // TODO: AJAX delete; for now, toast only
    if (window.notifications && window.notifications.showToast) {
      window.notifications.showToast('Item deleted successfully!', 'success');
    }
  }

  // Event delegation
  document.addEventListener('click', function (e) {
    const target = e.target.closest('[data-action]');
    if (!target) return;
    const action = target.getAttribute('data-action');
    const row = findRow(target);
    if (!row) return;

    switch (action) {
      case 'toggle-details':
        e.preventDefault();
        toggleDetails(row);
        break;
      case 'quick-edit':
        e.preventDefault();
        enableInlineEdit(row);
        break;
      case 'cancel-edit':
        e.preventDefault();
        cancelInlineEdit(row);
        break;
      case 'delete':
        e.preventDefault();
        deleteItem(row);
        break;
      case 'select-item':
        // no-op for now; hook bulk actions toolbar later
        break;
      default:
        break;
    }
  });

  // Intercept inline edit form submit
  document.addEventListener('submit', function (e) {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.getAttribute('data-action') !== 'save-inline') return;
    e.preventDefault();
    const row = findRow(form);
    saveInlineEdit(row, form);
  });

  // Keyboard accessibility for toggle button
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const target = e.target.closest('[data-action="toggle-details"]');
    if (!target) return;
    e.preventDefault();
    const row = findRow(target);
    toggleDetails(row);
  });

  // Expose minimal API for debugging
  window.itemsTable = { toggleDetails, enableInlineEdit, cancelInlineEdit };
})();
