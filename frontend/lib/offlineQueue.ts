/** Minimal IndexedDB offline attempt queue (no Dexie dependency). */

const DB_NAME = "pegazus-offline";
const STORE = "attempts";

export type QueuedAttempt = {
  client_attempt_id: string;
  session_id: string;
  item_id: string;
  part_index: number;
  answer: Record<string, unknown>;
  latency_ms: number;
  hint_level: number;
  created_at: number;
};

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "client_attempt_id" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function enqueueAttempt(row: QueuedAttempt): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(row);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

export async function listQueued(): Promise<QueuedAttempt[]> {
  const db = await openDb();
  const rows = await new Promise<QueuedAttempt[]>((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const req = tx.objectStore(STORE).getAll();
    req.onsuccess = () => resolve(req.result as QueuedAttempt[]);
    req.onerror = () => reject(req.error);
  });
  db.close();
  // Rows queued by older clients carry step_index/submitted_latex, which the server no longer
  // accepts: convert them, or one stale row would 422 the whole sync batch and its attempts be lost.
  return rows.map((r) => {
    const old = r as QueuedAttempt & { step_index?: number; submitted_latex?: string };
    return old.answer
      ? r
      : { ...r, part_index: old.step_index ?? 0, answer: { latex: old.submitted_latex ?? "" } };
  });
}

export async function removeQueued(ids: string[]): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    const store = tx.objectStore(STORE);
    for (const id of ids) store.delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}
