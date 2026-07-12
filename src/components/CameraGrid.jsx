import { RISK_COLORS } from '../lib/risk'
import { zones } from '../data/mockData'

function zoneRisk(zoneId) {
  return zones.find((z) => z.id === zoneId)?.risk ?? 'green'
}

export default function CameraGrid({ cameras }) {
  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between">
        <p className="eyebrow">Camera Feeds</p>
        <p className="font-mono text-xs text-muted">{cameras.length} online</p>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {cameras.map((cam) => {
          const risk = zoneRisk(cam.zone)
          const color = RISK_COLORS[risk]
          return (
            <div
              key={cam.id}
              className="relative aspect-video overflow-hidden rounded-md border border-line bg-panel2"
            >
              {/* scanline placeholder for the actual video element */}
              <div
                className="absolute inset-0 opacity-40"
                style={{
                  backgroundImage:
                    'repeating-linear-gradient(0deg, rgba(255,255,255,0.03) 0px, rgba(255,255,255,0.03) 1px, transparent 1px, transparent 3px)'
                }}
              />
              <div className="absolute inset-0 grid place-items-center">
                <span className="font-mono text-[10px] text-muted">NO SIGNAL — MOCK</span>
              </div>

              <div className="absolute left-2 top-2 flex items-center gap-1.5">
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ backgroundColor: cam.status === 'live' ? '#37D67A' : '#7C8B8E' }}
                />
                <span className="font-mono text-[10px] text-ink/80">{cam.id.toUpperCase()}</span>
              </div>

              <div
                className="absolute right-2 top-2 rounded px-1.5 py-0.5 font-mono text-[10px]"
                style={{ backgroundColor: color + '22', color }}
              >
                {cam.count}
              </div>

              <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between bg-gradient-to-t from-black/70 to-transparent px-2 py-1.5">
                <span className="truncate text-[10px] text-ink/70">{cam.label}</span>
                <span className="font-mono text-[10px] text-muted">{cam.fps}fps</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
