/* Starry Pixel engine for T3 Code (MIT). Runs only while the selected theme defines --og-cfg:
   the sky pixels swirl, stars and moon drift, birds, a fox and a hare pass by, stars fall,
   and the village lights follow the local clock. */
;(() => {
  try {
    const root = document.documentElement;
    const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
    // Share of village windows lit, by hour: every light on in the morning, most off at night.
    const LIT = [[0, .14], [5, .1], [6.5, .7], [7.5, 1.3], [12, 1.3], [16, .95], [19, .75], [21.5, .45], [23, .22], [24, .14]];
    const hex = c => { const n = parseInt(c.slice(1), 16); return [n >> 16 & 255, n >> 8 & 255, n & 255]; };
    const mix = (a, b, t) => `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * t)).join(',')})`;
    let run = null, key = '';

    function litShare() {
      const d = new Date(), h = d.getHours() + d.getMinutes() / 60;
      for (let i = 1; i < LIT.length; i++) {
        if (h <= LIT[i][0]) {
          const [h0, f0] = LIT[i - 1], [h1, f1] = LIT[i];
          return f0 + (f1 - f0) * (h - h0) / (h1 - h0);
        }
      }
      return LIT[0][1];
    }

    function random(seed) {
      let s = seed >>> 0;
      return () => (s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296;
    }

    function start(cfg, src, starSrc) {
      const { w, h, pixel } = cfg;
      const state = { stop: false, raf: 0 };
      const canvas = state.canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      canvas.setAttribute('aria-hidden', 'true');
      canvas.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;object-fit:cover;' +
        'pointer-events:none;z-index:0;' + (pixel ? 'image-rendering:pixelated;' : '');
      document.body.prepend(canvas);
      const ctx = canvas.getContext('2d');
      const load = url => new Promise((ok, fail) => { const i = new Image(); i.onload = () => ok(i); i.onerror = fail; i.src = url; });
      Promise.all([load(src), load(starSrc)]).then(([img, stars]) => { if (!state.stop) setup(img, stars); })
        .catch(error => console.warn('Orbital Glass engine: images failed to load', error));

      function setup(img, starImage) {
        const scratch = document.createElement('canvas');
        scratch.width = w;
        scratch.height = h;
        const sc = scratch.getContext('2d', { willReadFrequently: true });
        sc.drawImage(img, 0, 0, w, h);
        const sky = new Uint32Array(sc.getImageData(0, 0, w, h).data.buffer);
        const over = new Uint8Array(w * h);  // land (hills, village, cypress): the sky there is left alone
        for (let i = 0, p = 0; i < cfg.mask.length; i++) {
          if (i & 1) over.fill(1, p, p + cfg.mask[i]);
          p += cfg.mask[i];
        }

        // Every sky pixel near a vortex turns around its center; the closer, the faster.
        const top = cfg.horizon[0] * h, bottom = cfg.horizon[1] * h;
        // One smooth flow field: every vortex pushes the sky around its center (closer = faster),
        // and the pushes add up, so neighboring swirls blend instead of tearing.
        const list = [];
        for (let y = 0; y < bottom; y++) {
          const fade = y < top ? 1 : (bottom - y) / (bottom - top);
          for (let x = 0; x < w; x++) {
            if (over[y * w + x]) continue;
            let vx = 0, vy = 0;
            for (const q of cfg.vortices) {
              const dx = x - q[0], dy = y - q[1];
              const a = cfg.amp * q[3] * q[4] * Math.exp(-(dx * dx + dy * dy) / (q[2] * q[2]));
              vx -= dy * a;
              vy += dx * a;
            }
            vx *= fade;
            vy *= fade;
            if (Math.hypot(vx, vy) < 0.4) continue;
            list.push(y * w + x, x, y, vx, vy, (BAYER[(y & 3) * 4 + (x & 3)] + 0.5) / 16);
          }
        }
        // per pixel: x, y, flow x, flow y (pixels moved per period), dither threshold
        const n = list.length / 6, at = new Int32Array(n), field = new Float32Array(n * 5);
        for (let i = 0; i < n; i++) {
          at[i] = list[i * 6];
          for (let j = 0; j < 5; j++) field[i * 5 + j] = list[i * 6 + 1 + j];
        }
        const frame = ctx.createImageData(w, h), out = new Uint32Array(frame.data.buffer);

        const sample = (o, t) => {  // the sky color that has flowed here after t of a period
          let sx = (field[o] - field[o + 2] * t + 0.5) | 0, sy = (field[o + 1] - field[o + 3] * t + 0.5) | 0;
          sx = sx < 0 ? 0 : sx >= w ? w - 1 : sx;
          sy = sy < 0 ? 0 : sy >= h ? h - 1 : sy;
          return sky[sy * w + sx];
        };

        // Flow-map loop: two copies drift around the vortex half a period apart and cross-fade,
        // so the sky keeps turning forever without winding itself up.
        function swirl(now) {
          const p1 = (now / 1000 / cfg.period) % 1, p2 = (p1 + 0.5) % 1, w1 = 1 - Math.abs(2 * p1 - 1);
          for (let i = 0, o = 0; i < n; i++, o += 5) {
            if (pixel) {  // dithered cross-fade keeps every pixel on the palette
              out[at[i]] = field[o + 4] < w1 ? sample(o, p1) : sample(o, p2);
            } else {
              const c1 = sample(o, p1), c2 = sample(o, p2), w2 = 1 - w1;
              out[at[i]] = 0xff000000 |
                (((c1 >>> 16 & 255) * w1 + (c2 >>> 16 & 255) * w2) << 16) |
                (((c1 >>> 8 & 255) * w1 + (c2 >>> 8 & 255) * w2) << 8) |
                ((c1 & 255) * w1 + (c2 & 255) * w2);
            }
          }
        }

        const rnd = random(1889), dark = hex(cfg.dark), lit = cfg.lit.map(hex);
        const u = cfg.unit;  // canvas pixels per art pixel (1 for the pixel theme)
        const TAU = Math.PI * 2;
        const layer = () => {
          const c = document.createElement('canvas');
          c.width = w;
          c.height = h;
          const g = c.getContext('2d');
          g.imageSmoothingEnabled = !pixel;
          return [c, g];
        };
        const maskCanvas = runs => {  // opaque where the mask is set: used to cut layers behind the land
          const [c, g] = layer(), data = g.createImageData(w, h), px = new Uint32Array(data.buffer);
          for (let i = 0, p = 0; i < runs.length; i++) {
            if (i & 1) px.fill(0xff000000, p, p + runs[i]);
            p += runs[i];
          }
          g.putImageData(data, 0, 0);
          return c;
        };
        const landCut = maskCanvas(cfg.mask), cypressCut = maskCanvas(cfg.cypress);
        const [starCanvas, sg] = layer(), [lifeCanvas, lg] = layer();
        ctx.imageSmoothingEnabled = !pixel;
        const behind = (g, cut) => {
          g.globalCompositeOperation = 'destination-out';
          g.drawImage(cut, 0, 0);
          g.globalCompositeOperation = 'source-over';
        };
        const sprite = (g, rows, colors, x, y, flip) => {
          const width = rows[0].length;
          for (let r = 0; r < rows.length; r++) {
            for (let c = 0; c < width; c++) {
              const ch = rows[r][c];
              if (ch === '.') continue;
              g.fillStyle = colors[ch];
              g.fillRect(Math.round(x + (flip ? width - 1 - c : c) * u), Math.round(y + r * u), u, u);
            }
          }
        };

        // --- village windows -------------------------------------------------------------
        const windows = cfg.windows.map(([x, y, size]) => ({
          x, y, size, rank: rnd(), wobble: 0.08 + rnd() * 0.12, period: 90 + rnd() * 330, phase: rnd() * TAU,
          color: lit[(rnd() * lit.length) | 0], level: 1,
        }));
        let share = litShare(), shareAt = 0;
        function lights(now, dt) {
          if (now - shareAt > 30000) { share = litShare(); shareAt = now; }
          for (const win of windows) {
            const want = share >= 1.2 || win.rank + win.wobble * Math.sin(now / 1000 / win.period * TAU + win.phase) < share ? 1 : 0;
            if (!dt) win.level = want;  // open in the right state, then change slowly
            win.level += Math.sign(want - win.level) * Math.min(Math.abs(want - win.level), dt / cfg.fade);
            const level = pixel ? Math.round(win.level * 3) / 3 : win.level;
            ctx.shadowBlur = pixel ? 0 : 6 * level;
            ctx.shadowColor = mix(win.color, win.color, 0);
            ctx.fillStyle = mix(dark, win.color, level);
            ctx.fillRect(win.x, win.y, win.size, win.size);
          }
          ctx.shadowBlur = 0;
        }

        // --- stars and moon wander a little around their place ------------------------------
        const stars = cfg.stars.map(([x, y, r, arm, drift]) => ({
          x, y, r, arm, drift, px: 18 + rnd() * 22, py: 14 + rnd() * 20, fx: rnd() * TAU, fy: rnd() * TAU,
          twinkle: 1.3 + rnd() * 1.4, tp: rnd(), hidden: over[y * w + x] === 1, dx: 0, dy: 0,
        }));
        function heavens(now, moving) {
          sg.clearRect(0, 0, w, h);
          for (const s of stars) {
            const t = now / 1000;
            s.dx = moving ? s.drift * Math.sin(t / s.px * TAU + s.fx) : 0;
            s.dy = moving ? s.drift * 0.6 * Math.sin(t / s.py * TAU + s.fy) : 0;
            if (pixel) { s.dx = Math.round(s.dx); s.dy = Math.round(s.dy); }
            sg.drawImage(starImage, s.x - s.r, s.y - s.r, 2 * s.r, 2 * s.r, s.x - s.r + s.dx, s.y - s.r + s.dy, 2 * s.r, 2 * s.r);
          }
          behind(sg, landCut);
          ctx.drawImage(starCanvas, 0, 0);
          if (!moving) return;
          for (const s of stars) {
            if (s.hidden) continue;
            const glow = Math.sin(((now / 1000 / s.twinkle + s.tp) % 1) * Math.PI);
            const x = s.x + s.dx, y = s.y + s.dy;
            if (pixel) {  // a pixel cross that grows and shrinks
              const len = Math.round(glow * s.arm);
              if (!len) continue;
              ctx.fillStyle = '#fbe48a';
              ctx.fillRect(x - len, y, len * 2 + 1, 1);
              ctx.fillRect(x, y - len, 1, len * 2 + 1);
              ctx.fillStyle = '#fffbe6';
              ctx.fillRect(x, y, 1, 1);
            } else {  // a soft breathing halo
              const r = s.r * (s.arm ? 1.5 : 1.3), g = ctx.createRadialGradient(x, y, 0, x, y, r);
              g.addColorStop(0, `rgba(255,246,200,${(s.arm ? 0.55 : 0.3) * glow})`);
              g.addColorStop(0.35, `rgba(251,228,138,${(s.arm ? 0.22 : 0.12) * glow})`);
              g.addColorStop(1, 'rgba(251,228,138,0)');
              ctx.globalCompositeOperation = 'lighter';
              ctx.fillStyle = g;
              ctx.fillRect(x - r, y - r, 2 * r, 2 * r);
              ctx.globalCompositeOperation = 'source-over';
            }
          }
        }

        // --- life: birds crossing the sky, a fox and a hare along the hills, falling stars ----
        const BIRD = [['k.....k', '.k...k.', '..k.k..', '...k...'], ['.......', 'kk...kk', '..kkk..', '...k...'],
                      ['.......', '...k...', '.kk.kk.', 'k.....k']];
        const BIRD_COLORS = { k: '#0a1128' };
        const FOX = [
          ['..e..........', '.eHh.........', 'HHHbbbbbbb.tt', '..bbbbbbbbttw', '..l..l..l..l.'],
          ['..e..........', '.eHh.........', 'HHHbbbbbbb.tt', '..bbbbbbbbttw', '...l.l...l.l.'],
        ];
        const FOX_COLORS = { e: '#5e3418', H: '#b0662e', h: '#140c05', b: '#9a5a2e', t: '#a8642c', w: '#e8eef8', l: '#2a1c12' };
        const HARE = [['.....ee.', '......e.', '.bbbbbH.', 'bbbbbbbn', '.l...l..'], ['.....ee.', '.....e..', '.bbbbbH.', 'bbbbbbbn', 'l.....l.']];
        const HARE_COLORS = { e: '#7d8eab', b: '#8e9fbd', H: '#a7b6d1', n: '#c9d6ea', l: '#4a5a78' };
        const groundAt = x => cfg.ground[Math.max(0, Math.min(cfg.ground.length - 1, Math.round(x / 4)))];
        let flocks = [], walkers = [], meteors = [];
        let nextFlock = 4, nextWalker = 9, nextMeteor = 2.5, walkerKind = 0;

        function spawn(t) {
          if (t > nextFlock) {
            nextFlock = t + 18 + rnd() * 22;
            const dir = rnd() < 0.5 ? 1 : -1, y = (cfg.sky[0] + rnd() * (cfg.sky[1] - cfg.sky[0])) * h;
            const n = 3 + ((rnd() * 4) | 0), birds = [];
            for (let i = 0; i < n; i++) {
              birds.push({ back: i * 9 * u + rnd() * 3 * u, side: (i % 2 ? 1 : -1) * Math.ceil(i / 2) * 3 * u,
                           flap: 0.4 + rnd() * 0.25, phase: rnd() });
            }
            flocks.push({ dir, y, x: dir > 0 ? -12 * u : w + 12 * u, speed: w / (11 + rnd() * 7), bob: rnd() * TAU, birds });
          }
          if (t > nextWalker) {
            nextWalker = t + 24 + rnd() * 26;
            const fox = walkerKind++ % 2 === 0, dir = rnd() < 0.5 ? 1 : -1;
            const width = (fox ? 13 : 8) * u;
            walkers.push({ fox, dir, width, x: dir > 0 ? -width : w, speed: w / (fox ? 20 : 26), born: t });
          }
          if (t > nextMeteor) {
            nextMeteor = t + 2 + rnd() * 5;
            const count = rnd() < 0.2 ? 2 : 1;
            for (let i = 0; i < count; i++) {
              const dir = rnd() < 0.6 ? -1 : 1, angle = 0.25 + rnd() * 0.4;
              meteors.push({ x: (0.15 + rnd() * 0.8) * w, y: (0.02 + rnd() * 0.25) * h, vx: dir * Math.cos(angle), vy: Math.sin(angle),
                             dist: (0.12 + rnd() * 0.18) * w, dur: 0.55 + rnd() * 0.5, born: t + i * (0.2 + rnd() * 0.5),
                             tail: (10 + rnd() * 8) * u });
            }
          }
        }

        function life(now) {
          const t = now / 1000;
          spawn(t);
          lg.clearRect(0, 0, w, h);
          flocks = flocks.filter(f => {
            f.x += f.dir * f.speed * frameDt;
            const yb = f.y + Math.sin(t * 1.3 + f.bob) * 3 * u;
            for (const b of f.birds) {
              const x = f.x - f.dir * b.back, y = yb + b.side, beat = ((t / b.flap + b.phase) % 1);
              if (pixel) {
                sprite(lg, BIRD[[0, 1, 2, 1][(beat * 4) | 0]], BIRD_COLORS, x, y, f.dir < 0);
              } else {  // two brushed wing strokes
                const lift = Math.cos(beat * TAU) * 3.2 * u;
                lg.strokeStyle = '#0c1430';
                lg.lineWidth = 1.6 * u / 2;
                lg.lineCap = 'round';
                lg.beginPath();
                lg.moveTo(x - 4.5 * u, y - lift);
                lg.quadraticCurveTo(x - 2 * u, y - 0.8 * u, x, y + 0.8 * u);
                lg.quadraticCurveTo(x + 2 * u, y - 0.8 * u, x + 4.5 * u, y - lift);
                lg.stroke();
              }
            }
            const tailX = f.x - f.dir * (f.birds[f.birds.length - 1].back + 8 * u);
            return f.dir > 0 ? tailX < w + 8 * u : tailX > -8 * u;
          });
          walkers = walkers.filter(a => {
            const pace = a.fox ? 1 : (Math.sin((t - a.born) * 0.9) > -0.35 ? 1 : 0);  // the hare stops now and then
            a.x += a.dir * a.speed * frameDt * pace;
            const step = pace ? ((t * (a.fox ? 5.5 : 3.2)) | 0) % 2 : 0;
            const hop = a.fox || !pace ? 0 : Math.abs(Math.sin(t * 3.2 * Math.PI)) * 3 * u;
            const rows = (a.fox ? FOX : HARE)[step];
            const y = groundAt(a.x + a.width / 2) - rows.length * u + u - hop;
            sprite(lg, rows, a.fox ? FOX_COLORS : HARE_COLORS, a.x, y, a.fox ? a.dir > 0 : a.dir < 0);
            return a.dir > 0 ? a.x < w + a.width : a.x > -2 * a.width;
          });
          meteors = meteors.filter(m => {
            const k = (t - m.born) / m.dur;
            if (k < 0) return true;
            if (k > 1) return false;
            const head = m.dist * (1 - (1 - k) * (1 - k)), fade = k > 0.7 ? (1 - k) / 0.3 : 1;
            const hx = m.x + m.vx * head, hy = m.y + m.vy * head;
            if (pixel) {
              const TAIL = ['#fffbe6', '#fffbe6', '#fbe48a', '#fbe48a', '#f4c84a', '#f4c84a', '#c9a64a', '#86aee3', '#5a8fd6'];
              const len = Math.min(head, m.tail) * fade;
              for (let d = 0; d < len; d++) {
                lg.fillStyle = TAIL[Math.min(TAIL.length - 1, (d / m.tail * TAIL.length) | 0)];
                lg.fillRect(Math.round(hx - m.vx * d), Math.round(hy - m.vy * d), 1, 1);
              }
            } else {
              const len = Math.min(head, m.tail * 1.6), tx = hx - m.vx * len, ty = hy - m.vy * len;
              const g = lg.createLinearGradient(hx, hy, tx, ty);
              g.addColorStop(0, `rgba(255,251,230,${fade})`);
              g.addColorStop(0.3, `rgba(251,228,138,${0.6 * fade})`);
              g.addColorStop(1, 'rgba(134,174,227,0)');
              lg.strokeStyle = g;
              lg.lineWidth = 1.4;
              lg.lineCap = 'round';
              lg.beginPath();
              lg.moveTo(hx, hy);
              lg.lineTo(tx, ty);
              lg.stroke();
            }
            return true;
          });
          behind(lg, cypressCut);
          ctx.drawImage(lifeCanvas, 0, 0);
        }

        const still = matchMedia('(prefers-reduced-motion: reduce)');
        let last = 0, prev = 0, frameDt = 0;
        function tick(now) {
          if (state.stop) return;
          state.raf = requestAnimationFrame(tick);
          const fps = still.matches ? 1 : cfg.fps;
          if (now - last < 1000 / fps - 2) return;
          const dt = prev ? Math.min(now - prev, 1000) / 1000 : 0;
          frameDt = dt;
          prev = last = now;
          const moving = !still.matches;
          if (moving) swirl(now);
          ctx.putImageData(frame, 0, 0);
          heavens(now, moving);
          if (moving) life(now);
          lights(now, dt);
        }
        state.raf = requestAnimationFrame(tick);
      }
      return state;
    }

    function check() {
      if (!document.body) return;
      const style = getComputedStyle(root);
      let cfg = style.getPropertyValue('--og-cfg').trim();
      const next = cfg ? (root.getAttribute('data-theme-id') || '') + ':' + cfg.length : '';
      if (next === key) return;
      key = next;
      if (run) { run.stop = true; cancelAnimationFrame(run.raf); run.canvas.remove(); run = null; }
      if (!cfg) return;
      if (/^['"]/.test(cfg)) cfg = cfg.slice(1, -1);
      const url = name => (/url\(\s*['"]?([^'")\s]+)/.exec(style.getPropertyValue(name)) || [])[1];
      const sky = url('--og-sky'), stars = url('--og-stars');
      if (sky && stars) run = start(JSON.parse(cfg), sky, stars);
    }

    new MutationObserver(check).observe(root, { attributes: true, attributeFilter: ['data-theme-id', 'class'] });
    setInterval(check, 3000);
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', check);
    else check();
  } catch (error) {
    console.warn('Orbital Glass engine disabled:', error);
  }
})();
