function filtersPanel(storageKey = 'items_filters_open') {
  return {
    filtersOpen: localStorage.getItem(storageKey) !== 'false',
    toggle() {
      this.filtersOpen = !this.filtersOpen;
      localStorage.setItem(storageKey, this.filtersOpen);
      if (typeof this.$nextTick === 'function') {
        this.$nextTick(() => {
          if (typeof updateFiltersHeight === 'function') {
            updateFiltersHeight();
          }
        });
      } else if (typeof updateFiltersHeight === 'function') {
        updateFiltersHeight();
      }
    },
    init() {
      if (typeof this.$nextTick === 'function') {
        this.$nextTick(() => {
          if (typeof updateFiltersHeight === 'function') {
            updateFiltersHeight();
          }
        });
      } else if (typeof updateFiltersHeight === 'function') {
        updateFiltersHeight();
      }
    },
  };
}

if (typeof window !== 'undefined') {
  window.filtersPanel = filtersPanel;
}

if (typeof module !== 'undefined') {
  module.exports = { filtersPanel };
}

