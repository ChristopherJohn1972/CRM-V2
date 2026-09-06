import { get, post, patch, del } from './client';

export function listLeads(params = {}) {
  const q = new URLSearchParams();
  if (params.search) q.set('search', params.search);
  if (params.status) q.set('status', params.status);
  if (params.assigned_to) q.set('assigned_to', params.assigned_to);
  if (params.page) q.set('page', params.page);
  if (params.page_size) q.set('page_size', params.page_size);
  return get(`/api/leads/?${q.toString()}`);
}

export function getLead(id) {
  return get(`/api/leads/${id}/`);
}

export function createLead(payload) {
  return post('/api/leads/', payload);
}

export function updateLead(id, payload) {
  return patch(`/api/leads/${id}/`, payload);
}

export function deleteLead(id) {
  return del(`/api/leads/${id}/`);
}

export function transitionLead(id, payload) {
  return post(`/api/leads/${id}/transition/`, payload);
}

export function qualifyLead(id, payload) {
  return post(`/api/leads/${id}/qualify/`, payload);
}

export function listLeadFollowUps(leadId) {
  return get(`/api/leads/${leadId}/follow-ups/`);
}

export function createLeadFollowUp(leadId, payload) {
  return post(`/api/leads/${leadId}/follow-ups/`, payload);
}

export function completeLeadFollowUp(leadId, followUpId, payload) {
  return patch(`/api/leads/${leadId}/follow-ups/${followUpId}/complete/`, payload);
}

export function recordLeadConsent(leadId, payload) {
  return post(`/api/leads/${leadId}/consent/`, payload);
}
