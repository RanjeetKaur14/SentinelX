import { useEffect, useState } from 'react'
import { RISK_COLORS, RISK_LABELS } from '../lib/risk'

export default function TopBar({ level }) {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const time = now.toLocaleTimeString('en-US', { hour12: false })
  const color = RISK_COLORS[level]

  return (
    <header className="flex items-center justify-between border-b border-line bg-panel px-6 py-4">
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-md border border-signal/40 bg-signal/5 grid place-items-center">
          <span className="h-2.5 w-2.5 rounded-full bg-signal animate-blink" />
        </div>
        <div>
          <h1 className="font-display text-lg font-semibold leading-none tracking-tight">
            CrowdShield
          </h1>
          <p className="eyebrow mt-1">Live Ops · Site 04</p>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div
          className="flex items-center gap-2 rounded-full border px-3 py-1.5"
          style={{ borderColor: color + '55', backgroundColor: color + '14' }}
        >
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
          <span className="font-mono text-xs uppercase tracking-wide" style={{ color }}>
            {RISK_LABELS[level]}
          </span>
        </div>
        <div className="text-right">
          <p className="font-mono text-sm text-ink">{time}</p>
          <p className="eyebrow mt-0.5">Local Time</p>
        </div>
      </div>
    </header>
  )
}
