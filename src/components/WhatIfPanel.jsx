import { useMemo, useState } from 'react'
import { zones, simulateRedirect } from '../data/mockData'
import { RISK_COLORS, scoreToLevel } from '../lib/risk'

export default function WhatIfPanel() {
  const [sourceId, setSourceId] = useState('zone-c')
  const [targetId, setTargetId] = useState('zone-b')
  const [pct, setPct] = useState(30)

  const result = useMemo(
    () => simulateRedirect(sourceId, targetId, pct),
    [sourceId, targetId, pct]
  )

  const source = zones.find((z) => z.id === sourceId)
  const target = zones.find((z) => z.id === targetId)
  const projectedLevel = result ? scoreToLevel(result.projectedRisk) : 'green'

  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between">
        <p className="eyebrow">What-If Simulation</p>
        <span className="rounded-full border border-signal/30 px-2 py-0.5 font-mono text-[10px] text-signal">
          DECISION SUPPORT
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <label className="text-xs text-muted">
          Redirect from
          <select
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            className="mt-1 w-full rounded-md border border-line bg-panel2 px-2 py-1.5 text-sm text-ink"
          >
            {zones.map((z) => (
              <option key={z.id} value={z.id}>{z.name}</option>
            ))}
          </select>
        </label>

        <label className="text-xs text-muted">
          Redirect to
          <select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            className="mt-1 w-full rounded-md border border-line bg-panel2 px-2 py-1.5 text-sm text-ink"
          >
            {zones.filter((z) => z.id !== sourceId).map((z) => (
              <option key={z.id} value={z.id}>{z.name}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-4">
        <div className="flex items-center justify-between text-xs text-muted">
          <span>% of crowd redirected</span>
          <span className="font-mono text-ink">{pct}%</span>
        </div>
        <input
          type="range"
          min={5}
          max={70}
          step={5}
          value={pct}
          onChange={(e) => setPct(Number(e.target.value))}
          className="mt-2 w-full accent-signal"
        />
      </div>

      {result && (
        <div className="mt-5 rounded-md border border-line bg-panel2 p-4">
          <p className="text-sm leading-relaxed text-ink">
            If <span className="font-mono text-signal">{pct}%</span> of the crowd at{' '}
            <span className="text-ink">{source.name}</span> is redirected to{' '}
            <span className="text-ink">{target.name}</span>, estimated risk moves from{' '}
            <span className="font-mono" style={{ color: RISK_COLORS[scoreToLevel(result.baselineRisk)] }}>
              {result.baselineRisk}
            </span>{' '}
            to{' '}
            <span className="font-mono font-semibold" style={{ color: RISK_COLORS[projectedLevel] }}>
              {result.projectedRisk}
            </span>
            .
          </p>

          <div className="mt-3 flex items-center gap-4 text-xs text-muted">
            <span>≈ {result.moved} people moved</span>
            <span>Target load → {Math.round(result.newTargetDensity * 100)}%</span>
          </div>

          {result.targetOvercapacity && (
            <p className="mt-2 text-xs text-risk-orange">
              Warning: this shifts {target.name} above capacity. Consider a smaller redirect or a third zone.
            </p>
          )}
        </div>
      )}

      <p className="mt-3 text-[11px] text-muted">
        Rule-based estimate from live density + capacity data — not a guarantee, a starting point for responders.
      </p>
    </div>
  )
}
