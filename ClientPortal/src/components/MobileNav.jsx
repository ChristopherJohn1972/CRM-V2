import { NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { PORTAL_NAV_ITEMS } from './Sidebar';

export function MobileNav() {
  const { hasPermission } = useAuth();
  const items = PORTAL_NAV_ITEMS.filter((item) => !item.permission || hasPermission(item.permission)).slice(0, 5);

  return (
    <nav className="mobile-nav" aria-label="Mobile navigation">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) => `mobile-nav__item${isActive ? ' is-active' : ''}`}
        >
          {item.icon}
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}

export default MobileNav;
