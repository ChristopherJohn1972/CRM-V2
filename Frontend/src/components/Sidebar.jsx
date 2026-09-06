import { NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { PERMISSIONS, QUOTE_PERMISSIONS } from '../utils/constants';

const ICON = 'side-nav__link__icon';

/* ─── Icons: unique, colorful, immediately recognizable ─── */

function ClientsIcon() {
  return (
    <svg className={`${ICON} side-nav__link__icon--clients`} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function QuotesIcon() {
  return (
    <svg className={`${ICON} side-nav__link__icon--quotes`} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  );
}

function OrdersIcon() {
  return (
    <svg className={`${ICON} side-nav__link__icon--orders`} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="9" cy="21" r="1" />
      <circle cx="20" cy="21" r="1" />
      <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
    </svg>
  );
}

function CampaignsIcon() {
  return (
    <svg className={`${ICON} side-nav__link__icon--campaigns`} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 11l18-5v12L3 13v-2z" />
      <path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" />
    </svg>
  );
}

function LeadsIcon() {
  return (
    <svg className={`${ICON} side-nav__link__icon--leads`} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 2L2 7l10 5 10-5-10-5z" />
      <path d="M2 17l10 5 10-5" />
      <path d="M2 12l10 5 10-5" />
    </svg>
  );
}

function OperatorsIcon() {
  return (
    <svg className={`${ICON} side-nav__link__icon--operators`} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 18v-6a9 9 0 0 1 18 0v6" />
      <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" />
    </svg>
  );
}

function RolesIcon() {
  return (
    <svg className={`${ICON} side-nav__link__icon--roles`} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

function RightsIcon() {
  return (
    <svg className={`${ICON} side-nav__link__icon--rights`} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
    </svg>
  );
}

/* ─── Navigation configuration ─── */

const PRIMARY_NAV = [
  { label: 'Clients', to: '/clients', end: true, icon: <ClientsIcon /> },
];

const SALES_NAV = [
  { label: 'Quotes', to: '/quotes', end: true, icon: <QuotesIcon /> },
  { label: 'Sales Orders', to: '/sales-orders', end: true, icon: <OrdersIcon /> },
];

const MARKETING_NAV = [
  { label: 'Campaigns', to: '/campaigns', end: true, icon: <CampaignsIcon /> },
  { label: 'Leads', to: '/leads', end: true, icon: <LeadsIcon /> },
];

const IAM_NAV = [
  { label: 'Operators', to: '/operators', end: true, permission: PERMISSIONS.IAM_USER_MANAGE, icon: <OperatorsIcon /> },
  { label: 'Roles', to: '/roles', end: true, permission: PERMISSIONS.IAM_ROLE_MANAGE, icon: <RolesIcon /> },
  { label: 'Rights', to: '/rights', end: true, permission: PERMISSIONS.IAM_PERMISSION_AUDIT, icon: <RightsIcon /> },
];

/* ─── Sub-components ─── */

function NavLinkItem({ item }) {
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) => `side-nav__link${isActive ? ' is-active' : ''}`}
    >
      {item.icon}
      <span className="side-nav__link__label">{item.label}</span>
    </NavLink>
  );
}

function NavSection({ label, children }) {
  return (
    <>
      <div className="side-nav__section-label">{label}</div>
      {children}
    </>
  );
}

/* ─── Main sidebar ─── */

export function Sidebar() {
  const { hasPermission, user } = useAuth();
  const visibleSales = SALES_NAV;
  const visibleIam = IAM_NAV.filter((item) => hasPermission(item.permission));

  return (
    <aside className="app-sidebar">
      <nav className="side-nav" aria-label="Main">
        {PRIMARY_NAV.map((item) => <NavLinkItem key={item.to} item={item} />)}

        {visibleSales.length > 0 && (
          <>
            <div className="side-nav__divider" role="separator" />
            <NavSection label="Sales & Commerce">
              {visibleSales.map((item) => <NavLinkItem key={item.to} item={item} />)}
            </NavSection>
          </>
        )}

        {MARKETING_NAV.length > 0 && (
          <>
            <div className="side-nav__divider" role="separator" />
            <NavSection label="Marketing & Leads">
              {MARKETING_NAV.map((item) => <NavLinkItem key={item.to} item={item} />)}
            </NavSection>
          </>
        )}

        {visibleIam.length > 0 && (
          <>
            <div className="side-nav__divider" role="separator" />
            {visibleIam.map((item) => <NavLinkItem key={item.to} item={item} />)}
          </>
        )}
      </nav>
    </aside>
  );
}

export default Sidebar;
