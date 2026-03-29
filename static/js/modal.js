(function () {
  // Simple in-memory cache for prefetched modal content
  const MODAL_CACHE = new Map(); // key: url, value: { html, ts }
  const CACHE_TTL_MS = 60 * 1000; // 1 minute
  const INFLIGHT = new Map(); // url -> promise
  let prefetchTimer = null;
  let lastFocused = null;
  let trapHandler = null;
  function trapFocus(container) {
    if (trapHandler) container.removeEventListener("keydown", trapHandler);
    const focusable = container.querySelectorAll(
      'a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])',
    );
    if (!focusable.length) {
      container.focus();
      trapHandler = null;
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    trapHandler = function (e) {
      if (e.key !== "Tab") return;
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    container.addEventListener("keydown", trapHandler);
    first.focus();
  }
  function setAria(root, content) {
    const heading = content.querySelector("h1, h2, h3, h4, h5, h6");
    if (heading) {
      const id = heading.id || "modal-heading";
      heading.id = id;
      root.setAttribute("aria-labelledby", id);
    } else {
      root.removeAttribute("aria-labelledby");
    }
  }
  function openModal(html, { skipInit = false } = {}) {
    const root = document.getElementById("modal-root");
    const content = document.getElementById("modal-content");
    if (!root || !content) return;
    lastFocused = document.activeElement;
    content.innerHTML = html;
    if (!skipInit) {
      // Defer heavy enhancements to next frame to keep first paint snappy
      requestAnimationFrame(() => {
        if (window.initMultiselectChips) window.initMultiselectChips(content);
        // Initialize indent form first so it can mark inputs to opt out of overlays
        if (window.initIndentForm) window.initIndentForm(content);
        if (window.initPredictiveDropdowns)
          window.initPredictiveDropdowns(content);
        if (window.initPredictiveDatalistOverlay)
          window.initPredictiveDatalistOverlay(content);
        if (window.initRecipeComponentsTable)
          window.initRecipeComponentsTable(content);
      });
    }
    setAria(root, content);
    root.classList.remove("hidden");
    trapFocus(root);
  }
  function openDrawer(html, side = "right", { skipInit = false } = {}) {
    const root = document.getElementById("modal-root");
    const content = document.getElementById("modal-content");
    if (!root || !content) return;
    lastFocused = document.activeElement;
    content.innerHTML = `<div class="drawer ${side} wide">${html}</div>`;
    if (!skipInit) {
      requestAnimationFrame(() => {
        if (window.initMultiselectChips) window.initMultiselectChips(content);
        if (window.initIndentForm) window.initIndentForm(content);
        if (window.initPredictiveDropdowns)
          window.initPredictiveDropdowns(content);
        if (window.initPredictiveDatalistOverlay)
          window.initPredictiveDatalistOverlay(content);
        if (window.initRecipeComponentsTable)
          window.initRecipeComponentsTable(content);
      });
    }
    setAria(root, content);
    root.classList.remove("hidden");
    trapFocus(root);
  }
  function openLoading(type, url) {
    // Specialized skeleton for heavy drawers (create & edit item)
    let markup;
    if (
      type === "drawer" &&
      url &&
      /(item_create_partial|\/items\/\d+\/edit\/)/.test(url)
    ) {
      const isEdit = /\/items\/\d+\/edit\//.test(url);
      const heading = isEdit ? "Edit Item" : "Add New Item";
      markup = `
        <div class="bg-white rounded-xl shadow border border-gray-200 overflow-hidden drawer-panel max-w-drawer-xl" aria-busy="true">
          <div class="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
            <h3 class="text-lg font-semibold">${heading}</h3>
            <button type="button" class="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md transition focus:outline-none bg-white text-gray-400 border border-border cursor-wait" disabled>Loading…</button>
          </div>
          <div class="p-4 space-y-4">
            <div class="grid grid-cols-2 gap-3">
              ${Array.from({ length: 8 })
                .map(
                  () => `
                <div class=\"space-y-1\">
                  <div class=\"h-4 w-28 bg-gray-200 rounded\"></div>
                  <div class=\"h-9 w-full bg-gray-100 rounded border border-gray-200 animate-pulse\"></div>
                </div>`,
                )
                .join("")}
              <div class="col-span-2 space-y-1">
                <div class="h-4 w-32 bg-gray-200 rounded"></div>
                <div class="h-20 w-full bg-gray-100 rounded border border-gray-200 animate-pulse"></div>
              </div>
            </div>
            <div class="flex justify-end gap-2 pt-2">
              <div class="h-9 w-24 bg-gray-100 rounded border border-gray-200 animate-pulse"></div>
              <div class="h-9 w-28 bg-gray-100 rounded border border-gray-200 animate-pulse"></div>
            </div>
          </div>
        </div>`;
      openDrawer(markup, "right", { skipInit: true });
      return;
    }
    const spinner = `<div class="p-6 flex items-center justify-center" aria-live="polite"><div class="flex flex-col items-center gap-3"><div class="animate-spin h-6 w-6 rounded-full border-2 border-gray-300 border-t-primary" aria-label="Loading"></div><p class="text-sm text-gray-500">Loading…</p></div></div>`;
    if (type === "drawer") openDrawer(spinner, "right", { skipInit: true });
    else openModal(spinner, { skipInit: true });
  }

  function cacheSet(url, html) {
    MODAL_CACHE.set(url, { html, ts: Date.now() });
  }
  function cacheGet(url) {
    const entry = MODAL_CACHE.get(url);
    if (!entry) return null;
    if (Date.now() - entry.ts > CACHE_TTL_MS) {
      MODAL_CACHE.delete(url);
      return null;
    }
    return entry.html;
  }

  function triggerHtmxEvents(config, fallbackDetail) {
    if (!config) return;
    const entries = Array.isArray(config)
      ? config
      : Array.isArray(config.events)
        ? config.events
        : [config];
    entries.forEach((entry) => {
      if (!entry) return;
      const name = entry.event || entry.name;
      if (!name) return;
      const target = entry.target
        ? document.querySelector(entry.target)
        : document.body;
      if (!target) return;
      let detail;
      if (entry.detail !== undefined) detail = entry.detail;
      else if (fallbackDetail !== undefined) detail = fallbackDetail;
      else detail = null;
      if (window.htmx && typeof window.htmx.trigger === "function") {
        window.htmx.trigger(target, name, detail);
      } else {
        target.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
      }
    });
  }

  // Prefetch helper
  function prefetch(url) {
    if (!url) return;
    if (cacheGet(url)) return;
    if (INFLIGHT.has(url)) return;
    const p = fetch(url)
      .then((r) => (r.ok ? r.text() : Promise.reject()))
      .then((html) => {
        cacheSet(url, html);
        INFLIGHT.delete(url);
      })
      .catch(() => {
        INFLIGHT.delete(url);
      });
    INFLIGHT.set(url, p);
  }

  function schedulePrefetch(el) {
    const url = el.getAttribute("data-modal-url");
    if (!url || cacheGet(url)) return;
    if (INFLIGHT.has(url)) return; // already fetching
    // Small debounce to avoid spamming network when cursor just passes by
    if (prefetchTimer) clearTimeout(prefetchTimer);
    prefetchTimer = setTimeout(() => {
      const p = fetch(url)
        .then((r) => (r.ok ? r.text() : Promise.reject()))
        .then((html) => {
          cacheSet(url, html);
          INFLIGHT.delete(url);
        })
        .catch(() => {
          INFLIGHT.delete(url);
        });
      INFLIGHT.set(url, p);
    }, 120);
  }
  function closeModal() {
    const root = document.getElementById("modal-root");
    const content = document.getElementById("modal-content");
    if (!root || !content) return;
    root.classList.add("hidden");
    root.removeAttribute("aria-labelledby");
    content.innerHTML = "";
    try {
      root.dispatchEvent(new CustomEvent("modal:close", { bubbles: true }));
    } catch (_) {}
    if (lastFocused && typeof lastFocused.focus === "function") {
      lastFocused.focus();
      lastFocused = null;
    }
  }

  // public API
  window.modal = { open: openModal, openDrawer, close: closeModal };

  // delegation for close and open events
  document.addEventListener("click", function (e) {
    const tgt = e.target;
    if (!(tgt instanceof Element)) return;
    if (tgt.closest("[data-modal-close]")) {
      closeModal();
      return;
    }
    const opener = tgt.closest("[data-modal-url]");
    if (opener) {
      e.preventDefault();
      const url = opener.getAttribute("data-modal-url");
      const type = opener.getAttribute("data-modal-type") || "modal";
      const inlineTplId = opener.getAttribute("data-modal-inline-template");
      const noFetch = opener.hasAttribute("data-modal-no-fetch");
      const cached = cacheGet(url);
      if (cached) {
        // Open immediately with cached content
        if (type === "drawer") openDrawer(cached, "right");
        else openModal(cached);
      } else {
        // If this is the create item drawer, try inline template first
        let openedFromInline = false;
        if (type === "drawer" && /item_create_partial/.test(url)) {
          const tpl = inlineTplId
            ? document.getElementById(inlineTplId)
            : document.getElementById("inline-item-create-drawer");
          if (tpl && tpl.innerHTML.trim()) {
            openDrawer(tpl.innerHTML, "right");
            openedFromInline = true;
          }
        }
        // If configured to skip fetch (inline template is authoritative) stop here.
        if (openedFromInline && noFetch) {
          return;
        }
        if (!openedFromInline) openLoading(type, url);
        // Fallback: if still loading after 1500ms, force inline template (if present)
        if (!openedFromInline && inlineTplId) {
          setTimeout(() => {
            if (cacheGet(url)) return; // content arrived
            const root = document.getElementById("modal-root");
            if (!root || root.classList.contains("hidden")) return;
            const content = document.getElementById("modal-content");
            if (!content) return;
            if (
              content.textContent &&
              content.textContent.includes("Loading")
            ) {
              const tpl = document.getElementById(inlineTplId);
              if (tpl && tpl.innerHTML.trim()) {
                openDrawer(tpl.innerHTML, "right");
                if (window.console)
                  console.debug(
                    "[modal] fallback inline drawer shown after timeout",
                    url,
                  );
              }
            }
          }, 1500);
        }
        const doFetch = () =>
          fetch(url)
            .then((r) => (r.ok ? r.text() : Promise.reject()))
            .then((html) => {
              cacheSet(url, html);
              if (type === "drawer") {
                if (openedFromInline) {
                  const existing = document.getElementById("modal-content");
                  const currentLen = existing ? existing.textContent.length : 0;
                  const newLen = html.length;
                  if (Math.abs(currentLen - newLen) < 50) return; // skip repaint
                }
                openDrawer(html, "right");
              } else openModal(html);
            })
            .catch(() => {
              if (!openedFromInline) {
                const msg =
                  '<div class="p-6 text-sm text-red-600">Failed to load content. <button type="button" data-modal-close class="underline">Close</button></div>';
                if (type === "drawer") openDrawer(msg, "right");
                else openModal(msg);
              }
              if (window.notifications)
                window.notifications.showToast(
                  "Failed to load content",
                  "error",
                );
            });
        if (!noFetch) {
          if (INFLIGHT.has(url)) {
            INFLIGHT.get(url).then(() => {
              const html = cacheGet(url);
              if (html) {
                if (type === "drawer") openDrawer(html, "right");
                else openModal(html);
              }
            });
          } else {
            const p = doFetch();
            INFLIGHT.set(url, p);
          }
        }
      }
    }
  });

  // Hover/focus prefetch for annotated triggers
  document.addEventListener("pointerenter", function (e) {
    const tgt = e.target;
    if (!(tgt instanceof Element)) return;
    const el = tgt.closest('[data-modal-url][data-modal-prefetch="hover"]');
    if (!el) return;
    const url = el.getAttribute("data-modal-url");
    prefetch(url);
  });
  document.addEventListener("focusin", function (e) {
    const tgt = e.target;
    if (!(tgt instanceof Element)) return;
    const el = tgt.closest('[data-modal-url][data-modal-prefetch="hover"]');
    if (!el) return;
    const url = el.getAttribute("data-modal-url");
    prefetch(url);
  });

  // Idle prefetch for elements marked eager/idle
  function prefetchMarked() {
    const eager = document.querySelectorAll(
      '[data-modal-url][data-modal-prefetch="eager"]',
    );
    eager.forEach((el) => prefetch(el.getAttribute("data-modal-url")));
    const idle = () => {
      const els = document.querySelectorAll(
        '[data-modal-url][data-modal-prefetch="idle"]',
      );
      els.forEach((el) => prefetch(el.getAttribute("data-modal-url")));
    };
    if (window.requestIdleCallback)
      requestIdleCallback(idle, { timeout: 1200 });
    else setTimeout(idle, 800);
  }
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", prefetchMarked);
  else prefetchMarked();

  // Prefetch on hover / focus for perceived instant open
  document.addEventListener(
    "mouseover",
    (e) => {
      const tgt = e.target;
      if (!(tgt instanceof Element)) return;
      const opener = tgt.closest("[data-modal-url]");
      if (opener) schedulePrefetch(opener);
    },
    { passive: true },
  );
  document.addEventListener(
    "focusin",
    (e) => {
      const tgt = e.target;
      if (!(tgt instanceof Element)) return;
      const opener = tgt.closest("[data-modal-url]");
      if (opener) schedulePrefetch(opener);
    },
    { passive: true },
  );

  // Eager prefetch for elements marked with data-modal-prefetch="eager"
  document.addEventListener("DOMContentLoaded", () => {
    // Use idle callback if available to reduce main-thread contention
    const eager = Array.from(
      document.querySelectorAll(
        '[data-modal-url][data-modal-prefetch="eager"]',
      ),
    );
    const prefetchFn = () => {
      eager.forEach((el) => schedulePrefetch(el));
    };
    // Prime cache with any inline templates so first open is instant
    document.querySelectorAll("[data-modal-inline-template]").forEach((btn) => {
      const url = btn.getAttribute("data-modal-url");
      const tplId = btn.getAttribute("data-modal-inline-template");
      if (!url || !tplId || cacheGet(url)) return;
      const tpl = document.getElementById(tplId);
      if (tpl && tpl.innerHTML.trim()) {
        cacheSet(url, tpl.innerHTML);
        if (window.console)
          console.debug("[modal] primed cache from inline template", url);
      }
    });
    // Idle prefetch for first visible edit item link to remove first-click delay
    const prefetchFirstEdit = () => {
      // Find first edit link with data-modal-url containing /items/<id>/edit/
      const editLinks = Array.from(
        document.querySelectorAll("[data-modal-url]"),
      ).filter((el) =>
        /\/items\/\d+\/edit\//.test(el.getAttribute("data-modal-url") || ""),
      );
      if (editLinks.length) {
        schedulePrefetch(editLinks[0]);
        if (window.console)
          console.debug(
            "[modal] idle prefetched first edit drawer",
            editLinks[0].getAttribute("data-modal-url"),
          );
        // Staged prefetch of next few edit links (2-4) for likely early interactions
        const more = editLinks.slice(1, 4);
        more.forEach((el, idx) => {
          setTimeout(
            () => {
              if (!cacheGet(el.getAttribute("data-modal-url"))) {
                schedulePrefetch(el);
                if (window.console)
                  console.debug(
                    "[modal] staged prefetched edit drawer",
                    el.getAttribute("data-modal-url"),
                  );
              }
            },
            300 + idx * 180,
          ); // stagger to avoid burst
        });
      }
    };
    if ("requestIdleCallback" in window) {
      window.requestIdleCallback(prefetchFirstEdit, { timeout: 2000 });
    } else {
      setTimeout(prefetchFirstEdit, 350);
    }
    // Idle prefetch for first few View Details modals as well
    const prefetchFirstView = () => {
      const viewLinks = Array.from(
        document.querySelectorAll("[data-modal-url]"),
      ).filter((el) => {
        const u = el.getAttribute("data-modal-url") || "";
        // Match /items/<id>/ with optional ?partial=1, but exclude /edit/
        return /\/items\/\d+\/?/.test(u) && !/\/edit\//.test(u);
      });
      if (viewLinks.length) {
        schedulePrefetch(viewLinks[0]);
        const more = viewLinks.slice(1, 4);
        more.forEach((el, idx) => {
          setTimeout(
            () => {
              if (!cacheGet(el.getAttribute("data-modal-url"))) {
                schedulePrefetch(el);
              }
            },
            300 + idx * 180,
          );
        });
      }
    };
    if ("requestIdleCallback" in window) {
      window.requestIdleCallback(prefetchFirstView, { timeout: 2200 });
    } else {
      setTimeout(prefetchFirstView, 420);
    }
    if ("requestIdleCallback" in window) {
      window.requestIdleCallback(prefetchFn, { timeout: 1500 });
    } else {
      setTimeout(prefetchFn, 0);
    }

    // Viewport-based prefetch: when edit drawers become visible, prefetch once.
    function primeViewportPrefetch(root = document) {
      if (!("IntersectionObserver" in window)) return;
      const candidates = Array.from(
        root.querySelectorAll("[data-modal-url]"),
      ).filter((el) =>
        /\/items\/\d+\/edit\//.test(el.getAttribute("data-modal-url") || ""),
      );
      if (!candidates.length) return;
      let budget = 12; // safety cap per page view
      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (budget <= 0) return;
            if (entry.isIntersecting) {
              const el = entry.target;
              schedulePrefetch(el);
              io.unobserve(el);
              budget -= 1;
            }
          });
        },
        { rootMargin: "120px" },
      );
      candidates.forEach((el) => io.observe(el));
    }
    primeViewportPrefetch(document);
    document.addEventListener("htmx:afterSwap", (e) => {
      if (e && e.target) primeViewportPrefetch(e.target);
    });
  });

  // Intercept modal form submits for partial saves
  document.addEventListener("submit", function (e) {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (!form.hasAttribute("data-modal-form")) return;
    e.preventDefault();
    try {
      // Pre-submit guard: sync department hidden field from UI select if present
      try {
        const hiddenDept = form.querySelector("#id_department");
        const uiDept = form.querySelector("#department-ui");
        if (hiddenDept && uiDept) {
          hiddenDept.value = uiDept.value;
        }
      } catch (err) {
        /* non-fatal */
      }
      const csrf = form.querySelector(
        'input[name="csrfmiddlewaretoken"]',
      )?.value;
      // Client-side preflight validation for better UX
      const showInlineError = (msg) => {
        try {
          let alert = form.querySelector("[data-modal-error]");
          if (!alert) {
            alert = document.createElement("div");
            alert.setAttribute("data-modal-error", "");
            alert.className =
              "mb-3 px-3 py-2 rounded-md border border-red-200 bg-red-50 text-red-700 text-sm";
            form.insertBefore(alert, form.firstElementChild);
          }
          alert.textContent = msg;
          alert.scrollIntoView({ behavior: "smooth", block: "center" });
        } catch (_) {}
      };
      const cssEscape = (s) => {
        try {
          return window.CSS && window.CSS.escape
            ? window.CSS.escape(String(s))
            : String(s);
        } catch (_) {
          return String(s);
        }
      };
      const hiddenDept = form.querySelector("#id_department");
      const uiDept = form.querySelector("#department-ui");
      if (hiddenDept && uiDept) hiddenDept.value = uiDept.value;
      if (hiddenDept && !hiddenDept.value) {
        showInlineError("Please select a department");
        if (window.notifications)
          window.notifications.showToast("Please select a department", "error");
        return;
      }
      // Ensure at least one valid line (item id + positive qty) only when form opts in
      const requiresLineItems = form.hasAttribute("data-requires-line-items");
      if (requiresLineItems) {
        let hasValidLine = false;
        let checkedSources = false;
        const hiddenItems = Array.from(
          form.querySelectorAll('input[type="hidden"][data-item-hidden-for]'),
        );
        if (hiddenItems.length) {
          checkedSources = true;
          for (const h of hiddenItems) {
            const name = h.getAttribute("data-item-hidden-for") || h.name || "";
            if (!name) continue;
            const qtyName = name.replace(/-item$/, "-requested_qty");
            const qty = form.querySelector(
              `input[name="${cssEscape(qtyName)}"]`,
            );
            const qtyVal = qty ? parseFloat(qty.value) : NaN;
            if ((h.value || "").trim() && !Number.isNaN(qtyVal) && qtyVal > 0) {
              hasValidLine = true;
              break;
            }
          }
        }
        if (!hasValidLine) {
          const inlineItems = Array.from(
            form.querySelectorAll(
              'select[name^="items-"][name$="-item"], select[name^="items-"][name$="-ingredient"]',
            ),
          );
          if (inlineItems.length) {
            checkedSources = true;
            for (const select of inlineItems) {
              const value = (select.value || "").trim();
              if (!value) continue;
              const baseName = (select.name || "").replace(
                /-(item|ingredient)$/,
                "",
              );
              if (!baseName) continue;
              const qtyField =
                form.querySelector(
                  `input[name="${cssEscape(`${baseName}-quantity`)}"]`,
                ) ||
                form.querySelector(
                  `input[name="${cssEscape(`${baseName}-quantity_ordered`)}"]`,
                );
              const qtyVal = qtyField ? parseFloat(qtyField.value) : NaN;
              if (!Number.isNaN(qtyVal) && qtyVal > 0) {
                hasValidLine = true;
                break;
              }
            }
          }
        }
        if (checkedSources && !hasValidLine) {
          showInlineError("Add at least one item with a positive quantity");
          if (window.notifications)
            window.notifications.showToast(
              "Add at least one item with a positive quantity",
              "error",
            );
          return;
        }
      }

      const fd = new FormData(form);
      fd.set("partial", "1");
      const url = form.getAttribute("action") || window.location.href;
      const headers = Object.assign(
        { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
        csrf ? { "X-CSRFToken": csrf } : {},
      );
      fetch(url, {
        method: "POST",
        headers,
        body: fd,
        credentials: "same-origin",
      })
        .then(async (r) => {
          const ct = r.headers.get("content-type") || "";
          let data = null;
          if (ct.includes("application/json")) {
            try {
              data = await r.json();
            } catch (_) {
              data = null;
            }
          }
          if (!data) {
            try {
              const txt = await r.text();
              // Try to extract a meaningful message from HTML/text
              const msg =
                txt && txt.slice ? txt.slice(0, 400) : "Unexpected response";
              data = { ok: false, message: r.statusText || msg };
            } catch (_) {
              data = { ok: false, message: r.statusText || "Request failed" };
            }
          }
          if (r.ok && data && data.ok) {
            const shouldToast = data.toast !== false;
            const toastMsg = data.toast_message || data.message || "Saved";
            const toastType = data.toast_type || "success";
            if (shouldToast && window.notifications)
              window.notifications.showToast(toastMsg, toastType);
            closeModal();
            try {
              document.body.dispatchEvent(
                new CustomEvent("modal:success", {
                  detail: data,
                  bubbles: true,
                }),
              );
            } catch (_) {}
            // Success navigation: prefer explicit redirect if provided; otherwise
            // defer to flags returned by the server response.
            if (data && data.redirect) {
              try {
                window.location.href = data.redirect;
                return;
              } catch (_) {}
            }
            const reloadInstruction = data ? data.reload : undefined;
            const closeOnly = Boolean(data && data.close_only);
            const fallbackDetail = (data && data.recipe) || data;
            if (reloadInstruction && typeof reloadInstruction === "object") {
              const reloadUrl = reloadInstruction.url;
              const reloadTarget = reloadInstruction.target;
              if (
                reloadUrl &&
                reloadTarget &&
                window.htmx &&
                window.htmx.ajax
              ) {
                window.htmx.ajax("GET", reloadUrl, { target: reloadTarget });
                return;
              }
              if (reloadUrl) {
                window.location.href = reloadUrl;
                return;
              }
            }
            if (typeof reloadInstruction === "string") {
              window.location.href = reloadInstruction;
              return;
            }
            if (reloadInstruction === true) {
              window.location.reload();
              return;
            }
            if (closeOnly || reloadInstruction === false) {
              triggerHtmxEvents(data && data.htmx, fallbackDetail);
              triggerHtmxEvents(data && data.events, fallbackDetail);
              triggerHtmxEvents(data && data.trigger, fallbackDetail);
              return;
            }
            // Legacy fallback for endpoints that have not been updated yet.
            window.location.reload();
          } else {
            // Show inline error inside the modal form for better visibility
            const msg =
              (data && data.message) ||
              `${r.status} ${r.statusText || "Save failed"}`;
            showInlineError(msg);
            if (window.console)
              console.debug("[modal] submit failed", {
                status: r.status,
                statusText: r.statusText,
                data,
              });
            const toastType = (data && data.toast_type) || "error";
            if (window.notifications && data && data.toast !== false)
              window.notifications.showToast(msg, toastType);
          }
        })
        .catch(() => {
          const msg = "Network error";
          showInlineError(msg);
          if (window.notifications)
            window.notifications.showToast(msg, "error");
        });
    } catch (fatal) {
      // Surface any unexpected runtime error to the UI so it doesn't fail silently
      const msg =
        fatal && fatal.message
          ? `Unexpected error: ${fatal.message}`
          : "Unexpected error";
      try {
        let alert =
          form.querySelector("[data-modal-error]") ||
          document.createElement("div");
        alert.setAttribute("data-modal-error", "");
        alert.className =
          "mb-3 px-3 py-2 rounded-md border border-red-200 bg-red-50 text-red-700 text-sm";
        alert.textContent = msg;
        if (!alert.parentElement)
          form.insertBefore(alert, form.firstElementChild);
      } catch (_) {}
      if (window.console) console.error("[modal] fatal submit error", fatal);
      if (window.notifications) window.notifications.showToast(msg, "error");
    }
  });
})();
