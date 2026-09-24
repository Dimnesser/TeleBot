/* BrainCore Mini App — vanilla JS SPA, без сборки/зависимостей. */

const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  if (tg.setHeaderColor) try { tg.setHeaderColor('#05070c'); } catch (e) {}
  if (tg.setBackgroundColor) try { tg.setBackgroundColor('#05070c'); } catch (e) {}
}

// Диагностическая страховка: любая необработанная ошибка/rejection раньше
// просто вешала экран молча ("не открывается") — теперь хотя бы видно, что
// именно сломалось, вместо тишины.
window.addEventListener('error', (e) => {
  // «Script error.» без подробностей — ошибка из чужого скрипта (SDK Telegram,
  // шрифты): браузер прячет её текст, и нашему коду она не мешает.
  if (!e.filename || /^Script error\.?$/.test(e.message || '')) { console.warn('cross-origin error', e); return; }
  try { toast('Ошибка интерфейса: ' + (e.message || 'см. консоль'), 'error'); } catch (_) {}
});
window.addEventListener('unhandledrejection', (e) => {
  try { toast('Ошибка запроса: ' + (e.reason && e.reason.message || e.reason || 'см. консоль'), 'error'); } catch (_) {}
});

const DEV_ID_KEY = 'bb_dev_tg_id';

const RARITY_ORDER = ['common', 'rare', 'epic', 'legendary', 'mythic', 'brainrot_god', 'secret', 'og'];
const haptic = {
  tick() { try { tg && tg.HapticFeedback && tg.HapticFeedback.selectionChanged(); } catch (e) {} },
  impact(style = 'medium') { try { tg && tg.HapticFeedback && tg.HapticFeedback.impactOccurred(style); } catch (e) {} },
  success() { try { tg && tg.HapticFeedback && tg.HapticFeedback.notificationOccurred('success'); } catch (e) {} },
};
const fmt = (n) => Number(n).toLocaleString('ru-RU');

// ------------------------------------------------------------------- API

async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json' };
  let url = path;
  if (tg && tg.initData) {
    headers['Authorization'] = 'tma ' + tg.initData;
  } else {
    let devId = localStorage.getItem(DEV_ID_KEY);
    if (!devId) {
      devId = window.prompt('Dev-режим (не открыто из Telegram): введи любой числовой id для теста') || '1';
      localStorage.setItem(DEV_ID_KEY, devId);
    }
    url += (path.includes('?') ? '&' : '?') + 'dev_tg_id=' + encodeURIComponent(devId);
  }
  const res = await fetch(url, { ...opts, headers });
  let body = null;
  try { body = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) {
    const err = new Error((body && (body.message || body.error)) || 'request_failed');
    err.body = body; // код ошибки и данные (например, канал для подписки)
    throw err;
  }
  return body;
}

// ------------------------------------------------------------------- utils

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* Ценностная подсветка: все брейнроты в кейсах — Secret/OG (реальный тир
 * показывается текстом), а цвет свечения зависит от их ценности — чтобы
 * лента и сетки читались с одного взгляда. Тир НЕ выдумывается. */
const VALUE_BANDS = [
  [10000, '#ffd84d', '#ff4fd8'],
  [2500, '#ff5d7a', '#b3124a'],
  [800, '#b17aff', '#5b2bb5'],
  [250, '#43c6ff', '#1c5fae'],
  [0, '#c9d1e4', '#5d667a'],
];
function valueBand(value) {
  return VALUE_BANDS.find(([min]) => value >= min);
}
function glowVars(b) {
  const [, c1, c2] = valueBand(b.value || 0);
  return `--rc:${c1};--rca:${c2}`;
}
/* Цвет плитки дропа относительно цены кейса: серый — дешевле половины
 * цены, синий — почти окуп, фиолетовый — окуп, красный — ×3, золото — ×10. */
const REL_BANDS = [[10, '#ffc93c'], [3, '#ff4d6d'], [1, '#a66bff'], [0.5, '#3d8bff'], [0, '#5d6a86']];
function relColor(value, price) {
  const k = value / Math.max(price, 5);
  return REL_BANDS.find(([min]) => k >= min)[1];
}

/** Официальный рендер брейнрота (из вики, см. webapp/static/assets/brainrots).
 * Если ассета нет — честный плейсхолдер, никакой подменной картинки. */
function brainrotArt(b, sizeClass = '') {
  if (b.coins) return `<div class="p-tile is-coins ${sizeClass}" style="${glowVars(b)}">${COIN_SVG}</div>`;
  const img = b.image_url
    ? `<img src="${b.image_url}" alt="${escapeHtml(b.name)}" loading="lazy" draggable="false">`
    : '<span class="p-tile-missing">нет ассета</span>';
  return `<div class="p-tile ${b.rarity === 'og' ? 'is-og' : ''} ${sizeClass}" style="${glowVars(b)}">${img}</div>`;
}

function rarityBadge(b) {
  return `<span class="tier-badge tier-${b.rarity}">${escapeHtml(b.rarity_label || '?')}</span>`;
}

// ------------------------------------------------------------------- toast

function toast(message, kind = 'info') {
  const root = document.getElementById('toast-root');
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.remove(), 2800);
}

// ------------------------------------------------------------------- modal

function openModal(innerHtml) {
  closeModal();
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'active-modal';
  overlay.innerHTML = `<div class="modal-sheet">${innerHtml}</div>`;
  overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });
  document.getElementById('modal-root').appendChild(overlay);
  return overlay;
}
function closeModal() {
  const existing = document.getElementById('active-modal');
  if (existing) existing.remove();
}

// ------------------------------------------------------------------- state

let ME = null;

function popNumber(el) {
  if (!el) return;
  el.classList.remove('num-pop');
  void el.offsetWidth; // restart animation
  el.classList.add('num-pop');
}

async function refreshMe() {
  const prevTokens = ME ? ME.balance : null;
  ME = await api('/api/me');
  document.getElementById('drawer-username').textContent = ME.username ? '@' + ME.username : (ME.first_name || 'игрок');
  const drawerAvatar = document.getElementById('drawer-avatar');
  if (drawerAvatar && !drawerAvatar.dataset.ready) { drawerAvatar.outerHTML = avatarHtml(ME).replace('class="avatar ', 'id="drawer-avatar" data-ready="1" class="avatar '); }
  document.getElementById('drawer-balance').textContent = ME.balance;
  const topBalance = document.getElementById('topbar-tokens');
  if (topBalance) {
    topBalance.textContent = ME.balance;
    if (prevTokens !== null && prevTokens !== ME.balance) popNumber(topBalance);
  }
  return ME;
}

// ------------------------------------------------------------------- drawer

// Линейные иконки 24×24 (stroke = currentColor) — вместо эмодзи в меню.
const ICONS = {
  home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h5v-6h4v6h5V9.5"/>',
  deposit: '<rect x="3" y="6" width="18" height="14" rx="3"/><path d="M3 10h18"/><path d="M16 15h2"/><path d="M7 6V4.5h10V6"/>',
  upgrader: '<path d="M12 20V6"/><path d="m6 12 6-6 6 6"/><path d="M5 3h14"/>',
  battle: '<path d="M14.5 4H20v5.5L9 20.5 3.5 15z"/><path d="m7 13 4 4"/><path d="M3 21l2.5-2.5"/>',
  dice: '<rect x="3" y="3" width="18" height="18" rx="4"/><circle cx="8.5" cy="8.5" r="1.2" fill="currentColor"/><circle cx="15.5" cy="15.5" r="1.2" fill="currentColor"/><circle cx="15.5" cy="8.5" r="1.2" fill="currentColor"/><circle cx="8.5" cy="15.5" r="1.2" fill="currentColor"/>',
  crash: '<path d="M3 20c7 0 12-5 16-15"/><path d="M14 5h5v5"/><path d="M3 20h18"/>',
  inventory: '<path d="M5 9a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v12H5z"/><path d="M9 5V3h6v2"/><path d="M9 13h6"/>',
  quests: '<path d="M10 6h10M10 12h10M10 18h10"/><path d="m4 6 1.5 1.5L8 5M4 12l1.5 1.5L8 11M4 18l1.5 1.5L8 17"/>',
  giveaways: '<path d="M8 21h8M12 16v5"/><path d="M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/>',
  support: '<path d="M4 13v-1a8 8 0 0 1 16 0v1"/><rect x="3" y="13" width="4" height="6" rx="1.5"/><rect x="17" y="13" width="4" height="6" rx="1.5"/><path d="M19 19c0 1.5-2 2.5-5 2.5"/>',
  faq: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6"/><circle cx="12" cy="17.2" r=".9" fill="currentColor"/>',
  bonuses: '<rect x="3" y="8" width="18" height="13" rx="2"/><path d="M3 12h18M12 8v13"/><path d="M12 8S8.5 3 7 5.5 12 8 12 8zM12 8s3.5-5 5-2.5S12 8 12 8z"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h10"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  withdraw: '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 17v2.5A1.5 1.5 0 0 0 5.5 21h13a1.5 1.5 0 0 0 1.5-1.5V17"/>',
  wallet: '<path d="M4 7.5A2.5 2.5 0 0 1 6.5 5H18v3"/><rect x="3" y="8" width="18" height="12" rx="2.5"/><path d="M16 14h2"/>',
};
function icon(name, cls = '') {
  return `<svg class="ic ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ''}</svg>`;
}

const DRAWER_SECTIONS = [
  ['home', 'Кейсы'],
  ['upgrader', 'Апгрейдер'],
  ['dice', 'Дайсы'],
  ['crash', 'Краш'],
  ['battle', 'Батл'],
  ['inventory', 'Инвентарь'],
  ['quests', 'Квесты'],
  ['giveaways', 'Розыгрыши'],
  ['bonuses', 'Бонусы'],
  ['deposit', 'Пополнить баланс'],
  ['withdraw', 'Вывод брейнротов'],
  ['faq', 'FAQ'],
  ['support', 'Поддержка'],
];

const TOPNAV_SECTIONS = ['home', 'upgrader', 'dice', 'crash', 'battle', 'inventory', 'bonuses'];

function renderDrawer(active) {
  const root = document.getElementById('drawer-items');
  root.innerHTML = '';
  for (const [key, label] of DRAWER_SECTIONS) {
    const btn = document.createElement('button');
    btn.className = 'drawer-item' + (key === active ? ' active' : '');
    btn.innerHTML = `${icon(key)}<span>${label}</span>`;
    btn.addEventListener('click', () => { closeDrawer(); if (key === 'support') openSupport(); else navigate(key); });
    root.appendChild(btn);
  }
  // ПК: основные разделы прямо в шапке (виден только на широком экране)
  const nav = document.getElementById('topnav');
  if (nav) {
    nav.innerHTML = TOPNAV_SECTIONS.map((key) => {
      const label = DRAWER_SECTIONS.find(([k]) => k === key)[1];
      return `<button class="topnav-item${key === active ? ' active' : ''}" data-nav="${key}">${icon(key)}<span>${label}</span></button>`;
    }).join('');
    nav.querySelectorAll('[data-nav]').forEach((b) => b.addEventListener('click', () => navigate(b.dataset.nav)));
  }
}

function openDrawer() {
  document.getElementById('drawer').classList.remove('hidden');
  document.getElementById('drawer-overlay').classList.remove('hidden');
}
function closeDrawer() {
  document.getElementById('drawer').classList.add('hidden');
  document.getElementById('drawer-overlay').classList.add('hidden');
}

document.getElementById('btn-drawer').addEventListener('click', openDrawer);
document.getElementById('drawer-overlay').addEventListener('click', closeDrawer);
document.getElementById('btn-profile').addEventListener('click', () => navigate('profile'));
document.getElementById('btn-wallet').addEventListener('click', () => { haptic.tick(); navigate('deposit'); });
document.getElementById('brand-home').addEventListener('click', () => navigate('home'));
document.getElementById('drawer-profile').addEventListener('click', () => { closeDrawer(); navigate('profile'); });

// ------------------------------------------------------------------- router

const SCREENS = {
  home: renderCasesScreen,
  profile: renderProfileScreen,
  upgrader: renderUpgraderScreen,
  battle: renderBattleScreen,
  dice: renderDiceScreen,
  crash: renderCrashScreen,
  quests: renderQuestsScreen,
  giveaways: renderGiveawaysScreen,
  faq: renderFaqScreen,
  bonuses: renderBonusesScreen,
  deposit: renderDepositScreen,
  withdraw: renderWithdrawScreen,
  inventory: renderInventoryScreen,
};

// navigate() рендерит экран сама, с полными params (напр. category кейсов).
// location.hash при этом меняется и триггерит свой hashchange-листенер ниже
// — тот рендерит ТОТ ЖЕ экран, но без params (там их неоткуда взять — в
// hash пишется только имя экрана). Гонка двух async-рендеров, и чей fetch
// вернётся позже — тот и остаётся на экране: переключение вкладок категорий
// на кейсах visually откатывалось обратно на «Кейсы» почти в 100% случаев.
// Помечаем свой собственный переход, чтобы слушатель его не задваивал.
let ignoreNextHashChange = false;

function navigate(screen, params = {}) {
  ignoreNextHashChange = true;
  location.hash = '#' + screen;
  // Если hash не изменился (напр. клик по вкладке текущего экрана),
  // hashchange не срослась бы вообще — флаг иначе завис бы true навсегда
  // и проглотил бы следующий настоящий внешний переход хэша.
  setTimeout(() => { ignoreNextHashChange = false; }, 0);
  renderScreen(screen, params);
}

function skeletonGrid() {
  return `<div class="skeleton-grid">${Array(6).fill('<div class="skeleton skeleton-card"></div>').join('')}</div>`;
}

/* Системная кнопка «Назад» Telegram: закрывает кейс, иначе ведёт на главную. */
function syncBackButton() {
  if (!tg || !tg.BackButton) return;
  const screen = (location.hash || '#home').slice(1);
  if (document.getElementById('case-stage') || screen !== 'home') tg.BackButton.show(); else tg.BackButton.hide();
}
if (tg && tg.BackButton) {
  tg.BackButton.onClick(() => {
    haptic.tick();
    if (document.getElementById('case-stage')) { closeStage(); setTimeout(syncBackButton, 250); return; }
    if (document.getElementById('active-modal')) { closeModal(); return; }
    navigate('home');
  });
}

async function renderScreen(screen, params = {}) {
  closeStage();
  closeModal();
  stopCrashLoops();
  if (upgraderFx) { upgraderFx.stop(); upgraderFx = null; }
  renderDrawer(screen);
  setTimeout(syncBackButton, 0);
  const root = document.getElementById('screen');
  root.innerHTML = `<div class="section-title">&nbsp;</div>${skeletonGrid()}`;
  try {
    const fn = SCREENS[screen] || renderCasesScreen;
    await fn(root, params);
  } catch (err) {
    root.innerHTML = `<div class="empty-state">Ошибка: ${escapeHtml(err.message)}</div>`;
  }
}

window.addEventListener('hashchange', () => {
  if (ignoreNextHashChange) {
    ignoreNextHashChange = false;
    return;
  }
  const screen = (location.hash || '#home').slice(1);
  renderScreen(screen);
});

// =================================================================== ГЛАВНАЯ / КЕЙСЫ

function caseThemeVars(c) {
  const [c1, c2, c3] = (c.theme && c.theme.colors) || ['#8b93ff', '#d7dcff', '#0b0d1f'];
  return `--c1:${c1};--c2:${c2};--c3:${c3}`;
}

const COIN_SVG = `<svg viewBox="0 0 40 40" class="coin-art" aria-hidden="true"><circle cx="20" cy="20" r="17" fill="#ffd24d" stroke="#b8861a" stroke-width="2.5"/><circle cx="20" cy="20" r="12" fill="none" stroke="#b8861a" stroke-width="1.5"/><text x="20" y="26" text-anchor="middle" font-size="16" font-weight="900" fill="#8a5a00" font-family="Unbounded,sans-serif">B</text></svg>`;
const DEMAND_LABEL = { 'Very High': 'спрос ↑↑', High: 'спрос ↑', Medium: 'спрос =', Low: 'спрос ↓', 'Very Low': 'спрос ↓↓' };

function coinIcon() { return '<i class="b-coin"></i>'; }
function priceHtml(n) { return `<span class="price">${fmt(n)}${coinIcon()}</span>`; }

function marketChips(b) {
  if (!b.market) return '';
  const { tier, demand } = b.market;
  const hot = demand === 'Very High' || demand === 'High';
  const cold = demand === 'Very Low' || demand === 'Low';
  return `${tier ? `<span class="mk-tier">${tier}</span>` : ''}${demand ? `<span class="mk-demand ${hot ? 'hot' : cold ? 'cold' : ''}" title="${escapeHtml(demand)}">${hot ? '▲' : cold ? '▼' : '•'}</span>` : ''}`;
}

function freeWaitLabel(sec) {
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  return h ? `${h}ч ${m}м` : m ? `${m}м ${String(s).padStart(2, '0')}с` : `${s}с`;
}

let freeTimer = null;
let freeReadyAt = 0;

function caseFootRight(c) {
  if (c.category === 'free') {
    const left = Math.max(0, Math.ceil((freeReadyAt - Date.now()) / 1000));
    return left ? `<span class="case-status" data-free-timer>через ${freeWaitLabel(left)}</span>` : '<span class="case-status ready">Доступен</span>';
  }
  if (c.category === 'referral') {
    const n = caseCreditsLeft(c);
    return n ? `<span class="case-status ready">Осталось ${n}</span>` : '<span class="case-status">По коду</span>';
  }
  return priceHtml(c.price_tokens);
}

function caseCard(c, idx) {
  return `
    <button class="case-card fade-in-up" style="${caseThemeVars(c)};animation-delay:${Math.min(idx * 30, 300)}ms" data-case-id="${c.id}" data-name="${escapeHtml(c.name.toLowerCase())}">
      <div class="case-card-glow"></div>
      <div class="case-card-art">${CaseArt.artifact(c)}</div>
      <div class="case-card-name">${escapeHtml(c.name)}</div>
      <div class="case-card-foot">
        <span class="case-card-count">${c.item_count_label} предм.</span>
        ${caseFootRight(c)}
      </div>
    </button>`;
}

async function renderCasesScreen(root) {
  const [data, , wins] = await Promise.all([api('/api/cases'), refreshMe(), api('/api/recent-wins?limit=16').catch(() => [])]);
  freeReadyAt = Date.now() + (data.free_wait_seconds || 0) * 1000;
  const all = data.collections.flatMap((col) => col.cases);
  const freeCase = all.find((c) => c.category === 'free');

  const banner = freeCase ? `
    <button class="free-banner fade-in-up" data-case-id="${freeCase.id}" style="${caseThemeVars(freeCase)}">
      <div class="free-banner-row">
        <div class="free-banner-thumb">${CaseArt.artifact(freeCase)}</div>
        <div class="free-banner-text">
          <div class="free-banner-eyebrow">БЕСПЛАТНО</div>
          <div class="free-banner-title">${escapeHtml(freeCase.name)}</div>
          <div class="free-banner-every">каждые ${fmt(data.free_cooldown_hours)} ч${data.required_channel ? ` · для подписчиков ${escapeHtml(data.required_channel)}` : ''}</div>
        </div>
      </div>
      <div class="free-banner-sub" id="free-banner-sub"></div>
    </button>` : '';

  const sections = data.collections.filter((col) => col.cases.length).map((col) => `
    <section class="collection" data-collection="${col.key}">
      <h2 class="section-head ${col.key === 'apex' ? 'all-in' : ''}"><span>${escapeHtml(col.title)}</span></h2>
      <div class="case-grid">${col.cases.map(caseCard).join('')}</div>
    </section>`).join('');

  const live = wins.length ? `
    <section class="live">
      <div class="live-head"><span class="live-dot"></span>Последние выигрыши</div>
      <div class="live-row">${wins.map((w) => `
        <div class="live-card" style="--rc:${valueBand(w.value)[1]}">
          <div class="live-img">${dropImg(w)}</div>
          <div class="live-player">${escapeHtml(w.player)}</div>
          <div class="live-value">${fmt(w.value)}${coinIcon()}</div>
        </div>`).join('')}</div>
    </section>` : '';

  root.innerHTML = `
    ${banner}
    ${live}
    <div class="case-tools">
      <div class="case-tools-label">Быстрый фильтр</div>
      <input id="case-search" type="search" placeholder="Поиск кейса" autocomplete="off">
    </div>
    ${sections}
    <div class="empty-state hidden" id="cases-empty">Ничего не найдено</div>`;

  root.querySelectorAll('[data-case-id]').forEach((el) =>
    el.addEventListener('click', () => openCaseStage(Number(el.dataset.caseId)))
  );
  root.querySelector('#case-search').addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase();
    let shown = 0;
    root.querySelectorAll('.collection').forEach((sec) => {
      let n = 0;
      sec.querySelectorAll('.case-card').forEach((el) => {
        const ok = !q || el.dataset.name.includes(q);
        el.classList.toggle('hidden', !ok);
        n += ok;
      });
      sec.classList.toggle('hidden', !n);
      shown += n;
    });
    root.querySelector('#cases-empty').classList.toggle('hidden', !!shown);
  });
  startFreeTimer();
}

/** Тикает таймер бесплатного кейса на главной (баннер + карточка). */
function startFreeTimer() {
  if (freeTimer) clearInterval(freeTimer);
  const paint = () => {
    const sub = document.getElementById('free-banner-sub');
    if (!sub) { clearInterval(freeTimer); freeTimer = null; return; }
    const left = Math.max(0, Math.ceil((freeReadyAt - Date.now()) / 1000));
    sub.innerHTML = left ? `Следующий через ${freeWaitLabel(left)}` : '<b class="ok">Открыть бесплатно</b>';
    document.querySelectorAll('[data-free-timer]').forEach((el) => {
      if (left) el.textContent = 'через ' + freeWaitLabel(left);
      else { el.textContent = 'Доступен'; el.classList.add('ready'); el.removeAttribute('data-free-timer'); }
    });
  };
  paint();
  freeTimer = setInterval(paint, 1000);
}

/* ------------------------------------------------------------------ ПОПОЛНЕНИЕ
 * Честные пополнения, как на референсе: брейнроты и гирсы — заявка с ником в
 * игре (B зачисляет модератор после трейда), Stars — счёт Telegram прямо в
 * Mini App (B приходят после оплаты). Сам клиент баланс не трогает. */

let depositTab = 'brainrot';
const depositCart = { brainrot: {}, hirsy: {} };
let depositCatalog = null;
let depositOpenRequest = null; // своя заявка в очереди — новую не оставить, пока не решат

async function renderDepositScreen(root) {
  const [catalog, requests] = await Promise.all([api('/api/deposit/catalog'), api('/api/deposit/requests').catch(() => [])]);
  depositCatalog = catalog;
  depositOpenRequest = requests.find((r) => r.status === 'pending' || r.status === 'queued') || null;
  root.innerHTML = `
    <section class="dep">
      <button class="dep-close" aria-label="Закрыть" onclick="navigate('home')">✕</button>
      <div class="dep-eyebrow">Пополнение баланса</div>
      <h1 class="dep-title" id="dep-title"></h1>
      <div class="dep-tabs">
        ${[['brainrot', '<img src="/static/assets/brainrots/kraken.webp" alt="">', 'Брейнроты'], ['hirsy', '<img src="/static/assets/gears/rainbow-hammer.webp" alt="">', 'Гирсы'], ['stars', '⭐', 'Stars']].map(([k, e, t]) =>
          `<button class="dep-tab ${depositTab === k ? 'active' : ''}" data-tab="${k}"><span class="dep-tab-ic">${e}</span>${t}</button>`).join('')}
      </div>
      <div id="dep-body"></div>
    </section>
    <section class="dep-history" id="dep-history">${depositHistoryHtml(requests)}</section>`;
  root.querySelectorAll('[data-dcancel]').forEach((el) => el.addEventListener('click', async () => {
    if (!confirm(`Отменить заявку #${el.dataset.dcancel}?`)) return;
    try { await api(`/api/deposit/requests/${el.dataset.dcancel}/cancel`, { method: 'POST' }); toast('Заявка отменена', 'success'); }
    catch (err) { toast(err.message, 'error'); }
    renderDepositScreen(root);
  }));
  root.querySelectorAll('[data-tab]').forEach((el) => el.addEventListener('click', () => {
    depositTab = el.dataset.tab; haptic.tick();
    root.querySelectorAll('[data-tab]').forEach((t) => t.classList.toggle('active', t === el));
    paintDepositTab(root);
  }));
  paintDepositTab(root);
}

function depositHistoryHtml(requests) {
  if (!requests.length) return '';
  return `
    <div class="drops-title">Мои заявки</div>
    ${requests.map((r) => `
      <div class="dep-req st-${r.status}">
        <div><b>#${r.id}</b> · ${r.items.map((i) => `${escapeHtml(i.name)} ×${i.qty}`).join(', ')}</div>
        <div class="dep-req-foot"><span>${fmt(r.total_b)}${coinIcon()}${r.bonus_b ? `<span class="wd-topup">+${fmt(r.bonus_b)} по коду</span>` : ''}</span><span class="dep-status">${escapeHtml(r.status_label)}</span></div>
        ${r.status === 'pending' || r.status === 'queued' ? `<button class="dep-cancel" data-dcancel="${r.id}">Отменить</button>` : ''}
      </div>`).join('')}`;
}

function paintDepositTab(root) {
  const body = root.querySelector('#dep-body');
  root.querySelector('#dep-title').textContent = depositTab === 'stars' ? 'Telegram Stars' : depositTab === 'hirsy' ? 'Депозит гирсами' : 'Депозит брейнротом';
  if (depositTab === 'stars') { paintStars(body); return; }
  const items = depositCatalog[depositTab];
  body.innerHTML = `
    <p class="dep-hint">Выбери ${depositTab === 'hirsy' ? 'гирсы' : 'брейнротов'}, введи ник в игре и встань в очередь. Трейды идут строго по одному: дойдёт твоя очередь — модератор кинет трейд и зачислит${coinIcon()} на баланс.</p>
    ${depositOpenRequest ? `<div class="dep-queue">
      <b>${escapeHtml(depositOpenRequest.status_label)}</b>
      <span>Заявка #${depositOpenRequest.id} · ${fmt(depositOpenRequest.total_b)}${coinIcon()} · ник ${escapeHtml(depositOpenRequest.nickname)}. Новую можно оставить после решения по этой.</span>
    </div>` : ''}
    <div class="dep-filters">
      <input id="dep-search" type="search" placeholder="Поиск по названию…" autocomplete="off">
      <button class="dep-sort" id="dep-sort" data-dir="asc">↑ цена</button>
    </div>
    <div class="dep-grid" id="dep-grid"></div>
    <div class="dep-bar">
      <div><span class="muted">Итого</span><b id="dep-total">0</b>${coinIcon()}</div>
      <button class="open-btn" id="dep-next">Далее</button>
    </div>`;
  const grid = body.querySelector('#dep-grid');
  const cart = depositCart[depositTab];
  const unit = (i) => i.price_b;
  const paintTotal = () => {
    const total = items.reduce((sum, i) => sum + unit(i) * (cart[i.id] || 0), 0);
    body.querySelector('#dep-total').textContent = fmt(total);
    body.querySelector('#dep-next').disabled = !total || !!depositOpenRequest;
  };
  const paintGrid = () => {
    const q = body.querySelector('#dep-search').value.trim().toLowerCase();
    const dir = body.querySelector('#dep-sort').dataset.dir;
    const list = items.filter((i) => !q || i.name.toLowerCase().includes(q))
      .sort((a, b) => (dir === 'asc' ? a.price_b - b.price_b : b.price_b - a.price_b));
    grid.innerHTML = list.map((i) => `
      <div class="dep-item ${cart[i.id] ? 'picked' : ''}" data-id="${i.id}">
        ${i.hot_stock_left ? `<span class="dep-hot">🔥 ${i.hot_stock_left}</span>` : ''}
        <div class="dep-img">${i.image_url ? `<img src="${i.image_url}" alt="" loading="lazy">` : `<span>${escapeHtml(i.emoji)}</span>`}</div>
        <div class="dep-name">${escapeHtml(i.name)}</div>
        <div class="dep-price">${fmt(i.price_b)}${coinIcon()}${i.min_qty > 1 ? `<span> · от ${i.min_qty} шт</span>` : ''}</div>
        <div class="dep-qty"><button data-d="-1">−</button><b>${cart[i.id] || 0}</b><button data-d="1">+</button></div>
      </div>`).join('') || '<div class="empty-state">Ничего не найдено</div>';
  };
  grid.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-d]'); if (!btn) return;
    const card = btn.closest('[data-id]'); const item = items.find((i) => i.id === Number(card.dataset.id));
    const cur = cart[item.id] || 0;
    // как в чате: первый «+» сразу до минимальной партии, «−» ниже минимума — в 0
    const next = btn.dataset.d === '1' ? (cur ? cur + 1 : item.min_qty) : (cur <= item.min_qty ? 0 : cur - 1);
    if (next) cart[item.id] = next; else delete cart[item.id];
    haptic.tick();
    card.classList.toggle('picked', !!next);
    card.querySelector('.dep-qty b').textContent = next;
    paintTotal();
  });
  body.querySelector('#dep-search').addEventListener('input', paintGrid);
  body.querySelector('#dep-sort').addEventListener('click', (e) => {
    const b = e.currentTarget; b.dataset.dir = b.dataset.dir === 'asc' ? 'desc' : 'asc';
    b.textContent = b.dataset.dir === 'asc' ? '↑ цена' : '↓ цена';
    paintGrid();
  });
  body.querySelector('#dep-next').addEventListener('click', () => confirmDeposit(root, items, cart, unit));
  paintGrid(); paintTotal();
}

function confirmDeposit(root, items, cart, unit) {
  const picked = items.filter((i) => cart[i.id]);
  const total = picked.reduce((sum, i) => sum + unit(i) * cart[i.id], 0);
  const overlay = openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div class="dep-confirm">
      <div class="subscribe-title">Заявка на пополнение</div>
      <div class="dep-confirm-list">${picked.map((i) => `<div><span>${escapeHtml(i.name)} ×${cart[i.id]}</span><b>${fmt(unit(i) * cart[i.id])}${coinIcon()}</b></div>`).join('')}</div>
      <div class="dep-confirm-total">Зачислим <b id="dep-get">${fmt(total)}</b>${coinIcon()} после трейда</div>
      <input class="field stars-code" id="dep-code" maxlength="32" placeholder="Промокод (необязательно)" autocomplete="off">
      <div class="stars-hint" id="dep-code-hint">Любой промокод, партнёрский или реферальный код — бонус к зачислению.</div>
      <div class="dep-confirm-note">Заявка встанет в очередь. Трейды — по одному, в порядке очереди; модератор кинет трейд на этот ник.</div>
      <input class="field" id="dep-nick" maxlength="32" placeholder="Твой ник в Steal a Brainrot" autocomplete="off">
      <button class="open-btn" id="dep-send">Встать в очередь</button>
    </div>`);
  const nick = overlay.querySelector('#dep-nick');
  const codeInput = overlay.querySelector('#dep-code');
  let codeOk = true, seq = 0, timer = null;
  const checkCode = async () => {
    const code = codeInput.value.trim(); const my = ++seq;
    const hint = overlay.querySelector('#dep-code-hint');
    if (!code) { codeOk = true; overlay.querySelector('#dep-get').textContent = fmt(total); hint.textContent = 'Любой промокод, партнёрский или реферальный код — бонус к зачислению.'; hint.classList.remove('ok'); return; }
    try {
      const r = await api('/api/deposit/code?code=' + encodeURIComponent(code));
      if (my !== seq) return;
      codeOk = true;
      overlay.querySelector('#dep-get').textContent = fmt(total + Math.floor(total * r.bonus_percent / 100));
      hint.textContent = `Код принят: +${r.bonus_percent}% к зачислению`; hint.classList.add('ok');
    } catch (err) {
      if (my !== seq) return;
      codeOk = false; overlay.querySelector('#dep-get').textContent = fmt(total);
      hint.textContent = 'Такого кода нет — проверь или оставь поле пустым.'; hint.classList.remove('ok');
    }
  };
  codeInput.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(checkCode, 250); });
  overlay.querySelector('#dep-send').addEventListener('click', async (e) => {
    if (!codeOk) { toast('Такого кода нет — исправь или очисти поле', 'error'); return; }
    const btn = e.currentTarget; btn.disabled = true;
    try {
      const res = await api('/api/deposit/request', { method: 'POST', body: JSON.stringify({
        category: depositTab, items: cart, nickname: nick.value.trim(), code: codeInput.value.trim(),
      }) });
      closeModal(); haptic.success();
      toast(res.queue_position === 1 ? `Заявка #${res.request.id}: ты первый — жди трейд` : `Заявка #${res.request.id}: ты ${res.queue_position}-й в очереди`, 'success');
      Object.keys(cart).forEach((k) => delete cart[k]);
      renderDepositScreen(root);
    } catch (err) { toast(err.message, 'error'); btn.disabled = false; }
  });
}

function paintStars(body) {
  const { rate, code_bonus_percent: bonus, min } = depositCatalog.stars;
  body.innerHTML = `
    <p class="dep-hint">Оплата Telegram Stars — ${coinIcon()} зачисляются сразу после оплаты. Курс: 1 ⭐ = ${rate} B. Любой код — промокод, партнёрский или реферальный — даёт +${bonus}%.</p>
    <div class="dep-label">Количество Stars</div>
    <div class="stars-chips">${[50, 100, 250, 500, 1000, 2500].map((n) => `<button data-n="${n}">⭐ ${fmt(n)}</button>`).join('')}</div>
    <input class="field stars-input" id="stars-amount" type="number" inputmode="numeric" min="${min}" placeholder="Например: 625">
    <div class="dep-label">Промокод <span>(бонус +${bonus}%)</span></div>
    <input class="field stars-code" id="stars-code" maxlength="32" placeholder="PROMO" autocomplete="off">
    <div class="stars-get" id="stars-get"></div>
    <button class="open-btn" id="stars-pay" disabled>Создать счёт в Stars</button>
    <div class="stars-hint" id="stars-hint">Введи количество Stars выше.</div>`;
  const input = body.querySelector('#stars-amount');
  const codeInput = body.querySelector('#stars-code');
  const pay = body.querySelector('#stars-pay');
  let quoted = null, seq = 0, timer = null;
  const quote = async () => {
    const n = Math.floor(Number(input.value) || 0);
    const code = codeInput.value.trim();
    const my = ++seq;
    quoted = null; pay.disabled = true;
    pay.textContent = n >= min ? `Оплатить ⭐ ${fmt(n)}` : 'Создать счёт в Stars';
    if (n < min) {
      body.querySelector('#stars-get').innerHTML = '';
      body.querySelector('#stars-hint').textContent = input.value ? 'Минимум 1 ⭐' : 'Введи количество Stars выше.';
      return;
    }
    try {
      const q = await api('/api/deposit/stars/quote', { method: 'POST', body: JSON.stringify({ amount: n, code }) });
      if (my !== seq) return;
      quoted = { amount: n, code };
      body.querySelector('#stars-get').innerHTML = `Получишь <b>${fmt(q.credited)}</b>${coinIcon()}${q.bonus_percent ? `<span class="stars-bonus">+${q.bonus_percent}% за код</span>` : ''}`;
      body.querySelector('#stars-hint').textContent = '';
      pay.disabled = false;
      pay.textContent = `Оплатить ⭐ ${fmt(n)}`;
    } catch (err) {
      if (my !== seq) return;
      body.querySelector('#stars-get').innerHTML = '';
      body.querySelector('#stars-hint').textContent = err.body && err.body.error === 'bad_code' ? 'Такого кода нет — проверь или оставь поле пустым.' : err.message;
    }
  };
  const later = () => { clearTimeout(timer); timer = setTimeout(quote, 250); };
  body.querySelectorAll('[data-n]').forEach((b) => b.addEventListener('click', () => { input.value = b.dataset.n; haptic.tick(); quote(); }));
  input.addEventListener('input', later);
  codeInput.addEventListener('input', later);
  pay.addEventListener('click', async () => {
    if (!quoted) return;
    pay.disabled = true;
    try {
      const res = await api('/api/deposit/stars', { method: 'POST', body: JSON.stringify(quoted) });
      const done = async (status) => {
        pay.disabled = false;
        if (status !== 'paid') { if (status === 'failed') toast('Оплата не прошла', 'error'); return; }
        haptic.success();
        toast(`Оплачено! +${fmt(res.credited)} B`, 'success');
        // B начисляет бот по successful_payment — подтягиваем баланс
        for (let i = 0; i < 5; i++) { await sleep(1200); await refreshMe().catch(() => {}); }
      };
      if (tg && tg.openInvoice) tg.openInvoice(res.invoice_url, done);
      else { window.open(res.invoice_url, '_blank'); pay.disabled = false; }
    } catch (err) { toast(err.message, 'error'); pay.disabled = false; }
  });
}

/* ------------------------------------------------------------------ ВЫВОД
 * Сток админа + вывод брейнрота из инвентаря. Есть в стоке — выводится он
 * сам; нет — обмен на брейнротов из стока примерно той же цены (можно
 * несколькими штуками), недостающее бот доплачивает в B. */

let withdrawMode = 'withdraw'; // или 'exchange' — после кнопки «Обменять»

async function renderWithdrawScreen(root) {
  const [stock, inventory, requests] = await Promise.all([
    api('/api/withdraw/stock'), api('/api/inventory?limit=200'), api('/api/withdraw/requests').catch(() => []),
  ]);
  const inStock = Object.fromEntries(stock.map((s) => [s.name, s.count]));
  const openWd = requests.find((r) => r.status === 'pending' || r.status === 'queued');
  const inv = inventory.slice().sort((a, b) => b.value - a.value);
  root.innerHTML = `
    <section class="dep">
      <button class="dep-close" aria-label="Закрыть" onclick="navigate('home')">✕</button>
      <div class="dep-eyebrow">Вывод брейнротов</div>
      <h1 class="dep-title">Сток на вывод</h1>
      <p class="dep-hint">Выбери брейнрота из инвентаря. Если он есть в стоке — получишь его. Если нет — обмен на брейнротов из стока примерно той же цены, а разницу бот доплатит${coinIcon()} на баланс.</p>
      ${stock.length ? `<div class="dep-grid">${stock.map((s) => `
        <div class="dep-item">
          <span class="stock-count">×${s.count}</span>
          <div class="dep-img">${dropImg(s)}</div>
          <div class="dep-name">${escapeHtml(s.name)}</div>
          <div class="dep-price">${fmt(s.value)}${coinIcon()}</div>
        </div>`).join('')}</div>` : '<div class="empty-state">Сток пока пуст — загляни позже.</div>'}
    </section>
    <section class="dep">
      <div class="dep-eyebrow">Твой инвентарь</div>
      <h1 class="dep-title">${withdrawMode === 'exchange' ? 'Что обменять' : 'Что вывести'}</h1>
      <div class="dep-tabs two">
        <button class="dep-tab ${withdrawMode === 'withdraw' ? 'active' : ''}" data-mode="withdraw">📤 Вывести</button>
        <button class="dep-tab ${withdrawMode === 'exchange' ? 'active' : ''}" data-mode="exchange">🔁 Обменять</button>
      </div>
      <p class="dep-hint">${withdrawMode === 'exchange'
        ? 'Обмен — вместо своего брейнрота получаешь других из стока примерно той же цены (можно несколько штук), разницу бот доплатит на баланс.'
        : 'Вывод — получаешь этого же брейнрота, если он есть в стоке; если нет, бот предложит обмен.'}</p>
      ${openWd ? `<div class="dep-queue"><b>${escapeHtml(openWd.status_label)}</b><span>Вывод #${openWd.id} · ${escapeHtml(openWd.item.name)} · ник ${escapeHtml(openWd.nickname)}. Новый — после решения по этому.</span></div>` : ''}
      ${inv.length ? `<div class="dep-grid">${inv.map((i) => `
        <button class="dep-item wd-item" data-id="${i.id}">
          ${inStock[i.name] ? '<span class="stock-badge">в стоке</span>' : ''}
          <div class="dep-img">${dropImg(i)}</div>
          <div class="dep-name">${escapeHtml(i.name)}</div>
          <div class="dep-price">${fmt(i.value)}${coinIcon()}</div>
        </button>`).join('')}</div>` : '<div class="empty-state">Инвентарь пуст — открой кейс.</div>'}
    </section>
    ${requests.length ? `<section class="dep-history">
      <div class="drops-title">Мои выводы</div>
      ${requests.map((r) => `
        <div class="dep-req st-${r.status === 'done' ? 'approved' : r.status === 'cancelled' ? 'rejected' : 'pending'}">
          <div><b>#${r.id}</b> · ${escapeHtml(r.item.name)} → ${r.payout.map((p) => `${escapeHtml(p.name)} ×${p.qty}`).join(', ')}${r.topup_b ? ` + ${fmt(r.topup_b)} B` : ''}</div>
          <div class="dep-req-foot"><span>ник ${escapeHtml(r.nickname)}</span><span class="dep-status">${escapeHtml(r.status_label)}</span></div>
          ${r.status === 'pending' || r.status === 'queued' ? `<button class="dep-cancel" data-wcancel="${r.id}">Отменить</button>` : ''}
        </div>`).join('')}
    </section>` : ''}`;
  root.querySelectorAll('.wd-item').forEach((el) => el.addEventListener('click', () =>
    openWithdrawSheet(Number(el.dataset.id), withdrawMode === 'exchange', () => renderWithdrawScreen(root))));
  root.querySelectorAll('[data-mode]').forEach((el) => el.addEventListener('click', () => { withdrawMode = el.dataset.mode; renderWithdrawScreen(root); }));
  root.querySelectorAll('[data-wcancel]').forEach((el) => el.addEventListener('click', async () => {
    if (!confirm(`Отменить заявку на вывод #${el.dataset.wcancel}? Брейнрот вернётся в инвентарь.`)) return;
    try { await api(`/api/withdraw/${el.dataset.wcancel}/cancel`, { method: 'POST' }); toast('Вывод отменён', 'success'); }
    catch (err) { toast(err.message, 'error'); }
    renderWithdrawScreen(root);
  }));
}

async function openWithdrawSheet(itemId, exchange = false, onDone = null) {
  const { item, options } = await api(`/api/withdraw/options/${itemId}${exchange ? '?exchange=1' : ''}`);
  const optHtml = (o, idx) => `
    <button class="wd-opt ${idx === 0 ? 'picked' : ''}" data-idx="${idx}">
      <div class="wd-opt-items">${o.items.map((b) => `
        <div class="wd-opt-item"><div class="wd-opt-img">${dropImg(b)}</div><span>${escapeHtml(b.name)}</span><b>×${b.qty}</b></div>`).join('')}</div>
      <div class="wd-opt-foot">${o.direct ? 'Этот же брейнрот' : `Обмен · ${fmt(o.items.reduce((s, b) => s + b.value * b.qty, 0))}${coinIcon()}`}${o.topup_b ? `<span class="wd-topup">+${fmt(o.topup_b)} B на баланс</span>` : ''}</div>
    </button>`;
  const overlay = openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div class="dep-confirm">
      <div class="subscribe-title">${exchange ? 'Обмен' : 'Вывод'}: ${escapeHtml(item.name)}</div>
      <div class="muted" style="text-align:center">Ценность ${fmt(item.value)} B${!exchange && options.length && !options[0].direct ? ' · нет в стоке, выбери обмен' : ''}</div>
      ${options.length ? `<div class="wd-opts">${options.map(optHtml).join('')}</div>
        <input class="field" id="wd-nick" maxlength="32" placeholder="Твой ник в Steal a Brainrot" autocomplete="off">
        <button class="open-btn" id="wd-send">${exchange || !options[0].direct ? 'Обменять' : 'Вывести'}</button>`
        : '<div class="empty-state">В стоке сейчас нет ничего подходящего — загляни позже.</div>'}
    </div>`);
  if (!options.length) return;
  let chosen = 0;
  overlay.querySelectorAll('.wd-opt').forEach((el) => el.addEventListener('click', () => {
    chosen = Number(el.dataset.idx); haptic.tick();
    overlay.querySelectorAll('.wd-opt').forEach((o) => o.classList.toggle('picked', o === el));
  }));
  overlay.querySelector('#wd-send').addEventListener('click', async (e) => {
    const btn = e.currentTarget; btn.disabled = true;
    try {
      const r = await api('/api/withdraw', { method: 'POST', body: JSON.stringify({
        item_id: itemId, option_key: options[chosen].key, nickname: overlay.querySelector('#wd-nick').value.trim(), exchange,
      }) });
      closeModal(); haptic.success();
      toast(r.queue_position === 1 ? `Заявка #${r.id}: ты 1-й в очереди — жди трейд` : `Заявка #${r.id}: ты ${r.queue_position}-й в очереди`, 'success');
      if (onDone) onDone();
    } catch (err) { toast(err.message, 'error'); btn.disabled = false; }
  });
}

// =================================================================== СЦЕНА КЕЙСА

/* Сцена кейса — как на референсах: модель кейса, 1/3/5, «ОТКРЫТЬ КЕЙС» и
 * молния (быстрое открытие без ленты), ниже панель «ЧТО МОЖЕТ ВЫПАСТЬ».
 * Результат решает сервер ДО анимации; лента только показывает его. */

const AURA_PARTICLES = { fire: 'embers', bubbles: 'bubbles', confetti: 'confetti', smoke: 'wisps', snow: 'dust', leaves: 'dust', none: 'dust', dust: 'dust', sparkle: 'prism', crystal: 'prism', stars: 'prism', lightning: 'prism' };

function stageFlash(stage, color) {
  const el = stage.querySelector('.stage-flash');
  el.style.background = `radial-gradient(circle at 50% 30%, ${color}, transparent 65%)`;
  el.classList.remove('on'); void el.offsetWidth; el.classList.add('on');
}

function closeStage() {
  const el = document.getElementById('case-stage');
  if (!el) return;
  clearTimeout(el._freeTick);
  if (el._fx) { el._fx.stop(); el._fx = null; }
  el.classList.add('leaving');
  setTimeout(() => el.remove(), 200);
  document.body.classList.remove('stage-open');
}

function dropImg(b) {
  if (b.coins) return COIN_SVG;
  return b.image_url
    ? `<img src="${b.image_url}" alt="${escapeHtml(b.name)}" loading="lazy" draggable="false">`
    : '<span class="drop-missing">нет ассета</span>';
}

function dropTile(b, cls = '', attrs = '', price = 0) {
  return `
    <div class="drop-tile ${cls}" style="--rc:${relColor(b.value, price)}" ${attrs}>
      <div class="drop-img">${dropImg(b)}<span class="drop-value">${fmt(b.value)}${coinIcon()}</span></div>
      <div class="drop-name">${escapeHtml(b.coins ? 'Монеты' : b.name)}</div>
    </div>`;
}

async function openCaseStage(caseId, qty = 1) {
  const c = await api(`/api/cases/${caseId}`);
  document.getElementById('case-stage')?.remove();

  const stage = document.createElement('div');
  stage.id = 'case-stage';
  stage.className = 'stage';
  stage.style.cssText = caseThemeVars(c);
  document.body.appendChild(stage);
  document.body.classList.add('stage-open');
  syncBackButton();
  const topValue = Math.max(...c.items.map((i) => i.value));
  stage.innerHTML = `
    <canvas class="stage-fx"></canvas>
    <div class="stage-flash"></div>
    <div class="stage-scroll">
      <header class="stage-top">
        <button class="stage-close" aria-label="Назад">‹</button>
        <div class="stage-wallet"><span id="stage-tokens">${fmt(ME ? ME.balance : 0)}</span>${coinIcon()}</div>
      </header>
      <div class="stage-view" id="stage-view">
        <div class="stage-art">${CaseArt.artifact(c)}</div>
      </div>
      <div class="stage-glow"></div>
      <h1 class="stage-name">${escapeHtml(c.name)}</h1>
      <div class="stage-controls" id="stage-controls"></div>
      <section class="drops-panel">
        <div class="drops-title">Что может выпасть</div>
        <div class="drops-grid">
          ${c.items.map((i, idx) => dropTile(i, i.value === topValue ? 'is-top' : '', `data-item="${idx}"`, c.price_tokens)).join('')}
        </div>
      </section>
    </div>`;

  stage._fx = CaseArt.particles(stage.querySelector('.stage-fx'), AURA_PARTICLES[c.theme && c.theme.aura] || 'dust', c.theme ? c.theme.colors : ['#fff', '#fff']);
  stage.querySelector('.stage-close').addEventListener('click', () => { closeStage(); navigate('home'); });
  stage.querySelectorAll('[data-item]').forEach((el) =>
    el.addEventListener('click', () => { const it = c.items[Number(el.dataset.item)]; if (!it.coins) openBrainrotSheet(it); })
  );
  paintStageControls(stage, c, qty);
}

function caseCreditsLeft(c) {
  return (ME && ME.case_credits && ME.case_credits[c.code]) || 0;
}

function paintStageControls(stage, c, qty) {
  const controls = stage.querySelector('#stage-controls');
  controls.classList.remove('busy');
  const isFree = c.category === 'free';
  const isRef = c.category === 'referral';
  if (isFree || isRef) qty = 1;
  const total = c.price_tokens * qty;
  const credits = caseCreditsLeft(c);
  const byCredit = credits >= qty;
  const freeLeft = isFree ? Math.max(0, Math.ceil((freeReadyAt - Date.now()) / 1000)) : 0;
  let label = 'Открыть кейс', sub = `${fmt(total)}${coinIcon()}`, block = null;
  if (byCredit) { sub = `бесплатно · осталось ${credits}`; }
  else if (isFree) {
    sub = 'бесплатно';
    if (freeLeft) { label = 'Через ' + freeWaitLabel(freeLeft); block = 'Бесплатный кейс ещё перезаряжается'; }
  } else if (isRef) { sub = 'только по коду партнёра'; block = 'Этот кейс выдаётся за код партнёра'; }
  else if (!ME || ME.balance < total) { block = `Нужно ${fmt(total)}, у тебя ${fmt(ME ? ME.balance : 0)}. Пополни баланс.`; }

  controls.innerHTML = `
    ${isFree || isRef ? '' : `<div class="qty-switch">
      ${[1, 3, 5].map((q) => `<button class="qty-opt ${q === qty ? 'active' : ''}" data-qty="${q}">${q}</button>`).join('')}
    </div>`}
    <div class="open-row">
      <button class="open-btn" id="btn-open" ${block ? 'data-poor="1"' : ''}>${label}</button>
      <button class="quick-btn" id="btn-quick" aria-label="Быстрое открытие" ${block ? 'data-poor="1"' : ''}>
        <svg viewBox="0 0 24 24" class="ic"><path d="M13 2 4 14h7l-1 8 9-12h-7z" fill="currentColor"/></svg>
      </button>
    </div>
    <div class="open-sub">${sub}</div>`;
  controls.querySelectorAll('.qty-opt').forEach((el) =>
    el.addEventListener('click', () => { haptic.tick(); paintStageControls(stage, c, Number(el.dataset.qty)); })
  );
  const go = (fast) => (e) => {
    if (e.currentTarget.dataset.poor) { toast(block, 'error'); return; }
    runOpening(stage, c, qty, fast);
  };
  controls.querySelector('#btn-open').addEventListener('click', go(false));
  controls.querySelector('#btn-quick').addEventListener('click', go(true));
  clearTimeout(stage._freeTick);
  if (isFree && freeLeft && !byCredit) {
    stage._freeTick = setTimeout(() => { if (document.body.contains(controls) && !controls.classList.contains('busy')) paintStageControls(stage, c, qty); }, 1000);
  }
}

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function runOpening(stage, c, qty, fast = false) {
  const controls = stage.querySelector('#stage-controls');
  const view = stage.querySelector('#stage-view');
  controls.classList.add('busy');
  controls.querySelectorAll('button').forEach((b) => { b.disabled = true; });
  haptic.impact('medium');

  let res;
  try {
    res = await api(`/api/cases/${c.id}/open`, { method: 'POST', body: JSON.stringify({ qty, use_credits: caseCreditsLeft(c) >= qty }) });
  } catch (err) {
    paintStageControls(stage, c, qty);
    if (err.body && err.body.error === 'subscribe_required') { showSubscribeSheet(err.body, () => runOpening(stage, c, qty, fast)); return; }
    if (err.body && err.body.error === 'free_cooldown') { freeReadyAt = Date.now() + err.body.wait_seconds * 1000; paintStageControls(stage, c, qty); }
    toast('Ошибка: ' + err.message, 'error');
    return;
  }
  ME.balance = res.balance;
  if (ME.case_credits) ME.case_credits[c.code] = res.credits_left;
  if (c.category === 'free') freeReadyAt = Date.now() + (res.free_wait_seconds || 0) * 1000;
  stage.querySelector('#stage-tokens').textContent = fmt(res.balance);
  refreshMe().catch(() => {});

  if (!fast && !CaseArt.REDUCED) {
    const multi = res.reels.length > 1;
    view.innerHTML = `<div class="reels ${multi ? 'multi' : ''}">${res.reels.map((reel) => `
      <div class="reel">
        <div class="reel-track">${reel.map((i) => dropTile(i, 'reel-tile', '', c.price_tokens)).join('')}</div>
        <div class="reel-marker"></div>
      </div>`).join('')}</div>`;
    controls.classList.remove('busy'); // иначе pointer-events: none глушит «Пропустить»
    controls.innerHTML = '<button class="skip-btn" id="btn-skip">Пропустить</button>';
    const spins = [...view.querySelectorAll('.reel')].map((el, r) =>
      spinReel(el, res.reveal_index, (multi ? 4300 : 5600) + r * 260)
    );
    controls.querySelector('#btn-skip').addEventListener('click', () => spins.forEach((sp) => sp.skip()));
    await Promise.all(spins.map((sp) => sp.done));
    haptic.success();
    const best = res.won.reduce((a, b) => (b.value > a.value ? b : a));
    const color = relColor(best.value, c.price_tokens);
    stageFlash(stage, color);
    const vr = view.getBoundingClientRect();
    if (stage._fx) stage._fx.burst(vr.left + vr.width / 2, vr.top + vr.height / 2, color, best.value >= c.price_tokens * 3 ? 2 : best.value >= c.price_tokens ? 1.3 : 0.6);
    await sleep(750);
  }
  showReveal(stage, c, qty, res.won);
}

/** Лента: победитель уже стоит на revealIndex. Замедление с длинным
 * хвостом, остановка в случайной точке внутри карточки победителя. */
function spinReel(reelEl, revealIndex, duration) {
  const track = reelEl.querySelector('.reel-track');
  const cards = track.children;
  // offsetLeft/offsetWidth не зависят от transform-анимаций появления.
  const winner = cards[revealIndex];
  const cardW = winner.offsetWidth;
  const step = cards[1].offsetLeft - cards[0].offsetLeft;
  const viewW = reelEl.clientWidth;
  const center = winner.offsetLeft - cards[0].offsetLeft + cardW / 2 - viewW / 2;
  const target = center + (Math.random() - 0.5) * cardW * 0.8;
  let skipped = false, lastIdx = -1, resolve;
  const done = new Promise((r) => { resolve = r; });
  const start = performance.now();
  const ease = (t) => 1 - Math.pow(1 - t, 5);

  function finish(snap) {
    track.style.transition = snap ? 'transform 260ms ease-out' : 'transform 450ms cubic-bezier(.25,.1,.25,1)';
    track.style.transform = `translate3d(${-center}px,0,0)`;
    setTimeout(() => {
      winner.classList.add('won');
      reelEl.classList.add('stopped');
      resolve();
    }, snap ? 280 : 470);
  }
  function frame(now) {
    if (skipped) return;
    const t = Math.min(1, (now - start) / duration);
    const x = target * ease(t);
    track.style.transform = `translate3d(${-x}px,0,0)`;
    const idx = Math.floor((x + viewW / 2) / step);
    if (idx !== lastIdx) { lastIdx = idx; if (t < 0.98) haptic.tick(); }
    if (t < 1) requestAnimationFrame(frame); else finish(false);
  }
  requestAnimationFrame(frame);
  return { done, skip() { if (!skipped) { skipped = true; finish(true); } } };
}

function gameInfoHtml(b) {
  if (!b.game) return '';
  return `
    <div class="game-info">
      <div><span>Цена в игре</span><b>$${escapeHtml(b.game.cost)}</b></div>
      <div><span>Доход</span><b>$${escapeHtml(b.game.income)}/с</b></div>
      <a href="${b.game.wiki_url}" target="_blank" rel="noopener">вики · ${escapeHtml(b.game.as_of)}</a>
    </div>`;
}

function showReveal(stage, c, qty, won) {
  const view = stage.querySelector('#stage-view');
  const controls = stage.querySelector('#stage-controls');
  const total = won.reduce((sum, w) => sum + w.value, 0);
  const sellable = won.filter((w) => !w.coins);
  const payoutTotal = sellable.reduce((sum, w) => sum + w.sell_payout, 0);
  const again = (c.category !== 'free' && c.category !== 'referral') || caseCreditsLeft(c) >= qty;

  const cost = Math.max(c.price_tokens * qty, 1);
  const mult = total / cost;
  const bestColor = relColor(Math.max(...won.map((w) => w.value)), c.price_tokens);
  view.innerHTML = `
    <div class="result" style="--rc:${bestColor}">
      <div class="result-rays"></div>
      <div class="drops-title">${won.length > 1 ? `Ваш дроп · <span data-count="${total}">0</span>${coinIcon()}` : 'Ваш дроп'}</div>
      <div class="result-grid n${won.length}">
        ${won.map((w, i) => dropTile(w, `result-tile ${w.value >= Math.max(c.price_tokens, 5) ? 'is-win' : ''}`, `data-won="${i}"`, c.price_tokens)).join('')}
      </div>
      ${c.price_tokens ? `<div class="result-mult ${mult >= 1 ? 'up' : 'down'}">×${mult.toFixed(mult >= 10 ? 0 : 1)} к цене кейса</div>` : ''}
      ${won.length === 1 ? gameInfoHtml(won[0]) : ''}
    </div>`;
  countUp(view);
  controls.classList.remove('busy');
  controls.innerHTML = `
    <div class="result-actions ${sellable.length ? '' : 'single'}">
      ${sellable.length ? `<button class="ghost-btn" id="btn-sell-all">Продать · ${fmt(payoutTotal)}${coinIcon()}</button>` : ''}
      <button class="ghost-btn" id="btn-keep">${sellable.length ? 'Забрать' : 'Готово'}</button>
    </div>
    ${again ? '<button class="open-btn" id="btn-again">Открыть ещё</button>' : ''}`;

  controls.querySelector('#btn-keep').addEventListener('click', () => {
    if (sellable.length) toast(won.length > 1 ? 'Брейнроты в инвентаре' : `${won[0].name} — в инвентаре`, 'success');
    resetStage(stage, c, qty);
  });
  if (sellable.length) controls.querySelector('#btn-sell-all').addEventListener('click', async (e) => {
    e.currentTarget.disabled = true;
    let sum = 0;
    for (let i = 0; i < won.length; i++) {
      if (won[i].coins) continue;
      try {
        const res = await api(`/api/inventory/${won[i].inventory_id}/sell`, { method: 'POST' });
        ME.balance = res.balance;
        sum += res.payout;
        view.querySelector(`[data-won="${i}"]`).classList.add('sold');
      } catch (err) { /* уже продан */ }
    }
    stage.querySelector('#stage-tokens').textContent = fmt(ME.balance);
    if (sum) toast(`Продано: +${fmt(sum)}`, 'success');
    refreshMe().catch(() => {});
    resetStage(stage, c, qty);
  });
  if (again) controls.querySelector('#btn-again').addEventListener('click', () => {
    if (caseCreditsLeft(c) < qty && ME.balance < c.price_tokens * qty) {
      toast(`Нужно ${fmt(c.price_tokens * qty)}, у тебя ${fmt(ME.balance)}. Пополни баланс.`, 'error');
      return;
    }
    runOpening(stage, c, qty);
  });
}

/** Бесплатный кейс только для подписчиков канала: подписаться → проверить. */
function showSubscribeSheet(info, retry) {
  const overlay = openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div class="subscribe-sheet">
      <div class="subscribe-icon">📣</div>
      <div class="subscribe-title">Подпишись на канал</div>
      <p class="muted">Бесплатный кейс открывается только подписчикам ${escapeHtml(info.channel)}.</p>
      <button class="open-btn" id="btn-sub-go">Подписаться</button>
      <button class="ghost-btn" id="btn-sub-check">Я подписался — открыть</button>
    </div>`);
  overlay.querySelector('#btn-sub-go').addEventListener('click', () => {
    if (tg && tg.openTelegramLink) tg.openTelegramLink(info.channel_url); else window.open(info.channel_url, '_blank');
  });
  overlay.querySelector('#btn-sub-check').addEventListener('click', () => { closeModal(); retry(); });
}

/** Цифры результата «набегают» от 0 — момент выигрыша читается лучше. */
function countUp(root) {
  const els = [...root.querySelectorAll('[data-count]')];
  root.querySelectorAll('.result-tile .drop-value').forEach((el) => {
    const n = el.firstChild; if (n && n.nodeType === 3) { const span = document.createElement('span'); span.dataset.count = n.textContent.replace(/\D/g, ''); el.replaceChild(span, n); els.push(span); }
  });
  const start = performance.now(), dur = CaseArt.REDUCED ? 1 : 700;
  (function tick(now) {
    const t = Math.min(1, (now - start) / dur), k = 1 - Math.pow(1 - t, 3);
    els.forEach((el) => { el.textContent = fmt(Math.round(Number(el.dataset.count) * k)); });
    if (t < 1) requestAnimationFrame(tick);
  })(start);
}

function resetStage(stage, c, qty) {
  stage.querySelector('#stage-view').innerHTML = `<div class="stage-art">${CaseArt.artifact(c)}</div>`;
  paintStageControls(stage, c, qty);
}

function openBrainrotSheet(b) {
  openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div class="reveal" style="${glowVars(b)}">
      <div class="reveal-rays"></div>
      <div class="reveal-art">${brainrotArt(b)}</div>
      ${rarityBadge(b)}
      <div class="reveal-name">${escapeHtml(b.name)}</div>
      <div class="reveal-value">${fmt(b.value)}${coinIcon()}</div>
      ${b.market ? `<div class="market-line">${b.market.tier ? `Тир трейдеров <b>${b.market.tier}</b>` : ''}${b.market.tier && b.market.demand ? ' · ' : ''}${b.market.demand ? `<b>${DEMAND_LABEL[b.market.demand] || escapeHtml(b.market.demand)}</b>` : ''}</div>` : ''}
      ${gameInfoHtml(b)}
    </div>`);
}

// =================================================================== ИНВЕНТАРЬ

let inventoryFilter = 'all';
let inventorySort = 'value';

async function renderInventoryScreen(root) {
  const items = await api('/api/inventory?limit=200');
  paintInventory(root, items);
}

function paintInventory(root, items) {
  const filtered = inventoryFilter === 'all' ? items : items.filter((i) => i.rarity === inventoryFilter);
  const sorted = filtered.slice().sort((a, b) => {
    if (inventorySort === 'value') return b.value - a.value;
    if (inventorySort === 'rarity') return RARITY_ORDER.indexOf(b.rarity) - RARITY_ORDER.indexOf(a.rarity);
    return new Date(b.obtained_at) - new Date(a.obtained_at);
  });

  const rarityCounts = {};
  items.forEach((i) => { rarityCounts[i.rarity] = (rarityCounts[i.rarity] || 0) + 1; });
  const chips = ['all', ...RARITY_ORDER].map((r) => {
    if (r !== 'all' && !rarityCounts[r]) return '';
    const count = r === 'all' ? items.length : rarityCounts[r];
    const label = r === 'all' ? 'Все' : (items.find((i) => i.rarity === r) || {}).rarity_label || r;
    const rc = r === 'all' ? '#c6ff3d' : (items.find((i) => i.rarity === r) || {}).rarity_color || '#8a93a8';
    return `<button class="filter-chip ${inventoryFilter === r ? 'active' : ''}" style="--rc:${rc}" data-r="${r}">${label} (${count})</button>`;
  }).join('');

  const tiles = sorted.map((i, idx) => `
    <div class="inv-tile fade-in-up" style="--rc:${i.rarity_color};animation-delay:${Math.min(idx * 25, 300)}ms">
      ${brainrotArt(i)}
      <div class="inv-name">${escapeHtml(i.name)}</div>
      <div class="inv-value">${fmt(i.value)}${coinIcon()}</div>
      <button class="inv-sell-btn" data-sell="${i.id}" data-payout="${i.value}">Продать · ${i.value}${coinIcon()}</button>
      <div class="inv-actions">
        <button class="inv-act" data-wd="${i.id}">Вывести</button>
        <button class="inv-act" data-ex="${i.id}">Обменять</button>
      </div>
    </div>`).join('') || '<div class="empty-state" style="grid-column:1/-1">Пусто — открой кейс на главной.</div>';

  root.innerHTML = `
    <div class="section-title">ИНВЕНТАРЬ</div>
    <div class="filter-row">${chips}</div>
    <div class="pill-row">
      <button class="pill sort-pill ${inventorySort === 'value' ? 'active' : ''}" data-sort="value">По цене</button>
      <button class="pill sort-pill ${inventorySort === 'rarity' ? 'active' : ''}" data-sort="rarity">По редкости</button>
      <button class="pill sort-pill ${inventorySort === 'date' ? 'active' : ''}" data-sort="date">По дате</button>
    </div>
    ${items.length ? `<div class="btn-row"><button class="btn btn-ghost" id="btn-sell-all" style="flex:1">💰 Продать всё (${items.length})</button><button class="btn btn-ghost" onclick="navigate('withdraw')" style="flex:1">📤 Вывод и сток</button></div>` : ''}
    <div class="inventory-grid">${tiles}</div>
  `;

  root.querySelectorAll('.filter-chip').forEach((el) => el.addEventListener('click', () => { inventoryFilter = el.dataset.r; paintInventory(root, items); }));
  const afterWithdraw = async () => paintInventory(root, await api('/api/inventory?limit=200'));
  root.querySelectorAll('[data-wd]').forEach((el) => el.addEventListener('click', () => openWithdrawSheet(Number(el.dataset.wd), false, afterWithdraw)));
  root.querySelectorAll('[data-ex]').forEach((el) => el.addEventListener('click', () => openWithdrawSheet(Number(el.dataset.ex), true, afterWithdraw)));
  root.querySelectorAll('.sort-pill').forEach((el) => el.addEventListener('click', () => { inventorySort = el.dataset.sort; paintInventory(root, items); }));
  root.querySelectorAll('[data-sell]').forEach((el) => el.addEventListener('click', async (e) => {
    e.stopPropagation();
    el.disabled = true;
    try {
      const res = await api(`/api/inventory/${el.dataset.sell}/sell`, { method: 'POST' });
      toast(`Продано: ${res.sold_name} +${res.payout} B`, 'success');
      ME.balance = res.balance;
      const topBalance = document.getElementById('topbar-tokens');
      if (topBalance) { topBalance.textContent = res.balance; popNumber(topBalance); }
      const fresh = await api('/api/inventory?limit=200');
      paintInventory(root, fresh);
    } catch (err) {
      toast('Ошибка: ' + err.message, 'error');
      el.disabled = false;
    }
  }));
  root.querySelector('#btn-sell-all')?.addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    let total = 0;
    for (const item of items) {
      try {
        const res = await api(`/api/inventory/${item.id}/sell`, { method: 'POST' });
        total += res.payout;
        ME.balance = res.balance;
      } catch (err) { /* предмет уже продан/удалён — пропускаем */ }
    }
    toast(`Продано всё: +${total} B`, 'success');
    const topBalance = document.getElementById('topbar-tokens');
    if (topBalance) { topBalance.textContent = ME.balance; popNumber(topBalance); }
    const fresh = await api('/api/inventory?limit=200');
    paintInventory(root, fresh);
  });
}

// =================================================================== ПРОФИЛЬ

function tgUser() {
  return (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) || null;
}

function avatarHtml(me, cls = '') {
  const u = tgUser();
  const name = me.username ? me.username : (me.first_name || '?');
  const letter = escapeHtml(name.replace('@', '').charAt(0).toUpperCase() || '?');
  const photo = u && u.photo_url ? `<img src="${u.photo_url}" alt="" onerror="this.remove()">` : '';
  return `<div class="avatar ${cls}"><span>${letter}</span>${photo}</div>`;
}

async function renderProfileScreen(root) {
  const [me, inventory] = await Promise.all([refreshMe(), api('/api/inventory?limit=500')]);
  const byValue = inventory.slice().sort((a, b) => b.value - a.value);
  const recent = inventory.slice().sort((a, b) => new Date(b.obtained_at) - new Date(a.obtained_at)).slice(0, 8);
  const total = inventory.reduce((s, i) => s + i.value, 0);
  const ogCount = inventory.filter((i) => i.rarity === 'og').length;
  const displayName = me.username ? '@' + me.username : (me.first_name || 'игрок');

  root.innerHTML = `
    <div class="profile-hero">
      <div class="profile-hero-bg"></div>
      ${avatarHtml(me, 'avatar-lg')}
      <div class="profile-name">${escapeHtml(displayName)}</div>
      <div class="profile-id">ID ${me.tg_id}</div>
      <div class="profile-wallets">
        <div><span>Баланс</span><b>${fmt(me.balance)}${coinIcon()}</b></div>
        <button class="profile-topup" onclick="navigate('deposit')">${icon('wallet')}Пополнить</button>
      </div>
    </div>
    <div class="profile-stats">
      <div><b>${inventory.length}</b><span>брейнротов</span></div>
      <div><b>${fmt(total)}</b><span>ценность${coinIcon()}</span></div>
      <div><b>${ogCount}</b><span>OG</span></div>
      <div><b>${me.referral_count}</b><span>рефералов</span></div>
    </div>
    ${byValue.length ? `
      <h3 class="profile-h">Витрина</h3>
      <div class="showcase">
        ${byValue.slice(0, 3).map((b, i) => `
          <div class="showcase-card ${i === 0 ? 'top' : ''}" style="${glowVars(b)}">
            ${i === 0 ? '<div class="reveal-rays"></div>' : ''}
            ${brainrotArt(b)}
            ${rarityBadge(b)}
            <div class="showcase-name">${escapeHtml(b.name)}</div>
            <div class="showcase-value">${fmt(b.value)}${coinIcon()}</div>
          </div>`).join('')}
      </div>
      <h3 class="profile-h">Последние дропы</h3>
      <div class="recent-row">
        ${recent.map((b) => `<div class="recent-card" style="${glowVars(b)}">${brainrotArt(b)}<div class="recent-src">${escapeHtml(b.case_name)}</div></div>`).join('')}
      </div>` : '<div class="empty-state">Пока пусто — открой первый кейс на главной.</div>'}
    <div class="btn-row" style="margin-top:14px">
      <button class="btn btn-ghost" onclick="navigate('inventory')">🎒 Инвентарь</button>
      <button class="btn btn-primary" onclick="navigate('home')">Открыть кейс</button>
    </div>
    <div class="btn-row">
      <button class="btn btn-ghost" onclick="navigate('withdraw')">📤 Вывести</button>
      <button class="btn btn-ghost" onclick="withdrawMode='exchange';navigate('withdraw')">🔁 Обменять</button>
    </div>
    <div class="btn-row"><button class="btn btn-ghost" onclick="openSupport()">🆘 Поддержка</button></div>
    <div id="my-cases"></div>
    ${me.partner_code ? `
      <div class="panel partner-self">
        <div class="panel-title">Ты партнёр BrainCore</div>
        <div class="admin-stats"><span>код <b>${escapeHtml(me.partner_code)}</b></span><span>${me.partner_percent}% с пополнений рефералов</span></div>
        <button class="btn-chip" id="copy-partner-link" style="margin-top:10px;width:100%">Скопировать ссылку</button>
      </div>` : ''}
    ${me.deposit_bonus_percent ? `<div class="panel"><div class="panel-title">Бонус к пополнению</div><div class="admin-stats"><span class="hl">+${me.deposit_bonus_percent}% к каждому пополнению</span></div></div>` : ''}
    ${promoCardHtml()}
    ${me.is_admin ? adminPanelHtml() : ''}
  `;
  bindPromoForm(root);
  renderMyCases(root, me);
  root.querySelector('#copy-partner-link')?.addEventListener('click', async () => {
    const base = await api('/api/referral').then((r) => r.link.split('?')[0]).catch(() => 'https://t.me/BrainCorre_bot');
    const link = `${base}?start=${me.partner_code}`;
    try { await navigator.clipboard.writeText(link); toast('Ссылка скопирована', 'success'); } catch (_) { toast(link); }
  });
  if (me.is_admin) bindAdminPanel(root);
}
// =================================================================== ПРОМОКОД + АДМИНКА

function promoCardHtml() {
  return `
    <div class="panel">
      <div class="panel-title">Промокод</div>
      <form class="inline-form" id="promo-form" autocomplete="off">
        <input class="field" id="promo-input" placeholder="Введи код" maxlength="32" autocapitalize="characters" />
        <button class="btn-chip" type="submit">Активировать</button>
      </form>
    </div>`;
}

function bindPromoForm(root) {
  const form = root.querySelector('#promo-form');
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = form.querySelector('#promo-input');
    const btn = form.querySelector('button');
    if (!input.value.trim()) return;
    btn.disabled = true;
    try {
      const res = await api('/api/promo/redeem', { method: 'POST', body: JSON.stringify({ code: input.value }) });
      haptic.success();
      if (res.partner) {
        toast(`Партнёрский код активирован: 🎁 реферальный кейс ×${res.partner.case_amount} и +${res.partner.deposit_bonus_percent}% к пополнениям`, 'success');
      } else {
        const p = res.promo;
        const what = p.kind === 'case' ? `🎁 ${p.amount} бесплатн. открытий кейса` : `+${fmt(p.amount)} B`;
        toast(`Промокод активирован: ${what}`, 'success');
      }
      input.value = '';
      await refreshMe();
      renderProfileScreen(root);
    } catch (err) {
      const msg = { not_found: 'Такого промокода нет', exhausted: 'Промокод закончился', already_used: 'Ты уже активировал этот промокод', empty: 'Введи промокод' }[err.message] || err.message;
      toast(msg, 'error');
    }
    btn.disabled = false;
  });
}

let adminCases = null;

function adminPanelHtml() {
  return `
    <div class="panel admin-panel">
      <div class="panel-title">Админ-панель <span class="admin-badge">ADMIN</span></div>

      <div class="admin-sub">Заявки на пополнение</div>
      <div id="admin-deposits" class="promo-list"><div class="muted">Загрузка…</div></div>

      <div class="admin-sub">Заявки на вывод</div>
      <div id="admin-withdrawals" class="promo-list"><div class="muted">Загрузка…</div></div>

      <div class="admin-sub">Сток на вывод</div>
      <input class="field" id="stock-search" placeholder="Найти брейнрота…" autocomplete="off" />
      <div id="admin-stock" class="stock-list"></div>

      <div class="admin-sub">Бесплатный кейс</div>
      <form class="admin-grid" id="admin-settings" autocomplete="off">
        <input class="field full" id="s-channel" placeholder="Канал подписки: @username или t.me/… (пусто — без подписки)" />
        <input class="field" id="s-hours" type="number" min="0.5" max="168" step="0.5" placeholder="Раз в N часов" />
        <input class="field" id="s-rate" type="number" min="0.01" step="0.01" placeholder="1 ⭐ = ? B" />
        <input class="field" id="s-bonus" type="number" min="0" step="1" placeholder="Бонус за код, %" />
        <button class="btn-chip full" type="submit">Сохранить</button>
      </form>
      <div class="muted admin-hint" id="s-status"></div>

      <div class="admin-sub">Бот поддержки</div>
      <form class="inline-form" id="admin-support-bot" autocomplete="off">
        <input class="field" id="sb-token" type="password" placeholder="Токен из @BotFather" />
        <button class="btn-chip" type="submit">Подключить</button>
      </form>
      <div class="muted admin-hint" id="sb-status"></div>

      <form class="inline-form" id="admin-find" autocomplete="off">
        <input class="field" id="admin-q" placeholder="@username или Telegram ID" />
        <button class="btn-chip" type="submit">Найти</button>
      </form>
      <div id="admin-user"></div>

      <div class="admin-sub">Партнёрки</div>
      <form class="admin-grid" id="admin-partner" autocomplete="off">
        <input class="field full" id="p-user" placeholder="Партнёр: @username или ID" />
        <input class="field" id="p-code" placeholder="Реф-код (необязательно)" maxlength="32" />
        <input class="field" id="p-commission" type="number" min="0.1" max="50" step="0.1" placeholder="% партнёру" />
        <input class="field" id="p-bonus" type="number" min="0" max="100" step="0.1" placeholder="Бонус к пополнению %" />
        <input class="field" id="p-cases" type="number" min="0" max="100" value="1" placeholder="Кейсов" />
        <select class="field full" id="p-case"></select>
        <button class="btn-chip" type="submit">Выдать партнёрку</button>
      </form>
      <div id="admin-partners" class="promo-list"></div>

      <div class="admin-sub">Промокод</div>
      <form class="admin-grid" id="admin-promo" autocomplete="off">
        <select class="field" id="promo-kind">
          <option value="balance">Баланс B</option>
          <option value="case">🎁 Кейс</option>
        </select>
        <input class="field" id="promo-amount" type="number" min="1" placeholder="Сколько" />
        <select class="field hidden" id="promo-case"></select>
        <input class="field" id="promo-uses" type="number" min="1" value="1" placeholder="Активаций" />
        <input class="field" id="promo-code" placeholder="Свой код (необязательно)" maxlength="32" />
        <button class="btn-chip" type="submit">Сгенерировать</button>
      </form>
      <div id="admin-promo-result"></div>
      <div class="admin-sub">Последние промокоды</div>
      <div id="admin-promos" class="promo-list"></div>
    </div>`;
}

function caseOptions() {
  return (adminCases || []).map((c) => `<option value="${c.code}">${escapeHtml(c.name)}</option>`).join('');
}

function adminUserHtml(u) {
  const credits = Object.entries(u.case_credits || {}).map(([code, n]) => {
    const c = (adminCases || []).find((x) => x.code === code);
    return `${escapeHtml(c ? c.name : code)} ×${n}`;
  }).join(', ');
  return `
    <div class="admin-user">
      <div class="admin-user-head">
        <b>${u.username ? '@' + escapeHtml(u.username) : escapeHtml(u.first_name || 'игрок')}</b>
        <span class="muted">ID ${u.tg_id}</span>
      </div>
      <div class="admin-stats">
        <span>${fmt(u.balance)}${coinIcon()}</span>
        <span>реф. ${u.referral_count}</span>
        <span class="${u.partner_percent != null ? 'hl' : ''}">${u.partner_percent != null ? 'партнёр ' + u.partner_percent + '%' : 'не партнёр'}</span>
      </div>
      ${credits ? `<div class="muted" style="font-size:12px;margin-top:4px">Кейсы: ${credits}</div>` : ''}
      <div class="admin-actions">
        <div class="inline-form"><input class="field" id="g-balance" type="number" min="1" placeholder="Сколько B" /><button class="btn-chip" data-grant="balance">Выдать B</button><button class="btn-chip ghost" id="g-take">Списать</button></div>
        <button class="btn-chip danger" id="g-zero">🗑 Обнулить баланс (${fmt(u.balance)} B)</button>
        <div class="inline-form luck-form">
          <input class="field" id="g-luck" type="number" min="0.1" max="20" step="0.1" placeholder="Подкрутка ×" value="${u.luck || ''}" />
          <button class="btn-chip" id="g-luck-set">Подкрутить</button>
          ${u.luck ? '<button class="btn-chip ghost" id="g-luck-off">Снять</button>' : ''}
        </div>
        <div class="muted luck-note">${u.luck ? `Подкрутка ×${u.luck}: ${u.luck > 1 ? 'чаще' : 'реже'} окупающий дроп в кейсах и батле, шанс апгрейдера ×${u.luck}` : 'Шансы честные. ×2 — вдвое чаще окупающий дроп и шанс апгрейда, ×0.5 — наоборот.'}</div>
        <div class="inline-form"><select class="field" id="g-case">${caseOptions()}</select><input class="field narrow" id="g-case-n" type="number" min="1" value="1" /><button class="btn-chip" data-grant="case">Выдать кейс</button></div>
      </div>
    </div>`;
}

async function bindAdminPanel(root) {
  const panel = root.querySelector('.admin-panel');
  if (!panel) return;
  if (!adminCases) {
    const catalog = await api('/api/cases');
    const all = catalog.collections.flatMap((col) => col.cases);
    adminCases = [...all.filter((c) => c.category === 'referral'), ...all.filter((c) => c.category !== 'referral')];
  }
  panel.querySelector('#promo-case').innerHTML = caseOptions();
  panel.querySelector('#p-case').innerHTML = caseOptions();
  const botLink = await api('/api/referral').then((r) => r.link.split('?')[0]).catch(() => 'https://t.me/BrainCorre_bot');

  const depositsBox = panel.querySelector('#admin-deposits');
  async function loadDeposits() {
    const list = await api('/api/admin/deposits').catch(() => []);
    depositsBox.innerHTML = list.map((r) => `
      <div class="admin-dep st-${r.status}">
        <div class="admin-dep-head"><b>${r.queue_position}.</b><b>#${r.id}</b><span>${escapeHtml(r.player)}</span><span class="dep-status">${r.queue_position === 1 ? 'Кинуть трейд' : 'Ждёт'}</span></div>
        <div class="admin-dep-items">${r.items.map((i) => `${escapeHtml(i.name)} ×${i.qty}`).join(', ')}</div>
        <div class="admin-dep-foot">
          <span>ник: <b>${escapeHtml(r.nickname)}</b> · ${fmt(r.total_b)}${coinIcon()}${r.bonus_b ? ` +${fmt(r.bonus_b)} (${escapeHtml(r.promo_code)})` : ''}</span>
          <span class="admin-dep-actions">
            ${r.queue_position === 1 ? `<button class="btn-chip" data-dep="${r.id}" data-act="approve">Зачислить</button>` : ''}
            <button class="btn-chip ghost" data-dep="${r.id}" data-act="reject">Отклонить</button>
          </span>
        </div>
      </div>`).join('') || '<div class="muted">Открытых заявок нет</div>';
    depositsBox.querySelectorAll('[data-dep]').forEach((b) => b.addEventListener('click', async () => {
      const approve = b.dataset.act === 'approve';
      if (!approve && !confirm(`Отклонить заявку #${b.dataset.dep}?`)) return;
      b.disabled = true;
      try {
        const res = await api(`/api/admin/deposits/${b.dataset.dep}`, { method: 'POST', body: JSON.stringify({ action: b.dataset.act }) });
        toast(approve ? `Заявка #${res.id}: зачислено ${fmt(res.credited)} B` : `Заявка #${res.id} отклонена`, 'success');
      } catch (err) { toast(err.message, 'error'); }
      loadDeposits();
    }));
  }
  loadDeposits();

  const wdBox = panel.querySelector('#admin-withdrawals');
  async function loadWithdrawals() {
    const list = await api('/api/admin/withdrawals').catch(() => []);
    wdBox.innerHTML = list.map((r) => `
      <div class="admin-dep">
        <div class="admin-dep-head"><b>${r.queue_position}.</b><b>#${r.id}</b><span>${escapeHtml(r.player)}</span><span class="dep-status">ник ${escapeHtml(r.nickname)}</span></div>
        <div class="admin-dep-items">${escapeHtml(r.item.name)} (${fmt(r.item.value)} B) → <b>${r.payout.map((p) => `${escapeHtml(p.name)} ×${p.qty}`).join(', ')}</b>${r.topup_b ? ` + ${fmt(r.topup_b)} B` : ''}</div>
        <div class="admin-dep-foot"><span></span><span class="admin-dep-actions">
          ${r.queue_position === 1 ? `<button class="btn-chip" data-wd="${r.id}" data-act="done">Выдано</button>` : '<span class="muted">ждёт очереди</span>'}
          <button class="btn-chip ghost" data-wd="${r.id}" data-act="cancel">Отменить</button>
        </span></div>
      </div>`).join('') || '<div class="muted">Заявок на вывод нет</div>';
    wdBox.querySelectorAll('[data-wd]').forEach((b) => b.addEventListener('click', async () => {
      if (b.dataset.act === 'cancel' && !confirm(`Отменить вывод #${b.dataset.wd}? Брейнрот вернётся игроку.`)) return;
      b.disabled = true;
      try {
        await api(`/api/admin/withdrawals/${b.dataset.wd}`, { method: 'POST', body: JSON.stringify({ action: b.dataset.act }) });
        toast(b.dataset.act === 'done' ? 'Отмечено как выдано' : 'Вывод отменён', 'success');
      } catch (err) { toast(err.message, 'error'); }
      loadWithdrawals(); loadStock();
    }));
  }
  const stockBox = panel.querySelector('#admin-stock');
  let stockAll = [];
  const paintStock = () => {
    const q = panel.querySelector('#stock-search').value.trim().toLowerCase();
    const list = stockAll.filter((s) => (q ? s.name.toLowerCase().includes(q) : s.count > 0));
    stockBox.innerHTML = list.map((s) => `
      <div class="stock-row ${s.count ? '' : 'zero'}">
        <span class="stock-img">${s.image_url ? `<img src="${s.image_url}" alt="">` : ''}</span>
        <span class="stock-name">${escapeHtml(s.name)}<small>${fmt(s.value)} B</small></span>
        <span class="dep-qty"><button data-stock="${escapeHtml(s.name)}" data-d="-1">−</button><b>${s.count}</b><button data-stock="${escapeHtml(s.name)}" data-d="1">+</button></span>
      </div>`).join('') || `<div class="muted">${q ? 'Не найдено' : 'Сток пуст — найди брейнрота поиском и нажми +'}</div>`;
    stockBox.querySelectorAll('[data-stock]').forEach((b) => b.addEventListener('click', async () => {
      try {
        const r = await api('/api/admin/stock', { method: 'POST', body: JSON.stringify({ name: b.dataset.stock, delta: Number(b.dataset.d) }) });
        const row = stockAll.find((s) => s.name === r.name); if (row) row.count = r.count;
        haptic.tick(); paintStock();
      } catch (err) { toast(err.message, 'error'); }
    }));
  };
  async function loadStock() { stockAll = await api('/api/admin/stock').catch(() => []); paintStock(); }
  panel.querySelector('#stock-search').addEventListener('input', paintStock);
  loadWithdrawals(); loadStock();

  const settingsForm = panel.querySelector('#admin-settings');
  const paintSettings = (st) => {
    settingsForm.querySelector('#s-channel').value = st.required_channel || '';
    settingsForm.querySelector('#s-hours').value = st.free_case_cooldown_hours;
    settingsForm.querySelector('#s-rate').value = st.stars_rate;
    settingsForm.querySelector('#s-bonus').value = st.stars_code_bonus_percent;
    panel.querySelector('#s-status').textContent = st.required_channel
      ? `Подписка на ${st.required_channel} обязательна · кейс раз в ${st.free_case_cooldown_hours} ч`
      : `Без обязательной подписки · кейс раз в ${st.free_case_cooldown_hours} ч`;
    panel.querySelector('#s-status').textContent += ` · 1 ⭐ = ${st.stars_rate} B, код +${st.stars_code_bonus_percent}%`;
    const sb = panel.querySelector('#sb-status');
    sb.innerHTML = st.support_bot
      ? `✅ Подключён <b>@${escapeHtml(st.support_bot)}</b> — игроки пишут туда, обращения приходят тебе в этот бот, отвечай реплаем. Нажми в нём /start. <button class="btn-chip ghost danger" id="sb-off">Отключить</button>`
      : 'Создай бота в @BotFather (/newbot) и вставь его токен. Пока не подключён — поддержка работает в основном боте.';
    const off = sb.querySelector('#sb-off');
    if (off) off.addEventListener('click', () => saveSupportBot(''));
  };
  const saveSupportBot = async (token) => {
    try {
      paintSettings(await api('/api/admin/settings', { method: 'POST', body: JSON.stringify({ support_bot_token: token }) }));
      panel.querySelector('#sb-token').value = '';
      toast(token ? 'Бот поддержки подключён' : 'Бот поддержки отключён', 'success');
    } catch (err) { toast(err.message, 'error'); }
  };
  panel.querySelector('#admin-support-bot').addEventListener('submit', (e) => {
    e.preventDefault();
    const token = panel.querySelector('#sb-token').value.trim();
    if (!token) { toast('Вставь токен бота', 'error'); return; }
    saveSupportBot(token);
  });
  api('/api/admin/settings').then(paintSettings).catch(() => {});
  settingsForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const st = await api('/api/admin/settings', { method: 'POST', body: JSON.stringify({
        required_channel: settingsForm.querySelector('#s-channel').value.trim(),
        free_case_cooldown_hours: Number(settingsForm.querySelector('#s-hours').value),
        stars_rate: Number(settingsForm.querySelector('#s-rate').value),
        stars_code_bonus_percent: Number(settingsForm.querySelector('#s-bonus').value),
      }) });
      paintSettings(st);
      toast('Сохранено', 'success');
    } catch (err) { toast(err.message, 'error'); }
  });

  async function loadPartners() {
    const list = await api('/api/admin/partners');
    const box = panel.querySelector('#admin-partners');
    box.innerHTML = list.map((pc) => {
      const who = pc.partner.username ? '@' + pc.partner.username : (pc.partner.first_name || pc.partner.tg_id);
      const caseName = ((adminCases || []).find((c) => c.code === pc.case_code) || {}).name;
      return `
        <div class="partner-row ${pc.is_active ? '' : 'off'}">
          <div class="partner-head"><code>${escapeHtml(pc.code)}</code><b>${escapeHtml(String(who))}</b><span class="muted">${pc.uses} акт.</span></div>
          <div class="admin-stats">
            <span>${pc.commission_percent ?? '—'}% партнёру</span>
            <span>+${pc.deposit_bonus_percent}% к пополнению</span>
            ${pc.case_code ? `<span>🎁 ${escapeHtml(caseName || pc.case_code)} ×${pc.case_amount}</span>` : ''}
            ${pc.is_active ? '' : '<span>снята</span>'}
          </div>
          ${pc.is_active ? `<div class="partner-actions">
            <button class="btn-chip ghost" data-copy="${botLink}?start=${escapeHtml(pc.code)}">Ссылка</button>
            <button class="btn-chip ghost" data-copy="${escapeHtml(pc.code)}">Код</button>
            <button class="btn-chip danger" data-revoke="${pc.partner.tg_id}">Снять</button>
          </div>` : ''}
        </div>`;
    }).join('') || '<div class="muted">Партнёров пока нет</div>';
    box.querySelectorAll('[data-copy]').forEach((b) => b.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(b.dataset.copy); toast('Скопировано', 'success'); } catch (_) { toast(b.dataset.copy); }
    }));
    box.querySelectorAll('[data-revoke]').forEach((b) => b.addEventListener('click', async () => {
      try { await api('/api/admin/partners/revoke', { method: 'POST', body: JSON.stringify({ user: b.dataset.revoke }) }); toast('Партнёрка снята', 'success'); loadPartners(); }
      catch (err) { toast('Ошибка: ' + err.message, 'error'); }
    }));
  }
  loadPartners();

  panel.querySelector('#admin-partner').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
      user: panel.querySelector('#p-user').value,
      code: panel.querySelector('#p-code').value,
      commission_percent: panel.querySelector('#p-commission').value,
      deposit_bonus_percent: panel.querySelector('#p-bonus').value || 0,
      case_code: panel.querySelector('#p-case').value,
      case_amount: panel.querySelector('#p-cases').value || 0,
    };
    try {
      const pc = await api('/api/admin/partners', { method: 'POST', body: JSON.stringify(body) });
      toast(`Партнёрка выдана · код ${pc.code}`, 'success');
      haptic.success();
      panel.querySelector('#p-code').value = '';
      loadPartners();
    } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
  });
  let current = null;

  const userBox = panel.querySelector('#admin-user');
  function showUser(u) {
    current = u;
    userBox.innerHTML = adminUserHtml(u);
    userBox.querySelectorAll('[data-grant]').forEach((b) => b.addEventListener('click', async () => {
      const kind = b.dataset.grant;
      const body = { user: String(current.tg_id), kind };
      if (kind === 'balance') body.amount = userBox.querySelector('#g-balance').value;
      if (kind === 'case') { body.case_code = userBox.querySelector('#g-case').value; body.amount = userBox.querySelector('#g-case-n').value; }
      try {
        showUser(await api('/api/admin/grant', { method: 'POST', body: JSON.stringify(body) }));
        toast('Выдано', 'success'); haptic.success();
      } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
    }));
    const setLuck = async (luck) => {
      try {
        showUser(await api('/api/admin/luck', { method: 'POST', body: JSON.stringify({ user: String(current.tg_id), luck }) }));
        toast(luck ? `Подкрутка ×${luck} включена` : 'Подкрутка снята — шансы честные', 'success');
      } catch (err) { toast(err.message, 'error'); }
    };
    userBox.querySelector('#g-luck-set').addEventListener('click', () => setLuck(Number(userBox.querySelector('#g-luck').value) || null));
    const setBalance = async (body, done) => {
      try {
        showUser(await api('/api/admin/balance', { method: 'POST', body: JSON.stringify({ user: String(current.tg_id), ...body }) }));
        toast(done, 'success'); haptic.success();
      } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
    };
    userBox.querySelector('#g-take').addEventListener('click', () => {
      const amount = Number(userBox.querySelector('#g-balance').value);
      if (!amount || amount <= 0) { toast('Введи, сколько B списать', 'error'); return; }
      setBalance({ amount }, `Списано ${fmt(amount)} B`);
    });
    userBox.querySelector('#g-zero').addEventListener('click', () => {
      if (!confirm(`Обнулить баланс игрока ID ${current.tg_id} (${fmt(current.balance)} B)?`)) return;
      setBalance({ mode: 'zero' }, 'Баланс обнулён');
    });
    const off = userBox.querySelector('#g-luck-off');
    if (off) off.addEventListener('click', () => setLuck(null));
  }

  panel.querySelector('#admin-find').addEventListener('submit', async (e) => {
    e.preventDefault();
    const q = panel.querySelector('#admin-q').value.trim();
    if (!q) return;
    try { showUser(await api('/api/admin/user?q=' + encodeURIComponent(q))); }
    catch (err) { userBox.innerHTML = `<div class="muted" style="margin:8px 2px">Не найден. Игрок должен хотя бы раз открыть бота.</div>`; }
  });

  const kindSel = panel.querySelector('#promo-kind');
  kindSel.addEventListener('change', () => panel.querySelector('#promo-case').classList.toggle('hidden', kindSel.value !== 'case'));

  async function loadPromos() {
    const list = await api('/api/admin/promos');
    panel.querySelector('#admin-promos').innerHTML = list.map((p) => `
      <div class="promo-row">
        <code>${escapeHtml(p.code)}</code>
        <span>${p.kind !== 'case' ? fmt(p.amount) + coinIcon() : '🎁 ' + p.amount + ' · ' + escapeHtml(((adminCases || []).find((c) => c.code === p.case_code) || {}).name || p.case_code)}</span>
        <span class="muted">${p.uses}/${p.max_uses}</span>
      </div>`).join('') || '<div class="muted">Пока нет</div>';
  }
  loadPromos();

  panel.querySelector('#admin-promo').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
      kind: kindSel.value,
      amount: panel.querySelector('#promo-amount').value,
      max_uses: panel.querySelector('#promo-uses').value || 1,
      case_code: panel.querySelector('#promo-case').value,
      code: panel.querySelector('#promo-code').value,
    };
    try {
      const p = await api('/api/admin/promos', { method: 'POST', body: JSON.stringify(body) });
      const out = panel.querySelector('#admin-promo-result');
      out.innerHTML = `<button class="promo-created" id="promo-copy"><code>${escapeHtml(p.code)}</code><span>Скопировать</span></button>`;
      out.querySelector('#promo-copy').addEventListener('click', async () => {
        try { await navigator.clipboard.writeText(p.code); toast('Скопировано', 'success'); } catch (_) { toast(p.code); }
      });
      panel.querySelector('#promo-code').value = '';
      haptic.success();
      loadPromos();
    } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
  });
}


// =================================================================== АПГРЕЙДЕР

// Вклад — до 5 брейнротов инвентаря; сервер считает шанс по их сумме.
const UPG_MAX_STAKE = 5;
let upgraderState = { stake: [], target: null };
const stakeValue = (stake) => stake.reduce((sum, b) => sum + b.value, 0);
let upgraderSpinning = false;
let upgraderFx = null;

function ringArc(pct) {
  // Зона успеха: от 12 часов по часовой стрелке на pct% окружности.
  const r = 88, c = 2 * Math.PI * r;
  return `<circle class="upg-zone" id="upg-zone" cx="100" cy="100" r="${r}" stroke-dasharray="${(c * pct) / 100} ${c}" />`;
}

async function renderUpgraderScreen(root) {
  if (upgraderFx) { upgraderFx.stop(); upgraderFx = null; }
  const { stake, target } = upgraderState;
  const sv = stakeValue(stake);
  const ready = stake.length && target;
  const chance = ready ? computeChance(sv, target.value) : 0;
  const mult = ready ? (target.value / sv).toFixed(2) : null;
  const stakeSlot = `
    <button class="upg-slot ${stake.length ? 'filled' : ''}" id="slot-contribution" style="${stake.length ? glowVars({ value: sv }) : ''}">
      ${stake.length ? `
        <div class="upg-stack n${stake.length}">${stake.map((b) => brainrotArt(b)).join('')}</div>
        <div class="upg-slot-name">${stake.length === 1 ? escapeHtml(stake[0].name) : `${stake.length} ${stake.length === 5 ? 'брейнротов' : 'брейнрота'}`}</div>
        <div class="upg-slot-value">${fmt(sv)}${coinIcon()}</div>`
        : `<div class="upg-slot-plus">+</div><div class="upg-slot-hint">до ${UPG_MAX_STAKE} шт</div>`}
    </button>`;

  const slot = (b, label, id) => `
    <button class="upg-slot ${b ? 'filled' : ''}" id="${id}" style="${b ? glowVars(b) : ''}">
      ${b ? `${brainrotArt(b)}<div class="upg-slot-name">${escapeHtml(b.name)}</div><div class="upg-slot-value">${fmt(b.value)}${coinIcon()}</div>`
          : '<div class="upg-slot-plus">+</div>'}
    </button>`;

  root.innerHTML = `
    <div class="section-title">АПГРЕЙДЕР</div>
    <div class="upg-stage" id="upg-stage">
      <div class="upg-ring-wrap">
        <canvas class="upg-fx" id="upg-fx"></canvas>
        <svg class="upg-ring" viewBox="0 0 200 200">
          <circle class="upg-track" cx="100" cy="100" r="88"/>
          ${ringArc(chance)}
          ${Array.from({ length: 60 }, (_, i) => `<line class="upg-tick ${i % 5 ? '' : 'major'}" x1="100" y1="${i % 5 ? 6 : 4}" x2="100" y2="${i % 5 ? 11 : 13}" transform="rotate(${i * 6} 100 100)"/>`).join('')}
        </svg>
        <div class="upg-needle" id="upg-needle"><i class="upg-trail"></i><span></span></div>
        <div class="upg-center" id="upg-center">
          ${target ? `<div class="upg-center-art">${brainrotArt(target)}</div>` : ''}
          <div class="upg-chance" id="upg-chance">${ready ? chance + '%' : '—'}</div>
          <div class="upg-label" id="upg-label">${mult ? '×' + mult : 'ШАНС'}</div>
        </div>
      </div>
      <div class="upg-slots">
        ${stakeSlot}
        <div class="upg-arrow">➜</div>
        ${slot(target, 'Цель · шанс 75%…1%', 'slot-target')}
      </div>
    </div>
    <div id="upg-actions">
      <div class="upg-row">
        <button class="open-btn upg-btn" id="btn-spin" ${ready ? '' : 'disabled'} style="--c1:#c6ff3d;--c2:#5dffb0">
          <span class="open-btn-shine"></span>
          <span class="open-btn-label">Прокачать</span>
          <span class="open-btn-price">${ready ? chance + '%' : '—'}</span>
        </button>
        <button class="quick-btn" id="btn-spin-fast" aria-label="Мгновенный прокрут" ${ready ? '' : 'disabled'}>
          <svg viewBox="0 0 24 24" class="ic"><path d="M13 2 4 14h7l-1 8 9-12h-7z" fill="currentColor"/></svg>
        </button>
      </div>
      <button class="btn btn-ghost" style="margin-top:8px" id="btn-reset">Сбросить</button>
    </div>
  `;
  upgraderFx = CaseArt.particles(root.querySelector('#upg-fx'), 'none', ['#c6ff3d', '#ffffff']);

  root.querySelector('#slot-contribution').addEventListener('click', async () => {
    if (upgraderSpinning) return;
    const [items, all] = await Promise.all([api('/api/inventory?limit=200'), api('/api/upgrader/targets?min_value=0')]);
    // Вклад без хотя бы одной цели с шансом 1–75% не подходит — иначе игрок
    // упрётся в пустой список целей.
    const hasTarget = (v) => all.some((t) => t.value * 75 >= v * 100 && t.value <= v * 100);
    openStakePicker(items.slice().sort((a, b) => b.value - a.value), upgraderState.stake, hasTarget, (stake) => {
      upgraderState = { stake, target: null }; renderUpgraderScreen(root);
    });
  });
  root.querySelector('#slot-target').addEventListener('click', async () => {
    if (upgraderSpinning) return;
    const st = upgraderState.stake;
    if (!st.length) { toast('Сначала выбери своих брейнротов', 'error'); return; }
    const targets = await api(`/api/upgrader/targets?min_value=${stakeValue(st)}${st.length === 1 ? '&exclude_name=' + encodeURIComponent(st[0].name) : ''}`);
    openBrainrotPicker('Во что прокачать', targets,
      'Для этого брейнрота нет целей с шансом 75%…1% — выбери другого.',
      (t) => { upgraderState.target = t; renderUpgraderScreen(root); });
  });
  root.querySelector('#btn-reset').addEventListener('click', () => {
    if (upgraderSpinning) return;
    upgraderState = { stake: [], target: null };
    renderUpgraderScreen(root);
  });

  const spinBtn = root.querySelector('#btn-spin');
  const fastBtn = root.querySelector('#btn-spin-fast');
  const spin = async (fast) => {
    if (upgraderSpinning || !ready) return;
    upgraderSpinning = true;
    spinBtn.disabled = true; fastBtn.disabled = true;
    haptic.impact('medium');
    let res;
    try {
      res = await api('/api/upgrader/spin', { method: 'POST', body: JSON.stringify({ contribution_item_ids: stake.map((b) => b.id), target_name: target.name }) });
    } catch (err) {
      upgraderSpinning = false; spinBtn.disabled = false; fastBtn.disabled = false;
      toast('Ошибка: ' + err.message, 'error');
      return;
    }

    const stage = root.querySelector('#upg-stage');
    const needle = root.querySelector('#upg-needle');
    stage.classList.add('spinning');
    // 6 оборотов + точка остановки; кривая — быстрый разгон, долгое мягкое торможение.
    const finalDeg = 360 * 6 + (res.roll_point / 100) * 360;
    const duration = CaseArt.REDUCED || fast ? 350 : 5200;
    const start = performance.now();
    const ease = (t) => 1 - Math.pow(1 - t, 5);
    let lastTick = 0, lastDeg = 0;
    await new Promise((resolve) => {
      function frame(now) {
        const t = Math.min(1, (now - start) / duration);
        const deg = finalDeg * ease(t);
        const speed = Math.min(1, (deg - lastDeg) / 14);
        lastDeg = deg;
        needle.style.transform = `rotate(${deg}deg)`;
        needle.style.setProperty('--trail', speed.toFixed(3));
        const tick = Math.floor(deg / 6);
        if (tick !== lastTick) { lastTick = tick; if (t > 0.55 && t < 0.97) haptic.tick(); }
        if (t < 1) requestAnimationFrame(frame); else resolve();
      }
      requestAnimationFrame(frame);
    });
    stage.classList.remove('spinning');
    upgraderSpinning = false;
    upgraderState = { stake: [], target: null };
    refreshMe().catch(() => {});
    showUpgradeOnWheel(root, res, stake, target);
  };
  spinBtn.addEventListener('click', () => spin(false));
  fastBtn.addEventListener('click', () => spin(true));
}

/** Выбор вклада: до UPG_MAX_STAKE брейнротов, внизу — сумма и «Готово». */
function openStakePicker(items, current, hasTarget, onDone) {
  const picked = new Set(current.map((b) => b.id));
  const overlay = openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div class="picker-title">Твои брейнроты <span class="muted">· до ${UPG_MAX_STAKE}</span></div>
    ${items.length ? `<div class="pick-grid">${items.map((b) => `
      <button class="pick-tile" data-id="${b.id}" style="${glowVars(b)}">
        ${brainrotArt(b)}
        <div class="pick-name">${escapeHtml(b.name)}</div>
        <div class="pick-value">${fmt(b.value)}${coinIcon()}</div>
      </button>`).join('')}</div>` : '<div class="empty-state">Инвентарь пуст — сначала открой кейс.</div>'}
    <div class="stake-bar">
      <span id="stake-sum"></span>
      <button class="open-btn" id="stake-done">Готово</button>
    </div>`);
  const byId = Object.fromEntries(items.map((b) => [b.id, b]));
  const paint = () => {
    const sel = [...picked].map((id) => byId[id]).filter(Boolean);
    const sum = stakeValue(sel);
    overlay.querySelectorAll('.pick-tile').forEach((el) => {
      const on = picked.has(Number(el.dataset.id));
      el.classList.toggle('picked', on);
      el.disabled = !on && picked.size >= UPG_MAX_STAKE;
    });
    overlay.querySelector('#stake-sum').innerHTML = sel.length
      ? `${sel.length}/${UPG_MAX_STAKE} · ${fmt(sum)}${coinIcon()}${hasTarget(sum) ? '' : ' <span class="stake-warn">нет целей</span>'}`
      : 'Выбери брейнротов';
    overlay.querySelector('#stake-done').disabled = !sel.length || !hasTarget(sum);
  };
  overlay.querySelectorAll('.pick-tile').forEach((el) => el.addEventListener('click', () => {
    const id = Number(el.dataset.id);
    if (picked.has(id)) picked.delete(id); else if (picked.size < UPG_MAX_STAKE) picked.add(id);
    haptic.tick(); paint();
  }));
  overlay.querySelector('#stake-done').addEventListener('click', () => {
    closeModal(); onDone([...picked].map((id) => byId[id]).filter(Boolean));
  });
  paint();
}

/** Результат прямо на колесе, без модалок. Выигрыш — цель в центре и
 * вспышка частиц; проигрыш — просто надпись «ФЕЙЛ». */
function showUpgradeOnWheel(root, res, stake, target) {
  const stage = root.querySelector('#upg-stage');
  const center = root.querySelector('#upg-center');
  if (res.success) {
    const b = res.won_item;
    stage.classList.add('upg-win');
    center.innerHTML = `
      <div class="upg-center-art won">${brainrotArt(b)}</div>
      <div class="upg-result-word win">WIN</div>
      <div class="upg-label">+${fmt(b.value)}${coinIcon()}</div>`;
    haptic.success();
    const wrap = root.querySelector('.upg-ring-wrap');
    if (upgraderFx) upgraderFx.burst(wrap.clientWidth / 2, wrap.clientHeight / 2, '#c6ff3d', 1.3);
  } else {
    stage.classList.add('upg-fail');
    center.innerHTML = `<div class="upg-result-word fail">ФЕЙЛ</div><div class="upg-label">шанс был ${res.chance}%</div>`;
  }
  root.querySelector('#upg-actions').innerHTML = `
    <button class="open-btn upg-btn" id="btn-again" style="--c1:#c6ff3d;--c2:#5dffb0">
      <span class="open-btn-shine"></span><span class="open-btn-label">Новый апгрейд</span><span class="open-btn-price">↻</span>
    </button>`;
  root.querySelector('#btn-again').addEventListener('click', () => renderUpgraderScreen(root));
}

// Запасной расчёт (сервер присылает chance_percent у каждой цели).
function computeChance(contributionValue, targetValue) {
  if (targetValue <= 0) return 95;
  const raw = Math.round((contributionValue / targetValue) * 100);
  return Math.max(1, Math.min(95, raw));
}

function openBrainrotPicker(title, list, emptyText, onPick, isDisabled = null) {
  const tiles = list.map((b, idx) => {
    const off = isDisabled && isDisabled(b);
    return `
    <button class="pick-tile ${off ? 'off' : ''}" style="${glowVars(b)}" data-idx="${idx}" ${off ? 'disabled' : ''}>
      ${brainrotArt(b)}
      <div class="pick-name">${escapeHtml(b.name)}</div>
      <div class="pick-value">${off ? off : fmt(b.value) + coinIcon()}</div>
    </button>`;
  }).join('') || `<div class="empty-state" style="grid-column:1/-1">${emptyText}</div>`;
  const overlay = openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <h3 class="picker-title">${title}</h3>
    <div class="pick-grid">${tiles}</div>
  `);
  overlay.querySelectorAll('[data-idx]').forEach((el) =>
    el.addEventListener('click', () => {
      haptic.tick();
      const item = list[Number(el.dataset.idx)];
      closeModal();
      onPick(item);
    })
  );
}

function openItemPicker(items, onPick) {
  openBrainrotPicker('Выбери брейнрота', items.slice().sort((a, b) => b.value - a.value), 'Инвентарь пуст — сначала открой кейс.', onPick);
}

function openTargetPicker(targets, onPick) {
  openBrainrotPicker('Во что прокачать', targets, 'Нет целей дороже вклада.', onPick);
}

// =================================================================== КРАШ
//
// Вся сцена — один <canvas> (звёзды, сетка, кривая, ракета), поверх — DOM с
// множителем. Кривая e^(k·t) считается на клиенте по той же формуле, что на
// сервере; сервер опрашивается только ради момента взрыва. Отображаемое
// время отстаёт от реального на CRASH_DISPLAY_LAG — к моменту, когда график
// доходит до точки взрыва, ответ сервера о взрыве обычно уже получен, и
// множитель не «перескакивает» назад.

const CRASH_DISPLAY_LAG = 0.3;
const CRASH_POLL_MS = 250;
let crashLoop = null;

function stopCrashLoops() {
  if (crashLoop) { crashLoop.stop(); crashLoop = null; }
}

function crashMult(state, t) {
  return Math.min(Math.exp(state.growth_per_sec * Math.max(0, t)), state.max_multiplier);
}

function currentPrize(state, mult) {
  // Лучшая ступень лестницы, доступная при этом множителе (иначе — сама ставка).
  let prize = state.stake, next = null;
  for (const step of state.ladder || []) {
    if (step.at <= mult) prize = step;
    else { next = step; break; }
  }
  return { prize, next };
}

async function renderCrashScreen(root) {
  stopCrashLoops();
  const state = await api('/api/crash/state');
  root.innerHTML = `
    <div class="section-title">КРАШ</div>
    <div class="crash-history" id="crash-history"></div>
    <div class="crash-board" id="crash-board">
      <canvas class="crash-canvas" id="crash-canvas"></canvas>
      <canvas class="crash-fx" id="crash-fx"></canvas>
      <div class="crash-readout">
        <div class="crash-mult" id="crash-mult">1.00×</div>
        <div class="crash-status" id="crash-status">ГОТОВ К СТАРТУ</div>
      </div>
    </div>
    <div id="crash-prize"></div>
    <div id="crash-actions"></div>
  `;
  paintCrashHistory(root, state.history);
  crashLoop = createCrashScene(root);
  if (state.active) runCrashRound(root, state);
  else paintCrashIdle(root, state);
}

function paintCrashHistory(root, history) {
  const el = root.querySelector('#crash-history');
  if (!el) return;
  el.innerHTML = `<span class="crash-history-label">Прошлые</span>` + ((history || []).slice().reverse().map((v) =>
    `<span class="crash-chip ${v >= 3 ? 'hi' : v >= 1.5 ? 'mid' : 'lo'}">${Number(v).toFixed(2)}×</span>`).join('') || '<span class="crash-chip">—</span>');
}

/** Канвас-сцена: звёзды летят со скоростью от множителя, кривая и ракета. */
function createCrashScene(root) {
  const canvas = root.querySelector('#crash-canvas');
  const ctx = canvas.getContext('2d');
  const fx = CaseArt.particles(root.querySelector('#crash-fx'), 'none', ['#fff', '#fff']);
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  let w = 0, h = 0, raf = 0, running = true;
  const stars = Array.from({ length: 70 }, () => ({ x: Math.random(), y: Math.random(), z: 0.3 + Math.random() * 0.7 }));
  const scene = { mode: 'idle', mult: 1, t: 0, state: null, color: '#c6ff3d' };

  function resize() {
    const r = canvas.getBoundingClientRect();
    w = r.width; h = r.height;
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resize();
  const ro = window.ResizeObserver ? new ResizeObserver(resize) : null;
  if (ro) ro.observe(canvas);

  const pad = { l: 44, r: 18, t: 20, b: 22 };
  let last = performance.now();

  function frame(now) {
    if (!running) return;
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    ctx.clearRect(0, 0, w, h);

    // звёзды
    const speed = scene.mode === 'flying' ? 0.04 + Math.min(0.5, (scene.mult - 1) * 0.06) : 0.01;
    for (const s of stars) {
      s.x -= speed * s.z * dt * 3; s.y += speed * s.z * dt * 1.5;
      if (s.x < 0) s.x += 1; if (s.y > 1) s.y -= 1;
      ctx.globalAlpha = 0.25 + s.z * 0.55;
      ctx.fillStyle = '#dfe4ff';
      ctx.fillRect(s.x * w, s.y * h, s.z * 1.6, s.z * 1.6);
    }
    ctx.globalAlpha = 1;

    const gw = w - pad.l - pad.r, gh = h - pad.t - pad.b;
    const t = scene.t;
    const spanT = Math.max(10, t * 1.12);
    const top = Math.max(2, 1 + (scene.mult - 1) * 1.3);
    const X = (tt) => pad.l + (tt / spanT) * gw;
    const Y = (m) => pad.t + gh - ((m - 1) / (top - 1)) * gh;

    // сетка и шкала
    ctx.strokeStyle = 'rgba(255,255,255,.06)'; ctx.lineWidth = 1;
    ctx.fillStyle = 'rgba(255,255,255,.35)'; ctx.font = '600 10px Manrope, sans-serif'; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    for (let i = 0; i <= 4; i++) {
      const m = 1 + ((top - 1) * i) / 4, y = Y(m);
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
      ctx.fillText(m.toFixed(m < 10 ? 1 : 0) + '×', pad.l - 8, y);
    }

    if (scene.state && scene.mode !== 'idle') {
      // кривая
      const pts = [];
      const n = 60;
      for (let i = 0; i <= n; i++) { const tt = (t * i) / n; pts.push([X(tt), Y(crashMult(scene.state, tt))]); }
      const grad = ctx.createLinearGradient(pad.l, h, w, 0);
      if (scene.mode === 'crashed') { grad.addColorStop(0, '#ff4d6d'); grad.addColorStop(1, '#ff8a5c'); }
      else { grad.addColorStop(0, '#5dffb0'); grad.addColorStop(0.6, '#c6ff3d'); grad.addColorStop(1, '#ffd24d'); }
      ctx.beginPath(); ctx.moveTo(pts[0][0], pad.t + gh);
      pts.forEach(([x, y]) => ctx.lineTo(x, y));
      ctx.lineTo(pts[n][0], pad.t + gh); ctx.closePath();
      const fill = ctx.createLinearGradient(0, pad.t, 0, pad.t + gh);
      fill.addColorStop(0, scene.mode === 'crashed' ? 'rgba(255,77,109,.22)' : 'rgba(198,255,61,.22)'); fill.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = fill; ctx.fill();
      ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.strokeStyle = grad; ctx.lineWidth = 3.5; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.shadowColor = scene.mode === 'crashed' ? '#ff4d6d' : '#c6ff3d'; ctx.shadowBlur = 12; ctx.stroke(); ctx.shadowBlur = 0;

      // ракета на кончике, по касательной
      if (scene.mode !== 'crashed') {
        const [x1, y1] = pts[n - 3], [x2, y2] = pts[n];
        const ang = Math.max(-1.2, Math.min(0, Math.atan2(y2 - y1, x2 - x1)));
        drawRocket(ctx, x2, y2, ang, now, scene.mode === 'flying');
      }
      scene.tip = pts[n];
    } else {
      // ракета ждёт на старте
      const bob = Math.sin(now / 400) * 3;
      drawRocket(ctx, pad.l + 18, pad.t + gh - 10 + bob, -0.35, now, false);
      scene.tip = [pad.l + 18, pad.t + gh - 10];
    }
    raf = requestAnimationFrame(frame);
  }
  raf = requestAnimationFrame(frame);

  return {
    scene,
    burst(color, power) { if (scene.tip) fx.burst(scene.tip[0], scene.tip[1], color, power); },
    stop() { running = false; cancelAnimationFrame(raf); if (ro) ro.disconnect(); fx.stop(); if (scene.poll) clearInterval(scene.poll); },
  };
}

function drawRocket(ctx, x, y, ang, now, burning) {
  ctx.save();
  ctx.translate(x, y); ctx.rotate(ang);
  // пламя
  const f = burning ? 1 + Math.sin(now / 45) * 0.25 : 0.45;
  const flame = ctx.createLinearGradient(-34 * f, 0, -8, 0);
  flame.addColorStop(0, 'rgba(255,90,40,0)'); flame.addColorStop(0.5, '#ff8a2e'); flame.addColorStop(1, '#fff3b0');
  ctx.fillStyle = flame;
  ctx.beginPath(); ctx.moveTo(-8, -5); ctx.quadraticCurveTo(-34 * f, 0, -8, 5); ctx.closePath(); ctx.fill();
  // корпус
  ctx.fillStyle = '#eef1f8';
  ctx.beginPath(); ctx.moveTo(-10, -7); ctx.lineTo(8, -7); ctx.quadraticCurveTo(22, -6, 26, 0); ctx.quadraticCurveTo(22, 6, 8, 7); ctx.lineTo(-10, 7); ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#c6ff3d';
  ctx.beginPath(); ctx.moveTo(-6, -7); ctx.lineTo(-13, -15); ctx.lineTo(1, -7); ctx.closePath(); ctx.fill();
  ctx.beginPath(); ctx.moveTo(-6, 7); ctx.lineTo(-13, 15); ctx.lineTo(1, 7); ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#1a1d2b'; ctx.strokeStyle = '#c6ff3d'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.arc(10, 0, 3.6, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.restore();
}

function prizeCardHtml(label, b, extra = '') {
  return `
    <div class="prize-card" style="${glowVars(b)}">
      ${brainrotArt(b)}
      <div class="prize-body">
        <div class="prize-label">${label}</div>
        <div class="prize-name">${escapeHtml(b.name)}</div>
        <div class="prize-value">${fmt(b.value)}${coinIcon()}</div>
        ${extra}
      </div>
    </div>`;
}

function paintCrashIdle(root, state, picked = null) {
  const scene = crashLoop.scene;
  scene.mode = 'idle'; scene.t = 0; scene.mult = 1; scene.state = null;
  root.querySelector('#crash-board').className = 'crash-board';
  root.querySelector('#crash-mult').textContent = '1.00×';
  root.querySelector('#crash-status').textContent = 'ГОТОВ К СТАРТУ';
  root.querySelector('#crash-prize').innerHTML = picked ? `
    <div class="ladder-preview">
      <div class="ladder-row">${(picked.ladder || []).slice(0, 12).map((s) => `
        <div class="ladder-step" style="${glowVars(s)}">${brainrotArt(s)}<span>×${s.at.toFixed(2)}</span></div>`).join('') || ''}</div>
    </div>` : '';
  const actions = root.querySelector('#crash-actions');
  actions.innerHTML = `
    <button class="stake-card stake-pick" id="btn-crash-pick" style="${picked ? glowVars(picked) : ''}">
      ${picked ? `${brainrotArt(picked)}<div><div class="stake-name">${escapeHtml(picked.name)}</div><div class="stake-value">Ставка · ${fmt(picked.value)}${coinIcon()}</div></div><span class="stake-change">Сменить</span>`
               : `<div class="upg-slot-plus">+</div><div><div class="stake-name">Выбери брейнрота</div></div>`}
    </button>
    <button class="open-btn" id="btn-crash-start" ${picked ? '' : 'disabled'} style="--c1:#c6ff3d;--c2:#5dffb0">
      <span class="open-btn-shine"></span><span class="open-btn-label">Взлёт</span><span class="open-btn-price">${picked ? fmt(picked.value) + coinIcon() : '—'}</span>
    </button>`;
  actions.querySelector('#btn-crash-pick').addEventListener('click', async () => {
    const [items, all] = await Promise.all([api('/api/inventory?limit=200'), api('/api/upgrader/targets?min_value=0')]);
    openItemPicker(items, (item) => {
      // лестница для превью — те же правила, что на сервере (crash_runtime.prize_ladder)
      item.ladder = all.filter((t) => t.value > item.value && t.value <= item.value * state.max_multiplier)
        .sort((a, b) => a.value - b.value).map((t) => ({ ...t, at: Math.round((t.value / item.value) * 100) / 100 }));
      paintCrashIdle(root, state, item);
    });
  });
  const startBtn = actions.querySelector('#btn-crash-start');
  startBtn.addEventListener('click', async () => {
    if (!picked) return;
    startBtn.disabled = true;
    try {
      const res = await api('/api/crash/start', { method: 'POST', body: JSON.stringify({ item_id: picked.id }) });
      haptic.impact('heavy');
      if (res.active) runCrashRound(root, res);
      else finishCrash(root, res); // взрыв на 1.00×
    } catch (err) {
      toast('Ошибка: ' + err.message, 'error');
      startBtn.disabled = false;
    }
  });
}

function runCrashRound(root, state) {
  const scene = crashLoop.scene;
  const board = root.querySelector('#crash-board');
  const multEl = root.querySelector('#crash-mult');
  const statusEl = root.querySelector('#crash-status');
  const prizeEl = root.querySelector('#crash-prize');
  const actions = root.querySelector('#crash-actions');
  scene.state = state; scene.mode = 'flying';
  board.className = 'crash-board flying';
  statusEl.textContent = 'В ПОЛЁТЕ';
  const t0 = performance.now() - state.elapsed * 1000;
  let shownPrize = null, done = false;

  actions.innerHTML = `<button class="open-btn cashout-btn" id="btn-crash-cashout" style="--c1:#ffd24d;--c2:#ff9d2e"><span class="open-btn-shine"></span><span class="open-btn-label">Забрать</span><span class="open-btn-price" id="cash-mult">1.00×</span></button>`;
  const cashBtn = actions.querySelector('#btn-crash-cashout');
  cashBtn.addEventListener('click', async () => {
    if (done) return;
    cashBtn.disabled = true;
    try {
      const res = await api('/api/crash/cashout', { method: 'POST' });
      finishCrash(root, res);
    } catch (err) {
      // уже взорвалась — итог придёт следующим опросом
    }
  });

  function tick() {
    if (done || !crashLoop || crashLoop.scene !== scene) return;
    const t = Math.max(0, (performance.now() - t0) / 1000 - CRASH_DISPLAY_LAG);
    const m = crashMult(state, t);
    scene.t = t; scene.mult = m;
    multEl.textContent = m.toFixed(2) + '×';
    const cm = root.querySelector('#cash-mult'); if (cm) cm.textContent = m.toFixed(2) + '×';
    const { prize, next } = currentPrize(state, m);
    if (!shownPrize || shownPrize.name !== prize.name) {
      if (shownPrize) haptic.tick();
      shownPrize = prize;
      prizeEl.innerHTML = prizeCardHtml('Заберёшь сейчас', prize, '<div class="prize-next" id="prize-next"></div>');
      prizeEl.firstElementChild.classList.add('bump');
    }
    const nextEl = root.querySelector('#prize-next');
    if (nextEl) {
      nextEl.innerHTML = next
        ? `<div class="prize-next-row"><span>Дальше: <b>${escapeHtml(next.name)}</b></span><span>×${next.at.toFixed(2)}</span></div>
           <div class="prize-bar"><i style="width:${Math.min(100, ((m - 1) / (next.at - 1)) * 100).toFixed(1)}%"></i></div>`
        : '<div class="prize-next-row"><span>Это лучший брейнрот для этой ставки</span></div>';
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);

  scene.poll = setInterval(async () => {
    try {
      const s = await api('/api/crash/state');
      if (!s.active && s.result) { clearInterval(scene.poll); finishCrash(root, s); }
    } catch (e) { /* сеть моргнула — следующий опрос */ }
  }, CRASH_POLL_MS);

  scene.finish = () => { done = true; clearInterval(scene.poll); };
}

function finishCrash(root, s) {
  if (!crashLoop) return;
  const scene = crashLoop.scene;
  if (scene.mode === 'crashed' || scene.mode === 'cashed') return;
  if (scene.finish) scene.finish();
  const r = s.result;
  const board = root.querySelector('#crash-board');
  const multEl = root.querySelector('#crash-mult');
  const statusEl = root.querySelector('#crash-status');
  scene.state = scene.state || s;
  if (r.outcome === 'crashed') {
    // Досчитываем кривую ровно до точки взрыва.
    scene.t = Math.log(r.crash_point) / s.growth_per_sec;
    scene.mult = r.crash_point;
    scene.mode = 'crashed';
    board.className = 'crash-board crashed';
    multEl.textContent = r.crash_point.toFixed(2) + '×';
    statusEl.textContent = 'ВЗРЫВ';
    crashLoop.burst('#ff6a3d', 1.6);
    haptic.impact('heavy');
    root.querySelector('#crash-prize').innerHTML = prizeCardHtml('Сгорело', s.stake);
    root.querySelector('#crash-prize .prize-card').classList.add('lost');
  } else {
    scene.mode = 'cashed';
    scene.mult = r.multiplier;
    board.className = 'crash-board cashed';
    multEl.textContent = r.multiplier.toFixed(2) + '×';
    statusEl.textContent = 'ЗАБРАНО';
    crashLoop.burst('#ffd24d', 1.1);
    haptic.success();
    root.querySelector('#crash-prize').innerHTML = prizeCardHtml('Получено — уже в инвентаре', r.prize);
    root.querySelector('#crash-prize .prize-card').classList.add('won');
  }
  paintCrashHistory(root, s.history);
  refreshMe().catch(() => {});
  const actions = root.querySelector('#crash-actions');
  actions.innerHTML = `<button class="open-btn" id="btn-crash-again" style="--c1:#c6ff3d;--c2:#5dffb0"><span class="open-btn-shine"></span><span class="open-btn-label">Новый полёт</span><span class="open-btn-price">↻</span></button>`;
  actions.querySelector('#btn-crash-again').addEventListener('click', () => paintCrashIdle(root, s));
}

// =================================================================== ДАЙСЫ

const DICE_COLORS = {
  '🔴': ['#ff4d5e', 'Красный'],
  '🟠': ['#ff9a2e', 'Оранжевый'],
  '🟡': ['#ffd84d', 'Жёлтый'],
  '🟢': ['#3ee08a', 'Зелёный'],
  '🔵': ['#3f8cff', 'Синий'],
  '🟣': ['#a66bff', 'Фиолетовый'],
};
// Грань кубика, которая смотрит на зрителя, для каждой из 6 граней: [rotX, rotY].
const DIE_FACE_ROT = [[0, 0], [0, 180], [0, -90], [0, 90], [-90, 0], [90, 0]];
const DIE_FACES = ['front', 'back', 'right', 'left', 'top', 'bottom'];

let diceState = { item: null, color: null, rolling: false, spins: 0 };

async function renderDiceScreen(root) {
  const rules = await api('/api/dice/rules');
  paintDice(root, rules);
}

function dieHtml(rules, i) {
  const faces = rules.colors.map((c, f) => `<div class="die-face ${DIE_FACES[f]}" style="--fc:${DICE_COLORS[c][0]}"><span></span></div>`).join('');
  return `<div class="die-wrap"><div class="die" id="die-${i}" style="transform:rotateX(-20deg) rotateY(${25 + i * 20}deg)">${faces}</div><div class="die-shadow"></div></div>`;
}

function paintDice(root, rules, lastResult = null) {
  const { item, color } = diceState;
  const table = Object.entries(rules.payout_table);
  root.innerHTML = `
    <div class="section-title">ДАЙСЫ</div>
    <div class="dice-table" id="dice-table">
      <div class="dice-felt"></div>
      <div class="dice-row3d">${[0, 1, 2, 3].map((i) => dieHtml(rules, i)).join('')}</div>
      <div class="dice-verdict" id="dice-verdict">${color ? `Ставка на <b style="color:${DICE_COLORS[color][0]}">${DICE_COLORS[color][1].toLowerCase()}</b>` : ''}</div>
    </div>

    <button class="stake-card stake-pick" id="dice-pick" style="${item ? glowVars(item) : ''}">
      ${item ? `${brainrotArt(item)}<div><div class="stake-name">${escapeHtml(item.name)}</div><div class="stake-value">Ставка · ${fmt(item.value)}${coinIcon()}</div></div><span class="stake-change">Сменить</span>`
             : `<div class="upg-slot-plus">+</div><div><div class="stake-name">Выбери брейнрота</div></div>`}
    </button>

    <div class="color-pick">
      ${rules.colors.map((c) => `
        <button class="gem ${c === color ? 'active' : ''}" style="--gc:${DICE_COLORS[c][0]}" data-color="${c}" aria-label="${DICE_COLORS[c][1]}"><span></span></button>`).join('')}
    </div>

    <button class="open-btn" id="btn-dice-roll" ${item && color ? '' : 'disabled'} style="--c1:${color ? DICE_COLORS[color][0] : '#c6ff3d'};--c2:#ffffff">
      <span class="open-btn-shine"></span><span class="open-btn-label">Бросить</span>
      <span class="open-btn-price">${item ? fmt(item.value) + coinIcon() : '—'}</span>
    </button>

    <div class="payouts">
      ${table.map(([n, m]) => `<div class="payout ${m ? 'win' : ''}"><b>${n}/4</b><span>${m ? '×' + m : '—'}</span></div>`).join('')}
      <div class="payout bonus"><b>Бонус</b><span>×${rules.bonus_multiplier} · ${rules.bonus_chance_percent}%</span></div>
    </div>
  `;

  root.querySelector('#dice-pick').addEventListener('click', async () => {
    if (diceState.rolling) return;
    const items = await api('/api/inventory?limit=200');
    openItemPicker(items, (i) => { diceState.item = i; paintDice(root, rules); });
  });
  root.querySelectorAll('.gem').forEach((el) => el.addEventListener('click', () => {
    if (diceState.rolling) return;
    haptic.tick();
    diceState.color = el.dataset.color;
    paintDice(root, rules);
  }));
  const rollBtn = root.querySelector('#btn-dice-roll');
  rollBtn.addEventListener('click', async () => {
    if (!diceState.item || !diceState.color || diceState.rolling) return;
    diceState.rolling = true;
    rollBtn.disabled = true;
    haptic.impact('heavy');
    let res;
    try {
      res = await api('/api/dice/roll', { method: 'POST', body: JSON.stringify({ item_id: diceState.item.id, color: diceState.color }) });
    } catch (err) {
      diceState.rolling = false; rollBtn.disabled = false;
      toast('Ошибка: ' + err.message, 'error');
      return;
    }
    await animateDice(root, rules, res);
    diceState.rolling = false;
    showDiceVerdict(root, rules, res);
  });
}

async function animateDice(root, rules, res) {
  diceState.spins += 1;
  const dur = CaseArt.REDUCED ? 200 : 1500;
  res.dice.forEach((c, i) => {
    const die = root.querySelector(`#die-${i}`);
    const [rx, ry] = DIE_FACE_ROT[rules.colors.indexOf(c)];
    const turnsX = 360 * (2 + diceState.spins * 2 + i);
    const turnsY = 360 * (3 + diceState.spins * 2 + i);
    die.parentElement.classList.remove('match', 'miss');
    die.parentElement.style.setProperty('--i', i);
    die.parentElement.classList.remove('rolling'); void die.offsetWidth;
    die.parentElement.classList.add('rolling');
    die.style.transition = `transform ${dur + i * 180}ms cubic-bezier(.18,.9,.25,1.02)`;
    die.style.transform = `rotateX(${rx - 12 + turnsX}deg) rotateY(${ry + 8 + turnsY}deg)`;
  });
  let ticks = 0;
  const tick = setInterval(() => { haptic.tick(); if (++ticks > 8) clearInterval(tick); }, 140);
  await sleep(dur + 3 * 180 + 80);
  clearInterval(tick);
  res.dice.forEach((c, i) => {
    const wrap = root.querySelector(`#die-${i}`).parentElement;
    wrap.classList.remove('rolling');
    if (c === diceState.color) wrap.classList.add('match');
    else if (!res.bonus) wrap.classList.add('miss');
  });
}

function showDiceVerdict(root, rules, res) {
  const verdict = root.querySelector('#dice-verdict');
  const table = root.querySelector('#dice-table');
  table.classList.add(res.win ? 'won' : 'lost');
  if (res.win) haptic.success(); else haptic.impact('rigid');
  verdict.innerHTML = res.win
    ? `<span class="v-win">${res.bonus ? 'Радужный бонус!' : `Совпадений: ${res.match_count}`} · ×${res.multiplier}</span><span class="v-sub">${escapeHtml(res.won_item.name)} → ${fmt(res.won_item.value)}${coinIcon()}</span>`
    : `<span class="v-lose">Совпадений: ${res.match_count} — мимо</span><span class="v-sub">${escapeHtml(res.stake.name)} сгорел</span>`;
  diceState.item = null;
  refreshMe().catch(() => {});
  const btn = root.querySelector('#btn-dice-roll');
  btn.querySelector('.open-btn-label').textContent = 'Ещё раз';
  btn.querySelector('.open-btn-price').textContent = '—';
  btn.disabled = false;
  // Основной обработчик броска молча выходит (diceState.item уже null),
  // этот — перерисовывает стол для нового броска.
  btn.addEventListener('click', () => paintDice(root, rules), { once: true });
}

// =================================================================== БАТЛ

async function renderBattleScreen(root) {
  const [cases, me] = await Promise.all([api('/api/battle/cases'), refreshMe()]);
  root.innerHTML = `
    <div class="section-title">БАТЛ</div>
    <div class="case-grid battle-grid">
      ${cases.map((c, idx) => `
        <button class="case-card battle-card fade-in-up" style="${caseThemeVars(c)};animation-delay:${Math.min(idx * 40, 320)}ms" data-id="${c.id}">
          <div class="case-card-art">${CaseArt.artifact(c, 'artifact-sm')}</div>
          <div class="case-card-name">${escapeHtml(c.name)}</div>
          <div class="case-card-foot"><span class="case-card-count">${c.item_count_label} предм.</span>${priceHtml(c.price_tokens)}</div>
        </button>`).join('') || '<div class="empty-state">Нет доступных кейсов для батла.</div>'}
    </div>`;
  root.querySelectorAll('[data-id]').forEach((el) =>
    el.addEventListener('click', () => startBattle(root, cases.find((c) => c.id === Number(el.dataset.id))))
  );
}

async function startBattle(root, c) {
  if (ME && ME.balance < c.price_tokens) { toast(`Нужно ${fmt(c.price_tokens)} B`, 'error'); return; }
  const detail = await api(`/api/cases/${c.id}`);
  const pool = detail.items.filter((i) => i.image_url);
  const me = ME || {};
  const overlay = openModal(`
    <div class="duel" style="${caseThemeVars(c)}">
      <div class="duel-title">${escapeHtml(c.name)}</div>
      <div class="duel-row">
        <div class="duel-side" id="duel-me"><div class="duel-who">${avatarHtml(me)}<span>Ты</span></div><div class="duel-slot"></div><div class="duel-value">…</div></div>
        <div class="duel-vs">VS</div>
        <div class="duel-side" id="duel-bot"><div class="duel-who"><div class="avatar"><span>B</span></div><span>Соперник</span></div><div class="duel-slot"></div><div class="duel-value">…</div></div>
      </div>
      <div class="duel-verdict" id="duel-verdict">Открываем…</div>
      <button class="btn btn-primary hidden" id="duel-done">Готово</button>
    </div>`);
  overlay.onclick = null;

  // Карусель картинок из реального пула кейса, пока ждём ответ сервера.
  const slots = [...overlay.querySelectorAll('.duel-slot')];
  let k = 0;
  const shuffle = setInterval(() => {
    slots.forEach((s, j) => { const b = pool[(k + j * 3) % pool.length]; s.innerHTML = brainrotArt(b); s.style.cssText = glowVars(b); });
    k += 1; haptic.tick();
  }, 90);

  let res;
  try {
    [res] = await Promise.all([
      api('/api/battle/start', { method: 'POST', body: JSON.stringify({ case_id: c.id }) }),
      sleep(CaseArt.REDUCED ? 100 : 1600),
    ]);
  } catch (err) {
    clearInterval(shuffle); closeModal(); toast('Ошибка: ' + err.message, 'error'); return;
  }
  clearInterval(shuffle);
  const put = (id, b) => {
    const side = overlay.querySelector(id);
    side.querySelector('.duel-slot').innerHTML = brainrotArt(b);
    side.querySelector('.duel-slot').style.cssText = glowVars(b);
    side.querySelector('.duel-value').innerHTML = `<b>${escapeHtml(b.name)}</b><span>${fmt(b.value)}${coinIcon()}</span>`;
    side.classList.add('landed');
  };
  put('#duel-me', res.player_item);
  await sleep(350);
  put('#duel-bot', res.bot_item);
  await sleep(450);
  const meSide = overlay.querySelector('#duel-me'), botSide = overlay.querySelector('#duel-bot');
  const verdict = overlay.querySelector('#duel-verdict');
  if (res.winner === 'player') { meSide.classList.add('win'); botSide.classList.add('lose'); verdict.innerHTML = `<span class="v-win">Победа · +${fmt(res.player_item.value + res.bot_item.value)}${coinIcon()}</span>`; haptic.success(); }
  else if (res.winner === 'bot') { botSide.classList.add('win'); meSide.classList.add('lose'); verdict.innerHTML = '<span class="v-lose">Поражение</span>'; haptic.impact('rigid'); }
  else { verdict.innerHTML = '<span class="v-sub">Ничья — ставка возвращена</span>'; }
  refreshMe().catch(() => {});
  const done = overlay.querySelector('#duel-done');
  done.classList.remove('hidden');
  done.addEventListener('click', () => { closeModal(); renderBattleScreen(root); });
}

// =================================================================== КВЕСТЫ

async function renderQuestsScreen(root) {
  const [quests, me] = await Promise.all([api('/api/quests'), refreshMe()]);
  const scopeLabel = { daily: 'ДНЕВНЫЕ', weekly: 'НЕДЕЛЬНЫЕ' };
  const groups = { daily: [], weekly: [] };
  quests.forEach((q) => groups[q.scope].push(q));

  const renderGroup = (label, list) => list.length ? `
    <h4 style="margin:18px 0 8px">${label}</h4>
    ${list.map((q) => `
      <div class="card">
        <div style="font-weight:800">${escapeHtml(q.title)} ${q.claimed ? '✅' : ''}</div>
        <div class="muted">${escapeHtml(q.description)}</div>
        <div class="muted" style="margin:6px 0">${q.progress_count}/${q.target_count} · сброс через ${q.reset_label}</div>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span class="item-value">+${q.reward_tokens}${coinIcon()}</span>
          ${q.claimable ? `<button class="btn btn-gold" style="width:auto;padding:8px 16px" data-claim="${q.id}">ЗАБРАТЬ</button>` : ''}
        </div>
      </div>`).join('')}` : '';

  root.innerHTML = `
    <div class="section-title">КВЕСТЫ</div>
    <div class="balance-line">Баланс: <b>${me.balance}${coinIcon()}</b></div>
    ${renderGroup(scopeLabel.daily, groups.daily)}
    ${renderGroup(scopeLabel.weekly, groups.weekly)}
  `;

  root.querySelectorAll('[data-claim]').forEach((el) =>
    el.addEventListener('click', async () => {
      try {
        const res = await api(`/api/quests/${el.dataset.claim}/claim`, { method: 'POST' });
        toast(`+${res.reward} B`, 'success');
        renderQuestsScreen(root);
      } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
    })
  );
}

// =================================================================== РОЗЫГРЫШИ

async function renderGiveawaysScreen(root) {
  const list = await api('/api/giveaways');
  root.innerHTML = `
    <div class="section-title">РОЗЫГРЫШИ</div>
    ${list.length ? list.map((g) => `
      <div class="card">
        <div style="font-weight:800">${escapeHtml(g.title)}</div>
        <div class="muted">${escapeHtml(g.prize_description)}</div>
        <div class="muted" style="margin:6px 0">Участников: ${g.entries} · до ${new Date(g.ends_at).toLocaleString('ru-RU')}</div>
        ${g.joined
          ? '<div class="muted">✅ Ты участвуешь</div>'
          : `<button class="btn btn-primary" data-join="${g.id}">Участвовать</button>`}
      </div>`).join('') : '<div class="empty-state">Сейчас нет активных розыгрышей.</div>'}
  `;
  root.querySelectorAll('[data-join]').forEach((el) =>
    el.addEventListener('click', async () => {
      try {
        await api(`/api/giveaways/${el.dataset.join}/join`, { method: 'POST' });
        toast('Ты участвуешь!', 'success');
        renderGiveawaysScreen(root);
      } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
    })
  );
}

// =================================================================== FAQ

/* Поддержка — чат в самом боте: открываем бота с ?start=support. */
async function openSupport() {
  haptic.tick();
  try {
    const { url } = await api('/api/support');
    if (tg && tg.openTelegramLink) { tg.openTelegramLink(url); tg.close && tg.close(); } else window.open(url, '_blank');
  } catch (err) { toast(err.message, 'error'); }
}

async function renderFaqScreen(root) {
  const entries = await api('/api/faq');
  root.innerHTML = `
    <div class="section-title">FAQ</div>
    <button class="btn btn-primary support-cta" id="faq-support">${icon('support')}<span>Написать в поддержку</span></button>
    ${entries.map((e) => `
      <div class="card">
        <div style="font-weight:800;margin-bottom:6px">${escapeHtml(e.question)}</div>
        <div class="muted">${escapeHtml(e.answer)}</div>
      </div>`).join('')}
  `;
  root.querySelector('#faq-support').addEventListener('click', openSupport);
}

// =================================================================== БОНУСЫ

async function renderBonusesScreen(root, params = {}) {
  const tab = params.tab || 'referral';
  root.innerHTML = `
    <div class="section-title">БОНУСЫ</div>
    <div class="category-tabs">
      <button class="category-tab ${tab === 'referral' ? 'active' : ''}" id="tab-referral">Реферальная программа</button>
      <button class="category-tab ${tab === 'staking' ? 'active' : ''}" id="tab-staking">Стейкинг</button>
    </div>
    <div id="bonuses-body"></div>
  `;
  root.querySelector('#tab-referral').addEventListener('click', () => renderBonusesScreen(root, { tab: 'referral' }));
  root.querySelector('#tab-staking').addEventListener('click', () => renderBonusesScreen(root, { tab: 'staking' }));

  const body = root.querySelector('#bonuses-body');
  if (tab === 'staking') await renderStakingTab(body);
  else await renderReferralTab(body);
}

async function renderReferralTab(body) {
  const r = await api('/api/referral');
  body.innerHTML = `
    <div class="card">
      <div class="muted">Мой реферальный код</div>
      <div style="font-weight:800;font-size:18px;margin:6px 0">${r.code}</div>
      <a class="link" href="${r.link}" target="_blank">${r.link}</a>
    </div>
    <div class="card">
      <div>Тир: <b>${r.tier.name}</b> — комиссия ${r.tier.commission_percent}%</div>
      ${r.next_tier ? `<div class="muted">До «${r.next_tier.name}»: ещё ${r.next_tier.remaining} чел.</div>` : '<div class="muted">Максимальный тир достигнут.</div>'}
    </div>
    <div class="stat-grid">
      <div class="stat-box"><div class="stat-label">Рефералов</div><div class="stat-value">${r.referral_count}</div></div>
      <div class="stat-box"><div class="stat-label">Заработано</div><div class="stat-value">${r.earned_total}${coinIcon()}</div></div>
    </div>
  `;
}

async function renderStakingTab(body) {
  const s = await api('/api/staking');
  if (s.active) {
    body.innerHTML = `
      <div class="card">
        <div class="muted">АКТИВНЫЙ СТЕЙК</div>
        <div style="font-weight:800;font-size:18px;margin:6px 0">${s.active.amount}${coinIcon()} на ${s.active.term_days} дн. (+${s.active.bonus_percent}%)</div>
        <div class="muted">Погашение: ${new Date(s.active.matures_at).toLocaleString('ru-RU')}</div>
        <div class="muted">Выплата: ${s.active.payout}${coinIcon()}</div>
        ${s.active.matured
          ? '<button class="btn btn-gold" id="btn-stake-claim" style="margin-top:10px">ЗАБРАТЬ</button>'
          : '<div class="muted" style="margin-top:10px">Забрать раньше срока нельзя.</div>'}
      </div>
      ${stakingStatsHtml(s)}
    `;
    body.querySelector('#btn-stake-claim')?.addEventListener('click', async () => {
      try {
        const res = await api(`/api/staking/${s.active.id}/claim`, { method: 'POST' });
        toast(`+${res.payout} B`, 'success');
        renderStakingTab(body);
      } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
    });
    return;
  }

  body.innerHTML = `
    <div class="card">
      <p class="muted">Заморозь B и забирай их обратно с надбавкой. Минимум ${s.min_amount}${coinIcon()}. Твой баланс: ${s.balance}${coinIcon()}.</p>
      <div class="pill-row">
        ${s.tiers.map((t) => `<button class="pill tier-pill" data-term="${t.term_days}" data-bonus="${t.bonus_percent}">${t.label}<br>+${t.bonus_percent}%</button>`).join('')}
      </div>
      <input id="stake-amount" type="number" min="${s.min_amount}" max="${s.balance}" placeholder="Сколько заморозить" style="width:100%;padding:12px;border-radius:9px;border:1px solid var(--border);background:var(--bg-elevated);color:var(--text);margin-bottom:10px" />
      <button class="btn btn-gold" id="btn-stake-start">Заморозить</button>
    </div>
    ${stakingStatsHtml(s)}
  `;

  let selectedTerm = s.tiers[0]?.term_days;
  body.querySelectorAll('.tier-pill').forEach((el) => {
    if (Number(el.dataset.term) === selectedTerm) el.classList.add('active');
    el.addEventListener('click', () => {
      selectedTerm = Number(el.dataset.term);
      body.querySelectorAll('.tier-pill').forEach((p) => p.classList.toggle('active', p === el));
    });
  });

  body.querySelector('#btn-stake-start').addEventListener('click', async () => {
    const amount = Number(body.querySelector('#stake-amount').value);
    if (!amount) { toast('Укажи сумму', 'error'); return; }
    try {
      await api('/api/staking/start', { method: 'POST', body: JSON.stringify({ term_days: selectedTerm, amount }) });
      toast('Стейк открыт!', 'success');
      renderStakingTab(body);
    } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
  });
}

function stakingStatsHtml(s) {
  return `
    <div class="stat-grid">
      <div class="stat-box"><div class="stat-label">Заморожено всего</div><div class="stat-value">${s.total_frozen}${coinIcon()}</div></div>
      <div class="stat-box"><div class="stat-label">Заработано сверху</div><div class="stat-value">${s.total_bonus}${coinIcon()}</div></div>
    </div>`;
}

// ------------------------------------------------------------------- boot

window.closeModal = closeModal;
window.navigate = navigate;
window.openCaseStage = openCaseStage;

(async function boot() {
  try {
    await refreshMe();
    const initial = (location.hash || '#home').slice(1);
    await renderScreen(initial);
  } catch (err) {
    document.getElementById('screen').innerHTML = `<div class="empty-state">Не удалось загрузить: ${escapeHtml(err.message)}</div>`;
  }
})();


/** «Мои кейсы»: бесплатные открытия (от промокода, партнёрки, админа). */
async function renderMyCases(root, me) {
  const box = root.querySelector('#my-cases');
  const entries = Object.entries(me.case_credits || {});
  if (!box || !entries.length) return;
  const cases = await Promise.all(entries.map(([code]) => api('/api/cases/by-code/' + code).catch(() => null)));
  box.innerHTML = `
    <div class="panel">
      <div class="panel-title">Мои кейсы</div>
      <div class="my-cases">
        ${cases.map((c, i) => c ? `
          <button class="my-case" style="${caseThemeVars(c)}" data-open="${c.id}">
            ${CaseArt.artifact(c, 'artifact-sm')}
            <div class="my-case-name">${escapeHtml(c.name)}</div>
            <span class="my-case-count">×${entries[i][1]}</span>
          </button>` : '').join('')}
      </div>
    </div>`;
  box.querySelectorAll('[data-open]').forEach((b) => b.addEventListener('click', () => openCaseStage(Number(b.dataset.open))));
}
