/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base: 'rgb(var(--color-base) / <alpha-value>)',
        panel: 'rgb(var(--color-panel) / <alpha-value>)',
        panel2: 'rgb(var(--color-panel2) / <alpha-value>)',
        line: 'rgb(var(--color-line) / <alpha-value>)',
        ink: 'rgb(var(--color-ink) / <alpha-value>)',
        muted: 'rgb(var(--color-muted) / <alpha-value>)',
        signal: 'rgb(var(--color-signal) / <alpha-value>)',
        risk: {
          green: 'rgb(var(--color-risk-green) / <alpha-value>)',
          yellow: 'rgb(var(--color-risk-yellow) / <alpha-value>)',
          orange: 'rgb(var(--color-risk-orange) / <alpha-value>)',
          red: 'rgb(var(--color-risk-red) / <alpha-value>)'
        }
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace']
      },
      boxShadow: {
        panel: '0 0 0 1px #1F2A2D, 0 8px 24px -12px rgba(0,0,0,0.6)'
      },
      keyframes: {
        sweep: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' }
        },
        pulse2: {
          '0%, 100%': { opacity: 0.15, transform: 'scale(0.9)' },
          '50%': { opacity: 0.5, transform: 'scale(1.05)' }
        },
        blink: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.3 }
        }
      },
      animation: {
        sweep: 'sweep 4s linear infinite',
        pulse2: 'pulse2 2.4s ease-in-out infinite',
        blink: 'blink 1.4s ease-in-out infinite'
      }
    }
  },
  plugins: []
}
