import { useState, createContext, useContext, useEffect } from 'react';
import { authService } from '../services/authService';

const AuthContext = createContext();

const buildUiUser = (profile) => {
  const name = profile.full_name || profile.email?.split('@')[0] || 'User';
  const initials = name
    .split(' ')
    .map((word) => word[0] || '')
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const colorMap = {
    maker: '#10B981',
    checker: '#F59E0B',
    approver: '#DC143C',
    admin: '#2563EB',
  };

  return {
    id: profile.id,
    username: profile.username,
    email: profile.email,
    employee_id: profile.employee_id,
    department: profile.department || profile.department_name || null,
    designation: profile.designation || null,
    full_name: name,
    name,
    title: profile.role ? profile.role.charAt(0).toUpperCase() + profile.role.slice(1) : 'User',
    initials: initials || profile.email?.slice(0, 2).toUpperCase() || 'U',
    color: colorMap[profile.role] || '#6B7280',
    must_change_password: Boolean(profile.must_change_password),
    profile_photo: profile.profile_photo || null,
  };
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [mustChangePassword, setMustChangePassword] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadUser = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const response = await authService.me();
      setUser(buildUiUser(response.data));
      setRole(response.data.role);
      setMustChangePassword(Boolean(response.data.must_change_password));
      setIsAuthenticated(true);
    } catch {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      setUser(null);
      setRole(null);
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  // Unified login for all roles. Returns the backend `user` block so the caller
  // can enforce first-login password change and redirect by role.
  const login = async (email, password) => {
    setError(null);
    try {
      const response = await authService.login(email, password);
      const { access, refresh, user: userBlock } = response.data;
      localStorage.setItem('accessToken', access);
      localStorage.setItem('refreshToken', refresh);
      setUser(buildUiUser(userBlock));
      setRole(userBlock.role);
      setMustChangePassword(Boolean(userBlock.must_change_password));
      setIsAuthenticated(true);
      return userBlock;
    } catch (err) {
      setError(err);
      throw err;
    }
  };

  const completePasswordChange = () => {
    setMustChangePassword(false);
    setUser((prev) => (prev ? { ...prev, must_change_password: false } : prev));
  };

  const logout = async () => {
    // Flip UI state immediately so the app treats the user as logged out at once.
    const refresh = localStorage.getItem('refreshToken');
    setUser(null);
    setRole(null);
    setIsAuthenticated(false);
    setMustChangePassword(false);
    // Best-effort server-side blacklist of the (rotation-current) refresh token —
    // uses the tokens still in storage. Never leave the user half-logged-in: clear
    // client tokens whether or not the call succeeds (M5).
    try {
      if (refresh) await authService.logout(refresh);
    } catch {
      // network/expired token — proceed to clear locally regardless.
    } finally {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
    }
  };

  return (
    <AuthContext.Provider value={{
      user, role, isAuthenticated, mustChangePassword, loading, error,
      login, logout, completePasswordChange, refreshUser: loadUser,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext); // eslint-disable-line react-refresh/only-export-components
