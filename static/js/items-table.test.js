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
    btn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
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
