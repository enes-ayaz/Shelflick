import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#0a0a0c",
        surface: {
          DEFAULT: "#121216",
          elevated: "#181820",
          card: "rgba(22, 22, 28, 0.75)",
          border: "rgba(255, 255, 255, 0.08)",
        },
        brand: {
          primary: "#6366f1",
          hover: "#4f46e5",
          accent: "#8b5cf6",
          gold: "#f59e0b",
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "'Segoe UI'",
          "Roboto",
          "Oxygen",
          "Ubuntu",
          "Cantarell",
          "sans-serif",
        ],
      },
      boxShadow: {
        glow: "0 0 25px -5px rgba(99, 102, 241, 0.25)",
        gold: "0 0 20px -3px rgba(245, 158, 11, 0.3)",
      },
      animation: {
        "scroll-up": "scrollUp 60s linear infinite",
        "scroll-down": "scrollDown 60s linear infinite",
        pulse_subtle: "pulseSubtle 3s ease-in-out infinite",
      },
      keyframes: {
        scrollUp: {
          "0%": { transform: "translateY(0%)" },
          "100%": { transform: "translateY(-50%)" },
        },
        scrollDown: {
          "0%": { transform: "translateY(-50%)" },
          "100%": { transform: "translateY(0%)" },
        },
        pulseSubtle: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.7" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
