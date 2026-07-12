import { RISK_COLORS } from '../lib/risk'
import { zones } from '../data/mockData'
import CameraConfig from './CameraConfig'

function zoneFor(zoneId) {
  return zones.find((z) => z.id === zoneId)
}

export default function LiveFeed({ cameras, selected, onToggle }) {
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
            return (
              <div key={cam.id} className="overflow-hidden rounded-md border border-line">
                <div className="relative aspect-video bg-panel2">
                  <div
                    className="absolute inset-0 opacity-60"
                    style={{
                      backgroundImage:
                        'repeating-linear-gradient(0deg, rgba(0,0,0,0.03) 0px, rgba(0,0,0,0.03) 1px, transparent 1px, transparent 3px)'
                    }}
                  />
                  <div className="absolute inset-0 grid place-items-center">
                    <span className="font-mono text-xs text-muted">NO SIGNAL — MOCK</span>
                  </div>
                  <div className="absolute left-3 top-3 flex items-center gap-1.5">
                    <span
                      className="h-1.5 w-1.5 rounded-full"
                      style={{ backgroundColor: cam.status === 'live' ? '#1E9A5C' : '#68767A' }}
                    />
                    <span className="font-mono text-xs text-ink">{cam.id.toUpperCase()}</span>
                  </div>
                  <div
                    className="absolute right-3 top-3 rounded px-2 py-0.5 font-mono text-xs font-semibold"
                    style={{ backgroundColor: color + '1A', color }}
                  >
                    {cam.count} people
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-px bg-line text-center">
                  <div className="bg-panel px-2 py-2">
                    <p className="font-mono text-sm font-semibold text-ink">{cam.fps}</p>
                    <p className="text-[10px] text-muted">FPS</p>
                  </div>
                  <div className="bg-panel px-2 py-2">
                    <p className="font-mono text-sm font-semibold" style={{ color }}>
                      {risk.toUpperCase()}
                    </p>
                    <p className="text-[10px] text-muted">RISK</p>
                  </div>
                  <div className="bg-panel px-2 py-2">
                    <p className="font-mono text-sm font-semibold text-ink">
                      {zone ? Math.round(zone.density * 100) : '—'}%
                    </p>
                    <p className="text-[10px] text-muted">DENSITY</p>
                  </div>
                  <div className="bg-panel px-2 py-2">
                    <p className="truncate px-1 font-mono text-sm font-semibold text-ink">
                      {zone?.name ?? '—'}
                    </p>
                    <p className="text-[10px] text-muted">ZONE</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
