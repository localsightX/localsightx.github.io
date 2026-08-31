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
