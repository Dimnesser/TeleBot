/* BrainCore Mini App — vanilla JS SPA, без сборки/зависимостей. */

const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  if (tg.setHeaderColor) try { tg.setHeaderColor('#07060c'); } catch (e) {}
  if (tg.setBackgroundColor) try { tg.setBackgroundColor('#07060c'); } catch (e) {}
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
  if (!res.ok) throw new Error((body && body.error) || 'request_failed');
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

/** Официальный рендер брейнрота (из вики, см. webapp/static/assets/brainrots).
 * Если ассета нет — честный плейсхолдер, никакой подменной картинки. */
function brainrotArt(b, sizeClass = '') {
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
  const prevTokens = ME ? ME.game_tokens : null;
  ME = await api('/api/me');
  document.getElementById('drawer-username').textContent = ME.username ? '@' + ME.username : (ME.first_name || 'игрок');
  const drawerAvatar = document.getElementById('drawer-avatar');
  if (drawerAvatar && !drawerAvatar.dataset.ready) { drawerAvatar.outerHTML = avatarHtml(ME).replace('class="avatar ', 'id="drawer-avatar" data-ready="1" class="avatar '); }
  document.getElementById('drawer-balance').textContent = ME.balance;
  const topBalance = document.getElementById('topbar-tokens');
  if (topBalance) {
    topBalance.textContent = ME.game_tokens;
    if (prevTokens !== null && prevTokens !== ME.game_tokens) popNumber(topBalance);
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
  faq: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6"/><circle cx="12" cy="17.2" r=".9" fill="currentColor"/>',
  bonuses: '<rect x="3" y="8" width="18" height="13" rx="2"/><path d="M3 12h18M12 8v13"/><path d="M12 8S8.5 3 7 5.5 12 8 12 8zM12 8s3.5-5 5-2.5S12 8 12 8z"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h10"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
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
  ['faq', 'FAQ'],
];

function renderDrawer(active) {
  const root = document.getElementById('drawer-items');
  root.innerHTML = '';
  for (const [key, label] of DRAWER_SECTIONS) {
    const btn = document.createElement('button');
    btn.className = 'drawer-item' + (key === active ? ' active' : '');
    btn.innerHTML = `${icon(key)}<span>${label}</span>`;
    btn.addEventListener('click', () => { closeDrawer(); navigate(key); });
    root.appendChild(btn);
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
  deposit: renderDepositPlaceholder,
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

async function renderScreen(screen, params = {}) {
  closeStage();
  closeModal();
  stopCrashLoops();
  renderDrawer(screen);
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

function caseCard(c, idx) {
  return `
    <button class="case-card fade-in-up" style="${caseThemeVars(c)};animation-delay:${Math.min(idx * 45, 400)}ms" data-case-id="${c.id}">
      <div class="case-card-glow"></div>
      <div class="case-card-art">${CaseArt.artifact(c, 'artifact-sm')}</div>
      <div class="case-card-body">
        <div class="case-card-name">${escapeHtml(c.name)}</div>
        <div class="case-card-tagline">${escapeHtml(c.theme ? c.theme.tagline : '')}</div>
        <div class="case-card-foot">
          <span class="case-card-count">${c.item_count_label} брейнротов</span>
          <span class="price-chip">${fmt(c.price_tokens)} 🎫</span>
        </div>
      </div>
    </button>`;
}

async function renderCasesScreen(root) {
  const [data, me, recentWins] = await Promise.all([
    api('/api/cases'),
    refreshMe(),
    api('/api/recent-wins?limit=14').catch(() => []),
  ]);
  const all = data.collections.flatMap((col) => col.cases);
  const featured = all.slice().sort((a, b) => b.price_tokens - a.price_tokens)[0];

  const hero = featured ? `
    <button class="hero-case fade-in-up" style="${caseThemeVars(featured)}" data-case-id="${featured.id}">
      <div class="hero-case-bg"></div>
      <div class="hero-case-text">
        <div class="eyebrow">Главный кейс</div>
        <div class="hero-case-name">${escapeHtml(featured.name)}</div>
        <div class="hero-case-tagline">${escapeHtml(featured.theme ? featured.theme.tagline : '')}</div>
        <span class="price-chip price-chip-lg">${fmt(featured.price_tokens)} 🎫</span>
      </div>
      <div class="hero-case-art">${CaseArt.artifact(featured, 'artifact-float')}</div>
    </button>` : '';

  const ticker = recentWins.length ? `
    <div class="live-strip">
      <div class="live-label"><span class="live-dot"></span>Live-дропы</div>
      <div class="live-row">
        ${recentWins.map((w) => `
          <div class="live-card" style="${glowVars(w)}" title="${escapeHtml(w.name)}">
            ${brainrotArt(w)}
            <div class="live-player">${escapeHtml(w.player)}</div>
            <div class="live-value">${fmt(w.value)}</div>
          </div>`).join('')}
      </div>
    </div>` : '';

  const sections = data.collections.map((col) => `
    <section class="collection">
      <div class="collection-head">
        <h2 class="collection-title">${escapeHtml(col.title)}</h2>
        <div class="collection-sub">${escapeHtml(col.subtitle)}</div>
      </div>
      <div class="case-grid ${col.cases.length === 1 ? 'single' : ''}">${col.cases.map(caseCard).join('')}</div>
    </section>`).join('');

  root.innerHTML = `
    <div class="wallet-row">
      <div class="wallet"><span class="wallet-label">Демо-баланс</span><span class="wallet-value" id="home-tokens">${fmt(me.game_tokens)} 🎫</span></div>
      <button class="btn-chip" id="btn-topup">+ ${'Пополнить'}</button>
      <button class="btn-chip ghost" id="btn-inventory">Инвентарь</button>
    </div>
    ${hero}
    ${ticker}
    ${sections}
    <p class="fine-print">Внутри кейсов — только реальные брейнроты Steal a Brainrot тиров Secret и OG с официальными изображениями из вики игры. Шанс каждого — обратно пропорционален его ценности, цена кейса выведена из содержимого.</p>`;

  root.querySelectorAll('[data-case-id]').forEach((el) =>
    el.addEventListener('click', () => openCaseStage(Number(el.dataset.caseId)))
  );
  root.querySelector('#btn-inventory').addEventListener('click', () => navigate('inventory'));
  root.querySelector('#btn-topup').addEventListener('click', async () => {
    const res = await api('/api/demo-topup', { method: 'POST' });
    toast(`+${fmt(res.amount)} 🎫`, 'success');
    ME.game_tokens = res.game_tokens;
    const el = root.querySelector('#home-tokens');
    el.textContent = `${fmt(res.game_tokens)} 🎫`;
    popNumber(el);
    refreshMe();
  });
}

function renderDepositPlaceholder(root) {
  root.innerHTML = `
    <div class="section-title">ПОПОЛНИТЬ БАЛАНС</div>
    <div class="card">
      <p class="muted">Пополнение через обменник (брейнроты/гирсы/Stars) с очередью на подтверждение пока доступно
      только в самом боте — это первая версия Mini App, раздел ещё не перенесён сюда.</p>
      <p class="muted">Открой пополнение прямо в чате с ботом (кнопка «💰 ПОПОЛНИТЬ БАЛАНС» в его меню).</p>
    </div>`;
}

// =================================================================== СЦЕНА КЕЙСА

let stageFx = null;

function closeStage() {
  if (stageFx) { stageFx.stop(); stageFx = null; }
  const el = document.getElementById('case-stage');
  if (!el) return;
  el.classList.add('leaving');
  setTimeout(() => el.remove(), 220);
  document.body.classList.remove('stage-open');
}

async function openCaseStage(caseId, qty = 1) {
  const c = await api(`/api/cases/${caseId}`);
  closeStage();
  document.getElementById('case-stage')?.remove();

  const stage = document.createElement('div');
  stage.id = 'case-stage';
  stage.className = 'stage';
  stage.style.cssText = caseThemeVars(c);
  document.body.appendChild(stage);
  document.body.classList.add('stage-open');
  stage.innerHTML = `
    <div class="stage-bg"></div>
    <canvas class="stage-fx"></canvas>
    <div class="stage-flash"></div>
    <div class="stage-scroll">
      <header class="stage-top">
        <button class="stage-close" aria-label="Закрыть">✕</button>
        <div class="stage-wallet"><span id="stage-tokens">${fmt(ME ? ME.game_tokens : 0)}</span> 🎫</div>
      </header>
      <div class="stage-hero" id="stage-hero">
        <div class="stage-art">${CaseArt.artifact(c, 'artifact-lg artifact-float')}</div>
        <div class="eyebrow">${escapeHtml(c.item_count_label + ' брейнротов · до ' + c.best_rarity_label)}</div>
        <h1 class="stage-name">${escapeHtml(c.name)}</h1>
        <p class="stage-lore">${escapeHtml(c.theme ? c.theme.lore : '')}</p>
      </div>
      <div class="stage-reels hidden" id="stage-reels"></div>
      <div class="stage-controls" id="stage-controls"></div>
      <section class="stage-contents">
        <div class="contents-head">
          <h3>Что внутри</h3>
          <span class="muted">средний дроп ${fmt(Math.round(c.expected_value))} 🎫 · возврат ~${c.target_rtp_percent}%</span>
        </div>
        <div class="contents-grid">
          ${c.items.map((i, idx) => `
            <button class="content-tile fade-in-up" style="${glowVars(i)};animation-delay:${Math.min(idx * 30, 360)}ms" data-item="${idx}">
              ${brainrotArt(i)}
              <div class="content-name">${escapeHtml(i.name)}</div>
              <div class="content-meta"><span class="content-value">${fmt(i.value)}</span><span class="content-chance">${formatChance(i.chance_percent)}</span></div>
            </button>`).join('')}
        </div>
      </section>
    </div>`;

  stageFx = CaseArt.particles(stage.querySelector('.stage-fx'), c.theme ? c.theme.particles : 'dust', c.theme ? c.theme.colors : ['#fff', '#fff']);
  stage.querySelector('.stage-close').addEventListener('click', () => { closeStage(); navigate('home'); });
  stage.querySelectorAll('[data-item]').forEach((el) =>
    el.addEventListener('click', () => openBrainrotSheet(c.items[Number(el.dataset.item)]))
  );
  paintStageControls(stage, c, qty);
}

function formatChance(p) {
  if (p >= 10) return p.toFixed(1) + '%';
  if (p >= 1) return p.toFixed(2) + '%';
  return p.toFixed(3) + '%';
}

function paintStageControls(stage, c, qty) {
  const controls = stage.querySelector('#stage-controls');
  const total = c.price_tokens * qty;
  const enough = ME && ME.game_tokens >= total;
  controls.innerHTML = `
    <div class="qty-switch" role="tablist">
      ${[1, 3, 5].map((q) => `<button class="qty-opt ${q === qty ? 'active' : ''}" data-qty="${q}">×${q}</button>`).join('')}
    </div>
    <button class="open-btn" id="btn-open" ${enough ? '' : 'data-poor="1"'}>
      <span class="open-btn-shine"></span>
      <span class="open-btn-label">${enough ? 'Открыть' : 'Не хватает 🎫'}</span>
      <span class="open-btn-price">${fmt(total)} 🎫</span>
    </button>`;
  controls.querySelectorAll('.qty-opt').forEach((el) =>
    el.addEventListener('click', () => { haptic.tick(); paintStageControls(stage, c, Number(el.dataset.qty)); })
  );
  controls.querySelector('#btn-open').addEventListener('click', (e) => {
    if (e.currentTarget.dataset.poor) {
      toast(`Нужно ${fmt(total)} 🎫, у тебя ${fmt(ME.game_tokens)} 🎫. Пополни демо-баланс на главной.`, 'error');
      return;
    }
    runOpening(stage, c, qty);
  });
}

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function runOpening(stage, c, qty) {
  const controls = stage.querySelector('#stage-controls');
  controls.classList.add('busy');
  controls.querySelector('#btn-open').disabled = true;
  const art = stage.querySelector('.stage-art .artifact');
  haptic.impact('heavy');
  art.classList.add('charging');

  let res;
  try {
    [res] = await Promise.all([
      api(`/api/cases/${c.id}/open`, { method: 'POST', body: JSON.stringify({ qty }) }),
      sleep(CaseArt.REDUCED ? 100 : 900),
    ]);
  } catch (err) {
    art.classList.remove('charging');
    controls.classList.remove('busy');
    toast('Ошибка: ' + err.message, 'error');
    paintStageControls(stage, c, qty);
    return;
  }
  ME.game_tokens = res.game_tokens;
  const walletEl = stage.querySelector('#stage-tokens');
  walletEl.textContent = fmt(res.game_tokens);
  popNumber(walletEl);
  refreshMe().catch(() => {});

  // Артефакт «лопается» — вспышка цветом темы и старт ленты.
  flash(stage, 'var(--c1)');
  stageFx && stageFx.burst(stage.clientWidth / 2, stage.querySelector('.stage-art').getBoundingClientRect().top + 90, getComputedStyle(stage).getPropertyValue('--c2').trim() || '#fff', 0.8);
  stage.querySelector('#stage-hero').classList.add('collapsed');
  controls.innerHTML = '<button class="skip-btn" id="btn-skip">Пропустить</button>';

  const reelsEl = stage.querySelector('#stage-reels');
  reelsEl.classList.remove('hidden');
  const multi = res.reels.length > 1;
  reelsEl.innerHTML = res.reels.map((reel, r) => `
    <div class="reel ${multi ? 'reel-sm' : ''}" data-reel="${r}">
      <div class="reel-marker"></div>
      <div class="reel-track">
        ${reel.map((i) => `
          <div class="reel-card" style="${glowVars(i)}">
            ${brainrotArt(i)}
            ${multi ? '' : `<div class="reel-card-name">${escapeHtml(i.name)}</div>`}
            <div class="reel-card-bar"></div>
          </div>`).join('')}
      </div>
    </div>`).join('');

  const spins = [...reelsEl.querySelectorAll('.reel')].map((el, r) =>
    spinReel(el, res.reveal_index, (CaseArt.REDUCED ? 700 : (multi ? 3600 : 5200)) + r * 450)
  );
  controls.querySelector('#btn-skip').addEventListener('click', () => spins.forEach((s) => s.skip()));
  await Promise.all(spins.map((s) => s.done));

  // Эффект остановки.
  const best = res.won.slice().sort((a, b) => b.value - a.value)[0];
  const [, bc] = valueBand(best.value);
  haptic.success();
  flash(stage, bc);
  const reelRect = reelsEl.getBoundingClientRect();
  stageFx && stageFx.burst(stage.clientWidth / 2, reelRect.top + reelRect.height / 2, bc, best.rarity === 'og' ? 2.2 : best.value >= 2500 ? 1.5 : 1);
  if (best.rarity === 'og' || best.value >= 10000) stage.classList.add('shake');
  await sleep(CaseArt.REDUCED ? 100 : 750);
  stage.classList.remove('shake');
  showReveal(stage, c, qty, res.won);
}

/** Анимация ленты: сервер уже выбрал победителя (он стоит на revealIndex).
 * Лента едет с сильным замедлением, «перелетает» внутрь соседней карточки
 * на случайную долю и доводится ровно в центр — ощущение живой остановки. */
function spinReel(reelEl, revealIndex, duration) {
  const track = reelEl.querySelector('.reel-track');
  const cards = track.children;
  // offsetLeft/offsetWidth — layout-координаты, на них НЕ влияет transform
  // (у .reel есть анимация появления со scale(.96): getBoundingClientRect
  // в этот момент занижал ширину карточки на 4%, и за 34 карточки лента
  // «недоезжала» почти на целую карточку — победитель вставал правее маркера).
  const winnerEl = cards[revealIndex];
  const cardW = winnerEl.offsetWidth;
  const step = cards[1].offsetLeft - cards[0].offsetLeft;
  const viewW = reelEl.clientWidth;
  const center = winnerEl.offsetLeft - cards[0].offsetLeft + cardW / 2 - viewW / 2;
  const jitter = (Math.random() - 0.5) * cardW * 0.7;
  const target = center + jitter;
  const marker = reelEl.querySelector('.reel-marker');
  let skipped = false, lastIdx = -1, resolve;
  const done = new Promise((r) => { resolve = r; });
  const start = performance.now();
  const ease = (t) => 1 - Math.pow(1 - t, 4.2);

  function finish() {
    track.style.transition = 'transform 380ms cubic-bezier(.34,1.56,.64,1)';
    track.style.transform = `translate3d(${-center}px,0,0)`;
    setTimeout(() => {
      cards[revealIndex].classList.add('won');
      reelEl.classList.add('stopped');
      resolve();
    }, 400);
  }
  function frame(now) {
    if (skipped) return;
    const t = Math.min(1, (now - start) / duration);
    const x = target * ease(t);
    track.style.transform = `translate3d(${-x}px,0,0)`;
    const idx = Math.floor((x + viewW / 2) / step);
    if (idx !== lastIdx) {
      lastIdx = idx;
      marker.classList.remove('tick'); void marker.offsetWidth; marker.classList.add('tick');
      if (t < 0.97) haptic.tick();
    }
    if (t < 1) requestAnimationFrame(frame); else finish();
  }
  requestAnimationFrame(frame);
  return {
    done,
    skip() { if (!skipped) { skipped = true; finish(); } },
  };
}

function flash(stage, color) {
  const el = stage.querySelector('.stage-flash');
  el.style.background = `radial-gradient(circle at 50% 45%, ${color}, transparent 70%)`;
  el.classList.remove('on'); void el.offsetWidth; el.classList.add('on');
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
  const reelsEl = stage.querySelector('#stage-reels');
  const controls = stage.querySelector('#stage-controls');
  const total = won.reduce((s, w) => s + w.value, 0);
  const payoutTotal = won.reduce((s, w) => s + w.sell_payout, 0);

  const cards = won.map((w, i) => `
    <div class="reveal ${won.length > 1 ? 'reveal-sm' : ''} ${w.rarity === 'og' ? 'is-og' : ''}" style="${glowVars(w)};animation-delay:${i * 90}ms" data-won="${i}">
      <div class="reveal-rays"></div>
      <div class="reveal-art">${brainrotArt(w)}</div>
      ${rarityBadge(w)}
      <div class="reveal-name">${escapeHtml(w.name)}</div>
      <div class="reveal-value">${fmt(w.value)} 🎫</div>
      ${won.length === 1 ? gameInfoHtml(w) : ''}
      ${won.length > 1 ? `<button class="sell-mini" data-sell="${i}">↯ ${fmt(w.sell_payout)} 🎫</button>` : ''}
    </div>`).join('');

  reelsEl.innerHTML = `
    <div class="reveal-wrap ${won.length > 1 ? 'multi' : ''}">${cards}</div>
    ${won.length > 1 ? `<div class="reveal-total">Итого: <b>${fmt(total)} 🎫</b></div>` : ''}`;

  controls.classList.remove('busy');
  controls.innerHTML = `
    <div class="reveal-actions">
      <button class="btn-chip ghost" id="btn-keep">Забрать${won.length > 1 ? ' всё' : ''}</button>
      <button class="btn-chip ghost" id="btn-sell-all">Продать${won.length > 1 ? ' всё' : ''} · ${fmt(payoutTotal)} 🎫</button>
    </div>
    <button class="open-btn" id="btn-again">
      <span class="open-btn-shine"></span>
      <span class="open-btn-label">Ещё раз</span>
      <span class="open-btn-price">${fmt(c.price_tokens * qty)} 🎫</span>
    </button>`;

  const sold = new Set();
  async function sell(i) {
    if (sold.has(i)) return 0;
    sold.add(i);
    const res = await api(`/api/inventory/${won[i].inventory_id}/sell`, { method: 'POST' });
    ME.game_tokens = res.game_tokens;
    stage.querySelector('#stage-tokens').textContent = fmt(res.game_tokens);
    const card = reelsEl.querySelector(`[data-won="${i}"]`);
    card.classList.add('sold');
    const mini = card.querySelector('.sell-mini');
    if (mini) { mini.disabled = true; mini.textContent = `+${fmt(res.payout)} 🎫`; }
    return res.payout;
  }

  reelsEl.querySelectorAll('[data-sell]').forEach((el) =>
    el.addEventListener('click', async () => {
      el.disabled = true;
      try { const p = await sell(Number(el.dataset.sell)); if (p) toast(`+${fmt(p)} 🎫`, 'success'); }
      catch (err) { toast('Ошибка: ' + err.message, 'error'); el.disabled = false; }
    })
  );
  controls.querySelector('#btn-sell-all').addEventListener('click', async (e) => {
    e.currentTarget.disabled = true;
    let sum = 0;
    for (let i = 0; i < won.length; i++) { try { sum += await sell(i); } catch (err) { /* уже продан */ } }
    if (sum) toast(`Продано: +${fmt(sum)} 🎫`, 'success');
    popNumber(stage.querySelector('#stage-tokens'));
  });
  controls.querySelector('#btn-keep').addEventListener('click', () => {
    toast(won.length > 1 ? 'Брейнроты в инвентаре' : `${won[0].name} — в инвентаре`, 'success');
    resetStage(stage, c, qty);
  });
  controls.querySelector('#btn-again').addEventListener('click', () => {
    resetStage(stage, c, qty);
    runOpening(stage, c, qty);
  });
}

function resetStage(stage, c, qty) {
  const reelsEl = stage.querySelector('#stage-reels');
  reelsEl.classList.add('hidden');
  reelsEl.innerHTML = '';
  const art = stage.querySelector('.stage-art .artifact');
  art.classList.remove('charging');
  stage.querySelector('#stage-hero').classList.remove('collapsed');
  paintStageControls(stage, c, qty);
  refreshMe().catch(() => {});
}

function openBrainrotSheet(b) {
  openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div class="reveal" style="${glowVars(b)}">
      <div class="reveal-rays"></div>
      <div class="reveal-art">${brainrotArt(b)}</div>
      ${rarityBadge(b)}
      <div class="reveal-name">${escapeHtml(b.name)}</div>
      <div class="reveal-value">${fmt(b.value)} 🎫 · шанс ${formatChance(b.chance_percent)}</div>
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
      <div class="inv-value">${fmt(i.value)} 🎫</div>
      <button class="inv-sell-btn" data-sell="${i.id}" data-payout="${Math.round(i.value * 0.9)}">Продать · ${Math.round(i.value * 0.9)} 🎫</button>
    </div>`).join('') || '<div class="empty-state" style="grid-column:1/-1">Пусто — открой кейс на главной.</div>';

  root.innerHTML = `
    <div class="section-title">ИНВЕНТАРЬ</div>
    <div class="filter-row">${chips}</div>
    <div class="pill-row">
      <button class="pill sort-pill ${inventorySort === 'value' ? 'active' : ''}" data-sort="value">По цене</button>
      <button class="pill sort-pill ${inventorySort === 'rarity' ? 'active' : ''}" data-sort="rarity">По редкости</button>
      <button class="pill sort-pill ${inventorySort === 'date' ? 'active' : ''}" data-sort="date">По дате</button>
    </div>
    ${items.length ? `<div class="btn-row"><button class="btn btn-ghost" id="btn-sell-all" style="flex:1">💰 Продать всё (${items.length})</button></div>` : ''}
    <div class="inventory-grid">${tiles}</div>
  `;

  root.querySelectorAll('.filter-chip').forEach((el) => el.addEventListener('click', () => { inventoryFilter = el.dataset.r; paintInventory(root, items); }));
  root.querySelectorAll('.sort-pill').forEach((el) => el.addEventListener('click', () => { inventorySort = el.dataset.sort; paintInventory(root, items); }));
  root.querySelectorAll('[data-sell]').forEach((el) => el.addEventListener('click', async (e) => {
    e.stopPropagation();
    el.disabled = true;
    try {
      const res = await api(`/api/inventory/${el.dataset.sell}/sell`, { method: 'POST' });
      toast(`Продано: ${res.sold_name} +${res.payout} 🎫`, 'success');
      ME.game_tokens = res.game_tokens;
      const topBalance = document.getElementById('topbar-tokens');
      if (topBalance) { topBalance.textContent = res.game_tokens; popNumber(topBalance); }
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
        ME.game_tokens = res.game_tokens;
      } catch (err) { /* предмет уже продан/удалён — пропускаем */ }
    }
    toast(`Продано всё: +${total} 🎫`, 'success');
    const topBalance = document.getElementById('topbar-tokens');
    if (topBalance) { topBalance.textContent = ME.game_tokens; popNumber(topBalance); }
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
        <div><span>Демо</span><b>${fmt(me.game_tokens)} 🎫</b></div>
        <div><span>Баланс</span><b>${fmt(me.balance)} 🪙</b></div>
      </div>
    </div>
    <div class="profile-stats">
      <div><b>${inventory.length}</b><span>брейнротов</span></div>
      <div><b>${fmt(total)}</b><span>ценность 🎫</span></div>
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
            <div class="showcase-value">${fmt(b.value)} 🎫</div>
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
  `;
}

// =================================================================== АПГРЕЙДЕР

let upgraderState = { contribution: null, target: null };
let upgraderSpinning = false;

function ringArc(pct) {
  // SVG-дуга зоны успеха: от 12 часов по часовой стрелке на pct% окружности.
  const r = 88, c = 2 * Math.PI * r;
  return `<circle class="upg-zone" cx="100" cy="100" r="${r}" stroke-dasharray="${(c * pct) / 100} ${c}" />`;
}

async function renderUpgraderScreen(root) {
  const { contribution, target } = upgraderState;
  const chance = contribution && target ? (target.chance_percent || computeChance(contribution.value, target.value)) : 0;
  const mult = contribution && target ? (target.value / contribution.value).toFixed(2) : null;

  const slot = (b, label, id) => `
    <button class="upg-slot ${b ? 'filled' : ''}" id="${id}" style="${b ? glowVars(b) : ''}">
      ${b ? `${brainrotArt(b)}<div class="upg-slot-name">${escapeHtml(b.name)}</div><div class="upg-slot-value">${fmt(b.value)} 🎫</div>`
          : `<div class="upg-slot-plus">+</div><div class="upg-slot-label">${label}</div>`}
    </button>`;

  root.innerHTML = `
    <div class="section-title">АПГРЕЙДЕР</div>
    <div class="upg-stage" id="upg-stage">
      <div class="upg-ring-wrap">
        <svg class="upg-ring" viewBox="0 0 200 200">
          <circle class="upg-track" cx="100" cy="100" r="88"/>
          ${ringArc(chance)}
          ${Array.from({ length: 60 }, (_, i) => `<line class="upg-tick ${i % 5 ? '' : 'major'}" x1="100" y1="${i % 5 ? 6 : 4}" x2="100" y2="${i % 5 ? 11 : 13}" transform="rotate(${i * 6} 100 100)"/>`).join('')}
        </svg>
        <div class="upg-needle" id="upg-needle"><span></span></div>
        <div class="upg-center">
          <div class="upg-chance" id="upg-chance">${contribution && target ? chance + '%' : '—'}</div>
          <div class="upg-label">${mult ? '×' + mult : 'ШАНС'}</div>
        </div>
      </div>
      <div class="upg-slots">
        ${slot(contribution, 'Твой брейнрот', 'slot-contribution')}
        <div class="upg-arrow">➜</div>
        ${slot(target, 'Цель', 'slot-target')}
      </div>
    </div>
    <button class="open-btn upg-btn" id="btn-spin" ${contribution && target ? '' : 'disabled'} style="--c1:#c6ff3d;--c2:#5dffb0">
      <span class="open-btn-shine"></span>
      <span class="open-btn-label">Прокачать</span>
      <span class="open-btn-price">${contribution && target ? chance + '%' : '—'}</span>
    </button>
    <button class="btn btn-ghost" style="margin-top:8px" id="btn-reset">Сбросить</button>
    <p class="fine-print">Зелёная зона — твой шанс. Стрелка остановится в ней — получаешь цель, мимо — вклад сгорает. Исход решает сервер до начала анимации.</p>
  `;

  root.querySelector('#slot-contribution').addEventListener('click', async () => {
    if (upgraderSpinning) return;
    const items = await api('/api/inventory?limit=200');
    openItemPicker(items, (item) => {
      upgraderState = { contribution: item, target: null };
      renderUpgraderScreen(root);
    });
  });
  root.querySelector('#slot-target').addEventListener('click', async () => {
    if (upgraderSpinning) return;
    if (!upgraderState.contribution) { toast('Сначала выбери своего брейнрота', 'error'); return; }
    const c = upgraderState.contribution;
    const targets = await api(`/api/upgrader/targets?min_value=${c.value}&exclude_name=${encodeURIComponent(c.name)}`);
    openTargetPicker(targets, (t) => { upgraderState.target = t; renderUpgraderScreen(root); });
  });
  root.querySelector('#btn-reset').addEventListener('click', () => {
    if (upgraderSpinning) return;
    upgraderState = { contribution: null, target: null };
    renderUpgraderScreen(root);
  });

  const spinBtn = root.querySelector('#btn-spin');
  spinBtn.addEventListener('click', async () => {
    if (upgraderSpinning || !contribution || !target) return;
    upgraderSpinning = true;
    spinBtn.disabled = true;
    haptic.impact('heavy');
    let res;
    try {
      res = await api('/api/upgrader/spin', {
        method: 'POST',
        body: JSON.stringify({ contribution_item_id: contribution.id, target_name: target.name }),
      });
    } catch (err) {
      upgraderSpinning = false;
      spinBtn.disabled = false;
      toast('Ошибка: ' + err.message, 'error');
      return;
    }

    // Стрелка: 5 полных оборотов + точка остановки из ответа сервера.
    const needle = root.querySelector('#upg-needle');
    const stage = root.querySelector('#upg-stage');
    const finalDeg = 360 * 5 + (res.roll_point / 100) * 360;
    const duration = CaseArt.REDUCED ? 300 : 4200;
    const start = performance.now();
    const ease = (t) => 1 - Math.pow(1 - t, 4);
    let lastTick = 0;
    await new Promise((resolve) => {
      function frame(now) {
        const t = Math.min(1, (now - start) / duration);
        const deg = finalDeg * ease(t);
        needle.style.transform = `rotate(${deg}deg)`;
        if (Math.floor(deg / 12) !== lastTick) { lastTick = Math.floor(deg / 12); if (t < 0.95) haptic.tick(); }
        if (t < 1) requestAnimationFrame(frame); else resolve();
      }
      requestAnimationFrame(frame);
    });

    stage.classList.add(res.success ? 'upg-win' : 'upg-lose');
    if (res.success) haptic.success(); else haptic.impact('rigid');
    await sleep(CaseArt.REDUCED ? 50 : 700);
    upgraderSpinning = false;
    upgraderState = { contribution: null, target: null };
    refreshMe().catch(() => {});
    showUpgradeResult(root, res, contribution, target);
  });
}

function showUpgradeResult(root, res, contribution, target) {
  const b = res.success ? res.won_item : contribution;
  const overlay = openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div class="reveal ${res.success ? '' : 'upg-lost'}" style="${glowVars(b)}">
      <div class="reveal-rays"></div>
      <div class="upg-result-title">${res.success ? 'Прокачано!' : 'Не повезло'}</div>
      <div class="reveal-art">${brainrotArt(b)}</div>
      ${rarityBadge(b)}
      <div class="reveal-name">${escapeHtml(b.name)}</div>
      <div class="reveal-value">${res.success ? '+' : '−'}${fmt(b.value)} 🎫</div>
      <div class="muted" style="position:relative">Шанс был ${res.chance}%</div>
    </div>
    <button class="btn btn-primary" style="margin-top:14px" id="upg-again">Ещё апгрейд</button>
  `);
  overlay.querySelector('#upg-again').addEventListener('click', () => { closeModal(); renderUpgraderScreen(root); });
  overlay.addEventListener('click', (e) => { if (e.target === overlay) renderUpgraderScreen(root); });
  overlay.querySelector('.modal-close').addEventListener('click', () => renderUpgraderScreen(root));
}

// Запасной расчёт (сервер присылает chance_percent у каждой цели): те же
// границы, что UPGRADER_MIN/MAX_CHANCE_PERCENT на сервере — минимум 75%.
function computeChance(contributionValue, targetValue) {
  if (targetValue <= 0) return 95;
  const raw = Math.round((contributionValue / targetValue) * 100);
  return Math.max(75, Math.min(95, raw));
}

function openBrainrotPicker(title, list, emptyText, onPick) {
  const tiles = list.map((b, idx) => `
    <button class="pick-tile" style="${glowVars(b)}" data-idx="${idx}">
      ${brainrotArt(b)}
      <div class="pick-name">${escapeHtml(b.name)}</div>
      <div class="pick-value">${fmt(b.value)} 🎫</div>
    </button>`).join('') || `<div class="empty-state" style="grid-column:1/-1">${emptyText}</div>`;
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

let crashPollTimer = null;
let crashRaf = 0;

function stopCrashLoops() {
  clearInterval(crashPollTimer);
  cancelAnimationFrame(crashRaf);
}

function crashMultiplierAt(curve, seconds) {
  const raw = Math.pow(1 + curve.growth_rate, seconds / curve.tick_seconds);
  return Math.min(raw, curve.max_multiplier);
}

async function renderCrashScreen(root) {
  stopCrashLoops();
  const state = await api('/api/crash/state');
  const history = (state.history || '').split(',').map((h) => h.trim()).filter((h) => h && h !== '—');
  root.innerHTML = `
    <div class="section-title">КРАШ</div>
    <div class="crash-history">${history.slice(-10).reverse().map((h) => {
      const v = parseFloat(h);
      return `<span class="crash-chip ${v >= 2 ? 'hi' : v < 1.2 ? 'lo' : ''}">${escapeHtml(h)}</span>`;
    }).join('') || '<span class="muted">История раундов появится после первого полёта</span>'}</div>
    <div class="crash-board" id="crash-board">
      <svg class="crash-graph" viewBox="0 0 300 180" preserveAspectRatio="none">
        <defs>
          <linearGradient id="crashFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c6ff3d" stop-opacity=".35"/><stop offset="1" stop-color="#c6ff3d" stop-opacity="0"/></linearGradient>
        </defs>
        <g class="crash-grid">${[36, 72, 108, 144].map((y) => `<line x1="0" x2="300" y1="${y}" y2="${y}"/>`).join('')}</g>
        <path id="crash-area" fill="url(#crashFill)" d=""/>
        <path id="crash-line" class="crash-line" d=""/>
        <circle id="crash-dot" class="crash-dot" r="5" cx="0" cy="180"/>
      </svg>
      <div class="crash-readout">
        <div class="crash-mult" id="crash-mult">1.00×</div>
        <div class="crash-status" id="crash-status">ГОТОВ К СТАРТУ</div>
      </div>
    </div>
    <div class="crash-stake" id="crash-stake"></div>
    <div id="crash-actions"></div>
  `;
  paintCrashControls(root, state);
  if (state.active) runCrashRound(root, state);
}

function paintCrashControls(root, state, pickedItem = null) {
  const stake = state.active ? state.stake : pickedItem;
  root.querySelector('#crash-stake').innerHTML = stake ? `
    <div class="stake-card" style="${glowVars(stake)}">
      ${brainrotArt(stake)}
      <div><div class="stake-name">${escapeHtml(stake.name)}</div><div class="stake-value">Ставка · ${fmt(stake.value)} 🎫</div></div>
      <div class="stake-win" id="crash-potential">${state.active ? '' : ''}</div>
    </div>` : '';
  const actions = root.querySelector('#crash-actions');
  if (state.active) {
    actions.innerHTML = `<button class="open-btn" id="btn-crash-cashout" style="--c1:#ffd24d;--c2:#ff9d2e"><span class="open-btn-shine"></span><span class="open-btn-label">Забрать</span><span class="open-btn-price" id="crash-cash-value">—</span></button>`;
    actions.querySelector('#btn-crash-cashout').addEventListener('click', async (e) => {
      e.currentTarget.disabled = true;
      try {
        const res = await api('/api/crash/cashout', { method: 'POST' });
        stopCrashLoops();
        haptic.success();
        const board = root.querySelector('#crash-board');
        board.classList.add('cashed');
        root.querySelector('#crash-mult').textContent = res.multiplier.toFixed(2) + '×';
        root.querySelector('#crash-status').textContent = `ЗАБРАНО · ${fmt(res.won_item.value)} 🎫`;
        refreshMe().catch(() => {});
        setTimeout(() => { if (location.hash === '#crash') renderCrashScreen(root); }, 2200);
      } catch (err) {
        toast('Не успел — ракета уже взорвалась', 'error');
      }
    });
    return;
  }
  actions.innerHTML = `
    <div class="btn-row">
      <button class="btn btn-ghost" id="btn-crash-pick">${pickedItem ? 'Сменить брейнрота' : 'Выбрать брейнрота'}</button>
    </div>
    <button class="open-btn" id="btn-crash-start" ${pickedItem ? '' : 'disabled'} style="--c1:#c6ff3d;--c2:#5dffb0">
      <span class="open-btn-shine"></span><span class="open-btn-label">Взлёт</span><span class="open-btn-price">${pickedItem ? fmt(pickedItem.value) + ' 🎫' : '—'}</span>
    </button>`;
  actions.querySelector('#btn-crash-pick').addEventListener('click', async () => {
    const items = await api('/api/inventory?limit=200');
    openItemPicker(items, (item) => paintCrashControls(root, state, item));
  });
  const startBtn = actions.querySelector('#btn-crash-start');
  startBtn.addEventListener('click', async () => {
    if (!pickedItem) return;
    startBtn.disabled = true;
    try {
      const res = await api('/api/crash/start', { method: 'POST', body: JSON.stringify({ item_id: pickedItem.id }) });
      haptic.impact('heavy');
      paintCrashControls(root, res);
      runCrashRound(root, res);
    } catch (err) {
      toast('Ошибка: ' + err.message, 'error');
      startBtn.disabled = false;
    }
  });
}

/** Кривая рисуется локально по той же формуле, что и на сервере; сервер
 * опрашивается только чтобы узнать момент взрыва (точку краша знает он один). */
function runCrashRound(root, state) {
  stopCrashLoops();
  const t0 = performance.now() - state.elapsed * 1000;
  const line = root.querySelector('#crash-line');
  const area = root.querySelector('#crash-area');
  const dot = root.querySelector('#crash-dot');
  const multEl = root.querySelector('#crash-mult');
  const statusEl = root.querySelector('#crash-status');
  const board = root.querySelector('#crash-board');
  board.classList.remove('crashed', 'cashed');
  board.classList.add('flying');
  statusEl.textContent = 'В ПОЛЁТЕ';
  let ended = false;

  function draw(now) {
    if (ended) return;
    const secs = (now - t0) / 1000;
    const m = crashMultiplierAt(state, secs);
    const span = Math.max(6, secs * 1.15);
    const top = Math.max(2, m * 1.2);
    const pts = [];
    for (let i = 0; i <= 40; i++) {
      const s = (secs * i) / 40;
      const x = (s / span) * 300;
      const y = 180 - ((crashMultiplierAt(state, s) - 1) / (top - 1)) * 170;
      pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }
    const d = 'M' + pts.join(' L');
    line.setAttribute('d', d);
    area.setAttribute('d', d + ` L${pts[pts.length - 1].split(',')[0]},180 L0,180 Z`);
    const [lx, ly] = pts[pts.length - 1].split(',');
    dot.setAttribute('cx', lx); dot.setAttribute('cy', ly);
    multEl.textContent = m.toFixed(2) + '×';
    const cash = root.querySelector('#crash-cash-value');
    if (cash && state.stake) cash.textContent = fmt(Math.round(state.stake.value * m)) + ' 🎫';
    crashRaf = requestAnimationFrame(draw);
  }
  crashRaf = requestAnimationFrame(draw);

  crashPollTimer = setInterval(async () => {
    try {
      const s = await api('/api/crash/state');
      if (s.active) return;
      ended = true;
      stopCrashLoops();
      if (s.crashed || !s.active) {
        board.classList.remove('flying');
        board.classList.add('crashed');
        multEl.textContent = (s.multiplier || 1).toFixed(2) + '×';
        statusEl.textContent = 'ВЗРЫВ';
        haptic.impact('rigid');
        const actions = root.querySelector('#crash-actions');
        if (actions) actions.innerHTML = `<button class="open-btn" disabled style="--c1:#ff4d6d;--c2:#ff8a5c"><span class="open-btn-label">Ставка сгорела</span><span class="open-btn-price">${(s.multiplier || 1).toFixed(2)}×</span></button>`;
        setTimeout(() => { if (location.hash === '#crash') renderCrashScreen(root); }, 2200);
      }
    } catch (e) { /* сеть моргнула — следующий опрос */ }
  }, 500);
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
      <div class="dice-verdict" id="dice-verdict">${color ? `Ставка на <b style="color:${DICE_COLORS[color][0]}">${DICE_COLORS[color][1].toLowerCase()}</b>` : 'Выбери цвет и брейнрота'}</div>
    </div>

    <button class="stake-card stake-pick" id="dice-pick" style="${item ? glowVars(item) : ''}">
      ${item ? `${brainrotArt(item)}<div><div class="stake-name">${escapeHtml(item.name)}</div><div class="stake-value">Ставка · ${fmt(item.value)} 🎫</div></div><span class="stake-change">Сменить</span>`
             : `<div class="upg-slot-plus">+</div><div><div class="stake-name">Выбери брейнрота</div><div class="stake-value">Он станет ставкой</div></div>`}
    </button>

    <div class="color-pick">
      ${rules.colors.map((c) => `
        <button class="gem ${c === color ? 'active' : ''}" style="--gc:${DICE_COLORS[c][0]}" data-color="${c}" aria-label="${DICE_COLORS[c][1]}"><span></span></button>`).join('')}
    </div>

    <button class="open-btn" id="btn-dice-roll" ${item && color ? '' : 'disabled'} style="--c1:${color ? DICE_COLORS[color][0] : '#c6ff3d'};--c2:#ffffff">
      <span class="open-btn-shine"></span><span class="open-btn-label">Бросить</span>
      <span class="open-btn-price">${item ? fmt(item.value) + ' 🎫' : '—'}</span>
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
  });
}

function showDiceVerdict(root, rules, res) {
  const verdict = root.querySelector('#dice-verdict');
  const table = root.querySelector('#dice-table');
  table.classList.add(res.win ? 'won' : 'lost');
  if (res.win) haptic.success(); else haptic.impact('rigid');
  verdict.innerHTML = res.win
    ? `<span class="v-win">${res.bonus ? 'Радужный бонус!' : `Совпадений: ${res.match_count}`} · ×${res.multiplier}</span><span class="v-sub">${escapeHtml(res.won_item.name)} → ${fmt(res.won_item.value)} 🎫</span>`
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
    <p class="screen-lead">Дуэль 1×1: ты и соперник открываете один и тот же кейс. У кого дроп дороже — забирает оба брейнрота. Ничья — возврат ставки.</p>
    <div class="case-grid battle-grid">
      ${cases.map((c, idx) => `
        <button class="case-card battle-card fade-in-up" style="${caseThemeVars(c)};animation-delay:${Math.min(idx * 40, 320)}ms" data-id="${c.id}">
          <div class="case-card-glow"></div>
          <div class="case-card-art">${CaseArt.artifact(c, 'artifact-sm')}</div>
          <div class="case-card-body">
            <div class="case-card-name">${escapeHtml(c.name)}</div>
            <div class="case-card-foot"><span class="case-card-count">вход</span><span class="price-chip">${fmt(c.price_tokens)} 🎫</span></div>
          </div>
        </button>`).join('') || '<div class="empty-state">Нет доступных кейсов для батла.</div>'}
    </div>`;
  root.querySelectorAll('[data-id]').forEach((el) =>
    el.addEventListener('click', () => startBattle(root, cases.find((c) => c.id === Number(el.dataset.id))))
  );
}

async function startBattle(root, c) {
  if (ME && ME.game_tokens < c.price_tokens) { toast(`Нужно ${fmt(c.price_tokens)} 🎫`, 'error'); return; }
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
    side.querySelector('.duel-value').innerHTML = `<b>${escapeHtml(b.name)}</b><span>${fmt(b.value)} 🎫</span>`;
    side.classList.add('landed');
  };
  put('#duel-me', res.player_item);
  await sleep(350);
  put('#duel-bot', res.bot_item);
  await sleep(450);
  const meSide = overlay.querySelector('#duel-me'), botSide = overlay.querySelector('#duel-bot');
  const verdict = overlay.querySelector('#duel-verdict');
  if (res.winner === 'player') { meSide.classList.add('win'); botSide.classList.add('lose'); verdict.innerHTML = `<span class="v-win">Победа · +${fmt(res.player_item.value + res.bot_item.value)} 🎫</span>`; haptic.success(); }
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
          <span class="item-value">+${q.reward_tokens} 🎫</span>
          ${q.claimable ? `<button class="btn btn-gold" style="width:auto;padding:8px 16px" data-claim="${q.id}">ЗАБРАТЬ</button>` : ''}
        </div>
      </div>`).join('')}` : '';

  root.innerHTML = `
    <div class="section-title">КВЕСТЫ</div>
    <div class="balance-line">Баланс: <b>${me.game_tokens} 🎫</b></div>
    ${renderGroup(scopeLabel.daily, groups.daily)}
    ${renderGroup(scopeLabel.weekly, groups.weekly)}
  `;

  root.querySelectorAll('[data-claim]').forEach((el) =>
    el.addEventListener('click', async () => {
      try {
        const res = await api(`/api/quests/${el.dataset.claim}/claim`, { method: 'POST' });
        toast(`+${res.reward} 🎫`, 'success');
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

async function renderFaqScreen(root) {
  const entries = await api('/api/faq');
  root.innerHTML = `
    <div class="section-title">FAQ</div>
    ${entries.map((e) => `
      <div class="card">
        <div style="font-weight:800;margin-bottom:6px">${escapeHtml(e.question)}</div>
        <div class="muted">${escapeHtml(e.answer)}</div>
      </div>`).join('')}
  `;
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
      <div class="stat-box"><div class="stat-label">Заработано</div><div class="stat-value">${r.earned_total} 🪙</div></div>
    </div>
  `;
}

async function renderStakingTab(body) {
  const s = await api('/api/staking');
  if (s.active) {
    body.innerHTML = `
      <div class="card">
        <div class="muted">АКТИВНЫЙ СТЕЙК</div>
        <div style="font-weight:800;font-size:18px;margin:6px 0">${s.active.amount} 🪙 на ${s.active.term_days} дн. (+${s.active.bonus_percent}%)</div>
        <div class="muted">Погашение: ${new Date(s.active.matures_at).toLocaleString('ru-RU')}</div>
        <div class="muted">Выплата: ${s.active.payout} 🪙</div>
        ${s.active.matured
          ? '<button class="btn btn-gold" id="btn-stake-claim" style="margin-top:10px">ЗАБРАТЬ</button>'
          : '<div class="muted" style="margin-top:10px">Забрать раньше срока нельзя.</div>'}
      </div>
      ${stakingStatsHtml(s)}
    `;
    body.querySelector('#btn-stake-claim')?.addEventListener('click', async () => {
      try {
        const res = await api(`/api/staking/${s.active.id}/claim`, { method: 'POST' });
        toast(`+${res.payout} 🪙`, 'success');
        renderStakingTab(body);
      } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
    });
    return;
  }

  body.innerHTML = `
    <div class="card">
      <p class="muted">Заморозь 🪙 и забирай их обратно с надбавкой. Минимум ${s.min_amount} 🪙. Твой баланс: ${s.balance} 🪙.</p>
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
      <div class="stat-box"><div class="stat-label">Заморожено всего</div><div class="stat-value">${s.total_frozen} 🪙</div></div>
      <div class="stat-box"><div class="stat-label">Заработано сверху</div><div class="stat-value">${s.total_bonus} 🪙</div></div>
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
