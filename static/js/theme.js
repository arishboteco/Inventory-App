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

  function hexToRgb(hex) {
    const res = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return res ? [parseInt(res[1], 16), parseInt(res[2], 16), parseInt(res[3], 16)] : [0, 0, 0];
  }

  function luminance(hex) {
    const rgb = hexToRgb(hex).map(function(v) {
      v = v / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
  }

  function contrast(hex1, hex2) {
    const lum1 = luminance(hex1);
    const lum2 = luminance(hex2);
    const brightest = Math.max(lum1, lum2);
    const darkest = Math.min(lum1, lum2);
    return (brightest + 0.05) / (darkest + 0.05);
  }

  function passesContrast(color) {
    const lightBg = '#ffffff';
    const darkBg = '#0f172a';
    return contrast(color, lightBg) >= 4.5 && contrast(color, darkBg) >= 4.5;
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

    const feedback = document.getElementById('colour-feedback');
    const lastColors = {};

    ['primary', 'secondary', 'accent'].forEach(function(key) {
      const picker = document.getElementById('picker-' + key);
      if (!picker) { return; }

      const storedColor = localStorage.getItem('color-' + key);
      const initial = storedColor || picker.getAttribute('value');
      if (initial) {
        document.documentElement.style.setProperty('--color-' + key, initial);
        picker.value = initial;
        lastColors[key] = initial;
      }

      picker.addEventListener('input', function() {
        const newColor = picker.value;
        if (passesContrast(newColor)) {
          document.documentElement.style.setProperty('--color-' + key, newColor);
          localStorage.setItem('color-' + key, newColor);
          lastColors[key] = newColor;
          if (feedback) {
            feedback.textContent = '';
            feedback.classList.add('hidden');
          }
        } else {
          if (feedback) {
            feedback.textContent = 'Selected colour does not meet contrast guidelines and was reset.';
            feedback.classList.remove('hidden');
          }
          picker.value = lastColors[key];
        }
      });
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
            lastColors[key] = defaultVal;
          }
          localStorage.removeItem('color-' + key);
        });
        if (feedback) {
          feedback.textContent = '';
          feedback.classList.add('hidden');
        }
      });
    }
  });
})();
