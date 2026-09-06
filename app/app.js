/**
 * CredEasy Web App
 *
 * Architecture:
 *   - Single-file ES module, no build step.
 *   - Hash router (#/dashboard, #/parties, etc.)
 *   - localStorage as primary store (offline-first, mirrors mobile app)
 *   - Cloud sync via /api/parties and /api/transactions backend endpoints
 *   - Google OAuth via Supabase JS client
 *
 * Auth flow:
 *   1. User clicks "Continue with Google"
 *   2. supabase.auth.signInWithOAuth({ provider: 'google' }) opens Google consent
 *   3. On return, supabase handles the code exchange automatically
 *   4. Session stored by supabase-js; onAuthStateChange fires → render dashboard
 */

// ── Config ─────────────────────────────────────────────────────────────────
// Read from window._env (set by the server / build) or fall back to the
// staging defaults. The anon key is safe to embed — RLS enforces access.
const _env = (typeof window !== 'undefined' && window._env) || {};
const SUPABASE_URL     = _env.SUPABASE_URL     || 'https://placeholder.supabase.co';
const SUPABASE_ANON_KEY = _env.SUPABASE_ANON_KEY || 'placeholder-anon-key';
const BACKEND_URL      = _env.BACKEND_URL      || 'http://localhost:8000';

const IS_CONFIGURED =
  SUPABASE_URL     !== 'https://placeholder.supabase.co' &&
  SUPABASE_ANON_KEY !== 'placeholder-anon-key';

// ── Supabase client ────────────────────────────────────────────────────────
let supabase = null;
if (IS_CONFIGURED && window.supabase?.createClient) {
  supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
}

// ── Store ───────────────────────────────────────────────────────────────────
/** localStorage keys */
const LS_SESSION  = 'credeasy.session';
const LS_PARTIES  = 'credeasy.parties';
const LS_TXS     = 'credeasy.transactions';
const LS_PROFILE = 'credeasy.profile';

const Store = {
  getParties: () => { try { return JSON.parse(localStorage.getItem(LS_PARTIES) || '[]'); } catch { return []; } },
  setParties: (p) => localStorage.setItem(LS_PARTIES, JSON.stringify(p)),

  getTxs: () => { try { return JSON.parse(localStorage.getItem(LS_TXS) || '[]'); } catch { return []; } },
  setTxs: (t) => localStorage.setItem(LS_TXS, JSON.stringify(t)),

  getProfile: () => {
    try { const p = JSON.parse(localStorage.getItem(LS_PROFILE) || '{}'); return p || {}; }
    catch { return {}; }
  },
  setProfile: (p) => localStorage.setItem(LS_PROFILE, JSON.stringify(p)),

  getSession: () => {
    try { return JSON.parse(localStorage.getItem(LS_SESSION) || 'null'); }
    catch { return null; }
  },
  setSession: (s) => localStorage.setItem(LS_SESSION, JSON.stringify(s)),
  clearSession: () => localStorage.removeItem(LS_SESSION),
};

/** Calculate current balance for a party from transactions + opening balance */
function partyBalance(party, txs) {
  const ptxs = txs.filter(t => t.partyId === party.id || t.party_id === party.id);
  const open = party.openingBalance ?? party.opening_balance ?? 0;
  const net = ptxs.reduce((sum, t) => {
    if (t.type === 'DEBIT' || t.type === 'GAVE') return sum + (t.amount ?? 0);
    if (t.type === 'CREDIT' || t.type === 'GOT') return sum - (t.amount ?? 0);
    return sum;
  }, 0);
  return open + net;
}

// ── API client ─────────────────────────────────────────────────────────────
async function apiFetch(path, { token, method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method, headers,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  return res.json();
}

async function syncToCloud(token) {
  if (!token) return;
  setSyncBadge('syncing');
  try {
    const parties = Store.getParties();
    const txs = Store.getTxs();
    for (const p of parties) {
      await apiFetch('/api/parties', { token, method: 'POST', body: p });
    }
    for (const t of txs) {
      await apiFetch('/api/transactions', { token, method: 'POST', body: t });
    }
    setSyncBadge('synced');
  } catch {
    setSyncBadge('offline');
  }
}

async function loadFromCloud(token) {
  if (!token) return;
  try {
    const [pData, tData] = await Promise.all([
      apiFetch('/api/parties', { token }),
      apiFetch('/api/transactions', { token }),
    ]);
    if (pData.parties?.length) Store.setParties(pData.parties);
    if (tData.transactions?.length) Store.setTxs(tData.transactions);
  } catch { /* offline — keep local data */ }
}

// ── Routing ──────────────────────────────────────────────────────────────────
const VALID_ROUTES = ['', 'dashboard', 'parties', 'add', 'reports', 'settings'];

function navigate(hash) {
  window.location.hash = hash.startsWith('#') ? hash : `#/${hash}`;
}

function currentRoute() {
  const h = window.location.hash.replace('#', '').replace(/^\//, '');
  return VALID_ROUTES.includes(h) ? h : 'dashboard';
}

// ── Auth ────────────────────────────────────────────────────────────────────
async function signInWithGoogle() {
  if (!IS_CONFIGURED || !supabase) {
    showError('login-error',
      'Authentication is not configured. Set window._env.SUPABASE_URL and ' +
      'window._env.SUPABASE_ANON_KEY before deploying.');
    return;
  }
  try {
    const webOrigin = _env.WEB_URL || window.location.origin;
    const redirectTo = `${webOrigin}${window.location.pathname}`;
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo, skipBrowserRedirect: false },
    });
    if (error) throw error;
    // On success Supabase navigates the page away and handles the redirect
  } catch (e) {
    showError('login-error', e.message ?? 'Sign-in failed. Please try again.');
  }
}

async function signOut() {
  if (supabase) await supabase.auth.signOut();
  Store.clearSession();
  Store.setParties([]);
  Store.setTxs([]);
  showPage('login');
  window.location.hash = '';
}

// ── UI helpers ───────────────────────────────────────────────────────────────
function showError(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.hidden = false;
}
function clearError(id) {
  const el = document.getElementById(id);
  if (el) { el.textContent = ''; el.hidden = true; }
}
function showToast(msg, type = 'info') {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.hidden = false;
  setTimeout(() => { el.hidden = true; }, 3000);
}
function showLoading(show = true) {
  document.getElementById('loading-overlay').hidden = !show;
}
function showPage(page) {
  document.getElementById('login-page').hidden = page !== 'login';
  document.getElementById('dashboard-page').hidden = page !== 'dashboard';
  // Footer visibility
  document.querySelector('.login-footer').hidden = page !== 'login';
}
function setSyncBadge(state) {
  const badge = document.getElementById('sync-badge');
  const label = document.getElementById('sync-label');
  if (!badge) return;
  badge.className = 'sync-badge' + (state === 'syncing' ? ' syncing' : '');
  if (label) label.textContent = state === 'syncing' ? 'Syncing…' : state === 'offline' ? 'Offline' : 'Synced';
}

// ── Formatters ───────────────────────────────────────────────────────────────
function fmt(n) {
  return '₹' + Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}
function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}
function initials(name = '') {
  return name.trim().split(/\s+/).map(w => w[0]?.toUpperCase() ?? '').slice(0, 2).join('');
}

// ── Render helpers ──────────────────────────────────────────────────────────
function renderPartyItem(party, balance) {
  const isGet = balance > 0; // positive = "they owe me"
  const typeLabel = party.type === 'SUPPLIER' ? 'Supplier' : 'Customer';
  const badgeClass = party.type === 'SUPPLIER' ? 'badge-supplier' : 'badge-customer';
  return `
    <div class="party-item" data-id="${party.id}" tabindex="0" role="button" aria-label="View ${party.name}">
      <div class="party-avatar">${initials(party.name)}</div>
      <div class="party-info">
        <div class="party-name">${escHtml(party.name)}</div>
        <div class="party-phone">${party.phone ? escHtml(party.phone) : typeLabel}</div>
      </div>
      <div>
        <div class="party-balance ${isGet ? 'get' : 'give'}">${isGet ? '+' : '−'}${fmt(balance)}</div>
        <div style="text-align:right"><span class="party-type-badge ${badgeClass}">${typeLabel}</span></div>
      </div>
    </div>`;
}

function escHtml(s = '') {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Dashboard view ──────────────────────────────────────────────────────────
function renderDashboard() {
  const parties = Store.getParties();
  const txs = Store.getTxs();
  const profile = Store.getProfile();

  // Update shop name
  const shopEl = document.getElementById('shop-name');
  if (shopEl) shopEl.textContent = profile.name || 'My Shop';
  const settingsName = document.getElementById('settings-name');
  if (settingsName) settingsName.textContent = profile.name || 'My Shop';

  // Summary
  let totalGet = 0, totalGive = 0, getCount = 0, giveCount = 0;
  parties.forEach(p => {
    const bal = partyBalance(p, txs);
    if (bal > 0) { totalGet += bal; getCount++; }
    else if (bal < 0) { totalGive += Math.abs(bal); giveCount++; }
  });
  document.getElementById('summary-get').textContent = fmt(totalGet);
  document.getElementById('summary-get-count').textContent = `${getCount} customer${getCount !== 1 ? 's' : ''}`;
  document.getElementById('summary-give').textContent = fmt(totalGive);
  document.getElementById('summary-give-count').textContent = `${giveCount} supplier${giveCount !== 1 ? 's' : ''}`;

  // Recent parties (sorted by last transaction)
  const recentList = document.getElementById('recent-parties-list');
  const emptyDash = document.getElementById('empty-dashboard');
  if (parties.length === 0) {
    recentList.innerHTML = '';
    emptyDash.hidden = false;
  } else {
    emptyDash.hidden = true;
    const sorted = [...parties].sort((a, b) => {
      const aLast = txs.filter(t => t.partyId === a.id || t.party_id === a.id).sort((x,y) => new Date(y.date) - new Date(x.date))[0];
      const bLast = txs.filter(t => t.partyId === b.id || t.party_id === b.id).sort((x,y) => new Date(y.date) - new Date(x.date))[0];
      return new Date(bLast?.date ?? 0) - new Date(aLast?.date ?? 0);
    }).slice(0, 5);
    recentList.innerHTML = sorted.map(p => renderPartyItem(p, partyBalance(p, txs))).join('');
  }
}

// ── Parties view ─────────────────────────────────────────────────────────────
function renderParties() {
  const parties = Store.getParties();
  const txs = Store.getTxs();
  const searchEl = document.getElementById('party-search');
  const query = (searchEl?.value ?? '').toLowerCase().trim();
  const filtered = parties.filter(p =>
    !query || p.name.toLowerCase().includes(query) || (p.phone ?? '').includes(query)
  );
  const list = document.getElementById('all-parties-list');
  const empty = document.getElementById('empty-parties');

  if (filtered.length === 0) {
    list.innerHTML = '';
    empty.hidden = false;
  } else {
    empty.hidden = true;
    list.innerHTML = filtered.map(p => renderPartyItem(p, partyBalance(p, txs))).join('');
  }

  // Populate party dropdown in add transaction form
  const select = document.getElementById('tx-party');
  if (select) {
    const current = select.value;
    select.innerHTML = '<option value="">Select party…</option>' +
      parties.map(p => `<option value="${p.id}">${escHtml(p.name)}${p.phone ? ` · ${p.phone}` : ''}</option>`).join('');
    if (current && [...select.options].some(o => o.value === current)) select.value = current;
  }
}

// ── Reports view ─────────────────────────────────────────────────────────────
function renderReports() {
  // Summary report: show totals
  const parties = Store.getParties();
  const txs = Store.getTxs();
  let totalGet = 0, totalGive = 0;
  parties.forEach(p => {
    const bal = partyBalance(p, txs);
    if (bal > 0) totalGet += bal;
    else if (bal < 0) totalGive += Math.abs(bal);
  });
  // Reports view is static for now — more charts coming soon
  console.info('[Reports] Get:', fmt(totalGet), 'Give:', fmt(totalGive));
}

// ── Settings view ─────────────────────────────────────────────────────────────
function renderSettings(user) {
  const emailEl = document.getElementById('settings-email');
  if (emailEl) emailEl.textContent = user?.email ?? '—';
}

// ── Tab navigation ────────────────────────────────────────────────────────────
function activateTab(tabName) {
  document.querySelectorAll('.tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabName);
    t.setAttribute('aria-selected', t.dataset.tab === tabName);
  });
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  const panel = document.getElementById(`view-${tabName}`);
  if (panel) panel.classList.add('active');
}

// ── Transaction form ────────────────────────────────────────────────────────
let txFormType = 'GAVE';

function setupTxForm() {
  const form = document.getElementById('tx-form');
  if (!form) return;
  form.addEventListener('submit', async e => {
    e.preventDefault();
    clearError('tx-error');

    const partyId = document.getElementById('tx-party').value;
    const amount  = parseFloat(document.getElementById('tx-amount').value);
    const note    = document.getElementById('tx-note').value.trim();
    const date    = document.getElementById('tx-date').value || new Date().toISOString().split('T')[0];

    if (!partyId) { showError('tx-error', 'Please select a party.'); return; }
    if (!amount || amount <= 0) { showError('tx-error', 'Please enter a valid amount.'); return; }

    const session = Store.getSession();
    const tx = {
      id: crypto.randomUUID(),
      partyId: partyId,
      amount,
      type: txFormType,   // 'GAVE' or 'GOT'
      note,
      date,
      syncStatus: 'PENDING',
    };

    const txs = Store.getTxs();
    txs.unshift(tx);
    Store.setTxs(txs);

    form.reset();
    document.getElementById('tx-date').value = new Date().toISOString().split('T')[0];
    showToast('Transaction saved ✓');
    renderDashboard();
    renderParties();

    // Sync to cloud in background
    if (session?.access_token) syncToCloud(session.access_token);
  });

  document.getElementById('btn-gave').addEventListener('click', () => {
    txFormType = 'GAVE';
    document.getElementById('btn-gave').className = 'toggle-btn active';
    document.getElementById('btn-got').className   = 'toggle-btn';
  });
  document.getElementById('btn-got').addEventListener('click', () => {
    txFormType = 'GOT';
    document.getElementById('btn-got').className   = 'toggle-btn active';
    document.getElementById('btn-gave').className = 'toggle-btn';
  });
}

// ── Party modal ──────────────────────────────────────────────────────────────
let partyFormType = 'CUSTOMER';

function setupPartyModal() {
  const modal    = document.getElementById('party-modal');
  const form     = document.getElementById('party-form');
  const backdrop = document.getElementById('modal-backdrop');
  const closeBtn = document.getElementById('modal-close');
  const cancelBtn= document.getElementById('btn-cancel-party');

  function openModal() {
    modal.hidden = false;
    document.getElementById('party-name').focus();
    clearError('party-error');
    form.reset();
    document.getElementById('party-balance').value = '0';
    document.getElementById('btn-type-customer').className = 'toggle-btn active';
    document.getElementById('btn-type-supplier').className  = 'toggle-btn';
    partyFormType = 'CUSTOMER';
  }
  function closeModal() {
    modal.hidden = true;
    form.reset();
  }

  document.getElementById('btn-add-party')?.addEventListener('click', openModal);
  document.getElementById('btn-new-party')?.addEventListener('click', () => {
    activateTab('parties');
    setTimeout(openModal, 50);
  });
  backdrop?.addEventListener('click', closeModal);
  closeBtn?.addEventListener('click', closeModal);
  cancelBtn?.addEventListener('click', closeModal);

  document.getElementById('btn-type-customer').addEventListener('click', () => {
    partyFormType = 'CUSTOMER';
    document.getElementById('btn-type-customer').className = 'toggle-btn active';
    document.getElementById('btn-type-supplier').className  = 'toggle-btn';
  });
  document.getElementById('btn-type-supplier').addEventListener('click', () => {
    partyFormType = 'SUPPLIER';
    document.getElementById('btn-type-supplier').className = 'toggle-btn active';
    document.getElementById('btn-type-customer').className  = 'toggle-btn';
  });

  form?.addEventListener('submit', e => {
    e.preventDefault();
    clearError('party-error');

    const name    = document.getElementById('party-name').value.trim();
    const phone   = document.getElementById('party-phone').value.trim();
    const balance = parseFloat(document.getElementById('party-balance').value) || 0;

    if (!name) { showError('party-error', 'Name is required.'); return; }

    const party = {
      id: crypto.randomUUID(),
      name,
      phone,
      type: partyFormType,
      openingBalance: balance,
      createdAt: new Date().toISOString(),
    };

    const parties = Store.getParties();
    parties.unshift(party);
    Store.setParties(parties);

    closeModal();
    showToast('Party added ✓');
    renderParties();
    renderDashboard();

    // Sync in background
    const session = Store.getSession();
    if (session?.access_token) syncToCloud(session.access_token);
  });
}

// ── Carousel ────────────────────────────────────────────────────────────────
let carouselIndex = 0;
let carouselTimer = null;

function setupCarousel() {
  const slides = document.querySelectorAll('.carousel-slide');
  const dots   = document.querySelectorAll('.carousel-dots .dot');
  if (!slides.length) return;

  function goTo(i) {
    slides[carouselIndex]?.classList.remove('active');
    dots[carouselIndex]?.classList.remove('active');
    dots[carouselIndex]?.setAttribute('aria-selected', 'false');
    carouselIndex = ((i % slides.length) + slides.length) % slides.length;
    slides[carouselIndex]?.classList.add('active');
    dots[carouselIndex]?.classList.add('active');
    dots[carouselIndex]?.setAttribute('aria-selected', 'true');
  }

  function advance() { goTo(carouselIndex + 1); }

  dots.forEach((dot, i) => dot.addEventListener('click', () => {
    goTo(i);
    clearInterval(carouselTimer);
    carouselTimer = setInterval(advance, 4000);
  }));

  carouselTimer = setInterval(advance, 4000);
}

// ── Main init ────────────────────────────────────────────────────────────────
function init() {
  // Show loading while we check session
  showLoading(true);

  // ── Tab navigation ────────────────────────────────────────
  document.querySelectorAll('.tab-nav .tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const route = tab.dataset.tab;
      activateTab(route);
      window.location.hash = `#/${route}`;

      // Render view content on switch
      if (route === 'parties') renderParties();
      else if (route === 'reports') renderReports();
    });
  });

  // ── Google sign in ───────────────────────────────────────
  document.getElementById('btn-google')?.addEventListener('click', signInWithGoogle);
  document.getElementById('btn-signout')?.addEventListener('click', signOut);
  document.getElementById('btn-signout-settings')?.addEventListener('click', signOut);

  // ── View all parties ──────────────────────────────────────
  document.getElementById('btn-view-all-parties')?.addEventListener('click', () => {
    activateTab('parties');
    window.location.hash = '#/parties';
    renderParties();
  });

  // ── Party search ──────────────────────────────────────────
  document.getElementById('party-search')?.addEventListener('input', renderParties);

  // ── Edit shop name ────────────────────────────────────────
  document.getElementById('btn-edit-name')?.addEventListener('click', () => {
    const profile = Store.getProfile();
    const newName = prompt('Business name:', profile.name || 'My Shop');
    if (newName !== null) {
      profile.name = newName.trim() || 'My Shop';
      Store.setProfile(profile);
      renderDashboard();
    }
  });

  // ── Report cards ──────────────────────────────────────────
  document.getElementById('btn-report-summary')?.addEventListener('click', () => {
    showToast('Summary: see Dashboard tab →');
    activateTab('dashboard');
  });
  document.getElementById('btn-report-customer')?.addEventListener('click', () => {
    showToast('Select a party from Parties tab →');
    activateTab('parties');
  });
  document.getElementById('btn-report-pdf')?.addEventListener('click', () => {
    showToast('PDF export coming soon');
  });

  // ── Carousel ──────────────────────────────────────────────
  setupCarousel();

  // ── Forms ─────────────────────────────────────────────────
  setupTxForm();
  setupPartyModal();

  // ── Hash router ───────────────────────────────────────────
  window.addEventListener('hashchange', () => {
    const route = currentRoute();
    if (document.getElementById('dashboard-page').hidden === false) {
      activateTab(route);
      if (route === 'parties') renderParties();
      else if (route === 'reports') renderReports();
    }
  });

  // ── Auth state listener ───────────────────────────────────
  if (supabase) {
    supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session) {
        Store.setSession({
          access_token: session.access_token,
          refresh_token: session.refresh_token,
          user: session.user,
        });

        // Load from cloud first
        await loadFromCloud(session.access_token);

        // Set default date for transaction form
        document.getElementById('tx-date').value = new Date().toISOString().split('T')[0];

        // Render
        showPage('dashboard');
        renderDashboard();
        renderParties();
        renderSettings(session.user);
        setSyncBadge('synced');

        // Sync on login
        syncToCloud(session.access_token);

      } else if (event === 'SIGNED_OUT') {
        Store.clearSession();
        showPage('login');
      }
    });

    // Check existing session on load
    const { data: { session } } = await supabase.auth.getSession();
    if (session) {
      Store.setSession({
        access_token: session.access_token,
        refresh_token: session.refresh_token,
        user: session.user,
      });
      document.getElementById('tx-date').value = new Date().toISOString().split('T')[0];
      showPage('dashboard');
      await loadFromCloud(session.access_token);
      renderDashboard();
      renderParties();
      renderSettings(session.user);
      setSyncBadge('synced');

      // Restore tab from hash
      const route = currentRoute();
      activateTab(route);
    } else {
      showPage('login');
    }
  } else {
    // Supabase not loaded — show a useful message
    document.getElementById('btn-google').disabled = true;
    document.getElementById('btn-google').textContent = 'Auth not available (check config)';
    showPage('login');
  }

  showLoading(false);
}

// Boot when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
