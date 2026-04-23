const IDENTITY_API = process.env.REACT_APP_IDENTITY_API;
const ACSE_API = process.env.REACT_APP_ACSE_API;

export async function login(uin) {
  const res = await fetch(`${IDENTITY_API}/v1/auth/login?uin=${uin}`);
  if (!res.ok) throw new Error('Login failed');
  const data = await res.json();
  // Store token
  sessionStorage.setItem('access_token', data.access_token);
  return data;
}

export async function getScore() {
  const token = sessionStorage.getItem('access_token');
  // In a real app, we'd decode token to get internal_id, but for now we'll store it after login.
  const internalId = sessionStorage.getItem('internal_id');
  if (!internalId || !token) throw new Error('Not authenticated');
  
  const res = await fetch(`${ACSE_API}/v1/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ internal_id: internalId, consent_token: token })
  });
  if (!res.ok) throw new Error('Failed to fetch score');
  return res.json();
}

export function getInternalId() {
  return sessionStorage.getItem('internal_id');
}