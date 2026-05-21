/** @type {import('tailwindcss').Config} */

// Brand + neutral colors are driven by CSS variables (see styles/globals.css)
// so the whole app can flip between light and dark without per-component
// `dark:` variants. Each var holds space-separated RGB channels, and we wrap
// it with `<alpha-value>` so Tailwind opacity modifiers (e.g. text-ink/70,
// border-slate-200, bg-surface/80) keep working.
const v = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Brand — Grape Jelly. The ramp is theme-aware: in dark mode the
        // light tints (50–200) become deep grape surfaces while 700 becomes a
        // light accent so `text-grape-700` stays legible on a dark canvas.
        grape: {
          DEFAULT: v("--c-grape"),
          50: v("--c-grape-50"),
          100: v("--c-grape-100"),
          200: v("--c-grape-200"),
          300: v("--c-grape-300"),
          400: v("--c-grape-400"),
          500: v("--c-grape-500"),
          600: v("--c-grape-600"),
          700: v("--c-grape-700"),
          800: v("--c-grape-800"),
          900: v("--c-grape-900"),
        },
        violet: {
          electric: "#7C3AED",
        },
        // Semantic surfaces / text (theme-aware)
        ink: v("--c-ink"), // primary text
        cloud: v("--c-cloud"), // page canvas
        surface: {
          DEFAULT: v("--c-surface"), // cards / panels (was bg-white)
          muted: v("--c-surface-muted"),
        },
        // Neutral ramp — exact Tailwind values in light, inverted for dark.
        slate: {
          text: "#334155",
          50: v("--c-slate-50"),
          100: v("--c-slate-100"),
          200: v("--c-slate-200"),
          300: v("--c-slate-300"),
          400: v("--c-slate-400"),
          500: v("--c-slate-500"),
          600: v("--c-slate-600"),
          700: v("--c-slate-700"),
          800: v("--c-slate-800"),
          900: v("--c-slate-900"),
        },
        // Status colors keep fixed hues across themes.
        success: "#16A34A", // Growth Green
        warning: "#F59E0B", // Warning Amber
        danger: "#DC2626", // Danger Red
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 1px 2px rgba(17,24,39,0.04), 0 4px 16px rgba(17,24,39,0.06)",
        elevate: "0 8px 24px rgba(62,47,132,0.12)",
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.125rem",
      },
      backgroundImage: {
        // Saturated brand gradient — stays grape in both themes (hero, CTA,
        // sidebar). Soft gradient flips to deep grape in dark via the var.
        "grape-gradient":
          "linear-gradient(135deg, #3E2F84 0%, #6244C2 50%, #7C3AED 100%)",
        "grape-soft": "var(--grape-soft)",
      },
    },
  },
  plugins: [],
};
