module.exports = {
  content: [
    "./templates/**/*.{html,js}",
    "./static/js/**/*.js",
  ],
  theme: {
    screens: {
      sm: '640px',
      md: '768px',
      lg: '1024px',
      xl: '1280px',
      '2xl': '1536px',
      'max-sm': { max: '639px' },
      'max-md': { max: '767px' },
      'max-lg': { max: '1023px' },
      'max-xl': { max: '1279px' },
    },
    extend: {
      colors: {
        body: {
          light: '#ffffff',
          dark: '#0f172a',
        },
        bodyText: {
          light: '#111827',
          dark: '#f8fafc',
        },
        primary: 'var(--color-primary)',
        secondary: 'var(--color-secondary)',
        accent: 'var(--color-accent)',
        danger: 'var(--color-danger)',
        form: {
          bg: '#ffffff',
          border: '#6b7280',
          text: '#111827',
          darkBg: '#1e293b',
          darkBorder: '#64748b',
          darkText: '#f8fafc',
        },
        table: {
          border: '#6b7280',
          headerBg: 'var(--color-primary)',
          headerText: '#ffffff',
          hoverBg: '#e5e7eb',
          darkBorder: '#64748b',
          darkHoverBg: '#1e293b',
        },
      },
      spacing: {
        '0.5': 'var(--space-0-5)',
        '1': 'var(--space-1)',
        '2': 'var(--space-2)',
        '4': 'var(--space-4)',
      },
      fontSize: {
        base: 'var(--font-size-base)',
        h1: 'var(--font-size-h1)',
        h2: 'var(--font-size-h2)',
        badge: 'var(--font-size-badge)',
      },
      fontFamily: {
        sans: ['Roboto', 'sans-serif'],
      },
      boxShadow: {
        'form-focus-light': '0 0 0 2px rgba(29, 78, 216, 0.4)',
        'form-focus-dark': '0 0 0 2px rgba(29, 78, 216, 0.6)',
      },
    },
  },
  darkMode: 'class',
  plugins: [],
}
