import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        ide: {
          bg: "#0d1117",
          sidebar: "#161b22",
          border: "#30363d",
          active: "#1f242c",
          hover: "#21262d",
          text: "#c9d1d9",
          muted: "#8b949e",
        }
      },
      fontFamily: {
        mono: ["Consolas", "Monaco", "'Courier New'", "monospace"],
      }
    },
  },
  plugins: [],
};

export default config;
