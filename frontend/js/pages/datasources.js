/* ============================================================
   DATA SOURCES PAGE — Bank your Data
   Browse database tables, columns, and types.
   ============================================================ */

import { getTables, checkHealth } from '../api.js';
import { setTablesCache, getTablesCache, setHealthCache, getHealthCache } from '../state.js';

export async function render(container) {
  container.innerHTML = `
    <div class="datasources-page">
      <h1 class="page-title">Data Sources</h1>
      <p class="page-desc">Browse the connected database schema</p>
      <div class="ds-grid" id="ds-grid">
        <div style="padding:2rem;text-align:center;color:var(--text-400)">
          <span class="spinner-inline" style="display:inline-block;margin-bottom:0.75rem"></span><br/>
          Loading tables…
        </div>
      </div>
    </div>
  `;

  const grid = container.querySelector('#ds-grid');

  try {
    const [tablesData, health] = await Promise.all([
      getTablesCache() ? Promise.resolve({ tables: getTablesCache() }) : getTables(),
      getHealthCache() ?? checkHealth(),
    ]);

    const tables = tablesData.tables || [];
    setTablesCache(tables);
    setHealthCache(health);

    if (tables.length === 0) {
      grid.innerHTML = `<div style="padding:2rem;color:var(--text-400)">No tables found in the database.</div>`;
      return;
    }

    grid.innerHTML = tables.map(t => `
      <div class="ds-card">
        <div class="ds-card-head">
          <div class="ds-card-icon">
            <span class="material-symbols-outlined">table_chart</span>
          </div>
          <div class="ds-card-titlegroup">
            <div class="ds-card-title">${escapeHtml(t.name)}</div>
            <div class="ds-card-sub">${t.description || t.columns?.length + ' columns' || ''}</div>
          </div>
          <span class="ds-status connected"><span class="ds-status-dot"></span> Connected</span>
        </div>
        <div class="ds-columns">
          ${(t.columns || []).map(c => {
            const label = typeof c === 'string' ? c : `${c.name} (${c.type || '?'})`;
            return `<span class="ds-col-tag">${escapeHtml(label)}</span>`;
          }).join('')}
        </div>
      </div>
    `).join('');

  } catch (e) {
    grid.innerHTML = `<div class="results-error">${escapeHtml(e.message)}</div>`;
  }
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
