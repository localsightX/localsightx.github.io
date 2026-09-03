// Mobile nav
const toggle = document.getElementById('navToggle');
const links = document.getElementById('navLinks');
toggle.addEventListener('click', () => {
  const open = links.classList.toggle('open');
  toggle.setAttribute('aria-expanded', String(open));
});
links.querySelectorAll('a').forEach(a =>
  a.addEventListener('click', () => {
    links.classList.remove('open');
    toggle.setAttribute('aria-expanded', 'false');
  })
);

// Tabs
document.querySelectorAll('.tabs__btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const id = btn.dataset.tab;
    const root = btn.closest('.tabs');
    root.querySelectorAll('.tabs__btn').forEach(b => b.classList.toggle('is-active', b === btn));
    root.querySelectorAll('.tabs__panel').forEach(p =>
      p.classList.toggle('is-active', p.dataset.panel === id)
    );
  });
});

// Copy buttons
document.querySelectorAll('.copy').forEach(btn => {
  btn.addEventListener('click', async () => {
    const code = btn.parentElement.querySelector('code').innerText;
    try {
      await navigator.clipboard.writeText(code);
      const old = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => (btn.textContent = old), 1400);
    } catch (e) {
      btn.textContent = 'Copy failed';
    }
  });
});

// Year
document.getElementById('year').textContent = new Date().getFullYear();

// Reveal on scroll
const io = new IntersectionObserver(
  entries => entries.forEach(e => e.isIntersecting && e.target.classList.add('in')),
  { threshold: 0.12 }
);
document.querySelectorAll('.card, .flow__step, .section__head, .privacy__panel').forEach(el => {
  el.classList.add('reveal');
  io.observe(el);
});

// Product-tour tabs (separate from the quick-start code tabs)
document.querySelectorAll('#tourTabs .tabs__btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const id = btn.dataset.tour;
    const root = document.getElementById('tourTabs');
    root.querySelectorAll('.tabs__btn').forEach(b => {
      const on = b === btn;
      b.classList.toggle('is-active', on);
      b.setAttribute('aria-selected', String(on));
    });
    root.querySelectorAll('.tour-panel').forEach(p =>
      p.classList.toggle('is-active', p.dataset.tourPanel === id)
    );
  });
});


// Product-tour auto-slider: advances every 7s with a progress ring on the
// active tab; pauses on hover/focus within the section or after a manual
// click (resumes after 15s idle). A11y: buttons are real tabs, rotation
// stops entirely when the user prefers reduced motion.
(() => {
  const root = document.getElementById('tourTabs');
  if (!root) return;
  const btns = [...root.querySelectorAll('.tabs__btn')];
  const panels = [...root.querySelectorAll('.tour-panel')];
  const HOLD = 7000, IDLE = 15000;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  let i = 0, timer = null, paused = false, resumeAt = 0, prog = 0, last = 0;

  function show(n, fromAuto) {
    i = (n + btns.length) % btns.length;
    btns.forEach((b, k) => {
      const on = k === i;
      b.classList.toggle('is-active', on);
      b.setAttribute('aria-selected', String(on));
    });
    panels.forEach((p, k) => p.classList.toggle('is-active', k === i));
    prog = 0;
    if (!fromAuto) { paused = true; resumeAt = Date.now() + IDLE; }
  }

  function tick(ts) {
    if (last) {
      const dt = ts - last;
      if (paused && Date.now() > resumeAt) paused = false;
      if (!paused) {
        prog += dt;
        const b = btns[i];
        if (b) b.style.setProperty('--p', String(Math.min(1, prog / HOLD)));
        if (prog >= HOLD) show(i + 1, true);
      }
    }
    last = ts;
    requestAnimationFrame(tick);
  }

  btns.forEach((b, k) => b.addEventListener('click', () => show(k, false)));
  root.addEventListener('pointerenter', () => { paused = true; });
  root.addEventListener('pointerleave', () => { resumeAt = Date.now() + 250; paused = false; });
  root.addEventListener('focusin', () => { paused = true; resumeAt = Date.now() + IDLE; });

  if (!reduced.matches) { show(0, true); requestAnimationFrame(tick); }
})();
