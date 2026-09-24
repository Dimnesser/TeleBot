/* Модели кейсов BrainCore.
 *
 * Каждый кейс — открытый кейс-чемодан (жёсткий корпус, крышка откинута),
 * в наполнителе по теме кейса (монеты, лапша, клубника, кристаллы…) сидят
 * его герои — официальные рендеры самых дорогих брейнротов кейса (реальные
 * ассеты, не рисунки). Вокруг — аура темы (огонь, молнии, дым…).
 * Всё рисуется здесь в SVG, картинок кейсов нет.
 *
 * Слои: [аура сзади + крышка + проём] → <img> героев → [наполнитель +
 * передняя стенка + аура спереди]. Наполнитель перекрывает ноги героев —
 * они «сидят» в кейсе.
 *
 * API:
 *   CaseArt.artifact(caseJson, extraClass) -> HTML
 *   CaseArt.particles(canvas, kind, colors) -> { burst(x, y, color, power), stop() }
 */
(function () {
  let uid = 0;

  // Детерминированный ГСЧ: одна и та же модель кейса выглядит одинаково везде.
  function rng(seedStr) {
    let h = 1779033703 ^ seedStr.length;
    for (let i = 0; i < seedStr.length; i++) { h = Math.imul(h ^ seedStr.charCodeAt(i), 3432918353); h = (h << 13) | (h >>> 19); }
    return function () {
      h = Math.imul(h ^ (h >>> 16), 2246822507); h = Math.imul(h ^ (h >>> 13), 3266489909);
      return ((h ^= h >>> 16) >>> 0) / 4294967296;
    };
  }
  const f1 = (n) => Math.round(n * 10) / 10;

  // ------------------------------------------------------------ наполнитель
  // Каждый элемент рисуется вокруг (x, y) с масштабом k.
  const PIECES = {
    coins: (x, y, k, r) => {
      const a = f1((r() - 0.5) * 40);
      return `<g transform="translate(${x} ${y}) rotate(${a}) scale(${k})"><ellipse rx="7" ry="3.4" fill="#b8801a"/><ellipse cy="-1.2" rx="7" ry="3.4" fill="#ffd24d"/><ellipse cy="-1.2" rx="4.2" ry="1.9" fill="none" stroke="#e0a82a" stroke-width=".9"/></g>`;
    },
    junk: (x, y, k, r) => {
      const c = ['#8a6a4a', '#6d6f75', '#a1845f', '#4f5a4a', '#b39a72'][(r() * 5) | 0];
      const t = r();
      const body = t < 0.35 ? `<rect x="-6" y="-4" width="12" height="8" rx="1.5" fill="${c}"/><rect x="-6" y="-4" width="12" height="2" fill="#fff" opacity=".18"/>`
        : t < 0.65 ? `<circle r="4.5" fill="${c}"/><circle r="1.8" fill="#2a2320"/>`
        : `<path d="M-7 3 L-2 -5 L7 -2 L4 5 Z" fill="${c}"/>`;
      return `<g transform="translate(${x} ${y}) rotate(${f1((r() - 0.5) * 70)}) scale(${k})">${body}</g>`;
    },
    sand: (x, y, k, r) => `<g transform="translate(${x} ${y}) scale(${k})"><ellipse rx="9" ry="4" fill="${r() < 0.5 ? '#e8c27a' : '#d9ad5e'}"/><circle cx="${f1(r() * 6 - 3)}" cy="-1" r=".9" fill="#a9803c"/></g>`,
    wood: (x, y, k, r) => `<g transform="translate(${x} ${y}) rotate(${f1((r() - 0.5) * 50)}) scale(${k})"><rect x="-10" y="-3.5" width="20" height="7" rx="3.5" fill="#8a5a2c"/><ellipse cx="10" rx="3" ry="3.5" fill="#d9a066"/><ellipse cx="10" rx="1.4" ry="1.7" fill="none" stroke="#8a5a2c" stroke-width=".8"/></g>`,
    food: (x, y, k, r) => {
      const t = r();
      if (t < 0.5) return `<g transform="translate(${x} ${y}) rotate(${f1((r() - 0.5) * 90)}) scale(${k})"><rect x="-1.8" y="-8" width="3.6" height="16" rx="1" fill="#ffc93c"/><rect x="-1.8" y="-8" width="1.2" height="16" fill="#fff3b0" opacity=".6"/></g>`;
      if (t < 0.8) return `<g transform="translate(${x} ${y}) scale(${k})"><path d="M-7 0 Q-7 -6 0 -6 Q7 -6 7 0 Z" fill="#e0913a"/><rect x="-7.5" y="0" width="15" height="2" fill="#5ed36a"/><rect x="-7" y="2" width="14" height="2.5" fill="#6b3a1e"/><path d="M-7 4.5 H7 Q7 7 0 7 Q-7 7 -7 4.5 Z" fill="#e0913a"/></g>`;
      return `<g transform="translate(${x} ${y}) scale(${k})"><circle r="4.5" fill="#fff4e0"/><circle r="3" fill="#ffd8a0"/></g>`;
    },
    noodles: (x, y, k, r) => {
      const c = r() < 0.7 ? '#f0a045' : '#d8352a';
      const w = f1(8 + r() * 8);
      return `<path transform="translate(${x} ${y}) rotate(${f1((r() - 0.5) * 60)}) scale(${k})" d="M${-w} 0 q${w / 4} -5 ${w / 2} 0 t${w / 2} 0 t${w / 2} 0 t${w / 2} 0" fill="none" stroke="${c}" stroke-width="2.6" stroke-linecap="round"/>`;
    },
    pumpkins: (x, y, k) => `<g transform="translate(${x} ${y}) scale(${k})"><ellipse rx="7.5" ry="5.5" fill="#ff8a1f"/><ellipse rx="3" ry="5.5" fill="#ffa24a"/><rect x="-1" y="-8" width="2" height="3.5" rx=".8" fill="#3f8a2b"/><path d="M-4 -1 L-2 -1 L-3 -3 Z M2 -1 L4 -1 L3 -3 Z M-3.5 2 Q0 4 3.5 2" fill="#2a0c00" stroke="#2a0c00" stroke-width=".6"/></g>`,
    bills: (x, y, k, r) => `<g transform="translate(${x} ${y}) rotate(${f1((r() - 0.5) * 60)}) scale(${k})"><rect x="-9" y="-4.5" width="18" height="9" rx="1" fill="#5fae5a" stroke="#2f6b2c" stroke-width=".8"/><circle r="2.6" fill="none" stroke="#2f6b2c" stroke-width=".8"/><rect x="-7.5" y="-3" width="15" height="6" fill="none" stroke="#a6e3a0" stroke-width=".5"/></g>`,
    water: (x, y, k, r) => (r() < 0.6
      ? `<ellipse cx="${x}" cy="${y}" rx="${f1(10 * k)}" ry="${f1(4 * k)}" fill="${r() < 0.5 ? '#2fb6d8' : '#1f8fb3'}"/>`
      : `<g transform="translate(${x} ${y}) scale(${k})"><circle r="3.4" fill="#f4fbff"/><circle cx="-1" cy="-1" r="1" fill="#fff"/></g>`),
    bolts: (x, y, k, r) => (r() < 0.55
      ? `<g transform="translate(${x} ${y}) rotate(${f1(r() * 60)}) scale(${k})"><path d="M-5 0 L-2.5 -4.3 L2.5 -4.3 L5 0 L2.5 4.3 L-2.5 4.3 Z" fill="#9aa4b2" stroke="#4c5563" stroke-width=".8"/><circle r="1.8" fill="#2b313a"/></g>`
      : `<g transform="translate(${x} ${y}) rotate(${f1((r() - 0.5) * 40)}) scale(${k})"><rect x="-7" y="-4" width="14" height="8" rx="1" fill="#1d6b4a"/><path d="M-5 -1 H-1 V2 H4 M1 -2 H5" stroke="#3de0ff" stroke-width=".8" fill="none"/></g>`),
    gifts: (x, y, k, r) => {
      const c = ['#ff4f8b', '#4fe3ff', '#ffd84d', '#9b6bff', '#5ed36a'][(r() * 5) | 0];
      return `<g transform="translate(${x} ${y}) rotate(${f1((r() - 0.5) * 30)}) scale(${k})"><rect x="-6" y="-6" width="12" height="11" rx="1" fill="${c}"/><rect x="-1.2" y="-6" width="2.4" height="11" fill="#fff"/><rect x="-6" y="-1.5" width="12" height="2.4" fill="#fff"/></g>`;
    },
    candy: (x, y, k, r) => {
      const c = ['#ff6b6b', '#ffd84d', '#4fe3ff', '#ff9ef0', '#7cf06a'][(r() * 5) | 0];
      return r() < 0.5
        ? `<g transform="translate(${x} ${y}) scale(${k})"><circle r="5" fill="#fff"/><path d="M0 -5 A5 5 0 0 1 5 0 L0 0 Z M0 5 A5 5 0 0 1 -5 0 L0 0 Z" fill="${c}"/></g>`
        : `<g transform="translate(${x} ${y}) rotate(${f1((r() - 0.5) * 60)}) scale(${k})"><ellipse rx="5" ry="3.4" fill="${c}"/><path d="M-5 0 L-9 -3 L-9 3 Z M5 0 L9 -3 L9 3 Z" fill="${c}" opacity=".8"/></g>`;
    },
    crystals: (x, y, k, r) => {
      const c = ['#c7b0ff', '#9d7bff', '#e6dcff'][(r() * 3) | 0];
      return `<g transform="translate(${x} ${y}) rotate(${f1((r() - 0.5) * 50)}) scale(${k})"><path d="M0 -10 L4 -3 L3 5 L-3 5 L-4 -3 Z" fill="${c}" stroke="#fff" stroke-width=".6"/><path d="M0 -10 L0 5" stroke="#fff" stroke-width=".5" opacity=".6"/></g>`;
    },
    embers: (x, y, k, r) => `<g transform="translate(${x} ${y}) rotate(${f1(r() * 90)}) scale(${k})"><path d="M-6 2 L-3 -4 L4 -5 L7 1 L2 5 Z" fill="#2a1512"/><path d="M-3 0 L1 -2 L4 1" stroke="#ff6a1f" stroke-width="1.2" fill="none" class="art-flicker"/></g>`,
    smoke: (x, y, k, r) => `<circle cx="${x}" cy="${y}" r="${f1(7 * k)}" fill="${r() < 0.5 ? '#6b7079' : '#4a4e56'}" opacity=".9"/>`,
    snow: (x, y, k, r) => (r() < 0.65
      ? `<ellipse cx="${x}" cy="${y}" rx="${f1(9 * k)}" ry="${f1(4.5 * k)}" fill="#f4fbff"/>`
      : `<g transform="translate(${x} ${y}) rotate(${f1((r() - 0.5) * 40)}) scale(${k})"><rect x="-4.5" y="-4.5" width="9" height="9" rx="1.5" fill="#bfe8ff" opacity=".9" stroke="#fff" stroke-width=".6"/></g>`),
    strawberries: (x, y, k, r) => `<g transform="translate(${x} ${y}) rotate(${f1((r() - 0.5) * 50)}) scale(${k})"><path d="M0 7 C-7 3 -7 -4 0 -4 C7 -4 7 3 0 7 Z" fill="#e8283c"/><path d="M-4 -4 L0 -7 L4 -4 L2 -3 L0 -5 L-2 -3 Z" fill="#3fae4a"/><g fill="#ffe08a"><circle cx="-2" cy="0" r=".6"/><circle cx="2" cy="1" r=".6"/><circle cx="0" cy="3.5" r=".6"/></g></g>`,
  };

  function filling(kind, r) {
    const piece = PIECES[kind] || PIECES.coins;
    let out = '';
    // Горка: сзади мельче и выше, спереди крупнее; середина приподнята.
    for (let row = 0; row < 4; row++) {
      const y0 = 108 + row * 5;
      const n = 11 + row * 2;
      for (let i = 0; i < n; i++) {
        const x = 40 + (160 * (i + r() * 0.8)) / n;
        const hump = Math.cos(((x - 120) / 90) * Math.PI / 2) * 7;
        out += piece(f1(x), f1(y0 - hump + r() * 3), f1(0.8 + row * 0.12 + r() * 0.15), r);
      }
    }
    return out;
  }

  // ------------------------------------------------------------ аура
  function flame(x, y, ang, len, id) {
    return `<path transform="translate(${f1(x)} ${f1(y)}) rotate(${f1(ang)})" d="M-6 0 C-7 -${len * 0.45} -1 -${len * 0.6} 0 -${len} C2 -${len * 0.6} 8 -${len * 0.45} 6 0 Z" fill="url(#${id}fl)"/>`;
  }
  function bolt(x, y, ang, len) {
    const s = len / 4;
    return `<path transform="translate(${f1(x)} ${f1(y)}) rotate(${f1(ang)})" d="M0 0 L${f1(s * 0.5)} -${f1(s)} L-${f1(s * 0.3)} -${f1(s * 1.6)} L${f1(s * 0.6)} -${f1(s * 2.6)} L-${f1(s * 0.1)} -${f1(s * 3)} L${f1(s * 0.4)} -${f1(len)}" fill="none" stroke="#fff6a8" stroke-width="2.2" stroke-linejoin="round"/>`;
  }
  function star(x, y, rr, c) {
    return `<path transform="translate(${f1(x)} ${f1(y)})" d="M0 -${rr} L${f1(rr * 0.25)} -${f1(rr * 0.25)} L${rr} 0 L${f1(rr * 0.25)} ${f1(rr * 0.25)} L0 ${rr} L-${f1(rr * 0.25)} ${f1(rr * 0.25)} L-${rr} 0 L-${f1(rr * 0.25)} -${f1(rr * 0.25)} Z" fill="${c}"/>`;
  }
  function around(r, n, fn) {
    // Точки по эллипсу вокруг кейса (центр 120,104).
    let out = '';
    for (let i = 0; i < n; i++) {
      const t = (i / n) * Math.PI * 2 + r() * 0.4;
      const x = 120 + Math.cos(t) * (94 + r() * 10);
      const y = 102 + Math.sin(t) * (76 + r() * 8);
      out += fn(x, y, (t * 180) / Math.PI + 90, r);
    }
    return out;
  }

  function aura(kind, accent, id, r) {
    switch (kind) {
      case 'fire': return {
        defs: `<linearGradient id="${id}fl" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#ff3d1f"/><stop offset=".55" stop-color="#ff9a1f"/><stop offset="1" stop-color="#ffe45a"/></linearGradient>`,
        back: `<g class="art-flame">${around(r, 16, (x, y, a) => flame(x, y, a, 16 + r() * 16, id))}</g>`,
        front: `<g fill="none" stroke-linecap="round" class="art-flame"><path d="M18 170 C10 130 30 96 58 92" stroke="#ff7a1f" stroke-width="5"/><path d="M222 170 C230 130 210 96 182 92" stroke="#ff7a1f" stroke-width="5"/><path d="M24 176 C20 140 36 112 60 104" stroke="#ffd34a" stroke-width="2"/><path d="M216 176 C220 140 204 112 180 104" stroke="#ffd34a" stroke-width="2"/></g>`,
      };
      case 'lightning': return {
        defs: '',
        back: `<g class="art-flicker" filter="url(#${id}gl)">${around(r, 9, (x, y, a) => bolt(x, y, a + 180 + (r() - 0.5) * 30, 26 + r() * 20))}</g>`,
        front: `<g class="art-flicker" filter="url(#${id}gl)">${bolt(22, 186, 18, 70)}${bolt(218, 186, -18, 70)}</g>`,
      };
      case 'sparkle': return {
        defs: '',
        back: `<g class="art-twinkle">${around(r, 14, (x, y) => star(x, y, 3 + r() * 5, r() < 0.6 ? accent : '#ffffff'))}</g>`,
        front: `<g class="art-twinkle-2">${star(30, 150, 6, '#fff')}${star(210, 132, 5, accent)}${star(200, 190, 4, '#fff')}</g>`,
      };
      case 'dust': return {
        defs: '',
        back: around(r, 16, (x, y) => `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(1 + r() * 1.8)}" fill="${accent}" opacity=".6"/>`),
        front: '',
      };
      case 'stars': return {
        defs: '',
        back: `<path d="M196 18 A16 16 0 1 0 214 40 A12 12 0 1 1 196 18 Z" fill="#fff3b0"/><g class="art-twinkle">${around(r, 16, (x, y) => star(x, y, 1.5 + r() * 3, '#ffffff'))}</g>`,
        front: '',
      };
      case 'smoke': return {
        defs: `<filter id="${id}bl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>`,
        back: `<g filter="url(#${id}bl)" class="art-drift">${around(r, 12, (x, y) => `<circle cx="${f1(x)}" cy="${f1(y + 10)}" r="${f1(18 + r() * 16)}" fill="${r() < 0.5 ? '#5a5f69' : '#3a3e46'}" opacity=".85"/>`)}</g>`,
        front: `<g filter="url(#${id}bl)" class="art-drift"><circle cx="24" cy="188" r="16" fill="#5a5f69" opacity=".7"/><circle cx="216" cy="186" r="17" fill="#4a4e56" opacity=".7"/></g>`,
      };
      case 'bubbles': return {
        defs: '',
        back: around(r, 16, (x, y) => `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(2 + r() * 6)}" fill="none" stroke="${accent}" stroke-width="1.4" opacity=".75"/>`),
        front: `<g fill="none" stroke="${accent}" stroke-width="1.4"><circle cx="26" cy="150" r="6"/><circle cx="214" cy="140" r="4"/><circle cx="206" cy="176" r="7"/></g>`,
      };
      case 'confetti': return {
        defs: '',
        back: around(r, 22, (x, y) => `<rect x="${f1(x)}" y="${f1(y)}" width="5" height="2.6" rx=".6" fill="${['#ff4f8b', '#4fe3ff', '#ffd84d', '#9b6bff', '#5ed36a'][(r() * 5) | 0]}" transform="rotate(${f1(r() * 180)} ${f1(x)} ${f1(y)})"/>`),
        front: `<g><rect x="24" y="160" width="6" height="3" fill="#ffd84d" transform="rotate(30 24 160)"/><rect x="212" y="150" width="6" height="3" fill="#4fe3ff" transform="rotate(-20 212 150)"/></g>`,
      };
      case 'crystal': return {
        defs: '',
        back: around(r, 12, (x, y, a) => `<path transform="translate(${f1(x)} ${f1(y)}) rotate(${f1(a + 180)}) scale(${f1(1 + r())})" d="M0 -12 L5 -3 L3 6 L-3 6 L-5 -3 Z" fill="${r() < 0.5 ? '#c7b0ff' : '#9d7bff'}" stroke="#fff" stroke-width=".7" opacity=".9"/>`),
        front: `<path d="M22 188 L30 160 L38 188 Z M204 188 L214 154 L224 188 Z" fill="#c7b0ff" stroke="#fff" stroke-width=".8"/>`,
      };
      case 'snow': return {
        defs: '',
        back: around(r, 18, (x, y) => `<g transform="translate(${f1(x)} ${f1(y)}) scale(${f1(0.6 + r() * 0.7)})" stroke="#fff" stroke-width="1.4" stroke-linecap="round"><line x1="-5" y1="0" x2="5" y2="0"/><line x1="-2.5" y1="-4.3" x2="2.5" y2="4.3"/><line x1="-2.5" y1="4.3" x2="2.5" y2="-4.3"/></g>`),
        front: `<path d="M26 120 q2 8 0 14 q-3 -4 0 -14 Z M214 120 q2 10 0 16 q-3 -5 0 -16 Z" fill="#e8f8ff"/>`,
      };
      case 'leaves': return {
        defs: '',
        back: `<g fill="none" stroke="#3fae4a" stroke-width="3" stroke-linecap="round"><path d="M14 150 C4 100 30 40 80 22"/><path d="M226 150 C236 100 210 40 160 22"/></g>
          ${around(r, 12, (x, y) => (r() < 0.6
            ? `<path transform="translate(${f1(x)} ${f1(y)}) rotate(${f1(r() * 360)})" d="M0 0 C4 -6 10 -6 12 0 C10 6 4 6 0 0 Z" fill="#3fae4a"/>`
            : PIECES.strawberries(f1(x), f1(y), 1.1, r)))}`,
        front: `<g>${PIECES.strawberries(24, 176, 1.4, r)}${PIECES.strawberries(214, 170, 1.3, r)}</g>`,
      };
      default: return { defs: '', back: '', front: '' };
    }
  }

  // ------------------------------------------------------------ корпус
  function model(c) {
    const t = c.theme || { filling: 'coins', aura: 'none', shell: ['#4a5570', '#1a2030'], accent: '#8fb0ff' };
    const [light, dark] = t.shell;
    const accent = t.accent;
    const id = 'cm' + (uid++);
    const r = rng(c.code || c.name || 'case');
    const au = aura(t.aura, accent, id, r);
    const fill = filling(t.filling, r);

    const defs = `
      <defs>
        <linearGradient id="${id}b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${light}"/><stop offset="1" stop-color="${dark}"/></linearGradient>
        <linearGradient id="${id}l" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${dark}"/><stop offset="1" stop-color="${light}" stop-opacity=".85"/></linearGradient>
        <radialGradient id="${id}g" cx="50%" cy="60%" r="55%"><stop offset="0" stop-color="${accent}" stop-opacity=".75"/><stop offset="1" stop-color="${accent}" stop-opacity="0"/></radialGradient>
        <filter id="${id}gl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        ${au.defs}
      </defs>`;

    const back = `${defs}
      <ellipse cx="120" cy="192" rx="92" ry="7" fill="#000" opacity=".55"/>
      <ellipse cx="120" cy="96" rx="104" ry="84" fill="url(#${id}g)" opacity=".55"/>
      ${au.back}
      <!-- крышка, откинутая назад: видна её внутренняя сторона -->
      <path d="M44 106 L50 22 Q51 14 60 14 L180 14 Q189 14 190 22 L196 106 Z" fill="${dark}" stroke="#000" stroke-opacity=".5" stroke-width="2" stroke-linejoin="round"/>
      <path d="M54 102 L59 26 Q60 22 64 22 L176 22 Q180 22 181 26 L186 102 Z" fill="url(#${id}l)"/>
      <path d="M54 102 L59 26 Q60 22 64 22 L176 22 Q180 22 181 26 L186 102 Z" fill="${accent}" opacity=".12"/>
      <g stroke="#000" stroke-opacity=".22" stroke-width="1.2">${[40, 58, 76, 94].map((y) => `<line x1="${f1(58 - (y - 22) * 0.05)}" y1="${y}" x2="${f1(182 + (y - 22) * 0.05)}" y2="${y}"/>`).join('')}</g>
      <path d="M50 22 Q51 14 60 14 L180 14 Q189 14 190 22" fill="none" stroke="#fff" stroke-opacity=".25" stroke-width="1.5"/>
      <!-- проём корпуса -->
      <path d="M30 122 L40 104 L200 104 L210 122 Z" fill="#07080c"/>
      <ellipse cx="120" cy="110" rx="74" ry="7" fill="${accent}" opacity=".35"/>`;

    const front = `
      <g>${fill}</g>
      <!-- передняя стенка -->
      <path d="M26 122 L214 122 L214 178 Q214 190 202 190 L38 190 Q26 190 26 178 Z" fill="url(#${id}b)" stroke="#000" stroke-opacity=".55" stroke-width="2"/>
      <rect x="26" y="120" width="188" height="7" rx="3" fill="${light}" stroke="#000" stroke-opacity=".45" stroke-width="1.5"/>
      <rect x="28" y="121" width="184" height="2" rx="1" fill="#fff" opacity=".35"/>
      <g stroke="#000" stroke-opacity=".28" stroke-width="2">
        <line x1="34" y1="150" x2="206" y2="150"/>
        <line x1="84" y1="130" x2="84" y2="186"/><line x1="156" y1="130" x2="156" y2="186"/>
      </g>
      <g stroke="#fff" stroke-opacity=".12" stroke-width="1"><line x1="34" y1="152" x2="206" y2="152"/></g>
      <!-- замки -->
      ${[56, 184].map((x) => `<g transform="translate(${x} 128)"><rect x="-9" y="0" width="18" height="18" rx="3" fill="#2a2d33" stroke="#000" stroke-opacity=".6"/><rect x="-6" y="3" width="12" height="7" rx="1.5" fill="#c9ced6"/><rect x="-6" y="3" width="12" height="2" rx="1" fill="#fff" opacity=".6"/></g>`).join('')}
      <!-- уголки -->
      <g fill="#000" opacity=".35"><path d="M26 170 L26 178 Q26 190 38 190 L46 190 L46 182 Q34 182 34 170 Z"/><path d="M214 170 L214 178 Q214 190 202 190 L194 190 L194 182 Q206 182 206 170 Z"/></g>
      <!-- шильдик -->
      <g transform="translate(120 170)">
        <rect x="-32" y="-9" width="64" height="18" rx="4" fill="${dark}" stroke="#000" stroke-opacity=".5"/>
        <rect x="-30" y="-7" width="60" height="14" rx="3" fill="#000" opacity=".25"/>
        <text y="4" text-anchor="middle" font-family="Unbounded, Manrope, sans-serif" font-size="9" font-weight="800" font-style="italic" fill="${accent}" letter-spacing=".3">BrainCore</text>
      </g>
      ${au.front}`;
    return { back, front };
  }

  function heroesHtml(c) {
    const list = (c.heroes && c.heroes.length ? c.heroes : (c.top_item_image_url ? [{ name: c.top_item_name, image_url: c.top_item_image_url }] : []))
      .filter((h) => h.image_url);
    if (!list.length) return '<div class="case-hero case-hero-missing">нет ассета</div>';
    const [main, second] = list;
    const img = (h, cls) => `<img class="case-hero ${cls}" src="${h.image_url}" alt="${String(h.name || '').replace(/"/g, '&quot;')}" loading="lazy" draggable="false">`;
    return second ? img(second, 'hero-2') + img(main, 'hero-1 with-2') : img(main, 'hero-1');
  }

  function artifact(c, extraClass = '') {
    const { back, front } = model(c);
    return `
      <div class="artifact case-model aura-${(c.theme && c.theme.aura) || 'none'} ${extraClass}">
        <svg class="artifact-svg" viewBox="0 0 240 200" aria-hidden="true">${back}</svg>
        ${heroesHtml(c)}
        <svg class="artifact-svg artifact-front" viewBox="0 0 240 200" aria-hidden="true">${front}</svg>
      </div>`;
  }

  // ---------------------------------------------------------------- particles

  const REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function particles(canvas, kind, colors) {
    const ctx = canvas.getContext('2d');
    let w = 0, h = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);
    const ambient = [];
    const bursts = [];
    let raf = 0, running = true, last = performance.now();

    function resize() {
      const r = canvas.getBoundingClientRect();
      w = r.width; h = r.height;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    const ro = window.ResizeObserver ? new ResizeObserver(resize) : null;
    if (ro) ro.observe(canvas);

    const pick = (arr) => arr[(Math.random() * arr.length) | 0];
    const confettiColors = [colors[0], colors[1], '#ffffff', '#ffd84d', '#4fe3ff'];

    function spawn(initial) {
      const p = { x: Math.random() * w, y: initial ? Math.random() * h : h + 10, life: 0, seed: Math.random() * 10 };
      switch (kind) {
        case 'steam': Object.assign(p, { r: 10 + Math.random() * 22, vy: -12 - Math.random() * 14, vx: 0, a: 0.045, color: '#ffffff' }); break;
        case 'wisps': Object.assign(p, { r: 2 + Math.random() * 3, vy: -8 - Math.random() * 10, vx: 0, a: 0.8, color: pick(colors.slice(0, 2)), glow: 14 }); break;
        case 'bubbles': Object.assign(p, { r: 2 + Math.random() * 6, vy: -20 - Math.random() * 30, vx: 0, a: 0.55, color: colors[1], ring: true }); break;
        case 'dust': Object.assign(p, { y: initial ? Math.random() * h : -10, r: 1 + Math.random() * 2, vy: 6 + Math.random() * 10, vx: 0, a: 0.9, color: pick(colors.slice(0, 2)), twinkle: true, glow: 8 }); break;
        case 'embers': Object.assign(p, { r: 1 + Math.random() * 2.5, vy: -30 - Math.random() * 40, vx: 0, a: 1, color: pick(colors.slice(0, 2)), glow: 10, flicker: true }); break;
        case 'confetti': Object.assign(p, { y: initial ? Math.random() * h : -10, r: 3 + Math.random() * 3, vy: 22 + Math.random() * 26, vx: 0, a: 0.9, color: pick(confettiColors), rect: true, rot: Math.random() * 6 }); break;
        case 'prism': default: Object.assign(p, { r: 1.5 + Math.random() * 2.5, vy: -6 - Math.random() * 8, vx: 0, a: 1, hue: Math.random() * 360, star: true, glow: 12, twinkle: true }); break;
      }
      return p;
    }

    const count = REDUCED || kind === 'none' ? 0 : Math.round(Math.min(60, (w * h) / 9000));
    for (let i = 0; i < count; i++) ambient.push(spawn(true));

    function drawParticle(p, alpha) {
      ctx.globalAlpha = Math.max(0, Math.min(1, alpha));
      const color = p.hue !== undefined ? `hsl(${(p.hue + p.life * 60) % 360} 95% 70%)` : p.color;
      if (p.glow) { ctx.shadowBlur = p.glow; ctx.shadowColor = color; } else ctx.shadowBlur = 0;
      if (p.rect) {
        ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot + p.life * 4);
        ctx.fillStyle = color; ctx.fillRect(-p.r, -p.r / 2, p.r * 2, p.r); ctx.restore();
      } else if (p.star) {
        ctx.fillStyle = color; ctx.beginPath();
        for (let i = 0; i < 4; i++) {
          const t = (i / 4) * Math.PI * 2;
          ctx.lineTo(p.x + Math.cos(t) * p.r * 2.4, p.y + Math.sin(t) * p.r * 2.4);
          ctx.lineTo(p.x + Math.cos(t + Math.PI / 4) * p.r * 0.6, p.y + Math.sin(t + Math.PI / 4) * p.r * 0.6);
        }
        ctx.closePath(); ctx.fill();
      } else if (p.ring) {
        ctx.strokeStyle = color; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.stroke();
      } else {
        ctx.fillStyle = color; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
      }
    }

    function frame(now) {
      if (!running) return;
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      ctx.clearRect(0, 0, w, h);
      for (let i = 0; i < ambient.length; i++) {
        const p = ambient[i];
        p.life += dt;
        p.x += (p.vx + Math.sin(p.life * 1.3 + p.seed) * 10) * dt;
        p.y += p.vy * dt;
        if (kind === 'steam') p.r += dt * 6;
        let a = p.a;
        if (p.twinkle) a *= 0.45 + 0.55 * Math.abs(Math.sin(p.life * 3 + p.seed));
        if (p.flicker) a *= 0.6 + Math.random() * 0.4;
        drawParticle(p, a);
        if (p.y < -40 || p.y > h + 40) ambient[i] = spawn(false);
      }
      for (let i = bursts.length - 1; i >= 0; i--) {
        const p = bursts[i];
        p.life += dt;
        p.vx *= 0.97; p.vy = p.vy * 0.97 + 140 * dt;
        p.x += p.vx * dt; p.y += p.vy * dt;
        const t = p.life / p.ttl;
        if (t >= 1) { bursts.splice(i, 1); continue; }
        drawParticle(p, 1 - t);
      }
      ctx.globalAlpha = 1; ctx.shadowBlur = 0;
      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);

    return {
      burst(x, y, color, power = 1) {
        const n = Math.round((REDUCED ? 20 : 70) * power);
        for (let i = 0; i < n; i++) {
          const t = Math.random() * Math.PI * 2;
          const s = (160 + Math.random() * 380) * Math.sqrt(power);
          bursts.push({
            x, y, vx: Math.cos(t) * s, vy: Math.sin(t) * s - 120, life: 0, ttl: 0.9 + Math.random() * 0.9,
            r: 1.5 + Math.random() * 3, color: Math.random() < 0.3 ? '#ffffff' : color, glow: 12,
            rect: Math.random() < 0.35, rot: Math.random() * 6, seed: 0,
          });
        }
      },
      stop() {
        running = false; cancelAnimationFrame(raf);
        if (ro) ro.disconnect();
      },
    };
  }

  window.CaseArt = { artifact, particles, REDUCED };
})();
