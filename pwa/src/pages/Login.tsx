/**
 * pwa/src/pages/Login.tsx
 * Entry screen — user selects their track (MSME or Individual),
 * enters their national ID, and authenticates via the identity service.
 * On success, access_token and internal_id are saved to sessionStorage
 * and consent is granted for credit_scoring.
 */
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, grantConsent } from "../api/client";

type UserType = "msme" | "individual";

const TRACK_LABELS: Record<UserType, { title: string; subtitle: string; color: string }> = {
  msme: {
    title: "Business",
    subtitle: "Track finances & access business credit",
    color: "#1F3864",
  },
  individual: {
    title: "Personal",
    subtitle: "Manage personal finances & consumer credit",
    color: "#2E75B6",
  },
};

export default function Login() {
  const navigate = useNavigate();
  const [userType, setUserType]   = useState<UserType>("individual");
  const [uin, setUin]             = useState("");
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!uin.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const auth = await login(uin.trim(), userType);
      sessionStorage.setItem("access_token",  auth.access_token);
      sessionStorage.setItem("internal_id",   auth.internal_id);
      sessionStorage.setItem("user_type",     userType);
      // Grant credit scoring consent immediately after login
      await grantConsent(auth.internal_id, "credit_scoring", auth.access_token);
      navigate("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.brand}>LIFP</h1>
        <p style={styles.tagline}>Lesotho Inclusive Finance Platform</p>
      </div>

      {/* Track selector */}
      <div style={styles.trackRow}>
        {(["individual", "msme"] as UserType[]).map((t) => (
          <button
            key={t}
            onClick={() => setUserType(t)}
            style={{
              ...styles.trackBtn,
              background: userType === t ? TRACK_LABELS[t].color : "#f0f4f8",
              color: userType === t ? "#fff" : "#333",
            }}
          >
            <span style={styles.trackTitle}>{TRACK_LABELS[t].title}</span>
            <span style={styles.trackSub}>{TRACK_LABELS[t].subtitle}</span>
          </button>
        ))}
      </div>

      {/* Login form */}
      <form onSubmit={handleSubmit} style={styles.form}>
        <label style={styles.label} htmlFor="uin">
          National ID (UIN)
        </label>
        <input
          id="uin"
          type="text"
          value={uin}
          onChange={(e) => setUin(e.target.value)}
          placeholder="Enter your national ID"
          style={styles.input}
          autoComplete="off"
          required
        />

        {error && <p style={styles.error}>{error}</p>}

        <button type="submit" style={styles.submitBtn} disabled={loading}>
          {loading ? "Verifying identity…" : "Continue"}
        </button>
      </form>

      <p style={styles.consent}>
        By continuing, you consent to LIFP verifying your identity via the national
        digital ID system and using your mobile money data to generate a credit score.
        You can revoke consent at any time in Settings.
      </p>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: "#f5f7fa",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "2rem 1rem",
    fontFamily: "Arial, sans-serif",
  },
  header: {
    textAlign: "center",
    marginBottom: "2rem",
  },
  brand: {
    fontSize: "3rem",
    fontWeight: 800,
    color: "#1F3864",
    margin: 0,
  },
  tagline: {
    color: "#2E75B6",
    fontSize: "0.95rem",
    marginTop: "0.25rem",
  },
  trackRow: {
    display: "flex",
    gap: "1rem",
    marginBottom: "1.5rem",
    width: "100%",
    maxWidth: "400px",
  },
  trackBtn: {
    flex: 1,
    border: "none",
    borderRadius: "10px",
    padding: "1rem 0.75rem",
    cursor: "pointer",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "0.3rem",
    transition: "background 0.2s",
  },
  trackTitle: {
    fontWeight: 700,
    fontSize: "1rem",
  },
  trackSub: {
    fontSize: "0.75rem",
    opacity: 0.85,
    textAlign: "center",
  },
  form: {
    width: "100%",
    maxWidth: "400px",
    display: "flex",
    flexDirection: "column",
    gap: "0.75rem",
  },
  label: {
    fontWeight: 600,
    color: "#1F3864",
    fontSize: "0.9rem",
  },
  input: {
    padding: "0.85rem 1rem",
    borderRadius: "8px",
    border: "1.5px solid #BDD7EE",
    fontSize: "1rem",
    outline: "none",
  },
  error: {
    color: "#c0392b",
    fontSize: "0.85rem",
    margin: 0,
  },
  submitBtn: {
    padding: "0.9rem",
    borderRadius: "8px",
    border: "none",
    background: "#1F3864",
    color: "#fff",
    fontWeight: 700,
    fontSize: "1rem",
    cursor: "pointer",
    marginTop: "0.5rem",
  },
  consent: {
    maxWidth: "400px",
    marginTop: "1.5rem",
    fontSize: "0.75rem",
    color: "#888",
    textAlign: "center",
    lineHeight: 1.5,
  },
};
