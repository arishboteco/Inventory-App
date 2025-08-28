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
    const csrf = form.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
    fetch(`/items/${itemId}/inline-update/`, {
      method: 'POST',
      headers: csrf ? { 'X-CSRFToken': csrf } : {},
      body: formData,
    })
      .then((r) => r.json().catch(() => ({})))
      .then((data) => {
        if (data && data.ok) {
          cancelInlineEdit(row);
          if (window.notifications && window.notifications.showToast) {
            window.notifications.showToast(data.message || 'Item updated', 'success');
          }
        } else {
          if (window.notifications && window.notifications.showToast) {
            window.notifications.showToast((data && data.message) || 'Save failed', 'error');
          }
        }
      })
      .catch(() => {
        if (window.notifications && window.notifications.showToast) {
          window.notifications.showToast('Network error while saving', 'error');
        }
      });
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
      case 'table-quick-edit':
        e.preventDefault();
        // For table rows, show adjacent edit row
        const itemId = row.dataset.itemId;
        const editRow = document.getElementById(`edit-${itemId}`);
        if (editRow) {
          editRow.classList.toggle('hidden');
        }
        break;
      case 'cancel-edit':
        e.preventDefault();
        // Hide card edit or table edit
        const itemId2 = row.dataset.itemId;
        const editRow2 = document.getElementById(`edit-${itemId2}`);
        if (editRow2 && !editRow2.classList.contains('hidden')) {
          editRow2.classList.add('hidden');
        } else {
          cancelInlineEdit(row);
        }
        break;
      case 'delete':
        e.preventDefault();
        deleteItem(row);
        break;
      case 'open-edit':
        e.preventDefault();
        const href = target.getAttribute('data-href');
        if (!href) return;
        fetch(href, { headers: { 'X-Requested-With': 'fetch' }})
          .then(r => r.text())
          .then(html => { if (window.modal) window.modal.open(html); })
          .catch(() => { if (window.notifications) window.notifications.showToast('Failed to open editor', 'error'); });
        break;
      case 'select-item':
        updateBulkBar();
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
    // find row for cards; for table edit row, previousElementSibling is the item row
    let row = findRow(form);
    if (!row) {
      const editRow = form.closest('tr');
      if (editRow && editRow.previousElementSibling?.dataset?.itemId) {
        row = editRow.previousElementSibling;
      }
    }
    saveInlineEdit(row, form);
  });

  // Select-all support
  document.addEventListener('change', function (e) {
    const selAll = e.target?.closest('[data-select-all]');
    if (!selAll) return;
    const table = document.getElementById('grid-table');
    if (!table) return;
    table.querySelectorAll("input[name='selected_items']").forEach(cb => { cb.checked = e.target.checked; });
    updateBulkBar();
  });

  // Column visibility toggles
  document.addEventListener('change', function (e) {
    const ctl = e.target?.closest('[data-col-toggle]');
    if (!ctl) return;
    const col = ctl.value;
    const on = ctl.checked;
    document.querySelectorAll(`[data-col='${col}']`).forEach(el => {
      if (on) el.classList.remove('hidden'); else el.classList.add('hidden');
    });
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
  
  // Bulk actions bar helpers
  function countSelections() {
    return document.querySelectorAll("input[name='selected_items']:checked").length;
  }
  function updateBulkBar() {
    const count = countSelections();
    const bar = document.getElementById('bulk-actions');
    const label = document.getElementById('bulk-count');
    if (!bar || !label) return;
    label.textContent = `${count} selected`;
    if (count > 0) bar.classList.remove('hidden'); else bar.classList.add('hidden');
  }

  document.addEventListener('change', function (e) {
    if (e.target && e.target.name === 'selected_items') updateBulkBar();
  });

  document.addEventListener('click', function (e) {
    const btn = e.target.closest('[data-bulk-action]');
    if (!btn) return;
    const action = btn.getAttribute('data-bulk-action');
    const ids = Array.from(document.querySelectorAll("input[name='selected_items']:checked")).map(el => el.value);
    if (ids.length === 0) return;
    if (action === 'export') {
      // naive CSV export trigger: navigate to export URL with current query
      const url = new URL(window.location.origin + '/items/export/');
      // Retain existing filters
      const current = new URL(window.location.href);
      current.searchParams.forEach((v, k) => url.searchParams.append(k, v));
      window.location.assign(url.toString());
    } else if (action === 'deactivate') {
      if (window.notifications) window.notifications.showToast('Deactivate action queued', 'info');
    } else if (action === 'assign') {
      if (window.notifications) window.notifications.showToast('Assign to department not yet implemented', 'info');
    }
  });
})();
