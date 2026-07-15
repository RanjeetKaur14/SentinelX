// src/api/client.js
// Talks to stream_server.py (integration/stream_server.py), which is
// what actually runs detection + forwards to risk_engine. See that
// file's docstring for the full architecture.
//
// If you deploy this somewhere other than localhost, set
// VITE_STREAM_SERVER_URL in a .env file (Vite picks it up automatically).

export const STREAM_SERVER_URL =
  import.meta.env.VITE_STREAM_SERVER_URL || 'http://localhost:8001'

export function getVideoFeedUrl() {
  // Cache-busting isn't needed for MJPEG (it's a single long-lived
  // connection), so this URL can be used directly in an <img src="">.
  return `${STREAM_SERVER_URL}/video_feed`
}

export async function fetchLiveStatus() {
  const res = await fetch(`${STREAM_SERVER_URL}/live_status`)
  if (!res.ok) throw new Error(`live_status request failed: ${res.status}`)
  return res.json()
}
