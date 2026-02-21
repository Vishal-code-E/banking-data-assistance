/* ============================================================
   CONVERSATIONS PAGE — Stitch AI
   ChatGPT-style conversational interface.
   User types a natural-language question → we send SQL →
   backend returns data → we display an AI prose summary.
   ============================================================ */

import { executeQuery, getTables } from '../api.js';
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
   SEND HANDLER
   ============================================================ */
async function onSend() {
  const text = inputEl.value.trim();
  if (!text) return;

  inputEl.value = '';

  /* clear welcome on first message */
  if (getMessages().length === 0) chatFeedEl.innerHTML = '';

  /* user bubble */
  const userMsg = addUserMessage(text);
  appendBubble(userMsg);
  scrollToBottom();

  /* show progress */
  const progressId = showProgress();

  try {
    /* determine SQL from user question */
    const sql = await naturalLanguageToSQL(text);

    updateProgress(progressId, 40, 'Validating query…');

    /* execute through backend */
    const result = await executeQuery(sql);

    updateProgress(progressId, 80, 'Formatting results…');

    /* record history */
    addHistory({
      sql: result.validated_sql || sql,
      rowCount: result.execution_result?.row_count ?? 0,
      execTime: result.execution_result?.execution_time_ms ?? 0,
      error: result.error,
    });

    removeProgress(progressId);

    if (result.error) {
      const aiMsg = addAIMessage(
        `I encountered an issue running that query:\n\n**${result.error}**\n\nCould you rephrase or try a different question?`,
        result.validated_sql || sql,
      );
      appendBubble(aiMsg);
    } else {
      const prose = buildProseResponse(text, result);
      const aiMsg = addAIMessage(prose, result.validated_sql || sql);
      appendBubble(aiMsg);
    }
  } catch (err) {
    removeProgress(progressId);
    const aiMsg = addAIMessage(
      `Sorry, something went wrong while processing your request:\n\n**${err.message}**\n\nPlease try again.`,
    );
    appendBubble(aiMsg);
  }

  scrollToBottom();
}

/* ============================================================
   NATURAL LANGUAGE → SQL  (simple client-side mapping)
   ============================================================ */
async function naturalLanguageToSQL(question) {
  /* Make sure we have table info */
  let tables = getTablesCache();
  if (!tables) {
    const data = await getTables();
    tables = data.tables || data;
    setTablesCache(tables);
  }

  const q = question.toLowerCase();

  /* ----- customer queries ----- */
  if (/all\s+customers|show.*customers|list.*customers/.test(q)) {
    return 'SELECT * FROM customers';
  }
  if (/how\s+many\s+customers|customer\s+count|count.*customers/.test(q)) {
    return 'SELECT COUNT(*) AS customer_count FROM customers';
  }

  /* ----- account queries ----- */
  if (/total\s+balance|sum.*balance/.test(q)) {
    return 'SELECT SUM(balance) AS total_balance FROM accounts';
  }
  if (/all\s+accounts|show.*accounts|list.*accounts/.test(q)) {
    return 'SELECT * FROM accounts';
  }
  if (/how\s+many\s+accounts.*each|accounts.*per\s+customer/.test(q)) {
    return `SELECT c.name, COUNT(a.id) AS account_count
FROM customers c
LEFT JOIN accounts a ON a.customer_id = c.id
GROUP BY c.id, c.name
ORDER BY account_count DESC`;
  }
  if (/how\s+many\s+accounts|account\s+count|count.*accounts/.test(q)) {
    return 'SELECT COUNT(*) AS account_count FROM accounts';
  }
  if (/average\s+balance|avg.*balance|mean.*balance/.test(q)) {
    return 'SELECT ROUND(AVG(balance), 2) AS average_balance FROM accounts';
  }
  if (/highest\s+balance|max.*balance|largest\s+balance|top\s+balance/.test(q)) {
    return `SELECT a.*, c.name AS customer_name
FROM accounts a
JOIN customers c ON c.id = a.customer_id
ORDER BY a.balance DESC LIMIT 5`;
  }
  if (/lowest\s+balance|min.*balance|smallest\s+balance/.test(q)) {
    return `SELECT a.*, c.name AS customer_name
FROM accounts a
JOIN customers c ON c.id = a.customer_id
ORDER BY a.balance ASC LIMIT 5`;
  }

  /* ----- transaction queries ----- */
  if (/recent\s+transactions|latest\s+transactions/.test(q)) {
    const amountMatch = q.match(/above\s+\$?(\d+)|over\s+\$?(\d+)|more\s+than\s+\$?(\d+)/);
    const threshold = amountMatch ? (amountMatch[1] || amountMatch[2] || amountMatch[3]) : null;
    if (threshold) {
      return `SELECT t.*, a.account_number
FROM transactions t
JOIN accounts a ON a.id = t.account_id
WHERE t.amount > ${threshold}
ORDER BY t.created_at DESC LIMIT 20`;
    }
    return `SELECT t.*, a.account_number
FROM transactions t
JOIN accounts a ON a.id = t.account_id
ORDER BY t.created_at DESC LIMIT 20`;
  }
  if (/transactions?\s+above|transactions?\s+over|transactions?\s+more\s+than/.test(q)) {
    const amountMatch = q.match(/\$?(\d+)/);
    const threshold = amountMatch ? amountMatch[1] : '500';
    return `SELECT t.*, a.account_number
FROM transactions t
JOIN accounts a ON a.id = t.account_id
WHERE t.amount > ${threshold}
ORDER BY t.amount DESC`;
  }
  if (/all\s+transactions|show.*transactions|list.*transactions/.test(q)) {
    return 'SELECT * FROM transactions ORDER BY created_at DESC LIMIT 50';
  }
  if (/how\s+many\s+transactions|transaction\s+count|count.*transactions/.test(q)) {
    return 'SELECT COUNT(*) AS transaction_count FROM transactions';
  }
  if (/total.*transaction.*amount|sum.*transaction/.test(q)) {
    return 'SELECT SUM(amount) AS total_amount FROM transactions';
  }
  if (/transaction.*type|type.*transaction|deposit.*withdraw/.test(q)) {
    return `SELECT type, COUNT(*) AS count, SUM(amount) AS total_amount
FROM transactions GROUP BY type`;
  }

  /* ----- joined / complex ----- */
  if (/customer.*transaction|transaction.*customer/.test(q)) {
    return `SELECT c.name, COUNT(t.id) AS txn_count, SUM(t.amount) AS total_amount
FROM customers c
JOIN accounts a ON a.customer_id = c.id
JOIN transactions t ON t.account_id = a.id
GROUP BY c.id, c.name
ORDER BY total_amount DESC`;
  }

  /* ----- fallback: if it looks like raw SQL, pass through ----- */
  if (/^\s*(select|insert|update|delete|with)\s/i.test(question)) {
    return question.trim();
  }

  /* ----- ultimate fallback ----- */
  return `SELECT * FROM customers LIMIT 10`;
}

/* ============================================================
   BUILD PROSE RESPONSE  (convert raw data → natural text)
   ============================================================ */
function buildProseResponse(question, result) {
  const { execution_result, summary } = result;
  const data = execution_result?.data ?? [];
  const rowCount = execution_result?.row_count ?? 0;
  const execTime = execution_result?.execution_time_ms ?? 0;

  /* If the backend already provides a summary, prefer it */
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

function timeAgo(ts) {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return new Date(ts).toLocaleDateString();
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
    /* AI */
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

    group.innerHTML = `
      <div class="msg-label">
        <span class="material-symbols-outlined">smart_toy</span>
        <span class="msg-label-text">Stitch AI</span>
      </div>
      <div class="ai-content">
        <div class="ai-text">${renderMarkdown(msg.text)}</div>
        ${sqlBlock}
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
  }

  chatFeedEl.appendChild(group);
}

/* ============================================================
   PROGRESS INDICATOR (fake pipeline progress)
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
        <div class="progress-hint">Generating SQL from your question…</div>
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
