/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0b1220",
          900: "#0f172a",
          800: "#1a2438",
          700: "#243349",
          600: "#33445f",
        },
        teal: {
          500: "#14b8a6",
          400: "#2dd4bf",
        },
        cyan: { 500: "#06b6d4" },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        glow: "0 0 24px rgba(20, 184, 166, 0.15)",
      },
    },
  },
  plugins: [],
};
