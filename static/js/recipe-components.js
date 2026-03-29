/**
 * Recipe drawer helpers for managing the ingredient formset.
 * Handles cloning rows, fetching item metadata, grouping rows by
 * category, and updating the cost summary panel.
 */
(function () {
  "use strict";

  function toNumber(value) {
    var num = parseFloat(value);
    return Number.isFinite(num) ? num : 0;
  }

  function slugifyCategoryLabel(label) {
    return (
      String(label || "uncategorized")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "") || "uncategorized"
    );
  }

  function clampMarginValue(raw) {
    if (!Number.isFinite(raw)) {
      return 0;
    }
    if (raw < 0) {
      return 0;
    }
    if (raw > 95) {
      return 95;
    }
    return raw;
  }

  function parseLineCost(el) {
    if (!el) {
      return 0;
    }
    var text = String(el.textContent || "").replace(/[^0-9.-]/g, "");
    var value = parseFloat(text);
    return Number.isFinite(value) ? value : 0;
  }

  function getGroupColspan(table) {
    if (!table) {
      return 1;
    }
    if (table.tHead && table.tHead.rows.length) {
      return table.tHead.rows[0].cells.length || 1;
    }
    var firstBodyRow = table.querySelector("tbody tr");
    return firstBodyRow ? firstBodyRow.cells.length || 1 : 1;
  }

  function updateRowCost(row, options) {
    options = options || {};
    var scope =
      options.scope ||
      row.closest(".drawer-panel") ||
      row.closest("[data-modal-root]") ||
      document;
    var quantityInput = row.querySelector('input[id$="-quantity"]');
    var quantity = quantityInput
      ? toNumber(quantityInput.value)
      : toNumber(row.dataset.quantity);
    row.dataset.quantity = String(quantity);

    var costPerBase =
      typeof options.costPerBaseUnit === "number"
        ? options.costPerBaseUnit
        : toNumber(row.dataset.costPerBaseUnit);
    if (!Number.isFinite(costPerBase)) {
      costPerBase = 0;
    }
    row.dataset.costPerBaseUnit = String(costPerBase);

    var costElement = row.querySelector("[data-line-cost]");
    if (costElement) {
      // Apply loss %: effective_qty = qty / (1 - loss_pct/100)
      var lossPctInput = row.querySelector('input[id$="-loss_pct"]');
      var lossPct = lossPctInput ? toNumber(lossPctInput.value) : 0;
      var effectiveQty = quantity;
      if (lossPct > 0 && lossPct < 100) {
        effectiveQty = quantity / (1 - lossPct / 100);
      }
      var lineCost = effectiveQty * costPerBase;
      costElement.textContent = lineCost.toFixed(2);
    }

    var hasItem = row.dataset.hasItem === "1";
    if (!hasItem) {
      var select = row.querySelector('select[id$="-ingredient"]');
      hasItem = !!(select && select.value);
    }
    var hasZeroPrice = hasItem && quantity > 0 && costPerBase === 0;
    row.dataset.hasZeroPrice = hasZeroPrice ? "1" : "0";

    if (!options.silent && typeof window.updateRecipeCosts === "function") {
      window.updateRecipeCosts(scope);
    }
  }

  function parseIngredientValue(value) {
    if (!value || typeof value !== "string") {
      return null;
    }
    if (value.indexOf("i:") === 0) {
      return { kind: "item", id: value.slice(2) };
    }
    if (value.indexOf("r:") === 0) {
      return { kind: "sub", id: value.slice(2) };
    }
    return null;
  }

  function applyIngredientMeta(row, ingredientSelect, scope, data) {
    var baseId = ingredientSelect.id.replace(/-ingredient$/, "");
    var unitHidden = document.getElementById(baseId + "-unit");
    var unitDisplay = document.getElementById(baseId + "-unit_display");
    if (!data || !data.ok) {
      return;
    }
    var baseUnitValue = data.base_unit;
    if (!baseUnitValue || !String(baseUnitValue).trim()) {
      baseUnitValue = data.unit;
    }
    var resolvedUnit = baseUnitValue ? String(baseUnitValue).trim() : "";
    if (unitHidden) {
      unitHidden.value = resolvedUnit;
    }
    if (unitDisplay) {
      unitDisplay.value = resolvedUnit;
    }
    row.dataset.category = (data.category || "").trim();
    row.dataset.subcategory = (data.subcategory || "").trim();
    row.dataset.itemName = (data.name || "").trim();

    var costPerBaseUnit = toNumber(data.cost_per_base_unit);
    if (!costPerBaseUnit && data.last_purchase_price !== undefined) {
      var lastPrice = toNumber(data.last_purchase_price);
      var conversion = toNumber(data.conversion_factor) || 1;
      costPerBaseUnit = conversion ? lastPrice / conversion : 0;
    }
    if (!Number.isFinite(costPerBaseUnit) || costPerBaseUnit < 0) {
      costPerBaseUnit = 0;
    }
    row.dataset.costPerBaseUnit = String(costPerBaseUnit);
    row.dataset.hasZeroPrice = costPerBaseUnit === 0 ? "1" : "0";

    updateRowCost(row, { scope: scope });
  }

  function handleIngredientChange(row, ingredientSelect, scope) {
    var value = ingredientSelect.value;
    row.dataset.hasItem = value ? "1" : "0";

    var baseId = ingredientSelect.id.replace(/-ingredient$/, "");
    var unitHidden = document.getElementById(baseId + "-unit");
    var unitDisplay = document.getElementById(baseId + "-unit_display");

    if (!value) {
      if (unitHidden) {
        unitHidden.value = "";
      }
      if (unitDisplay) {
        unitDisplay.value = "";
      }
      row.dataset.category = "";
      row.dataset.subcategory = "";
      row.dataset.itemName = "";
      row.dataset.costPerBaseUnit = "0";
      row.dataset.hasZeroPrice = "0";
      updateRowCost(row, { scope: scope });
      return;
    }

    var parsed = parseIngredientValue(value);
    if (!parsed || !parsed.id) {
      row.dataset.category = "";
      row.dataset.subcategory = "";
      row.dataset.itemName = "";
      row.dataset.costPerBaseUnit = "0";
      updateRowCost(row, { scope: scope });
      return;
    }

    if (ingredientSelect.dataset.recipeFetching === "1") {
      return;
    }
    ingredientSelect.dataset.recipeFetching = "1";

    var url =
      parsed.kind === "sub"
        ? "/recipes/meta/" + encodeURIComponent(parsed.id) + "/"
        : "/items/meta/" + encodeURIComponent(parsed.id) + "/";

    fetch(url)
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Failed to fetch ingredient metadata");
        }
        return response.json();
      })
      .then(function (data) {
        applyIngredientMeta(row, ingredientSelect, scope, data);
      })
      .catch(function (err) {
        console.error("Unable to fetch ingredient metadata", err);
      })
      .finally(function () {
        delete ingredientSelect.dataset.recipeFetching;
      });
  }

  function bindRowEvents(row, scope) {
    if (row.dataset.recipeEventsBound === "1") {
      return;
    }
    row.dataset.recipeEventsBound = "1";

    var ingredientSelect = row.querySelector('select[id$="-ingredient"]');
    if (ingredientSelect) {
      ingredientSelect.addEventListener("change", function () {
        row.dataset.recipeBootstrapped = "1";
        handleIngredientChange(row, ingredientSelect, scope);
      });
    }

    var quantityInput = row.querySelector('input[id$="-quantity"]');
    if (quantityInput) {
      ["input", "change", "blur"].forEach(function (evt) {
        quantityInput.addEventListener(evt, function () {
          updateRowCost(row, { scope: scope });
        });
      });
    }

    var removeBtn = row.querySelector(".remove-row");
    if (removeBtn) {
      removeBtn.addEventListener("click", function (e) {
        e.preventDefault();
        var deleteField = row.querySelector('input[id$="-DELETE"]');
        if (deleteField) {
          deleteField.checked = true;
        }
        row.classList.add("hidden");
        row.dataset.hasItem = "0";
        row.dataset.costPerBaseUnit = "0";
        row.dataset.quantity = "0";
        row.dataset.hasZeroPrice = "0";
        updateRowCost(row, { scope: scope });
      });
    }

    if (
      typeof window.initPredictiveDropdowns === "function" &&
      !row.dataset.predictiveInit
    ) {
      window.initPredictiveDropdowns(row);
      row.dataset.predictiveInit = "1";
    }
  }

  function bootstrapRow(row, scope) {
    if (row.dataset.recipeBootstrapped === "1") {
      updateRowCost(row, { scope: scope, silent: true });
      return;
    }
    var ingredientSelect = row.querySelector('select[id$="-ingredient"]');
    if (ingredientSelect && ingredientSelect.value) {
      row.dataset.recipeBootstrapped = "1";
      handleIngredientChange(row, ingredientSelect, scope);
    } else {
      updateRowCost(row, { scope: scope, silent: true });
    }
  }

  function addRow(tbody, totalForms, emptyRow, scope) {
    if (!tbody || !totalForms || !emptyRow) {
      return;
    }
    var index = parseInt(totalForms.value, 10) || 0;
    totalForms.value = index + 1;

    var clone = emptyRow.cloneNode(true);
    clone.id = "";
    clone.classList.remove("hidden");
    clone.dataset.formIndex = String(index);
    clone.dataset.hasItem = "0";
    clone.dataset.quantity = "0";
    clone.dataset.costPerBaseUnit = "0";
    clone.dataset.hasZeroPrice = "0";

    clone.querySelectorAll("[name]").forEach(function (field) {
      if (field.name) {
        field.name = field.name.replace(/__prefix__/g, index);
      }
      if (field.id) {
        field.id = field.id.replace(/__prefix__/g, index);
      }
      if (field.type === "checkbox") {
        field.checked = false;
      } else if (field.type !== "hidden") {
        if (field.tagName === "SELECT") {
          field.selectedIndex = 0;
        } else {
          field.value = "";
        }
      }
    });

    clone.querySelectorAll("label[for]").forEach(function (label) {
      label.htmlFor = label.htmlFor.replace(/__prefix__/g, index);
    });

    var costEl = clone.querySelector("[data-line-cost]");
    if (costEl) {
      costEl.textContent = "0.00";
    }

    if (emptyRow.parentNode === tbody) {
      tbody.insertBefore(clone, emptyRow);
    } else {
      tbody.appendChild(clone);
    }

    clone.removeAttribute("data-recipe-events-bound");
    clone.removeAttribute("data-recipe-bootstrapped");
    clone.removeAttribute("data-predictive-init");
    delete clone.dataset.recipeEventsBound;
    delete clone.dataset.recipeBootstrapped;
    delete clone.dataset.predictiveInit;

    bindRowEvents(clone, scope);
    updateRowCost(clone, { scope: scope });
  }

  function updateRecipeCosts(root) {
    var scope = root || document;
    var table = scope.querySelector("#items-table");
    if (!table) {
      return;
    }
    var tbody = table.querySelector("tbody");
    if (!tbody) {
      return;
    }

    var activeElement = document.activeElement;
    var shouldRestoreFocus = Boolean(
      activeElement && table.contains(activeElement),
    );
    var selectionStart = null;
    var selectionEnd = null;
    var selectionDirection = null;
    var hasSelection = false;
    if (shouldRestoreFocus) {
      try {
        selectionStart = activeElement.selectionStart;
        selectionEnd = activeElement.selectionEnd;
        if (
          typeof selectionStart === "number" &&
          typeof selectionEnd === "number"
        ) {
          hasSelection = true;
          selectionDirection = activeElement.selectionDirection || null;
        }
      } catch (_) {
        hasSelection = false;
      }
    }

    var hiddenTemplate = scope.querySelector("#items-empty-row");
    if (hiddenTemplate && hiddenTemplate.parentNode === tbody) {
      tbody.removeChild(hiddenTemplate);
    }

    Array.from(tbody.querySelectorAll("tr[data-category-heading]")).forEach(
      function (row) {
        row.remove();
      },
    );

    var rows = Array.from(tbody.querySelectorAll("tr.form-row"));
    var groups = [];
    var groupMap = Object.create(null);
    var totalCost = 0;
    var hasZeroCostRows = false;

    rows.forEach(function (row) {
      if (row === hiddenTemplate) {
        return;
      }
      if (row.classList.contains("hidden")) {
        return;
      }
      var deleteField = row.querySelector('input[id$="-DELETE"]');
      if (deleteField && deleteField.checked) {
        return;
      }

      var category = (row.dataset.category || "").trim();
      if (!category) {
        category = "Uncategorized";
      }
      var key = category.toLowerCase() || "uncategorized";
      var group = groupMap[key];
      if (!group) {
        group = { key: key, label: category, rows: [], total: 0 };
        groupMap[key] = group;
        groups.push(group);
      }

      var lineCost = parseLineCost(row.querySelector("[data-line-cost]"));
      totalCost += lineCost;
      group.total += lineCost;
      group.rows.push(row);

      var hasItem = row.dataset.hasItem === "1";
      if (!hasItem) {
        var select = row.querySelector('select[id$="-ingredient"]');
        hasItem = !!(select && select.value);
      }
      var quantityValue = toNumber(row.dataset.quantity);
      if (!quantityValue) {
        var qtyInput = row.querySelector('input[id$="-quantity"]');
        quantityValue = toNumber(qtyInput ? qtyInput.value : 0);
      }
      var baseCostValue = toNumber(row.dataset.costPerBaseUnit);
      if (
        row.dataset.hasZeroPrice === "1" ||
        (hasItem && quantityValue > 0 && baseCostValue === 0)
      ) {
        hasZeroCostRows = true;
      }
    });

    groups.sort(function (a, b) {
      if (a.label === b.label) {
        return 0;
      }
      if (a.label === "Uncategorized") {
        return 1;
      }
      if (b.label === "Uncategorized") {
        return -1;
      }
      return a.label.localeCompare(b.label);
    });

    var fragment = document.createDocumentFragment();
    var colspan = getGroupColspan(table);

    groups.forEach(function (group, idx) {
      var headingRow = document.createElement("tr");
      headingRow.setAttribute("data-category-heading", "1");
      var headingCell = document.createElement("th");
      headingCell.setAttribute("scope", "colgroup");
      headingCell.colSpan = colspan;
      headingCell.id =
        "recipe-category-" + slugifyCategoryLabel(group.label) + "-" + idx;
      headingCell.className =
        "px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-600 bg-surfaceSubtle";
      headingCell.textContent = group.label;
      headingRow.appendChild(headingCell);
      fragment.appendChild(headingRow);
      group.headingId = headingCell.id;
      group.rows.forEach(function (row) {
        row.setAttribute("aria-labelledby", headingCell.id);
        fragment.appendChild(row);
      });
    });

    if (fragment.childNodes.length) {
      tbody.appendChild(fragment);
    }
    if (hiddenTemplate) {
      tbody.appendChild(hiddenTemplate);
    }

    var costContainer = scope.querySelector("#cost-by-category");
    if (costContainer) {
      while (costContainer.firstChild) {
        costContainer.removeChild(costContainer.firstChild);
      }
      if (!groups.length) {
        var emptyMessage = document.createElement("p");
        emptyMessage.className = "text-sm text-gray-500";
        emptyMessage.textContent = "Add items to see category totals.";
        costContainer.appendChild(emptyMessage);
      } else {
        groups.forEach(function (group) {
          var summaryRow = document.createElement("div");
          summaryRow.className = "flex items-center justify-between gap-2";
          summaryRow.setAttribute("role", "group");
          if (group.headingId) {
            summaryRow.setAttribute("aria-labelledby", group.headingId);
          }
          var label = document.createElement("span");
          label.className = "text-gray-600";
          label.textContent = group.label;
          var value = document.createElement("span");
          value.className = "font-medium text-bodyText";
          value.textContent = group.total.toFixed(2);
          summaryRow.appendChild(label);
          summaryRow.appendChild(value);
          costContainer.appendChild(summaryRow);
        });
      }
    }

    var zeroNotice = scope.querySelector("#recipe-zero-cost-notice");
    if (zeroNotice) {
      if (hasZeroCostRows) {
        zeroNotice.classList.remove("hidden");
      } else {
        zeroNotice.classList.add("hidden");
      }
    }

    var totalCostEl = scope.querySelector("#recipe-total-cost");
    if (totalCostEl) {
      totalCostEl.textContent = totalCost.toFixed(2);
    }

    var marginInput = scope.querySelector("#recipe-margin");
    if (marginInput && !marginInput.dataset.recipeMarginBound) {
      var marginHandler = function () {
        window.updateRecipeCosts(scope);
      };
      marginInput.addEventListener("input", marginHandler);
      marginInput.addEventListener("change", marginHandler);
      marginInput.dataset.recipeMarginBound = "1";
    }

    var marginValue = marginInput ? toNumber(marginInput.value) : 0;
    var clampedMargin = clampMarginValue(marginValue);
    if (marginInput && marginValue !== clampedMargin) {
      marginInput.value = clampedMargin;
    }
    var marginDecimal = clampedMargin / 100;
    var suggestedPrice = totalCost;
    if (marginDecimal > 0 && marginDecimal < 0.999) {
      suggestedPrice = totalCost / (1 - marginDecimal);
    }

    var suggestedEl = scope.querySelector("#recipe-suggested-price");
    if (suggestedEl) {
      suggestedEl.textContent = Number.isFinite(suggestedPrice)
        ? suggestedPrice.toFixed(2)
        : totalCost.toFixed(2);
    }

    if (shouldRestoreFocus && activeElement) {
      var isConnected =
        typeof activeElement.isConnected === "boolean"
          ? activeElement.isConnected
          : document.contains(activeElement);
      if (isConnected && typeof activeElement.focus === "function") {
        try {
          activeElement.focus({ preventScroll: true });
        } catch (_) {}
        if (
          hasSelection &&
          typeof activeElement.setSelectionRange === "function"
        ) {
          try {
            if (selectionDirection) {
              activeElement.setSelectionRange(
                selectionStart,
                selectionEnd,
                selectionDirection,
              );
            } else {
              activeElement.setSelectionRange(selectionStart, selectionEnd);
            }
          } catch (_) {}
        }
      }
    }
  }

  function initRecipeComponentsTable(root, tableId) {
    var scope = root || document;
    var id = tableId || "items-table";
    var selector = "#" + CSS.escape(id);
    var table = scope.querySelector(selector);
    if (!table) {
      return;
    }
    if (table.dataset.recipeInitialized === "1") {
      return;
    }

    var tbody = table.querySelector("tbody");
    if (!tbody) {
      return;
    }

    table.dataset.recipeInitialized = "1";

    var totalForms = scope.querySelector("#id_items-TOTAL_FORMS");
    var emptyRow = scope.querySelector("#items-empty-row");

    var existingRows = Array.from(tbody.querySelectorAll("tr.form-row"));
    var rowsToInitialize = existingRows.filter(function (row) {
      if (row === emptyRow) {
        return false;
      }
      if (row && row.id === "items-empty-row") {
        return false;
      }
      return true;
    });
    rowsToInitialize.forEach(function (row) {
      bindRowEvents(row, scope);
    });
    rowsToInitialize.forEach(function (row) {
      bootstrapRow(row, scope);
    });

    var addBtn = scope.querySelector("#add-row");
    if (addBtn && !addBtn.dataset.recipeAddBound) {
      addBtn.dataset.recipeAddBound = "1";
      addBtn.addEventListener("click", function (e) {
        e.preventDefault();
        addRow(tbody, totalForms, emptyRow, scope);
      });
    }

    var modalRoot = table.closest("[data-modal-root], .drawer-panel");
    if (modalRoot) {
      var resetHandler = function () {
        delete table.dataset.recipeInitialized;
      };
      modalRoot.addEventListener("modal:close", resetHandler, { once: true });
      var closeBtn = modalRoot.querySelector("[data-modal-close]");
      if (closeBtn) {
        closeBtn.addEventListener("click", resetHandler, { once: true });
      }
    }

    updateRecipeCosts(scope);
  }

  window.initRecipeComponentsTable = initRecipeComponentsTable;
  window.initRecipeItemsTable = initRecipeComponentsTable;
  window.updateRecipeCosts = updateRecipeCosts;
})();
