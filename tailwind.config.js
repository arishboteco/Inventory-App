module.exports = {
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
        // Neutrals & surfaces (warmer feel)
        body: "#f8f5f0",
        bodyText: "#1f2937",
        surface: "#ffffff",
        surfaceSubtle: "#f3ebe2",
        border: "#e3d5c8",
        form: { bg: "#fffaf3", border: "#e8dcca", text: "#1f2937" },

        // Primary brand
        primary: "#2563eb",
        primaryHover: "#1d4ed8",
        linkHover: "#1e3a8a",

        // Warm accent for highlights
        accent: {
          text: "#92400e",
          soft: "#fdf2d0",
          strong: "#f4b740",
          DEFAULT: "#f59f25",
        },

        // Semantic palettes
        success: {
          text: "#166534",
          soft: "#dcfce7",
          strong: "#22c55e",
          DEFAULT: "#15803d",
        },
        warning: {
          text: "#854d0e",
          soft: "#fef3c7",
          strong: "#f59e0b",
          DEFAULT: "#a16207",
        },
        danger: {
          text: "#7f1d1d",
          soft: "#fee2e2",
          strong: "#ef4444",
          DEFAULT: "#dc2626",
        },
        info: {
          text: "#1e3a8a",
          soft: "#dbeafe",
          strong: "#3b82f6",
          DEFAULT: "#2563eb",
        },

        table: {
          border: "#e5e7eb",
          headerBg: "#f9fafb",
          headerText: "#374151",
          hoverBg: "#f3f4f6",
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
        sans: ["Roboto", "sans-serif"],
      },
      boxShadow: {
        // Elevation tokens
        card: "0 1px 2px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.08)",
        "sticky-header": "0 2px 4px rgba(0,0,0,0.06)",
        overlay: "0 10px 25px rgba(0,0,0,0.25)",
        btn: "0 2px 4px rgba(0, 0, 0, 0.25)",
        "form-focus": "0 0 0 2px rgba(29, 78, 216, 0.4)",
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
