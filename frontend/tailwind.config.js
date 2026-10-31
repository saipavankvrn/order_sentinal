/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sentinel: {
          navy: '#0F172A',
          canvas: '#F8FAFC',
          blue: '#2563EB',
          red: '#EF4444',
          amber: '#F59E0B',
          emerald: '#10B981',
          slate: {
            800: '#1E293B',
            700: '#334155',
            600: '#475569',
            200: '#E2E8F0',
            100: '#F1F5F9',
            50: '#F8FAFC'
          }
        }
      }
    },
  },
  plugins: [],
}

