/**
 * pwa/src/db/localStore.ts
 * IndexedDB offline store via idb.
 * Stores transactions and a sync queue for when the device is offline.
 * Workbox Background Sync picks up the queue on reconnection.
 */
import { openDB, type DBSchema, type IDBPDatabase } from "idb";

// ── Schema ────────────────────────────────────────────────────────────────────

export interface LocalTransaction {
  id?: number;
  type: "cash_in" | "cash_out" | "airtime_purchase" | "bill_payment" | "merchant_payment";
  amount: number;
  note?: string;
  timestamp: string;   // ISO-8601
  synced: boolean;
}

export interface SyncQueueItem {
  id?: number;
  url: string;
  method: string;
  body: string;        // JSON.stringify'd payload
  createdAt: string;
}

export interface CachedScore {
  internal_id: string;
  score: number;
  tier: string;
  prob_default: number;
  model_version: string;
  factors: { feature: string; shap_value: number }[];
  cachedAt: string;    // ISO-8601; expire after 24 h
}

interface LIFPSchema extends DBSchema {
  transactions: {
    key: number;
    value: LocalTransaction;
    indexes: { "by-synced": boolean };
  };
  syncQueue: {
    key: number;
    value: SyncQueueItem;
  };
  scoreCache: {
    key: string;       // internal_id
    value: CachedScore;
  };
}

// ── DB singleton ──────────────────────────────────────────────────────────────

let _db: IDBPDatabase<LIFPSchema> | null = null;

export async function getDB(): Promise<IDBPDatabase<LIFPSchema>> {
  if (_db) return _db;
  _db = await openDB<LIFPSchema>("lifp-db", 1, {
    upgrade(db) {
      // Transactions store
      const txStore = db.createObjectStore("transactions", {
        keyPath: "id",
        autoIncrement: true,
      });
      txStore.createIndex("by-synced", "synced");

      // Offline sync queue
      db.createObjectStore("syncQueue", {
        keyPath: "id",
        autoIncrement: true,
      });

      // Credit score cache (keyed by internal_id)
      db.createObjectStore("scoreCache", { keyPath: "internal_id" });
    },
  });
  return _db;
}

// ── Transactions ──────────────────────────────────────────────────────────────

export async function saveTransaction(tx: Omit<LocalTransaction, "id">): Promise<number> {
  const db = await getDB();
  return db.add("transactions", tx);
}

export async function getUnsyncedTransactions(): Promise<LocalTransaction[]> {
  const db = await getDB();
  return db.getAllFromIndex("transactions", "by-synced", false);
}

export async function markSynced(id: number): Promise<void> {
  const db = await getDB();
  const tx = await db.get("transactions", id);
  if (tx) {
    tx.synced = true;
    await db.put("transactions", tx);
  }
}

export async function getAllTransactions(): Promise<LocalTransaction[]> {
  const db = await getDB();
  return db.getAll("transactions");
}

// ── Sync queue ────────────────────────────────────────────────────────────────

export async function enqueueRequest(item: Omit<SyncQueueItem, "id">): Promise<void> {
  const db = await getDB();
  await db.add("syncQueue", item);
}

export async function flushSyncQueue(): Promise<void> {
  const db = await getDB();
  const items = await db.getAll("syncQueue");
  for (const item of items) {
    try {
      const res = await fetch(item.url, {
        method: item.method,
        headers: { "Content-Type": "application/json" },
        body: item.body,
      });
      if (res.ok && item.id !== undefined) {
        await db.delete("syncQueue", item.id);
      }
    } catch {
      // Remain in queue; retry on next flush
    }
  }
}

// ── Score cache ───────────────────────────────────────────────────────────────

const SCORE_CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

export async function cacheScore(score: Omit<CachedScore, "cachedAt">): Promise<void> {
  const db = await getDB();
  await db.put("scoreCache", { ...score, cachedAt: new Date().toISOString() });
}

export async function getCachedScore(internalId: string): Promise<CachedScore | null> {
  const db = await getDB();
  const cached = await db.get("scoreCache", internalId);
  if (!cached) return null;
  const age = Date.now() - new Date(cached.cachedAt).getTime();
  if (age > SCORE_CACHE_TTL_MS) {
    await db.delete("scoreCache", internalId);
    return null;
  }
  return cached;
}
