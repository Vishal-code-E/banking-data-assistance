/* ============================================================
   DASHBOARD PAGE — Bank your Data
   Health overview, table stats, recent activity.
   ============================================================ */

import { checkHealth, getTables } from '../api.js';
import {
  setHealthCache, getHealthCache,
  setTablesCache, getTablesCache,
  getHistory,
} from '../state.js';

export async function render(container) {
  container.innerHTML = `
    <div class="dashboard-page">
      <h1 class="page-title">Dashboard</h1>
      <p class="page-desc">System health &amp; database overview</p>

      <div class="stats-grid" id="stats-grid">
        ${statCardSkeleton()}${statCardSkeleton()}${statCardSkeleton()}${statCardSkeleton()}
      </div>

      <div class="recent-section">
        <h2 class="recent-title">Recent Queries</h2>
        <div class="recent-list" id="recent-list"></div>
      </div>
    </div>
  `;

  loadStats(container);
  renderRecent(container);
}

/* ---------- stats ---------- */
async function loadStats(container) {
  try {
    const [health, tablesData] = await Promise.all([
      getHealthCache() ?? checkHealth(),
      getTablesCache() ? Promise.resolve({ tables: getTablesCache() }) : getTables(),
    ]);

    setHealthCache(health);
    if (tablesData.tables) setTablesCache(tablesData.tables);

    const tables = tablesData.tables || [];
    const totalCols = tables.reduce((s, t) => s + (t.columns?.length ?? 0), 0);
    const history = getHistory();

    const grid = container.querySelector('#stats-grid');
    grid.innerHTML = `
      ${statCard('Database', health.status === 'healthy' ? 'Connected' : 'Error', health.database || 'banking.db', health.status === 'healthy' ? 'stat-badge-up' : 'stat-badge-down')}
      ${statCard('Tables', tables.length, `${totalCols} total columns`)}
      ${statCard('Queries Run', history.length, history.length ? `Last: ${timeAgo(history[0].timestamp)}` : 'No queries yet')}
      ${statCard('Status', health.status === 'healthy' ? '● Online' : '● Offline', 'Real-time', health.status === 'healthy' ? 'stat-badge-up' : 'stat-badge-down')}
    `;
  } catch (e) {
    const grid = container.querySelector('#stats-grid');
    grid.innerHTML = `
      ${statCard('Database', 'Error', e.message, 'stat-badge-down')}
    `;
  }
}

function statCard(label, value, sub, badgeClass = '') {
  return `
    <div class="stat-card">
      <div class="stat-label">${label}</div>
      <div class="stat-value ${badgeClass}">${value}</div>
      <div class="stat-sub">${sub}</div>
    </div>
  `;
}

function statCardSkeleton() {
  return `
    <div class="stat-card">
      <div class="stat-label" style="width:60px;height:12px;background:var(--border);border-radius:4px"></div>
      <div class="stat-value" style="width:80px;height:24px;background:var(--border);border-radius:4px;margin-top:0.5rem"></div>
      <div class="stat-sub" style="width:100px;height:10px;background:var(--border-light);border-radius:4px;margin-top:0.5rem"></div>
    </div>
  `;
}

/* ---------- recent queries ---------- */
function renderRecent(container) {
  const list = container.querySelector('#recent-list');
  const history = getHistory();

  if (history.length === 0) {
    list.innerHTML = `
      <div class="history-empty">
        <span class="material-symbols-outlined">query_stats</span>
        No queries yet. Head to <strong>Conversations</strong> to start querying.
      </div>
    `;
    return;
  }

  list.innerHTML = history.slice(0, 5).map(h => `
    <div class="recent-item">
      <div class="recent-icon">
        <span class="material-symbols-outlined">${h.error ? 'error' : 'check_circle'}</span>
      </div>
      <div class="recent-info">
        <div class="recent-info-title">${escapeHtml(h.sql)}</div>
        <div class="recent-info-sub">${timeAgo(h.timestamp)} · ${h.rowCount} rows · ${h.execTime}ms</div>
      </div>
      <span class="material-symbols-outlined recent-arrow">chevron_right</span>
    </div>
  `).join('');
}

/* ---------- util ---------- */
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
