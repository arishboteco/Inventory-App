/** @jest-environment jsdom */
const fs = require("fs");
const path = require("path");

describe("table sticky header", () => {
  test("CSS rule sets sticky header top to 0", () => {
    const css = fs.readFileSync(
      path.resolve(__dirname, "../src/app.css"),
      "utf8",
    );
    expect(css).toMatch(
      /\.table-sticky thead th\s*{[^}]*(@apply[^;]*top-0|top: 0)/,
    );
  });
});
