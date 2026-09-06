/**
 * Helpers for the Operators / Roles / Rights / Access Review screens.
 * These mirror the backend's effective-access model (iam/access_services.py).
 */

export function groupByResource(permissionItems) {
  const byResource = {};
  for (const item of permissionItems) {
    const resource = item.resource || 'other';
    if (!byResource[resource]) byResource[resource] = [];
    byResource[resource].push(item);
  }
  return byResource;
}

export function roleCodeToPreview(roleCodes, rolesById, catalogByCode) {
  const seen = new Set();
  const items = [];
  for (const code of roleCodes) {
    const role = rolesById.get(code);
    if (!role) continue;
    for (const permCode of role.permission_codes || []) {
      if (seen.has(permCode)) continue;
      seen.add(permCode);
      const meta = catalogByCode.get(permCode) || {};
      items.push({
        code: permCode,
        name: meta.name || permCode,
        resource: meta.resource || 'other',
        action: meta.action || '',
        description: meta.description || '',
        effective: 'ALLOW',
        sources: [{ source: 'role', role_code: code, role_name: role.name, effect: 'ALLOW' }],
      });
    }
  }
  return groupByResource(items);
}

export function catalogueByCode(permissions) {
  const map = new Map();
  for (const p of permissions || []) map.set(p.code, p);
  return map;
}

export function operatorDisplayName(op) {
  if (!op) return '—';
  return [op.first_name, op.last_name].filter(Boolean).join(' ') || op.username || `User #${op.user_id}`;
}

export function uniqueCode(baseCode, existingCodes) {
  let candidate = baseCode;
  let n = 2;
  while (existingCodes.includes(candidate)) {
    candidate = `${baseCode}_${n}`;
    n += 1;
  }
  return candidate;
}

export function buildDuplicateRolePayload(role, existingCodes) {
  const code = uniqueCode(`${role.code}_copy`, existingCodes);
  return {
    name: `${role.name} (Copy)`,
    code,
    description: role.description || null,
    is_active: role.is_active,
    is_system_role: false,
    permission_codes: role.permission_codes || [],
    access_policy_codes: role.scope_codes || [],
  };
}
