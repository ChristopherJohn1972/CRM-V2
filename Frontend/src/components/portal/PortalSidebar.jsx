import { NavLink, useNavigate } from 'react-router-dom';
import { usePortalAuth } from '../../auth/PortalAuthContext';

const ICON = 'side-nav__link__icon';

function QuotesIcon() {
  return (
    <svg className={`${ICON} side-nav__link__icon--quotes`} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="2.5" y="1.5" width="11" height="13" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M5.5 5h5M5.5 8h5M5.5 11h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function DashboardIcon() {
  return (
    <svg className={`${ICON} side-nav__link__icon--dashboard`} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="9" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="2" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="9" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function LogoutIcon() {
  return (
    <svg className={`${ICON}`} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M6 2H4a2 2 0 00-2 2v8a2 2 0 002 2h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M10 11l3-3-3-3M13 8H6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function NavLinkItem({ item }) {
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) => `side-nav__link${isActive ? ' is-active' : ''}`}
    >
      {item.icon}
      {item.label}
    </NavLink>
  );
}

export function PortalSidebar() {
  const { user, logout } = usePortalAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/portal/login');
  };

  return (
    <aside className="app-sidebar">
      <nav className="side-nav" aria-label="Portal">
        <NavLinkItem item={{ label: 'Dashboard', to: '/portal', end: true, icon: <DashboardIcon /> }} />
        <NavLinkItem item={{ label: 'My Quotes', to: '/portal/quotes', end: true, icon: <QuotesIcon /> }} />

        <div className="side-nav__divider" role="separator" />

        <button className="side-nav__link side-nav__link--logout" onClick={handleLogout}>
          <LogoutIcon />
          Sign Out
        </button>
      </nav>

      {user && (
        <div className="portal-sidebar__user">
          <div className="portal-sidebar__user-name">{user.first_name} {user.last_name}</div>
          <div className="portal-sidebar__user-account">{user.account_number}</div>
        </div>
      )}
    </aside>
  );
}

export default PortalSidebar;
