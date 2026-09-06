import { useEffect, useState } from 'react';
import { NavLink, Link, useNavigate, useLocation } from 'react-router-dom';
import { usePortalAuth } from '../../auth/PortalAuthContext';
import { portalMe } from '../../api/portal';
import { getMomentumBalance } from '../../api/momentum';
import { portalListNotifications } from '../../api/portal';

function BellIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M10 2a5 5 0 00-5 5v3l-1.3 2.6a.5.5 0 00.45.7h11.7a.5.5 0 00.45-.7L15 10V7a5 5 0 00-5-5z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 14a2 2 0 004 0" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function HomeIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M3 8.5l7-6 7 6V16a1 1 0 01-1 1H4a1 1 0 01-1-1V8.5z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 17v-5h4v5" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function CampaignIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M3 10l7-7 7 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 8.5V16a1 1 0 001 1h8a1 1 0 001-1V8.5" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function ReferIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <circle cx="7" cy="7" r="3" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="14" cy="14" r="3" stroke="currentColor" strokeWidth="1.5" />
      <path d="M9.5 8.5l2 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function MomentumIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M10 2l2.5 5 5.5.8-4 3.9.9 5.3L10 14.5 5.1 17l.9-5.3-4-3.9 5.5-.8L10 2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

function PurchasesIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M6 6h8l1.5 8H4.5L6 6z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 6V4a2 2 0 014 0v2" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <circle cx="10" cy="7" r="3" stroke="currentColor" strokeWidth="1.5" />
      <path d="M4 17c0-3.3 2.7-6 6-6s6 2.7 6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

const NAV_ITEMS = [
  { to: '/portal', label: 'Home', icon: <HomeIcon />, end: true },
  { to: '/portal/campaigns', label: 'Campaigns', icon: <CampaignIcon /> },
  { to: '/portal/referrals', label: 'Refer', icon: <ReferIcon /> },
  { to: '/portal/momentum', label: 'Momentum', icon: <MomentumIcon /> },
  { to: '/portal/purchases', label: 'Purchases', icon: <PurchasesIcon /> },
];

export function PortalLayout({ children }) {
  const { user, logout } = usePortalAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [unreadCount, setUnreadCount] = useState(0);
  const [momentumPts, setMomentumPts] = useState(null);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [n, m] = await Promise.all([
          portalListNotifications({ unread_only: true }).catch(() => ({ count: 0 })),
          getMomentumBalance().catch(() => null),
        ]);
        setUnreadCount(n.count || n.results?.length || 0);
        setMomentumPts(m?.balance ?? null);
      } catch {}
    }
    load();
  }, [location.pathname]);

  useEffect(() => { setProfileMenuOpen(false); }, [location.pathname]);

  const handleLogout = async () => {
    await logout();
    navigate('/portal/login');
  };

  return (
    <div className="portal-app">
      {/* Desktop top header */}
      <header className="portal-topbar">
        <div className="portal-topbar__inner">
          <Link to="/portal" className="portal-topbar__brand">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
              <rect x="2" y="2" width="18" height="18" rx="3" stroke="currentColor" strokeWidth="2" />
              <path d="M7 11h8M11 7v8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <span className="portal-topbar__brand-text">Portal</span>
          </Link>

          <nav className="portal-topbar__nav" aria-label="Main navigation">
            {NAV_ITEMS.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `portal-topbar__link${isActive ? ' is-active' : ''}`}
              >
                {item.icon}
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="portal-topbar__right">
            {momentumPts !== null && (
              <Link to="/portal/momentum" className="portal-topbar__momentum">
                <MomentumIcon />
                <span>{momentumPts} pts</span>
              </Link>
            )}

            <Link to="/portal/notifications" className="portal-topbar__bell" aria-label="Notifications">
              <BellIcon />
              {unreadCount > 0 && <span className="portal-topbar__badge">{unreadCount > 9 ? '9+' : unreadCount}</span>}
            </Link>

            <div className="portal-topbar__profile">
              <button className="portal-topbar__avatar" onClick={() => setProfileMenuOpen(o => !o)} aria-label="Account menu">
                <UserIcon />
              </button>
              {profileMenuOpen && (
                <div className="portal-topbar__dropdown">
                  <div className="portal-topbar__dropdown-header">
                    <div className="portal-topbar__dropdown-name">{user?.first_name} {user?.last_name}</div>
                    <div className="portal-topbar__dropdown-account">{user?.account_number}</div>
                  </div>
                  <Link to="/portal/profile" className="portal-topbar__dropdown-item">Profile & Preferences</Link>
                  <Link to="/portal/notifications" className="portal-topbar__dropdown-item">Notifications</Link>
                  <button className="portal-topbar__dropdown-item portal-topbar__dropdown-item--danger" onClick={handleLogout}>Sign Out</button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="portal-main">
        <div className="portal-main__content">
          {children}
        </div>
      </main>

      {/* Mobile bottom nav */}
      <nav className="portal-bottomnav" aria-label="Mobile navigation">
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `portal-bottomnav__item${isActive ? ' is-active' : ''}`}
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export default PortalLayout;
