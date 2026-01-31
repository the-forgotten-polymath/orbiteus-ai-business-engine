"""Repo-wide documentation tests.

These run without any database, network, or backend dependencies. They wrap
`scripts/check_docs.py` and add a few extra structural assertions to keep the
documentation in sync with the engine's hard rules.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ADR = DOCS / "adr"
SCRIPT = ROOT / "scripts" / "check_docs.py"


def _load_check_docs():
    spec = importlib.util.spec_from_file_location("orbiteus_check_docs", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_docs_script_is_runnable():
    """The validator must be invokable via python and exit 0."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, cwd=ROOT
    )
    assert result.returncode == 0, (
        f"check_docs.py failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_check_docs_module_main_returns_zero():
    """Calling main() programmatically also returns 0."""
    mod = _load_check_docs()
    assert mod.main() == 0


def test_pre_prompt_exists_and_is_english():
    """pre-prompt.md must exist and contain English-only critical phrases."""
    text = (DOCS / "pre-prompt.md").read_text(encoding="utf-8")
    assert text.strip(), "pre-prompt.md is empty"
    must_contain = [
        "READ FIRST",
        "Identity",
        "Hard rules",
        "Authoritative tech stack",
        "Module convention",
        "Layering rules",
        "AI integration rules",
        "What to do when the user asks for X",
        "What you must never do",
        "Document map",
    ]
    for needle in must_contain:
        assert needle in text, f"pre-prompt.md missing section: {needle!r}"


def test_pre_prompt_lists_every_chapter():
    """Doc map in pre-prompt must reference every numbered chapter."""
    pre = (DOCS / "pre-prompt.md").read_text(encoding="utf-8")
    for path in DOCS.glob("[0-3][0-9]-*.md"):
        rel = f"docs/{path.name}"
        assert rel in pre, f"pre-prompt.md missing reference to {rel}"


def test_readme_lists_every_chapter():
    """docs/README.md must link every numbered chapter."""
    readme = (DOCS / "README.md").read_text(encoding="utf-8")
    for path in DOCS.glob("[0-3][0-9]-*.md"):
        assert path.name in readme, f"docs/README.md missing link to {path.name}"


def test_adr_index_lists_all_adrs():
    """ADR index must enumerate every adr/0NNN-*.md present on disk."""
    index = (ADR / "README.md").read_text(encoding="utf-8")
    for path in sorted(ADR.glob("0[0-9][0-9][0-9]-*.md")):
        assert path.name in index, f"adr/README.md missing entry for {path.name}"


def test_adr_files_have_status_header():
    """Every ADR must declare Status (and not be the bare template)."""
    for path in sorted(ADR.glob("0[0-9][0-9][0-9]-*.md")):
        text = path.read_text(encoding="utf-8")
        assert re.search(r"^- \*\*Status:\*\*", text, flags=re.MULTILINE), (
            f"{path.name} has no Status line"
        )
        assert "Proposed | Accepted | Superseded" not in text, (
            f"{path.name} still contains the template's Status placeholder"
        )


def test_no_old_documents_remain():
    """Old top-level docs should be removed once content has migrated."""
    forbidden = ["ARCHITECTURE.md", "TreeSpec-Backend.md", "TreeSpec-Frontend.md"]
    for name in forbidden:
        assert not (DOCS / name).exists(), f"docs/{name} should be removed"


def test_pre_prompt_mentions_vendor_neutrality():
    """Vendor-neutrality rule must remain visible to AI agents."""
    text = (DOCS / "pre-prompt.md").read_text(encoding="utf-8")
    assert "Vendor neutrality" in text, "pre-prompt.md must mention vendor neutrality"
    assert "AGENTS.md" in text, "pre-prompt.md must point to AGENTS.md"


def test_agents_md_points_to_pre_prompt():
    """AGENTS.md must direct agents to docs/pre-prompt.md before anything else."""
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "docs/pre-prompt.md" in text


def test_glossary_defines_engine():
    """Key terms must be defined in the glossary."""
    text = (DOCS / "glossary.md").read_text(encoding="utf-8")
    for term in ["Engine", "Tenant", "RequestContext", "BaseRepository", "BYOK", "Outbox", "ADR"]:
        assert f"**{term}**" in text, f"glossary missing definition for {term!r}"


def test_no_competing_vendor_strings_in_docs():
    """Sanity check: no leaked competitor mentions in tracked docs."""
    pattern = re.compile(r"openmercato|open\s*mercato", re.IGNORECASE)
    offenders: list[str] = []
    for path in [*DOCS.rglob("*.md"), ROOT / "AGENTS.md"]:
        text = path.read_text(encoding="utf-8")
        if pattern.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"Vendor name leaked into: {offenders}"
