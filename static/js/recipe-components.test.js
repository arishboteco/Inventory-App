/** @jest-environment jsdom */

describe("recipe cost helpers", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div>
        <div id="cost-by-category"></div>
        <div id="recipe-total-cost">0.00</div>
        <div id="recipe-suggested-price">0.00</div>
        <input id="recipe-margin" type="number" value="0" />
        <table id="items-table">
          <tbody>
            <tr class="form-row" data-form-index="0" data-category="Produce">
              <td><input id="id_items-0-quantity" type="number" value="2.00" /></td>
              <td><div data-line-cost>10.00</div></td>
            </tr>
            <tr class="form-row hidden" id="items-empty-row"></tr>
          </tbody>
        </table>
      </div>`;

    jest.isolateModules(() => {
      require("./recipe-components.js");
    });
  });

  test("updateRecipeCosts keeps focus and recalculates totals", () => {
    const quantityInput = document.getElementById("id_items-0-quantity");
    const lineCost = document.querySelector("[data-line-cost]");
    const total = document.getElementById("recipe-total-cost");
    const summary = document.getElementById("cost-by-category");

    quantityInput.focus();
    expect(document.activeElement).toBe(quantityInput);

    lineCost.textContent = "12.34";
    window.updateRecipeCosts();

    expect(document.activeElement).toBe(quantityInput);
    expect(total.textContent).toBe("12.34");
    expect(summary.textContent).toContain("Produce");
    expect(summary.textContent).toContain("12.34");

    lineCost.textContent = "15.50";
    window.updateRecipeCosts();

    expect(document.activeElement).toBe(quantityInput);
    expect(total.textContent).toBe("15.50");
  });
});
