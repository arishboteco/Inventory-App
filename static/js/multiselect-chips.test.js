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

  test("filters list and maintains accessibility", () => {
    const search = document.querySelector(".chips-search input");
    const items = document.querySelectorAll("li");

    // search input should receive focus for keyboard accessibility
    expect(document.activeElement).toBe(search);

    // filter for "beta"
    search.value = "beta";
    search.dispatchEvent(new Event("input", { bubbles: true }));

    // first item hidden
    expect(items[0].classList.contains("hidden")).toBe(true);
    expect(items[0].getAttribute("aria-hidden")).toBe("true");
    // second item visible
    expect(items[1].classList.contains("hidden")).toBe(false);
    expect(items[1].getAttribute("aria-hidden")).toBe("false");
  });
});
