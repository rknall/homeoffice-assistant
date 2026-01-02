/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  // Safelist classes that plugins may use at runtime (not in compiled sources)
  safelist: [
    // Grid columns for plugins (calendars need 7 columns)
    'grid-cols-5',
    'grid-cols-6',
    'grid-cols-7',
    'grid-cols-8',
    // Gap utilities
    'gap-5',
    'gap-6',
    'gap-8',
    'gap-10',
    'gap-12',
    // Modal backdrop opacity
    'bg-opacity-50',
    // Fixed positioning for modals
    'fixed',
    'inset-0',
    'z-50',
  ],
  theme: {
    extend: {},
  },
  plugins: [require('@tailwindcss/forms')({ strategy: 'class' })],
}
