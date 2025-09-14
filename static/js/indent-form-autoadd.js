/* Indent form helpers: bind auto-add of a new row when last row has item + qty */
(function () {
  const DEBUG = false;
  const log = (...a) => DEBUG && console.log("[indent-form]", ...a);

  function parseItemId(val) {
    if (!val) return null;
    const s = String(val).trim();
    const m = s.match(/^(\d+)\s*-/); // "22 - Chicken Wings"
    if (m) return m[1];
    if (/^\d+$/.test(s)) return s; // plain numeric id
    return s.length ? "_text_" : null;
  }

  function selectItemInput(row) {
    return (
      row.querySelector('input[name$="-item_display"]') ||
      row.querySelector('input[name$="-item"]') ||
      row.querySelector('input[list="item-options"]') ||
      row.querySelector('input[data-role="item"]')
    );
  }

  function selectQtyInput(row) {
    return (
      row.querySelector('input[name$="-requested_qty"]') ||
      row.querySelector('input[name$="-qty"]') ||
      row.querySelector('input[name$="-quantity"]')
    );
  }

  function rows(table) {
    return Array.from(table.querySelectorAll("tbody tr")).filter(
      (tr) => !tr.classList.contains("empty-form") && !tr.hidden,
    );
  }

  function lastRow(table) {
    const r = rows(table);
    return r[r.length - 1] || null;
  }

  function hasItemAndQty(row) {
    const itemInput = selectItemInput(row);
    const qtyInput = selectQtyInput(row);
    const itemVal = itemInput ? itemInput.value.trim() : "";
    const qtyVal = qtyInput ? parseFloat(qtyInput.value) : NaN;
    const okItem = !!parseItemId(itemVal);
    const okQty = Number.isFinite(qtyVal) && qtyVal > 0;
    return { okItem, okQty, itemVal, qtyVal };
  }

  function maybeAdd(table) {
    const lr = lastRow(table);
    if (!lr) return;

    const { okItem, okQty, itemVal, qtyVal } = hasItemAndQty(lr);
    log("maybeAdd:", { okItem, okQty, itemVal, qtyVal });

    if (okItem && okQty) {
      if (lr.dataset.autoAddDone === "1") return;
      lr.dataset.autoAddDone = "1";
      const addBtn = document.getElementById("add-row");
      if (addBtn) addBtn.click();

      // bind the new last row on next tick
      setTimeout(() => {
        const nr = lastRow(table);
        if (nr) bindRow(nr, table);
      }, 0);
    } else {
      lr.dataset.autoAddDone = "0";
    }
  }

  function bindRow(row, table) {
    if (row._indentAutoAddBound) return;
    row._indentAutoAddBound = true;

    const itemInput = selectItemInput(row);
    const qtyInput = selectQtyInput(row);

    const handler = () => maybeAdd(table);
    if (itemInput) {
      itemInput.addEventListener("input", handler);
      itemInput.addEventListener("change", handler);
      itemInput.addEventListener("blur", handler);
    }
    if (qtyInput) {
      qtyInput.addEventListener("input", handler);
      qtyInput.addEventListener("change", handler);
      qtyInput.addEventListener("blur", handler);
    }
  }

  function initIndentFormAutoAdd(root) {
    const scope = root || document;
    const table = scope.querySelector("#items-table");
    if (!table || table._indentAutoAddInit) return;
    table._indentAutoAddInit = true;

    // Bind existing rows
    rows(table).forEach((r) => bindRow(r, table));

    // Observe future rows (formset adds)
    const tbody = table.querySelector("tbody");
    if (tbody && !tbody._indentAutoAddObserver) {
      const obs = new MutationObserver((mutations) => {
        mutations.forEach((m) => {
          m.addedNodes.forEach((n) => {
            if (n.nodeType === 1 && n.matches("tr")) bindRow(n, table);
          });
        });
      });
      obs.observe(tbody, { childList: true });
      tbody._indentAutoAddObserver = obs;
    }

    // After clicking "Add Item", bind the new row
    const addBtn = document.getElementById("add-row");
    if (addBtn && !addBtn._indentAutoAddBound) {
      addBtn.addEventListener("click", () => {
        setTimeout(() => {
          const nr = lastRow(table);
          if (nr) bindRow(nr, table);
        }, 0);
      });
      addBtn._indentAutoAddBound = true;
    }
  }

  window.initIndentFormAutoAdd = initIndentFormAutoAdd;
})();
