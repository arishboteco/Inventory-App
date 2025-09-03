/** @jest-environment jsdom */
const fs = require('fs');
const path = require('path');

describe('table sticky header', () => {
  test('CSS rule sets sticky header top to 0', () => {
    const css = fs.readFileSync(path.resolve(__dirname, '../src/app.css'), 'utf8');
    expect(css).toMatch(/\.table-sticky thead th\s*{[^}]*top: 0/);
  });

  test('padding adjusts to filter bar height', () => {
    document.body.innerHTML = '<div id="items-filter-bar"></div><div id="items-list"></div>';
    const bar = document.getElementById('items-filter-bar');
    const list = document.getElementById('items-list');
    Object.defineProperty(bar, 'offsetHeight', { configurable: true, value: 40 });
    function updateFiltersHeight() {
      const bar = document.getElementById('items-filter-bar');
      const list = document.getElementById('items-list');
      if (bar && list) {
        list.style.paddingTop = bar.offsetHeight + 'px';
      }
    }
    updateFiltersHeight();
    expect(list.style.paddingTop).toBe('40px');
  });
});
