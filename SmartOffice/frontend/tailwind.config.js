/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        afmi: {
          dark: '#081C15',
          forest: '#1B4332',
          emerald: '#2D6A4F',
          sage: '#40916C',
          mint: '#52B788',
          lightmint: '#D8F3DC',
          gold: '#D4A373',
          darkgold: '#B08968',
          sand: '#EDE0D4',
          slate: '#F8F9FA',
          border: '#E2E8F0',
        }
      },
      fontFamily: {
        arabic: ['Noto Sans Arabic', 'Cairo', 'Segoe UI', 'Tahoma', 'sans-serif'],
        sans: ['Inter', 'Segoe UI', 'sans-serif']
      }
    },
  },
  plugins: [],
}
