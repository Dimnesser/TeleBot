/* Brainrot Battle Mini App — vanilla JS SPA, без сборки/зависимостей. */

const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  if (tg.setHeaderColor) try { tg.setHeaderColor('#08090f'); } catch (e) {}
  if (tg.setBackgroundColor) try { tg.setBackgroundColor('#08090f'); } catch (e) {}
}

// Диагностическая страховка: любая необработанная ошибка/rejection раньше
// просто вешала экран молча ("не открывается") — теперь хотя бы видно, что
// именно сломалось, вместо тишины.
window.addEventListener('error', (e) => {
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
  document.getElementById('drawer-balance').textContent = ME.balance;
  const topBalance = document.getElementById('topbar-tokens');
  if (topBalance) {
    topBalance.textContent = ME.game_tokens;
    if (prevTokens !== null && prevTokens !== ME.game_tokens) popNumber(topBalance);
  }
  return ME;
}

// ------------------------------------------------------------------- drawer

const DRAWER_SECTIONS = [
  ['home', '🏠 ГЛАВНАЯ'],
  ['deposit', '💰 ПОПОЛНИТЬ БАЛАНС'],
  ['upgrader', '⬆️ АПГРЕЙДЕР'],
  ['battle', '🛡️ БАТЛ'],
  ['dice', '🎲 ДАЙСЫ'],
  ['crash', '🚀 КРАШ'],
  ['inventory', '🎒 ИНВЕНТАРЬ'],
  ['quests', '📋 КВЕСТЫ'],
  ['giveaways', '🏆 РОЗЫГРЫШИ'],
  ['faq', '❓ FAQ'],
  ['bonuses', '🍀 БОНУСЫ'],
];

function renderDrawer(active) {
  const root = document.getElementById('drawer-items');
  root.innerHTML = '';
  for (const [key, label] of DRAWER_SECTIONS) {
    const btn = document.createElement('button');
    btn.className = 'drawer-item' + (key === active ? ' active' : '');
    btn.textContent = label;
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
  const cardW = cards[0].getBoundingClientRect().width + parseFloat(getComputedStyle(track).columnGap || '0');
  const viewW = reelEl.clientWidth;
  const center = revealIndex * cardW + cardW / 2 - viewW / 2;
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
    const idx = Math.floor((x + viewW / 2) / cardW);
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
    const rc = r === 'all' ? '#5b7cfa' : (items.find((i) => i.rarity === r) || {}).rarity_color || '#8a93a8';
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

async function renderProfileScreen(root) {
  const [me, inventory] = await Promise.all([refreshMe(), api('/api/inventory?limit=50')]);
  const bestDrop = inventory.slice().sort((a, b) => b.value - a.value)[0];
  const rarityCounts = {};
  inventory.forEach((i) => { rarityCounts[i.rarity] = (rarityCounts[i.rarity] || 0) + 1; });

  root.innerHTML = `
    <div class="section-title">ПРОФИЛЬ</div>
    <div class="card">
      <div style="display:flex;align-items:center;gap:12px">
        <div class="avatar" style="width:54px;height:54px;font-size:26px">🧑‍💻</div>
        <div>
          <div style="font-weight:800">${me.username ? '@' + escapeHtml(me.username) : escapeHtml(me.first_name || 'игрок')}</div>
          <div class="muted">Telegram id: ${me.tg_id}</div>
        </div>
      </div>
    </div>
    <div class="stat-grid">
      <div class="stat-box"><div class="stat-label">Реальный баланс</div><div class="stat-value">${me.balance} 🪙</div></div>
      <div class="stat-box"><div class="stat-label">Демо-фишки</div><div class="stat-value">${me.game_tokens} 🎫</div></div>
      <div class="stat-box"><div class="stat-label">Предметов в инвентаре</div><div class="stat-value">${inventory.length}</div></div>
      <div class="stat-box"><div class="stat-label">Рефералов</div><div class="stat-value">${me.referral_count}</div></div>
    </div>
    ${bestDrop ? `
      <h4 style="margin:18px 0 8px">Лучший дроп</h4>
      <div class="reveal-card" style="--rc:${bestDrop.rarity_color};padding:16px">
        ${brainrotArt(bestDrop)}
        <style>#app .reveal-card .p-tile{width:64px;height:64px;font-size:24px;margin:0 auto 8px}</style>
        ${rarityBadge(bestDrop)}
        <div class="reveal-name" style="font-size:15px;margin-top:6px">${escapeHtml(bestDrop.name)}</div>
        <div class="reveal-value" style="font-size:16px;--rc:${bestDrop.rarity_color}">${fmt(bestDrop.value)} 🎫</div>
      </div>` : ''}
    <button class="btn btn-ghost" style="margin-top:8px" onclick="navigate('inventory')">🎒 Весь инвентарь</button>
  `;
}

// =================================================================== АПГРЕЙДЕР

let upgraderState = { contribution: null, target: null };

async function renderUpgraderScreen(root) {
  const { contribution, target } = upgraderState;
  const chance = contribution && target ? computeChance(contribution.value, target.value) : null;

  root.innerHTML = `
    <div class="section-title">АПГРЕЙДЕР</div>
    <div class="dial-wrap">
      <div class="dial" style="background:conic-gradient(var(--r-mythic) ${chance ?? 0}%, #1a1c22 0)">
        <div class="dial" style="width:150px;height:150px;background:var(--bg);display:flex;flex-direction:column;align-items:center;justify-content:center">
          <div class="dial-chance">${chance !== null ? chance + '%' : '—'}</div>
          <div class="dial-label">ШАНС</div>
        </div>
      </div>
    </div>
    <div class="slot-row">
      <button class="slot ${contribution ? 'filled' : ''}" id="slot-contribution">
        ${contribution ? `${brainrotArt(contribution)}${escapeHtml(contribution.name)}<br><span class="item-value">${fmt(contribution.value)} 🎫</span>` : 'ТВОЙ ВКЛАД<br>выбрать из инвентаря'}
      </button>
      <div class="slot-arrow">→</div>
      <button class="slot ${target ? 'filled' : ''}" id="slot-target">
        ${target ? `${brainrotArt(target)}${escapeHtml(target.name)}<br><span class="item-value">${fmt(target.value)} 🎫</span>` : 'ЖЕЛАЕМЫЙ ПРЕДМЕТ<br>выбрать цель'}
      </button>
    </div>
    <button class="btn btn-primary" id="btn-spin" ${contribution && target ? '' : 'disabled'}>ПРОКАЧАТЬ</button>
    <button class="btn btn-ghost" style="margin-top:8px" id="btn-reset">Сбросить</button>
  `;

  root.querySelector('#slot-contribution').addEventListener('click', async () => {
    const items = await api('/api/inventory?limit=100');
    openItemPicker(items, (item) => {
      upgraderState.contribution = item;
      upgraderState.target = null;
      renderUpgraderScreen(root);
    });
  });

  root.querySelector('#slot-target').addEventListener('click', async () => {
    if (!contribution) { toast('Сначала выбери вклад', 'error'); return; }
    const targets = await api(`/api/upgrader/targets?min_value=${contribution.value}&exclude_name=${encodeURIComponent(contribution.name)}`);
    openTargetPicker(targets, (t) => {
      upgraderState.target = t;
      renderUpgraderScreen(root);
    });
  });

  root.querySelector('#btn-reset').addEventListener('click', () => {
    upgraderState = { contribution: null, target: null };
    renderUpgraderScreen(root);
  });

  const spinBtn = root.querySelector('#btn-spin');
  if (spinBtn) spinBtn.addEventListener('click', async () => {
    spinBtn.disabled = true;
    try {
      const res = await api('/api/upgrader/spin', {
        method: 'POST',
        body: JSON.stringify({
          contribution_item_id: contribution.id,
          target_name: target.name,
          target_value: target.value,
        }),
      });
      upgraderState = { contribution: null, target: null };
      if (res.success) toast(`✅ Успех! Получен: ${res.won_item.name} (${fmt(res.won_item.value)} 🎫)`, 'success');
      else toast('❌ Не повезло, предмет потерян.', 'error');
      renderUpgraderScreen(root);
    } catch (err) {
      toast('Ошибка: ' + err.message, 'error');
      spinBtn.disabled = false;
    }
  });
}

function computeChance(contributionValue, targetValue) {
  if (targetValue <= 0) return 95;
  const raw = Math.round((contributionValue / targetValue) * 100);
  return Math.max(1, Math.min(95, raw));
}

function openItemPicker(items, onPick) {
  const rows = items.map((i) => `
    <button class="item-row" style="width:100%;background:none;border:none;color:inherit;cursor:pointer;--rc:${i.rarity_color}" data-id="${i.id}">
      ${brainrotArt(i)}<span style="flex:1;margin:0 8px;text-align:left">${escapeHtml(i.name)}</span><span class="item-value" style="color:${i.rarity_color}">${fmt(i.value)} 🎫</span>
    </button>`).join('') || '<div class="empty-state">Инвентарь пуст — сначала открой кейс.</div>';
  const overlay = openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <h3>Выбери предмет</h3>
    <style>#active-modal .item-row .p-tile{width:36px;height:36px;font-size:14px;flex-shrink:0}</style>
    <div class="card" style="padding:0;max-height:400px;overflow-y:auto">${rows}</div>
  `);
  overlay.querySelectorAll('[data-id]').forEach((el) =>
    el.addEventListener('click', () => {
      const item = items.find((i) => i.id === Number(el.dataset.id));
      closeModal();
      onPick(item);
    })
  );
}

function openTargetPicker(targets, onPick) {
  const rows = targets.map((t, idx) => `
    <button class="item-row" style="width:100%;background:none;border:none;color:inherit;cursor:pointer;--rc:${t.rarity_color}" data-idx="${idx}">
      ${brainrotArt(t)}<span style="flex:1;margin:0 8px;text-align:left">${escapeHtml(t.name)}</span><span class="item-value" style="color:${t.rarity_color}">${fmt(t.value)} 🎫</span>
    </button>`).join('') || '<div class="empty-state">Нет подходящих целей дороже вклада.</div>';
  const overlay = openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <h3>Желаемый предмет</h3>
    <style>#active-modal .item-row .p-tile{width:36px;height:36px;font-size:14px;flex-shrink:0}</style>
    <div class="card" style="padding:0;max-height:400px;overflow-y:auto">${rows}</div>
  `);
  overlay.querySelectorAll('[data-idx]').forEach((el) =>
    el.addEventListener('click', () => {
      const t = targets[Number(el.dataset.idx)];
      closeModal();
      onPick(t);
    })
  );
}

// =================================================================== КРАШ

let crashPollTimer = null;

async function renderCrashScreen(root) {
  clearInterval(crashPollTimer);
  const state = await api('/api/crash/state');
  paintCrash(root, state);

  root.querySelector('#btn-crash-pick')?.addEventListener('click', async () => {
    const items = await api('/api/inventory?limit=100');
    openItemPicker(items, async (item) => {
      try {
        await api('/api/crash/start', { method: 'POST', body: JSON.stringify({ item_id: item.id }) });
        startCrashPolling(root);
      } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
    });
  });

  root.querySelector('#btn-crash-cashout')?.addEventListener('click', async () => {
    try {
      const res = await api('/api/crash/cashout', { method: 'POST' });
      clearInterval(crashPollTimer);
      toast(`💰 Забрано ×${res.multiplier}: ${res.won_item.name} (${fmt(res.won_item.value)} 🎫)`, 'success');
      renderCrashScreen(root);
    } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
  });

  if (state.active) startCrashPolling(root);
}

function startCrashPolling(root) {
  clearInterval(crashPollTimer);
  crashPollTimer = setInterval(async () => {
    try {
      const state = await api('/api/crash/state');
      paintCrash(root, state);
      if (!state.active) {
        clearInterval(crashPollTimer);
        if (state.crashed) toast(`💥 Крах на ×${state.multiplier}`, 'error');
      }
    } catch (e) { clearInterval(crashPollTimer); }
  }, 900);
}

function paintCrash(root, state) {
  const stakeLabel = state.stake ? `${escapeHtml(state.stake.name)} (${fmt(state.stake.value)} 🎫)` : 'предмет не выбран';
  root.innerHTML = `
    <div class="section-title">КРАШ</div>
    <div class="muted" style="text-align:center">История: ${state.history}</div>
    <div class="crash-stage">
      <div class="crash-rocket">🚀</div>
      <div class="crash-multiplier ${state.crashed ? 'crashed' : ''}">${(state.multiplier ?? 1).toFixed(2)}x</div>
      <div class="crash-status">${state.active ? 'В ПОЛЁТЕ' : state.crashed ? 'КРАХ' : 'ГОТОВ К СТАРТУ'}</div>
    </div>
    <div class="muted" style="margin-bottom:10px">Ставка: ${stakeLabel}</div>
    ${state.active
      ? '<button class="btn btn-gold" id="btn-crash-cashout">ЗАБРАТЬ ✋</button>'
      : '<button class="btn btn-primary" id="btn-crash-pick">Выбрать брейнрота и начать</button>'}
  `;
}

// =================================================================== ДАЙСЫ

let diceState = { item: null, color: null };

async function renderDiceScreen(root) {
  const rules = await api('/api/dice/rules');
  paintDice(root, rules);
}

function paintDice(root, rules) {
  const { item, color } = diceState;
  const colorMap = { '🔴': '#e5484d', '🟠': '#f0923c', '🟡': '#f0c043', '🟢': '#3ecf6e', '🔵': '#4c6fe0', '🟣': '#a04cf0' };
  const colors = rules.colors.map((c) => `<button class="color-dot ${c === color ? 'active' : ''}" style="background:${colorMap[c] || '#888'}" data-color="${c}"></button>`).join('');
  const rulesRows = Object.entries(rules.payout_table).map(([count, mult]) =>
    `<div class="item-row"><span>${count}/4 совпадений</span><span class="${mult ? 'item-value' : ''}">${mult ? `×${mult}` : 'проигрыш'}</span></div>`
  ).join('');

  root.innerHTML = `
    <div class="section-title">ДАЙСЫ</div>
    <button class="slot ${item ? 'filled' : ''}" id="slot-dice-item" style="width:100%;margin-bottom:10px;flex-direction:row;gap:10px">
      ${item ? `${brainrotArt(item)}Ставка: ${escapeHtml(item.name)} — ${fmt(item.value)} 🎫` : 'Выбрать предмет из инвентаря'}
    </button>
    <div class="color-row">${colors}</div>
    <button class="btn btn-primary" id="btn-dice-roll" ${item && color ? '' : 'disabled'}>БРОСИТЬ</button>
    <h4 style="margin:18px 0 8px">Правила игры</h4>
    <div class="card" style="padding:0">
      ${rulesRows}
      <div class="item-row"><span>🌈 БОНУС (${rules.bonus_chance_percent}%)</span><span class="item-value">×${rules.bonus_multiplier}</span></div>
    </div>
  `;

  root.querySelector('#slot-dice-item').addEventListener('click', async () => {
    const items = await api('/api/inventory?limit=100');
    openItemPicker(items, (i) => { diceState.item = i; paintDice(root, rules); });
  });
  root.querySelectorAll('.color-dot').forEach((el) =>
    el.addEventListener('click', () => { diceState.color = el.dataset.color; paintDice(root, rules); })
  );
  const rollBtn = root.querySelector('#btn-dice-roll');
  if (rollBtn) rollBtn.addEventListener('click', async () => {
    rollBtn.disabled = true;
    try {
      const res = await api('/api/dice/roll', {
        method: 'POST',
        body: JSON.stringify({ item_id: diceState.item.id, color: diceState.color }),
      });
      diceState = { item: null, color: null };
      const diceStr = res.dice.join(' ');
      if (res.win) toast(`${diceStr} — совпадений: ${res.match_count}${res.bonus ? ' 🌈 БОНУС' : ''}. Выигрыш ×${res.multiplier}: ${fmt(res.won_item.value)} 🎫`, 'success');
      else toast(`${diceStr} — совпадений: ${res.match_count}. Проигрыш.`, 'error');
      paintDice(root, rules);
    } catch (err) {
      toast('Ошибка: ' + err.message, 'error');
      rollBtn.disabled = false;
    }
  });
}

// =================================================================== БАТЛ

async function renderBattleScreen(root) {
  const cases = await api('/api/battle/cases');
  const rows = cases.map((c) => `
    <button class="item-row" style="width:100%;background:none;border:none;color:inherit;cursor:pointer" data-id="${c.id}">
      <span>${escapeHtml(c.name)}</span><span class="item-value">${c.price_tokens} 🎫</span>
    </button>`).join('') || '<div class="empty-state">Нет доступных кейсов для батла.</div>';

  root.innerHTML = `
    <div class="section-title">БАТЛ</div>
    <p class="muted">1×1 против бота-соперника: оба открывают один и тот же кейс, у кого дороже дроп — забирает оба предмета.</p>
    <div class="card" style="padding:0">${rows}</div>
  `;

  root.querySelectorAll('[data-id]').forEach((el) =>
    el.addEventListener('click', async () => {
      try {
        const res = await api('/api/battle/start', { method: 'POST', body: JSON.stringify({ case_id: Number(el.dataset.id) }) });
        renderBattleResult(res);
      } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
    })
  );
}

function renderBattleResult(res) {
  const title = res.winner === 'player' ? '🏆 Победа!' : res.winner === 'bot' ? '💀 Поражение' : '🤝 Ничья';
  openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <h2>${title}</h2>
    <div class="item-row" style="--rc:${res.player_item.rarity_color}">${brainrotArt(res.player_item)}<span style="flex:1;margin:0 8px">Ты: ${escapeHtml(res.player_item.name)}</span><span class="item-value" style="color:${res.player_item.rarity_color}">${fmt(res.player_item.value)} 🎫</span></div>
    <div class="item-row" style="--rc:${res.bot_item.rarity_color}">${brainrotArt(res.bot_item)}<span style="flex:1;margin:0 8px">Бот: ${escapeHtml(res.bot_item.name)}</span><span class="item-value" style="color:${res.bot_item.rarity_color}">${fmt(res.bot_item.value)} 🎫</span></div>
    <style>#active-modal .item-row .p-tile{width:36px;height:36px;font-size:14px;flex-shrink:0}</style>
    <button class="btn btn-primary" style="margin-top:14px" onclick="closeModal()">Готово</button>
  `);
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
