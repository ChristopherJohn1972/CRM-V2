import { useEffect } from 'react';
import { createPortal } from 'react-dom';

export function Drawer({ open, onClose, title, footer, children, labelledBy }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="drawer-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="drawer" role="dialog" aria-modal="true" aria-labelledby={labelledBy || 'drawer-title'}>
        <div className="drawer__header">
          <h2 className="drawer__title" id={labelledBy || 'drawer-title'}>{title}</h2>
          <button className="icon-btn" type="button" onClick={onClose} aria-label="Close panel">✕</button>
        </div>
        <div className="drawer__body">{children}</div>
        {footer && <div className="drawer__footer">{footer}</div>}
      </div>
    </div>,
    document.body
  );
}

export default Drawer;