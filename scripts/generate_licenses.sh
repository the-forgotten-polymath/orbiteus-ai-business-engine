#!/bin/sh
# Third-party license inventory (DoD §16.4 + §1.7).
#
# Generates two JSON manifests at the repo root:
#
#   THIRD_PARTY_LICENSES.python.json   — pip-licenses
#   THIRD_PARTY_LICENSES.node.json     — license-checker (admin-ui +
#                                       portal-ui workspaces)
#
# Then greps both for GPL/AGPL/LGPL families. Exits non-zero on any
# match — that's the no-GPL gate the CI workflow consumes.
#
# Run from the repo root:
#
#   sh scripts/generate_licenses.sh
#
# Designed to be safe to commit the resulting JSONs — they contain
# only public package metadata (name + version + license + URL),
# no source.
set -eu

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$ROOT"

echo "[licenses] generating Python license manifest"
if ! command -v pip-licenses >/dev/null 2>&1; then
  echo "[licenses] installing pip-licenses (transient)"
  pip install --quiet pip-licenses
fi
pip-licenses --format=json --with-urls --with-system \
  > THIRD_PARTY_LICENSES.python.json

echo "[licenses] generating Node license manifest"
# `license-checker` is invoked via npx — no global install required.
# `--excludePrivatePackages` skips our own workspace packages.
npx --yes license-checker --json --excludePrivatePackages \
  > THIRD_PARTY_LICENSES.node.json

echo "[licenses] auditing manifests for copyleft licenses"
# Python and Node manifests have different shapes, so we delegate to
# Python (always available — we just used it to install pip-licenses)
# instead of fighting `jq` availability.
python3 - <<'PY'
import json
import re
import sys

# Allow-list of packages that ship under a copyleft (GPL family)
# license but are still safe to redistribute alongside Apache 2.0 /
# MIT code, either because they link DYNAMICALLY (LGPL) or because
# they offer a permissive license alongside the GPL one (multi-
# license). Each entry is a literal package-name prefix (no version).
#
# Audit each addition with care — the test below is the no-GPL gate.
DYNAMIC_LINK_ALLOWLIST = (
    # JS — libvips bound by sharp via dynamic linkage (LGPL-3.0).
    "@img/sharp-libvips",
    # Python — psycopg2 / psycopg2-binary, LGPL with dynamic linkage
    # against the application code (we use it via SQLAlchemy + the
    # binary wheel).
    "psycopg2",
    "psycopg2-binary",
    # Python — num2words, LGPL helper for spelling out numbers
    # (currently transitive via Babel / docutils — no static
    # linkage, no PII surface).
    "num2words",
    # Python — docutils ships under a multi-license (BSD + GPL +
    # PSF + Public Domain) so the consumer picks BSD. Listed
    # explicitly so the audit script doesn't trip on the GPL token
    # in the joined license string.
    "docutils",
)

# `pip-licenses --format=json` emits a list of dicts with a "License"
# key. `license-checker --json` emits a dict keyed by
# "<name>@<version>" with a "licenses" field (string or list).
#
# A "GPL family" hit is any of:  GPL, AGPL, LGPL  (case-sensitive).
COPYLEFT = re.compile(r"\b(GPL|AGPL|LGPL)\b")


def is_allowed(pkg_name: str) -> bool:
    return any(pkg_name.startswith(prefix) for prefix in DYNAMIC_LINK_ALLOWLIST)


def license_str(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value or "")


def audit_python(path: str) -> list[str]:
    with open(path) as f:
        rows = json.load(f)
    bad = []
    for row in rows:
        name = row.get("Name", "<unknown>")
        lic = license_str(row.get("License"))
        if COPYLEFT.search(lic) and not is_allowed(name):
            bad.append(f"{name} → {lic}")
    return bad


def audit_node(path: str) -> list[str]:
    with open(path) as f:
        rows = json.load(f)
    bad = []
    for spec, row in rows.items():
        # Drop the trailing "@<version>".
        name = spec.rsplit("@", 1)[0] if "@" in spec[1:] else spec
        lic = license_str(row.get("licenses"))
        if COPYLEFT.search(lic) and not is_allowed(name):
            bad.append(f"{spec} → {lic}")
    return bad


offenders = []
offenders += audit_python("THIRD_PARTY_LICENSES.python.json")
offenders += audit_node("THIRD_PARTY_LICENSES.node.json")

if offenders:
    print("FAIL: copyleft (GPL/AGPL/LGPL) licenses outside the dynamic-link allow-list:")
    for line in offenders:
        print(f"  - {line}")
    sys.exit(1)

print("OK: no copyleft license outside the dynamic-link allow-list")
print("    (allow-list:", ", ".join(DYNAMIC_LINK_ALLOWLIST), ")")
PY
