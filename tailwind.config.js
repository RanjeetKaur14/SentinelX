/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base: '#F5F7F7',
        panel: '#FFFFFF',
        panel2: '#EEF1F1',
        line: '#DEE3E3',
        ink: '#182322',
        muted: '#68767A',
        signal: '#12897D',
        risk: {
          green: '#1E9A5C',
          yellow: '#B4860F',
          orange: '#C86A24',
          red: '#C93B3B'
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
