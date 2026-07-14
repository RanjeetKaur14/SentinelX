import { useState } from 'react'
import { useLiveStats } from '../hooks/useLiveStats'

function CameraFeedSurface({ cam, streamOk, setStreamOk }) {
  if (cam.streamUrl && streamOk) {
    return (
      <img
        src={cam.streamUrl}
        alt={cam.label}
        className="absolute inset-0 h-full w-full object-cover"
        onError={() => setStreamOk(false)}
      />
    )
  }

  return (
    <>
      <div
        className="absolute inset-0 opacity-60"
        style={{
          backgroundImage:
            'repeating-linear-gradient(0deg, rgba(0,0,0,0.03) 0px, rgba(0,0,0,0.03) 1px, transparent 1px, transparent 3px)'
        }}
      />
      <div className="absolute inset-0 grid place-items-center">
        <span className="font-mono text-xs text-muted">
          {cam.streamUrl ? 'STREAM UNAVAILABLE — CHECK BACKEND' : 'NO SIGNAL — MOCK'}
        </span>
      </div>
    </>
  )
}

export default function CameraCard({ cam, zone, risk, color }) {
  const [streamOk, setStreamOk] = useState(true)
  const { data: liveStats, connected } = useLiveStats(cam.statsUrl, 2000)

  // Prefer live backend numbers when they're actually arriving; otherwise mock.
  const count = connected && liveStats ? liveStats.people_count : cam.count
  const fps = connected && liveStats ? liveStats.fps : cam.fps

  return (
    <div className="overflow-hidden rounded-md border border-line">
      <div className="relative aspect-video bg-panel2">
        <CameraFeedSurface cam={cam} streamOk={streamOk} setStreamOk={setStreamOk} />

        <div className="absolute left-3 top-3 flex items-center gap-1.5">
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: cam.status === 'live' ? '#1E9A5C' : '#68767A' }}
          />
          <span className="font-mono text-xs text-white drop-shadow">{cam.id.toUpperCase()}</span>
          {cam.statsUrl && (
            <span
              className="ml-1 rounded px-1.5 py-0.5 font-mono text-[9px] font-semibold"
              style={{ backgroundColor: connected ? '#1E9A5CCC' : '#68767ACC', color: '#fff' }}
            >
              {connected ? 'LIVE' : 'MOCK'}
            </span>
          )}
        </div>
        <div
          className="absolute right-3 top-3 rounded px-2 py-0.5 font-mono text-xs font-semibold"
          style={{ backgroundColor: color + 'CC', color: '#fff' }}
        >
          {count} people
        </div>
      </div>

      <div className="grid grid-cols-4 gap-px bg-line text-center">
        <div className="bg-panel px-2 py-2">
          <p className="font-mono text-sm font-semibold text-ink">{fps}</p>
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
}
