/**
 * PO create/edit drawer and full-page form: formset add/remove, item → unit_price autofill.
 * Called from modal.js after drawer HTML is injected (inline scripts in partials do not run).
 */
(function () {
  function readItemPrices(form) {
    const el = form.querySelector("#po-item-prices");
    if (!el || !el.textContent) return {};
    try {
      return JSON.parse(el.textContent);
    } catch (_) {
      return {};
    }
  }

  function initPurchaseOrderDrawer(root) {
    const scope =
      root && root.nodeType === Node.ELEMENT_NODE ? root : document;
    const form =
      scope.querySelector("#po-drawer-form") || scope.querySelector("#po-form");
    if (!form || form._poDrawerInitialized) return;

    const formsetEl = form.querySelector("#items-formset");
    if (!formsetEl) return;

    const itemPrices = readItemPrices(form);
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
          row.style.display = "none";
        } else {
          row.remove();
        }
      });

      formsetEl.addEventListener("change", function (e) {
        const t = e.target;
        if (
          !t ||
          !t.classList ||
          !t.classList.contains("item-select")
        )
          return;
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
      });
    }

    if (!form._poFormsetInitialized && typeof window.initFormset === "function") {
      window.initFormset({
        formsetPrefix: prefix,
        addButtonId: "add-item",
        formContainer: "#items-formset",
        formClass: "item-form",
        templateId: "item-empty-form",
      });
      form._poFormsetInitialized = true;
    }

    if (form.id === "po-form" && !form._poNativeValidityBound) {
      form._poNativeValidityBound = true;
      form.addEventListener("submit", function (e) {
        if (!form.checkValidity()) {
          e.preventDefault();
          form.reportValidity();
        }
      });
    }

    form._poDrawerInitialized = true;
  }

  window.initPurchaseOrderDrawer = initPurchaseOrderDrawer;

  document.addEventListener("DOMContentLoaded", function () {
    if (
      document.getElementById("po-form") &&
      (!document.getElementById("modal-root") ||
        !document.getElementById("modal-root").contains(document.getElementById("po-form")))
    ) {
      initPurchaseOrderDrawer(document);
    }
  });
})();
