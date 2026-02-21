/* ============================================================
   SQL EDITOR PAGE — Stitch AI
   Direct SQL editing with line numbers & results as prose.
   ============================================================ */

import { executeQuery } from '../api.js';
import { addHistory } from '../state.js';

let textareaEl, lineNumsEl, resultsEl, runBtnEl;

export function render(container) {
  container.innerHTML = `
    <div class="sql-editor-page">
      <div class="editor-toolbar">
        <div class="editor-tab">
          <span class="material-symbols-outlined">code</span>
          Query 1
        </div>
        <div class="editor-actions">
          <button id="run-query-btn" class="run-btn">
            <span class="material-symbols-outlined">play_arrow</span>
            Run Query
          </button>
        </div>
      </div>

      <div class="editor-body">
        <div class="editor-textarea-wrap">
          <div class="editor-line-nums" id="line-nums"><span>1</span></div>
          <textarea
            id="sql-textarea"
            class="editor-textarea"
            spellcheck="false"
            placeholder="SELECT * FROM customers LIMIT 10;"
          ></textarea>
        </div>
        <div class="editor-results" id="editor-results" style="display:none">
          <div class="editor-results-header">
            <span class="editor-results-title">Results</span>
            <span class="editor-results-meta" id="results-meta"></span>
          </div>
          <div class="editor-results-content" id="results-content"></div>
        </div>
      </div>
    </div>
  `;

  textareaEl = container.querySelector('#sql-textarea');
  lineNumsEl = container.querySelector('#line-nums');
  resultsEl  = container.querySelector('#editor-results');
  runBtnEl   = container.querySelector('#run-query-btn');

  /* line numbers */
  textareaEl.addEventListener('input', updateLineNumbers);
  textareaEl.addEventListener('scroll', () => {
    lineNumsEl.scrollTop = textareaEl.scrollTop;
  });

  /* run */
  runBtnEl.addEventListener('click', runQuery);
  textareaEl.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); runQuery(); }
    /* tab indent */
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = textareaEl.selectionStart;
      const end = textareaEl.selectionEnd;
      textareaEl.value = textareaEl.value.substring(0, start) + '  ' + textareaEl.value.substring(end);
      textareaEl.selectionStart = textareaEl.selectionEnd = start + 2;
      updateLineNumbers();
    }
  });
}

function updateLineNumbers() {
  const lines = textareaEl.value.split('\n').length;
  lineNumsEl.innerHTML = Array.from({ length: lines }, (_, i) => `<span>${i + 1}</span>`).join('');
}

async function runQuery() {
  const sql = textareaEl.value.trim();
  if (!sql) return;

  runBtnEl.disabled = true;
  runBtnEl.innerHTML = '<span class="spinner-inline"></span> Running…';
  resultsEl.style.display = '';

  const meta = resultsEl.querySelector('#results-meta');
  const content = resultsEl.querySelector('#results-content');

  content.innerHTML = '<div style="display:flex;align-items:center;gap:0.5rem"><span class="spinner-inline"></span> Executing query…</div>';
  meta.textContent = '';

  try {
    const result = await executeQuery(sql);

    addHistory({
      sql: result.validated_sql || sql,
      rowCount: result.execution_result?.row_count ?? 0,
      execTime: result.execution_result?.execution_time_ms ?? 0,
      error: result.error,
    });

    if (result.error) {
      meta.textContent = 'Error';
      content.innerHTML = `<div class="results-error">${escapeHtml(result.error)}</div>`;
    } else {
      const data = result.execution_result?.data ?? [];
      const rows = result.execution_result?.row_count ?? 0;
      const ms   = result.execution_result?.execution_time_ms ?? 0;
      meta.textContent = `${rows} rows · ${ms}ms`;
      content.innerHTML = `<div class="results-text">${buildResultsText(data, rows)}</div>`;
    }
  } catch (e) {
    meta.textContent = 'Error';
    content.innerHTML = `<div class="results-error">${escapeHtml(e.message)}</div>`;
  }

  runBtnEl.disabled = false;
  runBtnEl.innerHTML = '<span class="material-symbols-outlined">play_arrow</span> Run Query';
}

function buildResultsText(data, rowCount) {
  if (rowCount === 0) return 'Query returned <strong>0 rows</strong>.';

  const keys = Object.keys(data[0]);

  if (rowCount === 1 && keys.length === 1) {
    return `Result: <strong>${formatVal(data[0][keys[0]])}</strong>`;
  }

  let html = `<strong>${rowCount} row${rowCount > 1 ? 's' : ''} returned:</strong><br/><br/>`;
  const show = data.slice(0, 20);
  show.forEach((row, i) => {
    const parts = keys.map(k => `${humanize(k)}: ${formatVal(row[k])}`).join(' · ');
    html += `<strong>${i + 1}.</strong> ${parts}<br/>`;
  });
  if (rowCount > 20) html += `<br/><em>…and ${rowCount - 20} more rows.</em>`;
  return html;
}

function humanize(k) { return k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
function formatVal(v) {
  if (v == null) return '—';
  if (typeof v === 'number') return v.toLocaleString();
  return escapeHtml(String(v));
}
function escapeHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
