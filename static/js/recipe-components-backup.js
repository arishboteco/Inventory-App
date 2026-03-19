/**
 * Recipe Items Table - Interactive formset management
 * Simplified from components to direct item selection
 */
(function () {
  "use strict";

  console.log("🔥 Loading recipe-components.js 🔥");

  // Immediate test - add this to see if the script loads at all
  window.DEBUG_RECIPE_JS_LOADED = true;

  // Enhanced debugging info at the top level
  console.log("🔍 Recipe Components Debug Info:", {
    location: window.location.href,
    readyState: document.readyState,
    allTables: document.querySelectorAll("table").length,
    allButtons: document.querySelectorAll("button").length,
    itemsTable: !!document.getElementById("items-table"),
    addButton: !!document.getElementById("add-row"),
    initPredictiveDropdowns: typeof window.initPredictiveDropdowns,
    predictiveDropdownsAvailable: !!window.initPredictiveDropdowns,
  });

  function initRecipeComponentsTable(root, tableId) {
    console.log("🚀 === INITIALIZING RECIPE COMPONENTS TABLE === 🚀");
    console.log("Root element:", root);
    console.log("Table ID:", tableId);

    root = root || document;
    tableId = tableId || "items-table";

    // Find the table - try multiple methods
    var table = document.getElementById(tableId);
    if (!table) {
      console.log(
        "⚠️ Table not found with getElementById, trying querySelector...",
      );
      table = document.querySelector("#" + tableId);
    }
    if (!table) {
      console.log(
        "⚠️ Table not found with querySelector, searching all tables...",
      );
      var tables = document.querySelectorAll("table");
      console.log(
        "Found tables:",
        Array.from(tables).map((t) => ({ id: t.id, classes: t.className })),
      );

      // Look for table with recipe-related content
      for (var i = 0; i < tables.length; i++) {
        var t = tables[i];
        if (
          t.querySelector("tbody") &&
          (t.id === tableId ||
            t.id.includes("table") ||
            t.querySelector('[id*="item"]'))
        ) {
          console.log("✅ Using table as fallback:", t.id || "no-id");
          table = t;
          break;
        }
      }
    }

    if (!table) {
      console.error(
        "❌ No items table found yet. This means the table HTML has not loaded.",
      );
      console.log("Available elements:", {
        allTables: document.querySelectorAll("table").length,
        allDivs: document.querySelectorAll('div[id*="item"]').length,
        formElements: document.querySelectorAll('input[name*="item"]').length,
      });
      return;
    }

    console.log("✅ Found table:", table.id);

    var tbody = table.querySelector("tbody");
    if (!tbody) {
      console.error("❌ Table has no tbody");
      return;
    }

    // Find form management elements
    var totalForms = document.getElementById("id_items-TOTAL_FORMS");
    var emptyRow = document.getElementById("items-empty-row");

    console.log("Form elements:", {
      totalForms: !!totalForms,
      emptyRow: !!emptyRow,
      totalFormsValue: totalForms ? totalForms.value : "N/A",
    });

    if (!totalForms || !emptyRow) {
      console.error("❌ Missing form management elements. Available elements:");
      console.log(
        "- All form inputs:",
        document.querySelectorAll('input[id*="TOTAL_FORMS"]'),
      );
      console.log("- All hidden rows:", document.querySelectorAll("tr.hidden"));
      return;
    }

    // Bind existing rows
    var existingRows = tbody.querySelectorAll("tr.form-row:not(.hidden)");
    console.log("Found existing rows:", existingRows.length);

    // Initialize predictive dropdowns for existing rows
    if (window.initPredictiveDropdowns && existingRows.length > 0) {
      console.log("🔍 Initializing predictive dropdowns for existing rows...");
      existingRows.forEach(function (row) {
        window.initPredictiveDropdowns(row);
      });
    }

    existingRows.forEach(function (row) {
      bindRowEvents(row);
    });

    // Find and setup add button
    var addBtn = document.getElementById("add-row");
    if (!addBtn) {
      console.log("⚠️ Add button not found with getElementById, searching...");
      addBtn = document.querySelector("#add-row");
    }
    if (!addBtn) {
      addBtn = document.querySelector('button[id*="add"]');
      if (addBtn) console.log("Found alternative add button:", addBtn.id);
    }

    if (addBtn) {
      console.log("✅ Setting up Add Item button");

      // Clear any existing event listeners
      var newBtn = addBtn.cloneNode(true);
      addBtn.parentNode.replaceChild(newBtn, addBtn);
      addBtn = newBtn;

      // Visual debugging
      addBtn.style.backgroundColor = "green";
      addBtn.style.color = "white";
      addBtn.title = "Ready to add items!";

      addBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        console.log("� === ADD ITEM CLICKED === 🔥");

        try {
          addNewRow(table, tbody, totalForms, emptyRow);
        } catch (error) {
          console.error("❌ Error adding row:", error);
        }
      });

      console.log("✅ Add button setup complete");
    } else {
      console.error("❌ Add Item button not found!");
    }
  }

  function addNewRow(table, tbody, totalForms, emptyRow) {
    console.log("🔧 Adding new row...");

    var index = parseInt(totalForms.value, 10) || 0;
    console.log("Current form count:", index);

    // Clone the empty row
    var newRow = emptyRow.cloneNode(true);

    // Replace the prefix in all form elements
    var inputs = newRow.querySelectorAll("input, select, textarea");
    inputs.forEach(function (input) {
      if (input.name) {
        input.name = input.name.replace("__prefix__", index);
      }
      if (input.id) {
        input.id = input.id.replace("__prefix__", index);
      }

      // Clear values for new row (except hidden fields)
      if (input.type !== "hidden") {
        if (input.tagName === "SELECT") {
          input.selectedIndex = 0; // Reset to first option (usually empty)
          // Ensure the select has the predictive class
          if (input.id && input.id.endsWith("-item")) {
            if (!input.classList.contains("predictive")) {
              input.classList.add("predictive");
              console.log("🔧 Added predictive class to:", input.id);
            }
          }
        } else {
          input.value = "";
        }
      }
    });

    // Replace prefix in labels
    var labels = newRow.querySelectorAll("label");
    labels.forEach(function (label) {
      if (label.htmlFor) {
        label.htmlFor = label.htmlFor.replace("__prefix__", index);
      }
    });

    // Clear the ID and make visible
    newRow.id = "";
    newRow.classList.remove("hidden");
    tbody.appendChild(newRow);
    totalForms.value = index + 1;

    console.log("🔧 Initializing new row...");

    // Use setTimeout to ensure DOM is updated before initializing dropdowns
    setTimeout(function () {
      console.log("🔧 Starting dropdown initialization for new row...");

      // Find the item select in the new row
      var itemSelect = newRow.querySelector('select[id$="-item"]');
      if (itemSelect) {
        console.log("🔍 Found item select:", itemSelect.id);

        // Ensure it has the predictive class and proper setup
        if (!itemSelect.classList.contains("predictive")) {
          itemSelect.classList.add("predictive");
          console.log("✅ Added predictive class");
        }

        // Remove any existing upgrade flag to force re-initialization
        delete itemSelect.dataset.predictiveUpgraded;

        console.log("🔍 Item select state before initialization:", {
          id: itemSelect.id,
          hasPredictiveClass: itemSelect.classList.contains("predictive"),
          isUpgraded: itemSelect.dataset.predictiveUpgraded,
          optionsCount: itemSelect.options.length,
        });
      }

      // Check if initPredictiveDropdowns is available
      console.log(
        "🔍 initPredictiveDropdowns available:",
        typeof window.initPredictiveDropdowns,
      );

      // Initialize predictive dropdowns for the new row
      if (window.initPredictiveDropdowns) {
        console.log("🔍 Calling initPredictiveDropdowns for new row...");
        try {
          window.initPredictiveDropdowns(newRow);
          console.log(
            "✅ initPredictiveDropdowns called successfully for new row",
          );
        } catch (error) {
          console.error("❌ Error calling initPredictiveDropdowns:", error);
        }

        // Wait a bit then check if it worked
        setTimeout(function () {
          if (itemSelect) {
            console.log("🔍 Item select state after initialization:", {
              id: itemSelect.id,
              isUpgraded: itemSelect.dataset.predictiveUpgraded,
              hasTextInput: !!document.getElementById(itemSelect.id + "_text"),
              isVisible: itemSelect.offsetParent !== null,
            });

            // If still not upgraded, try global initialization
            if (!itemSelect.dataset.predictiveUpgraded) {
              console.log("� Trying global initialization...");
              window.initPredictiveDropdowns(document);
            }
          }
        }, 50);
      } else {
        console.warn("⚠️ initPredictiveDropdowns not available");
      }

      // Bind events for the new row
      setTimeout(function () {
        bindRowEvents(newRow);
      }, 200);
    }, 10);

    console.log(
      "✅ Row added and scheduled for initialization! New count:",
      totalForms.value,
    );
  }

  function bindRowEvents(row) {
    console.log("🔗 Binding events for row:", row);

    // Find item selector - look for select with pattern ending in "-item"
    var itemSelect = row.querySelector('select[id$="-item"]');
    if (itemSelect) {
      console.log("✅ Binding change event to item selector:", itemSelect.id);

      // Bind to the original select element
      itemSelect.addEventListener("change", function () {
        var val = itemSelect.value;
        console.log("🔄 Item changed to:", val);

        if (!val) {
          handleItemChange(itemSelect, null);
          return;
        }

        handleItemChange(itemSelect, val);
      });

      // Also bind to the predictive dropdown text input if it exists
      var predictiveTextInput = row.querySelector('input[id$="-item_text"]');
      if (predictiveTextInput) {
        console.log(
          "✅ Also binding to predictive text input:",
          predictiveTextInput.id,
        );
        predictiveTextInput.addEventListener("input", function () {
          // The predictive dropdown should update the original select, which will trigger our change event
          console.log(
            "🔄 Predictive input changed:",
            predictiveTextInput.value,
          );
        });
      }

      // Use a more aggressive approach to detect predictive dropdown creation
      var checkForPredictiveInput = function () {
        var textInput = row.querySelector('input[id$="-item_text"]');
        if (textInput && !textInput._eventsBound) {
          console.log("🔍 Predictive text input detected, binding events");
          textInput._eventsBound = true;
          textInput.addEventListener("input", function () {
            console.log("🔄 Predictive input changed:", textInput.value);
          });
        } else if (!textInput) {
          // Keep checking for a bit
          setTimeout(checkForPredictiveInput, 100);
        }
      };

      // Start checking immediately and after a short delay
      setTimeout(checkForPredictiveInput, 10);
      setTimeout(checkForPredictiveInput, 100);
      setTimeout(checkForPredictiveInput, 500);
    } else {
      console.error("❌ Item select not found in row");
    }

    // Also bind to remove button
    var removeBtn = row.querySelector(".remove-row");
    if (removeBtn) {
      removeBtn.addEventListener("click", function (e) {
        e.preventDefault();
        console.log("🗑️ Remove button clicked");
        row.remove();
        // Note: In a real formset, you'd need to handle the DELETE field properly
      });
    }
  }

  function handleItemChange(itemSelect, val) {
    console.log("🔄 Handling item change for:", itemSelect.id, "value:", val);

    // Find unit fields for this row - the formset uses patterns like id_items-0-item, id_items-0-unit, etc.
    var baseId = itemSelect.id.replace("-item", "");
    var unitHidden = document.getElementById(baseId + "-unit");
    var unitDisplay = document.getElementById(baseId + "-unit_display");

    console.log("Unit fields lookup:", {
      baseId: baseId,
      searching_for_hidden: baseId + "-unit",
      searching_for_display: baseId + "-unit_display",
      hidden_found: !!unitHidden,
      display_found: !!unitDisplay,
      hiddenId: unitHidden ? unitHidden.id : "not found",
      displayId: unitDisplay ? unitDisplay.id : "not found",
    });

    // Debug: List all input fields in the row to see what's actually available
    var row = itemSelect.closest("tr");
    if (row) {
      var allInputs = row.querySelectorAll("input, select");
      console.log(
        "All inputs in row:",
        Array.from(allInputs).map(function (inp) {
          return { id: inp.id, name: inp.name, type: inp.type };
        }),
      );
    }

    // If no item selected, clear unit fields
    if (!val) {
      if (unitHidden) {
        unitHidden.value = "";
        console.log("✅ Cleared unit hidden field");
      }
      if (unitDisplay) {
        unitDisplay.value = "";
        console.log("✅ Cleared unit display field");
      }
      updateRowCost(itemSelect, null);
      return;
    }

    // Fetch item metadata using the item's primary key
    console.log("🌐 Fetching item meta for ID:", val);
    fetch("/items/meta/" + val + "/")
      .then(function (r) {
        console.log("📡 Item meta fetch status:", r.status);
        if (!r.ok) {
          throw new Error("Failed to fetch item meta: " + r.status);
        }
        return r.json();
      })
      .then(function (data) {
        console.log("📦 Item data received:", data);
        if (data && data.ok) {
          // Update unit fields - the hidden field stores the purchase unit, display shows the base unit
          if (unitHidden) {
            unitHidden.value = data.unit || "";
            console.log("✅ Set unit hidden field to:", data.unit);
          }
          if (unitDisplay) {
            unitDisplay.value = data.base_unit || data.unit || "";
            console.log(
              "✅ Set unit display field to:",
              data.base_unit || data.unit,
            );
          }

          // Update cost
          updateRowCost(itemSelect, data);
        } else {
          console.error("❌ Invalid item data received:", data);
        }
      })
      .catch(function (err) {
        console.error("❌ Failed to fetch item meta:", err);
      });
  }

  function updateRowCost(itemSelect, itemData) {
    console.log("💰 Updating row cost...");

    if (!itemData || !itemData.last_purchase_price) {
      console.log("⚠️ No cost data available");
      return;
    }

    // Find the cost display element for this row
    var row = itemSelect.closest("tr");
    var costElement = row ? row.querySelector("[data-line-cost]") : null;

    if (costElement) {
      // Get quantity to calculate line cost - use the same base ID pattern
      var baseId = itemSelect.id.replace("-item", "");
      var quantityInput = document.getElementById(baseId + "-quantity");
      var quantity = quantityInput ? parseFloat(quantityInput.value) || 0 : 0;

      var unitCost = parseFloat(itemData.last_purchase_price) || 0;
      var lineCost = quantity * unitCost;

      costElement.textContent = lineCost.toFixed(2);
      console.log("✅ Updated line cost to:", lineCost.toFixed(2));

      // Trigger recipe cost recalculation if available
      if (window.updateRecipeCosts) {
        setTimeout(window.updateRecipeCosts, 100);
      }
    }
  }

  // Expose globally with the correct name for modal.js
  window.initRecipeComponentsTable = initRecipeComponentsTable;
  window.initRecipeItemsTable = initRecipeComponentsTable; // Keep backward compatibility

  // Add a simple debug function
  window.testRecipeJS = function () {
    console.log("🧪 Testing recipe JS...");
    console.log("- Add button exists:", !!document.getElementById("add-row"));
    console.log("- Table exists:", !!document.getElementById("items-table"));
    console.log(
      "- TOTAL_FORMS exists:",
      !!document.getElementById("id_items-TOTAL_FORMS"),
    );
    console.log(
      "- Empty row exists:",
      !!document.getElementById("items-empty-row"),
    );

    var addBtn = document.getElementById("add-row");
    if (addBtn) {
      addBtn.style.backgroundColor = "lime";
      addBtn.style.color = "black";
      addBtn.title = "FOUND BY TEST";
      console.log("✅ Add button found and highlighted!");

      // Try to manually add a click listener
      addBtn.onclick = function () {
        alert("Manual click handler works!");
        console.log("🎯 Manual click triggered!");
      };
      console.log("🔗 Manual click handler attached");
    } else {
      console.log("❌ Add button not found!");
    }

    // Run dropdown debug
    window.debugRecipeDropdowns();
  };

  // Add a function to debug dropdown state
  window.debugRecipeDropdowns = function () {
    console.log("🔍 === DROPDOWN DEBUG === 🔍");
    var allSelects = document.querySelectorAll('select[id*="item"]');
    console.log("Total item selects found:", allSelects.length);

    allSelects.forEach(function (select, idx) {
      var hasPredictiveClass = select.classList.contains("predictive");
      var hasTextInput = !!document.getElementById(select.id + "_text");
      var isUpgraded = select.dataset.predictiveUpgraded === "1";

      console.log(`Select ${idx + 1}:`, {
        id: select.id,
        hasPredictiveClass: hasPredictiveClass,
        hasTextInput: hasTextInput,
        isUpgraded: isUpgraded,
        visible: !select.style.display || select.style.display !== "none",
      });
    });

    var allTextInputs = document.querySelectorAll('input[id*="item_text"]');
    console.log("Predictive text inputs found:", allTextInputs.length);

    allTextInputs.forEach(function (input, idx) {
      console.log(`Text input ${idx + 1}:`, {
        id: input.id,
        visible: input.offsetParent !== null,
      });
    });
  };

  // Add a function to manually trigger adding a row
  window.manualAddRow = function () {
    console.log("🔧 Manual add row triggered...");
    var totalForms = document.getElementById("id_items-TOTAL_FORMS");
    var emptyRow = document.getElementById("items-empty-row");
    var table = document.getElementById("items-table");

    if (!totalForms || !emptyRow || !table) {
      console.error("Missing required elements:", {
        totalForms: !!totalForms,
        emptyRow: !!emptyRow,
        table: !!table,
      });
      return;
    }

    var tbody = table.querySelector("tbody");
    addNewRow(table, tbody, totalForms, emptyRow);
  };

  // Auto-initialize
  console.log("🎯 Recipe items module: setting up auto-initialization...");

  function tryAutoInit() {
    console.log("🔄 Attempting auto-initialization...");

    // Debug current DOM state
    console.log("Current DOM state:", {
      readyState: document.readyState,
      tablesFound: document.querySelectorAll("table").length,
      itemsTable: !!document.getElementById("items-table"),
      addButton: !!document.getElementById("add-row"),
      totalForms: !!document.getElementById("id_items-TOTAL_FORMS"),
      emptyRow: !!document.getElementById("items-empty-row"),
    });

    if (
      document.getElementById("items-table") ||
      document.querySelector('[id$="items-table"]')
    ) {
      console.log("🎯 Found items table, initializing...");
      initRecipeComponentsTable(document);
    } else if (document.querySelectorAll("table").length > 0) {
      console.log(
        "⚠️ No items-table found, but other tables exist. Attempting init anyway...",
      );
      initRecipeComponentsTable(document);
    } else {
      console.log("⏳ No tables found yet, DOM may still be loading...");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", tryAutoInit);
  } else {
    tryAutoInit();
  }

  // Also try after a delay for dynamically loaded content
  setTimeout(tryAutoInit, 500);
  setTimeout(tryAutoInit, 1500);

  console.log("🎉 Recipe items module loaded");
})();
