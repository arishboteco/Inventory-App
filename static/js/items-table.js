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
      case 'confirm-bulk': {
        e.preventDefault();
        const actionType = target.getAttribute('data-action-type');
        const ids = Array.from(document.querySelectorAll("input[name='selected_items']:checked")).map(el => el.value);
        if (ids.length === 0) return;
        const fd = new FormData();
        fd.append('action', actionType);
        ids.forEach(id => fd.append('ids[]', id));
        if (actionType === 'assign_dept') {
          const sel = document.getElementById('bulk-dept-select');
          if (sel && sel.value) fd.append('dept_id', sel.value);
        }
        fetch('/items/bulk/', { method: 'POST', headers: { 'X-CSRFToken': getCsrfToken() }, body: fd })
          .then(r => r.json().catch(() => ({})))
          .then(data => {
            if (data && data.ok) {
              if (window.notifications) window.notifications.showToast('Bulk action complete', 'success');
              window.location.reload();
            } else {
              if (window.notifications) window.notifications.showToast((data && data.message) || 'Bulk action failed', 'error');
            }
          })
          .catch(() => { if (window.notifications) window.notifications.showToast('Network error', 'error'); });
        break; }
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
    const hidden = JSON.parse(localStorage.getItem('items_table_hidden') || '[]');
    const idx = hidden.indexOf(col);
    if (!on && idx === -1) hidden.push(col);
    if (on && idx !== -1) hidden.splice(idx, 1);
    localStorage.setItem('items_table_hidden', JSON.stringify(hidden));
  });

  document.addEventListener('DOMContentLoaded', function () {
    const hidden = JSON.parse(localStorage.getItem('items_table_hidden') || '[]');
    if (hidden.length) {
      hidden.forEach(col => {
        document.querySelectorAll(`[data-col='${col}']`).forEach(el => el.classList.add('hidden'));
        document.querySelectorAll(`[data-col-toggle][value='${col}']`).forEach(cb => cb.checked = false);
      });
    }
  });

  function getCsrfToken() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    if (m) return decodeURIComponent(m[1]);
    const inp = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return inp ? inp.value : '';
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
      const html = `
        <div class=\"card\" style=\"max-width:420px\">\n          <div class=\"card-header\"><strong>Deactivate ${ids.length} item(s)?</strong></div>\n          <div class=\"card-body\">\n            <p class=\"mb-3\">Items will be marked Inactive. You can reactivate later.</p>\n            <div class=\"flex\" style=\"gap:.5rem; justify-content:flex-end\">\n              <button type=\"button\" class=\"btn-secondary\" data-modal-close>Cancel</button>\n              <button type=\"button\" class=\"btn-primary\" data-action=\"confirm-bulk\" data-action-type=\"deactivate\">Confirm</button>\n            </div>\n          </div>\n        </div>`;
      if (window.modal) window.modal.open(html);
    } else if (action === 'assign') {
      const tpl = document.getElementById('dept-select-template');
      const selectHtml = tpl ? tpl.outerHTML.replace('id=\"dept-select-template\"', 'id=\"bulk-dept-select\"') : '<input id=\"bulk-dept-select\" placeholder=\"Dept ID\">';
      const html = `
        <div class=\"card\" style=\"max-width:480px\">\n          <div class=\"card-header\"><strong>Assign Department</strong></div>\n          <div class=\"card-body\">\n            <label class=\"form-label\">Department</label>\n            ${selectHtml}\n            <div class=\"mt-3 flex\" style=\"gap:.5rem; justify-content:flex-end\">\n              <button type=\"button\" class=\"btn-secondary\" data-modal-close>Cancel</button>\n              <button type=\"button\" class=\"btn-primary\" data-action=\"confirm-bulk\" data-action-type=\"assign_dept\">Assign</button>\n            </div>\n          </div>\n        </div>`;
      if (window.modal) window.modal.open(html);
    }
  });
})();
