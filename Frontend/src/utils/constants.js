export const CUSTOMER_TYPES = {
  INDIVIDUAL: 'Individual',
  BUSINESS: 'Business',
  ORGANISATION: 'Organisation',
};

export const CUSTOMER_STATUS = {
  PROSPECT: 'Prospect',
  ONBOARDING: 'Onboarding',
  ACTIVE: 'Active',
  INACTIVE: 'Inactive',
  SUSPENDED: 'Suspended',
  CLOSED: 'Closed',
  ARCHIVED: 'Archived',
};

export const ACCOUNT_NUMBER_STATUS = {
  ACTIVE: 'Active',
  RESERVED: 'Reserved',
  RETIRED: 'Retired',
};

export const STATUS_VARIANT = {
  PROSPECT: 'neutral',
  ONBOARDING: 'info',
  ACTIVE: 'success',
  INACTIVE: 'muted',
  SUSPENDED: 'warning',
  CLOSED: 'danger',
  ARCHIVED: 'muted',
};

export const STATUS_COLORS = {
  PROSPECT: { bg: '#EFF6FF', text: '#2563EB', dot: '#2563EB' },
  ONBOARDING: { bg: '#F5F3FF', text: '#7C3AED', dot: '#7C3AED' },
  ACTIVE: { bg: '#F0FDF4', text: '#16A34A', dot: '#16A34A' },
  INACTIVE: { bg: '#F8FAFC', text: '#64748B', dot: '#64748B' },
  SUSPENDED: { bg: '#FFFBEB', text: '#D97706', dot: '#F59E0B' },
  CLOSED: { bg: '#FEF2F2', text: '#DC2626', dot: '#DC2626' },
  ARCHIVED: { bg: '#F1F5F9', text: '#475569', dot: '#475569' },
};

export const ADDRESS_TYPES = {
  BILLING: 'Billing',
  SHIPPING: 'Shipping',
  OFFICE: 'Office',
  HOME: 'Home',
  OTHER: 'Other',
};

export const ACCESS_CLASSIFICATIONS = {
  PUBLIC: 'Public',
  INTERNAL: 'Internal',
  RESTRICTED: 'Restricted',
  CONFIDENTIAL: 'Confidential',
};

export const NOTE_VISIBILITY = {
  PRIVATE: 'Private',
  TEAM: 'Team',
  PUBLIC: 'Public',
};

export const ACTIVITY_STATUS = {
  OPEN: 'Open',
  IN_PROGRESS: 'In progress',
  COMPLETED: 'Completed',
  CANCELLED: 'Cancelled',
};

export const ACTIVITY_PRIORITY = {
  LOW: 'Low',
  MEDIUM: 'Medium',
  HIGH: 'High',
  URGENT: 'Urgent',
};

export const COMMUNICATION_STATUS = {
  QUEUED: 'Queued',
  SENT: 'Sent',
  DELIVERED: 'Delivered',
  FAILED: 'Failed',
  REJECTED: 'Rejected',
  UNKNOWN: 'Unknown',
  OPEN: 'Open',
};

export const PERMISSIONS = {
  CUSTOMER_READ: 'clients.customer.read',
  CUSTOMER_CREATE: 'clients.customer.create',
  CUSTOMER_UPDATE: 'clients.customer.update',
  CUSTOMER_DELETE: 'clients.customer.delete',
  CUSTOMER_STATUS: 'clients.customer.status.change',
  CUSTOMER_SENSITIVE: 'clients.customer.sensitive.read',
  CONTACT_CREATE: 'clients.contact.create',
  CONTACT_UPDATE: 'clients.contact.update',
  CONTACT_DELETE: 'clients.contact.delete',
  RELATIONSHIP_CREATE: 'clients.relationship.create',
  RELATIONSHIP_DELETE: 'clients.relationship.delete',
  ADDRESS_WRITE: 'clients.address.write',
  ACTIVITY_CREATE: 'activities.activity.create',
  ACTIVITY_UPDATE: 'activities.activity.update',
  NOTE_CREATE: 'activities.note.create',
  SMS_SEND: 'communications.sms.send',
  SMS_READ: 'communications.sms.read',
  EMAIL_SEND: 'communications.email.send',
  EMAIL_READ: 'communications.email.read',
  DOCUMENT_UPLOAD: 'documents.document.upload',
  DOCUMENT_DOWNLOAD: 'documents.document.download',
  ACCOUNTING_SUMMARY: 'accounting.summary.read',
  ACCOUNTING_TRANSACTIONS: 'accounting.transactions.read',
  PORTAL_ADMIN: 'portal.user.manage',
  PORTAL_CREDENTIAL_ACCESS: 'portal.credential.read',
  PORTAL_CREDENTIAL_RESET: 'portal.credential.reset',
  AUDIT_READ: 'audit.read',
  IAM_USER_MANAGE: 'iam.user.manage',
  IAM_ROLE_MANAGE: 'iam.role.manage',
  IAM_PERMISSION_AUDIT: 'iam.permission.audit',
  CAMPAIGN_READ: 'campaign.view',
  CAMPAIGN_CREATE: 'campaign.create',
  CAMPAIGN_UPDATE: 'campaign.edit',
  CAMPAIGN_DELETE: 'campaign.delete',
  SALES_ORDER_READ: 'sales_order.sales_order.read',
  SALES_ORDER_CREATE: 'sales_order.sales_order.create',
  SALES_ORDER_UPDATE: 'sales_order.sales_order.update',
  SALES_ORDER_DELETE: 'sales_order.sales_order.delete',
  SALES_ORDER_WORKFLOW: 'sales_order.sales_order.workflow',
  SALES_ORDER_CALCULATE: 'sales_order.sales_order.calculate',
};

export const SCOPE_HIERARCHY = ['NONE', 'OWN', 'ASSIGNED', 'TEAM', 'DEPARTMENT', 'ALL'];

export const SCOPE_MEANINGS = {
  NONE: 'No records',
  OWN: 'Records owned by the operator',
  ASSIGNED: 'Records assigned to the operator',
  TEAM: 'Records belonging to the operator’s team',
  DEPARTMENT: 'Records belonging to the operator’s department',
  ALL: 'All records permitted by the system',
};

export const SCOPE_TO_POLICY = {
  OWN: 'SCOPE_OWN',
  ASSIGNED: 'SCOPE_ASSIGNED',
  TEAM: 'SCOPE_TEAM',
  DEPARTMENT: 'SCOPE_DEPARTMENT',
  ALL: 'GLOBAL_ALL',
};

export const OPERATOR_STATUS = {
  PENDING: 'Pending',
  ACTIVE: 'Active',
  SUSPENDED: 'Suspended',
  DEACTIVATED: 'Deactivated',
};

export const OPERATOR_STATUS_VARIANT = {
  PENDING: 'warning',
  ACTIVE: 'success',
  SUSPENDED: 'warning',
  DEACTIVATED: 'muted',
};

// ---------------------------------------------------------------------------
// Quote Status
// ---------------------------------------------------------------------------

export const QUOTE_STATUS = {
  DRAFT: 'DRAFT',
  PENDING_APPROVAL: 'PENDING_APPROVAL',
  APPROVED: 'APPROVED',
  SENT: 'SENT',
  VIEWED: 'VIEWED',
  ACCEPTED: 'ACCEPTED',
  REJECTED: 'REJECTED',
  EXPIRED: 'EXPIRED',
  CANCELLED: 'CANCELLED',
};

export const QUOTE_STATUS_LABELS = {
  DRAFT: 'Draft',
  PENDING_APPROVAL: 'Pending Approval',
  APPROVED: 'Approved',
  SENT: 'Sent',
  VIEWED: 'Viewed',
  ACCEPTED: 'Accepted',
  REJECTED: 'Rejected',
  EXPIRED: 'Expired',
  CANCELLED: 'Cancelled',
};

export const QUOTE_STATUS_VARIANT = {
  DRAFT: 'muted',
  PENDING_APPROVAL: 'warning',
  APPROVED: 'info',
  SENT: 'info',
  VIEWED: 'info',
  ACCEPTED: 'success',
  REJECTED: 'danger',
  EXPIRED: 'muted',
  CANCELLED: 'muted',
};

// ---------------------------------------------------------------------------
// Quote Type
// ---------------------------------------------------------------------------

export const QUOTE_TYPE = {
  PRODUCT: 'PRODUCT',
  SERVICE: 'SERVICE',
  PROJECT: 'PROJECT',
};

export const QUOTE_TYPE_LABELS = {
  PRODUCT: 'Product',
  SERVICE: 'Service',
  PROJECT: 'Project',
};

// ---------------------------------------------------------------------------
// Template Type
// ---------------------------------------------------------------------------

export const TEMPLATE_TYPE = {
  DEFAULT: 'DEFAULT',
  PRODUCT: 'PRODUCT',
  SERVICE: 'SERVICE',
  PROJECT: 'PROJECT',
};

export const TEMPLATE_TYPE_LABELS = {
  DEFAULT: 'Default',
  PRODUCT: 'Product',
  SERVICE: 'Service',
  PROJECT: 'Project',
};

// ---------------------------------------------------------------------------
// Quote Permissions
// ---------------------------------------------------------------------------

export const QUOTE_PERMISSIONS = {
  READ: 'quotes.quote.read',
  CREATE: 'quotes.quote.create',
  UPDATE: 'quotes.quote.update',
  DELETE: 'quotes.quote.delete',
  DUPLICATE: 'quotes.quote.duplicate',
  CALCULATE: 'quotes.quote.calculate',
  SUBMIT_APPROVAL: 'quotes.quote.submit_approval',
  APPROVE: 'quotes.quote.approve',
  REJECT: 'quotes.quote.reject',
  SEND: 'quotes.quote.send',
  PREVIEW: 'quotes.quote.preview',
  DOWNLOAD_PDF: 'quotes.quote.download_pdf',
  VIEW_AUDIT: 'quotes.quote.view_audit',
  CONVERT: 'quotes.quote.convert_to_order',
  MANAGE_TEMPLATES: 'quotes.quote.manage_templates',
  MANAGE_TAX: 'quotes.quote.manage_tax_rules',
  MANAGE_PAYMENT_TERMS: 'quotes.quote.manage_payment_terms',
};

// ---------------------------------------------------------------------------
// Campaign Status
// ---------------------------------------------------------------------------

export const CAMPAIGN_STATUS_COLORS = {
  DRAFT: { bg: '#F8FAFC', text: '#64748B', dot: '#64748B' },
  PRODUCT_SELECTED: { bg: '#F5F3FF', text: '#7C3AED', dot: '#7C3AED' },
  CONFIGURING: { bg: '#EFF6FF', text: '#2563EB', dot: '#2563EB' },
  CREATIVE_GENERATING: { bg: '#FFF7ED', text: '#EA580C', dot: '#EA580C' },
  CREATIVE_READY: { bg: '#F0FDF4', text: '#16A34A', dot: '#16A34A' },
  READY_FOR_REVIEW: { bg: '#F5F3FF', text: '#7C3AED', dot: '#7C3AED' },
  CHANGES_REQUIRED: { bg: '#FFFBEB', text: '#D97706', dot: '#F59E0B' },
  APPROVED: { bg: '#F0FDF4', text: '#16A34A', dot: '#16A34A' },
  LAUNCHING: { bg: '#EFF6FF', text: '#2563EB', dot: '#2563EB' },
  ACTIVE: { bg: '#F0FDF4', text: '#16A34A', dot: '#16A34A' },
  PAUSED: { bg: '#FFFBEB', text: '#D97706', dot: '#F59E0B' },
  COMPLETED: { bg: '#F1F5F9', text: '#475569', dot: '#475569' },
  CANCELLED: { bg: '#FEF2F2', text: '#DC2626', dot: '#DC2626' },
  ABANDONED: { bg: '#FEF2F2', text: '#DC2626', dot: '#DC2626' },
  GENERATION_FAILED: { bg: '#FEF2F2', text: '#DC2626', dot: '#DC2626' },
};

export const CAMPAIGN_STATUS_LABELS = {
  DRAFT: 'Draft',
  PRODUCT_SELECTED: 'Product Selected',
  CONFIGURING: 'Configuring',
  CREATIVE_GENERATING: 'Generating Creative',
  CREATIVE_READY: 'Creative Ready',
  READY_FOR_REVIEW: 'Ready for Review',
  CHANGES_REQUIRED: 'Changes Required',
  APPROVED: 'Approved',
  LAUNCHING: 'Launching',
  ACTIVE: 'Active',
  PAUSED: 'Paused',
  COMPLETED: 'Completed',
  CANCELLED: 'Cancelled',
  ABANDONED: 'Abandoned',
  GENERATION_FAILED: 'Generation Failed',
};

export const CAMPAIGN_TYPE_LABELS = {
  PROMOTIONAL: 'Promotional',
  SEASONAL: 'Seasonal',
  PRODUCT_LAUNCH: 'Product Launch',
  REFERRAL_BOOST: 'Referral Boost',
  LOYALTY: 'Loyalty',
  CUSTOM: 'Custom',
};

export const CAMPAIGN_OBJECTIVE_LABELS = {
  AWARENESS: 'Awareness',
  CONVERSION: 'Conversion',
  LEAD_GENERATION: 'Lead Generation',
  ENGAGEMENT: 'Engagement',
  RETENTION: 'Retention',
  CUSTOM: 'Custom',
};