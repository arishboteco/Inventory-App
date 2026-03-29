module.exports = {
  darkMode: "class",
  content: ["./templates/**/*.{html,js}", "./static/js/**/*.js"],
  safelist: ["hidden"],
  theme: {
    container: {
      center: true,
      screens: {
        sm: "640px",
        md: "768px",
        lg: "1024px",
        xl: "1280px",
        "2xl": "1536px",
      },
      // Page gutters: 16→24→32 by breakpoint
      padding: {
        DEFAULT: "1rem",
        md: "1.5rem",
        lg: "2rem",
      },
    },
    screens: {
      sm: "640px",
      md: "768px",
      lg: "1024px",
      xl: "1280px",
      "2xl": "1536px",
      "max-sm": { max: "639px" },
      "max-md": { max: "767px" },
      "max-lg": { max: "1023px" },
      "max-xl": { max: "1279px" },
      "max-2xl": { max: "1535px" },
    },
    extend: {
      colors: {
        // Semantic tokens from CSS variables (see static/src/app.css :root / html.dark)
        body: "var(--color-body-bg)",
        bodyText: "var(--color-body-text)",
        surface: "var(--color-surface)",
        surfaceSubtle: "var(--color-surface-subtle)",
        border: "var(--color-border)",
        form: {
          bg: "var(--color-form-bg)",
          border: "var(--color-form-border)",
          text: "var(--color-form-text)",
        },

        primary: "rgb(var(--color-primary-rgb) / <alpha-value>)",
        primaryHover: "var(--color-primary-hover)",
        linkHover: "var(--color-link-hover)",

        accent: {
          text: "var(--color-accent-text)",
          soft: "var(--color-accent-soft)",
          strong: "var(--color-accent-strong)",
          DEFAULT: "var(--color-accent)",
        },

        success: {
          text: "var(--color-success-text)",
          soft: "var(--color-success-soft)",
          strong: "var(--color-success-strong)",
          DEFAULT: "var(--color-success-default)",
          dark: "var(--color-success-dark)",
        },
        warning: {
          text: "var(--color-warning-text)",
          soft: "var(--color-warning-soft)",
          strong: "var(--color-warning-strong)",
          DEFAULT: "var(--color-warning-default)",
        },
        danger: {
          text: "var(--color-danger-text)",
          soft: "var(--color-danger-soft)",
          strong: "var(--color-danger-strong)",
          DEFAULT: "var(--color-danger-default)",
        },
        info: {
          text: "var(--color-info-text)",
          soft: "var(--color-info-soft)",
          strong: "var(--color-info-strong)",
          DEFAULT: "var(--color-info-default)",
        },

        table: {
          border: "var(--color-table-border)",
          headerBg: "var(--color-table-header-bg)",
          headerText: "var(--color-table-header-text)",
          hoverBg: "var(--color-table-hover-bg)",
        },
      },
      spacing: {
        // 4/8/12/16/24 px increments
        1: "0.25rem",
        2: "0.5rem",
        3: "0.75rem",
        4: "1rem",
        6: "1.5rem",
        8: "2rem",
        12: "3rem",
        16: "4rem",
        24: "6rem",
        9.5: "2.375rem",
        30: "7.5rem",
      },
      maxWidth: {
        "drawer-sm": "30rem",
        "drawer-md": "32.5rem",
        "drawer-lg": "45rem",
        "drawer-xl": "53.75rem",
      },
      maxHeight: {
        "screen-90": "90vh",
      },
      borderRadius: {
        // Radius tokens
        sm: "4px",
        md: "6px",
        lg: "8px",
        xl: "12px",
      },
      fontSize: {
        badge: ["clamp(0.8rem, 0.3vw + 0.7rem, 1rem)", { lineHeight: "1" }],
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        // Elevation tokens
        card: "var(--shadow-card)",
        "sticky-header": "var(--shadow-sticky-header)",
        overlay: "var(--shadow-overlay)",
        btn: "var(--shadow-btn)",
        "form-focus": "var(--shadow-form-focus)",
      },
    },
  },
  plugins: [
    require("tailwindcss-fluid-type")({
      settings: {
        fontSizeMin: 0.875,
        fontSizeMax: 1.125,
        ratioMin: 1.15,
        ratioMax: 1.2,
        screenMin: 20,
        screenMax: 96,
        unit: "rem",
        prefix: "",
        extendValues: true,
      },
      values: {
        xs: [-2, 1.6],
        sm: [-1, 1.6],
        base: [0, 1.6],
        lg: [1, 1.6],
        xl: [2, 1.4],
        h1: [3, 1.25],
        h2: [2, 1.25],
        h3: [1, 1.3],
        label: [-1, 1.6],
        body: [0, 1.6],
        caption: [-2, 1.6],
      },
    }),
    require("@tailwindcss/forms"),
  ],
};
