module.exports = {
  content: ["./templates/**/*.{html,js}", "./static/js/**/*.js"],
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
      padding: {
        DEFAULT: "var(--space-8)",
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
        body: "#ffffff",
        bodyText: "#111827",
        primary: "#2563eb",
        secondary: "#15803d",
        accent: "#b45309",
        danger: "#dc2626",
        border: "#9ca3af",
        linkHover: "#1e3a8a",
        navText: "#ffffff",
        form: {
          bg: "#ffffff",
          border: "#9ca3af",
          text: "#111827",
        },
        table: {
          border: "#9ca3af",
          headerBg: "#2563eb",
          headerText: "#ffffff",
          hoverBg: "#f3f4f6",
        },
      },
      spacing: {
        0.5: "var(--space-0-5)",
        1: "var(--space-1)",
        2: "var(--space-2)",
        4: "var(--space-4)",
        6: "var(--space-6)",
        8: "var(--space-8)",
      },
      fontSize: {
        base: ["clamp(1rem, 0.5vw + 0.9rem, 1.25rem)", { lineHeight: "1.5" }],
        h1: ["clamp(1.6rem, 1vw + 1.3rem, 2.5rem)", { lineHeight: "1.25" }],
        h2: ["clamp(1.3rem, 0.75vw + 1.1rem, 2rem)", { lineHeight: "1.3" }],
        badge: ["clamp(0.8rem, 0.3vw + 0.7rem, 1rem)", { lineHeight: "1" }],
      },
      fontFamily: {
        sans: ["Roboto", "sans-serif"],
      },
      boxShadow: {
        "form-focus": "0 0 0 2px rgba(29, 78, 216, 0.4)",
      },
    },
  },
  plugins: [require("tailwindcss-fluid-type"), require("@tailwindcss/forms")],
};
