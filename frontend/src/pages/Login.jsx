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

  useEffect(() => {
    document.title = 'Office Management System — NIF';
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
    <div className="page login-page">
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

      <main className="auth-card" role="main">
        <div className="auth-brand">
          <img src="/NIF.png" alt="Nepal Internet Foundation" className="auth-logo" width="190" height="84" />
          <h1 className="auth-title">Office Management System</h1>
          <p className="auth-tagline">Nepal Internet Foundation — Secure internal workspace</p>
        </div>

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
      </main>
    </div>
  );
};

export default Login;
