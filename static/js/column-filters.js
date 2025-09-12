(function () {
  const cache = new Map();
  const LIMIT = 50;
  const CLIENT_TTL = 30000; // 30s fallback TTL

  function createDropdown() {
    const tpl = document.getElementById("column-filter-dropdown-template");
    if (!tpl) return null;
    return tpl.content.firstElementChild.cloneNode(true);
  }

  function closeDropdown(drop) {
    if (drop) drop.classList.add("hidden");
    document.removeEventListener("click", drop ? drop._outsideHandler : null);
  }

  function positionDropdown(drop, btn) {
    const rect = btn.getBoundingClientRect();
    drop.style.top = `${rect.bottom + window.scrollY}px`;
    drop.style.left = `${rect.left + window.scrollX}px`;
  }

  function fetchOptions(field, params, page = 1) {
    const p = new URLSearchParams(params);
    p.set("limit", LIMIT);
    p.set("page", page);
    return fetch(`/items/distinct/${field}/?${p.toString()}`)
      .then(async (r) => {
        if (!r.ok) return { data: [], ttl: 0 };
        const data = await r.json();
        const cc = r.headers.get("Cache-Control") || "";
        const m = cc.match(/max-age=(\d+)/);
        const ttl = m ? parseInt(m[1], 10) * 1000 : 0;
        return { data, ttl };
      })
      .catch(() => ({ data: [], ttl: 0 }));
  }

  function populateOptions(drop, options, param, params, append = false) {
    const container = drop.querySelector("[data-filter-options]");
    if (!append) container.innerHTML = "";
    const current = (params.get(param) || "").split(",").filter(Boolean);
    options.forEach((opt) => {
      const value = typeof opt === "string" ? opt : opt.value;
      const label = typeof opt === "string" ? opt : opt.label;
      const wrapper = document.createElement("label");
      wrapper.setAttribute("role", "menuitemcheckbox");
      wrapper.className = "flex items-center gap-2";
      wrapper.innerHTML = `<input type="checkbox" class="h-4 w-4" value="${value}" ${current.includes(String(value)) ? "checked" : ""}> <span>${label}</span>`;
      container.appendChild(wrapper);
    });
  }

  function syncForm(params) {
    const form = document.getElementById("filters");
    if (!form) return;
    // Remove hidden inputs that are no longer present and have no visible counterpart
    form.querySelectorAll('input[type="hidden"]').forEach((el) => {
      if (
        !params.has(el.name) &&
        !form.querySelector(`[name="${el.name}"]:not([type="hidden"])`)
      ) {
        el.remove();
      }
    });
    params.forEach((val, key) => {
      const field = form.querySelector(`[name="${key}"]:not([type="hidden"])`);
      if (field) {
        field.value = val;
        field.dispatchEvent(new Event("input"));
      } else {
        let input = form.querySelector(`input[name="${key}"]`);
        if (!input) {
          input = document.createElement("input");
          input.type = "hidden";
          input.name = key;
          form.appendChild(input);
        }
        input.value = val;
      }
    });
  }

  function applyFilter(drop, btn) {
    const param = btn.dataset.param;
    const params = new URLSearchParams(window.location.search);
    const checkboxes = drop.querySelectorAll('input[type="checkbox"]');
    const search = drop.querySelector("[data-filter-search]");
    if (checkboxes.length) {
      const values = Array.from(checkboxes)
        .filter((c) => c.checked)
        .map((c) => c.value);
      if (values.length) params.set(param, values.join(","));
      else params.delete(param);
    } else if (search) {
      const val = search.value.trim();
      if (val) params.set(param, val);
      else params.delete(param);
    }
    syncForm(params);
    history.replaceState(
      null,
      "",
      `${window.location.pathname}?${params.toString()}`,
    );
    if (window.htmx) {
      window.htmx.ajax(
        "GET",
        `/items/table/?${params.toString()}`,
        "#items-list",
      );
    }
    closeDropdown(drop);
  }

  function initColumnFilters(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-filter-btn]").forEach((btn) => {
      if (btn._cfBound) return;
      btn._cfBound = true;
      btn.addEventListener("click", async () => {
        if (btn._dropdown && !btn._dropdown.classList.contains("hidden")) {
          closeDropdown(btn._dropdown);
          return;
        }
        let drop = btn._dropdown;
        if (!drop) {
          drop = createDropdown();
          if (!drop) return;
          btn._dropdown = drop;
          document.body.appendChild(drop);
          const field = btn.dataset.field;
          const params = new URLSearchParams(window.location.search);
          const key = `${field}|${params.toString()}`;
          let entry = cache.get(key);
          const now = Date.now();
          if (!entry || entry.expires < now) {
            const { data, ttl } = await fetchOptions(field, params, 1);
            entry = {
              options: data.slice(),
              page: 1,
              done: data.length < LIMIT,
              expires: now + (ttl || CLIENT_TTL),
            };
            cache.set(key, entry);
          }
          populateOptions(drop, entry.options, btn.dataset.param, params);
          const showMore = drop.querySelector("[data-show-more]");
          if (!entry.done) showMore.classList.remove("hidden");
          const loadMore = async () => {
            if (entry.done) return;
            const { data, ttl } = await fetchOptions(
              field,
              new URLSearchParams(window.location.search),
              entry.page + 1,
            );
            entry.page += 1;
            entry.options = entry.options.concat(data);
            entry.done = data.length < LIMIT;
            entry.expires = Date.now() + (ttl || CLIENT_TTL);
            cache.set(key, entry);
            populateOptions(
              drop,
              data,
              btn.dataset.param,
              new URLSearchParams(window.location.search),
              true,
            );
            if (entry.done) showMore.classList.add("hidden");
          };
          showMore.addEventListener("click", loadMore);
          const container = drop.querySelector("[data-filter-options]");
          container.addEventListener("scroll", () => {
            if (
              container.scrollTop + container.clientHeight >=
              container.scrollHeight - 5
            ) {
              loadMore();
            }
          });
          drop
            .querySelector("[data-select-all]")
            .addEventListener("click", () => {
              drop
                .querySelectorAll('input[type="checkbox"]')
                .forEach((c) => (c.checked = true));
            });
          drop.querySelector("[data-clear]").addEventListener("click", () => {
            drop
              .querySelectorAll('input[type="checkbox"]')
              .forEach((c) => (c.checked = false));
            const search = drop.querySelector("[data-filter-search]");
            if (search) search.value = "";
          });
          drop
            .querySelector("[data-apply]")
            .addEventListener("click", () => applyFilter(drop, btn));
          drop._outsideHandler = (ev) => {
            if (!drop.contains(ev.target) && ev.target !== btn)
              closeDropdown(drop);
          };
        } else {
          const params = new URLSearchParams(window.location.search);
          const key = `${btn.dataset.field}|${params.toString()}`;
          const entry = cache.get(key);
          if (entry) {
            populateOptions(drop, entry.options, btn.dataset.param, params);
            const showMore = drop.querySelector("[data-show-more]");
            if (entry.done) showMore.classList.add("hidden");
            else showMore.classList.remove("hidden");
          }
        }
        positionDropdown(drop, btn);
        drop.classList.remove("hidden");
        document.addEventListener("click", drop._outsideHandler);
        const search = drop.querySelector("[data-filter-search]");
        if (search) search.focus();
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => initColumnFilters());
  document.body.addEventListener("htmx:afterSwap", (e) =>
    initColumnFilters(e.target),
  );
})();
