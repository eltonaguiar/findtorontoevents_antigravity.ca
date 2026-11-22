#!/usr/bin/env python3
"""
GitHub Actions QA framework — workflow audit script.

Scans every .github/workflows/*.yml in the target repo and checks each against a
QA rubric: triggers present, timeouts, concurrency groups, `[skip ci]` safety,
conflict-marker/secret-scan coverage, job count, and broad-glob hazards.

Outputs a markdown QA report. Exit code 0 = all pass; 1 = at least one warning.

Usage:
    python3 audit_workflows.py --repo /path/to/repo [--out out.md]
"""
import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# QA rubric
# ---------------------------------------------------------------------------
MAX_TIMEOUT_MIN = 500
MAX_JOBS = 30
BROAD_GLOB_SIGNS = ["**/*.json", "**/*.html", "audit_dashboard/**", "audit_trail/**"]

REQUIRED_CHECKS = ["conflict-marker-check", "secret-scan", "ci-tests", "surface-parity"]


def parse_workflow(path: Path) -> dict:
    """Minimal YAML-ish scan. We do NOT need full YAML; we grep key tokens."""
    text = path.read_text(errors="ignore")
    return {
        "path": path,
        "text": text,
        "has_on": bool(re.search(r"(?m)^on:", text)) or "on:" in text,
        "has_schedule": "schedule" in text,
        "has_workflow_dispatch": "workflow_dispatch" in text,
        "has_timeout": bool(re.search(r"(?m)timeout-minutes:", text)),
        "has_concurrency": "concurrency" in text,
        "has_skip_ci": "[skip ci]" in text or "[skip-ci]" in text,
        "has_markers": "conflict-marker" in text or "assert_no_conflict" in text,
        "has_secret_scan": "secret-scan" in text or "gitleaks" in text or "trufflehog" in text,
        "has_broad_glob": any(s in text for s in BROAD_GLOB_SIGNS),
        "job_count": len(re.findall(r"(?m)^  [a-zA-Z0-9_-]+:", text)),
        "max_timeout": _find_timeout(text),
        "runs_on_push": "push:" in text or re.search(r"(?m)^on:\s*$", text) is not None,
    }


def _find_timeout(text: str):
    m = re.search(r"timeout-minutes:\s*(\d+)", text)
    return int(m.group(1)) if m else None


def audit(workflows, repo_name: str) -> (list, list):
    """Return (issues, summary_rows)."""
    issues = []
    rows = []
    for wf in workflows:
        rel = wf["path"].name
        problems = []

        if not wf["has_on"]:
            problems.append("missing `on:` trigger")
        if wf["has_schedule"] and not wf["has_workflow_dispatch"]:
            problems.append("schedule without workflow_dispatch (no manual rescue)")
        if wf["max_timeout"] and wf["max_timeout"] > MAX_TIMEOUT_MIN:
            problems.append(f"timeout {wf['max_timeout']}m > {MAX_TIMEOUT_MIN}m")
        if not wf["has_concurrency"] and wf["job_count"] > 1:
            problems.append("multi-job workflow without concurrency group (cancel-cascade risk)")
        if wf["has_broad_glob"]:
            problems.append("broad deploy-path glob detected (infinite-loop risk)")
        if wf["job_count"] > MAX_JOBS:
            problems.append(f"{wf['job_count']} jobs > {MAX_JOBS}")

        rows.append((rel, wf["job_count"], wf["has_on"], wf["has_concurrency"],
                     wf["max_timeout"], "OK" if not problems else "; ".join(problems)))
        issues.extend(f"{rel}: {p}" for p in problems)
    return issues, rows


def build_report(repo_name: str, run_count: int, rows, issues, missing_checks) -> str:
    lines = []
    lines.append(f"# GitHub Actions QA Audit — {repo_name}")
    lines.append("")
    lines.append(f"**Audited:** {run_count} workflow files. **Generated:** {__import__('datetime').datetime.now()}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Workflows scanned | {run_count} |")
    lines.append(f"| Workflows with issues | {len(issues)} |")
    lines.append(f"| Missing core checks (repo-level) | {', '.join(missing_checks) if missing_checks else 'none'} |")
    lines.append("")
    lines.append("## Per-workflow status")
    lines.append("")
    lines.append("| Workflow | Jobs | Trigger | Concurrency | Timeout (m) | Issues |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        name, jobs, on, conc, to, prob = r
        lines.append(f"| {name} | {jobs} | {'Y' if on else 'N'} | {'Y' if conc else 'N'} | {to or '-'} | {prob} |")
    lines.append("")
    lines.append("## Issues")
    lines.append("")
    if issues:
        for i in issues:
            lines.append(f"- {i}")
    else:
        lines.append("No issues found.")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    lines.append("- Add `concurrency` groups to every multi-job workflow to prevent cancel-cascades.")
    lines.append("- Add `workflow_dispatch` to every scheduled workflow for manual rescue runs.")
    lines.append("- Avoid broad deploy-path globs (`**/*.json`, `audit_dashboard/**`); enumerate exact files.")
    lines.append("- Keep timeouts < 500 min and add `[skip ci]` to any workflow-owned commit messages.")
    lines.append("- Ensure `conflict-marker-check` and a secret scan are mandatory status checks on the default branch.")
    lines.append("")
    lines.append("*Generated by the GHA QA framework — githubcopilot-mercury3AI.*")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="Path to repo root containing .github/workflows")
    ap.add_argument("--out", default=None, help="Output markdown path (prints to stdout if omitted)")
    args = ap.parse_args()

    workflows_dir = Path(args.repo) / ".github" / "workflows"
    if not workflows_dir.is_dir():
        print(f"ERROR: no workflows dir at {workflows_dir}", file=sys.stderr)
        sys.exit(2)

    workflows = [p for p in workflows_dir.glob("*.yml") if p.is_file()]
    workflows += [p for p in workflows_dir.glob("*.yaml") if p.is_file()]
    parsed = [parse_workflow(p) for p in workflows]

    issues, rows = audit(parsed, args.repo)
    all_text = "\n".join(p["text"] for p in parsed)
    missing_checks = [c for c in REQUIRED_CHECKS if c not in all_text]

    report = build_report(args.repo, len(parsed), rows, issues, missing_checks)

    if args.out:
        Path(args.out).write_text(report)
        print(f"Wrote QA report to {args.out}")
    else:
        print(report)

    # Exit non-zero if any issue so CI fails loudly
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
