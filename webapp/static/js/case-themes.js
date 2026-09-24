/* Визуальные темы кейсов BrainCore.
 *
 * Каждый кейс — модель открытого сундука со своей тематикой (деревянный
 * ящик Нонны, склеп, хим-контейнер, сейф, кованый сундук, затонувший,
 * подарок, королевский ларец), нарисованная здесь в SVG. Внутри —
 * официальный рендер самого дорогого брейнрота кейса (реальный ассет, не
 * рисунок). Сами брейнроты здесь НЕ рисуются.
 *
 * API:
 *   CaseArt.artifact(caseJson, extraClass) -> HTML
 *   CaseArt.particles(canvas, kind, colors) -> { burst(x, y, color, power), stop() }
 */
(function () {
  let uid = 0;

  /* ------------------------------------------------------------------
   * Модель кейса — открытый сундук в псевдо-3D (крышка откинута назад,
   * брейнрот «сидит» внутри и выглядывает из проёма). Геометрия общая,
   * тематику задаёт скин: материал корпуса, окантовка, узор, эмблема на
   * замке, свечение изнутри и декор вокруг.
   * viewBox 0..200. Проём — y≈96..112, передняя стенка — y 112..188.
   * ------------------------------------------------------------------ */

  const EMBLEMS = {
    pizza: (c) => `<path d="M-11 -9 L11 -9 L0 13 Z" fill="#ffcf5a" stroke="${c}" stroke-width="2" stroke-linejoin="round"/>
      <path d="M-11 -9 Q0 -14 11 -9" fill="none" stroke="#c9772f" stroke-width="4" stroke-linecap="round"/>
      <circle cx="-3" cy="-3" r="2.4" fill="#d8352a"/><circle cx="4" cy="-2" r="2.4" fill="#d8352a"/><circle cx="0" cy="5" r="2" fill="#d8352a"/>`,
    pumpkin: () => `<ellipse cx="0" cy="2" rx="13" ry="10" fill="#ff8a1f"/><ellipse cx="0" cy="2" rx="5" ry="10" fill="#ff9d3c"/>
      <rect x="-1.5" y="-12" width="3" height="5" rx="1" fill="#3f8a2b"/>
      <path d="M-7 -1 L-3 -1 L-5 -5 Z M3 -1 L7 -1 L5 -5 Z" fill="#2a0c00"/><path d="M-7 5 Q0 10 7 5 L4 6 L2 4 L0 6 L-2 4 L-4 6 Z" fill="#2a0c00"/>`,
    biohazard: (c) => `<circle r="13" fill="#11160a"/><g fill="${c}"><circle cx="0" cy="-6" r="5"/><circle cx="-5.5" cy="3.5" r="5"/><circle cx="5.5" cy="3.5" r="5"/></g>
      <circle r="3.5" fill="#11160a"/><circle r="1.6" fill="${c}"/>`,
    dial: (c) => `<circle r="13" fill="#1a1405" stroke="${c}" stroke-width="2"/>
      ${Array.from({ length: 12 }, (_, i) => `<line x1="0" y1="-11" x2="0" y2="-8" stroke="${c}" stroke-width="1.5" transform="rotate(${i * 30})"/>`).join('')}
      <circle r="5" fill="${c}"/><line x1="0" y1="0" x2="0" y2="-9" stroke="#1a1405" stroke-width="2" transform="rotate(35)"/>`,
    flame: () => `<path d="M0 -14 C8 -6 11 0 8 7 C6 12 -6 12 -8 7 C-10 1 -6 -3 -3 -6 C-3 -1 0 1 2 -1 C3 -5 1 -9 0 -14 Z" fill="#ff5a1f"/>
      <path d="M0 -3 C4 1 5 4 3 8 C1 10 -3 10 -4 7 C-5 4 -2 2 0 -3 Z" fill="#ffd34a"/>`,
    anchor: (c) => `<g fill="none" stroke="${c}" stroke-width="3" stroke-linecap="round"><circle cx="0" cy="-9" r="3"/><line x1="0" y1="-6" x2="0" y2="11"/>
      <line x1="-6" y1="-2" x2="6" y2="-2"/><path d="M-10 4 Q-8 11 0 11 Q8 11 10 4"/></g>`,
    star: () => `<path d="M0 -13 L3.8 -4 L13 -4 L5.6 1.8 L8.4 11 L0 5.4 L-8.4 11 L-5.6 1.8 L-13 -4 L-3.8 -4 Z" fill="#fff36b" stroke="#ff4f8b" stroke-width="1.5"/>`,
    crown: () => `<path d="M-12 7 L-12 -6 L-6 0 L0 -10 L6 0 L12 -6 L12 7 Z" fill="#ffd84d" stroke="#fff6c4" stroke-width="1.2"/>
      <circle cx="0" cy="2" r="2.6" fill="#ff4fd8"/><circle cx="-7" cy="3" r="1.8" fill="#7cf3ff"/><circle cx="7" cy="3" r="1.8" fill="#7cf3ff"/>`,
    diamond: (c) => `<path d="M-12 -4 L-6 -11 L6 -11 L12 -4 L0 12 Z" fill="${c}" stroke="#fff" stroke-width="1.2"/>
      <path d="M-12 -4 L12 -4 M-6 -11 L-3 -4 L0 12 L3 -4 L6 -11" fill="none" stroke="#fff" stroke-width=".9" opacity=".7"/>`,
    chart: (c) => `<g fill="none" stroke="${c}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M-11 9 L-4 1 L1 5 L10 -8"/><path d="M4 -8 L10 -8 L10 -2"/></g>`,
    snow: (c) => `<g stroke="${c}" stroke-width="2.4" stroke-linecap="round">${[0, 60, 120].map((r) => `<g transform="rotate(${r})"><line x1="0" y1="-12" x2="0" y2="12"/><path d="M-3 -9 L0 -6 L3 -9 M-3 9 L0 6 L3 9" fill="none"/></g>`).join('')}</g>`,
    coin: () => `<circle r="12" fill="#ffd24d" stroke="#b8861a" stroke-width="2"/><circle r="8" fill="none" stroke="#b8861a" stroke-width="1.2"/>
      <text y="4.5" text-anchor="middle" font-size="12" font-weight="900" fill="#8a5a00" font-family="Unbounded,sans-serif">B</text>`,
    question: (c) => `<text y="8" text-anchor="middle" font-size="24" font-weight="900" fill="${c}" font-family="Unbounded,sans-serif">?</text>`,
    moon: () => `<path d="M4 -12 A12 12 0 1 0 12 6 A9 9 0 1 1 4 -12 Z" fill="#fff3b0"/><circle cx="-6" cy="-6" r="1.2" fill="#fff"/><circle cx="8" cy="-10" r="1" fill="#fff"/>`,
    bolt: (c) => `<path d="M3 -13 L-8 2 L-1 2 L-4 13 L8 -3 L1 -3 Z" fill="${c}" stroke="#fff" stroke-width="1"/>`,
    recycle: (c) => `<g fill="none" stroke="${c}" stroke-width="3" stroke-linecap="round"><path d="M-8 6 L-11 0 L-5 -9"/><path d="M-1 -11 L6 -11 L10 -3"/><path d="M11 3 L7 10 L-3 10"/></g>
      <g fill="${c}"><path d="M-5 -9 L-9 -9 L-5 -4 Z"/><path d="M10 -3 L12 -7 L6 -6 Z"/><path d="M-3 10 L0 13 L0 7 Z"/></g>`,
    wrench: (c) => `<path d="M8 -12 A6 6 0 0 0 1 -4 L-10 7 A2.5 2.5 0 0 0 -6 11 L5 0 A6 6 0 0 0 12 -8 L8 -5 L5 -8 Z" fill="${c}" stroke="#fff" stroke-width=".8"/>`,
    bow: (c) => `<g fill="${c}" stroke="#fff" stroke-width="1"><path d="M0 0 Q-14 -12 -13 0 Q-14 12 0 0 Z"/><path d="M0 0 Q14 -12 13 0 Q14 12 0 0 Z"/><circle r="3.5"/></g>`,
    apple: () => `<path d="M0 -6 C-8 -12 -14 -4 -11 4 C-8 12 -3 12 0 9 C3 12 8 12 11 4 C14 -4 8 -12 0 -6 Z" fill="#ff5a4a"/><path d="M0 -6 Q2 -12 6 -13" fill="none" stroke="#6b3a14" stroke-width="2"/><path d="M1 -9 Q6 -13 9 -9 Q5 -7 1 -9 Z" fill="#5ed36a"/>`,
    key: (c) => `<circle cx="-5" cy="-4" r="6" fill="none" stroke="${c}" stroke-width="3"/><path d="M-1 0 L10 11 M5 6 L8 3 M8 9 L11 6" stroke="${c}" stroke-width="3" stroke-linecap="round"/>`,
  };

  // Скины: body (светлый/тёмный), trim (окантовка), lidIn (внутренняя сторона крышки),
  // glow (свечение изнутри), emblem, pattern(id) → узор передней стенки, deco → декор.
  const SKINS = {
    crate: {
      body: ['#b46a3a', '#6b3518'], trim: '#3a1d0c', lidIn: '#4a250f', glow: '#ffd36b', emblem: 'pizza', plate: '#fff4e0',
      pattern: () => `<g stroke="#5a2c12" stroke-width="2" opacity=".7"><line x1="30" y1="137" x2="170" y2="137"/><line x1="30" y1="162" x2="170" y2="162"/></g>
        <g stroke="#e0935a" stroke-width="1" opacity=".35"><path d="M40 124 q20 3 40 0 t40 0"/><path d="M60 150 q20 3 40 0 t40 0"/><path d="M36 176 q20 3 40 0 t40 0"/></g>`,
      frontDeco: (id) => `<defs><pattern id="${id}gh" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#fff"/><rect width="5" height="10" fill="#e8372a" opacity=".75"/><rect width="10" height="5" fill="#e8372a" opacity=".75"/></pattern></defs>
        <path d="M24 108 L176 108 L176 122 Q166 132 156 122 Q146 132 136 122 Q126 132 116 122 Q106 132 96 122 Q86 132 76 122 Q66 132 56 122 Q46 132 36 122 Q30 128 24 122 Z" fill="url(#${id}gh)" stroke="#b3241b" stroke-width="1.5"/>`,
    },
    crypt: {
      body: ['#4a2a6e', '#1c0d2e'], trim: '#0c0614', lidIn: '#140a22', glow: '#c37bff', emblem: 'pumpkin', plate: '#2a1740',
      pattern: () => `<g fill="none" stroke="#7a4cb0" stroke-width="1.5" opacity=".6"><path d="M50 184 L50 150 Q50 132 64 132 Q78 132 78 150 L78 184"/><path d="M122 184 L122 150 Q122 132 136 132 Q150 132 150 150 L150 184"/></g>`,
      backDeco: () => `<g fill="#1c0d2e"><path d="M22 58 q10 -8 20 0 q-4 -10 6 -14 q-10 2 -14 -6 q-2 10 -12 8 q8 4 0 12 z" opacity=".9"/><path d="M160 36 q9 -7 18 0 q-3 -9 5 -12 q-9 2 -12 -5 q-2 9 -11 7 q7 4 0 10 z" opacity=".9"/></g>`,
      frontDeco: () => `<g fill="#0c0614"><path d="M26 112 L30 96 L34 112 Z"/><path d="M166 112 L170 96 L174 112 Z"/></g>
        <g><rect x="176" y="150" width="6" height="30" rx="2" fill="#f4ecd8"/><path d="M179 150 q-4 -8 0 -14 q4 6 0 14" fill="#ffb13b" class="art-flicker"/></g>`,
    },
    hazmat: {
      body: ['#dfe6ea', '#7f8c95'], trim: '#2b3238', lidIn: '#3a454d', glow: '#7dff4a', emblem: 'biohazard', plate: '#11160a',
      pattern: (id) => `<defs><pattern id="${id}hz" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="14" height="14" fill="#ffd21f"/><rect width="7" height="14" fill="#15181a"/></pattern></defs>
        <rect x="30" y="170" width="140" height="12" fill="url(#${id}hz)"/>
        <rect x="44" y="122" width="40" height="22" rx="4" fill="#0d2a12" stroke="#2b3238" stroke-width="2"/><rect x="47" y="125" width="34" height="16" rx="3" fill="#7dff4a" opacity=".35" class="art-pulse"/>`,
      frontDeco: () => `<g fill="#9dff6b" opacity=".85"><path d="M150 112 q3 10 0 16 q-4 4 -4 -3 q0 -8 4 -13 z"/><path d="M66 112 q2 6 0 10 q-3 3 -3 -2 q0 -5 3 -8 z"/></g>`,
    },
    vault: {
      body: ['#2b2616', '#0f0c05'], trim: '#ffc94a', lidIn: '#1a1506', glow: '#ffe28a', emblem: 'dial', plate: '#1a1405',
      pattern: () => `<g stroke="#ffc94a" stroke-width="1" opacity=".22">${Array.from({ length: 7 }, (_, i) => `<line x1="${30 + i * 24}" y1="112" x2="${54 + i * 24 - 24}" y2="188"/>`).join('')}</g>
        <g stroke="#ffc94a" stroke-width="3" fill="none"><rect x="36" y="118" width="128" height="64" rx="6" opacity=".5"/></g>`,
      frontDeco: () => `<g>${[[40, 190], [58, 194], [150, 192], [166, 188], [132, 196]].map(([x, y], i) => `<ellipse cx="${x}" cy="${y}" rx="9" ry="4" fill="#ffc94a" stroke="#a87a12" stroke-width="1.2" transform="rotate(${i % 2 ? 12 : -10} ${x} ${y})"/>`).join('')}</g>
        <g fill="#ffc94a"><ellipse cx="72" cy="100" rx="8" ry="3.5"/><ellipse cx="128" cy="101" rx="8" ry="3.5"/></g>`,
    },
    forge: {
      body: ['#3b3f47', '#15171b'], trim: '#0a0b0d', lidIn: '#1c1e22', glow: '#ff7a1f', emblem: 'flame', plate: '#1c1e22',
      pattern: () => `<g fill="none" stroke="#ff6a1f" stroke-width="2.2" stroke-linecap="round" class="art-flicker"><path d="M52 118 l8 12 l-6 10 l10 14"/><path d="M142 124 l-6 10 l8 8 l-4 16"/><path d="M96 168 l8 6 l-2 10"/></g>
        <g fill="#6c727d">${[[38, 120], [162, 120], [38, 180], [162, 180]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3.5"/>`).join('')}</g>`,
      backDeco: () => `<g class="art-flame" fill="#ff3d1f" opacity=".75"><path d="M30 118 Q22 80 44 60 Q42 88 58 94 Q54 64 76 40 Q78 76 92 86 L92 118 Z"/><path d="M170 118 Q178 80 156 60 Q158 88 142 94 Q146 64 124 40 Q122 76 108 86 L108 118 Z"/></g>`,
    },
    sunken: {
      body: ['#2f7c7a', '#0f3534'], trim: '#1b2a24', lidIn: '#0f2a2a', glow: '#5dfff0', emblem: 'anchor', plate: '#0f3534',
      pattern: () => `<g stroke="#0c2b2a" stroke-width="2" opacity=".8"><line x1="30" y1="137" x2="170" y2="137"/><line x1="30" y1="162" x2="170" y2="162"/></g>
        <g fill="#d9e6d6" stroke="#8aa396" stroke-width="1">${[[46, 176, 5], [56, 181, 3.5], [150, 128, 4.5], [158, 134, 3], [140, 180, 4]].map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}"/>`).join('')}</g>`,
      frontDeco: () => `<g fill="none" stroke="#3fbf6a" stroke-width="4" stroke-linecap="round" class="art-sway"><path d="M24 192 q-8 -18 2 -32 q8 -12 0 -26"/><path d="M178 192 q8 -16 -2 -30 q-8 -12 2 -22"/></g>`,
    },
    gift: {
      body: ['#ff4f8b', '#a3124e'], trim: '#6a0a31', lidIn: '#7a0e3a', glow: '#fff36b', emblem: 'star', plate: '#4fe3ff',
      pattern: () => `<rect x="90" y="112" width="20" height="76" fill="#4fe3ff"/><rect x="30" y="140" width="140" height="16" fill="#4fe3ff"/>
        <g fill="#fff" opacity=".35">${[[48, 124], [140, 126], [62, 172], [150, 176], [128, 168]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3"/>`).join('')}</g>`,
      frontDeco: () => `<g fill="#4fe3ff" stroke="#1ea7c2" stroke-width="1.5"><path d="M46 118 Q24 96 22 112 Q22 126 46 118 Z"/><path d="M46 118 Q60 96 70 108 Q74 122 46 118 Z"/><circle cx="46" cy="118" r="5"/>
        <path d="M44 122 L36 138 M48 122 L54 138" stroke-width="4" stroke-linecap="round"/></g>`,
    },
    royal: {
      body: ['#6a1f8f', '#2a0838'], trim: '#ffd84d', lidIn: '#3a0c4e', glow: '#ff9ef0', emblem: 'crown', plate: '#2a0838',
      pattern: () => `<g stroke="#ffd84d" stroke-width="1" opacity=".28">${Array.from({ length: 6 }, (_, i) => `<line x1="${30 + i * 28}" y1="112" x2="${58 + i * 28}" y2="188"/><line x1="${58 + i * 28}" y1="112" x2="${30 + i * 28}" y2="188"/>`).join('')}</g>
        <g>${[[52, 128, '#7cf3ff'], [148, 128, '#ff4fd8'], [52, 174, '#ff4fd8'], [148, 174, '#7cf3ff']].map(([x, y, c]) => `<path d="M${x} ${y - 6} L${x + 5} ${y} L${x} ${y + 6} L${x - 5} ${y} Z" fill="${c}" stroke="#fff" stroke-width=".8"/>`).join('')}</g>`,
      lidDeco: () => `<path d="M80 46 L84 30 L92 40 L100 24 L108 40 L116 30 L120 46 Z" fill="#ffd84d" stroke="#fff6c4" stroke-width="1.2"/>`,
    },
    // --- рыночные кейсы
    hype: {
      body: ['#ff5b3a', '#8a1a06'], trim: '#2a0700', lidIn: '#4a0e02', glow: '#ffc14d', emblem: 'flame', plate: '#2a0700',
      pattern: () => stripes('#ffc14d', .22) + `<g fill="none" stroke="#ffc14d" stroke-width="2.5" stroke-linecap="round" opacity=".8"><path d="M44 176 L60 160 L72 168 L92 146"/><path d="M84 146 L92 146 L92 154"/></g>`,
      backDeco: () => `<g class="art-flame" fill="#ff5b3a" opacity=".6"><path d="M34 118 Q26 86 46 66 Q46 90 60 96 Q58 70 78 50 Q80 80 92 90 L92 118 Z"/><path d="M166 118 Q174 86 154 66 Q154 90 140 96 Q142 70 122 50 Q120 80 108 90 L108 118 Z"/></g>`,
    },
    chips: {
      body: ['#4d8dff', '#122a66'], trim: '#050c1f', lidIn: '#0a1a44', glow: '#b9d4ff', emblem: 'diamond', plate: '#050c1f',
      pattern: () => `<g fill="#b9d4ff" opacity=".22">${Array.from({ length: 12 }, (_, i) => `<path d="M${40 + (i % 6) * 24} ${126 + Math.floor(i / 6) * 40} l6 -8 l6 8 l-6 8 z"/>`).join('')}</g>`,
      frontDeco: () => `<g>${[[40, 188, '#4d8dff'], [58, 192, '#fff'], [146, 190, '#b9d4ff'], [164, 187, '#4d8dff']].map(([x, y, c]) => `<ellipse cx="${x}" cy="${y}" rx="9" ry="4" fill="${c}" stroke="#050c1f" stroke-width="1.5"/>`).join('')}</g>`,
    },
    runners: {
      body: ['#2fe3a0', '#0c6b47'], trim: '#03140d', lidIn: '#063a26', glow: '#c4ffe6', emblem: 'chart', plate: '#03140d',
      pattern: () => stripes('#c4ffe6', .16) + `<g stroke="#03140d" stroke-width="2" opacity=".5"><line x1="30" y1="137" x2="170" y2="137"/><line x1="30" y1="162" x2="170" y2="162"/></g>`,
    },
    illiquid: {
      body: ['#b9c7d6', '#4a5a6c'], trim: '#141c26', lidIn: '#26323f', glow: '#e3f3ff', emblem: 'snow', plate: '#141c26',
      pattern: () => `<g fill="#fff" opacity=".35"><path d="M30 112 L170 112 L168 120 Q150 128 140 118 Q124 130 108 118 Q92 130 78 118 Q60 130 46 118 Q38 126 30 120 Z"/></g>
        <g stroke="#fff" stroke-width="1.2" opacity=".3"><path d="M50 140 l14 10 l-6 16 M150 150 l-12 8 l4 14"/></g>`,
      frontDeco: () => `<g fill="#e3f3ff" opacity=".9">${[[36, 112, 10], [60, 112, 7], [150, 112, 9], [168, 112, 6]].map(([x, y, h]) => `<path d="M${x - 3} ${y} L${x + 3} ${y} L${x} ${y + h} Z"/>`).join('')}</g>`,
    },
    // --- бесплатные и эконом
    freebie: {
      body: ['#8fd3ff', '#2a6f9e'], trim: '#07121c', lidIn: '#12344c', glow: '#e6f6ff', emblem: 'bow', plate: '#07121c',
      pattern: () => `<rect x="90" y="112" width="20" height="76" fill="#e6f6ff" opacity=".85"/><rect x="30" y="140" width="140" height="14" fill="#e6f6ff" opacity=".85"/>`,
    },
    partner: {
      body: ['#c6ff3d', '#4f7a0a'], trim: '#0b1206', lidIn: '#233a05', glow: '#eaffb0', emblem: 'bolt', plate: '#0b1206',
      pattern: () => stripes('#0b1206', .18),
    },
    cardboard: {
      body: ['#d9aa6a', '#8a5f2c'], trim: '#5a3a14', lidIn: '#6e4a1e', glow: '#f3dcae', emblem: 'question', plate: '#b98748',
      pattern: () => `<rect x="30" y="140" width="140" height="12" fill="#e9d3a8" opacity=".75"/><g stroke="#6e4a1e" stroke-width="1" opacity=".5"><path d="M40 170 L70 170 M44 176 L64 176"/></g>
        <g fill="none" stroke="#6e4a1e" stroke-width="1.6" opacity=".6"><path d="M136 166 l6 -8 l6 8 M142 158 L142 176"/></g>`,
    },
    bin: {
      body: ['#6fae7f', '#2a5a37'], trim: '#08120b', lidIn: '#173320', glow: '#d8f0de', emblem: 'recycle', plate: '#08120b',
      pattern: () => `<g stroke="#08120b" stroke-width="3" opacity=".35">${[52, 76, 124, 148].map((x) => `<line x1="${x}" y1="122" x2="${x}" y2="182"/>`).join('')}</g>`,
    },
    lunchbox: {
      body: ['#ff8a5c', '#a3401a'], trim: '#1a0b05', lidIn: '#4a1c0a', glow: '#ffe0c2', emblem: 'apple', plate: '#fff4e8',
      pattern: () => `<g fill="#fff" opacity=".25">${Array.from({ length: 14 }, (_, i) => `<circle cx="${40 + (i % 7) * 20}" cy="${128 + Math.floor(i / 7) * 44}" r="4"/>`).join('')}</g>`,
    },
    toolbox: {
      body: ['#ff4d5e', '#8a0f1c'], trim: '#170506', lidIn: '#3a0a10', glow: '#ffd0d4', emblem: 'wrench', plate: '#2a2d33',
      pattern: () => `<g fill="#170506" opacity=".35"><rect x="40" y="122" width="30" height="6" rx="3"/><rect x="130" y="122" width="30" height="6" rx="3"/></g>
        <g fill="#c9ced6">${[[38, 120], [162, 120], [38, 180], [162, 180]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3.2"/>`).join('')}</g>`,
    },
    piggy: {
      body: ['#ff8fc7', '#b33d78'], trim: '#1a0712', lidIn: '#4a1230', glow: '#ffe3f1', emblem: 'coin', plate: '#4a1230',
      pattern: () => `<rect x="84" y="118" width="32" height="5" rx="2.5" fill="#1a0712" opacity=".6"/>`,
      frontDeco: () => `<g>${[[40, 190], [60, 194], [148, 191], [166, 187]].map(([x, y], i) => `<ellipse cx="${x}" cy="${y}" rx="8" ry="3.6" fill="#ffd24d" stroke="#b8861a" stroke-width="1.2" transform="rotate(${i % 2 ? 12 : -10} ${x} ${y})"/>`).join('')}</g>`,
    },
    sahur: {
      body: ['#4a57c9', '#161b52'], trim: '#070a1f', lidIn: '#0e1236', glow: '#dfe3ff', emblem: 'moon', plate: '#070a1f',
      pattern: () => `<g fill="#fff">${[[44, 126], [150, 132], [64, 172], [138, 176], [118, 124], [52, 150]].map(([x, y], i) => `<circle cx="${x}" cy="${y}" r="${i % 2 ? 1 : 1.6}" opacity=".7"/>`).join('')}</g>`,
    },
    mystery: {
      body: ['#8a63d6', '#321a66'], trim: '#0d0719', lidIn: '#1d0f3a', glow: '#efe4ff', emblem: 'question', plate: '#0d0719',
      pattern: () => `<g fill="#efe4ff" opacity=".16" font-family="Unbounded,sans-serif" font-weight="900" font-size="18">${[[40, 136], [140, 136], [58, 178], [128, 180]].map(([x, y]) => `<text x="${x}" y="${y}">?</text>`).join('')}</g>`,
    },
    firstsecret: {
      body: ['#3a3322', '#12100a'], trim: '#ffd84d', lidIn: '#221d0e', glow: '#fff4c2', emblem: 'key', plate: '#171002',
      pattern: () => `<g stroke="#ffd84d" stroke-width="2" fill="none" opacity=".4"><rect x="38" y="120" width="124" height="60" rx="6"/></g>`,
    },
  };

  function stripes(color, opacity) {
    return `<g stroke="${color}" stroke-width="6" opacity="${opacity}">${Array.from({ length: 9 }, (_, i) => `<line x1="${10 + i * 22}" y1="190" x2="${50 + i * 22}" y2="110"/>`).join('')}</g>`;
  }

  function chest(id, skinKey, colors) {
    const s = SKINS[skinKey] || SKINS.vault;
    const [light, dark] = s.body;
    const back = `
      <defs>
        <linearGradient id="${id}b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${light}"/><stop offset="1" stop-color="${dark}"/></linearGradient>
        <linearGradient id="${id}l" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="${s.lidIn}"/><stop offset="1" stop-color="${dark}"/></linearGradient>
        <radialGradient id="${id}g" cx="50%" cy="70%" r="60%"><stop offset="0" stop-color="${s.glow}" stop-opacity=".95"/><stop offset=".45" stop-color="${colors[0]}" stop-opacity=".45"/><stop offset="1" stop-color="${colors[0]}" stop-opacity="0"/></radialGradient>
      </defs>
      <ellipse cx="100" cy="190" rx="84" ry="9" fill="#000" opacity=".45"/>
      <ellipse cx="100" cy="92" rx="96" ry="86" fill="url(#${id}g)" class="art-pulse"/>
      ${s.backDeco ? s.backDeco(id) : ''}
      <!-- крышка, откинутая назад -->
      <path d="M40 98 L160 98 L152 34 Q100 22 48 34 Z" fill="url(#${id}l)" stroke="${s.trim}" stroke-width="4" stroke-linejoin="round"/>
      <path d="M48 34 Q100 22 152 34 L150 24 Q100 10 50 24 Z" fill="${dark}" stroke="${s.trim}" stroke-width="3" stroke-linejoin="round"/>
      <path d="M52 92 L148 92 L142 42 Q100 32 58 42 Z" fill="none" stroke="${s.trim}" stroke-width="1.5" opacity=".5"/>
      ${s.lidDeco ? s.lidDeco(id) : ''}
      <!-- проём со свечением -->
      <path d="M28 112 L172 112 L160 96 L40 96 Z" fill="${dark}" stroke="${s.trim}" stroke-width="3" stroke-linejoin="round"/>
      <ellipse cx="100" cy="104" rx="58" ry="8" fill="${s.glow}" opacity=".85" class="art-pulse"/>
      <path class="art-rays" d="M58 104 L30 20 L70 20 Z M100 104 L92 6 L108 6 Z M142 104 L130 20 L170 20 Z" fill="${s.glow}" opacity=".25"/>`;
    const E = EMBLEMS[s.emblem] || EMBLEMS.star;
    const front = `
      <!-- передняя стенка -->
      <clipPath id="${id}fc"><path d="M28 112 L172 112 L168 186 Q168 190 164 190 L36 190 Q32 190 32 186 Z"/></clipPath>
      <path d="M28 112 L172 112 L168 186 Q168 190 164 190 L36 190 Q32 190 32 186 Z" fill="url(#${id}b)" stroke="${s.trim}" stroke-width="4" stroke-linejoin="round"/>
      <g clip-path="url(#${id}fc)">${s.pattern(id)}</g>
      <path d="M30 116 L170 116" stroke="#fff" stroke-width="2" opacity=".25"/>
      <!-- уголки -->
      <g fill="${s.trim}">
        <path d="M28 112 L48 112 L46 122 L30 124 Z"/><path d="M172 112 L152 112 L154 122 L170 124 Z"/>
        <path d="M32 190 L50 190 L48 180 L33 178 Z"/><path d="M168 190 L150 190 L152 180 L167 178 Z"/>
      </g>
      ${s.frontDeco ? s.frontDeco(id) : ''}
      <!-- замок с эмблемой темы -->
      <g transform="translate(100 150)">
        <rect x="-20" y="-24" width="40" height="46" rx="10" fill="${s.trim}"/>
        <rect x="-17" y="-21" width="34" height="40" rx="8" fill="${s.plate}"/>
        <g transform="translate(0 -1)">${E(colors[0])}</g>
      </g>`;
    return { back, front };
  }

  function artifact(c, extraClass = '') {
    const theme = c.theme || { shape: 'vault', colors: ['#8b93ff', '#d7dcff', '#0b0d1f'] };
    const id = 'ca' + (uid++);
    const { back, front } = chest(id, theme.shape, theme.colors);
    const hero = c.top_item_image_url
      ? `<img class="artifact-hero" src="${c.top_item_image_url}" alt="${c.top_item_name || ''}" loading="lazy" draggable="false">`
      : `<div class="artifact-hero artifact-hero-missing">нет ассета</div>`;
    return `
      <div class="artifact case-model skin-${theme.shape} ${extraClass}">
        <svg class="artifact-svg" viewBox="0 0 200 200" aria-hidden="true">${back}</svg>
        ${hero}
        <svg class="artifact-svg artifact-front" viewBox="0 0 200 200" aria-hidden="true">${front}</svg>
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
