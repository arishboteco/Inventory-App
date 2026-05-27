/** @jest-environment jsdom */

describe("global form validation feedback", () => {
  beforeEach(() => {
    jest.resetModules();
    document.body.innerHTML = `
      <form>
        <div>
          <label for="id_supplier">Supplier</label>
          <input id="id_supplier" name="supplier" required />
          <p data-feedback="success" class="hidden"></p>
          <p data-feedback="error" class="hidden"></p>
        </div>
      </form>`;
    require("../../static/js/forms.js");
    document.dispatchEvent(new Event("DOMContentLoaded"));
  });

  test("shows app-owned required messages instead of browser text", () => {
    const input = document.getElementById("id_supplier");
    const error = document.querySelector('[data-feedback="error"]');

    input.dispatchEvent(new Event("blur", { bubbles: true }));

    expect(error.textContent).toBe("Supplier is required.");
    expect(error.classList.contains("hidden")).toBe(false);
  });
});
