import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: { ink: "#10243E", paper: "#F1F4F7", line: "#D8DFE7", mute: "#5A6B82", teal: { DEFAULT: "#0E7C7B", soft: "#D9EFEE" }, restock: "#1D6FA5", trim: "#B7791F" },
      fontFamily: { sans: ['"IBM Plex Sans"', "ui-sans-serif", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
} satisfies Config;
