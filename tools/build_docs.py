#!/usr/bin/env python3
"""build_docs.py — render the LocalSight product docs as static HTML pages.

Reads the Markdown documentation from the LocalSight source repository and
writes a fully styled, self-contained documentation section into this GitHub
Pages site (``docs/*.html`` + ``docs/search-index.json``).

The generated pages reuse the site's existing design system: they load
``assets/css/style.css`` (nav, brand, footer, tokens) and add
``assets/css/docs.css`` for the docs layout (sidebar / content / page TOC).

Why a generator instead of a runtime Markdown renderer?
  * The site is served statically with ``.nojekyll`` — no build step at serve
    time, no client-side Markdown library, no flash of unrendered text.
  * Cross-document links and screenshots are rewritten to their on-site
    targets (see ``rewrite_targets``), so the docs read like a handbook.
  * The search index is built once, offline.

Usage (from the repository root)::

    .venv/bin/python tools/build_docs.py                  # default: ../localsight
    .venv/bin/python tools/build_docs.py --src /path/to/localsight

Requires ``markdown`` and ``pygments`` (install into the repo's .venv, which
is gitignored — see README "Regenerating the docs").
"""

from __future__ import annotations

import argparse
import html as html_mod
import json
import os
import posixpath
import re
import sys

import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES_ROOT = os.path.dirname(HERE)
DEFAULT_SRC = os.path.normpath(os.path.join(PAGES_ROOT, "..", "localsight"))
OUT_DIR = os.path.join(PAGES_ROOT, "docs")
SHOTS_DIR = os.path.join(PAGES_ROOT, "assets", "img", "shots")
GITHUB = "https://github.com/localsightX/localsight"
RAW_GITHUB = "https://raw.githubusercontent.com/localsightX/localsight/main"

# Screenshots available on the site (assets/img/shots/*.webp). Markdown
# references like img/overview.png are rewritten onto these when present.
available_shots = {
    os.path.splitext(f)[0]
    for f in os.listdir(SHOTS_DIR)
    if f.lower().endswith(".webp")
}

# ── Icon set (Feather-style strokes, currentColor) ─────────────────────────
ICONS = {
    "rocket": '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    "wrench": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    "gauge": '<path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z"/><path d="M12 12l4-4"/>',
    "cpu": '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>',
    "git": '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="9" r="3"/><path d="M18 12v3a3 3 0 0 1-3 3H9M6 9v6"/>',
    "code": '<path d="M16 18l6-6-6-6M8 6l-6 6 6 6"/>',
    "plug": '<path d="M12 2v6M8 8h8l-1 6a4 4 0 0 1-6 0z"/><path d="M12 20v2"/>',
    "layers": '<path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3M21 5v14c0 1.66-4 3-9 3s-9-1.34-9-3V5"/>',
    "scale": '<path d="M12 3v18M5 7h14M7 7l-3 7h6zM17 7l-3 7h6z"/>',
    "milestone": '<path d="M7 3v18M7 7h9a3 3 0 0 1 0 6H7"/><circle cx="18" cy="10" r="2"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>',
    "alert": '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4M12 17h.01"/>',
}


def icon(name: str) -> str:
    body = ICONS.get(name, ICONS["book"])
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            + body + '</svg>')

# ── Documentation registry ─────────────────────────────────────────────────
# (category, source path inside the repo, output filename, title, blurb, icon)
# Order here drives the docs hub and the sidebar.
DOCS: list[dict] = [
    {"cat": "Getting started", "src": "docs/operations/installation.md",
     "out": "installation", "title": "Installation & Setup", "icon": "rocket",
     "blurb": "Prerequisites, three install paths (venv, Docker Compose, local rig), first-run bootstrap, and a post-install verification checklist."},
    {"cat": "Getting started", "src": "docs/USER_GUIDE.md",
     "out": "user-guide", "title": "User Guide", "icon": "book",
     "blurb": "Every screen of the console, end to end: cameras, privacy masks, behavior rules, live view, events, alerts, people, and privacy controls."},
    {"cat": "Operations", "src": "docs/operations/runbook.md",
     "out": "runbook", "title": "Operations Runbook", "icon": "gauge",
     "blurb": "Day-to-day operations: health & readiness, retention, backup and restore, capacity, alert channels, and the secure-deployment checklist."},
    {"cat": "Operations", "src": "docs/operations/troubleshooting.md",
     "out": "troubleshooting", "title": "Troubleshooting", "icon": "wrench",
     "blurb": "Symptom → likely cause → fix, for startup, cameras & ingestion, recording and live view, alerts, storage and performance."},
    {"cat": "Operations", "src": "docs/operations/onnx-detector.md",
     "out": "onnx-detector", "title": "AI Model Staging (ONNX)", "icon": "cpu",
     "blurb": "Stage detection, ANPR, face and attribute models with SHA-256 verification. Backends, GPU acceleration, and per-camera performance gates."},
    {"cat": "Operations", "src": "docs/operations/ci-cd-pipeline.md",
     "out": "ci-cd-pipeline", "title": "CI/CD Pipeline", "icon": "git",
     "blurb": "The 10-job pipeline behind every commit — lint, tests, SAST, dependency and container scans, browser e2e, quality gate — and its local equivalents."},
    {"cat": "Reference", "src": "docs/api/openapi-summary.md",
     "out": "api-reference", "title": "API Reference", "icon": "code",
     "blurb": "Every endpoint with its required permission, plus copy-paste curl use cases: cameras, search, timeline, rules, live view, analytics, alerts."},
    {"cat": "Reference", "src": "docs/integrations/tplink-vigi.md",
     "out": "tplink-vigi", "title": "Camera & NVR Integrations", "icon": "plug",
     "blurb": "TP-Link VIGI/Tapo setup (one call provisions a whole NVR), ONVIF discovery, and multi-vendor RTSP presets."},
    {"cat": "Architecture", "src": "docs/architecture/system-architecture.md",
     "out": "system-architecture", "title": "System Architecture", "icon": "layers",
     "blurb": "End-to-end data flow, the per-camera processing pipeline, security boundaries, and the scaling story."},
    {"cat": "Architecture", "src": "docs/architecture/erd.md",
     "out": "erd", "title": "Data Model (ERD)", "icon": "database",
     "blurb": "Tables and relationships, hot-path indexes, and exactly which columns are encrypted at rest."},
    {"cat": "Architecture", "src": "docs/architecture/adr.md",
     "out": "adr", "title": "Decision Records (ADR)", "icon": "milestone",
     "blurb": "Why a modular monolith, SQLite by default, swappable AI interfaces, envelope encryption, and no insecure defaults."},
    {"cat": "Architecture", "src": "docs/architecture/threat-model.md",
     "out": "threat-model", "title": "Threat Model", "icon": "scale",
     "blurb": "STRIDE-aligned threats with the attack, impact, mitigation, detection, and recovery for each."},
    {"cat": "Security", "src": "docs/security/SECURITY.md",
     "out": "security", "title": "Security Architecture", "icon": "shield",
     "blurb": "Authentication, RBAC, envelope encryption, audit logging, the SSRF egress guard, and AI supply-chain integrity."},
    {"cat": "Engineering", "src": "docs/reviews/CODE_ANALYSIS_REPORT.md",
     "out": "engineering-review", "title": "Architectural Review", "icon": "search",
     "blurb": "The full architectural review with evidence and fix rationale — every defect found, why it mattered, and the regression test that pins it."},
]
CATEGORIES = ["Getting started", "Operations", "Reference",
              "Architecture", "Security", "Engineering"]

# ── Markdown → HTML ────────────────────────────────────────────────────────
def render_markdown(text: str) -> str:
    """Convert Markdown to HTML with heading ids, tables and highlighted code."""
    md = markdown.Markdown(
        extensions=["extra", "sane_lists", "toc", "markdown.extensions.codehilite"],
        extension_configs={
            "toc": {"permalink": False, "title": "Contents"},
            "markdown.extensions.codehilite": {
                "css_class": "highlight",
                "guess_lang": False,
                "noclasses": False,
            },
        },
        output_format="html5",
    )
    return md.convert(text)


TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(html_fragment: str) -> str:
    return html_mod.unescape(TAG_RE.sub(" ", html_fragment))


# ── Link / image rewriting ─────────────────────────────────────────────────
def rewrite_targets(body: str, doc: dict, by_src: dict) -> str:
    """Point cross-doc links and screenshots at their on-site targets.

    * ``img/<name>.png`` → ``../assets/img/shots/<name>.webp`` when the site
      has that screenshot, else the upstream raw file.
    * relative ``.md`` links between registered docs → the generated page.
    * any other repo-relative path (scripts, .env, source files) → GitHub.
    * absolute URLs and same-page ``#anchors`` are left untouched.
    """
    src_dir = posixpath.dirname(doc["src"])

    def repl(match: "re.Match[str]") -> str:
        attr, val = match.group(1), match.group(2)
        if not val:
            return match.group(0)
        target = html_mod.unescape(val)
        if (target.startswith("#") or target.startswith("http://")
                or target.startswith("https://") or target.startswith("mailto:")):
            return match.group(0)

        is_img = attr == "src"
        target, _, fragment = target.partition("#")
        resolved = posixpath.normpath(posixpath.join(src_dir, target)) if src_dir else target

        if is_img:
            stem = os.path.splitext(os.path.basename(resolved))[0]
            new_val = (f"../assets/img/shots/{stem}.webp" if stem in available_shots
                       else f"{RAW_GITHUB}/{resolved}")
            return f'{attr}="{new_val}"'

        if resolved in by_src:
            new_val = f"{by_src[resolved]['out']}.html"
            if fragment:
                new_val += f"#{fragment}"
            return f'{attr}="{new_val}"'

        # Fall back to the source repository (blob view for browseability).
        return f'{attr}="{GITHUB}/blob/main/{resolved}"'

    return re.sub(r'(href|src)="([^"]*)"', repl, body)


# ── Prose post-processing ──────────────────────────────────────────────────
TABLE_RE = re.compile(r"(<table\b.*?</table>)", re.S)
HEADING_RE = re.compile(r'<h([23])\s+id="([^"]+)">(.*?)</h\1>', re.S)
CODEBLOCK_OPEN_RE = re.compile(r'<div class="(?:highlight|codehilite)">')
FRAG_RE = re.compile(r'href="#([^"]+)"')


def _norm_frag(frag: str) -> str:
    """Collapse a slug to a punctuation-insensitive form for anchor matching."""
    return re.sub(r"[^a-z0-9]+", "-", frag.lower()).strip("-")


LINK_RE = re.compile(r'(<a\s+href="([^"]+)">)(.*?)(</a>)', re.S)


def polish_link_text(body: str) -> str:
    """Show a document's title when a cross-link's text is a bare filename.

    The source Markdown links to companions with the filename as the label
    (``installation.md``); on the rendered site that reads poorly, so swap it
    for the registered page title. Only exact filename labels are rewritten,
    so hand-written prose labels are never touched.
    """
    title_by_out = {d["out"]: d for d in DOCS}

    def repl(match: "re.Match[str]") -> str:
        open_tag, href, text, close = match.group(1), match.group(2), \
            match.group(3), match.group(4)
        if href.startswith(("http", "mailto:")):
            return match.group(0)
        stem = href.split("#")[0]
        if not stem.endswith(".html"):
            return match.group(0)
        doc = title_by_out.get(stem[:-5])
        if not doc:
            return match.group(0)
        if strip_tags(text).strip().lower() == os.path.basename(doc["src"]).lower():
            return open_tag + doc["title"] + close
        return match.group(0)

    return LINK_RE.sub(repl, body)


def fix_fragments(body: str) -> str:
    """Rejoin same-page anchors that assume GitHub's slugify.

    The source Markdown's internal links were written for GitHub's anchor
    algorithm (``Health & readiness`` → ``health--readiness``), which differs
    from Python-Markdown's (``health-readiness``). Every heading id we emit is
    authoritative, so a link whose *normalized* form matches a real id is
    rewritten onto that id. Cross-page ``page.html#frag`` links are left alone.
    """
    ids = set(re.findall(r'<h[23]\s+id="([^"]+)"', body))
    by_norm: dict[str, str] = {}
    for hid in ids:
        by_norm.setdefault(_norm_frag(hid), hid)

    def repl(match: "re.Match[str]") -> str:
        frag = match.group(1)
        if frag in ids:
            return match.group(0)
        target = by_norm.get(_norm_frag(frag))
        return f'href="#{target}"' if target else match.group(0)

    return FRAG_RE.sub(repl, body)


def postprocess(body: str) -> tuple[str, list[dict]]:
    # Wrap tables so wide ones scroll instead of blowing out the grid.
    body = TABLE_RE.sub(r'<div class="tablewrap">\1</div>', body)
    # Copy button on every fenced code block (wired up by docs.js).
    body = CODEBLOCK_OPEN_RE.sub(
        '<div class="highlight" tabindex="0">'
        '<button class="copybtn" type="button" aria-label="Copy code">Copy</button>',
        body)
    # Page outline for the right rail.
    toc: list[dict] = []
    for level, hid, inner in HEADING_RE.findall(body):
        label = re.sub(r"\s+", " ", strip_tags(inner)).strip()
        if label:
            toc.append({"level": int(level), "id": hid, "label": label})
    return body, toc


# ── Shared chrome (nav / sidebar / footer) ─────────────────────────────────
# The docs nav mirrors the product page nav but points in-page sections back
# at ../index.html#… and adds a prominent Documentation entry.
NAV_LINKS = [
    ("Product tour", "../index.html#tour"),
    ("AI engines", "../index.html#features"),
    ("Compare", "../index.html#compare"),
    ("Privacy", "../index.html#privacy"),
    ("Quick start", "../index.html#start"),
    ("Open source", "../index.html#opensource"),
    ("Cameras", "../index.html#cameras"),
]


def nav_html(active_docs: bool = False) -> str:
    links = "".join(f'<a href="{href}">{label}</a>' for label, href in NAV_LINKS)
    docs_cls = ' aria-current="page"' if active_docs else ""
    return f"""
  <header class="nav" id="nav">
    <div class="container nav__inner">
      <a class="brand" href="../index.html" aria-label="LocalSight home">
        <img src="../assets/img/favicon.svg" alt="" width="30" height="30" />
        <span>Local<strong>Sight</strong></span>
      </a>
      <nav class="nav__links" id="navLinks" aria-label="Primary">
        {links}
        <a href="../docs/"{docs_cls}>Documentation</a>
        <a class="nav__cta" href="{GITHUB}" target="_blank" rel="noopener">GitHub ↗</a>
      </nav>
      <button class="nav__toggle" id="navToggle" aria-label="Toggle menu" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
    </div>
  </header>"""


FOOTER_DOC_LINKS = [
    ("Installation", "installation.html"),
    ("User guide", "user-guide.html"),
    ("Operations runbook", "runbook.html"),
    ("Troubleshooting", "troubleshooting.html"),
    ("ONNX detector", "onnx-detector.html"),
    ("API reference", "api-reference.html"),
    ("Security", "security.html"),
]
FOOTER_MORE_LINKS = [
    ("Architecture", "system-architecture.html"),
    ("Threat model", "threat-model.html"),
    ("Camera integrations", "tplink-vigi.html"),
    ("Engineering review", "engineering-review.html"),
]


def footer_html() -> str:
    doc_links = "".join(f'          <a href="{h}">{l}</a>\n' for l, h in FOOTER_DOC_LINKS)
    more_links = "".join(f'          <a href="{h}">{l}</a>\n' for l, h in FOOTER_MORE_LINKS)
    return f"""
  <footer class="footer">
    <div class="container footer__inner">
      <div class="footer__brand">
        <img src="../assets/img/favicon.svg" alt="" width="26" height="26" />
        <span>Local<strong>Sight</strong></span>
        <p>Local-first, privacy-by-design video intelligence.</p>
      </div>
      <nav class="footer__cols" aria-label="Footer">
        <div>
          <h2 class="footer__h">Project</h2>
          <a href="{GITHUB}" target="_blank" rel="noopener">Source</a>
          <a href="{GITHUB}/issues" target="_blank" rel="noopener">Issues</a>
          <a href="{GITHUB}/blob/main/LICENSE" target="_blank" rel="noopener">License</a>
        </div>
        <div>
          <h2 class="footer__h">Docs</h2>
{doc_links.rstrip()}        </div>
        <div>
          <h2 class="footer__h">More</h2>
{more_links.rstrip()}        </div>
      </nav>
    </div>
    <div class="container footer__bottom">
      <span>© <span id="year"></span> LocalSight contributors.</span>
      <span>Built for privacy. Runs offline.</span>
    </div>
  </footer>"""


def sidebar_html(current_out: str | None) -> str:
    """Grouped documentation list; the current page is marked aria-current."""
    groups = ""
    for cat in CATEGORIES:
        items = "".join(
            "      <li><a href=\"{out}.html\"{cur}>{title}</a></li>\n".format(
                out=d["out"],
                cur=' aria-current="page"' if d["out"] == current_out else "",
                title=d["title"])
            for d in DOCS if d["cat"] == cat)
        groups += (
            "    <div class=\"docsnav__group\">\n"
            f"      <h2 class=\"docsnav__h\">{cat}</h2>\n"
            "      <ul>\n" + items + "      </ul>\n"
            "    </div>\n")
    return """
    <nav class="docsnav" id="docsnav" aria-label="Documentation">
      <button class="docsnav__toggle" id="docsnavToggle" aria-expanded="false" aria-controls="docsnavBody">
        <span>Documentation</span><span class="chev" aria-hidden="true">▾</span>
      </button>
      <div class="docsnav__body" id="docsnavBody">
""" + groups.rstrip() + """
      </div>
    </nav>"""


def toc_html(toc: list[dict]) -> str:
    """Right-rail outline built from the page's own h2/h3."""
    if not toc:
        return ""
    items = ""
    for entry in toc:
        cls = "toc-h3" if entry["level"] == 3 else ""
        items += ('      <li><a class="{c}" href="#{i}" data-toc="{i}">{l}</a></li>\n'
                  .format(c=cls, i=entry["id"], l=entry["label"]))
    return """
    <nav class="toc" id="toc" aria-label="On this page">
      <h2 class="toc__h">On this page</h2>
      <ul>
""" + items.rstrip() + """
      </ul>
    </nav>"""


# ── Page assembly ─────────────────────────────────────────────────────────
PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} — LocalSight Docs</title>
  <meta name="description" content="{description}" />
  <meta name="theme-color" content="#0b1020" />
  <link rel="icon" href="../assets/img/favicon.svg" type="image/svg+xml" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="../assets/css/style.css" />
  <link rel="stylesheet" href="../assets/css/syntax.css" />
  <link rel="stylesheet" href="../assets/css/docs.css" />
</head>
<body>
  <a class="skip-link" href="#doccontent">Skip to content</a>
{nav}
  <main id="main">
    <div class="docshead">
      <div class="container">
        <p class="crumb">
          <a href="../docs/">Documentation</a>
          <span class="sep">/</span>
          <span>{category}</span>
          <span class="sep">/</span>
          <span>{title}</span>
        </p>
        <h1>{title}</h1>
        <p class="lede">{lede}</p>
        <p class="meta">
          <span class="tag">{reading} min read</span>
          <a class="editlink" href="{edit_url}" target="_blank" rel="noopener">{edit_icon} Edit on GitHub</a>
        </p>
      </div>
    </div>
    <div class="docshell">
      <div class="docgrid">
{sidebar}        <article class="prose" id="doccontent">
{body}
        </article>
{toc}      </div>
    </div>
  </main>
{footer}
  <script src="../assets/js/main.js"></script>
  <script src="../assets/js/docs.js"></script>
</body>
</html>
"""

EDIT_ICON = ('<svg width="13" height="13" viewBox="0 0 24 24" fill="none" '
             'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
             'stroke-linejoin="round" aria-hidden="true">'
             '<path d="M12 20h9M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>')


def reading_minutes(text: str) -> int:
    return max(1, round(len(re.findall(r"\w+", strip_tags(text))) / 220))


def build_page(doc: dict, by_src: dict) -> dict:
    src_abs = os.path.join(by_src["__root__"], doc["src"])
    with open(src_abs, encoding="utf-8") as fh:
        markdown_text = fh.read()

    # Drop the level-1 title: the docshead already renders the page title.
    markdown_text = re.sub(r"^#\s+.*$", "", markdown_text, count=1, flags=re.M)

    body = render_markdown(markdown_text)
    body, toc = postprocess(body)
    body = rewrite_targets(body, doc, by_src)
    body = polish_link_text(body)
    body = fix_fragments(body)

    page = PAGE_TEMPLATE.format(
        title=doc["title"],
        description=doc["blurb"],
        category=doc["cat"],
        lede=doc["blurb"],
        reading=reading_minutes(body),
        edit_url=f"{GITHUB}/blob/main/{doc['src']}",
        edit_icon=EDIT_ICON,
        nav=nav_html(active_docs=True),
        sidebar=sidebar_html(doc["out"]),
        body=body.strip(),
        toc=toc_html(toc),
        footer=footer_html(),
    )
    out_path = os.path.join(OUT_DIR, f"{doc['out']}.html")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(page)

    return {
        "url": f"{doc['out']}.html",
        "title": doc["title"],
        "category": doc["cat"],
        "blurb": doc["blurb"],
        "text": re.sub(r"\s+", " ", strip_tags(body)).strip(),
    }


def build_search_index(entries: list[dict]) -> None:
    index = [{"url": e["url"], "title": e["title"], "category": e["category"],
              "blurb": e["blurb"], "text": e["text"]} for e in entries]
    out_path = os.path.join(OUT_DIR, "search-index.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, separators=(",", ":"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render the LocalSight docs site.")
    ap.add_argument("--src", default=DEFAULT_SRC,
                    help="path to the localsight source repo (default: ../localsight)")
    args = ap.parse_args(argv)

    src_root = os.path.abspath(args.src)
    if not os.path.isdir(src_root):
        print(f"error: source repo not found: {src_root}", file=sys.stderr)
        return 1

    by_src = {"__root__": src_root, **{d["src"]: d for d in DOCS}}
    missing = [d["src"] for d in DOCS
               if not os.path.isfile(os.path.join(src_root, d["src"]))]
    if missing:
        print("error: source docs missing in " + src_root, file=sys.stderr)
        for m in missing:
            print("  - " + m, file=sys.stderr)
        return 1

    os.makedirs(OUT_DIR, exist_ok=True)
    entries = []
    for doc in DOCS:
        entries.append(build_page(doc, by_src))
        print(f"  wrote docs/{doc['out']}.html")
    build_search_index(entries)
    print(f"  wrote docs/search-index.json ({len(entries)} documents)")
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())






