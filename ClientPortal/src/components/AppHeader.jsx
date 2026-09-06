import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import Avatar from './Avatar';
import { Menu, MenuItem } from './Menu';

export function AppHeader() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const name = user ? `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.customer_name : '';

  return (
    <header className="app-header">
      <div className="app-header__brand">
        <span className="app-header__brand-mark" aria-hidden="true" />
        <span>Client Portal</span>
      </div>
      <div className="app-header__user">
        {user?.account_number && (
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
            {user.account_number}
          </span>
        )}
        <Menu
          trigger={
            <span className="user-menu">
              <Avatar name={name} />
              <span className="user-menu__name">{name}</span>
            </span>
          }
        >
          <MenuItem onClick={() => navigate('/profile')}>My Profile</MenuItem>
          <MenuItem onClick={() => navigate('/profile?tab=security')}>Security</MenuItem>
          <MenuItem
            onClick={async () => {
              await logout();
              navigate('/login', { replace: true });
            }}
            danger
          >
            Sign out
          </MenuItem>
        </Menu>
      </div>
    </header>
  );
}

export default AppHeader;
