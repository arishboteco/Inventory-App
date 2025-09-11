(function () {
  const cache = new Map();
  const LIMIT = 50;

  function createDropdown() {
    const tpl = document.getElementById('column-filter-dropdown-template');
    if (!tpl) return null;
    return tpl.content.firstElementChild.cloneNode(true);
  }

  function closeDropdown(drop) {
    if (drop) drop.classList.add('hidden');
    document.removeEventListener('click', drop? drop._outsideHandler: null);
  }

  function positionDropdown(drop, btn) {
    const rect = btn.getBoundingClientRect();
    drop.style.top = `${rect.bottom + window.scrollY}px`;
    drop.style.left = `${rect.left + window.scrollX}px`;
  }

  function fetchOptions(field, params, page = 1) {
    const p = new URLSearchParams(params);
    p.set('limit', LIMIT);
    p.set('page', page);
    return fetch(`/items/distinct/${field}/?${p.toString()}`)
      .then((r) => (r.ok ? r.json() : []))
      .catch(() => []);
  }

  function populateOptions(drop, options, param, params, append = false) {
    const container = drop.querySelector('[data-filter-options]');
    if (!append) container.innerHTML = '';
    const current = (params.get(param) || '').split(',').filter(Boolean);
    options.forEach((opt) => {
      const value = typeof opt === 'string' ? opt : opt.value;
      const label = typeof opt === 'string' ? opt : opt.label;
      const wrapper = document.createElement('label');
      wrapper.setAttribute('role', 'menuitemcheckbox');
      wrapper.className = 'flex items-center gap-2';
      wrapper.innerHTML = `<input type="checkbox" class="h-4 w-4" value="${value}" ${current.includes(String(value)) ? 'checked' : ''}> <span>${label}</span>`;
      container.appendChild(wrapper);
    });
  }

  function syncForm(params) {
    const form = document.getElementById('filters');
    if (!form) return;
    form.querySelectorAll('input[type="hidden"]').forEach((el) => {
      if (!params.has(el.name)) el.remove();
    });
    params.forEach((val, key) => {
      let input = form.querySelector(`input[name="${key}"]`);
      if (!input) {
        input = document.createElement('input');
        input.type = 'hidden';
        input.name = key;
        form.appendChild(input);
      }
      input.value = val;
    });
  }

  function applyFilter(drop, btn) {
    const param = btn.dataset.param;
    const params = new URLSearchParams(window.location.search);
    const checkboxes = drop.querySelectorAll('input[type="checkbox"]');
    const search = drop.querySelector('[data-filter-search]');
    if (checkboxes.length) {
      const values = Array.from(checkboxes)
        .filter((c) => c.checked)
        .map((c) => c.value);
      if (values.length) params.set(param, values.join(','));
      else params.delete(param);
    } else if (search) {
      const val = search.value.trim();
      if (val) params.set(param, val); else params.delete(param);
    }
    syncForm(params);
    history.replaceState(null, '', `${window.location.pathname}?${params.toString()}`);
    if (window.htmx) {
      window.htmx.ajax('GET', `/items/table/?${params.toString()}`, '#items-list');
    }
    closeDropdown(drop);
  }

  document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('[data-filter-btn]');
    buttons.forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (btn._dropdown && !btn._dropdown.classList.contains('hidden')) {
          closeDropdown(btn._dropdown);
          return;
        }
        let drop = btn._dropdown;
        if (!drop) {
          drop = createDropdown();
          btn._dropdown = drop;
          document.body.appendChild(drop);
          drop._page = 1;
          const field = btn.dataset.field;
          const params = new URLSearchParams(window.location.search);
          if (field !== 'name') {
            let entry = cache.get(field);
            if (!entry) {
              const data = await fetchOptions(field, params, 1);
              entry = { options: data.slice(), page: 1, done: data.length < LIMIT };
              cache.set(field, entry);
            }
            populateOptions(drop, entry.options, btn.dataset.param, params);
            const showMore = drop.querySelector('[data-show-more]');
            if (!entry.done) showMore.classList.remove('hidden');
            const loadMore = async () => {
              if (entry.done) return;
              const data = await fetchOptions(field, new URLSearchParams(window.location.search), entry.page + 1);
              entry.page += 1;
              entry.options = entry.options.concat(data);
              entry.done = data.length < LIMIT;
              cache.set(field, entry);
              populateOptions(drop, data, btn.dataset.param, new URLSearchParams(window.location.search), true);
              if (entry.done) showMore.classList.add('hidden');
            };
            showMore.addEventListener('click', loadMore);
            const container = drop.querySelector('[data-filter-options]');
            container.addEventListener('scroll', () => {
              if (container.scrollTop + container.clientHeight >= container.scrollHeight - 5) {
                loadMore();
              }
            });
          } else {
            const search = drop.querySelector('[data-filter-search]');
            search.value = params.get(btn.dataset.param) || '';
          }
          drop.querySelector('[data-select-all]').addEventListener('click', () => {
            drop.querySelectorAll('input[type="checkbox"]').forEach((c) => (c.checked = true));
          });
          drop.querySelector('[data-clear]').addEventListener('click', () => {
            drop.querySelectorAll('input[type="checkbox"]').forEach((c) => (c.checked = false));
            const search = drop.querySelector('[data-filter-search]');
            if (search) search.value = '';
          });
          drop.querySelector('[data-apply]').addEventListener('click', () => applyFilter(drop, btn));
          drop._outsideHandler = (ev) => {
            if (!drop.contains(ev.target) && ev.target !== btn) closeDropdown(drop);
          };
        } else {
          const params = new URLSearchParams(window.location.search);
          const field = btn.dataset.field;
          const entry = cache.get(field);
          if (entry) {
            populateOptions(drop, entry.options, btn.dataset.param, params);
            const showMore = drop.querySelector('[data-show-more]');
            if (entry.done) showMore.classList.add('hidden');
            else showMore.classList.remove('hidden');
          }
        }
        positionDropdown(drop, btn);
        drop.classList.remove('hidden');
        document.addEventListener('click', drop._outsideHandler);
        const search = drop.querySelector('[data-filter-search]');
        if (search) search.focus();
      });
    });
  });
})();
