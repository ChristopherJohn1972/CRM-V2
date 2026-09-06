import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { RequireAuth } from './auth/RequireAuth';
import { PortalAuthProvider } from './auth/PortalAuthContext';
import { RequirePortalAuth } from './auth/RequirePortalAuth';
import { ToastProvider } from './components/Toast';
import AppLayout from './AppLayout';
import { PortalLayout } from './components/portal/PortalLayout';
import LoginPage from './pages/LoginPage';
import SignUpPage from './pages/SignUpPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import ClientsPage from './pages/ClientsPage';
import AddClientPage from './pages/AddClientPage';
import Customer360Page from './pages/Customer360Page';
import EditClientPage from './pages/EditClientPage';
import NotFoundPage from './pages/NotFoundPage';
import OperatorsPage from './pages/operators/OperatorsPage';
import AddOperatorPage from './pages/operators/AddOperatorPage';
import OperatorProfilePage from './pages/operators/OperatorProfilePage';
import AccessReviewPage from './pages/operators/AccessReviewPage';
import RolesPage from './pages/access/RolesPage';
import RoleDetailPage from './pages/access/RoleDetailPage';
import CreateRolePage from './pages/access/CreateRolePage';
import RightsPage from './pages/access/RightsPage';
import QuoteListPage from './pages/quotes/QuoteListPage';
import CreateQuotePage from './pages/quotes/CreateQuotePage';
import QuoteWorkspacePage from './pages/quotes/QuoteWorkspacePage';
import QuoteStudioPage from './pages/quotes/QuoteStudioPage';
import QuotePreviewPage from './pages/quotes/QuotePreviewPage';
import SalesOrderListPage from './pages/salesOrders/SalesOrderListPage';
import CreateSalesOrderPage from './pages/salesOrders/CreateSalesOrderPage';
import EditSalesOrderPage from './pages/salesOrders/EditSalesOrderPage';
import SalesOrderWorkspacePage from './pages/salesOrders/SalesOrderWorkspacePage';
import CampaignCommandCenter from './pages/campaigns/CampaignCommandCenter';
import CampaignDetailPage from './pages/campaigns/CampaignDetailPage';
import CreateCampaignPage from './pages/campaigns/CreateCampaignPage';
import EditCampaignPage from './pages/campaigns/EditCampaignPage';
import LeadListPage from './pages/leads/LeadListPage';
import CreateLeadPage from './pages/leads/CreateLeadPage';
import LeadDetailPage from './pages/leads/LeadDetailPage';
import PortalLoginPage from './pages/portal/PortalLoginPage';
import PortalDashboardPage from './pages/portal/PortalDashboardPage';
import PortalQuotesPage from './pages/portal/PortalQuotesPage';
import PortalQuoteDetailPage from './pages/portal/PortalQuoteDetailPage';
import PortalHomeDashboard from './pages/portal/PortalHomeDashboard';
import PortalCampaignListPage from './pages/portal/PortalCampaignListPage';
import PortalCampaignDetailPage from './pages/portal/PortalCampaignDetailPage';
import PortalLeadCapturePage from './pages/portal/PortalLeadCapturePage';
import PortalReferEarnHubPage from './pages/portal/PortalReferEarnHubPage';
import PortalMomentumWalletPage from './pages/portal/PortalMomentumWalletPage';
import LeadSubmissionSuccess from './pages/portal/LeadSubmissionSuccess';
import MyInterestsPage from './pages/portal/MyInterestsPage';
import InterestDetailPage from './pages/portal/InterestDetailPage';
import ReceiptVerifyPage from './pages/salesOrders/ReceiptVerifyPage';

function Shell() {
  return (
    <AppLayout>
      <Routes>
        <Route index element={<Navigate to="/clients" replace />} />
        <Route path="clients" element={<ClientsPage />} />
        <Route path="clients/new" element={<AddClientPage />} />
        <Route path="customers/:customerId" element={<Customer360Page />} />
        <Route path="customers/:customerId/edit" element={<EditClientPage />} />
        <Route path="quotes" element={<QuoteListPage />} />
        <Route path="quotes/new" element={<CreateQuotePage />} />
        <Route path="quotes/:quoteId/view" element={<QuotePreviewPage />} />
        <Route path="quotes/:quoteId" element={<QuoteWorkspacePage />} />
        <Route path="studio" element={<QuoteStudioPage />} />
        <Route path="studio/:quoteId" element={<QuoteStudioPage />} />
        <Route path="sales-orders" element={<SalesOrderListPage />} />
        <Route path="sales-orders/new" element={<CreateSalesOrderPage />} />
        <Route path="sales-orders/:orderId/edit" element={<EditSalesOrderPage />} />
        <Route path="sales-orders/:orderId" element={<SalesOrderWorkspacePage />} />
        <Route path="campaigns" element={<CampaignCommandCenter />} />
        <Route path="campaigns/new" element={<CreateCampaignPage />} />
        <Route path="campaigns/:campaignId/edit" element={<EditCampaignPage />} />
        <Route path="campaigns/:campaignId" element={<CampaignDetailPage />} />
        <Route path="leads" element={<LeadListPage />} />
        <Route path="leads/new" element={<CreateLeadPage />} />
        <Route path="leads/:leadId" element={<LeadDetailPage />} />
        <Route path="operators" element={<OperatorsPage />} />
        <Route path="operators/new" element={<AddOperatorPage />} />
        <Route path="operators/:operatorId" element={<OperatorProfilePage />} />
        <Route path="operators/:operatorId/access-review" element={<AccessReviewPage />} />
        <Route path="roles" element={<RolesPage />} />
        <Route path="roles/new" element={<CreateRolePage />} />
        <Route path="roles/:roleId" element={<RoleDetailPage />} />
        <Route path="rights" element={<RightsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppLayout>
  );
}

function PortalShell() {
  return (
    <PortalLayout>
      <Routes>
        <Route index element={<PortalHomeDashboard />} />
        <Route path="home" element={<PortalHomeDashboard />} />
        <Route path="dashboard" element={<PortalDashboardPage />} />
        <Route path="quotes" element={<PortalQuotesPage />} />
        <Route path="quotes/:quoteId" element={<PortalQuoteDetailPage />} />
        <Route path="campaigns" element={<PortalCampaignListPage />} />
        <Route path="campaigns/:campaignId" element={<PortalCampaignDetailPage />} />
        <Route path="leads/new" element={<PortalLeadCapturePage />} />
        <Route path="leads/success" element={<LeadSubmissionSuccess />} />
        <Route path="interests" element={<MyInterestsPage />} />
        <Route path="interests/:leadId" element={<InterestDetailPage />} />
        <Route path="referrals" element={<PortalReferEarnHubPage />} />
        <Route path="momentum" element={<PortalMomentumWalletPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </PortalLayout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <PortalAuthProvider>
        <ToastProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignUpPage />} />
              <Route path="/forgot-password" element={<ForgotPasswordPage />} />
              <Route path="/reset-password" element={<ResetPasswordPage />} />
              <Route path="/portal/login" element={<PortalLoginPage />} />
              <Route path="/verify/receipt/:token" element={<ReceiptVerifyPage />} />
              <Route element={<RequireAuth />}>
                <Route path="/*" element={<Shell />} />
              </Route>
              <Route element={<RequirePortalAuth />}>
                <Route path="/portal/*" element={<PortalShell />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </PortalAuthProvider>
    </AuthProvider>
  );
}