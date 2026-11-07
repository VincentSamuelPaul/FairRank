import { useEffect, useRef, useState } from 'react'

/** True when the person asked the OS for less motion. Everything animated checks this. */
export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(prefersReducedMotion)
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const on = () => setReduced(mq.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  return reduced
}

/**
 * Counts from 0 to `target` once, on first paint. Later changes of `target` apply immediately.
 * No animation under reduced motion and in tests, so numbers are always correct the instant they render.
 */
export function useCountUp(target: number, ms = 400): number {
  const skip = prefersReducedMotion() || import.meta.env.MODE === 'test'
  const played = useRef(false)
  const [v, setV] = useState(skip ? target : 0)
  useEffect(() => {
    if (skip || played.current) {
      setV(target)
      return
    }
    let raf = 0
    const t0 = performance.now()
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / ms)
      setV(Math.round(target * (1 - (1 - p) ** 3)))
      if (p < 1) raf = requestAnimationFrame(tick)
      else played.current = true // only once it has finished, so React StrictMode's double effect still animates in dev
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms, skip])
  return v
}

/** Renders a number that counts up on first paint. */
export function CountUp({ value, ms = 400 }: { value: number; ms?: number }) {
  return <>{useCountUp(value, ms)}</>
}
