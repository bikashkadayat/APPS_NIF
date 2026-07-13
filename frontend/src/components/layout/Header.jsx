import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth.jsx';
import NotificationBell from '../notifications/NotificationBell.jsx';
import Avatar from '../common/Avatar.jsx';
import { todayBS, msUntilMidnight } from '../../services/bsDate.js';

const Header = ({ menuOpen = false, onMenu }) => {
  const navigate = useNavigate();
  const { role, user, logout } = useAuth();

  // Live Nepali (BS) date, refreshed automatically at midnight.
  const [bsDate, setBsDate] = useState(() => todayBS());
  useEffect(() => {
    let timer;
    const tick = () => {
      setBsDate(todayBS());
      timer = setTimeout(tick, msUntilMidnight());
    };
    timer = setTimeout(tick, msUntilMidnight());
    return () => clearTimeout(timer);
  }, []);

  const handleLogout = () => {
    localStorage.setItem('justLoggedOut', 'true');
    logout();
    navigate('/login');
  };

  return (
    <header className="header">

      {/* Mobile-only hamburger (CSS hides it on desktop). Toggles the nav drawer. */}
      <button
        id="menu-hamburger"
        type="button"
        className="hd-hamburger"
        aria-label={menuOpen ? 'Close menu' : 'Open menu'}
        aria-expanded={menuOpen}
        aria-controls="app-sidebar"
        onClick={onMenu}
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M3 6h18M3 12h18M3 18h18" />
        </svg>
      </button>

      <div className="hd-brand">
        <button
          type="button"
          className="hd-logo hd-logo-btn"
          onClick={() => navigate('/leave')}
          aria-label="Go to dashboard"
          style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
        >
          <img src="/NIF.png" alt="NIF Logo" style={{ height: '42px', objectFit: 'contain' }} />
        </button>
        <div className="hd-sep"></div>
        <div className="hd-meta" style={{ display: 'flex', flexDirection: 'column' }}>
          <span className="hd-portal" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', letterSpacing: '1px' }}>PORTAL SYSTEM</span>
          <span className="hd-bs" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>B.S. {bsDate || '—'}</span>
        </div>
      </div>
      <div className="hd-right" style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <NotificationBell />
        <div className="hd-user" onClick={() => navigate('/profile')} style={{ cursor: 'pointer' }}>
          <Avatar className="hd-av" photo={user?.profile_photo} initials={user?.initials || 'U'}
                  color={user?.initials ? user.color : '#999'} size={40} radius="12px" fontSize={14} />
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 600 }}>{user?.full_name || user?.username || 'User'}</div>
            <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>{user?.email || ''} · {role ? role.charAt(0).toUpperCase() + role.slice(1) : 'Guest'}</div>
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={handleLogout} style={{ marginLeft: '18px' }}>
          Logout
        </button>
      </div>
    </header>
  );
};

export default Header;
