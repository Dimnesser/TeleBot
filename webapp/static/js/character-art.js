/* Собственные векторные иллюстрации персонажей — не фото. Проверено дважды
 * (curl напрямую): скачать реальные рендеры нельзя — egress-прокси возвращает
 * 403 на любой image-CDN (Wikia/Fandom, Wikimedia, Imgur, jsDelivr) и на сам
 * figma.com. Figma MCP тоже не вариант: whoami показывает seat="View" на
 * Starter-плане — по официальной таблице лимитов Figma это 20 write-вызовов
 * в МЕСЯЦ на весь аккаунт (не на сессию), и они уже исчерпаны прошлым
 * прогоном; чтобы поднять лимит, нужно одновременно и сменить план, и сменить
 * тип места на Full/Dev — то есть это не «подожди» и не временный затык.
 *
 * Поэтому — оригинальные SVG-иллюстрации от руки. Изначально было 9
 * персонажей из кейсов «Драгон»/«Тако» (единственных, чей состав был виден на
 * скриншотах исходного приложения). Теперь здесь ВСЕ 18 уникальных
 * «top_item» — самый ценный (и потому самый заметный, см. top_item_name в
 * webapp/api.py) персонаж КАЖДОГО из 36 кейсов, так что каждая карточка на
 * главном экране и иконка-герой в модалке кейса получают тематический арт, а
 * не плейсхолдер-эмодзи. Персонажи вроде Tralalero Tralala/Skibidi Toilet —
 * интернет-мемы без единого канонiчного дизайна (это AI-генерируемые
 * фьюжны), поэтому трактовка от имени (акула в кроссовках, унитаз с головой
 * и т.п.) — обоснованная интерпретация, а не выдумка с нуля.
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
  'Tralalero Tralala': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="100" cy="105" rx="46" ry="62" fill="#5c7a94"/>
    <polygon points="82,46 100,18 118,46" fill="#3e5a70"/>
    <ellipse cx="100" cy="118" rx="30" ry="42" fill="#dce8ee"/>
    <circle cx="86" cy="92" r="7" fill="#141414"/>
    <polygon points="76,108 84,120 92,108" fill="#fff"/>
    <polygon points="94,110 102,124 110,110" fill="#fff"/>
    <polygon points="112,108 120,120 128,108" fill="#fff"/>
    <rect x="66" y="168" width="26" height="18" rx="6" fill="#2f6fd6"/>
    <rect x="108" y="168" width="26" height="18" rx="6" fill="#2f6fd6"/>
    <rect x="66" y="178" width="26" height="8" rx="4" fill="#fff"/>
    <rect x="108" y="178" width="26" height="8" rx="4" fill="#fff"/>
  </svg>`,
  'Skibidi Toilet': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <rect x="56" y="120" width="88" height="52" rx="10" fill="#f2f4f7"/>
    <rect x="64" y="96" width="72" height="34" rx="16" fill="#fff"/>
    <ellipse cx="100" cy="96" rx="36" ry="14" fill="#dfe6ec"/>
    <ellipse cx="100" cy="96" rx="26" ry="9" fill="#8a97a6"/>
    <circle cx="100" cy="62" r="30" fill="#e8b98c"/>
    <circle cx="90" cy="58" r="5" fill="#241a14"/><circle cx="110" cy="58" r="5" fill="#241a14"/>
    <ellipse cx="100" cy="76" rx="12" ry="9" fill="#7a2b1e"/>
    <rect x="72" y="176" width="56" height="10" rx="5" fill="#c7cfd9"/>
  </svg>`,
  'Sigma Boy': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="100" cy="118" rx="54" ry="50" fill="#4a4a52"/>
    <polygon points="58,84 46,52 76,72" fill="#4a4a52"/>
    <polygon points="142,84 154,52 124,72" fill="#4a4a52"/>
    <ellipse cx="100" cy="128" rx="34" ry="24" fill="#dcdce0"/>
    <rect x="66" y="98" width="68" height="18" rx="9" fill="#141414"/>
    <circle cx="82" cy="107" r="3" fill="#3a3a40"/><circle cx="118" cy="107" r="3" fill="#3a3a40"/>
    <path d="M 84 144 Q 100 136 116 144" stroke="#241a1a" stroke-width="3" fill="none" stroke-linecap="round"/>
    <circle cx="100" cy="168" r="8" fill="#f0c043"/>
    <circle cx="84" cy="172" r="6" fill="#f0c043"/><circle cx="116" cy="172" r="6" fill="#f0c043"/>
  </svg>`,
  'Glorbo Fruttodrillo': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="100" cy="130" rx="58" ry="30" fill="#3e9e52"/>
    <path d="M 46 118 Q 30 108 40 96 Q 56 100 60 116 Z" fill="#3e9e52"/>
    <polygon points="52,102 58,90 66,104" fill="#2a7a3c"/>
    <polygon points="66,98 72,86 80,100" fill="#2a7a3c"/>
    <circle cx="48" cy="102" r="5" fill="#fff"/><circle cx="49" cy="103" r="2.5" fill="#141414"/>
    <circle cx="118" cy="112" r="14" fill="#f0a93c"/><circle cx="140" cy="120" r="11" fill="#e8433c"/>
    <circle cx="128" cy="134" r="10" fill="#f0c043"/><circle cx="104" cy="138" r="9" fill="#e8433c"/>
    <ellipse cx="70" cy="140" rx="16" ry="10" fill="#dcefc8"/>
  </svg>`,
  'Chef Crabracadaba': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="100" cy="128" rx="48" ry="36" fill="#d8402f"/>
    <circle cx="52" cy="108" r="18" fill="#d8402f"/><circle cx="148" cy="108" r="18" fill="#d8402f"/>
    <path d="M 40 100 Q 28 92 34 104 Q 44 110 48 102 Z" fill="#b8281a"/>
    <path d="M 160 100 Q 172 92 166 104 Q 156 110 152 102 Z" fill="#b8281a"/>
    <circle cx="84" cy="120" r="6" fill="#141414"/><circle cx="116" cy="120" r="6" fill="#141414"/>
    <path d="M 80 76 L 66 50 L 92 62 Z" fill="#7a3cb8"/>
    <path d="M 92 62 L 118 46 L 116 74 Z" fill="#8a4cd0"/>
    <circle cx="70" cy="54" r="4" fill="#f0c043"/>
    <rect x="128" y="142" width="4" height="30" fill="#7a3cb8" transform="rotate(20 130 157)"/>
    <polygon points="144,138 150,148 138,148" fill="#f0c043" transform="rotate(20 144 143)"/>
  </svg>`,
  'Cappuccino Assassino': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <path d="M 66 90 L 74 158 Q 76 172 100 172 Q 124 172 126 158 L 134 90 Z" fill="#f4ead8"/>
    <ellipse cx="100" cy="90" rx="34" ry="12" fill="#5c3a24"/>
    <path d="M 66 96 Q 44 96 46 114 Q 48 130 68 122" stroke="#c9a876" stroke-width="7" fill="none"/>
    <rect x="64" y="112" width="72" height="16" fill="#141414"/>
    <circle cx="84" cy="120" r="4" fill="#e8b98c"/><circle cx="116" cy="120" r="4" fill="#e8b98c"/>
    <polygon points="100,138 106,158 94,158" fill="#8a97a6"/>
  </svg>`,
  'Ballerina Cappuccina': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <path d="M 70 66 L 76 118 Q 78 130 100 130 Q 122 130 124 118 L 130 66 Z" fill="#f4ead8"/>
    <ellipse cx="100" cy="66" rx="30" ry="10" fill="#7a4a2c"/>
    <path d="M 90 56 Q 100 40 112 54" stroke="#c9a876" stroke-width="5" fill="none" stroke-linecap="round"/>
    <circle cx="90" cy="98" r="4" fill="#241a14"/><circle cx="110" cy="98" r="4" fill="#241a14"/>
    <path d="M 92 112 Q 100 118 108 112" stroke="#241a14" stroke-width="2.5" fill="none"/>
    <path d="M 70 130 Q 100 150 130 130 L 138 148 Q 100 166 62 148 Z" fill="#f06b9c"/>
    <rect x="86" y="148" width="6" height="34" fill="#f4ead8"/><rect x="108" y="148" width="6" height="34" fill="#f4ead8"/>
    <ellipse cx="89" cy="184" rx="8" ry="4" fill="#e0a0c0"/><ellipse cx="111" cy="184" rx="8" ry="4" fill="#e0a0c0"/>
  </svg>`,
  'Banditto Bobritto': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="100" cy="116" rx="52" ry="46" fill="#8a5a34"/>
    <ellipse cx="66" cy="88" r="14" fill="#8a5a34"/><ellipse cx="134" cy="88" r="14" fill="#8a5a34"/>
    <rect x="70" y="98" width="60" height="20" rx="4" fill="#141414"/>
    <circle cx="86" cy="108" r="2.5" fill="#dcdce0"/><circle cx="114" cy="108" r="2.5" fill="#dcdce0"/>
    <rect x="88" y="128" width="10" height="16" rx="2" fill="#fff"/><rect x="102" y="128" width="10" height="16" rx="2" fill="#fff"/>
    <ellipse cx="100" cy="176" rx="26" ry="12" fill="#6a4222"/>
  </svg>`,
  'Pengolino Nuvoletto': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="100" cy="128" rx="46" ry="40" fill="#a87848"/>
    <path d="M 60 108 Q 100 92 140 108" stroke="#8a5a34" stroke-width="8" fill="none"/>
    <path d="M 64 126 Q 100 110 136 126" stroke="#8a5a34" stroke-width="8" fill="none"/>
    <path d="M 68 144 Q 100 130 132 144" stroke="#8a5a34" stroke-width="8" fill="none"/>
    <circle cx="86" cy="102" r="4" fill="#241a14"/>
    <ellipse cx="66" cy="66" rx="30" ry="18" fill="#fff"/>
    <ellipse cx="90" cy="60" rx="22" ry="14" fill="#fff"/>
    <ellipse cx="126" cy="70" rx="24" ry="15" fill="#fff"/>
  </svg>`,
  'Pinealotto Fruttarino': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="100" cy="126" rx="42" ry="52" fill="#e0a934"/>
    <path d="M 64 96 L 76 118 L 88 96 L 100 118 L 112 96 L 124 118 L 136 96" stroke="#a8730f" stroke-width="4" fill="none"/>
    <path d="M 64 126 L 76 148 L 88 126 L 100 148 L 112 126 L 124 148 L 136 126" stroke="#a8730f" stroke-width="4" fill="none"/>
    <polygon points="80,74 90,38 96,76" fill="#3e9e52"/>
    <polygon points="100,72 100,32 110,74" fill="#3e9e52"/>
    <polygon points="112,76 128,42 122,78" fill="#3e9e52"/>
    <circle cx="88" cy="150" r="4" fill="#241a14"/><circle cx="112" cy="150" r="4" fill="#241a14"/>
  </svg>`,
  'Pipi Avocado': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <path d="M 100 40 Q 150 50 150 112 Q 150 168 100 176 Q 50 168 50 112 Q 50 50 100 40 Z" fill="#5c8a3c"/>
    <path d="M 100 54 Q 138 62 138 112 Q 138 158 100 165 Q 62 158 62 112 Q 62 62 100 54 Z" fill="#c8dc8a"/>
    <circle cx="100" cy="118" r="30" fill="#7a4a2c"/>
    <circle cx="90" cy="110" r="4" fill="#4a2a18"/><circle cx="110" cy="110" r="4" fill="#4a2a18"/>
    <path d="M 92 126 Q 100 132 108 126" stroke="#4a2a18" stroke-width="2.5" fill="none"/>
  </svg>`,
  'Boneca Ambalabu': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <circle cx="100" cy="86" r="40" fill="#f0d0ae"/>
    <path d="M 64 70 Q 60 40 90 46" stroke="#8a5a2c" stroke-width="6" fill="none" stroke-linecap="round"/>
    <path d="M 136 70 Q 140 40 110 46" stroke="#8a5a2c" stroke-width="6" fill="none" stroke-linecap="round"/>
    <path d="M 82 80 L 90 88 M 90 80 L 82 88" stroke="#7a3020" stroke-width="3"/>
    <path d="M 110 80 L 118 88 M 118 80 L 110 88" stroke="#7a3020" stroke-width="3"/>
    <path d="M 88 104 Q 100 98 112 104" stroke="#7a3020" stroke-width="2.5" fill="none"/>
    <rect x="66" y="124" width="68" height="54" rx="10" fill="#d8402f"/>
    <path d="M 66 138 L 134 138 M 66 152 L 134 152 M 66 166 L 134 166" stroke="#8a1a10" stroke-width="2" stroke-dasharray="4 4"/>
  </svg>`,
  'La Grande Combinasion': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <circle cx="66" cy="120" r="38" fill="#a259e6"/><circle cx="128" cy="94" r="32" fill="#f0435c"/>
    <circle cx="140" cy="146" r="30" fill="#f0a93c"/><circle cx="88" cy="76" r="26" fill="#3ecf6e"/>
    <polygon points="100,26 108,44 92,44" fill="#f0c043"/>
    <circle cx="56" cy="112" r="5" fill="#fff"/><circle cx="56" cy="112" r="2.5" fill="#241a33"/>
    <circle cx="76" cy="112" r="5" fill="#fff"/><circle cx="76" cy="112" r="2.5" fill="#241a33"/>
    <circle cx="120" cy="88" r="4" fill="#fff"/><circle cx="120" cy="88" r="2" fill="#241a33"/>
    <circle cx="136" cy="88" r="4" fill="#fff"/><circle cx="136" cy="88" r="2" fill="#241a33"/>
    <circle cx="132" cy="142" r="4" fill="#fff"/><circle cx="132" cy="142" r="2" fill="#241a33"/>
    <circle cx="148" cy="142" r="4" fill="#fff"/><circle cx="148" cy="142" r="2" fill="#241a33"/>
  </svg>`,
  'Frogo Elfo': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <polygon points="60,80 40,52 70,66" fill="#3e9e52"/>
    <polygon points="140,80 160,52 130,66" fill="#3e9e52"/>
    <ellipse cx="100" cy="118" rx="52" ry="44" fill="#4bb864"/>
    <circle cx="78" cy="92" r="16" fill="#4bb864"/><circle cx="122" cy="92" r="16" fill="#4bb864"/>
    <circle cx="78" cy="90" r="7" fill="#141414"/><circle cx="122" cy="90" r="7" fill="#141414"/>
    <path d="M 76 130 Q 100 144 124 130" stroke="#1f6a30" stroke-width="4" fill="none" stroke-linecap="round"/>
    <polygon points="82,58 100,36 106,60" fill="#2a7a3c"/>
  </svg>`,
  'Cupcake Koala': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <path d="M 62 118 L 138 118 L 128 180 Q 100 190 72 180 Z" fill="#e8433c"/>
    <path d="M 64 122 L 136 122 M 68 138 L 132 138 M 72 154 L 128 154" stroke="#b8281a" stroke-width="3"/>
    <path d="M 66 118 Q 100 94 134 118 Q 116 106 100 112 Q 84 106 66 118 Z" fill="#f4ead8"/>
    <circle cx="100" cy="88" r="30" fill="#9aa0a8"/>
    <circle cx="72" cy="68" r="14" fill="#9aa0a8"/><circle cx="128" cy="68" r="14" fill="#9aa0a8"/>
    <circle cx="72" cy="68" r="7" fill="#6c727a"/><circle cx="128" cy="68" r="7" fill="#6c727a"/>
    <circle cx="90" cy="86" r="4" fill="#241a14"/><circle cx="110" cy="86" r="4" fill="#241a14"/>
    <ellipse cx="100" cy="98" rx="8" ry="6" fill="#241a14"/>
  </svg>`,
  'Hydra Dragon Cannelloni': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="100" cy="140" rx="50" ry="34" fill="#3a9e5c"/>
    <path d="M 70 118 Q 62 84 76 54" stroke="#3a9e5c" stroke-width="18" fill="none" stroke-linecap="round"/>
    <path d="M 130 118 Q 138 84 124 54" stroke="#3a9e5c" stroke-width="18" fill="none" stroke-linecap="round"/>
    <circle cx="76" cy="48" r="16" fill="#3a9e5c"/><circle cx="124" cy="48" r="16" fill="#3a9e5c"/>
    <circle cx="71" cy="45" r="4" fill="#fff"/><circle cx="81" cy="45" r="4" fill="#fff"/>
    <circle cx="119" cy="45" r="4" fill="#fff"/><circle cx="129" cy="45" r="4" fill="#fff"/>
    <polygon points="66,36 72,22 78,38" fill="#2a7a44"/><polygon points="114,38 120,22 126,36" fill="#2a7a44"/>
    <rect x="60" y="154" width="80" height="18" rx="9" fill="#eed3a0"/>
    <circle cx="76" cy="163" r="5" fill="#bd2a1f"/><circle cx="100" cy="163" r="5" fill="#bd2a1f"/><circle cx="124" cy="163" r="5" fill="#bd2a1f"/>
  </svg>`,
  'Brr Brr Patapim': `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <rect x="76" y="90" width="48" height="76" rx="16" fill="#8a5a34"/>
    <path d="M 78 100 L 122 100 M 78 116 L 122 116 M 78 132 L 122 132 M 78 148 L 122 148" stroke="#6a4222" stroke-width="2"/>
    <circle cx="100" cy="66" r="34" fill="#a8703f"/>
    <path d="M 100 70 Q 84 96 78 108 Q 90 112 100 92 Q 110 112 122 108 Q 116 96 100 70 Z" fill="#a8703f"/>
    <circle cx="90" cy="58" r="4" fill="#241a14"/><circle cx="110" cy="58" r="4" fill="#241a14"/>
    <polygon points="82,36 100,20 96,42" fill="#7a5230"/>
    <polygon points="70,180 78,160 86,180" fill="#dfe6ec"/>
    <polygon points="114,180 122,160 130,180" fill="#dfe6ec"/>
    <rect x="60" y="112" width="12" height="4" fill="#8a5a34"/><rect x="128" y="112" width="12" height="4" fill="#8a5a34"/>
  </svg>`,
};
