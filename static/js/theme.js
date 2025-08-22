(function() {
  function applyTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }
  document.addEventListener('DOMContentLoaded', function() {
    const stored = localStorage.getItem('theme');
    if (stored) {
      applyTheme(stored);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      applyTheme('dark');
    }
    const toggle = document.getElementById('theme-toggle');
    if (toggle) {
      toggle.addEventListener('click', function() {
        const newTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
      });
    }
  });
})();
