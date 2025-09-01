/** @jest-environment jsdom */

// Integration test for delete action in items-table.js

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("items-table delete", () => {
  beforeEach(() => {
    document.body.innerHTML =
      '<table><tr class="item-row" data-item-id="1"><td><button data-action="delete">Del</button></td></tr></table>';
    document.cookie = "csrftoken=abc";
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ ok: true }),
      }),
    );
    global.confirm = jest.fn(() => true);
    window.notifications = { showToast: jest.fn() };
    // Require script after mocks and DOM setup
    jest.isolateModules(() => {
      require("./items-table.js");
    });
  });

  test("calls delete endpoint and removes row", async () => {
    const btn = document.querySelector('[data-action="delete"]');
    btn.click();
    await flushPromises();
    expect(fetch).toHaveBeenCalledWith(
      "/items/1/delete/",
      expect.objectContaining({
        method: "POST",
        headers: { "X-CSRFToken": "abc", "X-Requested-With": "fetch" },
      }),
    );
    expect(document.querySelector(".item-row")).toBeNull();
    expect(window.notifications.showToast).toHaveBeenCalledWith(
      "Item deleted successfully!",
      "success",
    );
  });
});

describe("items-table view", () => {
  beforeEach(() => {
    document.body.innerHTML =
      '<table><tr class="item-row" data-item-id="1"><td><a data-action="view" data-href="/items/1/?partial=1" href="/items/1/">View</a></td></tr></table>';
    global.fetch = jest.fn(() =>
      Promise.resolve({
        text: () => Promise.resolve("<div>ok</div>"),
      }),
    );
    window.modal = { open: jest.fn() };
    window.notifications = { showToast: jest.fn() };
    jest.isolateModules(() => {
      require("./items-table.js");
    });
  });

  test("opens modal with fetched content", async () => {
    const btn = document.querySelector('[data-action="view"]');
    btn.click();
    await flushPromises();
    expect(fetch).toHaveBeenCalledWith("/items/1/?partial=1", {
      headers: { "X-Requested-With": "fetch" },
    });
    expect(window.modal.open).toHaveBeenCalledWith("<div>ok</div>");
  });
});

describe("column visibility menu", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div>
        <button data-col-menu-button aria-haspopup="true" aria-expanded="false"></button>
        <ul data-col-menu class="hidden">
          <li><input type="checkbox" data-col-toggle value="category" checked></li>
          <li><input type="checkbox" data-col-toggle value="unit" checked></li>
        </ul>
      </div>`;
    // Require script after DOM setup
    jest.isolateModules(() => {
      require("./items-table.js");
    });
    document.dispatchEvent(new Event("DOMContentLoaded"));
  });

  test("closes menu on outside click", () => {
    const btn = document.querySelector("[data-col-menu-button]");
    const menu = document.querySelector("[data-col-menu]");
    // Open via keyboard shortcut
    btn.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
    );
    expect(btn.getAttribute("aria-expanded")).toBe("true");
    document.body.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(btn.getAttribute("aria-expanded")).toBe("false");
    expect(menu.classList.contains("hidden")).toBe(true);
  });

  test("supports keyboard navigation", () => {
    const btn = document.querySelector("[data-col-menu-button]");
    const menu = document.querySelector("[data-col-menu]");
    btn.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
    );
    const inputs = menu.querySelectorAll("input");
    expect(document.activeElement).toBe(inputs[0]);
    menu.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
    );
    expect(inputs).toContain(document.activeElement);
    menu.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }),
    );
    expect(inputs).toContain(document.activeElement);
    menu.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    );
    expect(btn.getAttribute("aria-expanded")).toBe("false");
    expect(menu.classList.contains("hidden")).toBe(true);
    expect(document.activeElement).toBe(btn);
  });
});

describe("stock_status column toggle", () => {
  beforeEach(() => {
    localStorage.setItem("items_table_hidden", '["stock_status"]');
    document.body.innerHTML = `
      <div>
        <label><input type="checkbox" data-col-toggle value="stock_status" checked></label>
        <table><tr><td data-col="stock_status">val</td></tr></table>
      </div>`;
    jest.isolateModules(() => {
      require("./items-table.js");
    });
    document.dispatchEvent(new Event("DOMContentLoaded"));
  });

  test("toggles visibility of stock_status column", () => {
    const cb = document.querySelector(
      '[data-col-toggle][value="stock_status"]',
    );
    const cell = document.querySelector('[data-col="stock_status"]');
    expect(cb.checked).toBe(false);
    expect(cell.classList.contains("hidden")).toBe(true);
    cb.checked = true;
    cb.dispatchEvent(new Event("change", { bubbles: true }));
    expect(cell.classList.contains("hidden")).toBe(false);
  });
});
