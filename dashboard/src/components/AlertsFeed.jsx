import { getRiskColors } from '../lib/risk'
import { useTheme } from '../context/ThemeContext'

export default function AlertsFeed({ alerts }) {
  const { isDark } = useTheme()
  const RISK_COLORS = getRiskColors(isDark)
  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between">
        <p className="eyebrow">Alert Timeline</p>
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-risk-red animate-blink" />
          <span className="font-mono text-[10px] text-muted">LIVE</span>
        </span>
      </div>

      <ul className="mt-4 space-y-3">
        {alerts.map((a) => {
          const color = RISK_COLORS[a.level]
          return (
            <li key={a.id} className="flex gap-3 border-l-2 pl-3" style={{ borderColor: color }}>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-ink">{a.title}</p>
                  <span className="font-mono text-[11px] text-muted">{a.time}</span>
                </div>
                <p className="mt-0.5 text-xs text-muted">
                  {a.zone} · {a.detail}
                </p>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
