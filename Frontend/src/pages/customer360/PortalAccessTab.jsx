import { useCallback, useEffect, useState } from 'react';
import { getPortalAccess, resetPortalPassword } from '../../api/customers';
import Button from '../../components/Button';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import SkeletonTable from '../../components/SkeletonTable';
import { useToast } from '../../components/Toast';
import { formatDateTime } from '../../utils/format';

export function PortalAccessTab({ customerId }) {
  const { notify } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [resetBusy, setResetBusy] = useState(false);
  const [resetResult, setResetResult] = useState(null);
  const [copiedField, setCopiedField] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getPortalAccess(customerId);
      setData(res);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleReset = async (portalUserId) => {
    setResetBusy(true);
    try {
      const res = await resetPortalPassword(customerId, { portal_user_id: portalUserId });
      setResetResult(res.reset_credentials);
      setData(res);
      notify('Password reset', {
        message: 'Temporary password has been generated.',
        variant: 'success',
      });
    } catch (err) {
      notify('Reset failed', {
        message: err.message || 'Could not reset the portal password.',
        variant: 'error',
      });
    } finally {
      setResetBusy(false);
    }
  };

  const copyToClipboard = async (text, field) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    }
  };

  if (loading) return <SkeletonTable columns={3} rows={4} />;
  if (error) return <ErrorState title="Could not load portal access" body={error.message} onRetry={load} />;

  if (!data?.provisioned) {
    return (
      <div className="form" style={{ gap: 20 }}>
        <EmptyState
          title="Portal access not provisioned"
          body="This customer does not have a portal account. Portal access is automatically provisioned when a customer is created with an email address."
        />
      </div>
    );
  }

  const portalUrl = data.portal_url || '';
  const users = data.portal_users || [];

  return (
    <div className="form" style={{ gap: 20 }}>
      {resetResult && (
        <div className="card card--highlight" style={{ borderLeft: '3px solid var(--color-success)' }}>
          <div className="card__body">
            <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600 }}>Temporary Password Generated</h3>
            <p style={{ margin: '0 0 12px', fontSize: 13, color: 'var(--color-text-secondary)' }}>
              Share this credential securely with the customer. They must change it on first login.
            </p>
            <dl className="def-list" style={{ margin: 0 }}>
              <dt>Email</dt>
              <dd>{resetResult.email}</dd>
              <dt>Temporary password</dt>
              <dd style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <code style={{ fontSize: 14, padding: '4px 8px', background: 'var(--color-bg-secondary)', borderRadius: 4 }}>
                  {resetResult.temp_password}
                </code>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(resetResult.temp_password, 'reset-password')}
                >
                  {copiedField === 'reset-password' ? 'Copied!' : 'Copy'}
                </Button>
              </dd>
            </dl>
          </div>
        </div>
      )}

      <section className="card">
        <div className="card__header">
          <h2 className="card__title">Portal Login</h2>
        </div>
        <div className="card__body">
          <dl className="def-list" style={{ display: 'grid', gridTemplateColumns: 'minmax(120px, 160px) 1fr', gap: '12px' }}>
            <dt>Portal URL</dt>
            <dd style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {portalUrl ? (
                <>
                  <a href={portalUrl} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 500 }}>
                    {portalUrl}
                  </a>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(portalUrl, 'url')}
                  >
                    {copiedField === 'url' ? 'Copied!' : 'Copy'}
                  </Button>
                </>
              ) : (
                <span className="cell-secondary">Not configured</span>
              )}
            </dd>
            <dt>Account number</dt>
            <dd><code>{data.account_number}</code></dd>
            <dt>Account status</dt>
            <dd>{data.account_status || 'Active'}</dd>
          </dl>
        </div>
      </section>

      <section className="card">
        <div className="card__header">
          <h2 className="card__title">Linked Portal Users</h2>
        </div>
        <div className="card__body">
          {users.length === 0 ? (
            <p className="field__hint">No portal users are linked to this customer account.</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table data-table--desktop">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Last Login</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.portal_user_id}>
                      <td style={{ fontWeight: 500 }}>{user.first_name} {user.last_name}</td>
                      <td className="cell-nowrap">{user.email}</td>
                      <td>
                        <span className="badge badge--neutral">{user.role}</span>
                        {user.is_primary && <span className="badge badge--info" style={{ marginLeft: 4 }}>Primary</span>}
                      </td>
                      <td>
                        <span className={`badge badge--${user.status?.split('.').pop() === 'ACTIVE' ? 'success' : user.status?.split('.').pop() === 'PENDING' ? 'warning' : 'neutral'}`}>
                          {user.status?.split('.').pop() || user.status}
                        </span>
                      </td>
                      <td className="cell-nowrap">{user.last_login_at ? formatDateTime(user.last_login_at) : 'Never'}</td>
                      <td>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleReset(user.portal_user_id)}
                          loading={resetBusy}
                          title="Reset this user's portal password"
                        >
                          Reset Password
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      <p className="field__hint" style={{ fontSize: 12 }}>
        Temporary passwords are securely hashed and never stored in plaintext.
        The credential is returned only at generation or reset time and must be shared out-of-band.
      </p>
    </div>
  );
}

export default PortalAccessTab;
