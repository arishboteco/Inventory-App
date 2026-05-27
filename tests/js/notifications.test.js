/** @jest-environment jsdom */

describe("notifications", () => {
  beforeEach(() => {
    jest.resetModules();
    jest.useFakeTimers();
    document.body.innerHTML = `<div id="notification-container"></div>`;
    global.requestAnimationFrame = (callback) => callback();
    require("../../static/js/notifications.js");
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test("decodes HTML entity apostrophes before rendering toast text", () => {
    window.notifications.showToast("Can&#x27;t save supplier", "error", 0);

    expect(document.body.textContent).toContain("Can't save supplier");
    expect(document.body.textContent).not.toContain("&#x27;");
  });
});
