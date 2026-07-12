import { RISK_COLORS, RISK_LABELS } from '../lib/risk'

export default function RiskGauge({ score, level }) {
  const color = RISK_COLORS[level]

  return (
    <div className="panel p-5 flex flex-col items-center">
      <p className="eyebrow self-start">Overall Risk Score</p>

      <div className="relative mt-4 h-48 w-48">
        {/* pulsing outer rings, colored by risk */}
        <div
          className="absolute inset-0 rounded-full animate-pulse2"
          style={{ boxShadow: `0 0 0 1.5px ${color}` }}
        />
        <div
          className="absolute inset-4 rounded-full"
          style={{ boxShadow: `0 0 0 1px ${color}66` }}
        />
        <div
          className="absolute inset-8 rounded-full"
          style={{ boxShadow: `0 0 0 1px ${color}40` }}
        />

        {/* rotating sweep */}
        <div className="absolute inset-0 animate-sweep" style={{ transformOrigin: '50% 50%' }}>
          <svg viewBox="0 0 200 200" className="h-full w-full">
            <defs>
              <linearGradient id="sweepGradient" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor={color} stopOpacity="0" />
                <stop offset="100%" stopColor={color} stopOpacity="0.55" />
              </linearGradient>
            </defs>
            <path d="M 100 100 L 100 6 A 94 94 0 0 1 165 35 Z" fill="url(#sweepGradient)" />
          </svg>
        </div>

        {/* center readout */}
        <div className="absolute inset-0 grid place-items-center">
          <div className="text-center">
            <p className="font-mono text-5xl font-semibold" style={{ color }}>
              {score}
            </p>
            <p className="eyebrow mt-1">{RISK_LABELS[level]}</p>
          </div>
        </div>
      </div>

      <div className="mt-5 grid w-full grid-cols-4 gap-1.5">
        {['green', 'yellow', 'orange', 'red'].map((l) => (
          <div
            key={l}
            className="h-1.5 rounded-full"
            style={{ backgroundColor: l === level ? RISK_COLORS[l] : '#1F2A2D' }}
          />
        ))}
      </div>
    </div>
  )
}
