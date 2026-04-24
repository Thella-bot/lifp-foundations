const IDENTITY_API = process.env.REACT_APP_IDENTITY_API || 'http://localhost:8002';
const ACSE_API = process.env.REACT_APP_ACSE_API || 'http://localhost:8001';

async function parseApiError(res, fallbackMessage) {
  try {
    const body = await res.json();
    if (body?.detail) return body.detail;
  } catch (e) {
    // Ignore parse errors and fall back to default message.
  }
  return fallbackMessage;
}

export async function login(uin, userType) {
  if (!uin || !uin.trim()) throw new Error('Please enter your National ID');

  const res = await fetch(`${IDENTITY_API}/v1/auth/login?uin=${encodeURIComponent(uin)}`);
  if (!res.ok) throw new Error(await parseApiError(res, 'Login failed'));
  const data = await res.json();
  sessionStorage.setItem('access_token', data.access_token);
  sessionStorage.setItem('internal_id', data.internal_id);
  sessionStorage.setItem('user_type', userType);   // "individual" or "business"
  return data;
}

export async function getScore() {
  const token = sessionStorage.getItem('access_token');
  const internalId = sessionStorage.getItem('internal_id');
  if (!token || !internalId) throw new Error('Not authenticated');
  const res = await fetch(`${ACSE_API}/v1/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ internal_id: internalId, consent_token: token }),
  });
  if (!res.ok) throw new Error(await parseApiError(res, 'Failed to fetch score'));
  return res.json();
}

export function getUserType() {
  return sessionStorage.getItem('user_type') || 'individual';
}
