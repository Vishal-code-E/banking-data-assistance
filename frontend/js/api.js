/* ============================================================
   API SERVICE — Bank your Data
   All communication with the FastAPI backend.
   ============================================================ */

/**
 * Resolve the backend API base URL.
 *
 * Priority:
 *  1. window.__API_BASE  – allows runtime injection via a <script> tag
 *  2. Known Render deployment mapping
 *  3. Fallback → localhost for local development.
 */
function resolveApiBase() {
  // 1. Explicit runtime override
  if (window.__API_BASE) return window.__API_BASE.replace(/\/+$/, '');

  const host = window.location.hostname;

  // 2. Render production
  if (host.endsWith('.onrender.com')) {
    return 'https://banking-data-assistance.onrender.com';
  }

  // 3. Local development
  return 'http://localhost:8001';
}

const API_BASE = resolveApiBase();

/**
 * Wrapper around fetch with timeout support.
 * Render free-tier cold starts can take 30-60 s, so we allow up to 120 s
 * for AI requests.
 */
async function request(url, opts = {}, timeoutMs = 120000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, { ...opts, signal: controller.signal });
    clearTimeout(timer);

    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || json.error || JSON.stringify(json));
    return json;
  } catch (err) {
    clearTimeout(timer);
    if (err.name === 'AbortError') {
      throw new Error(
        'Request timed out. The server may be waking up from a cold start — please try again in 30 seconds.'
      );
    }
    throw err;
  }
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
