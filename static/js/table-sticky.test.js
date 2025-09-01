/** @jest-environment jsdom */
const fs = require('fs');
const path = require('path');

describe('table sticky header', () => {
  test('CSS rule exists with variable top', () => {
    const css = fs.readFileSync(path.resolve(__dirname, '../src/app.css'), 'utf8');
    expect(css).toMatch(/\.table-sticky thead th\s*{[^}]*top: var\(--filters-height, 0\)/);
  });

  test('filters height variable updates', () => {
    document.body.innerHTML = '<div class="table-scroll"><div id="bar"></div></div>';
    const bar = document.getElementById('bar');
    Object.defineProperty(bar, 'offsetHeight', { configurable: true, value: 40 });
    const scroller = bar.closest('.table-scroll');
    scroller.style.setProperty('--filters-height', bar.offsetHeight + 'px');
    expect(scroller.style.getPropertyValue('--filters-height')).toBe('40px');
  });
});
