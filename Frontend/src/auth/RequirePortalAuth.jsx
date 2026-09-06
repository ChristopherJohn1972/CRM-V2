import { Navigate, Outlet } from 'react-router-dom';
import { usePortalAuth } from './PortalAuthContext';

export function RequirePortalAuth() {
  const { isAuthenticated, bootstrapped } = usePortalAuth();

  if (!bootstrapped) {
    return <div className="page-loading">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/portal/login" replace />;
  }

  return <Outlet />;
}

export default RequirePortalAuth;
