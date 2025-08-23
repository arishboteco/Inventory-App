(function() {
  function applyTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }

  // Apply the user's preferred theme immediately to avoid flashes of incorrect styling
  const stored = localStorage.getItem('theme');
  if (stored) {
    applyTheme(stored);
  } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    applyTheme('dark');
  }

  document.addEventListener('DOMContentLoaded', function() {
    const toggle = document.getElementById('theme-toggle');
    if (toggle) {
      toggle.addEventListener('click', function() {
        const newTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
      });
    }

    ['primary', 'secondary', 'accent'].forEach(function(key) {
      const storedColor = localStorage.getItem('color-' + key);
      const picker = document.getElementById('picker-' + key);
      if (storedColor) {
        document.documentElement.style.setProperty('--color-' + key, storedColor);
        if (picker) {
          picker.value = storedColor;
        }
      }
      if (picker) {
        picker.addEventListener('input', function() {
          document.documentElement.style.setProperty('--color-' + key, picker.value);
          localStorage.setItem('color-' + key, picker.value);
        });
      }
    });

    const reset = document.getElementById('colour-reset');
    if (reset) {
      reset.addEventListener('click', function() {
        ['primary', 'secondary', 'accent'].forEach(function(key) {
          const picker = document.getElementById('picker-' + key);
          if (picker) {
            const defaultVal = picker.getAttribute('value');
            document.documentElement.style.setProperty('--color-' + key, defaultVal);
            picker.value = defaultVal;
          }
          localStorage.removeItem('color-' + key);
        });
      });
    }
  });
})();
