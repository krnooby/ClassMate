/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      keyframes: {
        progress: {
          '0%': { width: '0%', marginLeft: '0%' },
          '50%': { width: '70%', marginLeft: '15%' },
          '100%': { width: '0%', marginLeft: '100%' },
        },
      },
      animation: {
        progress: 'progress 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
