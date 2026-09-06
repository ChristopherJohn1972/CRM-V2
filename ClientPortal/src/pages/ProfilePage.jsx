import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { changePassword } from '../api/auth';
import { fetchProfile, updateProfile } from '../api/portal';
import { useAuth } from '../auth/AuthContext';
import PageHeader from '../components/PageHeader';
import Button from '../components/Button';
import Field from '../components/Field';
import Avatar from '../components/Avatar';
import { useToast } from '../components/Toast';
import { SkeletonCards } from '../components/Skeleton';
import { ErrorState } from '../components/States';
import { ROLE_LABELS } from '../utils/constants';

export function ProfilePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { user, updateUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState(searchParams.get('tab') || 'profile');
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProfile();
      setProfile(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);
  useEffect(() => { const t = searchParams.get('tab'); if (t) setTab(t); }, [searchParams]);

  const switchTab = (t) => { setTab(t); setSearchParams({ tab: t }); };

  if (loading) return <SkeletonCards />;
  if (error) return <ErrorState detail={error} onRetry={load} />;
  if (!profile) return null;

  return (
    <div>
      <PageHeader title="Profile" subtitle="Manage your account settings" />

      <div className="tabs" style={{ marginBottom: 'var(--space-6)' }}>
        <button className={`tab${tab === 'profile' ? ' is-active' : ''}`} onClick={() => switchTab('profile')}>Profile</button>
        <button className={`tab${tab === 'security' ? ' is-active' : ''}`} onClick={() => switchTab('security')}>Security</button>
        <button className={`tab${tab === 'users' ? ' is-active' : ''}`} onClick={() => switchTab('users')}>Authorized Users</button>
      </div>

      {tab === 'profile' && <ProfileTab profile={profile} toast={toast} />}
      {tab === 'security' && <SecurityTab toast={toast} />}
      {tab === 'users' && <UsersTab users={profile.authorized_users} />}
    </div>
  );
}

function ProfileTab({ profile, toast }) {
  const [name, setName] = useState(profile.customer_name);
  const [email, setEmail] = useState(profile.email);
  const [phone, setPhone] = useState(profile.phone);
  const [address, setAddress] = useState(profile.address);
  const [saving, setSaving] = useState(false);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateProfile({ customer_name: name, email, phone, address });
      toast.success('Profile updated successfully.');
    } catch (err) {
      toast.error(err.message || 'Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <div className="card__header">
        <h2 className="card__title">Contact Information</h2>
      </div>
      <div className="card__body">
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-5)', marginBottom: 'var(--space-6)' }}>
          <Avatar name={profile.customer_name} size={64} />
          <div>
            <div style={{ fontWeight: 600, fontSize: 'var(--text-lg)' }}>{profile.customer_name}</div>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>{profile.account_number}</div>
            <span className={`badge badge--${profile.account_status === 'Active' ? 'success' : 'warning'}`} style={{ marginTop: 'var(--space-2)' }}>
              {profile.account_status}
            </span>
          </div>
        </div>

        <form className="form" onSubmit={handleSave}>
          <div className="form-grid">
            <Field label="Company Name" htmlFor="prof-name">
              <input id="prof-name" className="field__input" value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Field label="Email" htmlFor="prof-email">
              <input id="prof-email" className="field__input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </Field>
            <Field label="Phone" htmlFor="prof-phone">
              <input id="prof-phone" className="field__input" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </Field>
            <Field label="Address" htmlFor="prof-address">
              <input id="prof-address" className="field__input" value={address} onChange={(e) => setAddress(e.target.value)} />
            </Field>
          </div>
          <div className="form-actions">
            <Button type="submit" variant="primary" loading={saving}>Save Changes</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function SecurityTab({ toast }) {
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (newPw !== confirmPw) { toast.error('Passwords do not match.'); return; }
    setSaving(true);
    try {
      await changePassword(currentPw, newPw);
      toast.success('Password changed successfully.');
      setCurrentPw('');
      setNewPw('');
      setConfirmPw('');
    } catch (err) {
      toast.error(err.message || 'Failed to change password.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <div className="card__header"><h2 className="card__title">Change Password</h2></div>
      <div className="card__body">
        <form className="form" onSubmit={handleSubmit} style={{ maxWidth: 480 }}>
          <Field label="Current Password" required htmlFor="sec-current">
            <input id="sec-current" type="password" className="field__input" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} autoComplete="current-password" />
          </Field>
          <Field label="New Password" required htmlFor="sec-new">
            <input id="sec-new" type="password" className="field__input" value={newPw} onChange={(e) => setNewPw(e.target.value)} autoComplete="new-password" />
          </Field>
          <Field label="Confirm New Password" required htmlFor="sec-confirm">
            <input id="sec-confirm" type="password" className="field__input" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} autoComplete="new-password" />
          </Field>
          <div className="form-actions">
            <Button type="submit" variant="primary" loading={saving} disabled={!currentPw || !newPw || !confirmPw}>Change Password</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function UsersTab({ users }) {
  return (
    <div className="card">
      <div className="card__header">
        <h2 className="card__title">Authorized Portal Users</h2>
        <Button variant="primary" size="sm" onClick={() => alert('Invite user feature will be available when backend is connected.')}>Invite User</Button>
      </div>
      <div className="card__body" style={{ padding: 0 }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>
                  <div className="person-cell">
                    <Avatar name={`${u.first_name} ${u.last_name}`} />
                    <div className="person-cell__meta">
                      <div className="person-cell__name">{u.first_name} {u.last_name}</div>
                      <div className="person-cell__sub">{u.email}</div>
                    </div>
                  </div>
                </td>
                <td><span className="badge badge--info">{ROLE_LABELS[u.role] || u.role}</span></td>
                <td><span className={`badge badge--${u.status === 'Active' ? 'success' : 'muted'}`}>{u.status}</span></td>
                <td>
                  <Button variant="ghost" size="sm">Manage</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ProfilePage;
