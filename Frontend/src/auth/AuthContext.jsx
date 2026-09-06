import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { login as loginRequest, logout as logoutRequest, fetchMe } from '../api/auth';
import {
  clearStoredSession,
  getStoredToken,
  getStoredUser,
  storeSession,
} from './tokenStore';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredUser());
  const [token, setToken] = useState(() => getStoredToken());
  const [bootstrapped, setBootstrapped] = useState(false);

  const refreshUser = useCallback(async () => {
    const me = await fetchMe();
    setUser(me);
    const currentToken = getStoredToken();
    if (currentToken) storeSession(currentToken, me);
    return me;
  }, []);

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      if (!getStoredToken()) {
        setBootstrapped(true);
        return;
      }
      try {
        const me = await fetchMe();
        if (cancelled) return;
        setUser(me);
        const currentToken = getStoredToken();
        setToken(currentToken);
        if (currentToken) storeSession(currentToken, me);
      } catch (err) {
        if (cancelled) return;
        if (err && err.status === 401) {
          clearStoredSession();
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) setBootstrapped(true);
      }
    };
    boot();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (username, password) => {
    const session = await loginRequest(username, password);
    storeSession(session.token, session.user);
    setToken(session.token);
    setUser(session.user);
    return session.user;
  }, []);

  const logout = useCallback(async () => {
    await logoutRequest();
    clearStoredSession();
    setToken(null);
    setUser(null);
  }, []);

  const hasPermission = useCallback(
    (code) => {
      if (!user) return false;
      return (user.permissions || []).includes(code);
    },
    [user]
  );

  const value = useMemo(
    () => ({ user, token, isAuthenticated: Boolean(token && user), hasPermission, login, logout, refreshUser, bootstrapped }),
    [user, token, hasPermission, login, logout, refreshUser, bootstrapped]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}

export default AuthContext;