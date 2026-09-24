/* Визуальные темы кейсов Brainrot Battle.
 *
 * Каждый кейс — «артефакт» со своим силуэтом (тарелка, фонарь, колба,
 * сейф, наковальня, иллюминатор, хлопушка, корона), нарисованный здесь
 * в SVG. Внутри артефакта — официальный рендер самого дорогого брейнрота
 * кейса (реальный ассет, не рисунок). Сами брейнроты здесь НЕ рисуются.
 *
 * API:
 *   CaseArt.artifact(caseJson, extraClass) -> HTML
 *   CaseArt.particles(canvas, kind, colors) -> { burst(x, y, color, power), stop() }
 */
(function () {
  let uid = 0;

  // Каждая форма: back (под брейнротом) и front (поверх него). a/b/c — цвета темы.
  const SHAPES = {
    plate(id, [a, b, c]) {
      return {
        back: `
          <defs>
            <pattern id="${id}g" width="16" height="16" patternUnits="userSpaceOnUse" patternTransform="rotate(12)">
              <rect width="16" height="16" fill="#fff4e0"/>
              <rect width="8" height="16" fill="${a}" opacity=".55"/>
              <rect width="16" height="8" fill="${a}" opacity=".55"/>
            </pattern>
            <radialGradient id="${id}r" cx="50%" cy="42%" r="60%">
              <stop offset="0" stop-color="${b}" stop-opacity=".9"/>
              <stop offset=".55" stop-color="${a}" stop-opacity=".35"/>
              <stop offset="1" stop-color="${c}"/>
            </radialGradient>
          </defs>
          <ellipse cx="100" cy="112" rx="94" ry="78" fill="${c}" opacity=".6"/>
          <circle cx="100" cy="104" r="88" fill="url(#${id}g)"/>
          <circle cx="100" cy="104" r="88" fill="none" stroke="${a}" stroke-width="3"/>
          <circle cx="100" cy="104" r="64" fill="url(#${id}r)" stroke="#fff4e0" stroke-width="5"/>`,
        front: `<path d="M34 70 A74 74 0 0 1 120 32" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" opacity=".45"/>`,
      };
    },
    lantern(id, [a, b, c]) {
      return {
        back: `
          <defs>
            <radialGradient id="${id}l" cx="50%" cy="55%" r="55%">
              <stop offset="0" stop-color="${b}" stop-opacity=".95"/>
              <stop offset=".5" stop-color="${a}" stop-opacity=".55"/>
              <stop offset="1" stop-color="${c}" stop-opacity=".95"/>
            </radialGradient>
          </defs>
          <circle cx="100" cy="112" r="92" fill="${a}" opacity=".18" class="art-pulse"/>
          <path d="M84 20 a16 16 0 0 1 32 0" fill="none" stroke="${b}" stroke-width="5"/>
          <path d="M62 44 L138 44 L128 26 L72 26 Z" fill="${c}" stroke="${a}" stroke-width="3"/>
          <rect x="48" y="44" width="104" height="132" rx="18" fill="url(#${id}l)" stroke="${a}" stroke-width="4"/>`,
        front: `
          <g stroke="${c}" stroke-width="4" opacity=".7">
            <line x1="82" y1="46" x2="82" y2="174"/><line x1="118" y1="46" x2="118" y2="174"/>
          </g>
          <path d="M56 176 L144 176 L136 192 L64 192 Z" fill="${c}" stroke="${a}" stroke-width="3"/>
          <rect x="56" y="52" width="10" height="70" rx="5" fill="#fff" opacity=".25"/>`,
      };
    },
    flask(id, [a, b, c]) {
      const body = 'M82 18 L118 18 L118 70 L168 170 Q172 188 152 188 L48 188 Q28 188 32 170 L82 70 Z';
      return {
        back: `
          <defs>
            <clipPath id="${id}c"><path d="${body}"/></clipPath>
            <linearGradient id="${id}f" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stop-color="${b}"/><stop offset="1" stop-color="${a}"/>
            </linearGradient>
          </defs>
          <path d="${body}" fill="${c}" opacity=".85"/>
          <g clip-path="url(#${id}c)">
            <path class="art-wave" d="M0 120 Q25 110 50 120 T100 120 T150 120 T200 120 T250 120 V200 H0 Z" fill="url(#${id}f)" opacity=".85"/>
          </g>`,
        front: `
          <path d="${body}" fill="none" stroke="${b}" stroke-width="4" opacity=".9"/>
          <rect x="76" y="12" width="48" height="10" rx="5" fill="${b}"/>
          <path d="M92 78 L52 160" stroke="#fff" stroke-width="6" stroke-linecap="round" opacity=".3"/>`,
      };
    },
    vault(id, [a, b, c]) {
      const bolts = Array.from({ length: 12 }, (_, i) => {
        const t = (i / 12) * Math.PI * 2;
        return `<circle cx="${100 + Math.cos(t) * 80}" cy="${104 + Math.sin(t) * 80}" r="5" fill="${b}"/>`;
      }).join('');
      const ticks = Array.from({ length: 36 }, (_, i) => {
        const t = (i / 36) * Math.PI * 2;
        const r1 = 62, r2 = i % 3 ? 66 : 70;
        return `<line x1="${100 + Math.cos(t) * r1}" y1="${104 + Math.sin(t) * r1}" x2="${100 + Math.cos(t) * r2}" y2="${104 + Math.sin(t) * r2}"/>`;
      }).join('');
      return {
        back: `
          <defs>
            <radialGradient id="${id}v" cx="40%" cy="35%" r="75%">
              <stop offset="0" stop-color="${b}"/><stop offset=".45" stop-color="${a}"/><stop offset="1" stop-color="${c}"/>
            </radialGradient>
          </defs>
          <circle cx="100" cy="104" r="94" fill="url(#${id}v)"/>
          <circle cx="100" cy="104" r="94" fill="none" stroke="${c}" stroke-width="4" opacity=".6"/>
          ${bolts}
          <g class="art-spin" style="transform-origin:100px 104px" stroke="${c}" stroke-width="2">${ticks}</g>
          <circle cx="100" cy="104" r="58" fill="${c}" opacity=".88"/>`,
        front: `<path d="M40 64 A70 70 0 0 1 96 30" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".5"/>`,
      };
    },
    anvil(id, [a, b, c]) {
      return {
        back: `
          <defs>
            <radialGradient id="${id}h" cx="50%" cy="70%" r="60%">
              <stop offset="0" stop-color="${b}"/><stop offset=".5" stop-color="${a}" stop-opacity=".7"/><stop offset="1" stop-color="${c}" stop-opacity="0"/>
            </radialGradient>
          </defs>
          <ellipse cx="100" cy="120" rx="96" ry="86" fill="url(#${id}h)"/>
          <g class="art-flame" fill="${a}" opacity=".8">
            <path d="M60 150 Q48 96 76 70 Q72 104 92 112 Q86 70 112 40 Q112 90 132 100 Q134 78 146 70 Q164 110 140 150 Z"/>
          </g>
          <g class="art-flame art-flame-2" fill="${b}" opacity=".85">
            <path d="M78 150 Q72 116 92 98 Q92 122 106 126 Q104 100 120 82 Q124 116 136 150 Z"/>
          </g>`,
        front: `
          <path d="M34 150 L166 150 Q170 150 168 156 Q150 164 132 166 L128 178 L148 190 L52 190 L72 178 L68 166 Q40 162 30 156 Q28 150 34 150 Z"
                fill="${c}" stroke="${a}" stroke-width="3"/>
          <path d="M40 154 L160 154" stroke="${b}" stroke-width="3" opacity=".8"/>`,
      };
    },
    porthole(id, [a, b, c]) {
      const bolts = Array.from({ length: 8 }, (_, i) => {
        const t = (i / 8) * Math.PI * 2 + Math.PI / 8;
        return `<circle cx="${100 + Math.cos(t) * 84}" cy="${104 + Math.sin(t) * 84}" r="6" fill="${c}" stroke="${b}" stroke-width="2"/>`;
      }).join('');
      return {
        back: `
          <defs>
            <radialGradient id="${id}w" cx="50%" cy="30%" r="80%">
              <stop offset="0" stop-color="${b}" stop-opacity=".9"/><stop offset=".5" stop-color="${a}" stop-opacity=".7"/><stop offset="1" stop-color="${c}"/>
            </radialGradient>
          </defs>
          <circle cx="100" cy="104" r="72" fill="url(#${id}w)"/>
          <g class="art-rays" opacity=".35" fill="#fff">
            <path d="M80 34 L92 34 L70 176 L50 176 Z"/><path d="M112 34 L122 34 L134 176 L116 176 Z"/>
          </g>`,
        front: `
          <circle cx="100" cy="104" r="84" fill="none" stroke="${a}" stroke-width="22"/>
          <circle cx="100" cy="104" r="84" fill="none" stroke="${b}" stroke-width="3" opacity=".7"/>
          ${bolts}
          <path d="M52 78 A56 56 0 0 1 88 48" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" opacity=".45"/>`,
      };
    },
    popper(id, [a, b, c]) {
      const rays = Array.from({ length: 10 }, (_, i) => {
        const t = -Math.PI * 0.95 + (i / 9) * Math.PI * 0.9;
        return `<line x1="100" y1="120" x2="${100 + Math.cos(t) * 96}" y2="${120 + Math.sin(t) * 96}" stroke="${i % 2 ? a : b}"/>`;
      }).join('');
      return {
        back: `
          <circle cx="100" cy="104" r="90" fill="${c}" opacity=".7"/>
          <g class="art-pulse" stroke-width="7" stroke-linecap="round" opacity=".75">${rays}</g>`,
        front: `
          <g transform="rotate(-24 100 170)">
            <path d="M72 150 L128 150 L106 198 L94 198 Z" fill="${a}" stroke="#fff" stroke-width="2"/>
            <path d="M80 164 L120 164 M86 178 L114 178" stroke="${b}" stroke-width="5"/>
            <ellipse cx="100" cy="150" rx="28" ry="7" fill="${b}"/>
          </g>`,
      };
    },
    crown(id, [a, b, c]) {
      return {
        back: `
          <defs>
            <linearGradient id="${id}p" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="${a}"/><stop offset=".35" stop-color="#7cf3ff"/>
              <stop offset=".65" stop-color="${b}"/><stop offset="1" stop-color="${a}"/>
            </linearGradient>
          </defs>
          <polygon class="art-spin-slow" style="transform-origin:100px 110px" points="100,22 172,66 172,154 100,198 28,154 28,66" fill="url(#${id}p)" opacity=".85"/>
          <polygon points="100,40 156,74 156,146 100,180 44,146 44,74" fill="${c}" opacity=".85"/>`,
        front: `
          <path d="M58 44 L70 10 L86 32 L100 4 L114 32 L130 10 L142 44 Z" fill="${b}" stroke="#fff" stroke-width="2"/>
          <circle cx="100" cy="30" r="5" fill="${a}"/><circle cx="76" cy="34" r="4" fill="#7cf3ff"/><circle cx="124" cy="34" r="4" fill="#7cf3ff"/>`,
      };
    },
  };

  function artifact(c, extraClass = '') {
    const theme = c.theme || { shape: 'vault', colors: ['#8b93ff', '#d7dcff', '#0b0d1f'] };
    const shape = SHAPES[theme.shape] || SHAPES.vault;
    const id = 'ca' + (uid++);
    const { back, front } = shape(id, theme.colors);
    const hero = c.top_item_image_url
      ? `<img class="artifact-hero" src="${c.top_item_image_url}" alt="${c.top_item_name || ''}" loading="lazy" draggable="false">`
      : `<div class="artifact-hero artifact-hero-missing">нет ассета</div>`;
    return `
      <div class="artifact shape-${theme.shape} ${extraClass}">
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

    const count = REDUCED ? 0 : Math.round(Math.min(60, (w * h) / 9000));
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
