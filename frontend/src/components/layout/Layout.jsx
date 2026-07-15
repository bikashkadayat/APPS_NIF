import React, { useState, useEffect, useCallback } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import Header from './Header';
import LeaveSidebar from './LeaveSidebar';
import IdleWarningModal from '../common/IdleWarningModal';
import { useAuth } from '../../hooks/useAuth';
import { useIdleTimeout } from '../../hooks/useIdleTimeout';

const DESKTOP_MQ = '(min-width: 1024px)';
// Idle auto-logout (configurable via VITE_IDLE_TIMEOUT_MIN; default 20 min).
const IDLE_MIN = Number(import.meta.env.VITE_IDLE_TIMEOUT_MIN) || 20;
const IDLE_MS = IDLE_MIN * 60 * 1000;
const WARN_MS = 30 * 1000;

const Layout = () => {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { logout } = useAuth();
  const close = useCallback(() => setOpen(false), []);

  // Idle auto-logout: clear + blacklist tokens (useAuth.logout) and return to login.
  const handleIdleTimeout = useCallback(async () => {
    try { await logout(); } finally {
      try { localStorage.setItem('loggedOutReason', 'inactivity'); } catch { /* ignore */ }
      navigate('/login', { replace: true });
    }
  }, [logout, navigate]);
  const { warning, remaining, stayActive } = useIdleTimeout({
    timeoutMs: IDLE_MS, warningMs: WARN_MS, onTimeout: handleIdleTimeout,
  });

  // Auto-close the drawer on route change (nav-link click navigates then closes).
  useEffect(() => { setOpen(false); }, [location.pathname]);

  // Auto-close when the viewport crosses up to desktop, so state can't stick open.
  useEffect(() => {
    const mq = window.matchMedia(DESKTOP_MQ);
    const onChange = (e) => { if (e.matches) setOpen(false); };
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  // While open (mobile only): lock body scroll, ESC to close, move focus into the
  // drawer, trap Tab within it, and return focus to the hamburger on close.
  useEffect(() => {
    if (!open) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const drawer = document.getElementById('app-sidebar');
    const focusables = () => Array.from(
      drawer?.querySelectorAll('a[href], button:not([disabled])') || []
    );
    focusables()[0]?.focus();

    const onKey = (e) => {
      if (e.key === 'Escape') { setOpen(false); return; }
      if (e.key === 'Tab') {
        const items = focusables();
        if (!items.length) return;
        const firstEl = items[0], lastEl = items[items.length - 1];
        if (e.shiftKey && document.activeElement === firstEl) { e.preventDefault(); lastEl.focus(); }
        else if (!e.shiftKey && document.activeElement === lastEl) { e.preventDefault(); firstEl.focus(); }
      }
    };
    document.addEventListener('keydown', onKey);

    return () => {
      document.body.style.overflow = prevOverflow;
      document.removeEventListener('keydown', onKey);
      document.getElementById('menu-hamburger')?.focus();
    };
  }, [open]);

  return (
    <>
      <Header menuOpen={open} onMenu={() => setOpen((v) => !v)} />
      <div className="shell">
        <LeaveSidebar open={open} onClose={close} />
        <main className="main">
          <Outlet />
        </main>
      </div>
      <div className={`drawer-backdrop ${open ? 'show' : ''}`} onClick={close} aria-hidden="true" />
      {warning && <IdleWarningModal remaining={remaining} onStay={stayActive} onLogout={handleIdleTimeout} />}
    </>
  );
};

export default Layout;
