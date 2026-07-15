import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

// Single unified login for all roles (Phase 2.5). Public self-registration
// was removed; new accounts are created by an administrator.
const ROLE_ROUTES = {
  admin: '/leave',
  approver: '/leave',
  checker: '/leave/pending',
  maker: '/leave',
};

const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [formValues, setFormValues] = useState({ email: '', password: '' });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showLogoutSuccess, setShowLogoutSuccess] = useState(false);
  const from = location.state?.from?.pathname || '/';

  const [logoutReason, setLogoutReason] = useState(null);

  useEffect(() => {
    document.title = 'Office Management System — NIF';
    const reason = localStorage.getItem('loggedOutReason');
    if (reason === 'inactivity') {
      localStorage.removeItem('loggedOutReason');
      setLogoutReason('You were signed out due to inactivity. Please sign in again.');
    }
    const justLoggedOut = localStorage.getItem('justLoggedOut');
    if (justLoggedOut) {
      localStorage.removeItem('justLoggedOut');
      setShowLogoutSuccess(true);
      setTimeout(() => setShowLogoutSuccess(false), 4000);
    }
  }, []);

  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  const handleChange = (e) => setFormValues({ ...formValues, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await login(formValues.email, formValues.password);
      localStorage.setItem('justLoggedIn', 'true');
      // First-login password change takes precedence over the role redirect.
      if (user.must_change_password) {
        navigate('/auth/first-login-change-password', { replace: true });
        return;
      }
      navigate(ROLE_ROUTES[user.role] || from, { replace: true });
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      {showLogoutSuccess && (
        <div className="toast-notification">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          <span>Logged out successfully!</span>
        </div>
      )}
      {error && (
        <div className="popup-overlay" onClick={() => setError(null)}>
          <div className="popup-modal" onClick={(e) => e.stopPropagation()}>
            <div className="popup-icon popup-error-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
            </div>
            <h3>Login Failed</h3>
            <p>{error}</p>
            <button className="popup-btn" onClick={() => setError(null)}>OK</button>
          </div>
        </div>
      )}

      {/* Desktop branded hero: subtle mandala + Himalaya + bilingual brand */}
      <aside className="login-hero" aria-hidden="true">
        {/* Refined guilloché / mandala watermark (top-right), very slow spin */}
        <svg className="hero-mandala" viewBox="0 0 240 240" fill="none" stroke="currentColor" strokeWidth="1">
          <g className="mandala-spin">
            <circle cx="120" cy="120" r="112" />
            <circle cx="120" cy="120" r="94" />
            <circle cx="120" cy="120" r="60" />
            <circle cx="120" cy="120" r="32" />
            <circle cx="120" cy="120" r="15" />
            <defs>
              <path id="lp" d="M120 16 C144 52 144 84 120 114 C96 84 96 52 120 16 Z" />
              <path id="lp2" d="M120 44 C135 68 135 88 120 108 C105 88 105 68 120 44 Z" />
            </defs>
            {Array.from({ length: 12 }).map((_, i) => (
              <use key={`o${i}`} href="#lp" transform={`rotate(${i * 30} 120 120)`} />
            ))}
            {Array.from({ length: 12 }).map((_, i) => (
              <use key={`i${i}`} href="#lp2" transform={`rotate(${i * 30 + 15} 120 120)`} />
            ))}
            {Array.from({ length: 24 }).map((_, i) => (
              <circle key={`d${i}`} cx="120" cy="18" r="1.4" transform={`rotate(${i * 15} 120 120)`} />
            ))}
          </g>
          <circle className="mandala-accent" cx="120" cy="120" r="103" />
        </svg>

        {/* Drifting particles / faint stars in the upper navy sky */}
        <div className="hero-particles">
          <span /><span /><span /><span /><span /><span />
        </div>

        <div className="hero-content">
          <img src="/NIF.png" alt="" className="hero-logo" />
          <div className="hero-name-en">NEPAL INTERNET FOUNDATION</div>
          <div className="hero-name-np" lang="ne">नेपाल इन्टरनेट फाउन्डेसन</div>
          <p className="hero-tagline">
            Secure internal workspace
            <span lang="ne">सुरक्षित आन्तरिक कार्यक्षेत्र</span>
          </p>
        </div>

        <svg className="hero-himalaya" viewBox="0 0 1200 220" preserveAspectRatio="none" aria-hidden="true">
          <path className="ridge-back" d="M0 220 L120 88 L250 158 L400 64 L560 146 L700 40 L880 138 L1030 84 L1140 156 L1200 112 L1200 220 Z" />
          <path className="ridge-mid" d="M0 220 L150 150 L330 188 L520 128 L700 180 L900 146 L1080 190 L1200 158 L1200 220 Z" />
          <path className="ridge-front" d="M0 220 L120 182 L320 210 L500 176 L690 206 L900 182 L1080 210 L1200 188 L1200 220 Z" />
        </svg>

        {/* Last-mile connectivity: signal fanning from the Kathmandu hub out to
            remote village nodes across the range + hilltop villages & relay tower. */}
        <svg className="hero-network" viewBox="0 0 1200 400" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
          {/* elegant curved links fanning from the hub */}
          <g className="net-links">
            <path className="net-link" d="M330 300 Q230 244 150 235" />
            <path className="net-link" d="M330 300 Q400 214 470 150" />
            <path className="net-link net-flow" d="M330 300 Q490 182 650 110" />
            <path className="net-link" d="M330 300 Q580 224 820 190" />
            <path className="net-link net-flow" d="M330 300 Q660 194 985 140" />
            <path className="net-link" d="M330 300 Q720 244 1105 210" />
            <path className="net-link net-flow" d="M330 300 Q670 252 1000 256" />
          </g>

          {/* broadcast arcs above the hub */}
          <g className="net-arcs">
            <path className="net-arc" d="M295 300 A35 35 0 0 1 365 300" />
            <path className="net-arc" d="M278 300 A52 52 0 0 1 382 300" />
            <path className="net-arc" d="M260 300 A70 70 0 0 1 400 300" />
          </g>

          {/* remote hilltop villages + relay tower with Wi-Fi arcs */}
          <g className="net-village">
            <path d="M120 300 L134 289 L148 300" />
            <path d="M123 300 L123 311 L145 311 L145 300" />
            <path d="M150 302 L160 294 L170 302" />
            <path d="M152 302 L152 311 L168 311 L168 302" />
            <path d="M800 300 L813 290 L826 300" />
            <path d="M803 300 L803 311 L823 311 L823 300" />
            <path d="M1000 300 L1000 256" />
            <path d="M1000 300 L991 310" />
            <path d="M1000 300 L1009 310" />
            <path d="M994 284 L1006 292" />
            <path d="M1006 284 L994 292" />
            <path d="M989 250 A15 15 0 0 1 1011 250" />
            <path d="M982 254 A24 24 0 0 1 1018 254" />
          </g>

          {/* nodes: varied sizes, crimson accents among blue/white; hub with halo */}
          <g className="net-nodes">
            <circle className="net-hub-halo" cx="330" cy="300" r="11" />
            <circle className="net-hub" cx="330" cy="300" r="4.6" />
            <circle className="net-node net-twinkle" cx="150" cy="235" r="2.6" />
            <circle className="net-node" cx="470" cy="150" r="2.2" />
            <circle className="net-node-accent net-twinkle" cx="650" cy="110" r="3.2" />
            <circle className="net-node" cx="820" cy="190" r="2.6" />
            <circle className="net-node net-twinkle" cx="985" cy="140" r="3" />
            <circle className="net-node" cx="1105" cy="210" r="2.2" />
            <circle className="net-node-accent net-twinkle" cx="1000" cy="256" r="3" />
          </g>
        </svg>
      </aside>

      <div className="login-panel">
      <main className="auth-card" role="main">
        <div className="flag-bar" aria-hidden="true" />
        <div className="auth-brand">
          <img src="/NIF.png" alt="Nepal Internet Foundation" className="auth-logo" width="180" height="80" />
          <h1 className="auth-title">Office Management System</h1>
          <p className="auth-devanagari" lang="ne">नेपाल इन्टरनेट फाउन्डेसन</p>
          <p className="auth-tagline">Secure internal workspace</p>
        </div>

        {logoutReason && (
          <div role="status" style={{ background: '#fffbeb', border: '1px solid #fde68a', color: '#92400e', borderRadius: 10, padding: '10px 14px', fontSize: 13, marginBottom: 18, textAlign: 'center' }}>
            {logoutReason}
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-field">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              name="email"
              type="email"
              value={formValues.email}
              onChange={handleChange}
              required
              placeholder="you@nif.org.np"
              autoComplete="username"
              autoFocus
            />
          </div>

          <div className="auth-field">
            <label htmlFor="login-password">Password</label>
            <div className="password-input-wrapper">
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                name="password"
                value={formValues.password}
                onChange={handleChange}
                required
                placeholder="Enter your password"
                autoComplete="current-password"
              />
              <button type="button" className="password-toggle" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword}>
                {showPassword ? (
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                )}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary auth-submit"
            disabled={loading || !formValues.email.trim() || !formValues.password}
          >
            {loading ? (
              <><span className="auth-spinner" aria-hidden="true" />Signing in…</>
            ) : 'Sign In'}
          </button>
        </form>

        <p className="auth-help">Forgot your password? Contact your administrator.</p>
        <p className="auth-copyright">© Nepal Internet Foundation · Kathmandu, Nepal</p>
      </main>
      </div>
    </div>
  );
};

export default Login;
