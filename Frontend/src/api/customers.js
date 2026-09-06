import { get, post, patch, del } from './client';

function qs(params = {}) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, value);
  }
  const s = search.toString();
  return s ? `?${s}` : '';
}

export const listCustomers = (params = {}) => get(`/api/clients${qs(params)}`);

export const getCustomer = (customerId) => get(`/api/clients/${customerId}`);

export function createCustomer(payload) {
  return post('/api/clients', sanitizeCustomerPayload(payload));
}

export function updateCustomer(customerId, payload) {
  return patch(`/api/clients/${customerId}`, sanitizeCustomerPayload({ ...payload, version: payload.version }));
}

export function deleteCustomer(customerId) {
  return del(`/api/clients/${customerId}`);
}

export const changeStatus = (customerId, status, reason) =>
  post(`/api/clients/${customerId}/status`, { status, reason });

export const closeCustomer = (customerId, reason = '') =>
  post(`/api/clients/${customerId}/close`, { reason });

export const getContacts = (customerId) => get(`/api/clients/${customerId}/contacts`);
export const createContact = (customerId, payload) => post(`/api/clients/${customerId}/contacts`, payload);
export const updateContact = (customerId, contactId, payload) =>
  patch(`/api/clients/${customerId}/contacts/${contactId}`, payload);
export const deactivateContact = (customerId, contactId) => del(`/api/clients/${customerId}/contacts/${contactId}`);

export const getRelationships = (customerId) => get(`/api/clients/${customerId}/relationships`);
export const createRelationship = (customerId, payload) =>
  post(`/api/clients/${customerId}/relationships`, payload);
export const removeRelationship = (customerId, relationshipId) =>
  del(`/api/clients/${customerId}/relationships/${relationshipId}`);

export const getAddresses = (customerId) => get(`/api/clients/${customerId}/addresses`);
export const createAddress = (customerId, payload) => post(`/api/clients/${customerId}/addresses`, payload);
export const updateAddress = (customerId, addressId, payload) =>
  patch(`/api/clients/${customerId}/addresses/${addressId}`, payload);
export const deleteAddress = (customerId, addressId) => del(`/api/clients/${customerId}/addresses/${addressId}`);

export const getActivities = (customerId, params = {}) => get(`/api/clients/${customerId}/activities${qs(params)}`);
export const createActivity = (customerId, payload) => post(`/api/clients/${customerId}/activities`, payload);
export const updateActivity = (customerId, activityId, payload) =>
  patch(`/api/clients/${customerId}/activities/${activityId}`, payload);
export const completeActivity = (customerId, activityId) =>
  post(`/api/clients/${customerId}/activities/${activityId}/complete`);

export const getNotes = (customerId) => get(`/api/clients/${customerId}/notes`);
export const createNote = (customerId, payload) => post(`/api/clients/${customerId}/notes`, payload);

export const getTimeline = (customerId, params = {}) => get(`/api/clients/${customerId}/timeline${qs(params)}`);

export const getSms = (customerId, params = {}) => get(`/api/clients/${customerId}/sms${qs(params)}`);
export const sendSms = (customerId, payload) => post(`/api/clients/${customerId}/sms`, payload);
export const getEmails = (customerId, params = {}) => get(`/api/clients/${customerId}/email${qs(params)}`);
export const sendEmail = (customerId, payload) => post(`/api/clients/${customerId}/email`, payload);
export const getCalls = (customerId, params = {}) => get(`/api/clients/${customerId}/calls${qs(params)}`);
export const getCommunications = (customerId, params = {}) =>
  get(`/api/clients/${customerId}/communications${qs(params)}`);

export const getAccountingSummary = (customerId) => get(`/api/clients/${customerId}/accounting-summary`);
export const getAccountingTransactions = (customerId, params = {}) =>
  get(`/api/clients/${customerId}/accounting-transactions${qs(params)}`);

export const getCustomer360 = (customerId) => get(`/api/clients/${customerId}/360`);

export const getPortalAccess = (customerId) => get(`/api/clients/${customerId}/portal-access`);
export const resetPortalPassword = (customerId, payload = {}) =>
  post(`/api/clients/${customerId}/portal-access`, { action: 'reset', ...payload });

export const getNotifications = (customerId, params = {}) =>
  get(`/api/clients/${customerId}/notifications${qs(params)}`);

export function sanitizeCustomerPayload(payload) {
  const p = { ...payload };
  for (const key of ['customer_id', 'account_number', 'customer_number', 'status', 'status_reason', 'created_at', 'updated_at', '_360_url']) {
    delete p[key];
  }
  return p;
}

export default {
  listCustomers,
  getCustomer,
  createCustomer,
  updateCustomer,
  deleteCustomer,
  changeStatus,
  closeCustomer,
  getContacts,
  createContact,
  updateContact,
  deactivateContact,
  getRelationships,
  createRelationship,
  removeRelationship,
  getAddresses,
  createAddress,
  updateAddress,
  deleteAddress,
  getActivities,
  createActivity,
  updateActivity,
  completeActivity,
  getNotes,
  createNote,
  getTimeline,
  getSms,
  sendSms,
  getEmails,
  sendEmail,
  getCalls,
  getCommunications,
  getAccountingSummary,
  getAccountingTransactions,
  getCustomer360,
  getPortalAccess,
  resetPortalPassword,
  getNotifications,
};