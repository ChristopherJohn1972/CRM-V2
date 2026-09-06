import { get, post } from './client';

export function listReferralCodes(params = {}) {
  const q = new URLSearchParams();
  if (params.customer_id) q.set('customer_id', params.customer_id);
  if (params.status) q.set('status', params.status);
  if (params.page) q.set('page', params.page);
  return get(`/api/referrals/codes/?${q.toString()}`);
}

export function getReferralCode(id) {
  return get(`/api/referrals/codes/${id}/`);
}

export function createReferralCode(payload) {
  return post('/api/referrals/codes/', payload);
}

export function listReferralEvents(codeId) {
  return get(`/api/referrals/codes/${codeId}/events/`);
}

export function trackReferral(code) {
  return get(`/api/referrals/track/${code}/`);
}

export function listReferralTouchpoints(params = {}) {
  const q = new URLSearchParams();
  if (params.customer_id) q.set('customer_id', params.customer_id);
  if (params.campaign_id) q.set('campaign_id', params.campaign_id);
  if (params.page) q.set('page', params.page);
  return get(`/api/attribution/touchpoints/?${q.toString()}`);
}

export function recordTouchpoint(payload) {
  return post('/api/attribution/touchpoints/record/', payload);
}

export function computeAttribution(payload) {
  return post('/api/attribution/compute/', payload);
}

export function getRevenueByCampaign() {
  return get('/api/attribution/revenue-by-campaign/');
}
