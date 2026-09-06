import { get, post } from './client';

export async function login(username, password) {
  const data = await post('/api/auth/login', { username, password });
  return {
    token: data.token,
    expiresIn: data.expires_in,
    user: data.user,
  };
}

export async function register({ username, email, firstName, lastName, password, confirmPassword }) {
  const data = await post('/api/auth/register', {
    username,
    email,
    first_name: firstName,
    last_name: lastName,
    password,
    confirm_password: confirmPassword,
  });
  return data;
}

export async function logout() {
  try {
    await post('/api/auth/logout');
  } catch {
    // Even if the token is already invalid we clear the local session.
  }
}

export async function fetchMe() {
  const data = await get('/api/auth/me');
  return data;
}

export async function forgotPassword(username) {
  const data = await post('/api/auth/forgot-password', { username });
  return data;
}

export async function resetPassword(token, newPassword, confirmPassword) {
  const data = await post('/api/auth/reset-password', {
    token,
    new_password: newPassword,
    confirm_password: confirmPassword,
  });
  return data;
}