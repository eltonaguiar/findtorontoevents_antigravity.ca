#!/usr/bin/env python3
"""
Generate GitHub Actions high-level summary JSON + HTML dashboard.

Usage:
  python tools/generate_gha_summary_html.py
  python tools/generate_gha_summary_html.py --max-workflows 5
  python tools/generate_gha_summary_html.py --deploy
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.gha_summary_lib import (  # noqa: E402
    BAD_CONCLUSIONS,
    IN_PROGRESS_STATUSES,
    build_stale_workflow_set,
    fetch_bulk_runs,
    fetch_recent_runs,
    find_chronic_cancelled_workflows,
    find_unresolved_latest_failures,
    list_all_workflows,
    load_guardian_cache,
    normalize_run,
    scan_log_for_issues,
    should_scan_logs,
    utc_now_iso,
    workflow_shard,
)

DEFAULT_REPO = "eltonaguiar/findtorontoevents_antigravity.ca"
DEFAULT_JSON = REPO_ROOT / "reports" / "gha_actions_summary.json"
DEFAULT_HTML = REPO_ROOT / "reports" / "gha_actions_summary.html"


def collect_workflow_row(
    wf: Dict[str, Any],
    *,
    repo: str,
    branch: str,
    unresolved_ids: Set[int],
    chronic_names: Set[str],
    stale_reasons: Dict[str, str],
    skip_logs: bool,
    log_timeout: int,
) -> Dict[str, Any]:
    name = wf.get("name") or ""
    wid = wf.get("id")
    path = wf.get("path") or ""
    state = wf.get("state") or ""

    runs_raw = fetch_recent_runs(repo, name, branch, limit=3)
    runs = [normalize_run(r) for r in runs_raw]

    latest_status = ""
    latest_conclusion = ""
    last_ran_at = ""
    in_progress: Optional[Dict[str, Any]] = None
    log_scans: Dict[str, Any] = {}

    if runs:
        latest = runs[0]
        latest_status = latest.get("status") or ""
        latest_conclusion = latest.get("conclusion") or ""
        last_ran_at = latest.get("created_at") or latest.get("updated_at") or ""

        if (latest_status or "").lower() in IN_PROGRESS_STATUSES:
            in_progress = latest
            if should_scan_logs(
                {"status": latest_status, "conclusion": latest_conclusion},
                skip_logs=skip_logs,
            ):
                rid = latest.get("run_id")
                if rid:
                    try:
                        log_scans["in_progress"] = scan_log_for_issues(
                            int(rid), repo, log_timeout=log_timeout
                        )
                    except Exception as exc:
                        log_scans["in_progress"] = {"error": str(exc)}

        if (latest_status or "").lower() == "completed" and should_scan_logs(
            {"status": latest_status, "conclusion": latest_conclusion},
            skip_logs=skip_logs,
        ):
            rid = latest.get("run_id")
            if rid:
                try:
                    log_scans["latest"] = scan_log_for_issues(
                        int(rid), repo, log_timeout=log_timeout
                    )
                except Exception as exc:
                    log_scans["latest"] = {"error": str(exc)}

    never_run = len(runs) == 0
    stale_reason = stale_reasons.get(name)
    # Belt-and-suspenders: even if guardian cache says unresolved,
    # if the workflow's own latest run shows success, it's resolved.
    is_unresolved = (wid in unresolved_ids) if wid is not None else False
    if is_unresolved and runs and latest_status == "completed" and latest_conclusion == "success":
        is_unresolved = False
    flags = {
        "unresolved": is_unresolved,
        "chronic_cancelled": name in chronic_names,
        "never_run": never_run,
        "stale": bool(stale_reason) or never_run,
    }

    classification = ""
    err_c = warn_c = 0
    for key in ("latest", "in_progress"):
        scan = log_scans.get(key)
        if scan and not scan.get("error"):
            classification = scan.get("classification") or classification
            err_c += scan.get("error_count") or 0
            warn_c += scan.get("warning_count") or 0

    return {
        "name": name,
        "path": path,
        "state": state,
        "workflow_id": wid,
        "last_ran_at": last_ran_at,
        "latest_status": latest_status,
        "latest_conclusion": latest_conclusion,
        "flags": flags,
        "stale_reason": stale_reason or ("never_run" if never_run else ""),
        "runs": runs,
        "in_progress": in_progress,
        "log_scans": log_scans,
        "error_count": err_c,
        "warning_count": warn_c,
        "classification": classification,
    }


def compute_summary(workflows: List[Dict[str, Any]]) -> Dict[str, int]:
    s = {
        "in_progress": 0,
        "unresolved_failure": 0,
        "chronic_cancelled": 0,
        "latest_cancelled": 0,
        "latest_failure": 0,
        "never_run": 0,
        "stale_workflow": 0,
        "needs_attention": 0,
    }
    for w in workflows:
        flags = w.get("flags") or {}
        st = (w.get("latest_status") or "").lower()
        conc = (w.get("latest_conclusion") or "").lower()
        if st in IN_PROGRESS_STATUSES:
            s["in_progress"] += 1
        if flags.get("unresolved"):
            s["unresolved_failure"] += 1
        if flags.get("chronic_cancelled"):
            s["chronic_cancelled"] += 1
        if conc == "cancelled" and st == "completed":
            s["latest_cancelled"] += 1
        if conc in BAD_CONCLUSIONS:
            s["latest_failure"] += 1
        if flags.get("never_run"):
            s["never_run"] += 1
        if flags.get("stale"):
            s["stale_workflow"] += 1
        needs = (
            flags.get("unresolved")
            or flags.get("chronic_cancelled")
            or (conc in BAD_CONCLUSIONS and st == "completed")
        )
        if needs:
            s["needs_attention"] += 1
    return s


def render_html(payload: Dict[str, Any]) -> str:
    data_json = json.dumps(payload, ensure_ascii=False)
    gen = html.escape(payload.get("generated_at", ""))
    repo = html.escape(payload.get("repo", ""))
    branch = html.escape(payload.get("branch", ""))
    summary = payload.get("summary") or {}

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub Actions Summary — {repo}</title>
  <style>
    :root {{
      --bg: #0d1117;
      --panel: #161b22;
      --border: #30363d;
      --text: #e6edf3;
      --muted: #8b949e;
      --success: #3fb950;
      --failure: #f85149;
      --cancelled: #8b949e;
      --warning: #d29922;
      --progress: #58a6ff;
      --queued: #a371f7;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 1rem 1.5rem 3rem;
      line-height: 1.45;
    }}
    h1 {{ font-size: 1.5rem; margin: 0 0 0.25rem; }}
    .meta {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 1.25rem; }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1.25rem;
    }}
    .kpi {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.75rem 1rem;
    }}
    .kpi .n {{ font-size: 1.6rem; font-weight: 700; }}
    .kpi .l {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; }}
    .filters {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
      margin-bottom: 1rem;
    }}
    .chip {{
      background: var(--panel);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 0.35rem 0.65rem;
      border-radius: 999px;
      font-size: 0.8rem;
      cursor: pointer;
    }}
    .chip.active {{ border-color: var(--progress); background: #1f3a5f; }}
    input[type="search"] {{
      width: 100%;
      max-width: 420px;
      padding: 0.5rem 0.75rem;
      margin-bottom: 1rem;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 6px;
      color: var(--text);
    }}
    section {{ margin-bottom: 2rem; }}
    section h2 {{ font-size: 1.1rem; margin: 0 0 0.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.35rem; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }}
    th, td {{
      border: 1px solid var(--border);
      padding: 0.45rem 0.55rem;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: var(--panel); cursor: pointer; user-select: none; }}
    tr:hover td {{ background: #1c2128; }}
    tr.hidden {{ display: none; }}
    .badge {{
      display: inline-block;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: lowercase;
    }}
    .badge.success {{ background: #238636; color: #fff; }}
    .badge.failure, .badge.timed_out, .badge.startup_failure, .badge.stale, .badge.action_required {{
      background: #da3633; color: #fff;
    }}
    .badge.cancelled, .badge.skipped, .badge.neutral {{ background: #484f58; color: #fff; }}
    .badge.in_progress, .badge.queued, .badge.waiting, .badge.pending {{
      background: #1f6feb; color: #fff;
    }}
    .badge.warning {{ background: #9e6a03; color: #fff; }}
    details {{ margin: 0.25rem 0; }}
    details pre {{
      background: #010409;
      border: 1px solid var(--border);
      padding: 0.5rem;
      overflow-x: auto;
      font-size: 0.72rem;
      max-height: 280px;
    }}
    a {{ color: #58a6ff; }}
    footer {{ color: var(--muted); font-size: 0.8rem; margin-top: 2rem; }}
    .prior {{ font-size: 0.75rem; color: var(--muted); }}
  </style>
</head>
<body>
  <h1>GitHub Actions — High-Level Summary</h1>
  <p class="meta">Repo: <strong>{repo}</strong> · Branch: <strong>{branch}</strong> · Generated: <strong>{gen}</strong></p>

  <div class="kpis" id="kpis"></div>

  <input type="search" id="search" placeholder="Filter workflows by name…" aria-label="Search workflows">

  <div class="filters" id="filters"></div>

  <section id="sec-attention">
    <h2>Needs attention</h2>
    <table id="tbl-attention"><thead><tr>
      <th data-sort="name">Workflow</th>
      <th data-sort="status">Latest</th>
      <th data-sort="last">Last ran</th>
      <th>Flags</th>
      <th>Errors / Warnings</th>
      <th>Classification</th>
      <th>Link</th>
    </tr></thead><tbody></tbody></table>
  </section>

  <section id="sec-running">
    <h2>Running now</h2>
    <table id="tbl-running"><thead><tr>
      <th>Workflow</th><th>Status</th><th>Started</th><th>Errors / Warnings</th><th>Link</th>
    </tr></thead><tbody></tbody></table>
  </section>

  <section id="sec-all">
    <h2>All workflows</h2>
    <table id="tbl-all"><thead><tr>
      <th data-sort="name">Workflow</th>
      <th data-sort="last">Last ran</th>
      <th data-sort="status">Latest status</th>
      <th>Prior 2</th>
      <th data-sort="err">Errors</th>
      <th data-sort="warn">Warnings</th>
      <th>Classification</th>
      <th>Link</th>
    </tr></thead><tbody></tbody></table>
  </section>

  <footer>
    <p>Data embedded from <code>reports/gha_actions_summary.json</code>.
    Guardian cache: <a href="https://github.com/{repo}/blob/main/reports/actions_failure_guardian.json">actions_failure_guardian.json</a>.</p>
    <p>Regenerate: <code>python tools/generate_gha_summary_html.py --repo {repo} --branch {branch}</code></p>
  </footer>

  <script>
  const PAYLOAD = {data_json};

  function badge(status, conclusion) {{
    const st = (status || '').toLowerCase();
    const co = (conclusion || '').toLowerCase();
    let cls = co || st || 'neutral';
    if (st && st !== 'completed') cls = st.replace(/ /g, '_');
    const label = st === 'completed' ? (co || st) : st;
    return `<span class="badge ${{cls.replace(/ /g, '_')}}">${{label || '—'}}</span>`;
  }}

  function fmtTime(iso) {{
    if (!iso) return '—';
    try {{
      const d = new Date(iso);
      return d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
    }} catch (e) {{ return iso; }}
  }}

  function priorRuns(runs) {{
    if (!runs || runs.length < 2) return '<span class="prior">—</span>';
    return runs.slice(1).map(r =>
      `<span class="prior">${{badge(r.status, r.conclusion)}} <a href="${{r.url}}">#${{r.run_id}}</a></span>`
    ).join('<br>');
  }}

  function logDetail(w) {{
    const parts = [];
    for (const key of ['latest', 'in_progress']) {{
      const s = (w.log_scans || {{}})[key];
      if (!s) continue;
      if (s.error) {{
        parts.push(`<p><strong>${{key}}</strong>: ${{s.error}}</p>`);
        continue;
      }}
      const lines = (s.sample_lines || []).concat(s.critical_signals || []).slice(0, 20);
      if (lines.length) {{
        parts.push(`<details><summary>${{key}} log (${{s.error_count}} errors, ${{s.warning_count}} warnings) — ${{s.classification || ''}}</summary><pre>${{lines.join('\\n')}}</pre></details>`);
      }}
    }}
    if (w.runs && w.runs.length) {{
      parts.push('<details><summary>Last 3 runs</summary><pre>' +
        w.runs.map(r => `${{r.created_at}}  ${{r.status}}/${{r.conclusion}}  ${{r.url}}`).join('\\n') +
        '</pre></details>');
    }}
    return parts.join('');
  }}

  function flagStr(f) {{
    const bits = [];
    if (f.unresolved) bits.push('unresolved');
    if (f.chronic_cancelled) bits.push('chronic_cancelled');
    if (f.never_run) bits.push('never_run');
    if (f.stale) bits.push('stale');
    return bits.join(', ') || '—';
  }}

  function needsAttention(w) {{
    const f = w.flags || {{}};
    const co = (w.latest_conclusion || '').toLowerCase();
    const st = (w.latest_status || '').toLowerCase();
    return f.unresolved || f.chronic_cancelled ||
      (st === 'completed' && ['failure','timed_out','startup_failure','stale','action_required'].includes(co));
  }}

  function isRunning(w) {{
    return ['in_progress','queued','waiting','pending'].includes((w.latest_status||'').toLowerCase());
  }}

  function renderKpis(s) {{
    const items = [
      ['workflows_total', 'Workflows'],
      ['in_progress', 'Running'],
      ['needs_attention', 'Needs attention'],
      ['unresolved_failure', 'Unresolved'],
      ['chronic_cancelled', 'Chronic cancel'],
      ['latest_failure', 'Latest failed'],
      ['latest_cancelled', 'Latest cancelled'],
      ['never_run', 'Never run'],
    ];
    document.getElementById('kpis').innerHTML = items.map(([k, l]) =>
      `<div class="kpi"><div class="n">${{s[k] ?? 0}}</div><div class="l">${{l}}</div></div>`
    ).join('');
  }}

  function rowAttention(w) {{
    const url = (w.runs && w.runs[0] && w.runs[0].url) || '#';
    return `<tr data-name="${{w.name.toLowerCase()}}" data-status="${{(w.latest_conclusion||w.latest_status||'').toLowerCase()}}">
      <td>${{w.name}}<br><span class="prior">${{w.path}}</span>${{logDetail(w)}}</td>
      <td>${{badge(w.latest_status, w.latest_conclusion)}}</td>
      <td>${{fmtTime(w.last_ran_at)}}</td>
      <td>${{flagStr(w.flags)}}</td>
      <td>${{w.error_count}} / ${{w.warning_count}}</td>
      <td>${{w.classification || '—'}}</td>
      <td><a href="${{url}}" target="_blank" rel="noopener">Run</a></td>
    </tr>`;
  }}

  function rowRunning(w) {{
    const url = (w.in_progress && w.in_progress.url) || (w.runs && w.runs[0] && w.runs[0].url) || '#';
  const started = (w.in_progress && w.in_progress.created_at) || w.last_ran_at;
    return `<tr>
      <td>${{w.name}}</td>
      <td>${{badge(w.latest_status, w.latest_conclusion)}}</td>
      <td>${{fmtTime(started)}}</td>
      <td>${{w.error_count}} / ${{w.warning_count}}</td>
      <td><a href="${{url}}" target="_blank" rel="noopener">Run</a></td>
    </tr>`;
  }}

  function rowAll(w) {{
    const url = (w.runs && w.runs[0] && w.runs[0].url) || '#';
    return `<tr class="wf-row" data-name="${{w.name.toLowerCase()}}"
      data-status="${{(w.latest_conclusion||w.latest_status||'').toLowerCase()}}"
      data-err="${{w.error_count}}" data-warn="${{w.warning_count}}" data-last="${{w.last_ran_at||''}}">
      <td>${{w.name}}<details><summary>detail</summary>${{logDetail(w)}}</details></td>
      <td>${{fmtTime(w.last_ran_at)}}</td>
      <td>${{badge(w.latest_status, w.latest_conclusion)}}</td>
      <td>${{priorRuns(w.runs)}}</td>
      <td>${{w.error_count}}</td>
      <td>${{w.warning_count}}</td>
      <td>${{w.classification || '—'}}</td>
      <td><a href="${{url}}" target="_blank" rel="noopener">Run</a></td>
    </tr>`;
  }}

  const STATUS_CHIPS = ['all','failure','cancelled','success','skipped','in_progress','queued','timed_out','stale','never_run','chronic'];
  let activeFilter = 'all';

  function applyFilters() {{
    const q = (document.getElementById('search').value || '').toLowerCase();
    document.querySelectorAll('#tbl-all tbody tr').forEach(tr => {{
      const name = tr.dataset.name || '';
      const st = tr.dataset.status || '';
      let show = name.includes(q);
      if (activeFilter === 'never_run') show = show && st === '';
      else if (activeFilter === 'chronic') {{
        const w = PAYLOAD.workflows.find(x => x.name.toLowerCase() === name);
        show = show && w && w.flags && w.flags.chronic_cancelled;
      }} else if (activeFilter !== 'all') show = show && (st === activeFilter || st.includes(activeFilter));
      tr.classList.toggle('hidden', !show);
    }});
  }}

  function init() {{
    const wfs = PAYLOAD.workflows || [];
    renderKpis(PAYLOAD.summary || {{}});
    document.querySelector('#tbl-attention tbody').innerHTML =
      wfs.filter(needsAttention).map(rowAttention).join('') || '<tr><td colspan="7">None</td></tr>';
    document.querySelector('#tbl-running tbody').innerHTML =
      wfs.filter(isRunning).map(rowRunning).join('') || '<tr><td colspan="5">None</td></tr>';
    document.querySelector('#tbl-all tbody').innerHTML = wfs.map(rowAll).join('');

    const filt = document.getElementById('filters');
    filt.innerHTML = STATUS_CHIPS.map(c =>
      `<button type="button" class="chip ${{c==='all'?'active':''}}" data-f="${{c}}">${{c}}</button>`
    ).join('');
    filt.addEventListener('click', e => {{
      if (!e.target.dataset.f) return;
      activeFilter = e.target.dataset.f;
      filt.querySelectorAll('.chip').forEach(el => el.classList.toggle('active', el.dataset.f === activeFilter));
      applyFilters();
    }});
    document.getElementById('search').addEventListener('input', applyFilters);

    document.querySelectorAll('th[data-sort]').forEach(th => {{
      th.addEventListener('click', () => {{
        const key = th.dataset.sort;
        const tbody = th.closest('table').querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const dir = th.dataset.dir === 'asc' ? 'desc' : 'asc';
        th.dataset.dir = dir;
        rows.sort((a, b) => {{
          let av = a.dataset[key] || a.querySelector('td')?.textContent || '';
          let bv = b.dataset[key] || b.querySelector('td')?.textContent || '';
          if (key === 'err' || key === 'warn') {{ av = +av; bv = +bv; }}
          if (av < bv) return dir === 'asc' ? -1 : 1;
          if (av > bv) return dir === 'asc' ? 1 : -1;
          return 0;
        }});
        rows.forEach(r => tbody.appendChild(r));
      }});
    }});
  }}
  init();
  </script>
</body>
</html>
"""


def merge_shard_payloads(shards: List[Path]) -> Dict[str, Any]:
    merged_workflows: List[Dict[str, Any]] = []
    base: Dict[str, Any] = {}
    for p in sorted(shards):
        chunk = json.loads(p.read_text(encoding="utf-8"))
        if not base:
            base = {k: v for k, v in chunk.items() if k != "workflows"}
        merged_workflows.extend(chunk.get("workflows") or [])
    base["workflows"] = merged_workflows
    base["workflows_total"] = len(merged_workflows)
    base["summary"] = compute_summary(merged_workflows)
    return base


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--json", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    ap.add_argument("--bulk-limit", type=int, default=600)
    ap.add_argument("--max-workers", type=int, default=8)
    ap.add_argument("--log-timeout", type=int, default=120)
    ap.add_argument("--max-workflows", type=int, default=0, help="0 = all workflows")
    ap.add_argument("--skip-logs", action="store_true")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--shard-json", type=Path, help="Write shard JSON only (for parallel runs)")
    ap.add_argument("--merge-shards", nargs="+", type=Path, help="Merge shard JSONs then render HTML")
    ap.add_argument("--deploy", action="store_true")
    args = ap.parse_args()

    if args.merge_shards:
        payload = merge_shard_payloads(args.merge_shards)
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        args.html.write_text(render_html(payload), encoding="utf-8")
        print(f"Merged {len(args.merge_shards)} shards -> {args.json} + {args.html}")
        if args.deploy:
            from tools.deploy_gha_summary import deploy_summary  # noqa: WPS433

            deploy_summary(args.html)
        return 0

    print(f"Listing workflows for {args.repo}…")
    all_wfs = list_all_workflows(args.repo)
    if args.shards > 1:
        all_wfs = [w for w in all_wfs if workflow_shard(w.get("name") or "", args.shard, args.shards)]
    if args.max_workflows > 0:
        all_wfs = all_wfs[: args.max_workflows]

    print(f"Fetching bulk runs (limit {args.bulk_limit})…")
    bulk = fetch_bulk_runs(args.repo, args.branch, args.bulk_limit)

    guardian = load_guardian_cache()
    if guardian:
        print("Using fresh guardian cache for unresolved/chronic/stale hints")
        unresolved = guardian.get("unresolved_failures") or []
        chronic = guardian.get("chronic_cancel_workflows") or []
        if not chronic:
            chronic = find_chronic_cancelled_workflows(
                bulk, branch=args.branch, group_by_workflow_name=True
            )
        if not unresolved:
            unresolved = find_unresolved_latest_failures(bulk, args.branch)
    else:
        unresolved = find_unresolved_latest_failures(bulk, args.branch)
        chronic = find_chronic_cancelled_workflows(
            bulk, branch=args.branch, group_by_workflow_name=True
        )

    unresolved_ids: Set[int] = set()
    for u in unresolved:
        wid = u.get("workflow_id")
        if wid is not None:
            unresolved_ids.add(int(wid))

    # Cross-validate guardian unresolved entries against fresh bulk data.
    # If the latest bulk run for a workflow is success, it's no longer unresolved.
    if guardian and unresolved_ids:
        latest_by_wid: dict = {}
        for r in bulk:
            wid = r.get("workflow_id")
            if wid is not None and wid in unresolved_ids:
                created = r.get("created_at") or r.get("createdAt") or ""
                if wid not in latest_by_wid or created > latest_by_wid[wid].get("created_at", ""):
                    latest_by_wid[wid] = r
        for wid, r in latest_by_wid.items():
            if r.get("status") == "completed" and r.get("conclusion") == "success":
                unresolved_ids.discard(wid)
                print(f"  Guardian cache stale: workflow_id={wid} is now success — removed from unresolved")

    chronic_names: Set[str] = set()
    for c in chronic:
        n = c.get("workflow_name") or ""
        if n:
            chronic_names.add(n)

    stale_reasons = build_stale_workflow_set(guardian)

    print(f"Collecting {len(all_wfs)} workflows (workers={args.max_workers})…")
    workflows: List[Dict[str, Any]] = []
    done = 0

    def task(wf: Dict[str, Any]) -> Dict[str, Any]:
        return collect_workflow_row(
            wf,
            repo=args.repo,
            branch=args.branch,
            unresolved_ids=unresolved_ids,
            chronic_names=chronic_names,
            stale_reasons=stale_reasons,
            skip_logs=args.skip_logs,
            log_timeout=args.log_timeout,
        )

    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        futures = {pool.submit(task, wf): wf for wf in all_wfs}
        for fut in as_completed(futures):
            workflows.append(fut.result())
            done += 1
            if done % 25 == 0:
                print(f"  … {done}/{len(all_wfs)}")

    workflows.sort(key=lambda w: (w.get("name") or "").lower())

    payload: Dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "repo": args.repo,
        "branch": args.branch,
        "workflows_total": len(workflows),
        "summary": compute_summary(workflows),
        "unresolved_failures": unresolved,
        "chronic_cancelled": chronic,
        "guardian_cache_used": guardian is not None,
        "workflows": workflows,
    }

    out_json = args.shard_json or args.json
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_json}")

    if args.shard_json:
        return 0

    args.html.write_text(render_html(payload), encoding="utf-8")
    print(f"Wrote {args.html}")

    if args.deploy:
        from tools.deploy_gha_summary import deploy_summary  # noqa: WPS433

        deploy_summary(args.html)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
