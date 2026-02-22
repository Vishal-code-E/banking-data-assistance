# Frontend — Single-Page Application

This document covers the frontend architecture, including the SPA shell, routing, API integration, chat interface, data table rendering, chart intelligence engine, and state management.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [File Structure](#file-structure)
3. [SPA Shell and Routing](#spa-shell-and-routing)
4. [API Service Layer](#api-service-layer)
5. [State Management](#state-management)
6. [Conversations Page — Chat Interface](#conversations-page--chat-interface)
7. [Query Routing](#query-routing)
8. [Response Rendering](#response-rendering)
9. [Data Tables](#data-tables)
10. [Chart Intelligence Engine](#chart-intelligence-engine)
11. [Metric Cards](#metric-cards)
12. [Progress Indicators](#progress-indicators)
13. [Other Pages](#other-pages)
14. [Dependencies](#dependencies)

---

## Architecture Overview

The frontend is a vanilla JavaScript single-page application with no build step. It uses ES modules (`import`/`export`) loaded via `<script type="module">`. All styling is in a single CSS file.

There is no framework dependency (no React, Vue, or Angular). The application renders pages by injecting HTML into a container element and attaching event listeners imperatively.

---

## File Structure

```
frontend/
├── index.html                 # SPA shell (sidebar, header, page container)
├── styles.css                 # All styles (~1100 lines)
└── js/
    ├── app.js                 # Router, sidebar navigation, bootstrap
    ├── api.js                 # HTTP client (fetch wrapper)
    ├── state.js               # In-memory reactive store
    └── pages/
        ├── conversations.js   # Chat UI, chart engine, table builder
        ├── dashboard.js       # Dashboard overview page
        ├── sql-editor.js      # Direct SQL query editor
        ├── history.js         # Session query history viewer
        └── datasources.js     # Schema/table explorer
```

---

## SPA Shell and Routing

**File:** `frontend/index.html` and `frontend/js/app.js`

The HTML shell defines:
- A **sidebar** with navigation items (`data-page` attributes).
- A **top header** with title, badge, share/help buttons, and export.
- A **page container** (`#page-container`) where page modules render content.
- A **mobile sidebar overlay** for responsive layouts.

### Routing

`app.js` defines a `pages` map that lazily imports page modules:

```javascript
const pages = {
  conversations: async (c) => { (await import('./pages/conversations.js')).render(c); },
  dashboard:     async (c) => { (await import('./pages/dashboard.js')).render(c); },
  'sql-editor':  async (c) => { (await import('./pages/sql-editor.js')).render(c); },
  history:       async (c) => { (await import('./pages/history.js')).render(c); },
  datasources:   async (c) => { (await import('./pages/datasources.js')).render(c); },
};
```

`navigateTo(pageId)` clears the container, updates the header title/badge, highlights the active nav item, and calls the page's `render(container)` function. The initial page defaults to `conversations`.

Each page module exports a single `render(container)` function that receives the DOM container element.

---

## API Service Layer

**File:** `frontend/js/api.js`

### Base URL resolution

`resolveApiBase()` determines the backend URL:

| Priority | Condition | URL |
|---|---|---|
| 1 | `window.__API_BASE` is set | Uses that value |
| 2 | Hostname ends with `.onrender.com` | `https://banking-data-assistance.onrender.com` |
| 3 | Fallback | `http://localhost:8001` |

### Request wrapper

`request(url, opts, timeoutMs)` wraps `fetch` with:
- **AbortController timeout** — defaults to 120 seconds to accommodate Render free-tier cold starts (30–60s).
- **JSON parsing** — all responses are parsed as JSON.
- **Error normalization** — non-OK responses throw with `detail`, `error`, or stringified body.
- **Timeout error message** — provides user-friendly guidance when the server is waking up.

### Exported functions

| Function | Method | Endpoint | Returns |
|---|---|---|---|
| `checkHealth()` | GET | `/health` | Health status object |
| `getTables()` | GET | `/tables` | Table list with columns |
| `getInfo()` | GET | `/info` | App info and features |
| `executeQuery(sql)` | POST | `/query` | `QueryResponse` |
| `askQuestion(query)` | POST | `/ask` | `QueryResponse` |

---

## State Management

**File:** `frontend/js/state.js`

A simple in-memory store with getter/setter functions. No reactivity system — components read state directly when they need it.

| State field | Type | Description |
|---|---|---|
| `currentPage` | `string` | Active page ID |
| `messages` | `Array` | Chat messages (`{ role, text, sql, timestamp }`) |
| `history` | `Array` | Query history (max 50, newest first) |
| `tablesCache` | `Object\|null` | Cached `/tables` response |
| `healthCache` | `Object\|null` | Cached `/health` response |

### Message structure

User messages:
```javascript
{ role: 'user', text: '...', timestamp: Date.now() }
```

AI messages:
```javascript
{ role: 'ai', text: '...', sql: '...', _result: {...}, timestamp: Date.now() }
```

The `_result` field stores the full `QueryResponse` from the backend. It is used by the bubble renderer to build tables and charts.

---

## Conversations Page — Chat Interface

**File:** `frontend/js/pages/conversations.js` (~806 lines)

This is the primary page of the application. It implements a ChatGPT-style interface where users type natural-language questions and receive AI-generated answers with tables and charts.

### Layout

```
┌─────────────────────────────────────┐
│          Chat Messages              │
│  ┌────────────────────────────────┐ │
│  │ User bubble                    │ │
│  │ AI bubble (text + SQL + table  │ │
│  │                  + chart)      │ │
│  └────────────────────────────────┘ │
├─────────────────────────────────────┤
│  [ + ] [  Ask about your data...  ] │
│           BData Assistant can make  │
│           mistakes.                 │
└─────────────────────────────────────┘
```

### Welcome state

When no messages exist, a welcome card is shown with four clickable suggestion buttons:
- "Show me all customers"
- "What is the total balance across all accounts?"
- "List recent transactions above $500"
- "How many accounts does each customer have?"

Clicking a suggestion populates the input and triggers `onSend()`.

---

## Query Routing

The `onSend()` function determines how to route the user's input:

```javascript
const isRawSQL = /^\s*(SELECT|WITH)\s/i.test(text);
```

| Input pattern | Route | Endpoint |
|---|---|---|
| Starts with `SELECT` or `WITH` | Direct SQL | `POST /query` |
| Everything else | Natural language | `POST /ask` |

This allows power users to write raw SQL while casual users ask questions in plain English. Both routes return the same `QueryResponse` contract.

---

## Response Rendering

### `buildProseResponse(question, result)`

Generates a markdown-formatted text description of the results:

| Condition | Output style |
|---|---|
| AI summary > 30 chars | Uses the AI summary directly |
| 0 rows | "No results" message |
| 1 row, 1 column | Single value highlight: "The result is **X**" |
| 1 row, multiple columns | Bulleted key-value list |
| 2–10 rows | Numbered list with all columns |
| >10 rows | First 5 rows + "and N more" + numeric column statistics (min, max, avg) |

### `appendBubble(msg)`

Renders a message into the chat feed. For AI messages, the bubble contains:

1. **Text** — Rendered via `renderMarkdown()` (bold, italic, line breaks).
2. **SQL block** — Syntax-highlighted with copy-to-clipboard button.
3. **Data table** — Built by `buildDataTable()`.
4. **Chart or metric card** — Built by `buildChartBlock()`, rendered by `renderChart()`.

### Helper functions

| Function | Purpose |
|---|---|
| `humanize(key)` | Converts `snake_case` to `Title Case` |
| `formatValue(v)` | Locale-aware number formatting (2 decimals for floats, commas for large integers) |
| `escapeHtml(str)` | XSS prevention via DOM `textContent` |
| `highlightSQL(sql)` | Regex-based keyword highlighting for SQL display |
| `renderMarkdown(text)` | Converts `**bold**` and `_italic_` to HTML |

---

## Data Tables

### `buildDataTable(result)`

Generates an HTML table from query results:

- Columns are derived dynamically from the first row's keys.
- Displays up to 100 rows. If more exist, shows a "+N more rows" footer.
- Shows a header bar with row count and column count.
- Handles empty results with a "No data returned" empty state.
- All values pass through `escapeHtml()` and `formatValue()`.

---

## Chart Intelligence Engine

The chart system uses a multi-step pipeline to decide what visualization to render and how to configure it.

### Step 1 — Column classification

`classifyColumns(data)` examines every column in the result set and assigns a type:

| Type | Detection criteria |
|---|---|
| `id` | Column name matches `/^id$\|_id$\|^pk$\|^key$/i` |
| `numeric` | >80% of non-null values are `typeof number` |
| `temporal` | >60% match ISO date patterns, or column name contains `date/time/created/updated/timestamp/month/year/day` |
| `categorical` | Everything else |

ID columns are **excluded from charting** to prevent nonsensical visualizations (e.g., a bar chart of primary key integers).

### Step 2 — Chart type inference

`inferChartType(data, colTypes)` uses data shape heuristics:

| Condition | Chart type |
|---|---|
| No chartable numeric columns | `none` |
| 1 row, only numeric columns (aggregate) | `metric` |
| 1 row, 1 numeric column | `metric` |
| Temporal + numeric columns | `line` |
| Categorical + 1 numeric, ≤6 rows | `pie` |
| Categorical + 1 numeric, >6 rows | `bar` |
| Multiple numeric columns | `bar` (grouped) |
| >1 row, only numeric | `bar` |
| Default | `none` |

### Step 3 — Type resolution

`resolveChartType(suggestion, data, colTypes)` merges the backend's suggestion with the frontend's inference:

| Backend says | Frontend action |
|---|---|
| `bar`, `line`, `pie`, `doughnut` | Trust backend |
| `metric` | Use metric card |
| `table`, `none`, or empty | Run `inferChartType()` and auto-upgrade if data is chartable |

This ensures charts appear even when the backend conservatively suggests "table" for data that has clear visual patterns.

### Step 4 — Chart rendering

`renderChart(canvas, result)` creates a Chart.js instance:

1. Destroys any existing chart on the canvas.
2. Samples data to `CHART_MAX_ROWS` (200) if larger.
3. Reclassifies columns and resolves chart type.
4. Selects the label axis: first temporal column, then first categorical, then first non-numeric/non-id column.
5. Builds one dataset per numeric column (grouped bar/line) or a single dataset (pie/doughnut).
6. Configures Chart.js options:
   - Y-axis: `beginAtZero`, tick formatting (k/M suffixes for large numbers).
   - X-axis: max rotation 45°, hidden gridlines.
   - Tooltips: dark background, locale-formatted numbers.
   - Legend: bottom for pie/doughnut, top for multi-dataset charts.
   - Line charts: `tension: 0.3`, `fill: 'origin'`, point radius 3/6.
   - Bar charts: `borderRadius: 6`.

### Color palette

15 colors are defined in `CHART_PALETTE`:
```
#3b82f6, #22c55e, #f59e0b, #ef4444, #8b5cf6,
#ec4899, #14b8a6, #f97316, #6366f1, #06b6d4,
#84cc16, #d946ef, #0891b2, #e11d48, #7c3aed
```

Pie/doughnut charts use one color per data point. Bar/line charts use one color per dataset with `cc` alpha suffix.

---

## Metric Cards

### `buildMetricCard(data, colTypes)`

For single-aggregate results (e.g., `COUNT(*)`, `AVG(balance)`), a gradient metric card is rendered instead of a chart:

```
┌──────────────────────────┐
│  [monitoring icon]       │
│       45,750.50          │  ← Primary numeric value
│     Total Balance        │  ← Column name, humanized
│  Avg: 1,234  Count: 37  │  ← Additional numeric columns
└──────────────────────────┘
```

The card selects:
- **Primary value:** First chartable numeric column.
- **Label:** First categorical column (if present).
- **Extras:** All remaining numeric columns.

Styled via `.bdata-metric-card` CSS with a gradient background (`#1a2b3d` → `#2d4a6f`).

---

## Progress Indicators

When a query is running, a progress card is shown in the chat feed:

1. `showProgress()` — Creates a card with a progress bar at 10% and "Analysing query..." text.
2. `updateProgress(id, pct, hint)` — Updates the bar percentage and hint text (e.g., 20% "AI is analysing your question...", 80% "Formatting results...").
3. `removeProgress(id)` — Removes the card when results arrive.

The progress bar is animated via CSS transitions. The percentage values are fixed checkpoints (10 → 20 → 80), not real-time measurements.

---

## Other Pages

| Page | File | Description |
|---|---|---|
| Dashboard | `dashboard.js` | Overview with health status, table counts |
| SQL Editor | `sql-editor.js` | Direct SQL input with syntax highlighting, executes via `/query` |
| History | `history.js` | Lists past queries from the session state (max 50) |
| Data Sources | `datasources.js` | Displays table schemas and column details from `/tables` |

These pages follow the same pattern: export a `render(container)` function that sets `innerHTML` and attaches event listeners.

---

## Dependencies

| Dependency | Version | Loaded via | Purpose |
|---|---|---|---|
| Chart.js | 4.4.7 | CDN (`chart.umd.min.js`) | All chart rendering |
| Inter font | — | Google Fonts | Primary typeface |
| Material Symbols Outlined | — | Google Fonts | Icon system |

No npm, no bundler, no build step. The application is served as static files.
