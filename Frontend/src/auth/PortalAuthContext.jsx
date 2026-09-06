import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { portalLogin as portalLoginRequest, portalLogout as portalLogoutRequest, portalMe } from '../api/portal';
import {
  clearPortalSession,
  getPortalToken,
  getPortalUser,
  storePortalSession,
} from './portalTokenStore';

const PortalAuthContext = createContext(null);

export function PortalAuthProvider({ children }) {
  const [user, setUser] = useState(() => getPortalUser());
  const [token, setToken] = useState(() => getPortalToken());
  const [bootstrapped, setBootstrapped] = useState(false);
  const [mustChangePassword, setMustChangePassword] = useState(false);

  const refreshUser = useCallback(async () => {
    const me = await portalMe();
    setUser(me);
    const currentToken = getPortalToken();
    if (currentToken) storePortalSession(currentToken, me);
    return me;
  }, []);

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      if (!getPortalToken()) {
        setBootstrapped(true);
        return;
      }
      try {
        const me = await portalMe();
        if (cancelled) return;
        setUser(me);
        const currentToken = getPortalToken();
        setToken(currentToken);
        if (currentToken) storePortalSession(currentToken, me);
      } catch (err) {
        if (cancelled) return;
        if (err && err.status === 401) {
          clearPortalSession();
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) setBootstrapped(true);
      }
    };
    boot();
    return () => { cancelled = true; };
  }, []);

  const login = useCallback(async (email, accountNumber, password) => {
    const session = await portalLoginRequest(email, accountNumber, password);
    storePortalSession(session.token, session.portalUser);
    setToken(session.token);
    setUser(session.portalUser);
    setMustChangePassword(session.mustChangePassword);
    return session.portalUser;
  }, []);

  const logout = useCallback(async () => {
    await portalLogoutRequest();
    clearPortalSession();
    setToken(null);
    setUser(null);
    setMustChangePassword(false);
  }, []);

  const value = useMemo(
    () => ({ user, token, isAuthenticated: Boolean(token && user), mustChangePassword, login, logout, refreshUser, bootstrapped }),
    [user, token, mustChangePassword, login, logout, refreshUser, bootstrapped]
  );

  return <PortalAuthContext.Provider value={value}>{children}</PortalAuthContext.Provider>;
}

export function usePortalAuth() {
  const ctx = useContext(PortalAuthContext);
  if (!ctx) throw new Error('usePortalAuth must be used inside <PortalAuthProvider>');
  return ctx;
}

export default PortalAuthContext;
