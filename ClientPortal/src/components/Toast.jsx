import { createContext, useCallback, useContext, useMemo, useState } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((toast) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, ...toast }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  const success = useCallback((message) => addToast({ type: 'success', message }), [addToast]);
  const error = useCallback((message) => addToast({ type: 'error', message }), [addToast]);
  const info = useCallback((message) => addToast({ type: 'info', message }), [addToast]);

  const value = useMemo(() => ({ addToast, success, error, info }), [addToast, success, error, info]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      {toasts.length > 0 && (
        <div className="toast-stack">
          {toasts.map((t) => (
            <div key={t.id} className={`toast toast--${t.type || 'info'}`}>
              <div>
                <div className="toast__title">{t.title || (t.type === 'success' ? 'Success' : t.type === 'error' ? 'Error' : 'Notice')}</div>
                <div>{t.message}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
  return ctx;
}
