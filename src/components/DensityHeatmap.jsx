import { RISK_COLORS } from '../lib/risk'

export default function DensityHeatmap({ zones }) {
  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between">
        <p className="eyebrow">Zone Density</p>
        <p className="font-mono text-xs text-muted">{zones.length} zones tracked</p>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        {zones.map((z) => {
          const color = RISK_COLORS[z.risk]
          const pct = Math.min(100, Math.round(z.density * 100))
          return (
            <div key={z.id} className="rounded-md border border-line p-3">
              <div className="flex items-center justify-between">
                <p className="text-sm text-ink">{z.name}</p>
                <span className="font-mono text-xs" style={{ color }}>
                  {pct}%
                </span>
              </div>

              <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-line">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${pct}%`, backgroundColor: color }}
                />
              </div>

              <div className="mt-2 flex items-center justify-between">
                <span className="font-mono text-[11px] text-muted">
                  {z.count} / {z.capacity}
                </span>
                <span className="font-mono text-[11px] text-muted uppercase">{z.risk}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
