import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';

export function RequireAuth() {
  const { isAuthenticated, user, bootstrapped } = useAuth();
  const location = useLocation();

  if (!bootstrapped) return <div className="app-loading">Loading...</div>;

  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;

  if (user?.password_setup_required) return <Navigate to="/setup-password" replace />;

  return <Outlet />;
}

export function RequirePasswordSetup() {
  const { isAuthenticated, user, bootstrapped } = useAuth();

  if (!bootstrapped) return <div className="app-loading">Loading...</div>;

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  if (!user?.password_setup_required) return <Navigate to="/" replace />;

  return <Outlet />;
}

export default RequireAuth;
