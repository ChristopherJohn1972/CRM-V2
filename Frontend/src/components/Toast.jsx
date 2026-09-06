import { createContext, useCallback, useContext, useState } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((list) => list.filter((t) => t.id !== id));
  }, []);

  const notify = useCallback((title, options = {}) => {
    const id = Date.now() + Math.random();
    const toast = { id, title, message: options.message || '', variant: options.variant || 'info' };
    setToasts((list) => [...list, toast]);
    if (options.duration !== 0) {
      window.setTimeout(() => dismiss(id), options.duration || 5000);
    }
    return id;
  }, [dismiss]);

  return (
    <ToastContext.Provider value={{ notify, dismiss }}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast--${t.variant}`}>
            <div>
              <div className="toast__title">{t.title}</div>
              {t.message && <div>{t.message}</div>}
            </div>
            <button className="icon-btn" type="button" onClick={() => dismiss(t.id)} aria-label="Dismiss notification">✕</button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
  return ctx;
}

export default ToastProvider;