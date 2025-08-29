// Items Table interactions: accessible expand/collapse and inline edit
// Uses event delegation to avoid inline handlers in templates.

(function () {
  function findRow(el) {
    return el.closest(".item-row");
  }

  function toggleDetails(row) {
    const itemId = row?.dataset.itemId;
    if (!itemId) return;
    const details = document.getElementById(`details-${itemId}`);
    const toggleBtn = row.querySelector('[data-action="toggle-details"]');
    if (!details || !toggleBtn) return;

    const expanded = toggleBtn.getAttribute("aria-expanded") === "true";
    if (expanded) {
      details.classList.add("hidden");
      toggleBtn.setAttribute("aria-expanded", "false");
      // reset chevron rotation
      const svg = toggleBtn.querySelector("svg");
      if (svg) svg.style.transform = "rotate(0deg)";
    } else {
      details.classList.remove("hidden");
      toggleBtn.setAttribute("aria-expanded", "true");
      const svg = toggleBtn.querySelector("svg");
      if (svg) svg.style.transform = "rotate(90deg)";
    }
  }

  function enableInlineEdit(row) {
    const itemId = row?.dataset.itemId;
    if (!itemId) return;
    const editForm = document.getElementById(`edit-form-${itemId}`);
    const detailsView = document.getElementById(`details-view-${itemId}`);
    const detailsPanel = document.getElementById(`details-${itemId}`);
    if (!editForm || !detailsPanel) return;
    if (detailsPanel.classList.contains("hidden")) toggleDetails(row);
    editForm.classList.remove("hidden");
    if (detailsView) detailsView.classList.add("hidden");
  }

  // New: in-row inline editing (no extra row)
  function beginRowEdit(row) {
    if (!row || row.dataset.editing === "1") return;
    row.dataset.editing = "1";
    row.dataset.origHtml = row.innerHTML; // for cancel/restore

    const nameCell = row.querySelector('td[data-col="name"]');
    const ropCell = row.querySelector('td[data-col="rop"]');
    const categoryCell = row.querySelector('td[data-col="category"]');
    const unitCell = row.querySelector('td[data-col="unit"]');
    const stockCell = row.querySelector('td[data-col="stock"]');
    const statusCell = row.querySelector('td[data-col="status"]');
    const actionsCell = row.querySelector("td:last-child");

    const currentName = (
      nameCell?.querySelector(".font-medium")?.textContent || ""
    ).trim();
    const ropText = (ropCell?.textContent || "").trim();
    const currentRop = /^[-+]?[0-9]*\.?[0-9]+$/.test(ropText) ? ropText : "";
    const currentCategory = (categoryCell?.textContent || "")
      .trim()
      .split("→")[0]
      .trim();
    const currentUnit = (unitCell?.textContent || "").trim();
    const stockText = (stockCell?.textContent || "").trim();
    const currentStock = /^[-+]?[0-9]*\.?[0-9]+$/.test(stockText)
      ? stockText
      : "";
    const isActive = (statusCell?.textContent || "")
      .toLowerCase()
      .includes("active");

    nameCell.innerHTML = `<input type="text" name="name" class="form-input" value="${escapeHtml(currentName)}">`;
    if (categoryCell) {
      const tpl = document.getElementById("category-id-select-template");
      const cid = row.getAttribute("data-category-id") || "";
      if (tpl) {
        const sel = tpl.cloneNode(true);
        sel.id = "";
        sel.name = "category_id";
        sel.classList.add("form-select");
        Array.from(sel.options).forEach((o) => {
          if (o.value == cid) o.selected = true;
        });
        categoryCell.innerHTML = "";
        categoryCell.appendChild(sel);
      } else {
        categoryCell.innerHTML = `<input type="text" name="category" class="form-input" value="${escapeHtml(currentCategory)}" placeholder="Category">`;
      }
    }
    if (unitCell) {
      const tplU = document.getElementById("unit-select-template");
      const uid = row.getAttribute("data-unit-id") || "";
      if (tplU) {
        const selU = tplU.cloneNode(true);
        selU.id = "";
        selU.name = "unit_id";
        selU.classList.add("form-select");
        Array.from(selU.options).forEach((o) => {
          if (o.value == uid) o.selected = true;
        });
        unitCell.innerHTML = "";
        unitCell.appendChild(selU);
      } else {
        unitCell.innerHTML = `<input type="text" name="base_unit" class="form-input" value="${escapeHtml(currentUnit)}" placeholder="Unit">`;
      }
    }
    if (stockCell)
      stockCell.innerHTML = `<input type="number" step="0.01" name="current_stock" class="form-input" value="${escapeHtml(currentStock)}" placeholder="0">`;
    ropCell.innerHTML = `<input type="number" step="0.01" name="reorder_point" class="form-input" value="${escapeHtml(currentRop)}">`;
    statusCell.innerHTML = `<label class="inline-flex items-center gap-2"><input type="checkbox" name="is_active" ${isActive ? "checked" : ""} class="form-checkbox"><span>Active</span></label>`;
    actionsCell.innerHTML = `<div class="flex items-center" style="gap:.25rem"><button type="button" data-action="save-row" class="inline-flex items-center px-3 py-2 text-sm font-medium text-white bg-primary border border-transparent rounded-md hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed px-2.5 py-1.5 text-xs">Save</button><button type="button" data-action="cancel-row" class="inline-flex items-center px-3 py-2 text-sm font-medium text-bodyText bg-white border border-border rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed px-2.5 py-1.5 text-xs">Cancel</button></div>`;
  }

  function restoreRow(row) {
    if (!row || !row.dataset.origHtml) return;
    row.innerHTML = row.dataset.origHtml;
    delete row.dataset.origHtml;
    delete row.dataset.editing;
  }

  function saveRow(row) {
    if (!row) return;
    const itemId = row.dataset.itemId;
    const name = row.querySelector('input[name="name"]')?.value || "";
    const rop = row.querySelector('input[name="reorder_point"]')?.value || "";
    const categoryId =
      row.querySelector('select[name="category_id"]')?.value || "";
    const unitId = row.querySelector('select[name="unit_id"]')?.value || "";
    const currentStock =
      row.querySelector('input[name="current_stock"]')?.value || "";
    const active =
      row.querySelector('input[name="is_active"]')?.checked || false;

    const fd = new FormData();
    fd.append("name", name);
    if (rop !== "") fd.append("reorder_point", rop);
    if (categoryId !== "") fd.append("category_id", categoryId);
    if (unitId !== "") fd.append("unit_id", unitId);
    if (currentStock !== "") fd.append("current_stock", currentStock);
    if (active) fd.append("is_active", "on"); // presence -> True for Django

    const csrf = getCsrfToken();
    fetch(`/items/${itemId}/inline-update/`, {
      method: "POST",
      headers: csrf ? { "X-CSRFToken": csrf } : {},
      body: fd,
    })
      .then((r) => r.json().catch(() => ({})))
      .then((data) => {
        if (data && data.ok) {
          // restore and update visible values inline
          const prevHtml = row.dataset.origHtml;
          restoreRow(row);
          // Update fields after restore
          const nameCell = row.querySelector(
            'td[data-col="name"] .font-medium',
          );
          if (nameCell && name) nameCell.textContent = name;
          const ropCell = row.querySelector('td[data-col="rop"]');
          if (ropCell && rop !== "") ropCell.textContent = rop;
          const categoryCell = row.querySelector('td[data-col="category"]');
          if (categoryCell && categoryId !== "") {
            const sel = document.getElementById("category-id-select-template");
            if (sel) {
              const opt = Array.from(sel.options).find(
                (o) => o.value == categoryId,
              );
              if (opt) categoryCell.textContent = opt.textContent;
            }
            row.setAttribute("data-category-id", String(categoryId));
          }
          const unitCell = row.querySelector('td[data-col="unit"]');
          if (unitCell && unitId !== "") {
            const selU = document.getElementById("unit-select-template");
            if (selU) {
              const optU = Array.from(selU.options).find(
                (o) => o.value == unitId,
              );
              if (optU) unitCell.textContent = optU.textContent;
            }
            row.setAttribute("data-unit-id", String(unitId));
          }
          const stockCell = row.querySelector('td[data-col="stock"]');
          if (stockCell && currentStock !== "")
            stockCell.textContent = currentStock;
          const statusCell = row.querySelector('td[data-col="status"]');
          if (statusCell) {
            statusCell.innerHTML = active
              ? '<span class="badge badge-success">Active</span>'
              : '<span class="badge badge-error">Inactive</span>';
          }
          if (window.notifications && window.notifications.showToast) {
            window.notifications.showToast(
              data.message || "Item updated",
              "success",
            );
          }
        } else {
          if (window.notifications && window.notifications.showToast) {
            window.notifications.showToast(
              (data && data.message) || "Save failed",
              "error",
            );
          }
        }
      })
      .catch(() => {
        if (window.notifications && window.notifications.showToast) {
          window.notifications.showToast("Network error while saving", "error");
        }
      });
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function cancelInlineEdit(row) {
    const itemId = row?.dataset.itemId;
    if (!itemId) return;
    const editForm = document.getElementById(`edit-form-${itemId}`);
    const detailsView = document.getElementById(`details-view-${itemId}`);
    if (editForm) editForm.classList.add("hidden");
    if (detailsView) detailsView.classList.remove("hidden");
  }

  function saveInlineEdit(row, form) {
    const itemId = row?.dataset.itemId;
    if (!itemId) return;
    const formData = new FormData(form);
    let csrf = form.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
    if (!csrf) csrf = getCsrfToken();
    fetch(`/items/${itemId}/inline-update/`, {
      method: "POST",
      headers: csrf ? { "X-CSRFToken": csrf } : {},
      body: formData,
    })
      .then((r) => r.json().catch(() => ({})))
      .then((data) => {
        if (data && data.ok) {
          cancelInlineEdit(row);
          if (window.notifications && window.notifications.showToast) {
            window.notifications.showToast(
              data.message || "Item updated",
              "success",
            );
          }
        } else {
          if (window.notifications && window.notifications.showToast) {
            window.notifications.showToast(
              (data && data.message) || "Save failed",
              "error",
            );
          }
        }
      })
      .catch(() => {
        if (window.notifications && window.notifications.showToast) {
          window.notifications.showToast("Network error while saving", "error");
        }
      });
  }

  function deleteItem(row) {
    const itemId = row?.dataset.itemId;
    if (!itemId) return;
    if (
      !confirm(
        "Are you sure you want to delete this item? This action cannot be undone.",
      )
    )
      return;
    // TODO: AJAX delete; for now, toast only
    if (window.notifications && window.notifications.showToast) {
      window.notifications.showToast("Item deleted successfully!", "success");
    }
  }

  // Event delegation
  document.addEventListener("click", function (e) {
    const target = e.target.closest("[data-action]");
    if (!target) return;
    const action = target.getAttribute("data-action");
    // Prevent toggle-details if clicking a link with data-ignore-toggle
    if (
      action === "toggle-details" &&
      e.target.closest("[data-ignore-toggle]")
    ) {
      return;
    }
    const row = findRow(target);
    if (!row) return;

    switch (action) {
      case "toggle-details":
        e.preventDefault();
        toggleDetails(row);
        break;
      case "quick-edit":
        e.preventDefault();
        enableInlineEdit(row);
        break;
      case "table-quick-edit":
        e.preventDefault();
        beginRowEdit(row);
        break;
      case "cancel-edit":
        e.preventDefault();
        // Cancel for previous card edit or new in-row edit
        if (row.dataset.editing === "1") restoreRow(row);
        else cancelInlineEdit(row);
        break;
      case "cancel-row":
        e.preventDefault();
        restoreRow(row);
        break;
      case "save-row":
        e.preventDefault();
        saveRow(row);
        break;
      case "delete":
        e.preventDefault();
        deleteItem(row);
        break;
      case "open-edit":
        e.preventDefault();
        const href = target.getAttribute("data-href");
        if (!href) return;
        fetch(href, { headers: { "X-Requested-With": "fetch" } })
          .then((r) => r.text())
          .then((html) => {
            if (window.modal) window.modal.open(html);
          })
          .catch(() => {
            if (window.notifications)
              window.notifications.showToast("Failed to open editor", "error");
          });
        break;
      case "open-modal":
        e.preventDefault();
        {
          const href2 = target.getAttribute("data-href");
          if (!href2) return;
          fetch(href2, { headers: { "X-Requested-With": "fetch" } })
            .then((r) => r.text())
            .then((html) => {
              if (window.modal) window.modal.open(html);
            })
            .catch(() => {
              if (window.notifications)
                window.notifications.showToast("Failed to open", "error");
            });
        }
        break;
      case "select-item":
        updateBulkBar();
        break;
      case "confirm-bulk": {
        e.preventDefault();
        const actionType = target.getAttribute("data-action-type");
        const ids = Array.from(
          document.querySelectorAll("input[name='selected_items']:checked"),
        ).map((el) => el.value);
        if (ids.length === 0) return;
        const fd = new FormData();
        fd.append("action", actionType);
        ids.forEach((id) => fd.append("ids[]", id));
        if (actionType === "assign_dept") {
          const sel = document.getElementById("bulk-dept-select");
          if (sel && sel.value) fd.append("dept_id", sel.value);
        }
        fetch("/items/bulk/", {
          method: "POST",
          headers: { "X-CSRFToken": getCsrfToken() },
          body: fd,
        })
          .then((r) => r.json().catch(() => ({})))
          .then((data) => {
            if (data && data.ok) {
              if (window.notifications)
                window.notifications.showToast(
                  "Bulk action complete",
                  "success",
                );
              window.location.reload();
            } else {
              if (window.notifications)
                window.notifications.showToast(
                  (data && data.message) || "Bulk action failed",
                  "error",
                );
            }
          })
          .catch(() => {
            if (window.notifications)
              window.notifications.showToast("Network error", "error");
          });
        break;
      }
      default:
        break;
    }
  });

  // Intercept inline edit form submit
  document.addEventListener("submit", function (e) {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.getAttribute("data-action") !== "save-inline") return;
    e.preventDefault();
    // find row for cards; for table edit row, previousElementSibling is the item row
    let row = findRow(form);
    if (!row) {
      const editRow = form.closest("tr");
      if (editRow && editRow.previousElementSibling?.dataset?.itemId) {
        row = editRow.previousElementSibling;
      }
    }
    saveInlineEdit(row, form);
  });

  // Select-all support
  document.addEventListener("change", function (e) {
    const selAll = e.target?.closest("[data-select-all]");
    if (!selAll) return;
    const table = document.getElementById("grid-table");
    if (!table) return;
    table.querySelectorAll("input[name='selected_items']").forEach((cb) => {
      cb.checked = e.target.checked;
    });
    updateBulkBar();
  });

  // Column visibility toggles
  document.addEventListener("change", function (e) {
    const ctl = e.target?.closest("[data-col-toggle]");
    if (!ctl) return;
    const col = ctl.value;
    const on = ctl.checked;
    document.querySelectorAll(`[data-col='${col}']`).forEach((el) => {
      if (on) el.classList.remove("hidden");
      else el.classList.add("hidden");
    });
    const hidden = JSON.parse(
      localStorage.getItem("items_table_hidden") || "[]",
    );
    const idx = hidden.indexOf(col);
    if (!on && idx === -1) hidden.push(col);
    if (on && idx !== -1) hidden.splice(idx, 1);
    localStorage.setItem("items_table_hidden", JSON.stringify(hidden));
  });

  document.addEventListener("DOMContentLoaded", function () {
    const hidden = JSON.parse(
      localStorage.getItem("items_table_hidden") || "[]",
    );
    if (hidden.length) {
      hidden.forEach((col) => {
        document
          .querySelectorAll(`[data-col='${col}']`)
          .forEach((el) => el.classList.add("hidden"));
        document
          .querySelectorAll(`[data-col-toggle][value='${col}']`)
          .forEach((cb) => (cb.checked = false));
      });
    }
  });

  function getCsrfToken() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    if (m) return decodeURIComponent(m[1]);
    const inp = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return inp ? inp.value : "";
  }

  // Keyboard accessibility for toggle button
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" && e.key !== " ") return;
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
    return document.querySelectorAll("input[name='selected_items']:checked")
      .length;
  }
  function updateBulkBar() {
    const count = countSelections();
    const bar = document.getElementById("bulk-actions");
    const label = document.getElementById("bulk-count");
    if (!bar || !label) return;
    label.textContent = `${count} selected`;
    if (count > 0) bar.classList.remove("hidden");
    else bar.classList.add("hidden");
  }

  document.addEventListener("change", function (e) {
    if (e.target && e.target.name === "selected_items") updateBulkBar();
  });

  document.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-bulk-action]");
    if (!btn) return;
    const action = btn.getAttribute("data-bulk-action");
    const ids = Array.from(
      document.querySelectorAll("input[name='selected_items']:checked"),
    ).map((el) => el.value);
    if (ids.length === 0) return;
    if (action === "export") {
      // naive CSV export trigger: navigate to export URL with current query
      const url = new URL(window.location.origin + "/items/export/");
      // Retain existing filters
      const current = new URL(window.location.href);
      current.searchParams.forEach((v, k) => url.searchParams.append(k, v));
      window.location.assign(url.toString());
    } else if (action === "deactivate") {
      const html = `
        <div class=\"card\" style=\"max-width:420px\">\n          <div class=\"card-header\"><strong>Deactivate ${ids.length} item(s)?</strong></div>\n          <div class=\"card-body\">\n            <p class=\"mb-3\">Items will be marked Inactive. You can reactivate later.</p>\n            <div class=\"flex\" style=\"gap:.5rem; justify-content:flex-end\">\n              <button type=\"button\" class=\"inline-flex items-center px-3 py-2 text-sm font-medium text-bodyText bg-white border border-border rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed\" data-modal-close>Cancel</button>\n              <button type=\"button\" class=\"inline-flex items-center px-3 py-2 text-sm font-medium text-white bg-primary border border-transparent rounded-md hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed\" data-action=\"confirm-bulk\" data-action-type=\"deactivate\">Confirm</button>\n            </div>\n          </div>\n        </div>`;
      if (window.modal) window.modal.open(html);
    } else if (action === "assign") {
      const tpl = document.getElementById("dept-select-template");
      const selectHtml = tpl
        ? tpl.outerHTML.replace(
            'id=\"dept-select-template\"',
            'id=\"bulk-dept-select\"',
          )
        : '<input id=\"bulk-dept-select\" placeholder=\"Dept ID\">';
      const html = `
        <div class=\"card\" style=\"max-width:480px\">\n          <div class=\"card-header\"><strong>Assign Department</strong></div>\n          <div class=\"card-body\">\n            <label class=\"form-label\">Department</label>\n            ${selectHtml}\n            <div class=\"mt-3 flex\" style=\"gap:.5rem; justify-content:flex-end\">\n              <button type=\"button\" class=\"inline-flex items-center px-3 py-2 text-sm font-medium text-bodyText bg-white border border-border rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed\" data-modal-close>Cancel</button>\n              <button type=\"button\" class=\"inline-flex items-center px-3 py-2 text-sm font-medium text-white bg-primary border border-transparent rounded-md hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed\" data-action=\"confirm-bulk\" data-action-type=\"assign_dept\">Assign</button>\n            </div>\n          </div>\n        </div>`;
      if (window.modal) window.modal.open(html);
    }
  });
})();
