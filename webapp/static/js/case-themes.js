/* Модели кейсов BrainCore.
 *
 * Каждый кейс — 3D-рендер (three.js, офлайн: tools/case_renders) открытого
 * кейса-чемодана с тематическим наполнителем, аурой и героями кейса внутри
 * (официальные рендеры брейнротов). Здесь только вывод картинки и частицы.
 *
 * API:
 *   CaseArt.artifact(caseJson, extraClass) -> HTML
 *   CaseArt.particles(canvas, kind, colors) -> { burst(x, y, color, power), stop() }
 */
(function () {
  function artifact(c, extraClass = '') {
    const alt = String(c.name || '').replace(/"/g, '&quot;');
    return c.image_url
      ? `<div class="artifact case-render ${extraClass}"><img src="${c.image_url}" alt="${alt}" loading="lazy" draggable="false"></div>`
      : `<div class="artifact case-render missing ${extraClass}"><span>${alt}</span></div>`;
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
