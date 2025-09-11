/** @jest-environment jsdom */

describe('predictive dropdown', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <select id="category" class="predictive">
        <option value="">--</option>
        <option value="a">Alpha</option>
        <option value="b">Beta</option>
      </select>`;
    jest.isolateModules(() => {
      require('./predictive-dropdown.js');
    });
    document.dispatchEvent(new Event('DOMContentLoaded'));
  });

  test('selects option via keyboard', () => {
    const select = document.getElementById('category');
    const input = document.getElementById('category_text');
    const handler = jest.fn();
    select.addEventListener('change', handler);
    input.focus();
    input.dispatchEvent(new Event('focus'));
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(select.value).toBe('a');
    expect(handler).toHaveBeenCalled();
  });

  test('upgrades selects after htmx swap', () => {
    const wrapper = document.createElement('div');
    wrapper.innerHTML = `<select id="dept" class="predictive"><option value="">--</option><option value="1">One</option></select>`;
    document.body.appendChild(wrapper);
    wrapper.dispatchEvent(new Event('htmx:afterSwap', { bubbles: true }));
    expect(wrapper.querySelector('#dept_text')).not.toBeNull();
  });
});
