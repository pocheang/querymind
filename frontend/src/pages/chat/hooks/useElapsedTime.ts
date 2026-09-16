import { useEffect, useState } from "react";

/**
 * Milliseconds elapsed since `active` most recently became true, ticking
 * every `tickMs` while it stays true. Resets to 0 the instant `active` goes
 * false, so a caller does not have to track "which run is this" itself --
 * flipping `active` false and back true (a new question) starts the clock
 * over on its own.
 */
export function useElapsedTime(active: boolean, tickMs = 250): number {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!active) {
      setElapsed(0);
      return;
    }
    const startedAt = Date.now();
    setElapsed(0);
    const id = window.setInterval(() => setElapsed(Date.now() - startedAt), tickMs);
    return () => window.clearInterval(id);
  }, [active, tickMs]);

  return elapsed;
}
