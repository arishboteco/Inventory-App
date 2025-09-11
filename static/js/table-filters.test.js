/** @jest-environment jsdom */

describe('table filters', () => {
  beforeEach(() => {
    document.body.innerHTML = '<form id="filters"><input data-inline-filter /></form>';
    window.htmx = { trigger: jest.fn() };
    jest.useFakeTimers();
    jest.isolateModules(() => {
      require('./table-filters.js');
    });
    window.tableFilters.bind(document);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('triggers submit on input', () => {
    const input = document.querySelector('[data-inline-filter]');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    jest.runAllTimers();
    expect(window.htmx.trigger).toHaveBeenCalledWith(
      document.getElementById('filters'),
      'submit'
    );
  });
});
