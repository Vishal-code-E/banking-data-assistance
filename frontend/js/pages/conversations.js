/* ============================================================
   CONVERSATIONS PAGE — Stitch AI
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
          Stitch AI can make mistakes. Always verify critical financial data.
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
        <span class="msg-label-text">Stitch AI</span>
      </div>
      <div class="ai-content">
        <div class="ai-text">
          <strong>Welcome to Stitch AI!</strong><br/>
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
      `Sorry, something went wrong:\n\n**${err.message}**\n\nPlease try again.`,
    );
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
        <span class="msg-label-text">Stitch AI</span>
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
    const canvas = group.querySelector('.stitch-chart-canvas');
    if (canvas && msg._result) renderChart(canvas, msg._result);
  }

  chatFeedEl.appendChild(group);
}

/* ============================================================
   DATA TABLE
   ============================================================ */
function buildDataTable(result) {
  if (!result || result.error) return '';
  const data = result.execution_result?.data ?? [];
  if (data.length === 0) return '';

  const keys = Object.keys(data[0]);
  const showRows = data.slice(0, 50);
  const remaining = data.length - showRows.length;

  let html = `<div class="stitch-data-table-wrap">
    <table class="stitch-data-table">
      <thead><tr>${keys.map(k => `<th>${escapeHtml(humanize(k))}</th>`).join('')}</tr></thead>
      <tbody>`;
  showRows.forEach(row => {
    html += `<tr>${keys.map(k => `<td>${escapeHtml(formatValue(row[k]))}</td>`).join('')}</tr>`;
  });
  html += `</tbody></table>`;
  if (remaining > 0) html += `<div class="stitch-table-more">+${remaining} more rows</div>`;
  html += `</div>`;
  return html;
}

/* ============================================================
   CHART BLOCK  (Chart.js — degrades gracefully)
   ============================================================ */
function buildChartBlock(result) {
  if (!result || result.error) return '';
  const suggestion = result.chart_suggestion;
  if (!suggestion || suggestion === 'none' || suggestion === 'table') return '';
  const data = result.execution_result?.data ?? [];
  if (data.length === 0 || data.length > 30) return '';

  const id = 'chart-' + Math.random().toString(36).slice(2, 10);
  return `<div class="stitch-chart-wrap">
    <canvas class="stitch-chart-canvas" id="${id}" height="260"></canvas>
  </div>`;
}

function renderChart(canvas, result) {
  if (typeof Chart === 'undefined') return;

  // Destroy any existing chart on this canvas to prevent memory leaks
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();

  const suggestion = result.chart_suggestion;
  const data = result.execution_result?.data ?? [];
  if (data.length === 0) return;

  const keys = Object.keys(data[0]);
  if (keys.length < 2) return;

  let labelKey = keys[0];
  let valueKey = keys[1];
  for (const k of keys) {
    if (typeof data[0][k] === 'string') { labelKey = k; break; }
  }
  for (const k of keys) {
    if (typeof data[0][k] === 'number') { valueKey = k; break; }
  }

  const labels = data.map(r => String(r[labelKey]));
  const values = data.map(r => Number(r[valueKey]) || 0);

  const palette = [
    '#1a2b3d', '#3b82f6', '#22c55e', '#f59e0b', '#ef4444',
    '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#6366f1',
  ];

  const type = suggestion === 'pie' ? 'pie'
    : suggestion === 'line' ? 'line'
    : 'bar';

  new Chart(canvas, {
    type,
    data: {
      labels,
      datasets: [{
        label: humanize(valueKey),
        data: values,
        backgroundColor: type === 'pie'
          ? palette.slice(0, values.length)
          : palette[0] + 'cc',
        borderColor: type === 'pie' ? '#fff' : palette[0],
        borderWidth: type === 'pie' ? 2 : 1,
        borderRadius: type === 'bar' ? 6 : 0,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: type === 'pie', position: 'bottom' },
      },
      scales: type === 'pie' ? {} : {
        y: { beginAtZero: true, grid: { color: '#e2e8f0' } },
        x: { grid: { display: false } },
      },
    }
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
      <span class="msg-label-text">Stitch AI</span>
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
