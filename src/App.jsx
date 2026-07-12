import { useState } from 'react'
import TopBar from './components/TopBar'
import SideRail from './components/SideRail'
import RiskGauge from './components/RiskGauge'
import StatCard from './components/StatCard'
import CameraGrid from './components/CameraGrid'
import DensityHeatmap from './components/DensityHeatmap'
import AlertsFeed from './components/AlertsFeed'
import Timeline from './components/Timeline'
import WhatIfPanel from './components/WhatIfPanel'
import {
  zones,
  cameras,
  alerts,
  riskHistory,
  riskLabels,
  currentRisk
} from './data/mockData'

export default function App() {
  const [activeSection, setActiveSection] = useState('overview')

  return (
    <div className="flex h-screen flex-col">
      <TopBar level={currentRisk.level} />

      <div className="flex flex-1 overflow-hidden">
        <SideRail active={activeSection} onSelect={setActiveSection} />

        <main className="flex-1 overflow-y-auto px-6 py-6">
          <div className="grid grid-cols-4 gap-3">
            <StatCard label="People Tracked" value={currentRisk.peopleCount.toLocaleString()} sub="across 4 zones" />
            <StatCard label="Avg Walking Speed" value={currentRisk.avgSpeed} sub="site-wide" />
            <StatCard label="Flow Consistency" value={currentRisk.flowConsistency} sub="last 60s" />
            <StatCard label="Exit Status" value={currentRisk.exitStatus} sub="constrained routes" />
          </div>

          <div className="mt-4 grid grid-cols-3 gap-4">
            <div className="col-span-2 space-y-4">
              <CameraGrid cameras={cameras} />
              <div className="grid grid-cols-2 gap-4">
                <DensityHeatmap zones={zones} />
                <Timeline labels={riskLabels} data={riskHistory} />
              </div>
            </div>

            <div className="space-y-4">
              <RiskGauge score={currentRisk.score} level={currentRisk.level} />
              <AlertsFeed alerts={alerts} />
              <WhatIfPanel />
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
