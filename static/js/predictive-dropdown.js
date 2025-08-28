(function () {
  function upgradeSelect(select) {
    const container = document.createElement("div");
    container.className = "predictive-dropdown-container relative";
    
    const textInput = document.createElement("input");
    textInput.type = "text";
    textInput.className = select.className.replace("predictive", "").trim();
    textInput.placeholder = "Type to search...";
    const textId = select.id ? select.id + "_text" : "";
    if (textId) {
      textInput.id = textId;
    }

    const hiddenInput = document.createElement("input");
    hiddenInput.type = "hidden";
    hiddenInput.name = select.name;
    if (select.id) {
      hiddenInput.id = select.id;
    }

    const dropdown = document.createElement("div");
    dropdown.className = "predictive-dropdown-list absolute z-50 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto hidden";
    dropdown.style.top = "100%";
    dropdown.style.left = "0";

    const options = Array.from(select.options).map((opt) => ({
      text: opt.text,
      value: opt.value,
      selected: opt.selected
    }));

    // Set initial value if there's a selected option
    const selectedOption = options.find(opt => opt.selected);
    if (selectedOption) {
      textInput.value = selectedOption.text;
      hiddenInput.value = selectedOption.value;
    }

    function renderOptions(filteredOptions) {
      dropdown.innerHTML = "";
      filteredOptions.forEach((option) => {
        const optionEl = document.createElement("div");
        optionEl.className = "px-3 py-2 cursor-pointer hover:bg-blue-50 border-b border-gray-100 last:border-b-0";
        optionEl.textContent = option.text;
        optionEl.addEventListener("click", () => {
          textInput.value = option.text;
          hiddenInput.value = option.value;
          dropdown.classList.add("hidden");
          textInput.blur();
        });
        dropdown.appendChild(optionEl);
      });
    }

    textInput.addEventListener("input", (e) => {
      const query = e.target.value.toLowerCase();
      const filteredOptions = options.filter(opt => 
        opt.text.toLowerCase().includes(query)
      );
      
      renderOptions(filteredOptions);
      dropdown.classList.remove("hidden");
      
      // Update hidden input
      const exactMatch = filteredOptions.find(opt => 
        opt.text.toLowerCase() === query
      );
      hiddenInput.value = exactMatch ? exactMatch.value : "";
    });

    textInput.addEventListener("focus", () => {
      renderOptions(options);
      dropdown.classList.remove("hidden");
    });

    textInput.addEventListener("blur", (e) => {
      // Delay hiding to allow clicks on options
      setTimeout(() => {
        dropdown.classList.add("hidden");
      }, 150);
    });

    // Handle keyboard navigation
    textInput.addEventListener("keydown", (e) => {
      const visibleOptions = dropdown.querySelectorAll("div");
      const activeOption = dropdown.querySelector(".bg-blue-100");
      let activeIndex = Array.from(visibleOptions).indexOf(activeOption);

      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (activeOption) activeOption.classList.remove("bg-blue-100");
        activeIndex = Math.min(activeIndex + 1, visibleOptions.length - 1);
        if (visibleOptions[activeIndex]) {
          visibleOptions[activeIndex].classList.add("bg-blue-100");
        }
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        if (activeOption) activeOption.classList.remove("bg-blue-100");
        activeIndex = Math.max(activeIndex - 1, 0);
        if (visibleOptions[activeIndex]) {
          visibleOptions[activeIndex].classList.add("bg-blue-100");
        }
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (activeOption) {
          activeOption.click();
        }
      } else if (e.key === "Escape") {
        dropdown.classList.add("hidden");
        textInput.blur();
      }
    });

    if (select.id) {
      const label = document.querySelector(`label[for="${select.id}"]`);
      if (label) label.setAttribute("for", textInput.id);
    }

    container.appendChild(textInput);
    container.appendChild(hiddenInput);
    container.appendChild(dropdown);
    
    select.replaceWith(container);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("select.predictive").forEach(upgradeSelect);
  });
})();
