import { get, post } from './client';

export function getMomentumBalance(customerId) {
  return get(`/api/momentum/balance/${customerId}/`);
}

export function getMomentumLedger(customerId, params = {}) {
  const q = new URLSearchParams();
  if (params.page) q.set('page', params.page);
  if (params.page_size) q.set('page_size', params.page_size);
  return get(`/api/momentum/ledger/${customerId}/?${q.toString()}`);
}

export function earnMomentum(payload) {
  return post('/api/momentum/earn/', payload);
}

export function adjustMomentum(payload) {
  return post('/api/momentum/adjust/', payload);
}

export function listMomentumRules() {
  return get('/api/momentum/rules/');
}

export function createMomentumRule(payload) {
  return post('/api/momentum/rules/', payload);
}

export function updateMomentumRule(id, payload) {
  return post(`/api/momentum/rules/${id}/`, payload);
}
