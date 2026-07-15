import { useEffect, useState } from 'react'
import TopBar from './components/TopBar'
import RiskGauge from './components/RiskGauge'
import StatCard from './components/StatCard'
import LiveFeed from './components/LiveFeed'
import DensityHeatmap from './components/DensityHeatmap'
import CrowdInsights from './components/CrowdInsights'
import AlertsFeed from './components/AlertsFeed'
import Timeline from './components/Timeline'
import Switch from './components/Switch'
import { fetchLiveStatus } from './api/client'

const POLL_INTERVAL_MS = 1000
const HISTORY_LENGTH = 20

// NOTE ON WHAT'S STILL MOCK:
// The density heatmap is now REAL -- stream_server.py computes real
// per-zone counts from crowd_metrics.density and sends them over
// /live_status as `zones`. See zones_from_density() in stream_server.py
// for exactly how (and its honest caveat: these are anonymous grid
// cells, not named physical zones with real capacity numbers).
//
// CrowdInsights is still NOT wired to real data (still mock) -- it's
// a different multi-metric summary component that wasn't part of this
// pass. Still toggle-gated off by default and labeled "(demo)".
//
// REMOVED (was non-functional or pure-mock scaffolding):
// - SideRail: tracked an "active section" but nothing in the page ever
//   changed based on it -- dead navigation.
// - WhatIfPanel: pure what-if simulation against fake mock zones.
// - RiskGauge's old animated circular sweep -- flat score card instead.

export default function App() {
  const [showHeatmap, setShowHeatmap] = useState(false)
  const [showAnalysis, setShowAnalysis] = useState(false)

  const [status, setStatus] = useState(null)
  const [connectionError, setConnectionError] = useState(false)
  const [alerts, setAlerts] = useState([])
  const [riskHistory, setRiskHistory] = useState([])
  const [lastAlertLoggedAt, setLastAlertLoggedAt] = useState(0)
  const ALERT_MIN_GAP_MS = 8000   // don't log a new entry more than once per 8s,
                                    // regardless of A/B flapping near a threshold

  useEffect(() => {
    let cancelled = false

    async function poll() {
      try {
        const data = await fetchLiveStatus()
        if (cancelled) return
        setStatus(data)
        setConnectionError(false)

        setRiskHistory((prev) => {
          const next = [...prev, data.risk_score]
          return next.length > HISTORY_LENGTH ? next.slice(next.length - HISTORY_LENGTH) : next
        })

        if (data.alerts && data.alerts.length > 0) {
          // Rate-limited, not just deduped: the underlying risk score
          // can sit right at a rule boundary and flicker between two
          // different reason sets every poll (e.g. "Congestion" <->
          // "Caution") -- exact-match dedup against only the LAST
          // entry doesn't catch that alternation. A flat minimum gap
          // between logged entries does, regardless of what's flapping.
          const nowMs = Date.now()
          if (nowMs - lastAlertLoggedAt >= ALERT_MIN_GAP_MS) {
            setLastAlertLoggedAt(nowMs)
            setAlerts((prev) => {
              const newOnes = data.alerts.map((text, i) => ({
                id: `${data.updated_at}-${i}`,
                level: data.risk_level.toLowerCase(),
                title: text,
                zone: 'cam_01',
                detail: data.reasons.join(', '),
                time: new Date(data.updated_at).toLocaleTimeString()
              }))
              return [...newOnes, ...prev].slice(0, 20)
            })
          }
        }
      } catch (err) {
        if (!cancelled) setConnectionError(true)
      }
    }

    poll()
    const interval = setInterval(poll, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  const level = status ? status.risk_level.toLowerCase() : 'green'
  const riskLabels = riskHistory.map((_, i) => {
    const secondsAgo = (riskHistory.length - 1 - i) * (POLL_INTERVAL_MS / 1000)
    return secondsAgo === 0 ? 'now' : `-${secondsAgo}s`
  })

  return (
    <div className="flex h-screen flex-col">
      <TopBar level={level} />

      {connectionError && (
        <div className="bg-risk-red/10 px-4 py-1.5 text-center font-mono text-xs text-risk-red">
          Can't reach stream_server at the configured URL — is it running? (see src/api/client.js)
        </div>
      )}

      <main className="flex-1 overflow-y-auto px-6 py-6">
        <div className="grid grid-cols-10 gap-4">
          <div className="col-span-10 lg:col-span-7">
            <LiveFeed status={status} showHeatmap={showHeatmap} />
          </div>

          <div className="col-span-10 space-y-4 lg:col-span-3">
            <RiskGauge score={status?.risk_score ?? 0} level={level} />

            <div className="grid grid-cols-2 gap-3">
              <StatCard label="People Tracked" value={status?.people_count ?? '—'} sub="cam_01" />
              <StatCard label="Avg Speed" value={status ? `${status.average_speed} px/s` : '—'} sub="live" />
              <StatCard label="Flow" value={status?.flow_label ?? '—'} sub="last update" />
              <StatCard label="FPS" value={status?.fps ?? '—'} sub="processing" />
            </div>

            <AlertsFeed alerts={alerts} />
          </div>
        </div>

        <div className="panel mt-4 flex flex-wrap items-center gap-6 p-4">
          <Switch label="Show density heatmap" checked={showHeatmap} onChange={setShowHeatmap} />
          <Switch label="Show crowd analysis (demo)" checked={showAnalysis} onChange={setShowAnalysis} />
        </div>

        {(showHeatmap || showAnalysis) && (
          <div className="mt-4 grid grid-cols-2 gap-4">
            {showHeatmap && <DensityHeatmap zones={status?.zones ?? []} />}
            {showAnalysis && <CrowdInsights />}
          </div>
        )}

        <div className="mt-4">
          <Timeline labels={riskLabels} data={riskHistory} />
        </div>
      </main>
    </div>
  )
}
