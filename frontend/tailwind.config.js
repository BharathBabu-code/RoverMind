/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        mars: {
          950: '#06080d',
          900: '#0b0f17',
          850: '#101522',
          800: '#161d2d',
          750: '#1d263a',
          700: '#26324b',
          600: '#354566',
          copper: '#c8531f',
          rust: '#e25822',
          glow: '#ff733b',
          amber: '#f59e0b',
          sand: '#d97706',
          sky: '#38bdf8',
          cyan: '#06b6d4',
          emerald: '#10b981',
          danger: '#ef4444',
        },
      },
      fontFamily: {
        display: ['"Chakra Petch"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
      },
      boxShadow: {
        'hud': '0 0 25px rgba(0, 0, 0, 0.65)',
        'hud-glow': '0 0 20px rgba(226, 88, 34, 0.25)',
        'cyan-glow': '0 0 15px rgba(6, 182, 212, 0.3)',
      },
    },
  },
  plugins: [],
}
