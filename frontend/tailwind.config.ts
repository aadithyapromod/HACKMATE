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
        background: "#090d16",
        surface: "#111827",
        surfaceBorder: "#1f2937",
        primary: {
          DEFAULT: "#8b5cf6",
          hover: "#7c3aed",
          light: "#a78bfa",
          dark: "#6d28d9",
        },
      },
    },
  },
  plugins: [],
};

export default config;
