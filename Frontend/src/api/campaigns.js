import { get, post, patch, del } from './client';

export function listCampaigns(params = {}) {
  const q = new URLSearchParams();
  if (params.search) q.set('search', params.search);
  if (params.status) q.set('status', params.status);
  if (params.campaign_type) q.set('campaign_type', params.campaign_type);
  if (params.page) q.set('page', params.page);
  if (params.page_size) q.set('page_size', params.page_size);
  return get(`/api/campaigns/?${q.toString()}`);
}

export function getCampaign(id) {
  return get(`/api/campaigns/${id}/`);
}

export function createCampaign(payload) {
  return post('/api/campaigns/', payload);
}

export function updateCampaign(id, payload) {
  return patch(`/api/campaigns/${id}/`, payload);
}

export function deleteCampaign(id) {
  return del(`/api/campaigns/${id}/`);
}

export function transitionCampaign(id, payload) {
  return post(`/api/campaigns/${id}/transition/`, payload);
}

export function listCampaignCodes(campaignId) {
  return get(`/api/campaigns/${campaignId}/codes/`);
}

export function createCampaignCode(campaignId, payload) {
  return post(`/api/campaigns/${campaignId}/codes/`, payload);
}

export function listCampaignSources(campaignId) {
  return get(`/api/campaigns/${campaignId}/sources/`);
}

export function createCampaignSource(campaignId, payload) {
  return post(`/api/campaigns/${campaignId}/sources/`, payload);
}

export function createCampaignSchedule(campaignId, payload) {
  return post(`/api/campaigns/${campaignId}/schedule/`, payload);
}

export function generateBillboard(campaignId, payload) {
  return post(`/api/campaigns/${campaignId}/billboard/`, payload);
}

export function listCampaignProducts(campaignId) {
  return get(`/api/campaigns/${campaignId}/products/`);
}

export function getCampaignReadiness(campaignId) {
  return get(`/api/campaigns/${campaignId}/readiness/`);
}

export function launchCampaign(campaignId, payload) {
  return post(`/api/campaigns/${campaignId}/launch/`, payload);
}

export function getCampaignProgress(campaignId) {
  return get(`/api/campaigns/${campaignId}/progress/`);
}

export function addCampaignProducts(campaignId, payload) {
  return post(`/api/campaigns/${campaignId}/products/`, payload);
}

export function updateCampaignAudience(campaignId, payload) {
  return post(`/api/campaigns/${campaignId}/audience/`, payload);
}

export function updateCampaignOffer(campaignId, payload) {
  return post(`/api/campaigns/${campaignId}/offer/`, payload);
}

export function addCampaignChannel(campaignId, payload) {
  return post(`/api/campaigns/${campaignId}/channels/`, payload);
}

export function updateCampaignBudget(campaignId, payload) {
  return post(`/api/campaigns/${campaignId}/budget/`, payload);
}

export function getCampaignDashboardKPIs() {
  return get('/api/campaigns/dashboard/kpis/');
}

export function uploadProductImage(file) {
  const formData = new FormData();
  formData.append('file', file);
  return post('/api/campaigns/upload-image/', formData);
}
