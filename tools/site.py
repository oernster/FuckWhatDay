"""Generate the GitHub Pages site from one layout and a fragment per page.

Run as part of ``python -m tools.build``. Each page in ``PAGES`` is
``site/layout.html`` with its own fragment from ``site/pages`` dropped in,
so the header, navigation, footer and page order exist exactly once.
``tests/test_site.py`` fails if a committed page under ``docs/`` differs
from what this produces.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "site"
LAYOUT = SOURCE / "layout.html"
FRAGMENTS = SOURCE / "pages"
OUTPUT = ROOT / "docs"

PROGRAM_SCRIPTS = '<script src="bf.js"></script>\n<script src="site.js"></script>'


@dataclass(frozen=True, slots=True)
class Page:
    file: str
    label: str
    title: str
    description: str
    runs_program: bool = False


PAGES = (
    Page(
        "index.html",
        "Home",
        "FuckWhatDay: enterprise weekday resolution, in Brainfuck",
        "A Gregorian day of week calculator written in Brainfuck. No part of the "
        "calculation is delegated to a sensible programming language.",
    ),
    Page(
        "demo.html",
        "Demo",
        "Live demo | FuckWhatDay",
        "Run the real FuckWhatDay Brainfuck program in your browser.",
        runs_program=True,
    ),
    Page(
        "features.html",
        "Features",
        "Features | FuckWhatDay",
        "Eight instructions, seven weekdays and a great deal of validation.",
        runs_program=True,
    ),
    Page(
        "engineering.html",
        "Engineering",
        "Engineering | FuckWhatDay",
        "Benchmarks nobody asked for and how the thing actually works.",
    ),
    Page(
        "pricing.html",
        "Pricing",
        "Pricing | FuckWhatDay",
        "Transparent, predictable and in two of three cases identical.",
    ),
    Page(
        "faq.html",
        "FAQ",
        "FAQ | FuckWhatDay",
        "Frequently avoided questions about FuckWhatDay.",
    ),
)


def _nav(current: Page) -> str:
    links = []
    for page in PAGES[1:]:
        marker = ' aria-current="page"' if page is current else ""
        links.append(f'<a href="{page.file}"{marker}>{page.label}</a>')
    return "\n      ".join(links)


def _pager(current: Page) -> str:
    index = PAGES.index(current)
    parts = []
    if index > 0:
        before = PAGES[index - 1]
        parts.append(
            f'<a class="pager-prev" href="{before.file}">&larr; {before.label}</a>'
        )
    if index < len(PAGES) - 1:
        after = PAGES[index + 1]
        parts.append(
            f'<a class="pager-next" href="{after.file}">{after.label} &rarr;</a>'
        )
    return "\n    ".join(parts)


def render(page: Page) -> str:
    """Return the complete HTML for ``page``."""
    layout = Template(LAYOUT.read_text(encoding="utf-8"))
    return layout.substitute(
        title=page.title,
        description=page.description,
        nav=_nav(page),
        content=(FRAGMENTS / page.file).read_text(encoding="utf-8").rstrip("\n"),
        pager=_pager(page),
        scripts=PROGRAM_SCRIPTS if page.runs_program else "",
    )


def main() -> int:
    OUTPUT.mkdir(exist_ok=True)
    for page in PAGES:
        path = OUTPUT / page.file
        path.write_text(render(page), encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
