/* Собственные векторные иллюстрации персонажей — не фото (см. README в
 * webapp/static/assets/): скачать реальные рендеры физически нельзя (egress-
 * прокси режет любой image-CDN, включая сам figma.com), а аккаунт Figma
 * этого проекта уперся в лимит вызовов MCP на Starter-плане после первых же
 * попыток. Поэтому это — оригинальные SVG-иллюстрации от руки для всех 9
 * персонажей из подтверждённых скриншотом дроп-пулов «Драгон»/«Тако»
 * (единственные кейсы, чьё содержимое реально видно на скриншотах
 * исходного приложения — см. bot/data/seed_cases.py, _DRAGON_ITEMS/_TAKO_ITEMS).
 * Ключ — точное имя персонажа, как в bot/database/models.CaseItem.name. */
window.CHARACTER_ART = {
  'Dragon Cannelloni': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="100" cy="120" rx="62" ry="55" fill="#3a9e5c"/>
    <ellipse cx="100" cy="145" rx="38" ry="24" fill="#9edc9a"/>
    <polygon points="70,70 80,40 90,72" fill="#2a7a44"/>
    <polygon points="95,66 100,34 108,68" fill="#2a7a44"/>
    <polygon points="118,70 128,42 132,74" fill="#2a7a44"/>
    <circle cx="78" cy="108" r="14" fill="#fff"/><circle cx="122" cy="108" r="14" fill="#fff"/>
    <circle cx="80" cy="110" r="6" fill="#141414"/><circle cx="124" cy="110" r="6" fill="#141414"/>
    <ellipse cx="100" cy="140" rx="24" ry="15" fill="#9edc9a"/>
    <ellipse cx="92" cy="146" rx="2.5" ry="3.5" fill="#2a7a44"/><ellipse cx="108" cy="146" rx="2.5" ry="3.5" fill="#2a7a44"/>
    <rect x="50" y="150" width="100" height="22" rx="11" fill="#eed3a0" transform="rotate(-14 100 161)"/>
    <rect x="55" y="172" width="100" height="22" rx="11" fill="#eed3a0" transform="rotate(-14 105 183)"/>
    <circle cx="70" cy="158" r="6" fill="#bd2a1f"/><circle cx="130" cy="180" r="5" fill="#bd2a1f"/><circle cx="100" cy="168" r="4" fill="#bd2a1f"/>
  </svg>`,
  'Moby Bros': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="78" cy="120" rx="55" ry="34" fill="#5b86c9"/>
    <path d="M 30 120 Q 10 105 15 128 Q 25 130 30 120 Z" fill="#5b86c9"/>
    <path d="M 100 92 Q 108 60 118 92 Q 108 98 100 92 Z" fill="#8fb4e6"/>
    <circle cx="55" cy="112" r="6" fill="#141414"/>
    <path d="M 40 132 Q 55 140 70 132" stroke="#3a5f96" stroke-width="4" fill="none" stroke-linecap="round"/>
    <ellipse cx="145" cy="152" rx="38" ry="24" fill="#7ba3dd"/>
    <path d="M 175 152 Q 190 142 188 160 Q 178 162 175 152 Z" fill="#7ba3dd"/>
    <circle cx="128" cy="146" r="4.5" fill="#141414"/>
    <path d="M 118 160 Q 128 165 138 160" stroke="#3a5f96" stroke-width="3" fill="none" stroke-linecap="round"/>
  </svg>`,
  'La Casa Boo': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <path d="M 100 45 L 145 82 L 55 82 Z" fill="#8a5a3c"/>
    <rect x="65" y="82" width="70" height="48" fill="#c98f5e"/>
    <rect x="88" y="100" width="24" height="30" fill="#5a3a24"/>
    <path d="M 55 135 Q 55 105 100 105 Q 145 105 145 135 L 148 175 Q 148 190 132 182 Q 122 192 112 180 Q 100 192 88 180 Q 78 192 68 182 Q 52 190 52 175 Z" fill="#f4f2fb"/>
    <circle cx="82" cy="140" r="7" fill="#241a33"/><circle cx="118" cy="140" r="7" fill="#241a33"/>
    <ellipse cx="100" cy="156" rx="10" ry="7" fill="#241a33"/>
  </svg>`,
  'Rosey and Teddy': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <circle cx="70" cy="70" r="18" fill="#8a5a3c"/><circle cx="130" cy="70" r="18" fill="#8a5a3c"/>
    <circle cx="70" cy="70" r="9" fill="#c98f5e"/><circle cx="130" cy="70" r="9" fill="#c98f5e"/>
    <circle cx="100" cy="112" r="58" fill="#a4703f"/>
    <ellipse cx="100" cy="130" rx="32" ry="26" fill="#dcb388"/>
    <circle cx="82" cy="102" r="7" fill="#241a15"/><circle cx="118" cy="102" r="7" fill="#241a15"/>
    <ellipse cx="100" cy="122" rx="9" ry="7" fill="#3a281c"/>
    <path d="M 88 134 Q 100 144 112 134" stroke="#3a281c" stroke-width="3" fill="none" stroke-linecap="round"/>
    <g transform="translate(148,155)">
      <circle r="16" fill="#c8283f"/><circle cx="-8" cy="-8" r="10" fill="#e0435c"/><circle cx="9" cy="-6" r="10" fill="#e0435c"/>
      <rect x="-3" y="10" width="6" height="26" rx="3" fill="#3a9e5c"/>
    </g>
  </svg>`,
  'Foxini Lanternini': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <polygon points="55,60 78,35 85,75" fill="#e07b2a"/><polygon points="145,60 122,35 115,75" fill="#e07b2a"/>
    <polygon points="60,62 78,45 82,72" fill="#f4d8b8"/><polygon points="140,62 122,45 118,72" fill="#f4d8b8"/>
    <ellipse cx="100" cy="110" rx="52" ry="48" fill="#e07b2a"/>
    <path d="M 65 118 Q 100 150 135 118 Q 135 145 100 155 Q 65 145 65 118 Z" fill="#f4d8b8"/>
    <circle cx="80" cy="105" r="7" fill="#241a15"/><circle cx="120" cy="105" r="7" fill="#241a15"/>
    <ellipse cx="100" cy="122" rx="6" ry="5" fill="#241a15"/>
    <g transform="translate(152,148)">
      <rect x="-14" y="-18" width="28" height="34" rx="6" fill="#f0c043"/>
      <rect x="-16" y="-24" width="32" height="8" rx="4" fill="#a8730f"/>
      <rect x="-3" y="-30" width="6" height="8" fill="#a8730f"/>
      <circle r="6" fill="#fff4cc" opacity="0.85"/>
    </g>
  </svg>`,
  'La Supreme Combinasion': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <circle cx="70" cy="110" r="42" fill="#a259e6"/><circle cx="130" cy="90" r="36" fill="#f0435c"/><circle cx="115" cy="145" r="34" fill="#f0a93c"/>
    <circle cx="60" cy="100" r="6" fill="#fff"/><circle cx="60" cy="100" r="3" fill="#241a33"/>
    <circle cx="82" cy="100" r="6" fill="#fff"/><circle cx="82" cy="100" r="3" fill="#241a33"/>
    <circle cx="122" cy="82" r="5" fill="#fff"/><circle cx="122" cy="82" r="2.5" fill="#241a33"/>
    <circle cx="138" cy="82" r="5" fill="#fff"/><circle cx="138" cy="82" r="2.5" fill="#241a33"/>
    <circle cx="106" cy="140" r="5" fill="#fff"/><circle cx="106" cy="140" r="2.5" fill="#241a33"/>
    <circle cx="124" cy="140" r="5" fill="#fff"/><circle cx="124" cy="140" r="2.5" fill="#241a33"/>
  </svg>`,
  'Guest 666': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <circle cx="100" cy="115" r="55" fill="#b8283f"/>
    <polygon points="65,75 78,45 88,78" fill="#7a1626"/><polygon points="112,78 122,45 135,75" fill="#7a1626"/>
    <circle cx="82" cy="108" r="8" fill="#241014"/><circle cx="118" cy="108" r="8" fill="#241014"/>
    <path d="M 78 138 Q 100 122 122 138" stroke="#241014" stroke-width="4" fill="none" stroke-linecap="round"/>
    <rect x="66" y="165" width="68" height="22" rx="11" fill="#241014"/>
    <text x="100" y="181" font-size="15" font-weight="900" fill="#f0435c" text-anchor="middle" font-family="sans-serif">666</text>
  </svg>`,
  'Fortunu and Cashuru': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <g transform="translate(78,105)">
      <circle cx="-16" cy="-16" r="20" fill="#3ecf6e"/><circle cx="16" cy="-16" r="20" fill="#3ecf6e"/>
      <circle cx="-16" cy="16" r="20" fill="#3ecf6e"/><circle cx="16" cy="16" r="20" fill="#3ecf6e"/>
      <rect x="-4" y="10" width="8" height="34" rx="4" fill="#2a9e52"/>
      <circle cx="-16" cy="-16" r="6" fill="#1f7a3c"/><circle cx="16" cy="-16" r="6" fill="#1f7a3c"/>
      <circle cx="-16" cy="16" r="6" fill="#1f7a3c"/><circle cx="16" cy="16" r="6" fill="#1f7a3c"/>
    </g>
    <g transform="translate(142,132)">
      <circle r="34" fill="#f0c043"/><circle r="26" fill="#ffe08a"/>
      <text x="0" y="9" font-size="26" font-weight="900" fill="#a8730f" text-anchor="middle" font-family="sans-serif">$</text>
    </g>
  </svg>`,
  'Sammuni Fattini': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <rect x="60" y="70" width="80" height="90" rx="14" fill="#e8433c"/>
    <rect x="60" y="70" width="80" height="26" rx="14" fill="#c8283f"/>
    <circle cx="82" cy="112" r="8" fill="#241014"/><circle cx="118" cy="112" r="8" fill="#241014"/>
    <path d="M 82 136 Q 100 148 118 136" stroke="#241014" stroke-width="4" fill="none" stroke-linecap="round"/>
    <rect x="72" y="48" width="56" height="22" rx="6" fill="#a8730f"/>
    <circle cx="100" cy="46" r="10" fill="#f0c043"/>
  </svg>`,
};
