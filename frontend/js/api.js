/* ============================================================
   API SERVICE — Stitch AI
   All communication with the FastAPI backend.
   ============================================================ */

const API_BASE = 'http://localhost:8001';

/** Wrapper around fetch, returns parsed JSON or throws */
async function request(url, opts = {}) {
  const res = await fetch(url, opts);
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || JSON.stringify(json));
  return json;
}

/* ---------- public helpers ---------- */

export async function checkHealth() {
  return request(`${API_BASE}/health`);
}

export async function getTables() {
  return request(`${API_BASE}/tables`);
}

export async function getInfo() {
  return request(`${API_BASE}/info`);
}

/**
 * Execute a SQL query and return results.
 * @param {string} sql — raw SQL string
 * @returns {Promise<{validated_sql, execution_result, summary, chart_suggestion, error}>}
 */
export async function executeQuery(sql) {
  return request(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sql }),
  });
}

/**
 * Send a natural-language question through the AI engine.
 * @param {string} query — plain English question
 * @returns {Promise<{validated_sql, execution_result, summary, chart_suggestion, error}>}
 */
export async function askQuestion(query) {
  return request(`${API_BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
}
