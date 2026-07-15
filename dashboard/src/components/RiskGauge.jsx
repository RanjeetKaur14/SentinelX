import { getRiskColors, RISK_LABELS } from '../lib/risk'
import { useTheme } from '../context/ThemeContext'

// Replaces the old animated circular gauge (pulsing rings + rotating
// sweep) with a plain flat score card, per request for a more
// professional/less flashy look.

export default function RiskGauge({ score, level }) {
  const { isDark } = useTheme()
  const RISK_COLORS = getRiskColors(isDark)
  const color = RISK_COLORS[level]

  return (
    <div className="panel p-5">
      <p className="eyebrow">Overall Risk Score</p>

      <div className="mt-3 flex items-end justify-between">
        <p className="font-mono text-5xl font-semibold leading-none" style={{ color }}>
          {score}
        </p>
        <span
          className="rounded-full border px-3 py-1 font-mono text-xs font-semibold uppercase tracking-wide"
          style={{ borderColor: color + '55', backgroundColor: color + '14', color }}
        >
          {RISK_LABELS[level]}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-4 gap-1.5">
        {['green', 'yellow', 'orange', 'red'].map((l) => (
          <div
            key={l}
            className="h-1.5 rounded-full"
            style={{ backgroundColor: l === level ? RISK_COLORS[l] : 'rgb(var(--color-line))' }}
          />
        ))}
      </div>
    </div>
  )
}
