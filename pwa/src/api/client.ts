/**
 * pwa/src/api/client.ts
 * Typed API client for LIFP backend services.
 */

const ACSE_URL     = import.meta.env.VITE_ACSE_URL     ?? "http://localhost:8001";
const IDENTITY_URL = import.meta.env.VITE_IDENTITY_URL ?? "http://localhost:8002";

// ── Auth ──────────────────────────────────────────────────────────────────────
export interface AuthResponse {
  access_token: string;
  internal_id: string;
  token_type: string;
}

export async function login(
  uin: string,
  userType: "msme" | "individual",
): Promise<AuthResponse> {
  const res = await fetch(`${IDENTITY_URL}/v1/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ uin, user_type: userType }),
  });
  if (!res.ok) throw new Error(`Login failed: ${res.status}`);
  return res.json();
}

export async function grantConsent(
  _internalId: string,
  purpose: string,
  token: string,
  validDays = 365,
): Promise<void> {
  const res = await fetch(`${IDENTITY_URL}/v1/consent/grant`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ purpose, valid_days: validDays }),
  });
  if (!res.ok) throw new Error(`Consent grant failed: ${res.status}`);
}

// ── Scoring ───────────────────────────────────────────────────────────────────
export interface ScoreFactor {
  feature: string;
  shap_value: number;
}

export interface ScoreResponse {
  internal_id: string;
  score: number;
  tier: "A" | "B" | "C" | "D" | "E";
  prob_default: number;
  model_version: string;
  factors: ScoreFactor[];
}

export async function fetchScore(
  internalId: string,
  consentToken: string,
): Promise<ScoreResponse> {
  const res = await fetch(`${ACSE_URL}/v1/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      internal_id: internalId,
      consent_token: consentToken,
    }),
  });
  if (!res.ok) throw new Error(`Scoring failed: ${res.status}`);
  return res.json();
}
