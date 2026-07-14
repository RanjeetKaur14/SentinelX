import { getRiskColors } from '../lib/risk'
import { useTheme } from '../context/ThemeContext'
import { zones } from '../data/mockData'
import CameraConfig from './CameraConfig'
import CameraCard from './CameraCard'

function zoneFor(zoneId) {
  return zones.find((z) => z.id === zoneId)
}

export default function LiveFeed({ cameras, selected, onToggle }) {
  const { isDark } = useTheme()
  const RISK_COLORS = getRiskColors(isDark)
  const visible = cameras.filter((c) => selected.includes(c.id))

  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between">
        <p className="eyebrow">Live Feed</p>
        <p className="font-mono text-xs text-muted">{visible.length} of {cameras.length} shown</p>
      </div>

      <CameraConfig cameras={cameras} selected={selected} onToggle={onToggle} />

      {visible.length === 0 ? (
        <div className="grid h-64 place-items-center rounded-md border border-dashed border-line text-sm text-muted">
          Select a camera above to view its feed
        </div>
      ) : (
        <div className={`grid gap-4 ${visible.length === 1 ? 'grid-cols-1' : 'grid-cols-2'}`}>
          {visible.map((cam) => {
            const zone = zoneFor(cam.zone)
            const risk = zone?.risk ?? 'green'
            const color = RISK_COLORS[risk]
            return <CameraCard key={cam.id} cam={cam} zone={zone} risk={risk} color={color} />
          })}
        </div>
      )}
    </div>
  )
}
