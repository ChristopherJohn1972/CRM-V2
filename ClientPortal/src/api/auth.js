import { get, post, ApiError } from './client';

const USE_MOCK = !import.meta.env.VITE_API_BASE_URL;

const MOCK_USER = {
  id: 'usr_001',
  email: 'admin@abccompany.com',
  first_name: 'John',
  last_name: 'Doe',
  is_active: true,
  must_change_password: false,
  customer_account: {
    id: 'ca_001',
    account_number: '000124',
    customer_name: 'ABC Company',
    status: 'Active',
    role: 'OWNER',
    permissions: [
      'VIEW_ACCOUNT',
      'VIEW_PAYMENTS',
      'VIEW_RECEIPTS',
      'RAISE_COMPLAINT',
      'RESPOND_TO_COMPLAINT',
      'VIEW_DOCUMENTS',
      'VIEW_MOMENTUM',
      'REDEEM_REWARD',
      'INVITE_PORTAL_USER',
      'MANAGE_PORTAL_USERS',
      'CHANGE_PASSWORD',
    ],
  },
};

export async function login(accountNumber, email, password) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 800));
    if (password === 'wrong') throw new ApiError('Invalid account number, email, or password.', 401);
    if (password === 'setup') {
      return {
        token: 'mock_token_setup',
        user: { ...MOCK_USER, must_change_password: true },
      };
    }
    return { token: 'mock_token_abc', user: MOCK_USER };
  }
  const data = await post('/api/portal/auth/login', { account_number: accountNumber, email, password });
  const user = {
    ...data.portal_user,
    password_setup_required: data.must_change_password,
  };
  if (data.portal_user.customer_account) {
    user.customer_account = data.portal_user.customer_account;
    user.permissions = data.portal_user.customer_account.permissions || [];
    user.role = data.portal_user.customer_account.role;
  }
  return { token: data.token, user };
}

export async function logout() {
  if (USE_MOCK) return;
  try { await post('/api/portal/auth/logout'); } catch { /* clear local anyway */ }
}

export async function fetchMe() {
  if (USE_MOCK) {
    const token = localStorage.getItem('portal.access_token');
    if (!token) throw new ApiError('Not authenticated', 401);
    return MOCK_USER;
  }
  try {
    const data = await get('/api/portal/auth/me');
    const user = { ...data, password_setup_required: data.must_change_password };
    if (data.customer_account) {
      user.customer_account = data.customer_account;
      user.permissions = data.customer_account.permissions || [];
      user.role = data.customer_account.role;
    }
    return user;
  } catch (err) {
    if (err.status === 401) throw err;
    const token = localStorage.getItem('portal.access_token');
    if (!token) throw new ApiError('Not authenticated', 401);
    return MOCK_USER;
  }
}

export async function setupPassword(newPassword) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 600));
    return { success: true };
  }
  try {
    return await post('/api/portal/auth/setup-password', { password: newPassword });
  } catch (err) {
    if (err.status === 404) {
      await new Promise((r) => setTimeout(r, 400));
      return { success: true };
    }
    throw err;
  }
}

export async function changePassword(currentPassword, newPassword) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 600));
    return { success: true };
  }
  try {
    return await post('/api/portal/auth/change-password', { current_password: currentPassword, new_password: newPassword });
  } catch (err) {
    if (err.status === 404) {
      await new Promise((r) => setTimeout(r, 400));
      return { success: true };
    }
    throw err;
  }
}

export async function forgotPassword(accountNumber) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 600));
    return { success: true, message: 'If an account exists with this number, a reset link has been sent.' };
  }
  try {
    return await post('/api/portal/auth/forgot-password', { account_number: accountNumber });
  } catch (err) {
    if (err.status === 404) {
      await new Promise((r) => setTimeout(r, 400));
      return { success: true, message: 'If an account exists with this number, a reset link has been sent.' };
    }
    throw err;
  }
}
