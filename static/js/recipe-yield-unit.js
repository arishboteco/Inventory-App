/**
 * Sync recipe default_yield_unit hidden input with recipe type (FINAL → portion)
 * and sub-recipe base-unit select. Used by templates/inventory/recipes/_form_fields.html.
 * Call initRecipeYieldUnitRoots(container) after injecting recipe form HTML (e.g. modal drawer).
 */
(function () {
  function sync(root) {
    if (!root) {
      return;
    }
    var typeEl = root.querySelector("#id_type");
    if (!typeEl) {
      return;
    }
    var hidden = root.querySelector('input[name="default_yield_unit"]');
    var subSel = root.querySelector("#id_default_yield_unit_sub_select");
    var finalBlock = root.querySelector("[data-recipe-yield-final]");
    var subBlock = root.querySelector("[data-recipe-yield-sub]");
    if (!hidden || !subSel || !finalBlock || !subBlock) {
      return;
    }
    var isFinal = typeEl.value === "FINAL";
    finalBlock.classList.toggle("hidden", !isFinal);
    subBlock.classList.toggle("hidden", isFinal);
    if (isFinal) {
      hidden.value = "portion";
    } else {
      hidden.value = subSel.value || hidden.value;
    }
  }

  function bindRoot(root) {
    if (!root) {
      return;
    }
    var typeEl = root.querySelector("#id_type");
    if (!typeEl) {
      return;
    }
    typeEl.addEventListener("change", function () {
      sync(root);
    });
    var subSel = root.querySelector("#id_default_yield_unit_sub_select");
    if (subSel) {
      subSel.addEventListener("change", function () {
        if (typeEl.value !== "FINAL") {
          var hidden = root.querySelector('input[name="default_yield_unit"]');
          if (hidden) {
            hidden.value = subSel.value;
          }
        }
      });
    }
    var form = root.closest("form[data-modal-form]") || root.closest("form");
    if (form) {
      form.addEventListener("submit", function () {
        sync(root);
      });
    }
    sync(root);
  }

  function initRecipeYieldUnitRoots(container) {
    var scope = container || document;
    scope
      .querySelectorAll("[data-recipe-yield-unit-root]")
      .forEach(function (root) {
        if (root.dataset.recipeYieldUnitInit === "1") {
          return;
        }
        root.dataset.recipeYieldUnitInit = "1";
        bindRoot(root);
      });
  }

  window.initRecipeYieldUnitRoots = initRecipeYieldUnitRoots;

  function boot() {
    initRecipeYieldUnitRoots(document);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
