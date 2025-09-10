/** @jest-environment jsdom */

describe("form layout regression", () => {
  test("form does not overflow vertically at large viewport sizes", () => {
    // Simulate a large viewport
    window.innerWidth = 1920;
    window.innerHeight = 1080;

    document.body.innerHTML = `
      <form style="height:100vh; overflow-y:auto">
        <div>
          <label class="leading-normal block mb-1">Name</label>
          <input class="leading-normal px-3 py-2.5 block w-full" />
          <p class="leading-normal">Help text</p>
          <p class="leading-normal text-red-600">Error message</p>
        </div>
      </form>
    `;

    const form = document.querySelector("form");
    expect(form.scrollHeight).toBeLessThanOrEqual(window.innerHeight);
    form.querySelectorAll("label,input,p").forEach((el) => {
      expect(el.scrollHeight).toBe(el.clientHeight);
    });
  });
});

test("items_list template has no subcategory script", () => {
  const fs = require("fs");
  const path = require("path");
  const tpl = fs.readFileSync(
    path.join(
      __dirname,
      "..",
      "..",
      "templates",
      "inventory",
      "items_list.html",
    ),
    "utf8",
  );
  expect(tpl.includes("items/subcategories")).toBe(false);
});
