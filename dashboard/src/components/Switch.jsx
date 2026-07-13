export default function Switch({ label, checked, onChange }) {
  return (
    <label className="flex cursor-pointer items-center gap-2.5 select-none">
      <span
        onClick={() => onChange(!checked)}
        className={`relative h-5 w-9 rounded-full transition-colors ${
          checked ? 'bg-signal' : 'bg-line'
        }`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
            checked ? 'translate-x-4' : 'translate-x-0.5'
          }`}
        />
      </span>
      <span className="text-sm text-ink">{label}</span>
    </label>
  )
}
