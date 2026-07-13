export default function CameraConfig({ cameras, selected, onToggle }) {
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      <span className="eyebrow mr-1">Cameras</span>
      {cameras.map((cam) => {
        const active = selected.includes(cam.id)
        return (
          <button
            key={cam.id}
            onClick={() => onToggle(cam.id)}
            className={`rounded-full border px-3 py-1 font-mono text-[11px] transition-colors ${
              active
                ? 'border-signal bg-signal/10 text-signal'
                : 'border-line text-muted hover:border-muted'
            }`}
          >
            {cam.id.toUpperCase()}
          </button>
        )
      })}
    </div>
  )
}
