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

const CATEGORY_LABELS = {
  cases: '📦 Кейсы',
  thematic: '🎭 Тематические',
  allin: '🎰 ALL-IN',
  partners: '🤝 Партнёры',
  free: '🎁 Бесплатные',
};
const CATEGORY_TITLES = {
  cases: 'КЕЙСЫ',
  thematic: 'ТЕМАТИЧЕСКИЕ КЕЙСЫ',
  allin: 'ALL-IN',
  partners: 'ПАРТНЁРЫ',
  free: 'БЕСПЛАТНЫЕ КЕЙСЫ',
};
const RARITY_ORDER = ['common', 'rare', 'epic', 'legendary', 'mythic', 'secret', 'og'];

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

// Итало-brainrot-мемы — абсурдные животные/предметы-гибриды: без реальных
// рендеров (см. докстринг ниже) эмодзи-пул хотя бы намекает на характер
// персонажа вместо голых инициалов. Хэш от имени -> всегда один и тот же
// эмодзи для одного и того же персонажа.
const GLYPH_POOL = ['🐊','🦈','🐸','🦶','🐍','🦵','🐘','🦉','🐢','🦫','🐫','🦒','🦩','🦚','🦜','🐙',
  '🍕','🍔','🧀','🍦','🥐','🍩','🌵','🎪','🎩','👑','⚓','🚀','🛞','🔫','💣','🎺','🥁','🛹','🧦',
  '👟','🦷','👁️','🫀','🧠','🎭','🐲','🦖','🦣','🐆'];

function glyphFor(name) {
  let hash = 0;
  for (const ch of name || '?') hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return GLYPH_POOL[hash % GLYPH_POOL.length];
}

function monogramFor(name) {
  const words = (name || '?').split(/\s+/).filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return (name || '?').slice(0, 2).toUpperCase();
}

/** Prestige-tile: заменяет реальное фото персонажа, которого нет (сеть в
 * этой песочнице режет любые image-CDN, см. bot/data/brainrot_roster.py).
 * Многослойная процедурная карточка (не голые буквы): диагональные грани +
 * радиальный блик + крупный тематический эмодзи + мелкая монограмма-бейдж.
 * <img> всё равно указывает на /static/assets/brainrots/<slug>.png — если
 * туда положить настоящий файл, он подхватится сам, тайл спрячется onload. */
function prestigeTile(brainrot, sizeClass = '') {
  const rarity = brainrot.rarity || 'common';
  const rc = brainrot.rarity_color || '#8a93a8';
  const rca = brainrot.rarity_color_accent || '#5c6478';
  const mono = monogramFor(brainrot.name);
  const imgUrl = brainrot.image_url || `/static/assets/brainrots/${brainrot.slug || ''}.png`;
  // Ручные SVG-иллюстрации для персонажей из подтверждённых скриншотом
  // дроп-пулов «Драгон»/«Тако» (см. webapp/static/js/character-art.js) —
  // единственный источник реальной уникальной графики, доступный без сети
  // и без Figma (оба варианта скачивания настоящих рендеров недоступны в
  // этом окружении, см. README в webapp/static/assets/).
  const customArt = window.CHARACTER_ART && window.CHARACTER_ART[brainrot.name];
  const artOrGlyph = customArt
    ? `<div class="p-tile-art">${customArt}</div>`
    : `<span class="p-tile-glyph">${glyphFor(brainrot.name)}</span>`;
  return `
    <div class="p-tile r-${rarity} ${sizeClass} ${customArt ? 'has-art' : ''}" style="--rc:${rc};--rca:${rca}">
      <div class="p-tile-facets"></div>
      <span class="p-tile-mono">${escapeHtml(mono)}</span>
      ${artOrGlyph}
      <img src="${imgUrl}" alt="" loading="lazy" onerror="this.remove()" onload="this.parentElement.classList.add('has-photo')" />
    </div>`;
}

function rarityBadge(brainrot) {
  const rc = brainrot.rarity_color || '#8a93a8';
  return `<span class="rarity-badge" style="--rc:${rc}">${escapeHtml(brainrot.rarity_label || '?')}</span>`;
}

function caseCardStyle(c) {
  const rc = c.best_rarity_color || '#5b7cfa';
  return `--rc:${rc}`;
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

async function renderCasesScreen(root, params = {}) {
  const category = params.category || 'cases';
  const [data, me, recentWins] = await Promise.all([
    api(`/api/cases?category=${category}`),
    refreshMe(),
    api('/api/recent-wins?limit=12').catch(() => []),
  ]);

  const tabs = Object.entries(CATEGORY_LABELS).map(
    ([key, label]) => `<button class="category-tab ${key === category ? 'active' : ''}" data-cat="${key}">${label}</button>`
  ).join('');

  const cards = data.cases.map((c, idx) => {
    const price = c.price_tokens !== null ? `${c.price_tokens} 🎫` : 'по условию';
    const count = c.item_count_label !== null ? `${c.item_count_label} шт.` : '? шт.';
    // Иконка карточки — арт САМОГО ЦЕННОГО предмета из дроп-пула (top_item_name),
    // а не хэш от имени кейса: имя кейса («Драгон») не персонаж и не совпадает
    // ни с одним ключом в CHARACTER_ART, из-за чего раньше подставлялась
    // случайная не по теме эмодзи (напр. 🐢 для кейса «Драгон»).
    const caseAsBrainrot = {
      name: c.top_item_name || c.name,
      rarity: c.best_rarity || 'common',
      rarity_color: c.best_rarity_color,
      rarity_color_accent: c.best_rarity_color_accent,
      slug: c.top_item_slug || 'case-' + c.id,
    };
    return `
      <button class="case-card fade-in-up ${c.is_openable ? '' : 'locked'}" style="${caseCardStyle(c)};animation-delay:${Math.min(idx * 35, 350)}ms" data-case-id="${c.id}">
        ${c.is_openable ? '' : '<span class="lock-badge">🔒</span>'}
        <div class="case-art">${prestigeTile(caseAsBrainrot)}</div>
        <div class="case-name">${escapeHtml(c.name)}</div>
        ${c.best_rarity_label ? `<span class="rarity-badge" style="--rc:${c.best_rarity_color}">до ${escapeHtml(c.best_rarity_label)}</span>` : ''}
        <div class="case-meta"><span>${count}</span><span class="case-price">${price}</span></div>
      </button>`;
  }).join('') || '<div class="empty-state">В этой категории пока нет кейсов.</div>';

  const ticker = recentWins.length ? `
    <div class="ticker-wrap">
      <div class="ticker-label"><span class="ticker-dot"></span> Последние выигрыши</div>
      <div class="ticker-row">
        ${recentWins.map((w, idx) => `
          <div class="ticker-card fade-in-up" style="--rc:${w.rarity_color};animation-delay:${idx * 40}ms">
            <div class="ticker-tile">${prestigeTile(w)}</div>
            <div class="ticker-player">${escapeHtml(w.player)}</div>
            <div class="ticker-value">${w.value} B</div>
          </div>`).join('')}
      </div>
    </div>` : '';

  root.innerHTML = `
    <div class="section-title">${CATEGORY_TITLES[category]}</div>
    <div class="balance-hero">
      <div class="balance-tile gold"><div class="balance-tile-label">Демо 🎫</div><div class="balance-tile-value">${me.game_tokens}</div></div>
      <div class="balance-tile"><div class="balance-tile-label">Баланс B</div><div class="balance-tile-value">${me.balance}</div></div>
    </div>
    ${ticker}
    <div class="category-tabs">${tabs}</div>
    <div class="case-grid">${cards}</div>
    <div class="btn-row" style="margin-top:14px">
      <button class="btn btn-ghost" id="btn-inventory">🎒 Инвентарь</button>
      <button class="btn btn-gold" id="btn-topup">🎁 Пополнить демо</button>
    </div>`;

  root.querySelectorAll('.category-tab').forEach((el) =>
    el.addEventListener('click', () => navigate('home', { category: el.dataset.cat }))
  );
  root.querySelectorAll('.case-card').forEach((el) =>
    el.addEventListener('click', () => openCaseDetail(Number(el.dataset.caseId)))
  );
  root.querySelector('#btn-inventory').addEventListener('click', () => navigate('inventory'));
  root.querySelector('#btn-topup').addEventListener('click', async () => {
    const res = await api('/api/demo-topup', { method: 'POST' });
    toast(`+${res.amount} 🎫`, 'success');
    ME.game_tokens = res.game_tokens;
    navigate('home', { category });
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

// =================================================================== СТРАНИЦА КЕЙСА + РУЛЕТКА

async function openCaseDetail(caseId) {
  const c = await api(`/api/cases/${caseId}`);
  renderCaseDetailModal(c, 1);
}

function renderCaseDetailModal(c, qty) {
  const price = c.price_tokens !== null ? `${c.price_tokens} 🎫 за 1 шт.` : 'цена по условию';
  const items = (c.items || []).slice().sort((a, b) => b.value - a.value);
  const dropTable = items.map((i, idx) => `
    <div class="drop-tile fade-in-up" style="--rc:${i.rarity_color};animation-delay:${Math.min(idx * 30, 300)}ms">
      ${prestigeTile(i)}
      <div class="drop-name">${escapeHtml(i.name)}</div>
      <div class="drop-value">${i.value} B</div>
      <div class="drop-chance">${i.chance_percent}%</div>
    </div>`).join('') || '<div class="empty-state">Дроп-пул этого кейса пока не подтверждён.</div>';
  const totalCost = c.price_tokens !== null ? c.price_tokens * qty : null;

  // Иконка-герой — арт самого ценного предмета дроп-пула (items уже
  // отсортированы по value desc выше), а не хэш от имени кейса — см.
  // renderCasesScreen для того же исправления на карточках главного экрана.
  const heroBrainrot = items[0]
    ? items[0]
    : { name: c.top_item_name || c.name, rarity: c.best_rarity, rarity_color: c.best_rarity_color, rarity_color_accent: c.best_rarity_color_accent, slug: '' };
  const overlay = openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div style="display:flex;justify-content:center">${prestigeTile(heroBrainrot, '')}</div>
    <style>#active-modal .p-tile:first-of-type{width:120px;height:120px;font-size:44px;margin-bottom:12px}</style>
    <h2 style="margin:6px 0 4px;text-align:center">${escapeHtml(c.name)}</h2>
    <div class="muted" style="text-align:center">${price} · ${c.item_count_label ?? '?'} предм. ${c.best_rarity_label ? `· до <span style="color:${c.best_rarity_color}">${escapeHtml(c.best_rarity_label)}</span>` : ''}</div>
    ${c.note ? `<div class="muted" style="margin-top:6px;text-align:center">${escapeHtml(c.note)}</div>` : ''}
    <div id="reel-slot"></div>
    <div class="pill-row" style="margin-top:14px">
      ${[1, 3, 5].map((q) => `<button class="pill qty-pill ${q === qty ? 'active' : ''}" data-qty="${q}">${q}</button>`).join('')}
    </div>
    ${c.is_openable
      ? `<button class="btn btn-primary" id="btn-open-case">ОТКРЫТЬ КЕЙС ×${qty}${totalCost !== null ? ` — ${totalCost} 🎫` : ''}</button>`
      : `<div class="empty-state">Кейс пока нельзя открыть.</div>`}
    <h4 style="margin:18px 0 8px">Что может выпасть</h4>
    <div class="drop-table">${dropTable}</div>
  `);

  overlay.querySelectorAll('.qty-pill').forEach((el) =>
    el.addEventListener('click', () => renderCaseDetailModal(c, Number(el.dataset.qty)))
  );
  const openBtn = overlay.querySelector('#btn-open-case');
  if (openBtn) openBtn.addEventListener('click', async () => {
    openBtn.disabled = true;
    try {
      const res = await api(`/api/cases/${c.id}/open`, { method: 'POST', body: JSON.stringify({ qty }) });
      ME.game_tokens = res.game_tokens;
      if (qty === 1 && res.reel) {
        openBtn.disabled = true;
        await playReel(overlay.querySelector('#reel-slot'), res.reel, res.reveal_index);
        renderCaseOpenResult(c, res.won);
      } else {
        renderCaseOpenResult(c, res.won);
      }
    } catch (err) {
      toast('Ошибка: ' + err.message, 'error');
      openBtn.disabled = false;
    }
  });
}

const REEL_ITEM_WIDTH = 104; // 96px карточка + 8px gap, см. .reel-item/.reel-track в app.css

/** Рулетка: сервер уже решил результат (res.won[0]), reel[] — только
 * декорация вокруг него на позиции reveal_index (см. build_reel на
 * бэкенде). Анимация не выбирает исход — она едет к уже готовой позиции. */
function playReel(slot, reel, revealIndex) {
  return new Promise((resolve) => {
    slot.innerHTML = `
      <div class="reel-outer">
        <div class="reel-fade left"></div>
        <div class="reel-fade right"></div>
        <div class="reel-marker"></div>
        <div class="reel-track" id="reel-track">
          ${reel.map((i) => `
            <div class="reel-item" style="--rc:${i.rarity_color}">
              ${prestigeTile(i)}
              <div class="reel-item-name">${escapeHtml(i.name)}</div>
              <div class="reel-item-value">${i.value} B</div>
            </div>`).join('')}
        </div>
      </div>`;
    const track = slot.querySelector('#reel-track');
    const outerWidth = slot.querySelector('.reel-outer').clientWidth;
    requestAnimationFrame(() => {
      const target = revealIndex * REEL_ITEM_WIDTH + REEL_ITEM_WIDTH / 2 - outerWidth / 2;
      track.style.transition = 'transform 4.2s cubic-bezier(0.09, 0.85, 0.12, 1)';
      track.style.transform = `translateX(${-target}px)`;
    });
    track.addEventListener('transitionend', () => {
      const landed = slot.querySelectorAll('.reel-item')[revealIndex];
      if (landed) landed.style.boxShadow = '0 0 24px -2px var(--rc)';
      setTimeout(resolve, 350);
    }, { once: true });
  });
}

function renderCaseOpenResult(c, won) {
  if (won.length === 1) {
    const w = won[0];
    openModal(`
      <button class="modal-close" onclick="closeModal()">✕</button>
      <div class="reveal-card" style="--rc:${w.rarity_color}">
        ${prestigeTile(w)}
        <style>#active-modal .reveal-card .p-tile{width:110px;height:110px;font-size:40px;margin:0 auto 14px}</style>
        ${rarityBadge(w)}
        <div class="reveal-name" style="margin-top:8px">${escapeHtml(w.name)}</div>
        <div class="reveal-value" style="--rc:${w.rarity_color}">${w.value} B</div>
      </div>
      <button class="btn btn-primary" style="margin-top:16px" onclick="closeModal(); navigate('home')">Готово</button>
      <button class="btn btn-ghost" style="margin-top:8px" onclick="closeModal(); openCaseDetail(${c.id})">Открыть ещё раз</button>
    `);
    return;
  }
  const rows = won.map((i) => `<div class="item-row" style="--rc:${i.rarity_color}">${rarityBadge(i)}<span style="flex:1;margin:0 8px">${escapeHtml(i.name)}</span><span class="item-value" style="color:${i.rarity_color}">${i.value} B</span></div>`).join('');
  openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <h2 style="margin:0 0 10px">Результат: ${escapeHtml(c.name)}</h2>
    <div class="card" style="padding:0">${rows}</div>
    <button class="btn btn-primary" style="margin-top:14px" onclick="closeModal(); navigate('home')">Готово</button>
  `);
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
      ${prestigeTile(i)}
      <div class="inv-name">${escapeHtml(i.name)}</div>
      <div class="inv-value">${i.value} B</div>
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
        ${prestigeTile(bestDrop)}
        <style>#app .reveal-card .p-tile{width:64px;height:64px;font-size:24px;margin:0 auto 8px}</style>
        ${rarityBadge(bestDrop)}
        <div class="reveal-name" style="font-size:15px;margin-top:6px">${escapeHtml(bestDrop.name)}</div>
        <div class="reveal-value" style="font-size:16px;--rc:${bestDrop.rarity_color}">${bestDrop.value} B</div>
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
        ${contribution ? `${prestigeTile(contribution)}${escapeHtml(contribution.name)}<br><span class="item-value">${contribution.value} B</span>` : 'ТВОЙ ВКЛАД<br>выбрать из инвентаря'}
      </button>
      <div class="slot-arrow">→</div>
      <button class="slot ${target ? 'filled' : ''}" id="slot-target">
        ${target ? `${prestigeTile(target)}${escapeHtml(target.name)}<br><span class="item-value">${target.value} B</span>` : 'ЖЕЛАЕМЫЙ ПРЕДМЕТ<br>выбрать цель'}
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
      if (res.success) toast(`✅ Успех! Получен: ${res.won_item.name} (${res.won_item.value} B)`, 'success');
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
      ${prestigeTile(i)}<span style="flex:1;margin:0 8px;text-align:left">${escapeHtml(i.name)}</span><span class="item-value" style="color:${i.rarity_color}">${i.value} B</span>
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
      ${prestigeTile(t)}<span style="flex:1;margin:0 8px;text-align:left">${escapeHtml(t.name)}</span><span class="item-value" style="color:${t.rarity_color}">${t.value} B</span>
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
      toast(`💰 Забрано ×${res.multiplier}: ${res.won_item.name} (${res.won_item.value} B)`, 'success');
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
  const stakeLabel = state.stake ? `${escapeHtml(state.stake.name)} (${state.stake.value} B)` : 'предмет не выбран';
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
      ${item ? `${prestigeTile(item)}Ставка: ${escapeHtml(item.name)} — ${item.value} B` : 'Выбрать предмет из инвентаря'}
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
      if (res.win) toast(`${diceStr} — совпадений: ${res.match_count}${res.bonus ? ' 🌈 БОНУС' : ''}. Выигрыш ×${res.multiplier}: ${res.won_item.value} B`, 'success');
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
    <div class="item-row" style="--rc:${res.player_item.rarity_color}">${prestigeTile(res.player_item)}<span style="flex:1;margin:0 8px">Ты: ${escapeHtml(res.player_item.name)}</span><span class="item-value" style="color:${res.player_item.rarity_color}">${res.player_item.value} B</span></div>
    <div class="item-row" style="--rc:${res.bot_item.rarity_color}">${prestigeTile(res.bot_item)}<span style="flex:1;margin:0 8px">Бот: ${escapeHtml(res.bot_item.name)}</span><span class="item-value" style="color:${res.bot_item.rarity_color}">${res.bot_item.value} B</span></div>
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
window.openCaseDetail = openCaseDetail;

(async function boot() {
  try {
    await refreshMe();
    const initial = (location.hash || '#home').slice(1);
    await renderScreen(initial);
  } catch (err) {
    document.getElementById('screen').innerHTML = `<div class="empty-state">Не удалось загрузить: ${escapeHtml(err.message)}</div>`;
  }
})();
