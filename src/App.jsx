import { useState } from 'react'
import TopBar from './components/TopBar'
import SideRail from './components/SideRail'
import RiskGauge from './components/RiskGauge'
import StatCard from './components/StatCard'
import LiveFeed from './components/LiveFeed'
import DensityHeatmap from './components/DensityHeatmap'
import CrowdInsights from './components/CrowdInsights'
import AlertsFeed from './components/AlertsFeed'
import Timeline from './components/Timeline'
import WhatIfPanel from './components/WhatIfPanel'
import Switch from './components/Switch'
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
  const [selectedCams, setSelectedCams] = useState(['cam-01', 'cam-02'])
  const [showHeatmap, setShowHeatmap] = useState(false)
  const [showAnalysis, setShowAnalysis] = useState(false)

  const toggleCam = (id) => {
    setSelectedCams((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    )
  }

  return (
    <div className="flex h-screen flex-col">
      <TopBar level={currentRisk.level} />

      <div className="flex flex-1 overflow-hidden">
        <SideRail active={activeSection} onSelect={setActiveSection} />

        <main className="flex-1 overflow-y-auto px-6 py-6">
          {/* 70 / 30 split: live feed left, metrics + alerts right */}
          <div className="grid grid-cols-10 gap-4">
            <div className="col-span-10 lg:col-span-7">
              <LiveFeed cameras={cameras} selected={selectedCams} onToggle={toggleCam} />
            </div>

            <div className="col-span-10 space-y-4 lg:col-span-3">
              <RiskGauge score={currentRisk.score} level={currentRisk.level} />

              <div className="grid grid-cols-2 gap-3">
                <StatCard label="People Tracked" value={currentRisk.peopleCount.toLocaleString()} sub="4 zones" />
                <StatCard label="Avg Speed" value={currentRisk.avgSpeed} sub="site-wide" />
                <StatCard label="Flow" value={currentRisk.flowConsistency} sub="last 60s" />
                <StatCard label="Exits" value={currentRisk.exitStatus} sub="constrained" />
              </div>

              <AlertsFeed alerts={alerts} />
            </div>
          </div>

          {/* Toggle-gated deeper analysis, off by default */}
          <div className="panel mt-4 flex flex-wrap items-center gap-6 p-4">
            <Switch label="Show density heatmap" checked={showHeatmap} onChange={setShowHeatmap} />
            <Switch label="Show crowd analysis" checked={showAnalysis} onChange={setShowAnalysis} />
          </div>

          {(showHeatmap || showAnalysis) && (
            <div className="mt-4 grid grid-cols-2 gap-4">
              {showHeatmap && <DensityHeatmap zones={zones} />}
              {showAnalysis && <CrowdInsights />}
            </div>
          )}

          <div className="mt-4 grid grid-cols-2 gap-4">
            <Timeline labels={riskLabels} data={riskHistory} />
            <WhatIfPanel />
          </div>
        </main>
      </div>
    </div>
  )
}
