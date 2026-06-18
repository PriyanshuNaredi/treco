import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:               "var(--bg)",
        surface:          "var(--surface)",
        "surface-2":      "var(--surface-2)",
        "surface-3":      "var(--surface-3)",
        "border-default": "var(--border)",
        "green-brand":    "var(--green)",
        "green-brand-2":  "var(--green-2)",
        "red-brand":      "var(--red)",
        "amber-brand":    "var(--amber)",
        "blue-brand":     "var(--blue)",
        "text-primary":   "var(--text)",
        "text-muted":     "var(--text-2)",
        "text-subtle":    "var(--text-3)",
        /* legacy alias kept for backwards compat */
        "cyan-brand":     "var(--green)",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      animation: {
        "border-pulse": "border-pulse 2.2s ease-in-out infinite",
        "fade-in":      "fade-in 0.2s ease-out",
        "slide-in":     "slide-in 0.2s ease-out",
        shimmer:        "shimmer 1.4s ease-in-out infinite",
      },
      keyframes: {
        "border-pulse": {
          "0%, 100%": { opacity: "0.35" },
          "50%":       { opacity: "1" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        "slide-in": {
          from: { opacity: "0", transform: "translateY(-4px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          from: { backgroundPosition: "-200% 0" },
          to:   { backgroundPosition:  "200% 0" },
        },
      },
      boxShadow: {
        card: "0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.06)",
        "card-hover": "0 4px 12px 0 rgb(0 0 0 / 0.08), 0 1px 3px 0 rgb(0 0 0 / 0.06)",
        modal: "0 20px 60px -10px rgb(0 0 0 / 0.15), 0 4px 16px -4px rgb(0 0 0 / 0.1)",
      },
    },
  },
  plugins: [],
};

export default config;
