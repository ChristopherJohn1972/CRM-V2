export const PERMISSIONS = {
  VIEW_ACCOUNT: 'VIEW_ACCOUNT',
  VIEW_PAYMENTS: 'VIEW_PAYMENTS',
  VIEW_RECEIPTS: 'VIEW_RECEIPTS',
  RAISE_COMPLAINT: 'RAISE_COMPLAINT',
  RESPOND_TO_COMPLAINT: 'RESPOND_TO_COMPLAINT',
  VIEW_DOCUMENTS: 'VIEW_DOCUMENTS',
  VIEW_MOMENTUM: 'VIEW_MOMENTUM',
  REDEEM_REWARD: 'REDEEM_REWARD',
  INVITE_PORTAL_USER: 'INVITE_PORTAL_USER',
  MANAGE_PORTAL_USERS: 'MANAGE_PORTAL_USERS',
  CHANGE_PASSWORD: 'CHANGE_PASSWORD',
};

export const ROLES = {
  OWNER: 'OWNER',
  ADMIN: 'ADMIN',
  FINANCE: 'FINANCE',
  CONTACT: 'CONTACT',
  VIEWER: 'VIEWER',
};

export const ROLE_LABELS = {
  OWNER: 'Owner',
  ADMIN: 'Administrator',
  FINANCE: 'Finance',
  CONTACT: 'Contact',
  VIEWER: 'Viewer',
};

export const NOTIFICATION_TYPES = {
  PAYMENT: 'payment',
  COMPLAINT: 'complaint',
  DOCUMENT: 'document',
  ACCOUNT: 'account',
  MOMENTUM: 'momentum',
  SECURITY: 'security',
};

export const COMPLAINT_STATUSES = [
  'Submitted',
  'Under Review',
  'Assigned',
  'In Progress',
  'Resolved',
  'Closed',
];

export const COMPLAINT_CATEGORIES = [
  'Technical',
  'Billing',
  'Service',
  'Account',
  'Other',
];

export const DOCUMENT_CATEGORIES = [
  'Invoices',
  'Receipts',
  'Statements',
  'Contracts',
  'Notices',
  'Other',
];
