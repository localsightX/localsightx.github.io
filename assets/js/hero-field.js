/* LocalSight hero — "detection field".
 *
 * An original take on an AI-surveillance visual: the hero background is a
 * live inference view. Rectangles drift like tracked objects in a camera
 * scene, each carrying a track ID and a jittering confidence score; a soft
 * scan sweep passes periodically like a frame being processed; nearby
 * boxes share faint edges the way a tracker links appearances between
 * frames. Pure canvas 2D, ~60fps on a laptop iGPU, pauses entirely for
 * prefers-reduced-motion, and darkens under the page's own palette.
 * Decorative only — aria-hidden, no pointer events.
 */
(() => {
  const cv = document.getElementById('detfield');
  if (!cv) return;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (reduced.matches) { cv.remove(); return; }

  const ctx = cv.getContext('2d');
  let W = 0, H = 0, dpr = 1;
  const mouse = { x: -1e4, y: -1e4 };

  // palette (matches assets/css/style.css)
  const C = {
    accent:  [34, 211, 238],   // cyan
    accent2: [125, 232, 178],  // green
    warn:    [251, 191, 36],   // amber
    ink:     [11, 16, 32],     // bg
  };
  const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;

  // tracked "objects": label pools from the actual product
  const CLASSES = ['person', 'vehicle', 'bicycle', 'motorcycle', 'bus', 'truck', 'animal', 'bag', 'package'];
  const tracks = [];
  const N = 14;

  function rand(a, b) { return a + Math.random() * (b - a); }

  function spawn(i) {
    const w = rand(70, 150), h = rand(46, 110);
    return {
      x: rand(-40, W - w + 40),
      y: rand(20, H - h - 20),
      w, h,
      vx: rand(-0.16, 0.16), vy: rand(-0.10, 0.10),
      cls: CLASSES[(Math.random() * CLASSES.length) | 0],
      conf: rand(0.74, 0.97),
      id: 400 + ((Math.random() * 500) | 0),
      hue: Math.random(),
    };
  }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    const r = cv.getBoundingClientRect();
    W = r.width; H = r.height;
    cv.width = W * dpr; cv.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function init() {
    resize();
    tracks.length = 0;
    for (let i = 0; i < N; i++) tracks.push(spawn(i));
  }

  let sweep = -1;            // scan-sweep progress; <0 = idle
  let sweepCooldown = 140;   // frames until next sweep

  function colorFor(t) {
    if (t.cls === 'person') return C.accent;
    if (t.cls === 'vehicle' || t.cls === 'truck' || t.cls === 'bus') return C.accent2;
    return C.warn;
  }

  function draw(ts) {
    ctx.clearRect(0, 0, W, H);

    // vignette base so text stays readable over the canvas
    const g = ctx.createRadialGradient(W * 0.7, H * 0.25, 0, W * 0.7, H * 0.25, Math.max(W, H) * 0.8);
    g.addColorStop(0, rgba(C.ink, 0.0));
    g.addColorStop(1, rgba(C.ink, 0.55));
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);

    const mx = mouse.x, my = mouse.y;

    // tracker edges: faint links between nearby boxes (association lines)
    for (let i = 0; i < tracks.length; i++) {
      for (let j = i + 1; j < tracks.length; j++) {
        const a = tracks[i], b = tracks[j];
        const ax = a.x + a.w / 2, ay = a.y + a.h / 2;
        const bx = b.x + b.w / 2, by = b.y + b.h / 2;
        const d = Math.hypot(ax - bx, ay - by);
        if (d < 260) {
          ctx.strokeStyle = rgba(C.accent, (1 - d / 260) * 0.10);
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
        }
      }
    }

    // boxes
    for (const t of tracks) {
      t.x += t.vx; t.y += t.vy;
      // drift parallax away from the cursor (the field "responds")
      const px = t.x + t.w / 2 - mx, py = t.y + t.h / 2 - my;
      const pd = Math.hypot(px, py) || 1;
      const near = Math.max(0, 1 - pd / 420);
      const push = near * 0.6;
      t.x += (px / pd) * push; t.y += (py / pd) * push;

      if (t.x < -60) t.x = W + 40; if (t.x > W + 60) t.x = -40;
      if (t.y < 14) { t.y = 14; t.vy *= -1; }
      if (t.y + t.h > H - 14) { t.y = H - 14 - t.h; t.vy *= -1; }

      // confidence jitters like a live model
      t.conf += rand(-0.0025, 0.0025);
      t.conf = Math.min(0.98, Math.max(0.71, t.conf));

      const col = colorFor(t);
      const active = sweep >= 0 && Math.abs((t.y + t.h / 2) - sweep) < 90;
      const glow = active ? 0.95 : 0.55;

      ctx.strokeStyle = rgba(col, glow);
      ctx.lineWidth = active ? 2 : 1.2;
      ctx.strokeRect(t.x, t.y, t.w, t.h);

      // corner ticks (tracker style)
      const cl = 12;
      ctx.lineWidth = 2;
      ctx.strokeStyle = rgba(col, glow);
      ctx.beginPath();
      ctx.moveTo(t.x, t.y + cl); ctx.lineTo(t.x, t.y); ctx.lineTo(t.x + cl, t.y);
      ctx.moveTo(t.x + t.w - cl, t.y + t.h); ctx.lineTo(t.x + t.w, t.y + t.h); ctx.lineTo(t.x + t.w, t.y + t.h - cl);
      ctx.stroke();

      // label chip
      const label = `${t.cls} ${(t.conf * 100 | 0)}%`;
      const tid = `#${t.id}`;
      ctx.font = '600 11px "Space Grotesk", system-ui, sans-serif';
      const lw = ctx.measureText(label).width + 14;
      const lh = 18;
      const ly = t.y - lh - 3; const lx = t.x;
      ctx.fillStyle = rgba(col, active ? 0.22 : 0.14);
      ctx.strokeStyle = rgba(col, 0.5);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(lx, ly, lw, lh, 4); ctx.fill(); ctx.stroke();
      ctx.fillStyle = rgba(col, 0.95);
      ctx.fillText(label, lx + 7, ly + 13);
      ctx.fillStyle = rgba(col, 0.55);
      ctx.font = '600 9px ui-monospace, monospace';
      ctx.fillText(tid, lx + lw + 7, ly + 13);
    }

    // scan sweep
    if (sweep >= 0) {
      sweep += H / 90; // ~1.5s to cross
      if (sweep > H + 60) { sweep = -1; sweepCooldown = 150 + Math.random() * 180; }
      else {
        const sg = ctx.createLinearGradient(0, sweep - 70, 0, sweep);
        sg.addColorStop(0, rgba(C.accent, 0));
        sg.addColorStop(1, rgba(C.accent, 0.10));
        ctx.fillStyle = sg;
        ctx.fillRect(0, sweep - 70, W, 70);
        ctx.strokeStyle = rgba(C.accent, 0.30);
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(0, sweep); ctx.lineTo(W, sweep); ctx.stroke();
      }
    } else if (--sweepCooldown <= 0) {
      sweep = -70;
    }

    requestAnimationFrame(draw);
  }

  window.addEventListener('resize', init, { passive: true });
  cv.addEventListener('pointermove', (e) => {
    const r = cv.getBoundingClientRect();
    mouse.x = e.clientX - r.left; mouse.y = e.clientY - r.top;
  }, { passive: true });
  cv.addEventListener('pointerleave', () => { mouse.x = mouse.y = -1e4; });

  init();
  requestAnimationFrame(draw);
})();
