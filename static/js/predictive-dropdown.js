(function () {
  function upgradeSelect(select) {
    const dlId =
      (select.id || Math.random().toString(36).slice(2)) + "-options";

    const textInput = document.createElement("input");
    textInput.type = "text";
    textInput.setAttribute("list", dlId);
    textInput.className = select.className.replace("predictive", "").trim();
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

    const datalist = document.createElement("datalist");
    datalist.id = dlId;

    Array.from(select.options).forEach((opt) => {
      const option = document.createElement("option");
      option.value = opt.text;
      option.dataset.value = opt.value;
      datalist.appendChild(option);
      if (opt.selected) {
        textInput.value = opt.text;
        hiddenInput.value = opt.value;
      }
    });

    textInput.addEventListener("input", () => {
      const match = Array.from(datalist.options).find(
        (o) => o.value === textInput.value,
      );
      hiddenInput.value = match ? match.dataset.value : "";
    });

    if (select.id) {
      const label = document.querySelector(`label[for="${select.id}"]`);
      if (label) label.setAttribute("for", textInput.id);
    }

    select.replaceWith(textInput);
    textInput.insertAdjacentElement("afterend", hiddenInput);
    hiddenInput.insertAdjacentElement("afterend", datalist);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("select.predictive").forEach(upgradeSelect);
  });
})();
