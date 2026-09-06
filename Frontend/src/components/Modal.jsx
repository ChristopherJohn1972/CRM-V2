import { useEffect } from 'react';
import { createPortal } from 'react-dom';

export function Modal({ open, onClose, title, footer, children, labelledBy, wide, scrollable, className = '' }) {
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
    <div className="modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className={`modal${wide ? ' modal--wide' : ''}${className ? ` ${className}` : ''}`} role="dialog" aria-modal="true" aria-labelledby={labelledBy || 'modal-title'}>
        <div className="modal__header">
          <h2 className="modal__title" id={labelledBy || 'modal-title'}>{title}</h2>
          <button className="icon-btn" type="button" onClick={onClose} aria-label="Close dialog">✕</button>
        </div>
        <div className={`modal__body${scrollable ? ' modal__body--scroll' : ''}`}>{children}</div>
        {footer && <div className="modal__footer">{footer}</div>}
      </div>
    </div>,
    document.body
  );
}

export default Modal;