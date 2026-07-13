export default function StatCard({ label, value, sub }) {
  return (
    <div className="panel px-4 py-3">
      <p className="eyebrow">{label}</p>
      <p className="mt-1.5 font-mono text-2xl font-semibold text-ink">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}
    </div>
  )
}
