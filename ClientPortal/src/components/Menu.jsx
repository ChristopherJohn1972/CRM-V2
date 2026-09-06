import { useState, useRef, useEffect } from 'react';

export function Menu({ trigger, children }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    if (open) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  return (
    <div className="menu" ref={ref}>
      <div onClick={() => setOpen(!open)}>{trigger}</div>
      {open && <div className="menu__panel" onClick={() => setOpen(false)}>{children}</div>}
    </div>
  );
}

export function MenuItem({ children, onClick, danger, disabled, href }) {
  const cls = `menu__item${danger ? ' menu__item--danger' : ''}`;
  if (href) {
    return <a className={cls} href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
  }
  return (
    <button className={cls} onClick={onClick} disabled={disabled} type="button">
      {children}
    </button>
  );
}
