import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { PortalAuthProvider, usePortalAuth } from './auth/PortalAuth';
import LoginPage from './pages/LoginPage';
import QuotesListPage from './pages/QuotesListPage';
import QuoteDetailPage from './pages/QuoteDetailPage';

function RequirePortalAuth() {
  const { isAuthenticated, bootstrapped } = usePortalAuth();
  if (!bootstrapped) return <div className="portal-loading">Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function PortalLayout({ children }) {
  return (
    <div className="portal">
      <header className="portal-header">
        <div className="portal-header__brand">Client Portal</div>
      </header>
      <main className="portal-main">{children}</main>
    </div>
  );
}

function PortalShell() {
  return (
    <PortalLayout>
      <Routes>
        <Route index element={<Navigate to="/quotes" replace />} />
        <Route path="quotes" element={<QuotesListPage />} />
        <Route path="quotes/:quoteId" element={<QuoteDetailPage />} />
        <Route path="*" element={<Navigate to="/quotes" replace />} />
      </Routes>
    </PortalLayout>
  );
}

export default function App() {
  return (
    <PortalAuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequirePortalAuth />}>
            <Route path="/*" element={<PortalShell />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </PortalAuthProvider>
  );
}
