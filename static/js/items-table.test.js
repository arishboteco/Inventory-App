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
      <div data-col-menu-container>
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

  test("opens menu on focus", () => {
    const btn = document.querySelector("[data-col-menu-button]");
    const menu = document.querySelector("[data-col-menu]");
    btn.dispatchEvent(new Event("focus"));
    expect(btn.getAttribute("aria-expanded")).toBe("true");
    expect(menu.classList.contains("hidden")).toBe(false);
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

describe("sorting aria updates", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <table data-sortable>
        <thead>
          <tr><th aria-sort="none"><button data-sort="col1" class="sort">Name</button></th></tr>
        </thead>
        <tbody>
          <tr><td class="col0">A</td></tr>
          <tr><td class="col0">B</td></tr>
        </tbody>
      </table>`;
    jest.isolateModules(() => {
      require("./items-table.js");
    });
  });

  test("updates aria-sort when button toggles", async () => {
    const btn = document.querySelector("[data-sort]");
    btn.addEventListener("click", () => {
      btn.classList.add("asc");
    });
    btn.click();
    await flushPromises();
    expect(btn.closest("th").getAttribute("aria-sort")).toBe("ascending");

    btn.addEventListener("click", () => {
      btn.classList.remove("asc");
      btn.classList.add("desc");
    });
    btn.click();
    await flushPromises();
    expect(btn.closest("th").getAttribute("aria-sort")).toBe("descending");
  });
});

describe("details toggle", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <table>
        <tr class="item-row" data-item-id="1">
          <td data-col="name">
            <button class="main-row" data-action="toggle-details" aria-expanded="false" aria-controls="details-1">
              <svg></svg>
            </button>
          </td>
        </tr>
        <tr id="details-1" class="hidden"><td colspan="10">Details</td></tr>
      </table>`;
    jest.isolateModules(() => {
      require("./items-table.js");
    });
  });

  test("shows and hides details panel", () => {
    const row = document.querySelector(".item-row");
    const panel = document.getElementById("details-1");
    const btn = row.querySelector('[data-action="toggle-details"]');
    const svg = btn.querySelector("svg");
    window.itemsTable.toggleDetails(row);
    expect(panel.classList.contains("hidden")).toBe(false);
    expect(btn.getAttribute("aria-expanded")).toBe("true");
    expect(svg.classList.contains("rotate-90")).toBe(true);
    window.itemsTable.toggleDetails(row);
    expect(panel.classList.contains("hidden")).toBe(true);
    expect(btn.getAttribute("aria-expanded")).toBe("false");
    expect(svg.classList.contains("rotate-90")).toBe(false);
  });
});

describe("inline row edit", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <table>
        <tr class="item-row" data-item-id="1" data-category-id="2" data-unit-id="3">
          <td data-col="name"><span class="font-medium">Item</span></td>
          <td data-col="rop">5</td>
          <td data-col="category">Cat</td>
          <td data-col="unit">Unit</td>
          <td data-col="stock">10</td>
          <td data-col="status">Active</td>
          <td><button data-action="quick-edit">Edit</button></td>
        </tr>
      </table>`;
    jest.isolateModules(() => {
      require("./items-table.js");
    });
  });

  test("renders actions with gap class", () => {
    const btn = document.querySelector('[data-action="quick-edit"]');
    btn.click();
    const actionsDiv = document.querySelector("tr.item-row td:last-child div");
    expect(actionsDiv).not.toBeNull();
    expect(actionsDiv.classList.contains("gap-1")).toBe(true);
    expect(actionsDiv.classList.contains("flex")).toBe(true);
    expect(actionsDiv.getAttribute("style")).toBeNull();
  });
});
