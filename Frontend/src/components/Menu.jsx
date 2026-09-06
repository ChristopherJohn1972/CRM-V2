import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { cn } from '../utils/cn';

export function Menu({ trigger, children }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className="menu" ref={ref}>
      <span role="button" tabIndex={0} onClick={() => setOpen((v) => !v)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setOpen((v) => !v); }} aria-haspopup="menu" aria-expanded={open}>
        {trigger}
      </span>
      {open && (
        <div className="menu__panel" role="menu" style={undefined}>
          {typeof children === 'function' ? children(() => setOpen(false)) : children}
        </div>
      )}
    </div>
  );
}

export function MenuItem({ children, onClick, danger, disabled, className }) {
  return (
    <button
      type="button"
      role="menuitem"
      className={cn('menu__item', danger && 'menu__item--danger', className)}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

export function MenuLinkItem({ to, children, className }) {
  return (
    <Link to={to} role="menuitem" className={cn('menu__item menu__item--link', className)}>
      {children}
    </Link>
  );
}

export default Menu;