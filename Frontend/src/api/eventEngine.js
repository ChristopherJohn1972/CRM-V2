import { get, post } from './client';

export function listEventOutbox(params = {}) {
  const q = new URLSearchParams();
  if (params.status) q.set('status', params.status);
  if (params.page) q.set('page', params.page);
  return get(`/api/event-outbox/?${q.toString()}`);
}

export function processEventOutbox(batchSize = 50) {
  return post('/api/event-outbox/process/', { batch_size: batchSize });
}

export function retryFailedEvent(eventId) {
  return post(`/api/event-outbox/${eventId}/retry/`);
}
