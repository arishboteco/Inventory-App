/**
 * Smart Forms - Intelligent form behavior for enhanced UX
 * Features: Auto-complete, smart suggestions, dynamic categories, validation
 */

class SmartFormManager {
  constructor() {
    this.initializeSmartValidation();
    this.initializeFormFlow();
  }

  initializeSmartValidation() {
    const nameField = document.querySelector('input[name="name"]');
    const form = document.querySelector("#item-form");

    if (nameField && form) {
      let debounceTimer;
      nameField.addEventListener("input", (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          this.checkSimilarNames(e.target.value);
        }, 500);
      });
    }
  }

  async checkSimilarNames(name) {
    if (name.length < 3) return;

    try {
      const response = await fetch(
        `/items/check-similar-names/?name=${encodeURIComponent(name)}`,
      );
      const data = await response.json();

      const nameField = document.querySelector('input[name="name"]');
      const existingWarning = document.querySelector("#similar-names-warning");

      if (existingWarning) {
        existingWarning.remove();
      }

      if (data.similar_items && data.similar_items.length > 0) {
        const warning = document.createElement("div");
        warning.id = "similar-names-warning";
        warning.className =
          "mt-2 p-3 bg-warning-lightest border border-warning-soft rounded-md";
        warning.innerHTML = `
                    <div class="flex items-start">
                        <svg class="w-5 h-5 text-warning-medium mr-2 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                        </svg>
                        <div>
                            <h4 class="text-sm font-medium text-warning-dark">Similar items found:</h4>
                            <ul class="mt-1 text-sm text-warning">
                                ${data.similar_items.map((item) => `<li class="cursor-pointer hover:underline" onclick="fillItemData(${item.id})">${item.name} (${item.category || "No category"})</li>`).join("")}
                            </ul>
                            <p class="mt-1 text-xs text-warning-medium">Click an item to use its data as a template</p>
                        </div>
                    </div>
                `;
        nameField.parentNode.appendChild(warning);
      }
    } catch (error) {
      console.error("Error checking similar names:", error);
    }
  }

  initializeFormFlow() {
    // Smart form progression
    this.setupFormSections();
    this.setupProgressIndicator();
  }

  setupFormSections() {
    const sections = document.querySelectorAll(
      ".bg-gray-50, .bg-blue-50, .bg-success-lightest",
    );
    sections.forEach((section, index) => {
      const header = section.querySelector("h3");
      if (header) {
        const indicator = document.createElement("span");
        indicator.className = "ml-2 text-sm text-gray-500";
        indicator.textContent = `(${index + 1}/${sections.length})`;
        header.appendChild(indicator);
      }
    });
  }

  setupProgressIndicator() {
    const form = document.querySelector("#item-form");
    if (!form) return;

    const progressBar = document.createElement("div");
    progressBar.id = "form-progress";
    progressBar.className = "mb-4 bg-gray-200 rounded-full h-2";
    progressBar.innerHTML =
      '<div class="bg-blue-600 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>';

    form.insertBefore(progressBar, form.firstChild);

    // Monitor form completion
    const requiredFields = form.querySelectorAll("[required]");
    const allFields = form.querySelectorAll("input, select, textarea");

    allFields.forEach((field) => {
      field.addEventListener("change", () => this.updateProgress(form));
    });

    this.updateProgress(form);
  }

  updateProgress(form) {
    const requiredFields = form.querySelectorAll("[required]");
    const filledRequired = Array.from(requiredFields).filter(
      (field) => field.value.trim() !== "",
    ).length;
    const allFields = form.querySelectorAll(
      'input:not([type="hidden"]), select, textarea',
    );
    const filledAll = Array.from(allFields).filter(
      (field) => field.value.trim() !== "",
    ).length;

    const requiredProgress = (filledRequired / requiredFields.length) * 60; // 60% for required
    const optionalProgress = (filledAll / allFields.length) * 40; // 40% for all fields
    const totalProgress = Math.min(100, requiredProgress + optionalProgress);

    const progressBar = document.querySelector("#form-progress .bg-blue-600");
    if (progressBar) {
      progressBar.style.width = `${totalProgress}%`;
    }
  }
}

// Global functions for template population
window.fillItemData = async function (itemId) {
  try {
    const response = await fetch(`/items/${itemId}/`);
    const html = await response.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");

    // Extract item data and populate form
    const categoryElement = doc.querySelector('[data-field="category_id"]');
    const unitElement = doc.querySelector('[data-field="unit_id"]');

    if (categoryElement && categoryElement.textContent.trim()) {
      const categorySelect = document.querySelector(
        'select[data-field="category_id"]',
      );
      if (categorySelect) {
        categorySelect.value = categoryElement.textContent.trim();
      }
    }

    if (unitElement && unitElement.textContent.trim()) {
      const unitSelect = document.querySelector('select[data-field="unit_id"]');
      if (unitSelect) {
        unitSelect.value = unitElement.textContent.trim();
      }
    }

    // Close warning
    const warning = document.querySelector("#similar-names-warning");
    if (warning) warning.remove();

    // Show success message using unified notification system
    window.notifications.showToast(
      "Template data applied! Update the name and other fields as needed.",
      "success",
    );
  } catch (error) {
    console.error("Error loading item template:", error);
  }
};

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
  new SmartFormManager();
});
