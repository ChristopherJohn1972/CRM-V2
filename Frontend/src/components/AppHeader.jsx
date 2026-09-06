import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import Avatar from '../components/Avatar';
import { Menu, MenuItem } from '../components/Menu';

export function AppHeader() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const name = user ? `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username : '';
  const role = user?.role || user?.groups?.[0]?.name || '';

  return (
    <header className="app-header">
      <Link to="/clients" className="app-header__brand">
        <img src="/crm-logo.jpg" alt="CRM" className="app-header__brand-logo" />
      </Link>

      <div className="app-header__user">
        <Menu
          trigger={
            <button className="profile-control" type="button">
              <Avatar name={name} size={32} />
              <div className="profile-control__text">
                <span className="profile-control__name">{name}</span>
                {role && <span className="profile-control__role">{role}</span>}
              </div>
              <svg className="profile-control__chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>
          }
        >
          <div className="menu__header">
            <Avatar name={name} size={36} />
            <div className="menu__header-text">
              <div className="menu__header-name">{name}</div>
              {role && <div className="menu__header-role">{role}</div>}
            </div>
          </div>
          <div className="menu__divider" />
          <MenuItem onClick={() => navigate('/profile')}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            My Profile
          </MenuItem>
          <MenuItem onClick={() => navigate('/settings')}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            Settings
          </MenuItem>
          <MenuItem onClick={() => navigate('/change-password')}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            Change Password
          </MenuItem>
          <div className="menu__divider" />
          <MenuItem danger onClick={async () => { await logout(); navigate('/login', { replace: true }); }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            Sign Out
          </MenuItem>
        </Menu>
      </div>
    </header>
  );
}

export default AppHeader;
