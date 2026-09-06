import { useAuth } from '../auth/AuthContext';

/**
 * PermissionGate hides UI actions users are not allowed to perform.
 * The backend remains the enforcement point — this is convenience only.
 *
 * All current user permissions are supplied by the backend in the
 * login/`/api/auth/me` response (`user.permissions`).
 */
export function PermissionGate({ permission, mode = 'hidden', children }) {
  const { hasPermission } = useAuth();

  if (permission === undefined || permission === null) return children;

  const allowed = hasPermission(permission);

  if (allowed) return children;

  if (mode === 'disabled') {
    return <span aria-disabled="true" title="You do not have permission to perform this action">{children}</span>;
  }

  return null;
}

export default PermissionGate;