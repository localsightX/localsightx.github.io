#!/usr/bin/env python3
"""browser_check.py — render the docs in a real browser and report problems.

Loads each page, collects console errors / page errors, and screenshots a few
key views so the result can be eyeballed. Requires Playwright + a browser.

Usage (from the pages repo, with a Playwright-enabled interpreter):

    python tools/browser_check.py            # serve-less: uses file:// URLs
    python tools/browser_check.py --port 8765
"""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES_ROOT = os.path.dirname(HERE)

PAGES = [
    ("index.html", "landing"),
    ("docs/index.html", "docs-hub"),
    ("docs/installation.html", "docs-installation"),
    ("docs/user-guide.html", "docs-user-guide"),
    ("docs/troubleshooting.html", "docs-troubleshooting"),
    ("docs/api-reference.html", "docs-api"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0,
                    help="if set, load pages from http://localhost:<port>")
    ap.add_argument("--outdir", default=os.path.join(PAGES_ROOT, "..", "site_shots"))
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    base = f"http://localhost:{args.port}/" if args.port else None
    os.makedirs(args.outdir, exist_ok=True)

    failures = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        for rel, name in PAGES:
            url = base + rel if base else "file://" + os.path.join(PAGES_ROOT, rel)
            errors: list[str] = []
            page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
                    if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.goto(url, wait_until="networkidle", timeout=15000)
            # Trigger lazy behaviour: focus search, scroll, open a details.
            if name == "docs-hub":
                page.fill("#docSearch", "retention")
                page.wait_for_timeout(600)
                page.screenshot(path=os.path.join(args.outdir, f"{name}-search.png"))
            page.screenshot(path=os.path.join(args.outdir, f"{name}.png"), full_page=False)
            title = page.title()
            status = "OK" if not errors else "ERRORS"
            if errors:
                failures += 1
            print(f"  [{status}] {rel}  ({title})")
            for e in errors[:4]:
                print(f"        - {e}")
        browser.close()

    print(f"\nscreenshots written to {args.outdir}")
    return 1 if failures else 0



if __name__ == "__main__":
    raise SystemExit(main())
