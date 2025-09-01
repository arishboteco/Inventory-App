/** @jest-environment jsdom */
const { filtersPanel } = require('./filter-panel');

describe('filtersPanel', () => {
  beforeEach(() => {
    localStorage.clear();
    global.updateFiltersHeight = jest.fn();
  });

  test('reads state from localStorage', () => {
    localStorage.setItem('items_filters_open', 'false');
    const panel = filtersPanel();
    expect(panel.filtersOpen).toBe(false);
  });

  test('toggle persists state and recalculates height', () => {
    const panel = filtersPanel();
    panel.$nextTick = (cb) => cb();
    panel.toggle();
    expect(localStorage.getItem('items_filters_open')).toBe('false');
    expect(updateFiltersHeight).toHaveBeenCalled();
  });
});

