/* Brainrot Battle Mini App — vanilla JS SPA, без сборки/зависимостей. */

const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  if (tg.setHeaderColor) try { tg.setHeaderColor('#0a0e17'); } catch (e) {}
  if (tg.setBackgroundColor) try { tg.setBackgroundColor('#0a0e17'); } catch (e) {}
}

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
const CASE_EMOJI = ['📦', '🎁', '🧨', '🔮', '🗝️', '🏺', '💎', '🎲'];

function caseEmoji(name) {
  let hash = 0;
  for (const ch of name || '') hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return CASE_EMOJI[hash % CASE_EMOJI.length];
}
function caseArtColor(name) {
  const colors = ['#3a3f7a', '#5a2f6b', '#2f5a4e', '#6b3a2f', '#2f4a6b'];
  let hash = 0;
  for (const ch of name || '') hash = (hash * 17 + ch.charCodeAt(0)) >>> 0;
  return colors[hash % colors.length];
}

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

// ------------------------------------------------------------------- toast

function toast(message, kind = 'info') {
  const root = document.getElementById('toast-root');
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.remove(), 2600);
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

async function refreshMe() {
  ME = await api('/api/me');
  document.getElementById('drawer-username').textContent = ME.username ? '@' + ME.username : (ME.first_name || 'игрок');
  document.getElementById('drawer-balance').textContent = ME.balance;
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
};

function navigate(screen, params = {}) {
  location.hash = '#' + screen;
  renderScreen(screen, params);
}

async function renderScreen(screen, params = {}) {
  renderDrawer(screen);
  const root = document.getElementById('screen');
  root.innerHTML = '<div class="empty-state">Загрузка…</div>';
  try {
    const fn = SCREENS[screen] || renderCasesScreen;
    await fn(root, params);
  } catch (err) {
    root.innerHTML = `<div class="empty-state">Ошибка: ${escapeHtml(err.message)}</div>`;
  }
}

window.addEventListener('hashchange', () => {
  const screen = (location.hash || '#home').slice(1);
  renderScreen(screen);
});

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// =================================================================== ГЛАВНАЯ / КЕЙСЫ

async function renderCasesScreen(root, params = {}) {
  const category = params.category || 'cases';
  const [data] = await Promise.all([api(`/api/cases?category=${category}`), refreshMe()]);

  const tabs = Object.entries(CATEGORY_LABELS).map(
    ([key, label]) => `<button class="category-tab ${key === category ? 'active' : ''}" data-cat="${key}">${label}</button>`
  ).join('');

  const cards = data.cases.map((c) => {
    const price = c.price_tokens !== null ? `${c.price_tokens} 🎫` : 'цена уточняется';
    const count = c.item_count_label !== null ? `${c.item_count_label} предм.` : '? предм.';
    return `
      <button class="case-card ${c.is_openable ? '' : 'locked'}" data-case-id="${c.id}">
        ${c.is_openable ? '' : '<span class="lock-badge">🔒</span>'}
        <div class="case-art" style="--art-a:${caseArtColor(c.name)}">${caseEmoji(c.name)}</div>
        <div class="case-name">${escapeHtml(c.name)}</div>
        <div class="case-meta"><span>${count}</span><span class="case-price">${price}</span></div>
      </button>`;
  }).join('') || '<div class="empty-state">В этой категории пока нет кейсов.</div>';

  root.innerHTML = `
    <div class="section-title">${CATEGORY_TITLES[category]}</div>
    <div class="balance-line">Демо-баланс: <b>${ME.game_tokens} 🎫</b></div>
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
  root.querySelector('#btn-inventory').addEventListener('click', openInventoryModal);
  root.querySelector('#btn-topup').addEventListener('click', async () => {
    const res = await api('/api/demo-topup', { method: 'POST' });
    toast(`+${res.amount} 🎫`, 'success');
    ME.game_tokens = res.game_tokens;
    navigate('home', { category });
  });
}

async function openInventoryModal() {
  const items = await api('/api/inventory?limit=30');
  const rows = items.map((i) => `
    <div class="item-row"><span>${escapeHtml(i.item_name)} <span class="muted">(${escapeHtml(i.case_name)})</span></span><span class="item-value">${i.value} B</span></div>
  `).join('') || '<div class="empty-state">Инвентарь пуст.</div>';
  openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <h3>🎒 Инвентарь</h3>
    <div class="card" style="padding:0">${rows}</div>
  `);
}

async function openCaseDetail(caseId) {
  const c = await api(`/api/cases/${caseId}`);
  renderCaseDetailModal(c, 1);
}

function renderCaseDetailModal(c, qty) {
  const price = c.price_tokens !== null ? `${c.price_tokens} 🎫 за 1 шт.` : 'цена уточняется';
  const items = c.items.map((i) => `<div class="item-row"><span>${escapeHtml(i.name)}</span><span class="item-value">${i.value} B</span></div>`).join('')
    || '<div class="empty-state">Дроп-пул этого кейса пока не подтверждён.</div>';
  const totalCost = c.price_tokens !== null ? c.price_tokens * qty : null;

  const overlay = openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div class="case-art" style="--art-a:${caseArtColor(c.name)};height:120px;font-size:52px;margin-bottom:10px">${caseEmoji(c.name)}</div>
    <h2 style="margin:0 0 4px">${escapeHtml(c.name)}</h2>
    <div class="muted">${price} · ${c.item_count_label ?? '?'} предм.</div>
    ${c.note ? `<div class="muted" style="margin-top:6px">${escapeHtml(c.note)}</div>` : ''}
    <div class="pill-row" style="margin-top:14px">
      ${[1, 3, 5].map((q) => `<button class="pill qty-pill ${q === qty ? 'active' : ''}" data-qty="${q}">${q}</button>`).join('')}
    </div>
    ${c.is_openable
      ? `<button class="btn btn-primary" id="btn-open-case">ОТКРЫТЬ КЕЙС ×${qty}${totalCost !== null ? ` — ${totalCost} 🎫` : ''}</button>`
      : `<div class="empty-state">Кейс пока нельзя открыть.</div>`}
    <h4 style="margin:18px 0 8px">Что может выпасть</h4>
    <div class="card" style="padding:0;max-height:220px;overflow-y:auto">${items}</div>
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
      renderCaseOpenResult(c, res.won);
    } catch (err) {
      toast('Ошибка: ' + err.message, 'error');
      openBtn.disabled = false;
    }
  });
}

function renderCaseOpenResult(c, won) {
  const rows = won.map((i) => `<div class="item-row"><span>🎉 ${escapeHtml(i.name)}</span><span class="item-value">${i.value} B</span></div>`).join('');
  openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <h2 style="margin:0 0 10px">Результат: ${escapeHtml(c.name)}</h2>
    <div class="card" style="padding:0">${rows}</div>
    <button class="btn btn-primary" style="margin-top:14px" onclick="closeModal(); navigate('home')">Готово</button>
  `);
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

// =================================================================== ПРОФИЛЬ

async function renderProfileScreen(root) {
  const [me, inventory] = await Promise.all([refreshMe(), api('/api/inventory?limit=5')]);
  const bestDrop = inventory.slice().sort((a, b) => b.value - a.value)[0];

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
      <div class="stat-box"><div class="stat-label">Рефералов</div><div class="stat-value">${me.referral_count}</div></div>
      <div class="stat-box"><div class="stat-label">Заработано с рефералов</div><div class="stat-value">${me.referral_earned_total} 🪙</div></div>
    </div>
    ${bestDrop ? `
      <h4 style="margin:18px 0 8px">Лучший недавний дроп</h4>
      <div class="card" style="padding:0">
        <div class="item-row"><span>${escapeHtml(bestDrop.item_name)} <span class="muted">(${escapeHtml(bestDrop.case_name)})</span></span><span class="item-value">${bestDrop.value} B</span></div>
      </div>` : ''}
    <button class="btn btn-ghost" style="margin-top:16px" onclick="openInventoryModal()">🎒 Весь инвентарь</button>
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
      <div class="dial" style="background:conic-gradient(var(--accent-red) ${chance ?? 0}%, #241826 0)">
        <div class="dial" style="width:150px;height:150px;background:var(--bg);display:flex;flex-direction:column;align-items:center;justify-content:center">
          <div class="dial-chance">${chance !== null ? chance + '%' : '—'}</div>
          <div class="dial-label">ШАНС</div>
        </div>
      </div>
    </div>
    <div class="slot-row">
      <button class="slot ${contribution ? 'filled' : ''}" id="slot-contribution">
        ${contribution ? `${escapeHtml(contribution.item_name)}<br><span class="item-value">${contribution.value} B</span>` : 'ТВОЙ ВКЛАД<br>выбрать из инвентаря'}
      </button>
      <div class="slot-arrow">→</div>
      <button class="slot ${target ? 'filled' : ''}" id="slot-target">
        ${target ? `${escapeHtml(target.name)}<br><span class="item-value">${target.value} B</span>` : 'ЖЕЛАЕМЫЙ ПРЕДМЕТ<br>выбрать цель'}
      </button>
    </div>
    <button class="btn btn-primary" id="btn-spin" ${contribution && target ? '' : 'disabled'}>ПРОКАЧАТЬ</button>
    <button class="btn btn-ghost" style="margin-top:8px" id="btn-reset">Сбросить</button>
  `;

  root.querySelector('#slot-contribution').addEventListener('click', async () => {
    const items = await api('/api/inventory?limit=50');
    openItemPicker(items, (item) => {
      upgraderState.contribution = item;
      upgraderState.target = null;
      renderUpgraderScreen(root);
    });
  });

  root.querySelector('#slot-target').addEventListener('click', async () => {
    if (!contribution) { toast('Сначала выбери вклад', 'error'); return; }
    const targets = await api(`/api/upgrader/targets?min_value=${contribution.value}&exclude_name=${encodeURIComponent(contribution.item_name)}`);
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

// зеркалит bot/services/upgrader_service.chance_percent на фронте для мгновенного отображения
function computeChance(contributionValue, targetValue) {
  if (targetValue <= 0) return 95;
  const raw = Math.round((contributionValue / targetValue) * 100);
  return Math.max(1, Math.min(95, raw));
}

function openItemPicker(items, onPick) {
  const rows = items.map((i) => `
    <button class="item-row" style="width:100%;background:none;border:none;color:inherit;cursor:pointer" data-id="${i.id}">
      <span>${escapeHtml(i.item_name)}</span><span class="item-value">${i.value} B</span>
    </button>`).join('') || '<div class="empty-state">Инвентарь пуст — сначала открой кейс.</div>';
  const overlay = openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <h3>Выбери предмет</h3>
    <div class="card" style="padding:0">${rows}</div>
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
    <button class="item-row" style="width:100%;background:none;border:none;color:inherit;cursor:pointer" data-idx="${idx}">
      <span>${escapeHtml(t.name)}</span><span class="item-value">${t.value} B</span>
    </button>`).join('') || '<div class="empty-state">Нет подходящих целей дороже вклада.</div>';
  const overlay = openModal(`
    <button class="modal-close" onclick="closeModal()">✕</button>
    <h3>Желаемый предмет</h3>
    <div class="card" style="padding:0;max-height:320px;overflow-y:auto">${rows}</div>
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
    const items = await api('/api/inventory?limit=50');
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
    <button class="slot ${item ? 'filled' : ''}" id="slot-dice-item" style="width:100%;margin-bottom:10px">
      ${item ? `Ставка: ${escapeHtml(item.item_name)} — ${item.value} B` : 'Выбрать предмет из инвентаря'}
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
    const items = await api('/api/inventory?limit=50');
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
    <div class="item-row"><span>Ты</span><span class="item-value">${escapeHtml(res.player_item.name)} — ${res.player_item.value} B</span></div>
    <div class="item-row"><span>Бот</span><span class="item-value">${escapeHtml(res.bot_item.name)} — ${res.bot_item.value} B</span></div>
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
      const res = await api('/api/staking/start', { method: 'POST', body: JSON.stringify({ term_days: selectedTerm, amount }) });
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
window.openInventoryModal = openInventoryModal;

(async function boot() {
  try {
    await refreshMe();
    const initial = (location.hash || '#home').slice(1);
    await renderScreen(initial);
  } catch (err) {
    document.getElementById('screen').innerHTML = `<div class="empty-state">Не удалось загрузить: ${escapeHtml(err.message)}</div>`;
  }
})();
