/* ============================================================
   HISTORY PAGE — Bank your Data
   Display previous queries from the session state.
   ============================================================ */

import { getHistory } from '../state.js';

export function render(container) {
  const history = getHistory();

  container.innerHTML = `
    <div class="history-page">
      <h1 class="page-title">Query History</h1>
      <p class="page-desc">Browse your previous queries from this session</p>
      <div class="history-list" id="history-list"></div>
    </div>
  `;

  const list = container.querySelector('#history-list');

  if (history.length === 0) {
    list.innerHTML = `
      <div class="history-empty">
        <span class="material-symbols-outlined">history</span>
        No queries yet. Run a query in Conversations or the SQL Editor.
      </div>
    `;
    return;
  }

  list.innerHTML = history.map((h, i) => `
    <div class="history-item" data-idx="${i}">
      <div class="history-dot ${h.error ? 'error' : ''}"></div>
      <div class="history-info">
        <div class="history-sql">${escapeHtml(h.sql)}</div>
        <div class="history-meta">${timeAgo(h.timestamp)}${h.execTime ? ` · ${h.execTime}ms` : ''}</div>
      </div>
      <div class="history-rows">${h.error ? 'Error' : `${h.rowCount} rows`}</div>
    </div>
  `).join('');

  /* clicking a history item copies its SQL */
  list.querySelectorAll('.history-item').forEach(el => {
    el.addEventListener('click', () => {
      const idx = parseInt(el.dataset.idx, 10);
      const sql = history[idx]?.sql;
      if (sql) {
        navigator.clipboard.writeText(sql).then(() => {
          const infoEl = el.querySelector('.history-meta');
          const orig = infoEl.textContent;
          infoEl.textContent = 'Copied to clipboard!';
          setTimeout(() => { infoEl.textContent = orig; }, 1500);
        });
      }
    });
  });
}

function timeAgo(ts) {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return new Date(ts).toLocaleDateString();
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
