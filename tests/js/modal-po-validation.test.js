/** @jest-environment jsdom */

describe("modal purchase order validation", () => {
  beforeEach(() => {
    jest.resetModules();
    document.body.innerHTML = `
      <div id="modal-root" class="hidden"><div id="modal-content"></div></div>
      <form id="po-drawer-form" data-modal-form data-requires-line-items action="/purchase-orders/create/partial/">
        <input name="csrfmiddlewaretoken" value="token" />
        <input name="supplier" required value="" />
        <input name="order_date" required value="" />
        <div id="items-formset">
          <select name="items-0-item" required><option value=""></option></select>
          <input name="items-0-quantity_ordered" required type="number" value="" />
          <input name="items-0-unit_price" required type="number" value="" />
        </div>
      </form>`;
    global.fetch = jest.fn();
    window.notifications = { showToast: jest.fn() };
    require("../../static/js/modal.js");
  });

  test("reports native required errors before posting modal form", () => {
    const form = document.getElementById("po-drawer-form");
    form.checkValidity = jest.fn(() => false);
    form.reportValidity = jest.fn();

    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    expect(form.checkValidity).toHaveBeenCalled();
    expect(form.reportValidity).toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
  });
});
