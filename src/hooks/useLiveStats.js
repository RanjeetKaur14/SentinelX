import { useEffect, useRef, useState } from 'react'

// Polls a JSON endpoint on an interval. Returns null data (never throws)
// if the URL is empty or the backend is unreachable, so callers can just
// fall back to mock values instead of showing an error state mid-demo.
export function useLiveStats(url, intervalMs = 2000) {
  const [data, setData] = useState(null)
  const [connected, setConnected] = useState(false)
  const timerRef = useRef(null)

  useEffect(() => {
    if (!url) return

    let cancelled = false

    async function poll() {
      try {
        const res = await fetch(url)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()
        if (!cancelled) {
          setData(json)
          setConnected(true)
        }
      } catch {
        if (!cancelled) setConnected(false)
      }
    }

    poll()
    timerRef.current = setInterval(poll, intervalMs)

    return () => {
      cancelled = true
      clearInterval(timerRef.current)
    }
  }, [url, intervalMs])

  return { data, connected }
}
