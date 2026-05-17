/**
 * Chronos — Tailwind config.
 * Tokens lifted 1:1 from docs/design-tokens.md. CSS variables in
 * src/styles/tokens.css are the single source of truth at runtime; this
 * file mirrors them so utility classes resolve to the same values.
 *
 * If a value changes, update tokens.css FIRST, then mirror here.
 */

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{astro,html,ts,tsx,md,mdx}'],
  theme: {
    extend: {
      colors: {
        paper:        { DEFAULT: '#F4ECD8', 2: '#EFE5CC', 3: '#E7DBBE', edge: '#D9CBA8' },
        ink:          { DEFAULT: '#1F2A44', 2: '#2F3A55', mute: '#5A607A', faint: '#8A8775' },
        rule:         { DEFAULT: '#CDBE99', soft: '#DDCFA9' },
        gold:         { DEFAULT: '#B8860B', 2: '#C9A227', soft: '#E9D58A' },
        lane: {
          bible:           { label: '#1F2A44', soft: '#DAD4BE' },
          egypt:           { label: '#A88E3A', soft: '#E8DCB2' },
          rome:            { label: '#8B3A1F', soft: '#E4C8B8' },
          'church-history':{ label: '#5B4A6E', soft: '#DCD2E0' },
          science:         { label: '#4F7A3E', soft: '#DDE5CC' },
          arts:            { label: '#9A4225', soft: '#ECD4C4' },
          reformation:     { label: '#2F5A6B', soft: '#CDD9DD' },
        },
        status: {
          ok:     { fg: '#4F7A3E', bg: '#DFE7CC' },
          warn:   { fg: '#B07B11', bg: '#F2E5BC' },
          danger: { fg: '#9B2C1E', bg: '#EFD0C9' },
          ai:     { fg: '#E9D58A', bg: '#FBF6E8' },
        },
        // TV-gamma offset — only applied on /tv route via the .tv class.
        tv: { paper: '#EBE0C0', ink: '#1B2336', gold: '#D4A745' },
      },
      fontFamily: {
        serif: ['Lora', 'Georgia', 'serif'],
        sans:  ['Inter', 'system-ui', 'sans-serif'],
        mono:  ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        // Major-third scale (1.25), rounded to nearest px.
        '2xs':  '11px',
        xs:     '12px',
        sm:     '14px',
        base:   '16px',
        lg:     '18px',
        xl:     '22px',
        '2xl':  '26px',
        '3xl':  '32px',
        '4xl':  '40px',
        '5xl':  '84px',
        // TV-specific
        'tv-body':  '24px',
        'tv-row':   '28px',
        'tv-hero':  '104px',
        'tv-mega':  '144px',
      },
      spacing: {
        '0.5': '2px',
        '1':   '4px',
        '1.5': '6px',
        '2':   '8px',
        '2.5': '10px',
        '3':   '12px',
        '3.5': '14px',
        '4':   '16px',
        '5.5': '22px',
        '7':   '28px',
        '9':   '36px',
        '12':  '48px',
        '16':  '64px',
        '20':  '80px',
        '25':  '100px',
      },
      borderRadius: {
        sm:   '3px',
        md:   '6px',
        lg:   '10px',
        xl:   '22px',         // bottom-sheet top edge only
        pill: '9999px',
      },
      boxShadow: {
        paper:    '0 1px 0 rgba(31,42,68,.04) inset, 0 8px 24px -16px rgba(31,42,68,.18)',
        card:     '0 1px 2px rgba(31,42,68,.06), 0 6px 18px -12px rgba(31,42,68,.18)',
        hover:    '0 1px 2px rgba(31,42,68,.06), 0 14px 28px -16px rgba(31,42,68,.28)',
        tooltip:  '0 8px 24px -12px rgba(31,42,68,.6)',
        'tv-focus': '0 0 0 4px #15110a, 0 0 0 8px #E9C462, 0 20px 50px rgba(0,0,0,.55)',
      },
      ringColor:  { DEFAULT: '#B8860B' },
      ringOffsetColor: { DEFAULT: '#F4ECD8' },
    },
  },
  plugins: [],
};
