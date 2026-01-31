#!/usr/bin/env python3
"""Validate Orbiteus documentation structure.

Rules enforced:
1. Every numbered chapter `docs/NN-*.md` for NN in 01..33 exists.
2. `docs/README.md`, `docs/pre-prompt.md`, `docs/glossary.md` exist.
3. `docs/adr/README.md`, `docs/adr/_template.md`, and 0001..0017 ADRs exist.
4. Every file referenced by `docs/pre-prompt.md` and `docs/README.md` resolves.
5. Every ADR linked in `docs/adr/README.md` resolves.
6. No `[link](path)` to a missing markdown file inside `docs/`.

Exit code:
- 0 — all checks pass
- 1 — at least one violation
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ADR = DOCS / "adr"

REQUIRED_TOP = [
    DOCS / "README.md",
    DOCS / "pre-prompt.md",
    DOCS / "glossary.md",
]

REQUIRED_NUMBERED = list(range(1, 37))  # 01..36
REQUIRED_ADR_IDS = list(range(1, 18))   # 0001..0017
REQUIRED_ADR_TOP = [
    ADR / "README.md",
    ADR / "_template.md",
]

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")


def find_chapter(num: int) -> Path | None:
    pattern = f"{num:02d}-*.md"
    matches = list(DOCS.glob(pattern))
    return matches[0] if matches else None


def find_adr(num: int) -> Path | None:
    pattern = f"{num:04d}-*.md"
    matches = list(ADR.glob(pattern))
    return matches[0] if matches else None


def collect_links(md_path: Path) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    text = md_path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        for href in LINK_RE.findall(line):
            out.append((href, lineno))
    return out


def is_internal_md_link(href: str) -> bool:
    if href.startswith(("http://", "https://", "mailto:", "#")):
        return False
    return True


def resolve_link(base: Path, href: str) -> Path:
    raw = href.split("#", 1)[0]
    if raw.startswith("/"):
        return ROOT / raw.lstrip("/")
    return (base.parent / raw).resolve()


def main() -> int:
    errors: list[str] = []

    for p in REQUIRED_TOP:
        if not p.exists():
            errors.append(f"missing required doc: {p.relative_to(ROOT)}")

    for num in REQUIRED_NUMBERED:
        path = find_chapter(num)
        if path is None:
            errors.append(f"missing chapter docs/{num:02d}-*.md")

    for p in REQUIRED_ADR_TOP:
        if not p.exists():
            errors.append(f"missing required ADR file: {p.relative_to(ROOT)}")

    for num in REQUIRED_ADR_IDS:
        path = find_adr(num)
        if path is None:
            errors.append(f"missing ADR docs/adr/{num:04d}-*.md")

    md_files: list[Path] = []
    md_files.extend(p for p in DOCS.glob("*.md"))
    if ADR.exists():
        md_files.extend(p for p in ADR.glob("*.md"))

    for md in md_files:
        for href, lineno in collect_links(md):
            if not is_internal_md_link(href):
                continue
            target = resolve_link(md, href)
            if not target.exists():
                errors.append(
                    f"{md.relative_to(ROOT)}:{lineno} broken link → {href}"
                )

    if errors:
        print("Documentation check FAILED:\n", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(f"\n{len(errors)} issue(s).", file=sys.stderr)
        return 1

    print(
        f"Documentation check OK — {len(md_files)} markdown files validated, "
        f"{len(REQUIRED_NUMBERED)} chapters + {len(REQUIRED_ADR_IDS)} ADRs present."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
