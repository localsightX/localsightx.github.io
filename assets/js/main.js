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



// Product-tour carousel: one screenshot per slide, dots + arrows + swipe,
// auto-advance 5s. Rotation pauses while the visitor interacts and resumes
// after an idle window — engagement is DERIVED from live state each tick
// (hover or focus inside), never a sticky flag, so it can never deadlock.
(() => {
  const root = document.getElementById('tourCarousel');
  if (!root) return;
  const slidesEl = root.querySelector('.slides');
  const slides = [...slidesEl.querySelectorAll('.slide')];
  const dotsEl = root.querySelector('.car-dots');
  const prev = root.querySelector('.car-prev');
  const next = root.querySelector('.car-next');
  const HOLD = 5000, IDLE = 12000;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  let i = 0, timer = null, lastUse = 0;

  const occupied = () => root.matches(':hover') || root.contains(document.activeElement);

  slides.forEach((_, k) => {
    const d = document.createElement('button');
    d.type = 'button';
    d.setAttribute('role', 'tab');
    d.setAttribute('aria-label', `Screenshot ${k + 1} of ${slides.length}`);
    d.addEventListener('click', (e) => { go(k); used(e); });
    dotsEl.appendChild(d);
  });
  const dots = [...dotsEl.children];

  function go(n) {
    i = (n + slides.length) % slides.length;
    slidesEl.style.transform = `translateX(-${i * 100}%)`;
    dots.forEach((d, k) => {
      d.classList.toggle('is-active', k === i);
      d.setAttribute('aria-selected', String(k === i));
    });
    slides.forEach((s, k) => s.setAttribute('aria-hidden', String(k !== i)));
  }

  function used(e) {
    lastUse = Date.now();
    // Pointer-activated controls release focus so keyboard users don't lose
    // their place but rotation isn't held hostage by a clicked button.
    if (e && e.currentTarget && e.detail !== 0) e.currentTarget.blur();
  }

  prev.addEventListener('click', (e) => { go(i - 1); used(e); });
  next.addEventListener('click', (e) => { go(i + 1); used(e); });

  root.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') { go(i - 1); used(); e.preventDefault(); }
    if (e.key === 'ArrowRight') { go(i + 1); used(); e.preventDefault(); }
  });

  let x0 = null;
  root.addEventListener('touchstart', (e) => { x0 = e.touches[0].clientX; lastUse = Date.now(); }, { passive: true });
  root.addEventListener('touchend', (e) => {
    if (x0 === null) return;
    const dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 40) { go(dx < 0 ? i + 1 : i - 1); lastUse = Date.now(); }
    x0 = null;
  }, { passive: true });

  function tick() {
    clearTimeout(timer);
    if (!reduced.matches && !occupied() && Date.now() - lastUse > IDLE) {
      go(i + 1);                      // idle + unattended -> rotate
      timer = setTimeout(tick, HOLD);
    } else {
      timer = setTimeout(tick, 1200); // busy or cooling down -> re-check soon
    }
  }

  document.addEventListener('visibilitychange', () => {
    clearTimeout(timer);
    if (!document.hidden) timer = setTimeout(tick, 800);
  });

  go(0);
  if (!reduced.matches) timer = setTimeout(tick, HOLD); else go(0);
})();


// Mobile sticky CTA: hide itself while its destination (#start) is in view,
// so it never covers content the visitor is trying to read.
(() => {
  const bar = document.querySelector('.msticky');
  if (!bar) return;
  const target = document.getElementById('start');
  if (!target) return;
  const io = new IntersectionObserver((es) => {
    for (const e of es) bar.classList.toggle('is-hidden', e.isIntersecting);
  }, { rootMargin: '-80px 0px -120px 0px' });
  io.observe(target);
})();
