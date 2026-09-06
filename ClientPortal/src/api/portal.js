import { get, post, put, ApiError } from './client';

const USE_MOCK = !import.meta.env.VITE_API_BASE_URL;

const MOCK_DASHBOARD = {
  customer_name: 'ABC Company',
  account_number: '000124',
  account_status: 'Active',
  outstanding_balance: 4250.00,
  balance_date: '2026-08-24T10:30:00Z',
  momentum: { balance: 1240, earned_this_month: 120, next_reward_distance: 260 },
  open_complaints: 2,
  unread_notifications: 5,
  recent_payments: [
    { id: 'pay_001', date: '2026-08-24', reference: 'PAY-1045', amount: 1500.00, status: 'Confirmed', has_receipt: true },
    { id: 'pay_002', date: '2026-08-18', reference: 'PAY-1038', amount: 3000.00, status: 'Confirmed', has_receipt: true },
    { id: 'pay_003', date: '2026-08-10', reference: 'PAY-1031', amount: 2000.00, status: 'Confirmed', has_receipt: true },
  ],
  recent_notifications: [
    { id: 'n1', type: 'payment', title: 'Payment received', text: 'PAY-1045 confirmed', time: '2 hours ago', unread: true },
    { id: 'n2', type: 'complaint', title: 'Complaint updated', text: 'SR-2045 is now In Progress', time: '1 day ago', unread: true },
    { id: 'n3', type: 'document', title: 'New document', text: 'Invoice INV-2026-089 available', time: '2 days ago', unread: false },
  ],
};

const MOCK_PAYMENTS = [
  { id: 'pay_001', date: '2026-08-24', reference: 'PAY-1045', amount: 1500.00, status: 'Confirmed', has_receipt: true, description: 'Monthly service payment' },
  { id: 'pay_002', date: '2026-08-18', reference: 'PAY-1038', amount: 3000.00, status: 'Confirmed', has_receipt: true, description: 'Quarterly premium' },
  { id: 'pay_003', date: '2026-08-10', reference: 'PAY-1031', amount: 2000.00, status: 'Confirmed', has_receipt: true, description: 'Service payment' },
  { id: 'pay_004', date: '2026-07-24', reference: 'PAY-1022', amount: 1500.00, status: 'Confirmed', has_receipt: true, description: 'Monthly service payment' },
  { id: 'pay_005', date: '2026-07-10', reference: 'PAY-1015', amount: 2500.00, status: 'Pending', has_receipt: false, description: 'Service payment' },
  { id: 'pay_006', date: '2026-06-24', reference: 'PAY-1008', amount: 1500.00, status: 'Confirmed', has_receipt: true, description: 'Monthly service payment' },
];

const MOCK_PAYMENT_DETAIL = {
  id: 'pay_001',
  date: '2026-08-24',
  reference: 'PAY-1045',
  amount: 1500.00,
  status: 'Confirmed',
  description: 'Monthly service payment',
  payment_method: 'Bank Transfer',
  bank_reference: 'NBP-2026-08-4521',
  has_receipt: true,
  confirmed_at: '2026-08-24T14:22:00Z',
  timeline: [
    { status: 'Submitted', date: '2026-08-24T10:00:00Z', note: 'Payment submitted via bank transfer' },
    { status: 'Processing', date: '2026-08-24T12:15:00Z', note: 'Payment being verified' },
    { status: 'Confirmed', date: '2026-08-24T14:22:00Z', note: 'Payment confirmed and applied to account' },
  ],
};

const MOCK_COMPLAINTS = [
  { id: 'SR-2045', subject: 'Internet connectivity issues', category: 'Technical', status: 'In Progress', priority: 'High', created: '2026-08-20', last_update: '2026-08-23' },
  { id: 'SR-2038', subject: 'Billing discrepancy on August invoice', category: 'Billing', status: 'Under Review', priority: 'Medium', created: '2026-08-15', last_update: '2026-08-22' },
  { id: 'SR-2021', subject: 'Service installation delay', category: 'Service', status: 'Resolved', priority: 'Low', created: '2026-07-30', last_update: '2026-08-10' },
];

const MOCK_COMPLAINT_DETAIL = {
  id: 'SR-2045',
  subject: 'Internet connectivity issues',
  category: 'Technical',
  status: 'In Progress',
  priority: 'High',
  created: '2026-08-20T09:30:00Z',
  description: 'Experiencing intermittent internet connectivity since last week. Connection drops multiple times per day.',
  preferred_contact: 'Email',
  timeline: [
    { status: 'Submitted', date: '2026-08-20T09:30:00Z', note: 'Complaint registered by customer' },
    { status: 'Under Review', date: '2026-08-20T14:00:00Z', note: 'Being reviewed by technical team' },
    { status: 'Assigned', date: '2026-08-21T10:00:00Z', note: 'Assigned to field technician' },
    { status: 'In Progress', date: '2026-08-23T08:00:00Z', note: 'Technician dispatched to customer premises' },
  ],
  messages: [
    { id: 'm1', sender: 'Support Team', text: 'We have received your complaint and assigned it to our technical team.', date: '2026-08-20T14:00:00Z' },
    { id: 'm2', sender: 'You', text: 'Thank you. This has been affecting our business operations.', date: '2026-08-21T08:30:00Z' },
    { id: 'm3', sender: 'Support Team', text: 'A technician has been dispatched and will visit your premises on 23 Aug.', date: '2026-08-22T16:00:00Z' },
  ],
};

const MOCK_DOCUMENTS = [
  { id: 'doc_001', name: 'Invoice - August 2026', category: 'Invoices', date: '2026-08-01', type: 'PDF', size: '245 KB' },
  { id: 'doc_002', name: 'Payment Receipt - PAY-1045', category: 'Receipts', date: '2026-08-24', type: 'PDF', size: '128 KB' },
  { id: 'doc_003', name: 'Statement - Q3 2026', category: 'Statements', date: '2026-07-01', type: 'PDF', size: '512 KB' },
  { id: 'doc_004', name: 'Service Contract 2026', category: 'Contracts', date: '2026-01-15', type: 'PDF', size: '1.2 MB' },
  { id: 'doc_005', name: 'Payment Receipt - PAY-1038', category: 'Receipts', date: '2026-08-18', type: 'PDF', size: '132 KB' },
  { id: 'doc_006', name: 'Invoice - July 2026', category: 'Invoices', date: '2026-07-01', type: 'PDF', size: '238 KB' },
  { id: 'doc_007', name: 'Notice - Rate Adjustment', category: 'Notices', date: '2026-06-15', type: 'PDF', size: '89 KB' },
];

const MOCK_MOMENTUM = {
  balance: 1240,
  earned_this_month: 120,
  total_earned: 1240,
  next_reward_distance: 260,
  qualifying_payments_total: 1240000,
  recent_earnings: [
    { date: '2026-08-24', reference: 'PAY-1045', amount: 1500, momentum_earned: 1 },
    { date: '2026-08-18', reference: 'PAY-1038', amount: 3000, momentum_earned: 3 },
    { date: '2026-08-10', reference: 'PAY-1031', amount: 2000, momentum_earned: 2 },
    { date: '2026-07-24', reference: 'PAY-1022', amount: 1500, momentum_earned: 1 },
    { date: '2026-06-24', reference: 'PAY-1008', amount: 1500, momentum_earned: 1 },
  ],
};

const MOCK_REWARDS = [
  { id: 'rwd_001', name: 'Service Upgrade Voucher', tier: 'Entry', momentum_required: 1000, description: 'Upgrade your service plan for one month at no extra cost', available: true },
  { id: 'rwd_002', name: 'Free Installation', tier: 'Enhanced', momentum_required: 2500, description: 'Free professional installation for an additional service', available: false },
  { id: 'rwd_003', name: 'Premium Support Package', tier: 'Premium', momentum_required: 5000, description: '3 months of priority premium support', available: false },
  { id: 'rwd_004', name: 'Annual Service Credit', tier: 'Signature', momentum_required: 10000, description: 'Credit equivalent to one month of annual service fees', available: false },
];

const MOCK_REDEMPTIONS = [
  { id: 'red_001', reward: 'Service Upgrade Voucher', date: '2026-06-10', momentum_used: 1000, status: 'Redeemed' },
];

const MOCK_NOTIFICATIONS = [
  { id: 'n1', type: 'payment', category: 'Payment', title: 'Payment received', text: 'PAY-1045 for KES 1,500 has been confirmed.', time: '2 hours ago', date: '2026-08-24T14:22:00Z', unread: true },
  { id: 'n2', type: 'complaint', category: 'Complaint', title: 'Complaint updated', text: 'SR-2045 status changed to In Progress.', time: '1 day ago', date: '2026-08-23T08:00:00Z', unread: true },
  { id: 'n3', type: 'document', category: 'Document', title: 'New document available', text: 'Invoice INV-2026-089 has been uploaded.', time: '2 days ago', date: '2026-08-22T10:00:00Z', unread: false },
  { id: 'n4', type: 'momentum', category: 'Momentum', title: 'Momentum earned', text: 'You earned 1 Momentum from PAY-1045.', time: '2 days ago', date: '2026-08-22T14:22:00Z', unread: false },
  { id: 'n5', type: 'payment', category: 'Payment', title: 'Receipt available', text: 'Receipt for PAY-1038 is ready for download.', time: '1 week ago', date: '2026-08-18T14:00:00Z', unread: false },
  { id: 'n6', type: 'security', category: 'Security', title: 'Password changed', text: 'Your portal password was updated successfully.', time: '2 weeks ago', date: '2026-08-10T09:00:00Z', unread: false },
];

const MOCK_PROFILE = {
  customer_name: 'ABC Company',
  account_number: '000124',
  account_status: 'Active',
  email: 'admin@abccompany.com',
  phone: '+254 700 123 456',
  address: '123 Business Park, Nairobi',
  authorized_users: [
    { id: 'u1', first_name: 'John', last_name: 'Doe', email: 'john@abccompany.com', role: 'OWNER', status: 'Active' },
    { id: 'u2', first_name: 'Mary', last_name: 'Smith', email: 'mary@abccompany.com', role: 'ADMIN', status: 'Active' },
    { id: 'u3', first_name: 'Peter', last_name: 'Jones', email: 'peter@abccompany.com', role: 'VIEWER', status: 'Active' },
  ],
};

const MOCK_FAQS = [
  { id: 'faq1', question: 'How do I make a payment?', answer: 'Navigate to the Payments section and click "Make Payment". You can pay via bank transfer or mobile money.' },
  { id: 'faq2', question: 'How is Momentum calculated?', answer: 'You earn 1 Momentum for every KES 1,000 of qualifying confirmed payments. Momentum never expires.' },
  { id: 'faq3', question: 'How do I raise a complaint?', answer: 'Go to Complaints and click "Raise Complaint". Fill in the details and submit. You will receive a reference number.' },
  { id: 'faq4', question: 'How do I download my documents?', answer: 'Go to Documents, find the document you need, and click the download button. Documents are available based on your access permissions.' },
  { id: 'faq5', question: 'How do I add another portal user?', answer: 'Go to Profile > Authorized Users and click "Invite User". You need MANAGE_PORTAL_USERS permission.' },
];

async function mockOrApi(mockFn, apiPath) {
  if (USE_MOCK) return mockFn();
  return get(apiPath);
}

export function fetchDashboard() { return mockOrApi(() => MOCK_DASHBOARD, '/api/portal/dashboard'); }

export function fetchPayments() { return mockOrApi(() => MOCK_PAYMENTS, '/api/portal/payments'); }
export function fetchPaymentDetail(id) { return mockOrApi(() => MOCK_PAYMENT_DETAIL, `/api/portal/payments/${id}`); }

export function fetchComplaints() { return mockOrApi(() => MOCK_COMPLAINTS, '/api/portal/complaints'); }
export function fetchComplaintDetail(id) { return mockOrApi(() => MOCK_COMPLAINT_DETAIL, `/api/portal/complaints/${id}`); }
export async function createComplaint(data) {
  if (USE_MOCK) { await new Promise((r) => setTimeout(r, 800)); return { id: 'SR-2046', ...data, status: 'Submitted' }; }
  return post('/api/portal/complaints', data);
}
export async function replyToComplaint(id, text) {
  if (USE_MOCK) { await new Promise((r) => setTimeout(r, 500)); return { success: true }; }
  return post(`/api/portal/complaints/${id}/reply`, { text });
}

export function fetchDocuments() { return mockOrApi(() => MOCK_DOCUMENTS, '/api/portal/documents'); }

export function fetchMomentum() { return mockOrApi(() => MOCK_MOMENTUM, '/api/portal/momentum'); }

export function fetchRewards() { return mockOrApi(() => MOCK_REWARDS, '/api/portal/rewards'); }
export function fetchRedemptions() { return mockOrApi(() => MOCK_REDEMPTIONS, '/api/portal/rewards/redemptions'); }
export async function redeemReward(id) {
  if (USE_MOCK) { await new Promise((r) => setTimeout(r, 800)); return { success: true }; }
  return post(`/api/portal/rewards/${id}/redeem`);
}

export function fetchNotifications() { return mockOrApi(() => MOCK_NOTIFICATIONS, '/api/portal/notifications'); }
export async function markNotificationRead(id) {
  if (USE_MOCK) return { success: true };
  return put(`/api/portal/notifications/${id}/read`);
}
export async function markAllNotificationsRead() {
  if (USE_MOCK) return { success: true };
  return put('/api/portal/notifications/read-all');
}

export function fetchProfile() { return mockOrApi(() => MOCK_PROFILE, '/api/portal/profile'); }
export async function updateProfile(data) {
  if (USE_MOCK) { await new Promise((r) => setTimeout(r, 600)); return { success: true }; }
  return put('/api/portal/profile', data);
}

export function fetchFaqs() { return mockOrApi(() => MOCK_FAQS, '/api/portal/support/faqs'); }
export async function submitSupportRequest(data) {
  if (USE_MOCK) { await new Promise((r) => setTimeout(r, 800)); return { id: 'SR-3001', ...data }; }
  return post('/api/portal/support/request', data);
}
