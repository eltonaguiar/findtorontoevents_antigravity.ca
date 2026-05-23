#!/usr/bin/env python3
"""Curated GitHub Actions log reviewer using real logs + swarm_v2 LLM curation.

What it does:
1. Enumerates unique workflows from recent runs.
2. Pulls recent runs for each workflow.
3. Pulls job-level logs and extracts error/warning signal lines.
4. Produces a curated markdown report (deterministic or LLM-enhanced).

Optional:
- Can fetch a remote .env from FTP (using FTP_* env vars) to hydrate AI keys.
- Uses tools/swarm_v2/swarms/core/llm_client.py if available.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from ftplib import FTP_TLS
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable


DEFAULT_REPO = "eltonaguiar/findtorontoevents_antigravity.ca"

ERROR_RE = re.compile(
    r"(" 
    r"\b(error|fatal|traceback|exception|failed|failure|panic)\b|"
    r"\[error\]|"
    r"##\[error\]|"
    r"process completed with exit code|"
    r"timed?\s+out|"
    r"exceeded\s+\d+s\s+timeout"
    r")",
    re.IGNORECASE,
)

WARN_RE = re.compile(
    r"("
    r"\bwarn(ing)?\b|"
    r"##\[warning\]|"
    r"deprecated|"
    r"retrying|"
    r"non[- ]critical"
    r")",
    re.IGNORECASE,
)

NOISE_RE = re.compile(
    r"(^\s*$|^\[command\]|^Post job cleanup\.|^Run\s+|^shell:\s|^env:\s|hint:\s+to\s+use\s+in\s+all\s+of\s+your\s+new\s+repositories)",
    re.IGNORECASE,
)

TIME_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\s*")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


@dataclass
class JobFinding:
    workflow: str
    run_id: int
    run_url: str
    run_conclusion: str
    job_id: int
    job_name: str
    job_url: str
    job_conclusion: str
    errors: list[str]
    warnings: list[str]


def run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def gh_json(args: list[str]) -> Any:
    proc = run_gh(args)
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "gh command failed").strip()
        raise RuntimeError(msg)
    out = (proc.stdout or "").strip()
    if not out:
        return []
    return json.loads(out)


def parse_repo_from_git() -> str:
    try:
        proc = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode != 0:
            return DEFAULT_REPO
        raw = proc.stdout.strip()
        m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", raw)
        return m.group(1) if m else DEFAULT_REPO
    except Exception:
        return DEFAULT_REPO


def load_env_file(path: Path) -> int:
    if not path.exists():
        return 0
    loaded = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and not os.environ.get(key):
            os.environ[key] = value
            loaded += 1
    return loaded


def fetch_remote_env_via_ftp(candidates: Iterable[str]) -> tuple[int, str | None]:
    host = (os.environ.get("FTP_SERVER") or os.environ.get("FTP_HOST") or "").strip()
    user = (os.environ.get("FTP_USER") or "").strip()
    pwd = (os.environ.get("FTP_PASS") or "").strip()
    if not (host and user and pwd):
        return (0, None)

    tls = FTP_TLS()
    tls.connect(host, 21, timeout=30)
    tls.login(user=user, passwd=pwd)
    tls.prot_p()
    loaded = 0
    used_path = None
    try:
        for remote_path in candidates:
            bio = BytesIO()
            try:
                tls.retrbinary(f"RETR {remote_path}", bio.write)
            except Exception:
                continue

            text = bio.getvalue().decode("utf-8", errors="replace")
            for raw in text.splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and not os.environ.get(key):
                    os.environ[key] = value
                    loaded += 1
            used_path = remote_path
            break
    finally:
        try:
            tls.quit()
        except Exception:
            pass
    return (loaded, used_path)


def discover_workflows(repo: str, branch: str, since_days: int, list_limit: int) -> list[str]:
    runs = gh_json(
        [
            "run",
            "list",
            "--repo",
            repo,
            "--branch",
            branch,
            "--limit",
            str(list_limit),
            "--json",
            "workflowName,createdAt",
        ]
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    seen: OrderedDict[str, None] = OrderedDict()
    for run in runs:
        wf = (run.get("workflowName") or "").strip()
        created = run.get("createdAt") or ""
        if not wf:
            continue
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except Exception:
            continue
        if dt >= cutoff and wf not in seen:
            seen[wf] = None
    return list(seen.keys())


def list_runs_for_workflow(repo: str, branch: str, workflow: str, limit: int) -> list[dict[str, Any]]:
    proc = run_gh(
        [
            "run",
            "list",
            "--repo",
            repo,
            "--branch",
            branch,
            "-w",
            workflow,
            "--limit",
            str(limit),
            "--json",
            "databaseId,workflowName,status,conclusion,createdAt,url",
        ]
    )
    if proc.returncode != 0:
        return []
    txt = (proc.stdout or "").strip()
    return json.loads(txt) if txt else []


def list_jobs_for_run(repo: str, run_id: int) -> list[dict[str, Any]]:
    page = 1
    out: list[dict[str, Any]] = []
    while True:
        payload = gh_json(
            [
                "api",
                f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100&page={page}",
            ]
        )
        items = payload.get("jobs") or []
        out.extend(items)
        if len(items) < 100:
            break
        page += 1
    return out


def fetch_job_log(repo: str, run_id: int, job_id: int) -> str:
    proc = run_gh(["run", "view", str(run_id), "--repo", repo, "--job", str(job_id), "--log"])
    return ((proc.stdout or "") + (proc.stderr or "")).strip()


def normalize_line(line: str) -> str:
    s = TIME_PREFIX_RE.sub("", line.strip())
    s = ANSI_RE.sub("", s)
    s = re.sub(r"\s+", " ", s)
    if len(s) > 500:
        return s[:500] + "..."
    return s


def extract_signals(text: str, max_errors: int = 12, max_warnings: int = 8) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    for raw in text.splitlines():
        if NOISE_RE.search(raw):
            continue
        line = normalize_line(raw)
        if not line:
            continue
        if " PASSED [" in line:
            continue
        if " echo \"::error::" in line or " echo \"::warning::" in line:
            # Command echo noise (not the actual annotation event).
            continue
        if " net:timeout " in line:
            continue
        if " # 2026-04-12: abort on command failure" in line:
            continue
        if " # failure dumped competition-*.json" in line:
            continue
        if " = urllib.request.urlopen(" in line:
            continue
        if line.endswith("except Exception as e:"):
            continue
        if ERROR_RE.search(line):
            errs.append(line)
        elif WARN_RE.search(line):
            warns.append(line)

    # Dedup while preserving order
    errs = list(OrderedDict((e, None) for e in errs).keys())[:max_errors]
    warns = list(OrderedDict((w, None) for w in warns).keys())[:max_warnings]
    return errs, warns


def severity_score(f: JobFinding) -> int:
    penalty = 0
    if (f.job_conclusion or "").lower() in {"failure", "timed_out"}:
        penalty += 5
    elif (f.job_conclusion or "").lower() == "cancelled":
        penalty += 2
    return len(f.errors) * 3 + len(f.warnings) + penalty


def curate_with_swarm_v2(findings: list[JobFinding], max_items: int = 25) -> str | None:
    swarm_root = Path(__file__).resolve().parent / "swarm_v2"
    if not swarm_root.exists():
        return None

    if str(swarm_root) not in sys.path:
        sys.path.insert(0, str(swarm_root))

    try:
        from swarms.core.llm_client import LLMClient
    except Exception:
        return None

    client = LLMClient()
    if not client.available:
        return None

    top = sorted(findings, key=severity_score, reverse=True)[:max_items]
    payload = []
    for f in top:
        payload.append(
            {
                "workflow": f.workflow,
                "run_id": f.run_id,
                "run_url": f.run_url,
                "job_name": f.job_name,
                "job_url": f.job_url,
                "job_conclusion": f.job_conclusion,
                "errors": f.errors,
                "warnings": f.warnings,
            }
        )

    prompt = (
        "You are curating GitHub Actions job log findings for engineering triage. "
        "Return concise markdown with exactly these sections: "
        "1) Top Failing Jobs (ordered), 2) Repeated Error Themes, 3) High-Noise Warnings to Deprioritize, "
        "4) Quick Fix Queue (max 10 bullets).\n\n"
        "Each top job line must include workflow, job, and run URL. "
        "Do not invent errors; only use provided lines.\n\n"
        f"FINDINGS_JSON:\n{json.dumps(payload, ensure_ascii=True)}"
    )
    return client.complete(prompt, max_tokens=1800, temperature=0.1)


def build_report(
    repo: str,
    branch: str,
    workflows: list[str],
    findings: list[JobFinding],
    curated: str | None,
    ftp_env_loaded: int,
    ftp_env_path: str | None,
    local_env_loaded: int,
    strict: bool = False,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    top = sorted(findings, key=severity_score, reverse=True)

    lines: list[str] = []
    lines.append("# GitHub Actions Curated Job Log Review")
    if strict:
        lines.append("")
        lines.append("**Mode: STRICT** — only failed/cancelled/timed_out jobs reported.")
    lines.append("")
    lines.append(f"Generated: {now}")
    lines.append(f"Repository: {repo}")
    lines.append(f"Branch: {branch}")
    lines.append(f"Workflows reviewed: {len(workflows)}")
    mode_tag = " (STRICT mode)" if strict else ""
    lines.append(f"Jobs with signals: {len(findings)}{mode_tag}")
    if local_env_loaded:
        lines.append(f"Local .env vars loaded into process: {local_env_loaded}")
    if ftp_env_path:
        lines.append(f"FTP .env source used: {ftp_env_path} (vars loaded: {ftp_env_loaded})")
    lines.append("")

    if curated:
        lines.append("## Curated Analysis (swarm_v2)")
        lines.append("")
        lines.append(curated.strip())
        lines.append("")

    lines.append("## Top Job Findings")
    lines.append("")
    lines.append("| Rank | Workflow | Job | Conclusion | Error lines | Warning lines | Run | Job |")
    lines.append("|---:|---|---|---|---:|---:|---|---|")
    for idx, f in enumerate(top[:30], start=1):
        lines.append(
            "| "
            + f"{idx} | {f.workflow} | {f.job_name} | {f.job_conclusion or '-'} | "
            + f"{len(f.errors)} | {len(f.warnings)} | [run {f.run_id}]({f.run_url}) | [job {f.job_id}]({f.job_url}) |"
        )
    lines.append("")

    lines.append("## Error And Warning Excerpts")
    lines.append("")
    for f in top[:25]:
        lines.append(f"### {f.workflow} :: {f.job_name} :: run {f.run_id}")
        lines.append("")
        if f.errors:
            lines.append("Errors:")
            for e in f.errors:
                lines.append(f"- {e}")
        if f.warnings:
            lines.append("Warnings:")
            for w in f.warnings:
                lines.append(f"- {w}")
        if not f.errors and not f.warnings:
            lines.append("- No extracted signals")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Curated GitHub Actions run/job log reviewer.")
    parser.add_argument("--repo", default="", help="owner/repo (default: derived from git remote)")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--since-days", type=int, default=7)
    parser.add_argument("--list-limit", type=int, default=300)
    parser.add_argument("--max-workflows", type=int, default=40)
    parser.add_argument("--runs-per-workflow", type=int, default=3)
    parser.add_argument("--out", type=Path, default=Path("docs/GHA_SWARM_CURATED_REVIEW.md"))
    parser.add_argument(
        "--ftp-env-path",
        action="append",
        default=[],
        help="Remote FTP path to .env (repeatable). If omitted, defaults are tried.",
    )
    parser.add_argument("--skip-ftp-env", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Only report failed/cancelled/timed_out jobs (drops successful jobs with warnings)")
    args = parser.parse_args()

    repo = args.repo or parse_repo_from_git()

    local_env_loaded = load_env_file(Path(".env"))

    ftp_loaded = 0
    ftp_path = None
    if not args.skip_ftp_env:
        candidates = args.ftp_env_path or [
            ".env",
            "findtorontoevents.ca/.env",
            "tdotevent.ca/.env",
            "public_html/.env",
        ]
        try:
            ftp_loaded, ftp_path = fetch_remote_env_via_ftp(candidates)
        except Exception:
            ftp_loaded, ftp_path = (0, None)

    workflows = discover_workflows(repo, args.branch, args.since_days, args.list_limit)
    workflows = workflows[: args.max_workflows]

    findings: list[JobFinding] = []

    for workflow in workflows:
        runs = list_runs_for_workflow(repo, args.branch, workflow, args.runs_per_workflow)
        for run in runs:
            run_id = int(run.get("databaseId") or 0)
            if not run_id:
                continue
            run_url = run.get("url") or f"https://github.com/{repo}/actions/runs/{run_id}"
            run_conclusion = run.get("conclusion") or ""
            try:
                jobs = list_jobs_for_run(repo, run_id)
            except Exception:
                continue
            for job in jobs:
                job_id = int(job.get("id") or 0)
                if not job_id:
                    continue
                log = fetch_job_log(repo, run_id, job_id)
                if not log:
                    continue
                errors, warnings = extract_signals(log)
                if not errors and not warnings:
                    continue
                findings.append(
                    JobFinding(
                        workflow=workflow,
                        run_id=run_id,
                        run_url=run_url,
                        run_conclusion=run_conclusion,
                        job_id=job_id,
                        job_name=(job.get("name") or "(unknown)").strip(),
                        job_url=job.get("html_url")
                        or f"https://github.com/{repo}/actions/runs/{run_id}/job/{job_id}",
                        job_conclusion=(job.get("conclusion") or "").strip(),
                        errors=errors,
                        warnings=warnings,
                    )
                )

    if args.strict:
        strict_conclusions = {"failure", "cancelled", "timed_out"}
        before = len(findings)
        findings = [f for f in findings if (f.job_conclusion or "").lower() in strict_conclusions]
        dropped = before - len(findings)
        print(f"  --strict mode: kept {len(findings)} jobs, dropped {dropped} (successful jobs with warnings)")

    curated = curate_with_swarm_v2(findings)
    report = build_report(
        repo=repo,
        branch=args.branch,
        workflows=workflows,
        findings=findings,
        curated=curated,
        ftp_env_loaded=ftp_loaded,
        ftp_env_path=ftp_path,
        local_env_loaded=local_env_loaded,
        strict=args.strict,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    mode_tag = " (STRICT)" if args.strict else ""
    print(f"Wrote {args.out}{mode_tag} | workflows={len(workflows)} | findings={len(findings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
