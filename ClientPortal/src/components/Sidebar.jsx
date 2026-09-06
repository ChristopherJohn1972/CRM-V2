import { NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { PERMISSIONS } from '../utils/constants';

const ICON = 'side-nav__link__icon';

function DashboardIcon() {
  return (
    <svg className={ICON} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="1.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="9.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="1.5" y="9.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="9.5" y="9.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function PaymentsIcon() {
  return (
    <svg className={ICON} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="1.5" y="3.5" width="13" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M1.5 6.5h13" stroke="currentColor" strokeWidth="1.5" />
      <path d="M4 9.5h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function ComplaintsIcon() {
  return (
    <svg className={ICON} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 1.5l5.5 3v4c0 3.3-2.4 5.4-5.5 6.5-3.1-1.1-5.5-3.2-5.5-6.5v-4L8 1.5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M6 8l1.5 1.5L10 6.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DocumentsIcon() {
  return (
    <svg className={ICON} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M9.5 1.5H4a1.5 1.5 0 00-1.5 1.5v10A1.5 1.5 0 004 14.5h8A1.5 1.5 0 0013.5 13V5.5L9.5 1.5z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M9.5 1.5v4h4" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

function MomentumIcon() {
  return (
    <svg className={ICON} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 1.5l1.8 3.7 4 .6-2.9 2.8.7 4L8 10.6 4.4 12.6l.7-4L2.2 5.8l4-.6L8 1.5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

function RewardsIcon() {
  return (
    <svg className={ICON} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="2" y="5" width="12" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M5 5V3.5a3 3 0 016 0V5" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="8" cy="9" r="1.5" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function NotificationsIcon() {
  return (
    <svg className={ICON} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M4 6a4 4 0 018 0v2l1.5 2H2.5L4 8V6z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M6.5 12.5a1.5 1.5 0 003 0" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function ProfileIcon() {
  return (
    <svg className={ICON} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="5.5" r="3" stroke="currentColor" strokeWidth="1.5" />
      <path d="M2.5 14.5c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function SupportIcon() {
  return (
    <svg className={ICON} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M6 6.5a2 2 0 112.5 1.9c-.3.1-.5.3-.5.6V10" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <circle cx="8" cy="12" r="0.5" fill="currentColor" />
    </svg>
  );
}

const NAV_ITEMS = [
  { label: 'Dashboard', to: '/', end: true, icon: <DashboardIcon /> },
  { label: 'Payments', to: '/payments', permission: PERMISSIONS.VIEW_PAYMENTS, icon: <PaymentsIcon /> },
  { label: 'Complaints', to: '/complaints', permission: PERMISSIONS.RAISE_COMPLAINT, icon: <ComplaintsIcon /> },
  { label: 'Documents', to: '/documents', permission: PERMISSIONS.VIEW_DOCUMENTS, icon: <DocumentsIcon /> },
  { label: 'Momentum', to: '/momentum', permission: PERMISSIONS.VIEW_MOMENTUM, icon: <MomentumIcon /> },
  { label: 'Rewards', to: '/rewards', permission: PERMISSIONS.REDEEM_REWARD, icon: <RewardsIcon /> },
  { label: 'Notifications', to: '/notifications', icon: <NotificationsIcon /> },
  { label: 'Profile', to: '/profile', icon: <ProfileIcon /> },
  { label: 'Support', to: '/support', icon: <SupportIcon /> },
];

function NavLinkItem({ item }) {
  return (
    <NavLink to={item.to} end={item.end} className={({ isActive }) => `side-nav__link${isActive ? ' is-active' : ''}`}>
      {item.icon}
      {item.label}
    </NavLink>
  );
}

export function Sidebar() {
  const { hasPermission } = useAuth();
  const visible = NAV_ITEMS.filter((item) => !item.permission || hasPermission(item.permission));

  return (
    <aside className="app-sidebar">
      <nav className="side-nav" aria-label="Main">
        {visible.map((item) => <NavLinkItem key={item.to} item={item} />)}
      </nav>
    </aside>
  );
}

export const PORTAL_NAV_ITEMS = NAV_ITEMS;

export default Sidebar;
