/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0a0c10",
        surface: "#111318",
        surfaceAlt: "#161b22",
        border: "#21262d",
        borderLight: "#30363d",
        accent: "#58a6ff",
        accentGlow: "rgba(88,166,255,0.15)",
        success: "#3fb950",
        warning: "#d29922",
        danger: "#f85149",
        muted: "#8b949e",
        text: "#e6edf3",
        textDim: "#b1bac4",
        feature: "#a371f7",
      },
      fontFamily: {
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      animation: {
        spin: "spin 0.8s linear infinite",
        slideUp: "slideUp 0.25s ease",
      },
      keyframes: {
        slideUp: {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
}
