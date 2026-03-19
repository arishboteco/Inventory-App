(function () {
  console.log("🧹 Clean Recipe Components loaded");

  // Single global flag to prevent multiple initializations
  if (window.recipeComponentsLoaded) {
    console.log("⚠️ Recipe components already loaded, skipping");
    return;
  }
  window.recipeComponentsLoaded = true;

  function initRecipeComponentsTable() {
    console.log("🎯 Initializing recipe components table...");

    // Find elements
    var table =
      document.querySelector("#recipe-components-formset table") ||
      document.querySelector("#items-table");
    var tbody = table ? table.querySelector("tbody") : null;
    var totalForms = document.querySelector('input[name$="TOTAL_FORMS"]');
    var emptyRow =
      document.querySelector("tr.form-row.hidden") ||
      document.querySelector("#items-empty-row");
    var addBtn = document.getElementById("add-row");

    console.log("Found elements:", {
      table: !!table,
      tbody: !!tbody,
      totalForms: !!totalForms,
      emptyRow: !!emptyRow,
      addBtn: !!addBtn,
    });

    if (!table || !tbody || !totalForms || !emptyRow || !addBtn) {
      console.error("❌ Missing required elements for recipe components");
      return;
    }

    // Simple, direct button setup
    addBtn.onclick = function (e) {
      e.preventDefault();
      e.stopPropagation();

      console.log("🔥 Add Item clicked - creating ONE row");

      // Get current count
      var currentCount = parseInt(totalForms.value, 10) || 0;
      console.log("Current count:", currentCount);

      // Clone empty row
      var newRow = emptyRow.cloneNode(true);

      // Update all form elements
      newRow
        .querySelectorAll("input, select, textarea")
        .forEach(function (element) {
          if (element.name) {
            element.name = element.name.replace("__prefix__", currentCount);
          }
          if (element.id) {
            element.id = element.id.replace("__prefix__", currentCount);
          }

          // Clear values except hidden fields
          if (element.type !== "hidden") {
            if (element.tagName === "SELECT") {
              element.selectedIndex = 0;
            } else {
              element.value = "";
            }
          }
        });

      // Update labels
      newRow.querySelectorAll("label").forEach(function (label) {
        if (label.htmlFor) {
          label.htmlFor = label.htmlFor.replace("__prefix__", currentCount);
        }
      });

      // Make visible and add to table
      newRow.classList.remove("hidden");
      newRow.id = "";
      tbody.appendChild(newRow);

      // Update form count
      totalForms.value = currentCount + 1;

      console.log("✅ Row added. New count:", totalForms.value);

      // Initialize dropdown after a delay
      setTimeout(function () {
        var itemSelect = newRow.querySelector('select[id$="-item"]');
        if (itemSelect && window.initPredictiveDropdowns) {
          itemSelect.classList.add("predictive");
          delete itemSelect.dataset.predictiveUpgraded;
          window.initPredictiveDropdowns(newRow);
          console.log("🔧 Initialized dropdown for:", itemSelect.id);
        }
      }, 100);
    };

    console.log("✅ Recipe components initialized");
  }

  // Export the function
  window.initRecipeComponentsTable = initRecipeComponentsTable;

  // Try to initialize immediately if DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initRecipeComponentsTable);
  } else {
    setTimeout(initRecipeComponentsTable, 100);
  }
})();
