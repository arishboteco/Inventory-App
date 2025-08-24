document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-tabs]').forEach(container => {
    const tabs = container.querySelectorAll('[data-tab-target]');
    const panels = container.querySelectorAll('[role="tabpanel"]');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const target = tab.getAttribute('data-tab-target');
        tabs.forEach(t => {
          t.classList.remove('border-primary', 'text-primary');
          t.setAttribute('aria-selected', 'false');
        });
        panels.forEach(p => p.classList.add('hidden'));
        tab.classList.add('border-primary', 'text-primary');
        tab.setAttribute('aria-selected', 'true');
        const panel = container.querySelector(`#${target}`);
        if (panel) {
          panel.classList.remove('hidden');
        }
      });
    });
  });
});
