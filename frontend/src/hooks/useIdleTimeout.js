import { useEffect, useRef, useState, useCallback } from 'react';

// Cross-tab last-activity timestamp: any tab's activity keeps every tab alive.
export const IDLE_ACTIVITY_KEY = 'nif-last-activity';
const ACTIVITY_EVENTS = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'click'];

/**
 * Idle auto-logout timer. Polls a shared localStorage timestamp (multi-tab safe):
 *  - fires `onTimeout` once after `timeoutMs` of no activity across all tabs,
 *  - surfaces a `warning` (with live `remaining` seconds) in the last `warningMs`.
 * Activity resets it — except while the warning is showing, so the countdown is
 * real; the user must explicitly `stayActive()` (or move on after dismiss).
 */
export function useIdleTimeout({ timeoutMs = 20 * 60 * 1000, warningMs = 30 * 1000, onTimeout, enabled = true }) {
  const [warning, setWarning] = useState(false);
  const [remaining, setRemaining] = useState(Math.ceil(warningMs / 1000));
  const warningRef = useRef(false);
  const firedRef = useRef(false);

  const stamp = useCallback(() => {
    try { localStorage.setItem(IDLE_ACTIVITY_KEY, String(Date.now())); } catch { /* storage unavailable */ }
  }, []);

  useEffect(() => {
    if (!enabled) return undefined;
    if (!localStorage.getItem(IDLE_ACTIVITY_KEY)) stamp();

    let lastWrite = 0;
    const onActivity = () => {
      if (warningRef.current) return;                 // don't auto-dismiss the warning
      const t = Date.now();
      if (t - lastWrite > 1000) { lastWrite = t; stamp(); }
    };
    ACTIVITY_EVENTS.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));

    const tick = setInterval(() => {
      const last = Number(localStorage.getItem(IDLE_ACTIVITY_KEY)) || Date.now();
      const idle = Date.now() - last;
      if (idle >= timeoutMs) {
        if (!firedRef.current) { firedRef.current = true; onTimeout?.(); }
      } else if (idle >= timeoutMs - warningMs) {
        if (!warningRef.current) { warningRef.current = true; setWarning(true); }
        setRemaining(Math.max(0, Math.ceil((timeoutMs - idle) / 1000)));
      } else if (warningRef.current) {
        warningRef.current = false; setWarning(false);       // another tab reset it
      }
    }, 1000);

    return () => {
      ACTIVITY_EVENTS.forEach((e) => window.removeEventListener(e, onActivity));
      clearInterval(tick);
    };
  }, [enabled, timeoutMs, warningMs, onTimeout, stamp]);

  const stayActive = useCallback(() => {
    warningRef.current = false; firedRef.current = false;
    setWarning(false); stamp();
  }, [stamp]);

  return { warning, remaining, stayActive };
}

export default useIdleTimeout;
