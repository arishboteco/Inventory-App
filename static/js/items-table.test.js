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
    document.activeElement.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
    );
    expect(document.activeElement).toBe(inputs[1]);
    document.activeElement.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }),
    );
    expect(document.activeElement).toBe(inputs[0]);
    document.activeElement.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    );
    expect(btn.getAttribute("aria-expanded")).toBe("false");
    expect(menu.classList.contains("hidden")).toBe(true);
    expect(document.activeElement).toBe(btn);
  });
});
