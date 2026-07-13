import { zones, currentRisk } from '../data/mockData'
import { getRiskColors } from '../lib/risk'
import { useTheme } from '../context/ThemeContext'

function buildInsights() {
  const worst = [...zones].sort((a, b) => b.density - a.density)[0]
  const notes = [
    `${worst.name} is the most congested zone at ${Math.round(worst.density * 100)}% of capacity.`,
    `Site-wide flow consistency is ${currentRisk.flowConsistency}, meaning crowd movement is ${
      parseInt(currentRisk.flowConsistency) < 70 ? 'uneven — some areas moving, others stalled' : 'fairly steady'
    }.`,
    `Average walking speed has dropped to ${currentRisk.avgSpeed}, consistent with crowding rather than free movement.`,
    `${currentRisk.exitStatus} — reduced exit capacity increases risk if density keeps rising.`
  ]
  return notes
}

export default function CrowdInsights() {
  const { isDark } = useTheme()
  const RISK_COLORS = getRiskColors(isDark)
  const insights = buildInsights()

  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between">
        <p className="eyebrow">Crowd Analysis</p>
        <span className="rounded-full border border-line px-2 py-0.5 font-mono text-[10px] text-muted">
          MODEL OUTPUT
        </span>
      </div>

      <ul className="mt-4 space-y-2.5">
        {insights.map((note, i) => (
          <li key={i} className="flex gap-2.5 text-sm text-ink">
            <span
              className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full"
              style={{ backgroundColor: RISK_COLORS[currentRisk.level] }}
            />
            {note}
          </li>
        ))}
      </ul>

      <p className="mt-4 text-[11px] text-muted">
        Generated from live density, flow, and speed metrics — swap in Team 3's
        analytics-engine output here once available.
      </p>
    </div>
  )
}
