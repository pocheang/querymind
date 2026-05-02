export default {
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
    './index.html'
  ],
  css: [
    './src/styles/**/*.css'
  ],
  safelist: [
    /^data-theme/,
    /^theme-/,
    /^dark/,
    /^light/,
    'active',
    'disabled',
    'hover',
    'focus',
    'focus-visible'
  ],
  defaultExtractor: content => content.match(/[\w-/:]+(?<!:)/g) || []
}
