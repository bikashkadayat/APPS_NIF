import React, { useState, useEffect, useCallback } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Header from './Header';
import LeaveSidebar from './LeaveSidebar';

const DESKTOP_MQ = '(min-width: 1024px)';

const Layout = () => {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const close = useCallback(() => setOpen(false), []);

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
    </>
  );
};

export default Layout;
