// Tailwind CSS configuration without dark mode
module.exports = {
  content: [
    "./templates/**/*.{html,js}",
    "./static/js/**/*.js",
  ],
  theme: {
    container: {
      center: true,
      screens: {
        sm: '640px',
        md: '768px',
        lg: '1024px',
        xl: '1280px',
        '2xl': '1536px',
      },
      padding: {
        DEFAULT: 'var(--space-8)',
      },
    },
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
      'max-2xl': { max: '1535px' },
    },
    extend: {
      colors: {
        body: 'var(--color-body)',
        bodyText: 'var(--color-body-text)',
        primary: 'var(--color-primary)',
        secondary: 'var(--color-secondary)',
        accent: 'var(--color-accent)',
        danger: 'var(--color-danger)',
        border: 'var(--color-border)',
        form: {
          bg: 'var(--color-body)',
          border: 'var(--color-border)',
          text: 'var(--color-body-text)',
        },
        table: {
          border: 'var(--color-border)',
          headerBg: 'var(--color-primary)',
          headerText: 'var(--color-body)',
          hoverBg: 'var(--color-table-hover-bg)',
        },
      },
      spacing: {
        '0.5': 'var(--space-0-5)',
        '1': 'var(--space-1)',
        '2': 'var(--space-2)',
        '4': 'var(--space-4)',
        '6': 'var(--space-6)',
        '8': 'var(--space-8)',
      },
      fontSize: {
        base: ['var(--font-size-base)', { lineHeight: '1.5' }],
        h1: ['var(--font-size-h1)', { lineHeight: '1.25' }],
        h2: ['var(--font-size-h2)', { lineHeight: '1.3' }],
        badge: ['var(--font-size-badge)', { lineHeight: '1' }],
      },
      fontFamily: {
        sans: ['Roboto', 'sans-serif'],
      },
      boxShadow: {
        'form-focus': '0 0 0 2px rgba(29, 78, 216, 0.4)',
      },
    },
  },
  plugins: [],
}
