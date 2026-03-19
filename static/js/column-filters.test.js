/** @jest-environment jsdom */

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("column-filters dropdown", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <button data-filter-btn data-field="unit" data-param="base_unit"></button>
      <template id="column-filter-dropdown-template">
        <div>
          <input data-filter-search />
          <div data-filter-options></div>
          <button data-show-more class="hidden">Show more</button>
          <button data-select-all></button>
          <button data-clear></button>
          <button data-apply></button>
        </div>
      </template>`;
    global.fetch = jest.fn();
    window.fetch = global.fetch;
    jest.isolateModules(() => {
      require("./column-filters.js");
    });
    document.dispatchEvent(new Event("DOMContentLoaded"));
  });

  test("caches options per field", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([{ value: "a", label: "A" }]),
      headers: { get: () => null },
    });
    const btn = document.querySelector("[data-filter-btn]");
    btn.click();
    await flushPromises();
    expect(fetch).toHaveBeenCalledTimes(1);
    btn.click(); // closes
    btn.click(); // reopen
    await flushPromises();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  test("hides show more when fewer than limit options", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([{ value: "a", label: "A" }]),
      headers: { get: () => null },
    });
    const btn = document.querySelector("[data-filter-btn]");
    btn.click();
    await flushPromises();
    const showMore = document.querySelector("[data-show-more]");
    expect(showMore.classList.contains("hidden")).toBe(true);
  });
  test("rebinds after htmx swap", async () => {
    const container = document.createElement("div");
    container.innerHTML =
      '<button data-filter-btn data-field="unit" data-param="base_unit"></button>';
    document.body.appendChild(container);
    document.body.dispatchEvent(new Event("htmx:afterSwap", { bubbles: true }));
    await flushPromises();
    const btn = container.querySelector("[data-filter-btn]");
    expect(btn._cfBound).toBe(true);
  });
});
