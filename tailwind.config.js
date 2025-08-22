module.exports = {
  content: [
    "./templates/**/*.{html,js}",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        body: {
          light: '#f9fafb',
          dark: '#1f2937',
        },
        bodyText: {
          light: '#111827',
          dark: '#ffffff',
        },
        primary: '#1e40af',
        secondary: '#059669',
        accent: '#f59e0b',
        danger: '#dc2626',
        form: {
          bg: '#ffffff',
          border: '#d1d5db',
          text: '#111827',
          darkBg: '#374151',
          darkBorder: '#4b5563',
          darkText: '#f9fafb',
        },
        table: {
          border: '#e5e7eb',
          headerBg: '#1e40af',
          headerText: '#ffffff',
          hoverBg: '#f3f4f6',
          darkBorder: '#4b5563',
          darkHoverBg: '#1f2937',
        },
      },
      fontFamily: {
        sans: ['Roboto', 'sans-serif'],
      },
      boxShadow: {
        'form-focus-light': '0 0 0 2px rgba(30, 64, 175, 0.4)',
        'form-focus-dark': '0 0 0 2px rgba(30, 58, 138, 0.6)',
      },
    },
  },
  darkMode: 'class',
  plugins: [],
}
