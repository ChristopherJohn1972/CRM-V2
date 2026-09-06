import { useAuth } from '../auth/AuthContext';

export function PermissionGate({ permission, children, fallback = null }) {
  const { hasPermission } = useAuth();
  if (!hasPermission(permission)) return fallback;
  return children;
}

export default PermissionGate;
