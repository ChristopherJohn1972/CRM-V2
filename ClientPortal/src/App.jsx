import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { RequireAuth, RequirePasswordSetup } from './auth/RequireAuth';
import { ToastProvider } from './components/Toast';
import AppLayout from './AppLayout';
import LoginPage from './pages/LoginPage';
import SetupPasswordPage from './pages/SetupPasswordPage';
import DashboardPage from './pages/DashboardPage';
import PaymentsPage from './pages/PaymentsPage';
import PaymentDetailPage from './pages/PaymentDetailPage';
import ComplaintsPage from './pages/ComplaintsPage';
import ComplaintDetailPage from './pages/ComplaintDetailPage';
import DocumentsPage from './pages/DocumentsPage';
import MomentumPage from './pages/MomentumPage';
import RewardsPage from './pages/RewardsPage';
import NotificationsPage from './pages/NotificationsPage';
import ProfilePage from './pages/ProfilePage';
import SupportPage from './pages/SupportPage';
import NotFoundPage from './pages/NotFoundPage';

function PortalShell() {
  return (
    <AppLayout>
      <Routes>
        <Route index element={<DashboardPage />} />
        <Route path="payments" element={<PaymentsPage />} />
        <Route path="payments/:paymentId" element={<PaymentDetailPage />} />
        <Route path="complaints" element={<ComplaintsPage />} />
        <Route path="complaints/:complaintId" element={<ComplaintDetailPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="momentum" element={<MomentumPage />} />
        <Route path="rewards" element={<RewardsPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="support" element={<SupportPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppLayout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<RequirePasswordSetup />}>
              <Route path="/setup-password" element={<SetupPasswordPage />} />
            </Route>
            <Route element={<RequireAuth />}>
              <Route path="/*" element={<PortalShell />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}
