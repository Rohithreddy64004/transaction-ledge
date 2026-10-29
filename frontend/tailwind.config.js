/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17212f",
        navy: "#14253d",
        mint: "#54d2b2",
        paper: "#f6f8fb",
      },
      boxShadow: {
        soft: "0 16px 45px rgba(20, 37, 61, 0.08)",
      },
    },
  },
  plugins: [],
};
