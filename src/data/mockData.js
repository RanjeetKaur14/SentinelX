// Mock data — shaped to match shared/schemas.py so swapping in the
// real FastAPI / WebSocket feed later is a drop-in replacement.
// Replace the functions in src/api/client.js with real fetch/WS calls
// once Team 3 (backend) exposes the endpoints.

export const zones = [
  { id: 'zone-a', name: 'Main Entrance', capacity: 800, count: 612, density: 0.76, risk: 'orange' },
  { id: 'zone-b', name: 'Exit Gate B', capacity: 400, count: 118, density: 0.29, risk: 'green' },
  { id: 'zone-c', name: 'Central Plaza', capacity: 1200, count: 1041, density: 0.87, risk: 'red' },
  { id: 'zone-d', name: 'Food Court', capacity: 500, count: 260, density: 0.52, risk: 'yellow' }
]

export const cameras = [
  { id: 'cam-01', label: 'CAM 01 — Main Entrance', zone: 'zone-a', count: 612, fps: 24, status: 'live' },
  { id: 'cam-02', label: 'CAM 02 — Central Plaza N', zone: 'zone-c', count: 587, fps: 22, status: 'live' },
  { id: 'cam-03', label: 'CAM 03 — Central Plaza S', zone: 'zone-c', count: 454, fps: 23, status: 'live' },
  { id: 'cam-04', label: 'CAM 04 — Exit Gate B', zone: 'zone-b', count: 118, fps: 25, status: 'live' },
  { id: 'cam-05', label: 'CAM 05 — Food Court', zone: 'zone-d', count: 260, fps: 21, status: 'live' },
  { id: 'cam-06', label: 'CAM 06 — West Corridor', zone: 'zone-a', count: 89, fps: 24, status: 'degraded' }
]

export const alerts = [
  { id: 1, level: 'red', title: 'Stampede Risk', zone: 'Central Plaza', detail: 'Density 0.87, opposing flow detected', time: '18:42:11' },
  { id: 2, level: 'orange', title: 'Congestion Warning', zone: 'Main Entrance', detail: 'Inflow exceeds outflow by 34%', time: '18:41:02' },
  { id: 3, level: 'yellow', title: 'Exit Slowdown', zone: 'Food Court', detail: 'Walking speed dropped to 0.4 m/s', time: '18:38:47' },
  { id: 4, level: 'green', title: 'Zone Cleared', zone: 'Exit Gate B', detail: 'Density returned to normal', time: '18:35:19' }
]

// Overall system risk score, 0-100, and its 20-minute history for the timeline chart
export const riskHistory = [
  22, 24, 26, 31, 35, 38, 44, 47, 52, 58, 63, 67, 71, 76, 79, 82, 80, 84, 82, 82
]
export const riskLabels = riskHistory.map((_, i) => {
  const mins = 20 - i
  return mins === 0 ? 'now' : `-${mins}m`
})

export const currentRisk = {
  score: 82,
  level: 'red',
  peopleCount: 2033,
  avgSpeed: '0.6 m/s',
  flowConsistency: '61%',
  exitStatus: '1 of 4 constrained'
}

// Simple rule-based "what-if" model: redirecting X% of a source zone's
// crowd to a target zone reduces source risk score proportionally to
// the headroom in the target zone's capacity.
export function simulateRedirect(sourceZoneId, targetZoneId, pct) {
  const source = zones.find(z => z.id === sourceZoneId)
  const target = zones.find(z => z.id === targetZoneId)
  if (!source || !target) return null

  const moved = Math.round(source.count * (pct / 100))
  const newSourceCount = source.count - moved
  const newTargetCount = target.count + moved

  const newSourceDensity = newSourceCount / source.capacity
  const newTargetDensity = newTargetCount / target.capacity

  const baselineRisk = currentRisk.score
  const densityDelta = source.density - newSourceDensity
  const projectedRisk = Math.max(5, Math.round(baselineRisk - densityDelta * 90))

  return {
    moved,
    newSourceDensity,
    newTargetDensity,
    baselineRisk,
    projectedRisk,
    targetOvercapacity: newTargetDensity > 1
  }
}
