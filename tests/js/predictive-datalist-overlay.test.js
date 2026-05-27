/** @jest-environment jsdom */

describe("predictive datalist overlay", () => {
  beforeEach(() => {
    jest.resetModules();
    document.body.innerHTML = `
      <input id="supplier" name="supplier" list="supplier-options" data-predictive-input="1" />
      <datalist id="supplier-options">
        <option value="42">Acme Produce</option>
        <option value="77">Paper Goods</option>
      </datalist>`;
    jest.isolateModules(() => {
      require("../../static/js/predictive-datalist-overlay.js");
    });
    document.dispatchEvent(new Event("DOMContentLoaded"));
  });

  test("filters options by display label when option value is an id", () => {
    const input = document.getElementById("supplier");

    input.value = "prod";
    input.dispatchEvent(new Event("focus"));

    const overlay = document.querySelector(".predictive-overlay");
    expect(overlay.textContent).toContain("Acme Produce");
    expect(overlay.textContent).not.toContain("Paper Goods");
  });
});
