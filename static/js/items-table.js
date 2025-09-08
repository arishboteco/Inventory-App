// Items Table interactions: accessible expand/collapse and inline edit
// Uses event delegation to avoid inline handlers in templates.

(function () {
  // Track the currently edited row (quick edit mode)
  let currentEditingRow = null;
  const INPUT_CLASSES =
    "block w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary";
  const SELECT_CLASSES = INPUT_CLASSES;
  const CHECKBOX_CLASSES =
    "h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary";

  function findRow(el) {
    return el.closest(".item-row");
  }

  function toggleDetails(row) {
    const itemId = row?.dataset.itemId;
    if (!itemId) return;
    const details = document.getElementById(`details-${itemId}`);
    const toggleEl = row.querySelector('[data-action="toggle-details"]');
    if (!details || !toggleEl) return;

    const expanded = toggleEl.getAttribute("aria-expanded") === "true";
    details.classList.toggle("hidden", expanded);
    toggleEl.setAttribute("aria-expanded", expanded ? "false" : "true");
    const svg = toggleEl.querySelector("svg");
    if (svg) svg.classList.toggle("rotate-90", !expanded);
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

  function renderStockStatus(stock, rop) {
    const s = parseFloat(stock);
    const r = parseFloat(rop);
    if (!isNaN(s) && !isNaN(r)) {
      if (s <= r)
        return '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">Low Stock</span>';
      return '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-success-light text-success">In Stock</span>';
    }
    return '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">No Data</span>';
  }

  // New: in-row inline editing (no extra row)
  function beginRowEdit(row) {
    if (!row) return;
    // If this row is already being edited, treat call as a toggle (cancel)
    if (row.dataset.editing === "1") {
      restoreRow(row);
      return;
    }
    // If another row is in edit mode, restore it first
    if (currentEditingRow && currentEditingRow !== row) {
      restoreRow(currentEditingRow);
    }
    row.dataset.editing = "1";
    row.dataset.origHtml = row.innerHTML; // for cancel/restore
    row.classList.add("editing-row", "bg-yellow-50");
    currentEditingRow = row;

    const nameCell = row.querySelector('td[data-col="name"]');
    const categoryCell = row.querySelector('td[data-col="category"]');
    const unitCell = row.querySelector('td[data-col="unit"]');
    const stockCell = row.querySelector('td[data-col="stock"]');
    const statusCell = row.querySelector('td[data-col="status"]');
    const actionsCell = row.querySelector("td:last-child");

    const currentName = (
      nameCell?.querySelector(".font-medium")?.textContent || ""
    ).trim();
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

    nameCell.innerHTML = `<input type="text" name="name" class="${INPUT_CLASSES}" value="${escapeHtml(currentName)}">`;
    if (categoryCell) {
      const tpl = document.getElementById("category-id-select-template");
      const cid = row.getAttribute("data-category-id") || "";
      if (tpl) {
        const sel = tpl.cloneNode(true);
        sel.id = "";
        sel.name = "category_id";
        sel.className = `${sel.className} ${SELECT_CLASSES}`;
        Array.from(sel.options).forEach((o) => {
          if (o.value == cid) o.selected = true;
        });
        categoryCell.innerHTML = "";
        categoryCell.appendChild(sel);
      } else {
        categoryCell.innerHTML = `<input type="number" name="category_id" class="${INPUT_CLASSES}" value="${escapeHtml(cid)}" placeholder="Category ID">`;
      }
    }
    if (unitCell) {
      const tplU = document.getElementById("unit-select-template");
      const uid = row.getAttribute("data-unit-id") || "";
      if (tplU) {
        const selU = tplU.cloneNode(true);
        selU.id = "";
        selU.name = "unit_id";
        selU.className = `${selU.className} ${SELECT_CLASSES}`;
        Array.from(selU.options).forEach((o) => {
          if (o.value == uid) o.selected = true;
        });
        unitCell.innerHTML = "";
        unitCell.appendChild(selU);
      } else {
        unitCell.innerHTML = `<input type="number" name="unit_id" class="${INPUT_CLASSES}" value="${escapeHtml(currentUnit)}" placeholder="Unit ID">`;
      }
    }
    if (stockCell)
      stockCell.innerHTML = `<input type="number" step="0.01" name="current_stock" class="${INPUT_CLASSES}" value="${escapeHtml(currentStock)}" placeholder="0">`;
    statusCell.innerHTML = `<label class="inline-flex items-center gap-2"><input type="checkbox" name="is_active" ${isActive ? "checked" : ""} class="${CHECKBOX_CLASSES}"><span>Active</span></label>`;
    actionsCell.innerHTML = `<div class="flex items-center gap-1"><button type="button" data-action="save-row" class="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md transition focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed bg-primary text-white hover:bg-primaryHover focus:ring-2 focus:ring-primary">Save</button><button type="button" data-action="cancel-row" class="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md transition focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed bg-white text-gray-700 border border-border hover:bg-secondaryHover focus:ring-2 focus:ring-primary">Cancel</button></div>`;
  }

  function restoreRow(row) {
    if (!row || !row.dataset.origHtml) return;
    row.innerHTML = row.dataset.origHtml;
    delete row.dataset.origHtml;
    delete row.dataset.editing;
  row.classList.remove("editing-row", "bg-yellow-50");
  if (currentEditingRow === row) currentEditingRow = null;
  }

  function saveRow(row) {
    if (!row) return;
    const itemId = row.dataset.itemId;
    const name = row.querySelector('input[name="name"]')?.value || "";
    const categoryId =
      row.querySelector('select[name="category_id"]')?.value || "";
    const unitId = row.querySelector('select[name="unit_id"]')?.value || "";
    const currentStock =
      row.querySelector('input[name="current_stock"]')?.value || "";
    const active =
      row.querySelector('input[name="is_active"]')?.checked || false;

    const fd = new FormData();
    fd.append("name", name);
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
          const stockStatusCell = row.querySelector(
            'td[data-col="stock_status"]',
          );
          if (stockStatusCell) {
            const rop = row.getAttribute("data-rop") || "";
            stockStatusCell.innerHTML = renderStockStatus(currentStock, rop);
          }
          const statusCell = row.querySelector('td[data-col="status"]');
          if (statusCell) {
            statusCell.innerHTML = active
              ? '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-success-light text-success">Active</span>'
              : '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">Inactive</span>';
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
    const csrf = getCsrfToken();
    fetch(`/items/${itemId}/delete/`, {
      method: "POST",
      headers: {
        ...(csrf ? { "X-CSRFToken": csrf } : {}),
        "X-Requested-With": "fetch",
      },
    })
      .then((r) => r.json().catch(() => ({})))
      .then((data) => {
        if (data && data.ok) {
          row.remove();
          if (window.notifications && window.notifications.showToast) {
            window.notifications.showToast(
              "Item deleted successfully!",
              "success",
            );
          }
        } else if (window.notifications && window.notifications.showToast) {
          window.notifications.showToast("Unable to delete item.", "error");
        }
      })
      .catch(() => {
        if (window.notifications && window.notifications.showToast) {
          window.notifications.showToast("Unable to delete item.", "error");
        }
      });
  }

  function archiveItem(row) {
    const itemId = row?.dataset.itemId;
    if (!itemId) return;
    // Detect current active state from status cell text
    const statusCell = row.querySelector('td[data-col="status"]');
    const currentlyActive =
      statusCell && /Active/i.test(statusCell.textContent || "");
    const csrf = getCsrfToken();
    fetch(`/items/${itemId}/toggle/`, {
      method: "POST",
      headers: {
        ...(csrf ? { "X-CSRFToken": csrf } : {}),
        "X-Requested-With": "fetch",
      },
      body: new URLSearchParams({ page: "1" }),
    })
      .then((r) => {
        if (r.ok) {
          // Persist a toast to show after reload so the user receives feedback.
          try {
            const msg = currentlyActive
              ? "Item archived"
              : "Item activated";
            localStorage.setItem(
              "items_pending_toast",
              JSON.stringify({ message: msg, type: "success" }),
            );
          } catch (e) {
            /* ignore storage errors */
          }
          window.location.reload();
        } else if (window.notifications && window.notifications.showToast) {
          window.notifications.showToast("Unable to update item.", "error");
        }
      })
      .catch(() => {
        if (window.notifications && window.notifications.showToast) {
          window.notifications.showToast("Unable to update item.", "error");
        }
      });
  }

  // Event delegation
  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-ignore-toggle]")) {
      return;
    }
    const target = e.target.closest("[data-action]");
    if (!target) return;
    const action = target.getAttribute("data-action");
    const row = findRow(target);
    if (!row) return;

    switch (action) {
      case "toggle-details":
        e.preventDefault();
        toggleDetails(row);
        break;
      case "quick-edit":
        e.preventDefault();
        if (target.closest("table")) {
          beginRowEdit(row);
        } else {
          enableInlineEdit(row);
        }
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
      case "archive":
        e.preventDefault();
        archiveItem(row);
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
      case "view":
      case "open-modal":
        e.preventDefault();
        {
          const href2 =
            target.getAttribute("data-href") || target.getAttribute("href");
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
    const table = document.getElementById("items-table");
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
    // Show any pending toast (e.g., from archive/activate action that required reload)
    try {
      const pending = localStorage.getItem("items_pending_toast");
      if (pending) {
        const data = JSON.parse(pending);
        if (
          data &&
          data.message &&
          window.notifications &&
          window.notifications.showToast
        ) {
          window.notifications.showToast(data.message, data.type || "info");
        }
        localStorage.removeItem("items_pending_toast");
      }
    } catch (e) {
      /* ignore */
    }
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

    const menuContainer = document.querySelector("[data-col-menu-container]");
    const menuBtn = document.querySelector("[data-col-menu-button]");
    const menu = document.querySelector("[data-col-menu]");
    if (menuContainer && menuBtn && menu) {
      let skipOpen = false;
      function openMenu() {
        menu.classList.remove("hidden");
        menuBtn.setAttribute("aria-expanded", "true");
        const first = menu.querySelector("input");
        if (first) first.focus();
      }
      // focusReturn determines whether focus is explicitly moved back to the button.
      // Returning focus on outside clicks was swallowing the user's next intended click
      // (e.g. on filter inputs below), making it appear those controls were unclickable.
      function closeMenu(focusReturn = true) {
        if (menuBtn.getAttribute("aria-expanded") !== "true") return;
        menu.classList.add("hidden");
        menuBtn.setAttribute("aria-expanded", "false");
        if (focusReturn) {
          skipOpen = true;
          menuBtn.focus();
          setTimeout(() => {
            skipOpen = false;
          });
        }
      }

      menuBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        const expanded = menuBtn.getAttribute("aria-expanded") === "true";
        if (expanded) closeMenu(true);
        else openMenu();
      });

      menuBtn.addEventListener("keydown", function (e) {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          if (menuBtn.getAttribute("aria-expanded") !== "true") openMenu();
          const first = menu.querySelector("input");
          if (first) first.focus();
        }
      });

      menuBtn.addEventListener("focus", () => {
        if (skipOpen || menuBtn.getAttribute("aria-expanded") === "true")
          return;
        openMenu();
      });

      menuContainer.addEventListener("focusout", (e) => {
        if (!menuContainer.contains(e.relatedTarget)) {
          // Do not force focus back to button; allow focus to proceed to the newly clicked element.
          closeMenu(false);
        }
      });

      menu.addEventListener("keydown", function (e) {
        const items = Array.from(menu.querySelectorAll("input"));
        const index = items.indexOf(document.activeElement);
        if (e.key === "Escape") {
          e.preventDefault();
          closeMenu(true);
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          const next = items[(index + 1) % items.length];
          if (next) next.focus();
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          const prev = items[(index - 1 + items.length) % items.length];
          if (prev) prev.focus();
        }
      });

      document.addEventListener("click", function (e) {
        if (!menu.contains(e.target) && e.target !== menuBtn) {
          if (menuBtn.getAttribute("aria-expanded") === "true") {
            // Outside click: close without stealing focus
            closeMenu(false);
          }
        }
      });
    }
  });

  document.addEventListener("click", function (e) {
    const btn = e.target.closest("th button[data-sort]");
    if (!btn) return;
    const th = btn.closest("th");
    const thead = th.closest("thead");
    setTimeout(() => {
      const order = btn.classList.contains("asc")
        ? "ascending"
        : btn.classList.contains("desc")
          ? "descending"
          : "none";
      thead
        .querySelectorAll("th[aria-sort]")
        .forEach((h) => h.setAttribute("aria-sort", "none"));
      th.setAttribute("aria-sort", order);
    });
  });

  function getCsrfToken() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    if (m) return decodeURIComponent(m[1]);
    const inp = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return inp ? inp.value : "";
  }

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
          <div class=\"card\" style=\"max-width:420px\">\n          <div class=\"card-header\"><strong>Deactivate ${ids.length} item(s)?</strong></div>\n          <div class=\"card-body\">\n            <p class=\"mb-3\">Items will be marked Inactive. You can reactivate later.</p>\n            <div class=\"flex\" style=\"gap:.5rem; justify-content:flex-end\">\n              <button type=\"button\" class=\"inline-flex items-center px-4 py-2 text-sm font-medium rounded-md transition focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed bg-white text-gray-700 border border-border hover:bg-secondaryHover focus:ring-2 focus:ring-primary\" data-modal-close>Cancel</button>\n              <button type=\"button\" class=\"inline-flex items-center px-4 py-2 text-sm font-medium rounded-md transition focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed bg-primary text-white hover:bg-primaryHover focus:ring-2 focus:ring-primary\" data-action=\"confirm-bulk\" data-action-type=\"deactivate\">Confirm</button>\n            </div>\n          </div>\n        </div>`;
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
          <div class=\"card\" style=\"max-width:480px\">\n          <div class=\"card-header\"><strong>Assign Department</strong></div>\n          <div class=\"card-body\">\n            <label class=\"block text-sm font-medium text-gray-700 mb-1\">Department</label>\n            ${selectHtml}\n            <div class=\"mt-3 flex\" style=\"gap:.5rem; justify-content:flex-end\">\n              <button type=\"button\" class=\"inline-flex items-center px-4 py-2 text-sm font-medium rounded-md transition focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed bg-white text-gray-700 border border-border hover:bg-secondaryHover focus:ring-2 focus:ring-primary\" data-modal-close>Cancel</button>\n              <button type=\"button\" class=\"inline-flex items-center px-4 py-2 text-sm font-medium rounded-md transition focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed bg-primary text-white hover:bg-primaryHover focus:ring-2 focus:ring-primary\" data-action=\"confirm-bulk\" data-action-type=\"assign_dept\">Assign</button>\n            </div>\n          </div>\n        </div>`;
      if (window.modal) window.modal.open(html);
    }
  });

  // Global Escape key cancels current quick edit (if any)
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && currentEditingRow) {
      restoreRow(currentEditingRow);
    }
  });
})();
