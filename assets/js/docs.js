// docs.js — behaviour for the generated documentation pages and the docs hub.
// Progressive enhancement only; the pages remain readable with JS disabled.

/* ── Sidebar collapse (mobile) ──────────────────────────────────────────── */
(() => {
  const nav = document.getElementById('docsnav');
  const toggle = document.getElementById('docsnavToggle');
  const body = document.getElementById('docsnavBody');
  if (!nav || !toggle || !body) return;

  const narrow = () => window.matchMedia('(max-width: 900px)').matches;
  const apply = () => {
    if (narrow()) {
      body.hidden = true;              // hide the list, keep the toggle visible
      toggle.setAttribute('aria-expanded', 'false');
    } else {
      body.hidden = false;
      toggle.setAttribute('aria-expanded', 'true');
    }
  };
  apply();
  window.addEventListener('resize', apply);

  toggle.addEventListener('click', () => {
    const open = body.hidden;
    body.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
  });
  // Collapse after choosing a page on mobile.
  nav.addEventListener('click', (e) => {
    if (e.target.closest('a') && narrow()) {
      body.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
    }
  });
})();

/* ── Copy buttons on code blocks ────────────────────────────────────────── */
(() => {
  const blocks = document.querySelectorAll('.prose .highlight');
  blocks.forEach((block) => {
    const btn = block.querySelector('.copybtn');
    const code = block.querySelector('code');
    if (!btn || !code) return;
    btn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(code.innerText);
        btn.textContent = 'Copied!';
      } catch (e) {
        btn.textContent = 'Copy failed';
      }
      setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
    });
  });
})();

/* ── Scroll-spy for the page outline ────────────────────────────────────── */
(() => {
  const toc = document.getElementById('toc');
  if (!toc) return;
  const links = [...toc.querySelectorAll('a[data-toc]')];
  const headings = links
    .map((a) => document.getElementById(a.dataset.toc))
    .filter(Boolean);
  if (!headings.length) return;

  const setActive = (id) => links.forEach((a) =>
    a.setAttribute('aria-current', String(a.dataset.toc === id)));

  const visible = new Set();
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting) visible.add(e.target.id);
      else visible.delete(e.target.id);
    }
    const topmost = headings.map((h) => h.id).filter((id) => visible.has(id))[0];
    if (topmost) setActive(topmost);
  }, { rootMargin: '-90px 0px -70% 0px' });
  headings.forEach((h) => io.observe(h));
})();

/* ── Documentation search (hub page) ────────────────────────────────────── */
(() => {
  const input = document.getElementById('docSearch');
  if (!input) return;
  const results = document.getElementById('docSearchResults');
  const status = document.getElementById('docSearchStatus');
  const indexURL = new URL('search-index.json', document.baseURI).href;

  const STOP = new Set(['the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'for',
    'on', 'is', 'are', 'with', 'your', 'how', 'what', 'why', 'it', 'this',
    'that', 'as', 'at', 'by', 'be', 'from', 'can', 'do', 'if', 'not', 'all']);
  const esc = (s) => s.replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  let docs = null;
  let loadFailed = false;
  const load = async () => {
    if (docs || loadFailed) return docs;
    try {
      docs = await (await fetch(indexURL)).json();
    } catch (e) {
      loadFailed = true;
      console.warn('docs search index unavailable', e);
    }
    return docs;
  };

  // Case-insensitive substring scoring across title, category, blurb and body.
  const score = (doc, terms) => {
    const hay = (doc.title + ' \n ' + doc.category + ' \n ' +
                 doc.blurb + ' \n ' + doc.text).toLowerCase();
    let total = 0;
    for (const t of terms) {
      const idx = hay.indexOf(t);
      if (idx < 0) return 0;                 // AND semantics: every term must match
      total += 1 + Math.max(0, 12 - Math.floor(idx / 400));
      if (idx < doc.title.length + doc.category.length + 4) total += 4;
    }
    return total;
  };

  const snippet = (doc, terms) => {
    const hay = doc.text.toLowerCase();
    const at = hay.indexOf(terms[0]);
    if (at < 0) return esc(doc.blurb);
    const start = Math.max(0, at - 90);
    const end = Math.min(doc.text.length, at + terms[0].length + 150);
    const raw = (start > 0 ? '… ' : '') + doc.text.slice(start, end) +
                (end < doc.text.length ? ' …' : '');
    let out = esc(raw);
    for (const t of terms) {
      try {
        out = out.replace(
          new RegExp('(' + t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi'),
          '<mark>$1</mark>');
      } catch (e) { /* bad term — leave unhighlighted */ }
    }
    return out;
  };

  let timer = null;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(run, 110);
  });
  input.addEventListener('keydown', (e) => {
    const first = results.querySelector('.sresult');
    if (e.key === 'Enter' && first) first.click();
    if (e.key === 'Escape') { input.value = ''; run(); }
  });

  const run = async () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { results.innerHTML = ''; status.textContent = ''; return; }
    const terms = q.split(/\s+/).filter((t) => t.length > 1 && !STOP.has(t));
    if (!terms.length) {
      results.innerHTML = '<p class="searchempty">Type a keyword to search every page.</p>';
      status.textContent = '';
      return;
    }
    const index = await load();
    if (!index) {
      results.innerHTML = '<p class="searchempty">Search index could not be loaded.</p>';
      status.textContent = '';
      return;
    }
    const hits = index
      .map((d) => ({ d, s: score(d, terms) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 8);
    if (!hits.length) {
      results.innerHTML = '<p class="searchempty">No matches. Try “camera”, “alert”, “retention”, or “ffmpeg”.</p>';
      status.textContent = '0 results';
      return;
    }
    results.innerHTML = hits.map(({ d }) =>
      `<a class="sresult" href="${d.url}">
         <span class="t">${esc(d.title)}</span>
         <span class="c">${esc(d.category)}</span>
         <span class="d">${snippet(d, terms)}</span>
       </a>`).join('');
    status.textContent = `${hits.length} page${hits.length === 1 ? '' : 's'} match`;
  };

  // "/" focuses the search box — handy on a docs landing page.
  document.addEventListener('keydown', (e) => {
    const tag = document.activeElement ? document.activeElement.tagName : '';
    if (e.key === '/' && document.activeElement !== input && !/^(INPUT|TEXTAREA)$/.test(tag)) {
      e.preventDefault();
      input.focus();
    }
  });
})();
