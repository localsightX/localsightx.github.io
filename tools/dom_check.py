#!/usr/bin/env python3
"""dom_check.py — assert the docs pages are structured and behave correctly.

Objective layout checks that do not need eyeballing: element counts, active
navigation states, search behaviour, code-copy wiring and the mobile sidebar.

Usage:  python tools/dom_check.py --port 8765      (or file:// if --port omitted)
"""

from __future__ import annotations

import argparse
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES_ROOT = os.path.dirname(HERE)


def check(page, label: str, fn) -> bool:
    try:
        fn(page)
        print(f"  PASS  {label}")
        return True
    except AssertionError as e:
        print(f"  FAIL  {label}: {e}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    base = f"http://localhost:{args.port}/" if args.port else "file://" + PAGES_ROOT + "/"
    results: list[bool] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ── Landing page ────────────────────────────────────────────────────
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(base + "index.html", wait_until="networkidle")

        def landing(page):
            nav = page.eval_on_selector_all(
                ".nav__links a",
                "els => els.map(e => [e.textContent.trim(), e.getAttribute('href')])")
            assert any(t == "Documentation" and h == "docs/" for t, h in nav), \
                f"no Documentation nav link: {nav}"
            assert len(page.query_selector_all("#docs .dcard")) == 4, "docs band cards"
            foot = page.eval_on_selector_all(
                ".footer a", "els => els.map(e => e.getAttribute('href'))")
            assert any(h == "docs/troubleshooting.html" for h in foot), "footer docs link"
        results.append(check(page, "landing: nav link + docs band + footer", landing))

        # ── Docs hub ────────────────────────────────────────────────────────
        page.goto(base + "docs/index.html", wait_until="networkidle")

        def hub(page):
            assert len(page.query_selector_all(".dcard")) == 14, \
                f"hub card count {len(page.query_selector_all('.dcard'))}"
        results.append(check(page, "hub: 14 doc cards", hub))

        def search_works(page):
            page.fill("#docSearch", "retention")
            page.wait_for_timeout(700)
            n = len(page.query_selector_all(".sresult"))
            assert n >= 1, "search 'retention' returned no results"
            status = page.inner_text("#docSearchStatus")
            assert "match" in status, f"search status: {status!r}"
            page.fill("#docSearch", "zzzzqq")
            page.wait_for_timeout(700)
            assert page.query_selector(".searchempty") is not None, \
                "no empty-state shown for a nonsense query"
        results.append(check(page, "hub: search results + empty state", search_works))

        # ── A generated doc page ────────────────────────────────────────────
        page.goto(base + "docs/installation.html", wait_until="networkidle")

        def docpage(page):
            nav_links = page.query_selector_all(".docsnav a")
            assert len(nav_links) == 14, f"sidebar links {len(nav_links)}"
            current = page.query_selector('.docsnav a[aria-current="page"]')
            assert current is not None and current.get_attribute("href") == "installation.html", \
                "sidebar active link"
            assert page.query_selector(".toc li") is not None, "page outline missing"
            crumb = page.inner_text(".crumb")
            assert "Getting started" in crumb and "Installation & Setup" in crumb, crumb
            hl = len(page.query_selector_all(".prose .highlight"))
            cb = len(page.query_selector_all(".prose .copybtn"))
            assert hl == cb > 0, f"code blocks {hl} vs copy buttons {cb}"
            tw = len(page.query_selector_all(".tablewrap"))
            tb = len(page.query_selector_all(".prose table"))
            assert tw == tb, f"wrapped tables {tw} vs tables {tb}"
        results.append(check(page, "doc page: sidebar/outline/breadcrumb/code/tables", docpage))

        # ── Cross-page navigation actually works ────────────────────────────
        def navclick(page):
            page.click('.docsnav a[href="troubleshooting.html"]')
            page.wait_for_load_state("networkidle")
            assert page.title().startswith("Troubleshooting"), page.title()
            cur = page.query_selector('.docsnav a[aria-current="page"]')
            assert cur.get_attribute("href") == "troubleshooting.html", "active state moved"
        results.append(check(page, "doc page: sidebar navigation switches pages", navclick))

        # ── Mobile: sidebar collapsed behind its toggle ────────────────────
        mobile = browser.new_page(viewport={"width": 420, "height": 900})
        mobile.goto(base + "docs/installation.html", wait_until="networkidle")

        def mobilenav(mobile):
            assert mobile.is_hidden("#docsnavBody"), "nav body should start hidden on mobile"
            assert mobile.is_visible("#docsnavToggle"), "toggle should be visible on mobile"
            mobile.click("#docsnavToggle")
            mobile.wait_for_timeout(200)
            assert mobile.is_visible("#docsnavBody"), "toggle did not reveal the sidebar"
            # Choosing a page collapses it again.
            mobile.click('.docsnav a[href="runbook.html"]')
            mobile.wait_for_timeout(300)
            assert mobile.is_hidden("#docsnavBody"), "nav did not collapse after navigation"
        results.append(check(mobile, "mobile: sidebar toggle", mobilenav))

        browser.close()

    print()
    if all(results):
        print(f"ALL {len(results)} CHECKS PASSED")
        return 0
    print(f"{results.count(False)}/{len(results)} CHECKS FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
