"""Generate `audit_dashboard/research_index.html` — the top-level
listing of all research runs, grouped by asset class, newest first.

Reads `research/asset_class/<class>/run_*/​_summary.json` and renders a
single static page. Linked from `audit_dashboard/template.html` nav.
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    _EST_TZ = ZoneInfo("America/Toronto")
except (ImportError, KeyError):
    # ImportError: Python < 3.9 — we target 3.10+ but harmless.
    # KeyError: ZoneInfoNotFoundError subclasses KeyError; raised on
    #   Windows when the `tzdata` PyPI package is absent. Falling back
    #   to UTC keeps the generator import-clean; the rendered page says
    #   'UTC' instead of 'EDT/EST' but the build does not crash.
    _EST_TZ = timezone.utc


_MONTHS_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _fmt_est(dt: datetime) -> str:
    """Render a datetime in America/Toronto local time, locale-independent
    and Windows-portable. Example: 'May 11, 2026 3:34 PM EDT'.
    """
    est = dt.astimezone(_EST_TZ)
    month = _MONTHS_ABBR[est.month - 1]  # locale-independent month abbrev
    day = est.day
    year = est.year
    hour = est.hour % 12 or 12
    minute = f"{est.minute:02d}"
    ampm = "AM" if est.hour < 12 else "PM"
    tz = est.strftime("%Z") or "EST"
    return f"{month} {day}, {year} {hour}:{minute} {ampm} {tz}"


def _run_id_to_est(run_id: str) -> str:
    """Convert `run_2026-05-11T19-34-52Z` to a friendly EST/EDT string.
    Falls back to '' when the ID does not match the expected pattern.
    """
    m = re.match(r"run_(\d{4})-(\d{2})-(\d{2})T(\d{2})-(\d{2})-(\d{2})Z", run_id or "")
    if not m:
        return ""
    y, mo, d, hh, mm, ss = (int(x) for x in m.groups())
    try:
        utc = datetime(y, mo, d, hh, mm, ss, tzinfo=timezone.utc)
    except ValueError:
        return ""
    return _fmt_est(utc)

REPO_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = REPO_ROOT / "research" / "asset_class"
OUT_PATH = REPO_ROOT / "audit_dashboard" / "research_index.html"


def _e(s) -> str:
    return html.escape(str(s) if s is not None else "")


def _collect_runs() -> dict[str, list[dict]]:
    """Return {asset_class: [run_summary_dict, ...]}, newest first per class."""
    out: dict[str, list[dict]] = {}
    if not RESEARCH_ROOT.exists():
        return out
    for class_dir in sorted(RESEARCH_ROOT.iterdir()):
        if not class_dir.is_dir():
            continue
        runs = []
        for run_dir in sorted(class_dir.iterdir(), reverse=True):
            summary_path = run_dir / "_summary.json"
            if not summary_path.exists():
                continue
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            summary["_run_path"] = (
                f"research/asset_class/{class_dir.name}/{run_dir.name}/index.html"
            )
            summary["_run_dir_name"] = run_dir.name
            runs.append(summary)
        if runs:
            out[class_dir.name] = runs
    return out


def render(runs: dict[str, list[dict]]) -> str:
    sections = []
    for cls in sorted(runs):
        rows = []
        for r in runs[cls]:
            verdict = r.get("verdict", "PENDING")
            badge_color = {
                "GO": "#22c55e",
                "MIXED": "#fbbf24",
                "NO_EDGE": "#888",
                "PENDING": "#3b82f6",
                "ABORTED": "#ef4444",
            }.get(verdict, "#888")
            run_dir_name = r.get("_run_dir_name", "")
            est_str = _run_id_to_est(run_dir_name)
            rows.append(
                f"""<tr>
  <td><code>{_e(run_dir_name)}</code><br><span style="color:#94a3b8;font-size:11px">{_e(est_str)}</span></td>
  <td><span style="background:{badge_color};color:#0a0a0f;padding:2px 8px;border-radius:10px;font-weight:700">{_e(verdict)}</span></td>
  <td class="num">{r.get("n_candidates", 0)}</td>
  <td class="num">{r.get("n_backtested", 0)}</td>
  <td class="num">{r.get("n_independent_after_cross_test", 0)}</td>
  <td class="num">{r.get("n_citations_verified", 0)} / {r.get("n_citations_hallucinated", 0) + r.get("n_citations_verified", 0)}</td>
  <td class="num">${r.get("cost_usd", 0.0):.2f}</td>
  <td><a href="{_e(r["_run_path"])}">view →</a></td>
</tr>"""
            )
        body = "\n".join(rows) if rows else '<tr><td colspan="8"><i>No runs.</i></td></tr>'
        sections.append(
            f"""<section>
  <h2 style="text-transform:uppercase">{_e(cls)}</h2>
  <table class="data-table">
    <thead><tr><th>Run</th><th>Verdict</th><th>Candidates</th><th>Backtested</th><th>Independent</th><th>Citations verified/total</th><th>Cost</th><th>Page</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</section>"""
        )

    if not sections:
        sections.append(
            "<p><i>No research runs yet. Run "
            "<code>python -m tools.research.orchestrator --class bond</code> "
            "to seed the first.</i></p>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Research index · findtorontoevents.ca/audit</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 1200px; margin: 24px auto; padding: 0 16px; background: #0a0a0f; color: #e6e6f0; line-height: 1.5; }}
  h1 {{ margin-bottom: 4px; }}
  h2 {{ font-size: 14px; padding-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.1); color: #a0a0b0; }}
  table.data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  table.data-table th, table.data-table td {{ padding: 6px 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.08); }}
  table.data-table th {{ background: rgba(255,255,255,0.03); }}
  table.data-table td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  code {{ background: rgba(255,255,255,0.06); padding: 1px 6px; border-radius: 3px; font-size: 12px; }}
  section {{ margin: 24px 0; }}
  a {{ color: #60a5fa; }}
  header {{ padding: 16px; background: rgba(255,255,255,0.03); border-radius: 8px; margin-bottom: 16px; }}
</style>
</head>
<body>
<header>
  <h1>Asset-Class Research Index</h1>
  <div style="color:#a0a0b0;font-size:13px;margin-top:6px">
    Multi-AI consensus research runs producing sourced + backtested + cross-tested strategy candidates per asset class.
    See <code>tools/research/orchestrator.py</code> + <code>updates/2026-05-11-research-orchestrator-design.md</code> for the 5-pass protocol.
  </div>
  <div style="color:#94a3b8;font-size:12px;margin-top:8px">
    Index generated: <strong style="color:#e6e6f0">{_fmt_est(datetime.now(timezone.utc))}</strong>
    &nbsp;•&nbsp; All run timestamps shown below are also <strong>EST/EDT</strong>; the <code>run_*</code> directory IDs are UTC.
  </div>
</header>

<section style="margin-top:12px">
  <h2>How to read this page</h2>
  <div style="font-size:13px;color:#cbd5e1;line-height:1.6">
    Each run is one full 5-pass orchestrator cycle for one asset class:
    <strong>P1</strong> literature → <strong>P2</strong> candidate distillation →
    <strong>P3</strong> backtest → <strong>P4</strong> cross-test on out-of-sample fold →
    <strong>P5</strong> synthesis. Click <em>view →</em> to drill into the per-pass artifacts
    (<code>p1_literature.json</code>, <code>p2_candidates.json</code>, …, <code>p5_synthesis.md</code>).
    <br><br>
    <strong>Columns:</strong>
    <code>Candidates</code> = strategies P2 produced;
    <code>Backtested</code> = passed structural sanity to enter P3;
    <code>Independent</code> = survived P4 cross-test on a held-out fold;
    <code>Citations verified/total</code> = how many P1 citations resolved to a real URL;
    <code>Cost</code> = LLM spend for that run.
    <br><br>
    <strong>Verdict legend:</strong>
    <span style="background:#22c55e;color:#0a0a0f;padding:1px 8px;border-radius:10px;font-weight:700">GO</span>
    at least one candidate survived all 5 passes with Tier-2 floor stats (PF≥1.5, WR≥50, n≥100).
    &nbsp;
    <span style="background:#fbbf24;color:#0a0a0f;padding:1px 8px;border-radius:10px;font-weight:700">MIXED</span>
    survivors exist but fail the Tier-2 floor on one axis — needs human triage.
    &nbsp;
    <span style="background:#888;color:#0a0a0f;padding:1px 8px;border-radius:10px;font-weight:700">NO_EDGE</span>
    no candidate cleared cross-test.
    &nbsp;
    <span style="background:#3b82f6;color:#0a0a0f;padding:1px 8px;border-radius:10px;font-weight:700">PENDING</span>
    in flight.
    &nbsp;
    <span style="background:#ef4444;color:#0a0a0f;padding:1px 8px;border-radius:10px;font-weight:700">ABORTED</span>
    crashed before completing the 5 passes.
  </div>
</section>

{"".join(sections)}
<footer style="margin-top:32px;color:#a0a0b0;font-size:12px">
  Goal #1 (CLAUDE.md): phenomenal performance across ALL asset classes on /audit (Tier-2 floor PF≥1.5, WR≥50, MDD&lt;20, n≥100).
  This index updates whenever <code>python -m tools.research.build_research_index</code> runs (manually for now; CI cron in PR 3).
</footer>
</body>
</html>
"""


def main():
    runs = _collect_runs()
    OUT_PATH.write_text(render(runs), encoding="utf-8")
    print(f"wrote {OUT_PATH} — {sum(len(v) for v in runs.values())} runs across {len(runs)} classes")


if __name__ == "__main__":
    main()
