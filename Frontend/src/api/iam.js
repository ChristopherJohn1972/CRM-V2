import { get, post, patch, put, del } from './client';

export const listOperators = () => get('/api/iam/operators');
export const getOperator = (operatorId) => get(`/api/iam/operators/${operatorId}`);
export const updateOperator = (operatorId, payload) => patch(`/api/iam/operators/${operatorId}`, payload);

export function createOperator(payload) {
  return post('/api/iam/operators', payload);
}

export const setOperatorRoles = (operatorId, roleCodes) =>
  put(`/api/iam/operators/${operatorId}/roles`, { role_codes: roleCodes });

export const getOperatorDirectPermissions = (operatorId) =>
  get(`/api/iam/operators/${operatorId}/permissions`);
export const setOperatorDirectPermission = (operatorId, { permission_code, effect, reason }) =>
  post(`/api/iam/operators/${operatorId}/permissions`, { permission_code, effect, reason });
export const revokeOperatorDirectPermission = (operatorId, permissionCode) =>
  del(`/api/iam/operators/${operatorId}/permissions/${permissionCode}`);

export const getAccessReview = (operatorId) => get(`/api/iam/operators/${operatorId}/access-review`);

export const listRoles = () => get('/api/iam/roles');
export const getRole = (roleId) => get(`/api/iam/roles/${roleId}`);
export function createRole(payload) {
  return post('/api/iam/roles', payload);
}
export const updateRole = (roleId, payload) => patch(`/api/iam/roles/${roleId}`, payload);

export const getRightsCatalogue = () => get('/api/iam/rights');
export const getScopes = () => get('/api/iam/scopes');

export default {
  listOperators,
  getOperator,
  updateOperator,
  createOperator,
  setOperatorRoles,
  getOperatorDirectPermissions,
  setOperatorDirectPermission,
  revokeOperatorDirectPermission,
  getAccessReview,
  listRoles,
  getRole,
  createRole,
  updateRole,
  getRightsCatalogue,
  getScopes,
};