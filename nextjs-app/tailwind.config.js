/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: 'var(--primary-50)',
          100: 'var(--primary-100)',
          500: 'var(--primary-500)',
          600: 'var(--primary-600)',
        },
        accent: {
          50: 'var(--accent-50)',
          400: 'var(--accent-400)',
          500: 'var(--accent-500)',
        },
        calm: {
          50: 'var(--calm-50)',
          100: 'var(--calm-100)',
        },
      },
    },
  },
  plugins: [],
}
