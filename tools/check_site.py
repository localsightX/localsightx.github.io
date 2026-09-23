#!/usr/bin/env python3
"""check_site.py — verify every internal reference in the static site resolves.

Walks the HTML pages, resolves every relative href/src against the page's own
directory, and reports any target that does not exist on disk. Absolute URLs,
mailto/tel links and same-page fragments are skipped (fragments are validated
separately against the page's heading ids).

Usage:  .venv/bin/python tools/check_site.py
"""

from __future__ import annotations

import glob
import html as html_mod
import html.parser
import os
import posixpath
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES_ROOT = os.path.dirname(HERE)

ATTR_RE = re.compile(r'(?:href|src)="([^"]*)"')
ID_RE = re.compile(r'\bid="([^"]+)"')

# Elements that never have a closing tag (plus SVG children handled below).
VOID = {"meta", "link", "img", "br", "hr", "input", "source", "wbr"}
SVG_SELF = {"path", "circle", "rect", "ellipse", "line", "polyline",
            "polygon", "use", "stop", "feGaussianBlur"}


class BalanceChecker(html.parser.HTMLParser):
    """Reports unbalanced tags, tolerating void and self-closing SVG elements."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.problems: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in VOID or tag in SVG_SELF:
            return
        self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs) -> None:
        return  # self-closing — nothing to balance

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID or tag in SVG_SELF:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
            return
        if tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.problems.append(f"unclosed <{self.stack[-1]}>")
                self.stack.pop()
            self.stack.pop()
        else:
            self.problems.append(f"stray </{tag}>")


def check_wellformed(pages: list[str]) -> int:
    problems = 0
    for rel in pages:
        with open(os.path.join(PAGES_ROOT, rel), encoding="utf-8") as fh:
            doc = fh.read()
        checker = BalanceChecker()
        checker.feed(doc)
        for leftover in checker.stack:
            checker.problems.append(f"unclosed <{leftover}>")
        if checker.problems:
            problems += 1
            print(f"  {rel}: {'; '.join(checker.problems[:6])}"
                  + (" …" if len(checker.problems) > 6 else ""))
    return problems



def main() -> int:
    pages = sorted(
        os.path.relpath(p, PAGES_ROOT)
        for p in glob.glob(os.path.join(PAGES_ROOT, "*.html"))
        + glob.glob(os.path.join(PAGES_ROOT, "docs", "*.html"))
    )

    bad_refs: list[tuple[str, str, str]] = []
    bad_frags: list[tuple[str, str]] = []
    checked = 0

    for rel in pages:
        path = os.path.join(PAGES_ROOT, rel)
        with open(path, encoding="utf-8") as fh:
            doc = fh.read()
        base = posixpath.dirname(rel)
        ids = set(ID_RE.findall(doc))

        for target in {html_mod.unescape(t) for t in ATTR_RE.findall(doc)}:
            if not target or target.startswith(("http://", "https://", "mailto:", "tel:")):
                continue
            frag = ""
            if "#" in target:
                head, frag = target.split("#", 1)
            else:
                head = target
            if head:
                checked += 1
                resolved = posixpath.normpath(posixpath.join(base, head)) if base else head
                if not os.path.exists(os.path.join(PAGES_ROOT, resolved)):
                    bad_refs.append((rel, target, resolved))
                elif frag and frag not in ids:
                    # A fragment pointing at an id in *another* page is fine.
                    if not os.path.exists(os.path.join(PAGES_ROOT, resolved)):
                        bad_frags.append((rel, target))
            elif frag and frag not in ids:
                bad_frags.append((rel, target))

    print(f"checked {checked} relative references across {len(pages)} pages")
    if bad_refs:
        print(f"\nBROKEN REFERENCES ({len(bad_refs)}):")
        for rel, target, resolved in bad_refs:
            print(f"  {rel}: {target}  ->  {resolved}")
    if bad_frags:
        print(f"\nMISSING ANCHORS ({len(bad_frags)}):")
        for rel, target in bad_frags:
            print(f"  {rel}: {target}")

    print("\nHTML well-formedness:")
    malformed = check_wellformed(pages)
    if not malformed:
        print(f"  OK — all {len(pages)} pages balanced.")

    if bad_refs or bad_frags or malformed:
        return 1
    print("\nOK — every internal reference resolves and all pages are balanced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
