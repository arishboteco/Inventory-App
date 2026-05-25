/**
 * PO create/edit drawer and full-page form: formset add/remove, item → unit_price autofill.
 * Called from modal.js after drawer HTML is injected (inline scripts in partials do not run).
 */
(function () {
  function renumberFormsetRows(form, formsetEl, prefix) {
    const totalForms = form.querySelector(`#id_${prefix}-TOTAL_FORMS`);
    if (!totalForms) return;

    const rows = Array.from(formsetEl.querySelectorAll(".item-form"));
    let nextIndex = 0;

    rows.forEach(function (row) {
      row.querySelectorAll("input, select, textarea, label").forEach(function (el) {
        const attrName = el.getAttribute && el.getAttribute("name");
        if (attrName && attrName.indexOf(`${prefix}-`) === 0) {
          el.setAttribute(
            "name",
            attrName.replace(new RegExp(`^${prefix}-\\d+-`), `${prefix}-${nextIndex}-`),
          );
        }

        const attrId = el.getAttribute && el.getAttribute("id");
        if (attrId && attrId.indexOf(`id_${prefix}-`) === 0) {
          el.setAttribute(
            "id",
            attrId.replace(
              new RegExp(`^id_${prefix}-\\d+-`),
              `id_${prefix}-${nextIndex}-`,
            ),
          );
        }

        const attrFor = el.getAttribute && el.getAttribute("for");
        if (attrFor && attrFor.indexOf(`id_${prefix}-`) === 0) {
          el.setAttribute(
            "for",
            attrFor.replace(
              new RegExp(`^id_${prefix}-\\d+-`),
              `id_${prefix}-${nextIndex}-`,
            ),
          );
        }
      });
      nextIndex += 1;
    });

    totalForms.value = String(nextIndex);
  }

  function readItemPrices(form) {
    const el = form.querySelector("#po-item-prices");
    if (!el || !el.textContent) return {};
    try {
      return JSON.parse(el.textContent);
    } catch (_) {
      return {};
    }
  }

  function readItemVendorHints(form) {
    const el = form.querySelector("#po-item-vendor-hints");
    if (!el || !el.textContent) return {};
    try {
      return JSON.parse(el.textContent);
    } catch (_) {
      return {};
    }
  }

  function readItemLeadTimes(form) {
    const el = form.querySelector("#po-item-lead-times");
    if (!el || !el.textContent) return {};
    try {
      return JSON.parse(el.textContent);
    } catch (_) {
      return {};
    }
  }

  function parseOrderDate(value) {
    const raw = String(value || "").trim();
    let match = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (match) {
      return {
        date: new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])),
        format: "iso",
      };
    }
    match = raw.match(/^(\d{2})-(\d{2})-(\d{4})$/);
    if (match) {
      return {
        date: new Date(Number(match[3]), Number(match[2]) - 1, Number(match[1])),
        format: "dmy",
      };
    }
    return null;
  }

  function pad2(value) {
    return String(value).padStart(2, "0");
  }

  function formatDate(date, format) {
    const year = date.getFullYear();
    const month = pad2(date.getMonth() + 1);
    const day = pad2(date.getDate());
    if (format === "dmy") return `${day}-${month}-${year}`;
    return `${year}-${month}-${day}`;
  }

  function updateExpectedDeliveryDate(form, formsetEl, itemLeadTimes) {
    const orderInput = form.querySelector('[name="order_date"]');
    const expectedInput = form.querySelector('[name="expected_delivery_date"]');
    if (!orderInput || !expectedInput) return;

    const parsed = parseOrderDate(orderInput.value);
    if (!parsed) return;

    let maxLeadDays = null;
    formsetEl.querySelectorAll(".item-form").forEach(function (row) {
      if (row.style.display === "none") return;
      const deleted = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (deleted && deleted.checked) return;
      const itemSelect = row.querySelector("select.item-select");
      if (!itemSelect || !itemSelect.value) return;
      const leadDays = Number(itemLeadTimes[itemSelect.value]);
      if (!Number.isFinite(leadDays)) return;
      maxLeadDays = maxLeadDays === null ? leadDays : Math.max(maxLeadDays, leadDays);
    });

    if (maxLeadDays === null) return;
    if (expectedInput.value && expectedInput.dataset.poAutoDate !== "1") return;

    const expected = new Date(parsed.date);
    expected.setDate(expected.getDate() + maxLeadDays);
    expectedInput.value = formatDate(expected, parsed.format);
    expectedInput.dataset.poAutoDate = "1";
  }

  function applyHints(row, itemId, hints) {
    const suggestedEl = row.querySelector("[data-suggested-qty]");
    const priceHintEl = row.querySelector("[data-price-hint]");
    const hint = hints[itemId] || {};
    if (suggestedEl) {
      const qty = Number(hint.suggested_qty || 0);
      suggestedEl.textContent =
        qty > 0 ? `Suggested qty: ${qty.toFixed(2)}` : "";
    }
    if (priceHintEl) {
      const cheapest = Number(hint.cheapest_price || 0);
      const last = Number(hint.last_price || 0);
      if (cheapest > 0) {
        priceHintEl.textContent = `Cheapest vendor: ${cheapest.toFixed(2)} | Last: ${last.toFixed(2)}`;
      } else if (last > 0) {
        priceHintEl.textContent = `Last purchase: ${last.toFixed(2)}`;
      } else {
        priceHintEl.textContent = "";
      }
    }
  }

  function initPurchaseOrderDrawer(root) {
    const scope = root && root.nodeType === Node.ELEMENT_NODE ? root : document;
    const form =
      scope.querySelector("#po-drawer-form") || scope.querySelector("#po-form");
    if (!form || form._poDrawerInitialized) return;

    const formsetEl = form.querySelector("#items-formset");
    if (!formsetEl) return;

    const itemPrices = readItemPrices(form);
    const itemVendorHints = readItemVendorHints(form);
    const itemLeadTimes = readItemLeadTimes(form);
    const prefix = form.getAttribute("data-formset-prefix") || "items";

    if (!formsetEl._poDelegationBound) {
      formsetEl._poDelegationBound = true;
      formsetEl.addEventListener("click", function (e) {
        const t = e.target;
        if (!t || !t.classList || !t.classList.contains("remove-item")) return;
        const row = t.closest(".item-form");
        if (!row) return;
        const deleteInput = row.querySelector(
          'input[type="checkbox"][name$="-DELETE"]',
        );
        if (deleteInput) {
          deleteInput.checked = true;
          const rowPk = row.querySelector(
            'input[type="hidden"][name$="-id"], input[type="hidden"][name$="-po_item_id"]',
          );
          if (!rowPk || !String(rowPk.value || "").trim()) {
            row.remove();
            renumberFormsetRows(form, formsetEl, prefix);
            updateExpectedDeliveryDate(form, formsetEl, itemLeadTimes);
            return;
          }
          row.style.display = "none";
          updateExpectedDeliveryDate(form, formsetEl, itemLeadTimes);
        } else {
          row.remove();
          renumberFormsetRows(form, formsetEl, prefix);
          updateExpectedDeliveryDate(form, formsetEl, itemLeadTimes);
        }
      });

      formsetEl.addEventListener("change", function (e) {
        const t = e.target;
        if (!t || !t.classList || !t.classList.contains("item-select")) return;
        const row = t.closest(".item-form");
        if (!row) return;
        const priceInput = row.querySelector('input[name$="-unit_price"]');
        if (
          priceInput &&
          itemPrices[t.value] !== undefined &&
          itemPrices[t.value] !== null
        ) {
          priceInput.value = parseFloat(itemPrices[t.value]).toFixed(2);
        }
        applyHints(row, t.value, itemVendorHints);
        updateExpectedDeliveryDate(form, formsetEl, itemLeadTimes);
      });
    }

    const orderInput = form.querySelector('[name="order_date"]');
    const expectedInput = form.querySelector('[name="expected_delivery_date"]');
    if (orderInput && !orderInput._poLeadTimeBound) {
      orderInput._poLeadTimeBound = true;
      orderInput.addEventListener("change", function () {
        updateExpectedDeliveryDate(form, formsetEl, itemLeadTimes);
      });
    }
    if (expectedInput && !expectedInput._poLeadTimeBound) {
      expectedInput._poLeadTimeBound = true;
      expectedInput.addEventListener("input", function () {
        expectedInput.dataset.poAutoDate = "0";
      });
    }

    if (
      !form._poFormsetInitialized &&
      typeof window.initFormset === "function"
    ) {
      window.initFormset({
        formsetPrefix: prefix,
        addButtonId: "add-item",
        formContainer: "#items-formset",
        formClass: "item-form",
        templateId: "item-empty-form",
      });
      form._poFormsetInitialized = true;
    }

    formsetEl.querySelectorAll(".item-form").forEach(function (row) {
      const sel = row.querySelector("select.item-select");
      if (sel && sel.value) {
        applyHints(row, sel.value, itemVendorHints);
      }
    });
    updateExpectedDeliveryDate(form, formsetEl, itemLeadTimes);

    if (form.id === "po-form" && !form._poNativeValidityBound) {
      form._poNativeValidityBound = true;
      form.addEventListener("submit", function (e) {
        if (!form.checkValidity()) {
          e.preventDefault();
          form.reportValidity();
        }
      });
    }

    if (!form._poSubmitNormalizeBound) {
      form._poSubmitNormalizeBound = true;
      form.addEventListener("submit", function () {
        renumberFormsetRows(form, formsetEl, prefix);
      });
    }

    form._poDrawerInitialized = true;
  }

  window.initPurchaseOrderDrawer = initPurchaseOrderDrawer;

  document.addEventListener("DOMContentLoaded", function () {
    if (
      document.getElementById("po-form") &&
      (!document.getElementById("modal-root") ||
        !document
          .getElementById("modal-root")
          .contains(document.getElementById("po-form")))
    ) {
      initPurchaseOrderDrawer(document);
    }
  });
})();
