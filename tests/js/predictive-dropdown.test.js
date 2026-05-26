/** @jest-environment jsdom */

describe("predictive dropdown", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <select id="category" class="predictive">
        <option value="">--</option>
        <option value="a">Alpha</option>
        <option value="b">Beta</option>
      </select>`;
    jest.isolateModules(() => {
      require("../../static/js/predictive-dropdown.js");
    });
    document.dispatchEvent(new Event("DOMContentLoaded"));
  });

  test("selects option via keyboard", () => {
    const select = document.getElementById("category");
    const input = document.getElementById("category_text");
    const handler = jest.fn();
    select.addEventListener("change", handler);
    input.focus();
    input.dispatchEvent(new Event("focus"));
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown" }));
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    expect(select.value).toBe("a");
    expect(handler).toHaveBeenCalled();
  });

  test("upgrades selects after htmx swap", () => {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = `<select id="dept" class="predictive"><option value="">--</option><option value="1">One</option></select>`;
    document.body.appendChild(wrapper);
    wrapper.dispatchEvent(new Event("htmx:afterSwap", { bubbles: true }));
    expect(wrapper.querySelector("#dept_text")).not.toBeNull();
  });

  test("waits for the configured minimum search length before showing suggestions", () => {
    document.body.innerHTML = `
      <select id="ingredient" class="predictive" data-min-chars="2">
        <option value="">Type 2+ chars</option>
        <option value="i:1">Flour</option>
        <option value="i:2">Fish</option>
      </select>`;

    window.initPredictiveDropdowns(document);

    const input = document.getElementById("ingredient_text");
    input.focus();
    input.dispatchEvent(new Event("focus"));
    let dropdown = document.querySelector(".predictive-dropdown-list");
    expect(dropdown.querySelectorAll(".predictive-dropdown-option")).toHaveLength(0);

    input.value = "f";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    expect(dropdown.querySelectorAll(".predictive-dropdown-option")).toHaveLength(0);

    input.value = "fl";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    dropdown = document.querySelector(".predictive-dropdown-list");
    expect(dropdown.querySelectorAll(".predictive-dropdown-option")).toHaveLength(1);
    expect(dropdown.textContent).toContain("Flour");
  });
});
