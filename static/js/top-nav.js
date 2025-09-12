// Enhanced accessible grouped navigation menu
function initTopNav(doc = document) {
  const container = doc.querySelector('[data-top-nav]');
  if (!container) return;
  const groups = Array.from(container.querySelectorAll('[data-nav-group]'));

  function closeAll(except = null) {
    groups.forEach(g => {
      if (g === except) return;
      const btn = g.querySelector('[data-nav-trigger]');
      const panel = g.querySelector('[data-nav-panel]');
      if (btn && panel && btn.getAttribute('aria-expanded') === 'true') {
        btn.setAttribute('aria-expanded', 'false');
        panel.classList.add('hidden');
      }
    });
  }

  groups.forEach((group, groupIndex) => {
    const button = group.querySelector('[data-nav-trigger]');
    const panel = group.querySelector('[data-nav-panel]');
    if (!button || !panel) return;
    button.setAttribute('aria-expanded', 'false');
    panel.classList.add('hidden');

    // Toggle click
    button.addEventListener('click', () => {
      const expanded = button.getAttribute('aria-expanded') === 'true';
      if (expanded) {
        button.setAttribute('aria-expanded', 'false');
        panel.classList.add('hidden');
      } else {
        closeAll(group);
        button.setAttribute('aria-expanded', 'true');
        panel.classList.remove('hidden');
        focusFirstLink(panel);
      }
    });

    // Keyboard on trigger
    button.addEventListener('keydown', (e) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          if (button.getAttribute('aria-expanded') !== 'true') {
            closeAll(group);
            button.setAttribute('aria-expanded', 'true');
            panel.classList.remove('hidden');
          }
          focusFirstLink(panel);
          break;
        case 'ArrowUp':
          e.preventDefault();
          if (button.getAttribute('aria-expanded') !== 'true') {
            closeAll(group);
            button.setAttribute('aria-expanded', 'true');
            panel.classList.remove('hidden');
          }
          focusLastLink(panel);
          break;
        case 'ArrowRight':
          e.preventDefault();
          moveToGroup(groupIndex + 1);
          break;
        case 'ArrowLeft':
          e.preventDefault();
          moveToGroup(groupIndex - 1);
          break;
        case 'Escape':
          closeAll();
          button.focus();
          break;
        default:
          break;
      }
    });

    // Panel key handling
    panel.addEventListener('keydown', (e) => {
      const links = getLinks(panel);
      const currentIndex = links.indexOf(doc.activeElement);
      if (e.key === 'Escape') {
        closeAll();
        button.focus();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        links[(currentIndex + 1) % links.length].focus();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        links[(currentIndex - 1 + links.length) % links.length].focus();
      } else if (e.key === 'Tab') {
        // Close on tab out
        if (!e.shiftKey && currentIndex === links.length - 1) {
          closeAll();
        } else if (e.shiftKey && currentIndex === 0) {
          closeAll();
        }
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        moveToGroup(groupIndex + 1, { openPanel: true });
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        moveToGroup(groupIndex - 1, { openPanel: true });
      }
    });
  });

  function getLinks(panel) {
    return Array.from(panel.querySelectorAll('[data-nav-link]'));
  }
  function focusFirstLink(panel) {
    const first = getLinks(panel)[0];
    if (first) setTimeout(() => first.focus(), 0);
  }
  function focusLastLink(panel) {
    const links = getLinks(panel);
    const last = links[links.length - 1];
    if (last) setTimeout(() => last.focus(), 0);
  }
  function moveToGroup(index, { openPanel = false } = {}) {
    if (!groups.length) return;
    const newIndex = (index + groups.length) % groups.length;
    const g = groups[newIndex];
    const btn = g.querySelector('[data-nav-trigger]');
    const panel = g.querySelector('[data-nav-panel]');
    if (btn) {
      btn.focus();
      if (openPanel && panel) {
        closeAll(g);
        btn.setAttribute('aria-expanded', 'true');
        panel.classList.remove('hidden');
        focusFirstLink(panel);
      }
    }
  }

  // Close when clicking outside (capture phase)
  doc.addEventListener('click', (e) => {
    if (!container.contains(e.target)) {
      closeAll();
    }
  });
}

if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => initTopNav());
  window.topNav = { initTopNav };
}

// Export for test environments (Jest/CommonJS) without breaking browsers
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { initTopNav };
}
