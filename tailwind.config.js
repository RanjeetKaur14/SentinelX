/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base: '#0B0F10',
        panel: '#12181A',
        panel2: '#161D1F',
        line: '#1F2A2D',
        ink: '#E7EDEE',
        muted: '#7C8B8E',
        signal: '#3ADBC4',
        risk: {
          green: '#37D67A',
          yellow: '#E8C547',
          orange: '#F2924B',
          red: '#E5484D'
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
