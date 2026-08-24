import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#090d14",
        panel: "#101722",
        line: "#202c3c",
        muted: "#8c9bad",
        accent: "#39c6a3",
      },
      boxShadow: {
        panel: "0 18px 60px rgba(0, 0, 0, 0.22)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
