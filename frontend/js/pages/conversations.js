/* ============================================================
   CONVERSATIONS PAGE — Bank your Data
   ChatGPT-style conversational interface.
   User types a natural-language question → /ask endpoint →
   AI engine (LangGraph) → results rendered with table + chart.
   ============================================================ */

import { askQuestion, executeQuery, getTables } from '../api.js';
import {
  addUserMessage,
  addAIMessage,
  getMessages,
  addHistory,
  setTablesCache,
  getTablesCache,
} from '../state.js';

let chatFeedEl = null;
let inputEl    = null;
let sendBtn    = null;

/* ============================================================
   RENDER
   ============================================================ */
export function render(container) {
  container.innerHTML = `
    <div class="chat-page">
      <div class="chat-messages" id="chat-messages">
        <div class="chat-feed" id="chat-feed"></div>
      </div>
      <div class="chat-input-area">
        <div class="chat-input-wrap">
          <div class="input-prepend">
            <button class="input-attach-btn" title="Attach">
              <span class="material-symbols-outlined">add_circle</span>
            </button>
          </div>
          <input
            id="chat-input"
            class="chat-input"
            type="text"
            placeholder="Ask about your banking data..."
            autocomplete="off"
          />
          <div class="input-append">
            <button id="send-btn" class="send-btn" title="Send">
              <span class="material-symbols-outlined">arrow_upward</span>
            </button>
          </div>
        </div>
        <div class="chat-disclaimer">
          BData Assistant can make mistakes. Always verify critical financial data.
        </div>
      </div>
    </div>
  `;

  chatFeedEl = container.querySelector('#chat-feed');
  inputEl    = container.querySelector('#chat-input');
  sendBtn    = container.querySelector('#send-btn');

  /* replay previous messages */
  const msgs = getMessages();
  if (msgs.length === 0) {
    renderWelcome();
  } else {
    msgs.forEach(m => appendBubble(m));
  }

  /* events */
  sendBtn.addEventListener('click', onSend);
  inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend(); }
  });
  scrollToBottom();
}

/* ============================================================
   WELCOME STATE
   ============================================================ */
function renderWelcome() {
  chatFeedEl.innerHTML = `
    <div class="msg-group ai">
      <div class="msg-label">
        <span class="material-symbols-outlined">smart_toy</span>
        <span class="msg-label-text">BData Assistant</span>
      </div>
      <div class="ai-content">
        <div class="ai-text">
          <strong>Welcome to BData Assistant!</strong><br/>
          I can help you query and understand your banking data. Just ask a question in plain English and I'll fetch the relevant information for you.<br/><br/>
          <em>Try these:</em>
        </div>
        <div class="suggestions" id="suggestions"></div>
      </div>
    </div>
  `;

  const suggestions = [
    'Show me all customers',
    'What is the total balance across all accounts?',
    'List recent transactions above $500',
    'How many accounts does each customer have?',
  ];

  const sugBox = chatFeedEl.querySelector('#suggestions');
  sugBox.style.cssText = 'display:flex;flex-wrap:wrap;gap:0.5rem;';
  suggestions.forEach(s => {
    const btn = document.createElement('button');
    btn.textContent = s;
    btn.style.cssText = `
      padding: 0.5rem 1rem;
      background: var(--primary-light);
      border: 1px solid var(--border);
      border-radius: var(--radius-xl);
      font-size: 0.8125rem;
      color: var(--primary);
      cursor: pointer;
      transition: background 0.15s;
    `;
    btn.addEventListener('mouseenter', () => btn.style.background = 'var(--primary-10)');
    btn.addEventListener('mouseleave', () => btn.style.background = 'var(--primary-light)');
    btn.addEventListener('click', () => {
      inputEl.value = s;
      onSend();
    });
    sugBox.appendChild(btn);
  });
}

/* ============================================================
   SEND HANDLER — routes through /ask (AI engine)
   ============================================================ */
async function onSend() {
  const text = inputEl.value.trim();
  if (!text) return;

  inputEl.value = '';
  sendBtn.disabled = true;

  /* clear welcome on first message */
  if (getMessages().length === 0) chatFeedEl.innerHTML = '';

  /* user bubble */
  const userMsg = addUserMessage(text);
  appendBubble(userMsg);
  scrollToBottom();

  /* show progress */
  const progressId = showProgress();

  try {
    /* Decide route: raw SQL → /query, natural language → /ask */
    const isRawSQL = /^\s*(SELECT|WITH)\s/i.test(text);

    updateProgress(progressId, 20, isRawSQL ? 'Executing SQL…' : 'AI is analysing your question…');

    let result;
    if (isRawSQL) {
      result = await executeQuery(text);
    } else {
      result = await askQuestion(text);
    }

    updateProgress(progressId, 80, 'Formatting results…');

    /* record history */
    addHistory({
      sql: result.validated_sql || text,
      rowCount: result.execution_result?.row_count ?? 0,
      execTime: result.execution_result?.execution_time_ms ?? 0,
      error: result.error,
    });

    removeProgress(progressId);

    if (result.error) {
      const aiMsg = addAIMessage(
        `I encountered an issue:\n\n**${result.error}**\n\nCould you rephrase or try a different question?`,
        result.validated_sql || null,
      );
      aiMsg._result = result;
      appendBubble(aiMsg);
    } else {
      const prose = buildProseResponse(text, result);
      const aiMsg = addAIMessage(prose, result.validated_sql);
      aiMsg._result = result;
      appendBubble(aiMsg);
    }
  } catch (err) {
    removeProgress(progressId);
    const aiMsg = addAIMessage(
      `Sorry, something went wrong:\n\n**${err.message}**\n\nPlease check your connection and try again.`,
    );
    aiMsg._isError = true;
    appendBubble(aiMsg);
  }

  sendBtn.disabled = false;
  scrollToBottom();
}

/* ============================================================
   BUILD PROSE RESPONSE
   ============================================================ */
function buildProseResponse(question, result) {
  const { execution_result, summary } = result;
  const data = execution_result?.data ?? [];
  const rowCount = execution_result?.row_count ?? 0;
  const execTime = execution_result?.execution_time_ms
    ?? (execution_result?.execution_time_seconds
        ? Math.round(execution_result.execution_time_seconds * 1000)
        : 0);

  /* If the AI engine already provides a rich summary, prefer it */
  if (summary && summary.length > 30) {
    return summary;
  }

  if (rowCount === 0) {
    return `I ran the query and found **no results**. The database returned 0 rows. You might want to refine your question or check if the data exists.`;
  }

  /* single aggregate value */
  if (rowCount === 1 && data.length === 1) {
    const row = data[0];
    const keys = Object.keys(row);
    if (keys.length === 1) {
      const key = keys[0];
      const val = row[key];
      return `The result is **${formatValue(val)}**.\n\n_(Query returned 1 row in ${execTime}ms)_`;
    }
    /* single row, multiple columns */
    const parts = keys.map(k => `- **${humanize(k)}:** ${formatValue(row[k])}`);
    return `Here's what I found:\n\n${parts.join('\n')}\n\n_(1 row, ${execTime}ms)_`;
  }

  /* few rows → list them conversationally */
  if (rowCount <= 10) {
    const keys = Object.keys(data[0]);
    let text = `I found **${rowCount} result${rowCount > 1 ? 's' : ''}**:\n\n`;
    data.forEach((row, i) => {
      const parts = keys.map(k => `${humanize(k)}: ${formatValue(row[k])}`).join(' · ');
      text += `**${i + 1}.** ${parts}\n`;
    });
    text += `\n_(${rowCount} row${rowCount > 1 ? 's' : ''}, ${execTime}ms)_`;
    return text;
  }

  /* many rows → summarize */
  const keys = Object.keys(data[0]);
  let text = `I found **${rowCount} results**. Here's a summary of the first few:\n\n`;
  const preview = data.slice(0, 5);
  preview.forEach((row, i) => {
    const parts = keys.map(k => `${humanize(k)}: ${formatValue(row[k])}`).join(' · ');
    text += `**${i + 1}.** ${parts}\n`;
  });
  if (rowCount > 5) {
    text += `\n…and **${rowCount - 5} more** rows.\n`;
  }

  /* add numeric highlights */
  keys.forEach(k => {
    const nums = data.map(r => r[k]).filter(v => typeof v === 'number');
    if (nums.length > 2) {
      const sum  = nums.reduce((a, b) => a + b, 0);
      const avg  = sum / nums.length;
      const max  = Math.max(...nums);
      const min  = Math.min(...nums);
      text += `\n**${humanize(k)} stats:** min ${formatValue(min)}, max ${formatValue(max)}, avg ${formatValue(Math.round(avg * 100) / 100)}`;
    }
  });

  text += `\n\n_(${rowCount} rows, ${execTime}ms)_`;
  return text;
}

/* ============================================================
   HELPERS
   ============================================================ */
function humanize(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formatValue(v) {
  if (v == null) return '—';
  if (typeof v === 'number') {
    /* if it looks like money (e.g. balance, amount) give 2 decimals */
    if (Number.isInteger(v) && v > 100) return v.toLocaleString();
    if (!Number.isInteger(v)) return v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return v.toString();
  }
  return String(v);
}

/* ============================================================
   BUBBLE RENDERING
   ============================================================ */
function appendBubble(msg) {
  const group = document.createElement('div');
  group.className = `msg-group ${msg.role}`;

  if (msg.role === 'user') {
    group.innerHTML = `
      <div class="msg-label" style="justify-content:flex-end">
        <span class="msg-label-text">You</span>
      </div>
      <div class="bubble-user">${escapeHtml(msg.text)}</div>
    `;
  } else {
    /* ---- AI bubble ---- */
    const sqlBlock = msg.sql
      ? `<div class="sql-block">
           <div class="sql-header">
             <span class="sql-lang">sql</span>
             <button class="sql-copy-btn" data-sql="${escapeAttr(msg.sql)}">
               <span class="material-symbols-outlined">content_copy</span> Copy
             </button>
           </div>
           <div class="sql-body">
             <pre>${highlightSQL(msg.sql)}</pre>
           </div>
         </div>`
      : '';

    /* data table */
    const tableBlock = buildDataTable(msg._result);

    /* chart */
    const chartBlock = buildChartBlock(msg._result);

    group.innerHTML = `
      <div class="msg-label">
        <span class="material-symbols-outlined">smart_toy</span>
        <span class="msg-label-text">BData Assistant</span>
      </div>
      <div class="ai-content">
        <div class="ai-text">${renderMarkdown(msg.text)}</div>
        ${sqlBlock}
        ${tableBlock}
        ${chartBlock}
      </div>
    `;

    /* copy sql button */
    const copyBtn = group.querySelector('.sql-copy-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(msg.sql).then(() => {
          copyBtn.innerHTML = '<span class="material-symbols-outlined">check</span> Copied!';
          setTimeout(() => {
            copyBtn.innerHTML = '<span class="material-symbols-outlined">content_copy</span> Copy';
          }, 2000);
        });
      });
    }

    /* render chart.js canvas (if chart block present) */
    const canvas = group.querySelector('.bdata-chart-canvas');
    if (canvas && msg._result) renderChart(canvas, msg._result);
  }

  chatFeedEl.appendChild(group);
}

/* ============================================================
   DYNAMIC DATA TABLE
   ============================================================ */
function buildDataTable(result) {
  if (!result || result.error) return '';
  const data = result.execution_result?.data ?? [];
  if (data.length === 0) {
    return `<div class="bdata-empty-state">
      <span class="material-symbols-outlined">search_off</span>
      <span>No data returned</span>
    </div>`;
  }

  /* Derive columns dynamically from the first row — never hardcoded */
  const columns = Object.keys(data[0]);
  const MAX_DISPLAY = 100;
  const showRows = data.slice(0, MAX_DISPLAY);
  const remaining = data.length - showRows.length;

  let html = `<div class="bdata-data-table-wrap">
    <div class="bdata-table-header-bar">
      <span class="material-symbols-outlined" style="font-size:1rem">table_chart</span>
      <span>${data.length} row${data.length !== 1 ? 's' : ''} · ${columns.length} column${columns.length !== 1 ? 's' : ''}</span>
    </div>
    <table class="bdata-data-table">
      <thead><tr>${columns.map(k => `<th>${escapeHtml(humanize(k))}</th>`).join('')}</tr></thead>
      <tbody>`;
  showRows.forEach(row => {
    html += `<tr>${columns.map(k => `<td>${escapeHtml(formatValue(row[k]))}</td>`).join('')}</tr>`;
  });
  html += `</tbody></table>`;
  if (remaining > 0) html += `<div class="bdata-table-more">+${remaining} more rows (showing first ${MAX_DISPLAY})</div>`;
  html += `</div>`;
  return html;
}

/* ============================================================
   CHART INTELLIGENCE ENGINE
   Analyzes data shape and selects the optimal chart type.
   ============================================================ */

/** Color palette for charts */
const CHART_PALETTE = [
  '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#06b6d4',
  '#84cc16', '#d946ef', '#0891b2', '#e11d48', '#7c3aed',
];

/** Columns that are identifiers / surrogate keys — never chart these */
const ID_PATTERN = /^id$|_id$|^pk$|^key$/i;

/**
 * Classify each column as 'numeric', 'categorical', 'temporal', or 'id'.
 * ID-like columns are tagged separately so charts can ignore them.
 */
function classifyColumns(data) {
  if (!data.length) return {};
  const keys = Object.keys(data[0]);
  const info = {};

  for (const k of keys) {
    /* Tag id-like columns first */
    if (ID_PATTERN.test(k)) { info[k] = 'id'; continue; }

    const sample = data.map(r => r[k]).filter(v => v != null);
    if (sample.length === 0) { info[k] = 'categorical'; continue; }

    const numCount = sample.filter(v => typeof v === 'number').length;
    if (numCount / sample.length > 0.8) { info[k] = 'numeric'; continue; }

    /* Check for temporal patterns (ISO dates, datetime strings) */
    const datePattern = /^\d{4}-\d{2}-\d{2}|^\d{2}[\/\-]\d{2}[\/\-]\d{2,4}/;
    const dateCount = sample.filter(v => typeof v === 'string' && datePattern.test(v)).length;
    if (dateCount / sample.length > 0.6) { info[k] = 'temporal'; continue; }

    /* Check if column name hints at time */
    const timeName = /date|time|created|updated|timestamp|month|year|day/i;
    if (timeName.test(k) && typeof sample[0] === 'string') { info[k] = 'temporal'; continue; }

    info[k] = 'categorical';
  }
  return info;
}

/** Helper: get chartable numeric columns (excludes id-like) */
function getChartableNumeric(colTypes) {
  return Object.keys(colTypes).filter(k => colTypes[k] === 'numeric');
}

/**
 * Infer the best chart type from data shape when backend doesn't suggest one.
 *
 *  - 1 categorical + 1 numeric → bar
 *  - 1 temporal + 1 numeric   → line
 *  - single row, single numeric → metric (no chart)
 *  - many numeric columns       → grouped bar
 *  - 2-6 categorical slices     → pie
 *  - no numeric columns         → table (no chart)
 */
function inferChartType(data, colTypes) {
  const numericCols  = getChartableNumeric(colTypes);
  const catCols      = Object.keys(colTypes).filter(k => colTypes[k] === 'categorical');
  const temporalCols = Object.keys(colTypes).filter(k => colTypes[k] === 'temporal');

  /* No chartable numeric data → skip chart */
  if (numericCols.length === 0) return 'none';

  /* Single-row aggregate (COUNT, SUM, AVG) → metric card */
  if (data.length === 1 && numericCols.length >= 1 && catCols.length === 0 && temporalCols.length === 0) return 'metric';

  /* Single-row with a category label + value (e.g. type: savings, total: 1200) → metric */
  if (data.length === 1 && numericCols.length === 1) return 'metric';

  /* Time series detected → line */
  if (temporalCols.length >= 1 && numericCols.length >= 1) return 'line';

  /* Small categorical + 1 numeric → pie if ≤6 rows, bar otherwise */
  if (catCols.length >= 1 && numericCols.length === 1) {
    return data.length <= 6 ? 'pie' : 'bar';
  }

  /* Multiple numeric columns → grouped bar */
  if (numericCols.length > 1) return 'bar';

  /* Only numeric columns, no label axis — still bar if >1 row */
  if (data.length > 1) return 'bar';

  return 'none';
}

/** Maximum rows sampled for chart rendering (keeps charts readable) */
const CHART_MAX_ROWS = 200;

/**
 * Build the chart / metric-card container HTML.
 * Returns '' only when truly no visualization is possible.
 */
function buildChartBlock(result) {
  if (!result || result.error) return '';
  const data = result.execution_result?.data ?? [];
  if (data.length === 0) return '';

  const colTypes = classifyColumns(data);
  const suggestion = result.chart_suggestion;
  const resolved = resolveChartType(suggestion, data, colTypes);

  /* ---------- Metric card for single-value results ---------- */
  if (resolved === 'metric') {
    return buildMetricCard(data, colTypes);
  }

  if (resolved === 'none' || resolved === 'table') return '';

  const id = 'chart-' + Math.random().toString(36).slice(2, 10);
  const chartLabel = resolved === 'doughnut' ? 'Doughnut' : resolved.charAt(0).toUpperCase() + resolved.slice(1);
  const rowNote = data.length > CHART_MAX_ROWS
    ? ` <span style="opacity:.6;font-size:.75rem">(showing top ${CHART_MAX_ROWS} of ${data.length} rows)</span>` : '';
  return `<div class="bdata-chart-wrap">
    <div class="bdata-chart-title-bar">
      <span class="material-symbols-outlined" style="font-size:1rem">bar_chart</span>
      <span>Data Visualization — ${chartLabel} Chart${rowNote}</span>
    </div>
    <canvas class="bdata-chart-canvas" id="${id}" height="280"></canvas>
  </div>`;
}

/**
 * Build a big-number metric card for single-value aggregates.
 */
function buildMetricCard(data, colTypes) {
  const row = data[0];
  const keys = Object.keys(row);
  const numericCols = getChartableNumeric(colTypes);
  const catCols = keys.filter(k => colTypes[k] === 'categorical');

  /* Pick the primary value (first chartable numeric column) */
  const valKey = numericCols[0] || keys[0];
  const rawVal = row[valKey];
  const displayVal = typeof rawVal === 'number'
    ? rawVal.toLocaleString(undefined, { maximumFractionDigits: 2 })
    : String(rawVal ?? '—');

  /* Optional label from a categorical column */
  const labelKey = catCols[0];
  const labelHtml = labelKey
    ? `<div class="metric-label">${escapeHtml(humanize(labelKey))}: ${escapeHtml(String(row[labelKey]))}</div>` : '';

  /* Additional stats (other numeric columns) */
  let extras = '';
  if (numericCols.length > 1) {
    extras = numericCols.slice(1).map(k =>
      `<div class="metric-extra"><span class="metric-extra-label">${escapeHtml(humanize(k))}</span>` +
      `<span class="metric-extra-val">${typeof row[k] === 'number' ? row[k].toLocaleString(undefined, { maximumFractionDigits: 2 }) : row[k]}</span></div>`
    ).join('');
  }

  return `<div class="bdata-metric-card">
    <div class="metric-icon"><span class="material-symbols-outlined">monitoring</span></div>
    <div class="metric-value">${displayVal}</div>
    <div class="metric-key">${escapeHtml(humanize(valKey))}</div>
    ${labelHtml}
    ${extras ? `<div class="metric-extras">${extras}</div>` : ''}
  </div>`;
}

/**
 * Resolve chart type: trust backend suggestion when valid, but
 * auto-upgrade 'table' to a chart when the data is chartable.
 */
function resolveChartType(suggestion, data, colTypes) {
  const chartTypes = ['bar', 'line', 'pie', 'doughnut'];

  /* Backend explicitly chose a chart → trust it */
  if (suggestion && chartTypes.includes(suggestion)) return suggestion;

  /* Backend said 'metric' → honour it */
  if (suggestion === 'metric') return 'metric';

  /* Backend said 'table' or gave nothing — try to auto-infer a chart.
     This is the key improvement: we always TRY to visualize. */
  const inferred = inferChartType(data, colTypes);
  return inferred;
}

/**
 * Render the Chart.js visualization onto a <canvas>.
 * Fully dynamic — no hardcoded columns or values.
 */
function renderChart(canvas, result) {
  if (typeof Chart === 'undefined') return;

  /* 1. Destroy existing chart instance to prevent memory leaks */
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();

  let data = result.execution_result?.data ?? [];
  if (data.length === 0) return;

  /* Sample down for large datasets to keep charts readable */
  if (data.length > CHART_MAX_ROWS) data = data.slice(0, CHART_MAX_ROWS);

  const colTypes = classifyColumns(data);
  const keys = Object.keys(data[0]);
  const numericCols  = getChartableNumeric(colTypes);
  const catCols      = keys.filter(k => colTypes[k] === 'categorical');
  const temporalCols = keys.filter(k => colTypes[k] === 'temporal');

  if (numericCols.length === 0) return; /* nothing to chart */

  /* 2. Resolve chart type */
  const type = resolveChartType(result.chart_suggestion, data, colTypes);
  if (type === 'none' || type === 'table' || type === 'metric') return;

  /* 3. Determine label axis (first temporal, then categorical, then first non-id/non-numeric key) */
  let labelKey = temporalCols[0] || catCols[0]
    || keys.find(k => colTypes[k] !== 'numeric' && colTypes[k] !== 'id')
    || keys[0];

  /* 4. Build labels */
  const labels = data.map(r => {
    const v = r[labelKey];
    if (v == null) return '—';
    if (typeof v === 'string' && v.length > 24) return v.slice(0, 21) + '…';
    return String(v);
  });

  /* 5. Build datasets — one per numeric column for grouped bar/line */
  const isPie = (type === 'pie' || type === 'doughnut');
  const datasets = numericCols.map((col, i) => ({
    label: humanize(col),
    data: data.map(r => Number(r[col]) || 0),
    backgroundColor: isPie
      ? CHART_PALETTE.slice(0, data.length)
      : CHART_PALETTE[i % CHART_PALETTE.length] + 'cc',
    borderColor: isPie
      ? '#ffffff'
      : CHART_PALETTE[i % CHART_PALETTE.length],
    borderWidth: isPie ? 2 : 2,
    borderRadius: type === 'bar' ? 6 : 0,
    tension: type === 'line' ? 0.3 : 0,
    fill: type === 'line' ? 'origin' : undefined,
    pointRadius: type === 'line' ? 3 : undefined,
    pointHoverRadius: type === 'line' ? 6 : undefined,
  }));

  /* For pie/doughnut, only use the first numeric column */
  const chartDatasets = isPie ? [datasets[0]] : datasets;

  /* 6. Create Chart.js instance */
  new Chart(canvas, {
    type,
    data: {
      labels,
      datasets: chartDatasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: 'index',
      },
      plugins: {
        legend: {
          display: isPie || datasets.length > 1,
          position: isPie ? 'bottom' : 'top',
          labels: {
            usePointStyle: true,
            padding: 16,
            font: { size: 12, family: 'Inter' },
          },
        },
        tooltip: {
          backgroundColor: '#1a2b3d',
          titleFont: { family: 'Inter', weight: '600' },
          bodyFont: { family: 'Inter' },
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: (ctx) => {
              const val = ctx.parsed.y ?? ctx.parsed;
              const formatted = typeof val === 'number' ? val.toLocaleString() : val;
              return ` ${ctx.dataset.label}: ${formatted}`;
            },
          },
        },
      },
      scales: isPie ? {} : {
        y: {
          beginAtZero: true,
          grid: { color: '#e2e8f0', drawBorder: false },
          ticks: {
            font: { size: 11, family: 'Inter' },
            callback: (v) => {
              if (typeof v !== 'number') return v;
              if (Math.abs(v) >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M';
              if (Math.abs(v) >= 1_000) return (v / 1_000).toFixed(0) + 'k';
              return v;
            },
          },
        },
        x: {
          grid: { display: false },
          ticks: {
            font: { size: 11, family: 'Inter' },
            maxRotation: 45,
          },
        },
      },
    },
  });
}

/* ============================================================
   PROGRESS INDICATOR
   ============================================================ */
let progressCounter = 0;

function showProgress() {
  const id = ++progressCounter;
  const div = document.createElement('div');
  div.className = 'msg-group ai';
  div.id = `progress-${id}`;
  div.innerHTML = `
    <div class="msg-label">
      <span class="material-symbols-outlined">smart_toy</span>
      <span class="msg-label-text">BData Assistant</span>
    </div>
    <div class="ai-content">
      <div class="progress-card">
        <div class="progress-top">
          <span class="progress-label">
            <span class="material-symbols-outlined">autorenew</span>
            <span class="progress-text">Analysing query…</span>
          </span>
          <span class="progress-pct">10%</span>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width:10%"></div></div>
        <div class="progress-hint">Routing through AI agents…</div>
      </div>
    </div>
  `;
  chatFeedEl.appendChild(div);
  scrollToBottom();
  return id;
}

function updateProgress(id, pct, hint) {
  const el = document.getElementById(`progress-${id}`);
  if (!el) return;
  const fill = el.querySelector('.progress-fill');
  const pctEl = el.querySelector('.progress-pct');
  const hintEl = el.querySelector('.progress-hint');
  const textEl = el.querySelector('.progress-text');
  if (fill) fill.style.width = pct + '%';
  if (pctEl) pctEl.textContent = pct + '%';
  if (hintEl) hintEl.textContent = hint;
  if (textEl) textEl.textContent = hint;
  scrollToBottom();
}

function removeProgress(id) {
  const el = document.getElementById(`progress-${id}`);
  if (el) el.remove();
}

/* ============================================================
   MINI MARKDOWN → HTML
   ============================================================ */
function renderMarkdown(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/_(.+?)_/g, '<em>$1</em>')
    .replace(/\n/g, '<br/>');
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function escapeAttr(str) {
  return str.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/* basic SQL syntax highlight */
function highlightSQL(sql) {
  const keywords = /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AND|OR|NOT|IN|AS|ORDER|BY|GROUP|HAVING|LIMIT|OFFSET|INSERT|UPDATE|DELETE|SET|VALUES|INTO|COUNT|SUM|AVG|MIN|MAX|ROUND|DESC|ASC|DISTINCT|CASE|WHEN|THEN|ELSE|END|WITH|UNION|ALL|EXISTS|BETWEEN|LIKE|IS|NULL)\b/gi;
  const escaped = escapeHtml(sql);
  return escaped.replace(keywords, '<span class="kw">$1</span>')
                .replace(/'([^']*)'/g, '<span class="str">\'$1\'</span>');
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    const el = document.getElementById('chat-messages');
    if (el) el.scrollTop = el.scrollHeight;
  });
}
