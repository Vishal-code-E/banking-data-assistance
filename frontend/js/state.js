/* ============================================================
   STATE MANAGER — Stitch AI
   Simple reactive store for app-wide state.
   ============================================================ */

const state = {
  /** Current visible page id */
  currentPage: 'conversations',

  /** Chat messages: { role: 'user'|'ai', text, sql?, timestamp } */
  messages: [],

  /** Query history: { sql, rowCount, execTime, error, timestamp } */
  history: [],

  /** Cached tables info from /tables */
  tablesCache: null,

  /** Health data cache */
  healthCache: null,
};

/* ---------- accessors ---------- */

export function getState() {
  return state;
}

export function setPage(page) {
  state.currentPage = page;
}

/* ---------- chat messages ---------- */

export function addUserMessage(text) {
  const msg = { role: 'user', text, timestamp: Date.now() };
  state.messages.push(msg);
  return msg;
}

export function addAIMessage(text, sql = null) {
  const msg = { role: 'ai', text, sql, _result: null, timestamp: Date.now() };
  state.messages.push(msg);
  return msg;
}

export function getMessages() {
  return state.messages;
}

/* ---------- history ---------- */

export function addHistory(entry) {
  state.history.unshift({
    sql: entry.sql,
    rowCount: entry.rowCount ?? 0,
    execTime: entry.execTime ?? 0,
    error: entry.error ?? null,
    timestamp: Date.now(),
  });
  // cap at 50
  if (state.history.length > 50) state.history.length = 50;
}

export function getHistory() {
  return state.history;
}

/* ---------- caches ---------- */

export function setTablesCache(data) {
  state.tablesCache = data;
}

export function getTablesCache() {
  return state.tablesCache;
}

export function setHealthCache(data) {
  state.healthCache = data;
}

export function getHealthCache() {
  return state.healthCache;
}
