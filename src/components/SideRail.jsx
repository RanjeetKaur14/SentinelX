const ITEMS = [
  { id: 'overview', label: 'OV', title: 'Overview' },
  { id: 'cameras', label: 'CA', title: 'Cameras' },
  { id: 'zones', label: 'ZN', title: 'Zones' },
  { id: 'alerts', label: 'AL', title: 'Alerts' },
  { id: 'sim', label: 'WI', title: 'What-If' }
]

export default function SideRail({ active, onSelect }) {
  return (
    <nav className="hidden w-14 flex-col items-center gap-2 border-r border-line py-4 sm:flex">
      {ITEMS.map((item) => (
        <button
          key={item.id}
          title={item.title}
          onClick={() => onSelect(item.id)}
          className={`grid h-9 w-9 place-items-center rounded-md font-mono text-[11px] transition-colors ${
            active === item.id
              ? 'bg-signal/15 text-signal'
              : 'text-muted hover:bg-panel2 hover:text-ink'
          }`}
        >
          {item.label}
        </button>
      ))}
    </nav>
  )
}
