/** @jest-environment jsdom */
const { initTopNav } = require('./top-nav.js');

describe('top navigation groups', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div data-top-nav>
        <div data-nav-group class="top-nav-group">
          <button aria-expanded="false">Group</button>
          <div data-nav-panel class="hidden"><a href="#">Link</a></div>
        </div>
      </div>`;
    initTopNav(document);
  });

  test('click toggles visibility', () => {
    const button = document.querySelector('[data-nav-group] > button');
    const panel = document.querySelector('[data-nav-panel]');
    expect(panel.classList.contains('hidden')).toBe(true);
    button.click();
    expect(panel.classList.contains('hidden')).toBe(false);
    expect(button.getAttribute('aria-expanded')).toBe('true');
    button.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    expect(panel.classList.contains('hidden')).toBe(true);
    expect(button.getAttribute('aria-expanded')).toBe('false');
  });
});
