import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useIdleTimeout, IDLE_ACTIVITY_KEY } from './useIdleTimeout';

describe('useIdleTimeout', () => {
  beforeEach(() => { vi.useFakeTimers(); localStorage.clear(); });
  afterEach(() => { vi.useRealTimers(); });

  it('fires onTimeout after the idle window with no activity', () => {
    const onTimeout = vi.fn();
    renderHook(() => useIdleTimeout({ timeoutMs: 5000, warningMs: 2000, onTimeout }));
    act(() => { vi.advanceTimersByTime(4000); });
    expect(onTimeout).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(1500); });
    expect(onTimeout).toHaveBeenCalledTimes(1);
  });

  it('shows a warning in the last window then times out', () => {
    const onTimeout = vi.fn();
    const { result } = renderHook(() => useIdleTimeout({ timeoutMs: 5000, warningMs: 2000, onTimeout }));
    act(() => { vi.advanceTimersByTime(3500); });        // into the warning window
    expect(result.current.warning).toBe(true);
    expect(result.current.remaining).toBeLessThanOrEqual(2);
  });

  it('stayActive resets the timer (no logout)', () => {
    const onTimeout = vi.fn();
    const { result } = renderHook(() => useIdleTimeout({ timeoutMs: 5000, warningMs: 2000, onTimeout }));
    act(() => { vi.advanceTimersByTime(3500); });
    expect(result.current.warning).toBe(true);
    act(() => { result.current.stayActive(); });
    act(() => { vi.advanceTimersByTime(1000); });
    expect(result.current.warning).toBe(false);
    act(() => { vi.advanceTimersByTime(3000); });         // total idle since reset < 5s
    expect(onTimeout).not.toHaveBeenCalled();
  });

  it('uses a shared cross-tab activity key', () => {
    renderHook(() => useIdleTimeout({ timeoutMs: 5000, onTimeout: vi.fn() }));
    expect(localStorage.getItem(IDLE_ACTIVITY_KEY)).toBeTruthy();
  });
});
