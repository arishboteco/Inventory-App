(function() {
  function applyTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }

  document.addEventListener('DOMContentLoaded', function() {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const toggle = document.getElementById('theme-toggle');
    const sun = document.getElementById('theme-icon-sun');
    const moon = document.getElementById('theme-icon-moon');

    function updateToggle(theme) {
      if (!toggle) return;
      toggle.setAttribute('aria-pressed', theme === 'dark');
      if (sun && moon) {
        if (theme === 'dark') {
          sun.classList.add('hidden');
          moon.classList.remove('hidden');
        } else {
          sun.classList.remove('hidden');
          moon.classList.add('hidden');
        }
      }
    }

    const stored = localStorage.getItem('theme');
    let theme;
    if (stored) {
      theme = stored;
    } else {
      theme = mediaQuery.matches ? 'dark' : 'light';
    }
    applyTheme(theme);
    updateToggle(theme);

    if (toggle) {
      toggle.addEventListener('click', function() {
        const newTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
        updateToggle(newTheme);
      });
    }

    mediaQuery.addEventListener('change', function(e) {
      if (!localStorage.getItem('theme')) {
        const newTheme = e.matches ? 'dark' : 'light';
        applyTheme(newTheme);
        updateToggle(newTheme);
      }
    });
  });
})();
