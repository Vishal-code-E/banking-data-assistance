/* ============================================================
   APP.JS — Stitch AI  (router, sidebar, bootstrap)
   ============================================================ */

import { setPage, getState } from './state.js';

/* page loaders (lazy) */
const pages = {
  conversations: async (c) => { (await import('./pages/conversations.js')).render(c); },
  dashboard:     async (c) => { (await import('./pages/dashboard.js')).render(c); },
  'sql-editor':  async (c) => { (await import('./pages/sql-editor.js')).render(c); },
  history:       async (c) => { (await import('./pages/history.js')).render(c); },
  datasources:   async (c) => { (await import('./pages/datasources.js')).render(c); },
};

/* header configs per page */
const headerConfig = {
  conversations: { title: 'Stitch AI Assistant', badge: 'Beta v1.0' },
  dashboard:     { title: 'Dashboard', badge: 'Overview' },
  'sql-editor':  { title: 'SQL Editor', badge: 'Interactive' },
  history:       { title: 'Query History', badge: 'Session' },
  datasources:   { title: 'Data Sources', badge: 'Schema' },
};

/* ============================================================
   BOOTSTRAP
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  const container   = document.getElementById('page-container');
  const headerTitle = document.getElementById('header-title');
  const headerBadge = document.getElementById('header-badge');
  const sidebar     = document.querySelector('.sidebar');
  const overlay     = document.getElementById('sidebar-overlay');
  const mobileBtn   = document.getElementById('mobile-menu-btn');
  const navItems    = document.querySelectorAll('.nav-item[data-page]');

  /* ---------- navigate to a page ---------- */
  async function navigateTo(pageId) {
    if (!pages[pageId]) return;
    setPage(pageId);

    /* update header */
    const cfg = headerConfig[pageId] || {};
    if (headerTitle) headerTitle.textContent = cfg.title || pageId;
    if (headerBadge) headerBadge.textContent = cfg.badge || '';

    /* highlight nav */
    navItems.forEach(n => {
      n.classList.toggle('active', n.dataset.page === pageId);
    });

    /* render page */
    container.innerHTML = '';
    try {
      await pages[pageId](container);
    } catch (e) {
      container.innerHTML = `<div style="padding:2rem;color:var(--red-500)">Failed to load page: ${e.message}</div>`;
      console.error(e);
    }

    /* close mobile sidebar */
    closeMobileSidebar();
  }

  /* ---------- sidebar nav clicks ---------- */
  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      navigateTo(item.dataset.page);
    });
  });

  /* ---------- mobile sidebar ---------- */
  function openMobileSidebar() {
    sidebar.classList.add('open');
    overlay.classList.add('show');
  }
  function closeMobileSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
  }

  if (mobileBtn) mobileBtn.addEventListener('click', openMobileSidebar);
  if (overlay)   overlay.addEventListener('click', closeMobileSidebar);

  /* ---------- initial page ---------- */
  navigateTo(getState().currentPage || 'conversations');

  /* expose for debugging */
  window.__stitch = { navigateTo };
});
