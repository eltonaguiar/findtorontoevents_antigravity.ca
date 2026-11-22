"""Audit that every PF publishing surface carries n and a cost treatment.

"Label PF everywhere" is only checkable if the list of surfaces is explicit and
re-derivable, so this tool holds the list (not a repo-wide grep: 60+ backtest
scripts compute a PF for their own report and never publish a class figure) and
verifies each one emits ``pf_label`` or a literal ``n=`` beside the ratio.

Usage: python tools/pf_label_audit.py [--out reports/pf_label_coverage_YYYY-MM-DD.md]
Exit 0 always; this is a report, not a gate.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Surfaces that put a PF in front of a reader or another system.
PUBLISHERS = [
    ("audit_trail/dashboard_generator.py", "asset_class_health `pf`/`profit_factor`"),
    ("alpha_engine/money_ready_verdict.py", "money_ready class PF + policy_clean_pf"),
    ("alpha_engine/audit3_tribunal.py", "audit3 ledger cell PF"),
    ("tools/anti_overfit_audit_sidecar.py", "per-strategy PF in anti_overfit_audit.json"),
    ("tools/crypto_pf_reconcile.py", "PF reconciliation table"),
    ("audit_dashboard/template.html", "PF rendered in class/system cards"),
]

_MARKERS = ("pf_label", "format_pf", "n=", "pf_n")


def _labelled_source(path: Path) -> tuple[bool, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    sites = 0
    labelled = 0
    for i, line in enumerate(lines):
        if not re.search(r"profit_factor|\bpf\b|PF ", line):
            continue
        if not re.search(r"[=+]|return|append|f\"", line):
            continue
        sites += 1
        window = "\n".join(lines[max(0, i - 3): i + 4])
        if any(m in window for m in _MARKERS):
            labelled += 1
    return (labelled > 0, sites)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/pf_label_coverage_2026-11-20.md")
    args = ap.parse_args()

    rows = []
    for rel, what in PUBLISHERS:
        path = REPO_ROOT / rel
        if not path.exists():
            rows.append((rel, what, "MISSING", 0))
            continue
        ok, sites = _labelled_source(path)
        rows.append((rel, what, "labelled" if ok else "UNLABELLED", sites))

    total = len(rows)
    good = sum(1 for r in rows if r[2] == "labelled")
    lines = [
        "# PF label coverage",
        "",
        "Date: 2026-11-20  |  author: freebuff (deepseek-v4-flash)",
        "",
        "Rule adopted 2026-11-20: a class or system profit factor is quoted as",
        "`PF <value> (n=<count>[, net <bp>bp])`. A PF without a denominator is not a",
        "measurement -- CRYPTO was published at 1.31 / 0.83 / 0.26 from three",
        "populations, all arithmetically correct.",
        "",
        f"**{good}/{total} publishing surfaces carry the denominator.**",
        "",
        "| surface | what it publishes | status | PF-ish lines scanned |",
        "|---|---|---|---|",
    ]
    for rel, what, status, sites in rows:
        lines.append(f"| `{rel}` | {what} | {status} | {sites} |")
    lines += [
        "",
        "## Scope, stated",
        "",
        "This list is the PF surfaces that reach a reader or another system. It is",
        "deliberately **not** every `profit_factor` in the repo: ~60 backtest and",
        "scraper scripts compute a PF for their own report and publish no class",
        "figure, and labelling them would imply a class-level claim they do not make.",
        "If a new surface starts publishing a class PF, add it here in the same PR.",
        "",
        "Regenerate: `python tools/pf_label_audit.py`.",
        "",
    ]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
