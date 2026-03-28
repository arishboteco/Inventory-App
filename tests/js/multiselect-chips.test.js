/** @jest-environment jsdom */

describe("multiselect chips filter", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div data-multiselect="chips">
        <ul>
          <li><label><input type="checkbox" value="alpha">Alpha</label></li>
          <li><label><input type="checkbox" value="beta">Beta</label></li>
        </ul>
      </div>`;

    jest.isolateModules(() => {
      require("./multiselect-chips.js");
    });
    document.dispatchEvent(new Event("DOMContentLoaded"));
  });

  test("creates chip when option selected", () => {
    const checkbox = document.querySelector('input[value="alpha"]');
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event("change", { bubbles: true }));
    const chip = document.querySelector(".chips button");
    expect(chip).not.toBeNull();
    expect(chip.textContent).toContain("Alpha");
  });
});
