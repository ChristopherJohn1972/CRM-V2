import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { portalLogin, portalLogout, portalMe } from '../api/portal';

const PortalAuthContext = createContext(null);

export function PortalAuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem('portal_user');
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  });
  const [token, setToken] = useState(() => localStorage.getItem('portal_token'));
  const [bootstrapped, setBootstrapped] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      if (!localStorage.getItem('portal_token')) {
        setBootstrapped(true);
        return;
      }
      try {
        const me = await portalMe();
        if (cancelled) return;
        setUser(me);
        localStorage.setItem('portal_user', JSON.stringify(me));
      } catch {
        if (cancelled) return;
        localStorage.removeItem('portal_token');
        localStorage.removeItem('portal_user');
        setToken(null);
        setUser(null);
      } finally {
        if (!cancelled) setBootstrapped(true);
      }
    };
    boot();
    return () => { cancelled = true; };
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await portalLogin(email, password);
    localStorage.setItem('portal_token', data.token);
    localStorage.setItem('portal_user', JSON.stringify(data.user));
    setToken(data.token);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try { await portalLogout(); } catch { /* ignore */ }
    localStorage.removeItem('portal_token');
    localStorage.removeItem('portal_user');
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, token, isAuthenticated: Boolean(token && user), login, logout, bootstrapped }),
    [user, token, login, logout, bootstrapped],
  );

  return <PortalAuthContext.Provider value={value}>{children}</PortalAuthContext.Provider>;
}

export function usePortalAuth() {
  const ctx = useContext(PortalAuthContext);
  if (!ctx) throw new Error('usePortalAuth must be used inside PortalAuthProvider');
  return ctx;
}
