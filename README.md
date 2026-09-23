# LocalSight — GitHub Pages

The public website for **LocalSight**, a local-first, privacy-by-design video
intelligence platform. Served via GitHub Pages at
`https://localsightx.github.io/`.

## Sections

- **Landing page** (`index.html`) — the product page: hero, product tour,
  AI engines, cloud comparison, privacy posture, quick start, cameras, an
  on-site **Documentation** band, FAQ and CTA.
- **Documentation** (`docs/`) — the full operator handbook, generated from the
  source repository's Markdown:
  - Getting started — [Installation](docs/installation.html), [User Guide](docs/user-guide.html)
  - Operations — [Runbook](docs/runbook.html),
    [Troubleshooting](docs/troubleshooting.html),
    [ONNX model staging](docs/onnx-detector.html),
    [CI/CD pipeline](docs/ci-cd-pipeline.html)
  - Reference — [API reference](docs/api-reference.html),
    [Camera & NVR integrations](docs/tplink-vigi.html)
  - Architecture — [System architecture](docs/system-architecture.html),
    [Data model](docs/erd.html), [Decision records](docs/adr.html),
    [Threat model](docs/threat-model.html)
  - Security & engineering — [Security architecture](docs/security.html),
    [Architectural review](docs/engineering-review.html)
  - Plus a client-side **search** over every page (`docs/search-index.json`).

## Structure

```
index.html              # Product landing page
docs/                   # Generated documentation (14 pages + hub + search index)
assets/css/style.css    # Site styles (no framework, hand-built)
assets/css/docs.css     # Docs layout (sidebar / content / page TOC / cards)
assets/css/syntax.css   # Pygments code highlighting (dark)
assets/js/main.js       # Nav, tabs, copy buttons, scroll reveal, carousel
assets/js/docs.js       # Sidebar toggle, code copy, scroll-spy, docs search
assets/img/             # Brand mark + product screenshots (WebP)
tools/build_docs.py     # Markdown → HTML docs generator
tools/check_site.py     # Link + well-formedness checker
tools/dom_check.py      # Browser (Playwright) behaviour assertions
tools/browser_check.py  # Browser console-error + screenshot harness
```

## Local preview

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Regenerating the docs

The documentation pages are generated from the LocalSight source repo's
Markdown, so they stay in sync with the product. The generator rewrites
cross-document links onto the generated pages, maps screenshots onto the
site's WebP assets, wraps tables, adds copy buttons to code blocks, builds a
per-page outline, and emits the search index.

```bash
python3 -m venv .venv                        # one-time (gitignored)
.venv/bin/pip install markdown pygments
.venv/bin/python tools/build_docs.py         # default source: ../localsight
.venv/bin/python tools/build_docs.py --src /path/to/localsight
```

Then verify:

```bash
.venv/bin/python tools/check_site.py         # internal links + HTML balance
python tools/dom_check.py --port 8000        # behaviour (needs Playwright)
```

To add a document, add an entry to `DOCS` in `tools/build_docs.py` and re-run.

## Notes

- This is a static site (`.nojekyll`) — no build step or Jekyll theme required.
- Asset paths are relative so the site works both locally and as a GitHub
  project page under `/localsight.github.io/`.
- The docs hub and every generated page share the landing page's nav and
  footer, so the site reads as one product.
- Product content mirrors the main repo docs at
  <https://github.com/localsightX/localsight>.

