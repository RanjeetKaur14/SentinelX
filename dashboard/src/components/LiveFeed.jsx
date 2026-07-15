import { getRiskColors, RISK_LABELS } from '../lib/risk'
import { useTheme } from '../context/ThemeContext'
import { getVideoFeedUrl } from '../api/client'

// NOTE: this replaces the old mock version, which rendered a grid of
// 6 fake cameras each showing a "NO SIGNAL — MOCK" placeholder box
// (backed by src/data/mockData.js's `cameras` array). That made sense
// as a placeholder before a real feed existed, but once you're actually
// streaming from stream_server.py there's only ONE real live source
// right now, so the multi-camera selector (CameraConfig) and the fake
// per-camera grid are gone. If/when you wire up multiple real physical
// cameras later, this is the file to extend back into a grid.

const CAMERA_ID = 'cam_01' // matches stream_server.py's CAMERA_ID constant

export default function LiveFeed({ status, showHeatmap = false }) {
  const { isDark } = useTheme()
  const RISK_COLORS = getRiskColors(isDark)
  const level = status?.risk_level ? status.risk_level.toLowerCase() : 'green'
  const color = RISK_COLORS[level] ?? RISK_COLORS.green

  const zones = status?.zones ?? []
  // grid_rows/grid_cols come from stream_server.py's static config (see
  // latest_status); fall back to deriving from the zones themselves so
  // this still works against an older server that hasn't sent them yet.
  const gridRows = status?.grid_rows ?? (zones.length ? Math.max(...zones.map((z) => z.row)) + 1 : 0)
  const gridCols = status?.grid_cols ?? (zones.length ? Math.max(...zones.map((z) => z.col)) + 1 : 0)

  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between">
        <p className="eyebrow">Live Feed</p>
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-risk-red animate-blink" />
          <span className="font-mono text-[10px] text-muted">LIVE</span>
        </span>
      </div>

      <div className="mt-3 overflow-hidden rounded-md border border-line">
        <div className="relative aspect-video bg-panel2">
          <img
            src={getVideoFeedUrl()}
            alt="Live annotated camera feed"
            className="absolute inset-0 z-0 h-full w-full object-cover"
          />

          {showHeatmap && gridRows > 0 && gridCols > 0 && (
            <div
              className="pointer-events-none absolute inset-0 z-[5] grid"
              style={{
                gridTemplateRows: `repeat(${gridRows}, 1fr)`,
                gridTemplateColumns: `repeat(${gridCols}, 1fr)`,
              }}
            >
              {zones.map((z) => (
                <div
                  key={z.id}
                  className="transition-colors duration-500"
                  style={{
                    gridRow: z.row + 1,
                    gridColumn: z.col + 1,
                    // translucent fill so the video underneath stays
                    // clearly visible. Previous range (0.12-0.4) was
                    // too strong -- on a busy zone (concentration near
                    // 1.0, often colored vivid red/orange) 0.4 opacity
                    // reads as a near-solid block over real footage,
                    // not a tint. Capped much lower: 0.06 at empty,
                    // 0.22 at the single busiest zone in frame.
                    backgroundColor: RISK_COLORS[z.risk] ?? RISK_COLORS.green,
                    opacity: 0.06 + 0.16 * z.density,
                  }}
                />
              ))}
            </div>
          )}

          <div className="absolute left-3 top-3 z-10 flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: '#1E9A5C' }} />
            <span className="font-mono text-xs text-ink">{CAMERA_ID.toUpperCase()}</span>
          </div>

          <div
            className="absolute right-3 top-3 z-10 rounded px-2 py-0.5 font-mono text-xs font-semibold"
            style={{ backgroundColor: color + '1A', color }}
          >
            {status?.people_count ?? '—'} people
          </div>
        </div>

        <div className="grid grid-cols-3 gap-px bg-line text-center">
          <div className="bg-panel px-2 py-2">
            <p className="font-mono text-sm font-semibold text-ink">{status?.fps ?? '—'}</p>
            <p className="text-[10px] text-muted">FPS</p>
          </div>
          <div className="bg-panel px-2 py-2">
            <p className="font-mono text-sm font-semibold" style={{ color }}>
              {status?.risk_level ? RISK_LABELS[level] : '—'}
            </p>
            <p className="text-[10px] text-muted">RISK</p>
          </div>
          <div className="bg-panel px-2 py-2">
            <p className="font-mono text-sm font-semibold text-ink">{status?.risk_score ?? '—'}</p>
            <p className="text-[10px] text-muted">SCORE</p>
          </div>
        </div>
      </div>
    </div>
  )
}
