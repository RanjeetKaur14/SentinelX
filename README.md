# CrowdShield — Dashboard (Team 4)

Ops-room style live dashboard for the CrowdShield stampede-prevention system.
React + Vite + Tailwind + Chart.js, running entirely on mock data until the
backend (Team 3) exposes real endpoints.

## Run it

```bash
cd crowdshield-dashboard
npm install
npm run dev
```

Open http://localhost:5173

## What's here

```
src/
  components/
    TopBar.jsx          top bar: identity, clock, system status pill
    SideRail.jsx         left nav rail
    RiskGauge.jsx        signature radial "sonar sweep" risk instrument
    StatCard.jsx          headline metric readout
    CameraGrid.jsx         camera feed placeholders + detection overlay
    DensityHeatmap.jsx      per-zone density bars
    AlertsFeed.jsx           live alert timeline
    Timeline.jsx              20-minute risk score chart (Chart.js)
    WhatIfPanel.jsx            rule-based redirect simulator (the differentiator feature)
  data/
    mockData.js           stand-in for the FastAPI/WebSocket feed
  lib/
    risk.js                shared risk-level colors + helpers
```

## Design system

- **Colors**: charcoal base (`#0B0F10`), raised panels (`#12181A`), signal
  teal (`#3ADBC4`) for live/tracking UI, and the risk scale green → yellow →
  orange → red as the only saturated colors on the page.
- **Type**: Space Grotesk for headers, Inter for body/labels, **JetBrains
  Mono for every number** (counts, timestamps, scores) — this is what makes
  it read as an instrument panel instead of a generic admin template.
- Full tokens live in `tailwind.config.js`.

## Wiring up the real backend

Everything the UI needs is read from `src/data/mockData.js`, shaped to look
like the JSON coming out of `shared/schemas.py`. To go live:

1. Create `src/api/client.js` with real `fetch`/WebSocket calls to Team 3's
   FastAPI endpoints (people count, zone density, alerts, risk score).
2. Replace the static imports in `App.jsx` with state populated by that
   client (`useState` + `useEffect`, or a small WebSocket hook for the
   camera/zone/alert streams).
3. Component props are already typed by usage (see each component file) —
   as long as the real payload matches the mock shape, no component changes
   are needed.
4. For live video, swap the placeholder `<div>` in `CameraGrid.jsx` for an
   `<img>` (MJPEG stream) or `<video>` element pointed at the camera feed URL.

## Notes for the demo

- The **What-If panel** is the feature to lead with when judges ask "what
  makes this different from just detecting people" — it's rule-based
  (`simulateRedirect` in `mockData.js`), cheap to compute, and turns the
  dashboard from monitoring into decision support.
- `npm run build` produces a static `dist/` you can also just double-click
  open, if you need a zero-dependency fallback during the demo.
