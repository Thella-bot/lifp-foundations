import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchScore, type ScoreResponse } from "../api/client";
import {
  cacheScore,
  flushSyncQueue,
  getAllTransactions,
  getCachedScore,
  saveTransaction,
  type LocalTransaction,
} from "../db/localStore";

const TIER_COLOR: Record<string, string> = {
  A: "#27ae60",
  B: "#2ecc71",
  C: "#f39c12",
  D: "#e74c3c",
  E: "#8e44ad",
};

const TIER_LABEL: Record<string, string> = {
  A: "Excellent",
  B: "Good",
  C: "Fair",
  D: "Poor",
  E: "Very Poor",
};

export default function Dashboard() {
  const navigate = useNavigate();
  const token = sessionStorage.getItem("access_token") ?? "";
  const internalId = sessionStorage.getItem("internal_id") ?? "";
  const userType = (sessionStorage.getItem("user_type") as "msme" | "individual") ?? "individual";

  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [txns, setTxns] = useState<LocalTransaction[]>([]);
  const [offline, setOffline] = useState(!navigator.onLine);
  const [scoreError, setScoreError] = useState<string | null>(null);

  const [txType, setTxType] = useState<LocalTransaction["type"]>("cash_in");
  const [txAmount, setTxAmount] = useState("");
  const [txNote, setTxNote] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!token || !internalId) {
      navigate("/");
      return;
    }

    void loadScore();
    void loadTransactions();

    const handleOnline = () => {
      setOffline(false);
      void flushSyncQueue();
      void loadScore();
    };

    const handleOffline = () => {
      setOffline(true);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [internalId, navigate, token]);

  async function loadScore() {
    const cached = await getCachedScore(internalId);
    if (cached) {
      setScore(cached as ScoreResponse);
    }

    if (navigator.onLine) {
      try {
        const fresh = await fetchScore(internalId, token);
        await cacheScore(fresh);
        setScore(fresh);
        setScoreError(null);
      } catch {
        if (!cached) {
          setScoreError("Could not load score. You may be offline.");
        }
      }
    }
  }

  async function loadTransactions() {
    const all = await getAllTransactions();
    setTxns(all.slice(-10).reverse());
  }

  async function handleAddTransaction(e: React.FormEvent) {
    e.preventDefault();
    const amount = parseFloat(txAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      return;
    }

    setSaving(true);
    await saveTransaction({
      type: txType,
      amount,
      note: txNote.trim() || undefined,
      timestamp: new Date().toISOString(),
      synced: navigator.onLine,
    });

    setTxAmount("");
    setTxNote("");
    setSaving(false);

    await loadTransactions();
    if (navigator.onLine) {
      void flushSyncQueue();
    }
  }

  function handleLogout() {
    sessionStorage.clear();
    navigate("/");
  }

  function ScoreGauge({ s }: { s: ScoreResponse }) {
    const pct = ((s.score - 300) / 550) * 100;
    const color = TIER_COLOR[s.tier] ?? "#888";

    return (
      <div style={gaugeStyles.card}>
        <p style={gaugeStyles.label}>Your LIFP Credit Score</p>
        <div style={{ ...gaugeStyles.bar, background: "#e0e0e0" }}>
          <div style={{ ...gaugeStyles.fill, width: `${pct}%`, background: color }} />
        </div>
        <p style={{ ...gaugeStyles.scoreNum, color }}>{s.score}</p>
        <p style={{ ...gaugeStyles.tier, color }}>
          {s.tier} - {TIER_LABEL[s.tier]}
        </p>
        <p style={gaugeStyles.meta}>Model v{s.model_version}</p>

        {s.factors.length > 0 && (
          <details style={{ marginTop: "0.75rem", fontSize: "0.8rem", color: "#555" }}>
            <summary style={{ cursor: "pointer" }}>Top factors</summary>
            <ul style={{ paddingLeft: "1rem", margin: "0.5rem 0" }}>
              {s.factors.slice(0, 5).map((f) => (
                <li key={f.feature}>
                  {f.feature}: {f.shap_value > 0 ? "+" : ""}
                  {f.shap_value.toFixed(3)}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.topBar}>
        <span style={styles.brandSmall}>LIFP</span>
        <span style={styles.userTag}>{userType === "msme" ? "Business" : "Personal"}</span>
        <button onClick={handleLogout} style={styles.logoutBtn}>
          Log out
        </button>
      </div>

      {offline && <div style={styles.offlineBanner}>You are offline - data will sync when you reconnect.</div>}

      {score ? (
        <ScoreGauge s={score} />
      ) : scoreError ? (
        <div style={styles.errorCard}>{scoreError}</div>
      ) : (
        <div style={styles.loadingCard}>Loading your credit score...</div>
      )}

      <div style={styles.card}>
        <h3 style={styles.sectionTitle}>
          {userType === "msme" ? "Record a Business Transaction" : "Record a Transaction"}
        </h3>
        <form onSubmit={handleAddTransaction} style={styles.txForm}>
          <select value={txType} onChange={(e) => setTxType(e.target.value as LocalTransaction["type"])} style={styles.select}>
            <option value="cash_in">Cash In</option>
            <option value="cash_out">Cash Out</option>
            <option value="airtime_purchase">Airtime Purchase</option>
            <option value="bill_payment">Bill Payment</option>
            {userType === "msme" && <option value="merchant_payment">Merchant Payment</option>}
          </select>
          <input
            type="number"
            placeholder="Amount (M)"
            value={txAmount}
            onChange={(e) => setTxAmount(e.target.value)}
            style={styles.input}
            min="0"
            step="0.01"
            required
          />
          <input
            type="text"
            placeholder="Note (optional)"
            value={txNote}
            onChange={(e) => setTxNote(e.target.value)}
            style={styles.input}
          />
          <button type="submit" style={styles.addBtn} disabled={saving}>
            {saving ? "Saving..." : "Add"}
          </button>
        </form>
      </div>

      <div style={styles.card}>
        <h3 style={styles.sectionTitle}>Recent Transactions</h3>
        {txns.length === 0 ? (
          <p style={{ color: "#aaa", fontSize: "0.9rem" }}>No transactions yet.</p>
        ) : (
          <ul style={styles.txList}>
            {txns.map((t) => (
              <li key={t.id} style={styles.txItem}>
                <span style={styles.txType}>{t.type.replace(/_/g, " ")}</span>
                <span
                  style={{
                    fontWeight: 700,
                    color: t.type === "cash_in" ? "#27ae60" : "#e74c3c",
                  }}
                >
                  {t.type === "cash_in" ? "+" : "-"}M{t.amount.toFixed(2)}
                </span>
                {!t.synced && <span style={styles.pendingTag}>pending</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: "#f5f7fa",
    fontFamily: "Arial, sans-serif",
    paddingBottom: "2rem",
  },
  topBar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    background: "#1F3864",
    color: "#fff",
    padding: "0.75rem 1.25rem",
  },
  brandSmall: { fontWeight: 800, fontSize: "1.2rem", color: "#BDD7EE" },
  userTag: { fontSize: "0.85rem", color: "#BDD7EE" },
  logoutBtn: {
    background: "none",
    border: "1px solid #BDD7EE",
    color: "#BDD7EE",
    borderRadius: "6px",
    padding: "0.3rem 0.7rem",
    cursor: "pointer",
    fontSize: "0.8rem",
  },
  offlineBanner: {
    background: "#f39c12",
    color: "#fff",
    textAlign: "center",
    padding: "0.5rem",
    fontSize: "0.85rem",
  },
  card: {
    background: "#fff",
    borderRadius: "12px",
    margin: "1rem",
    padding: "1.25rem",
    boxShadow: "0 2px 8px rgba(0,0,0,0.07)",
  },
  errorCard: {
    background: "#fdecea",
    borderRadius: "12px",
    margin: "1rem",
    padding: "1.25rem",
    color: "#c0392b",
    fontSize: "0.9rem",
  },
  loadingCard: {
    background: "#fff",
    borderRadius: "12px",
    margin: "1rem",
    padding: "1.5rem",
    textAlign: "center",
    color: "#888",
    boxShadow: "0 2px 8px rgba(0,0,0,0.07)",
  },
  sectionTitle: { margin: "0 0 1rem", color: "#1F3864", fontSize: "1rem" },
  txForm: { display: "flex", flexDirection: "column", gap: "0.6rem" },
  select: {
    padding: "0.6rem",
    borderRadius: "7px",
    border: "1.5px solid #BDD7EE",
    fontSize: "0.95rem",
  },
  input: {
    padding: "0.6rem 0.8rem",
    borderRadius: "7px",
    border: "1.5px solid #BDD7EE",
    fontSize: "0.95rem",
  },
  addBtn: {
    padding: "0.7rem",
    borderRadius: "7px",
    border: "none",
    background: "#2E75B6",
    color: "#fff",
    fontWeight: 700,
    cursor: "pointer",
  },
  txList: {
    listStyle: "none",
    padding: 0,
    margin: 0,
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
  },
  txItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0.5rem 0",
    borderBottom: "1px solid #f0f0f0",
    fontSize: "0.9rem",
  },
  txType: { color: "#555", textTransform: "capitalize" },
  pendingTag: {
    fontSize: "0.7rem",
    color: "#f39c12",
    border: "1px solid #f39c12",
    borderRadius: "4px",
    padding: "0.1rem 0.3rem",
  },
};

const gaugeStyles: Record<string, React.CSSProperties> = {
  card: {
    background: "#fff",
    borderRadius: "12px",
    margin: "1rem",
    padding: "1.5rem",
    boxShadow: "0 2px 8px rgba(0,0,0,0.07)",
    textAlign: "center",
  },
  label: { color: "#555", fontSize: "0.85rem", margin: "0 0 0.75rem" },
  bar: {
    height: "14px",
    borderRadius: "7px",
    overflow: "hidden",
    marginBottom: "0.75rem",
  },
  fill: { height: "100%", borderRadius: "7px", transition: "width 0.6s ease" },
  scoreNum: { fontSize: "3.5rem", fontWeight: 800, margin: "0" },
  tier: { fontWeight: 700, fontSize: "1.1rem", margin: "0.2rem 0 0" },
  meta: { fontSize: "0.72rem", color: "#aaa", margin: "0.4rem 0 0" },
};
