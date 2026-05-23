"""Render one asset-class research run to a static HTML page.

Minimum-viable: header (class, ts, verdict), citations table,
candidates table, backtest table, cross-test table, synthesis prose,
next-steps callout for NO_EDGE runs, footer with cost + raw artifact link.

Reuses styling from audit_dashboard via a relative <link> so the page
sits naturally inside /audit/research/<class>/run_<ts>/.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from .schemas import (
    BacktestResult,
    Citation,
    CrossTestResult,
    RunSummary,
    StrategySpec,
    SynthesisRow,
)


def _e(s) -> str:
    return html.escape(str(s) if s is not None else "")


def _citations_table(citations: list[Citation]) -> str:
    rows = []
    for c in citations:
        verified_badge = '<span style="color:#22c55e">✓ verified</span>' if c.verified else '<span style="color:#ef4444">✗ unverified</span>'
        trust_badge = '<span style="color:#fbbf24">low-trust domain</span>' if c.low_trust else ""
        rows.append(
            f"""<tr>
  <td><a href="{_e(c.url)}" target="_blank" rel="noopener">{_e(c.url[:80])}…</a></td>
  <td>{_e(c.access_date)}</td>
  <td>{_e(c.title or "—")}</td>
  <td>{_e(c.evidence_strength)}</td>
  <td>{verified_badge} {trust_badge}</td>
</tr>"""
        )
    body = "\n".join(rows) if rows else '<tr><td colspan="5"><i>No citations yet (P1 swarm pending).</i></td></tr>'
    return f"""<section id="citations">
  <h2>Citations</h2>
  <table class="data-table">
    <thead><tr><th>URL</th><th>Access date</th><th>Title</th><th>Evidence</th><th>Status</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</section>"""


def _candidates_table(specs: list[StrategySpec]) -> str:
    rows = []
    for s in specs:
        refs = ", ".join(f'<a href="{_e(u)}" target="_blank" rel="noopener">[{i+1}]</a>' for i, u in enumerate(s.source_refs))
        rows.append(
            f"""<tr>
  <td><code>{_e(s.spec_id)}</code></td>
  <td>{_e(s.entry)}</td>
  <td>{_e(s.exit)}</td>
  <td>{_e(s.sizing)}</td>
  <td>{_e(", ".join(s.universe))}</td>
  <td>{refs or "—"}</td>
  <td><i>{_e(s.proposed_by_engine)}</i></td>
</tr>"""
        )
    body = "\n".join(rows) if rows else '<tr><td colspan="7"><i>No candidates.</i></td></tr>'
    return f"""<section id="candidates">
  <h2>Strategy candidates (P2)</h2>
  <table class="data-table">
    <thead><tr><th>spec_id</th><th>Entry</th><th>Exit</th><th>Sizing</th><th>Universe</th><th>Sources</th><th>Source engine</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</section>"""


def _backtest_table(results: list[BacktestResult]) -> str:
    rows = []
    for r in results:
        pf_cls = "pnl-pos" if r.pf >= 1.5 else ("pnl-neu" if r.pf >= 1.0 else "pnl-neg")
        rows.append(
            f"""<tr>
  <td><code>{_e(r.spec_id)}</code></td>
  <td class="num {pf_cls}">{r.pf:.2f}</td>
  <td class="num">{r.wr:.1f}</td>
  <td class="num">{r.mdd:.1f}</td>
  <td class="num">{r.sharpe:.2f}</td>
  <td class="num">{r.n_trades}</td>
  <td>{_e(r.data_window_start)} → {_e(r.data_window_end)}</td>
  <td><i>{_e(r.notes[:120])}</i></td>
</tr>"""
        )
    body = "\n".join(rows) if rows else '<tr><td colspan="8"><i>No backtest results.</i></td></tr>'
    return f"""<section id="backtest">
  <h2>Backtest (P3)</h2>
  <table class="data-table">
    <thead><tr><th>spec_id</th><th>PF</th><th>WR %</th><th>MDD %</th><th>Sharpe</th><th>n</th><th>Window</th><th>Notes</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</section>"""


def _cross_test_table(results: list[CrossTestResult]) -> str:
    rows = []
    for r in results:
        v_color = {"DUPLICATE": "#ef4444", "OVERLAP_WARNING": "#fbbf24", "INDEPENDENT": "#22c55e"}.get(r.verdict, "#888")
        nn = " ; ".join(f'{n["strategy"]} (ρ={n["rho"]:.2f})' for n in r.nearest_neighbors)
        rows.append(
            f"""<tr>
  <td><code>{_e(r.spec_id)}</code></td>
  <td class="num">{r.max_rho:.2f}</td>
  <td>{_e(r.max_rho_strategy)}</td>
  <td class="num">{r.symbol_overlap_pct:.1f}</td>
  <td style="color:{v_color}"><b>{_e(r.verdict)}</b></td>
  <td>{_e(nn)}</td>
</tr>"""
        )
    body = "\n".join(rows) if rows else '<tr><td colspan="6"><i>No cross-test results.</i></td></tr>'
    return f"""<section id="cross_test">
  <h2>Cross-test vs shipped strategies (P4)</h2>
  <table class="data-table">
    <thead><tr><th>spec_id</th><th>max |ρ|</th><th>nearest shipped</th><th>symbol overlap %</th><th>verdict</th><th>top neighbors</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</section>"""


def _synthesis_block(synthesis: list[SynthesisRow]) -> str:
    rows = []
    for s in synthesis:
        v_color = {"GO": "#22c55e", "MIXED": "#fbbf24", "NO_EDGE": "#888"}.get(s.verdict, "#888")
        votes = " | ".join(f'{eng}: <b>{vote}</b>' for eng, vote in (s.engine_votes or {}).items())
        rows.append(
            f"""<div style="margin:12px 0;padding:12px;border-left:3px solid {v_color};background:rgba(255,255,255,0.02)">
  <div><code>{_e(s.spec_id)}</code> — <span style="color:{v_color}"><b>{_e(s.verdict)}</b></span></div>
  <div style="margin-top:6px">{_e(s.rationale)}</div>
  {f'<div style="margin-top:6px;color:var(--text-dim)"><b>Engine votes:</b> {votes}</div>' if votes else ''}
  {f'<details style="margin-top:8px"><summary>Wiring plan</summary><pre style="white-space:pre-wrap">{_e(s.wiring_plan)}</pre></details>' if s.wiring_plan else ''}
</div>"""
        )
    body = "\n".join(rows) if rows else '<i>No synthesis yet (P5 swarm pending).</i>'
    return f"""<section id="synthesis">
  <h2>Synthesis (P5)</h2>
  {body}
</section>"""


def render(
    summary: RunSummary,
    citations: list[Citation],
    specs: list[StrategySpec],
    backtests: list[BacktestResult],
    cross_tests: list[CrossTestResult],
    synthesis: list[SynthesisRow],
    artifacts_dir: str = ".",
) -> str:
    verdict_color = {
        "GO": "#22c55e",
        "MIXED": "#fbbf24",
        "NO_EDGE": "#888",
        "PENDING": "#3b82f6",
        "ABORTED": "#ef4444",
    }.get(summary.verdict, "#888")

    no_edge_callout = ""
    if summary.verdict == "NO_EDGE":
        no_edge_callout = """<section id="next_steps" style="margin-top:24px;padding:16px;border:1px solid rgba(251,191,36,0.4);background:rgba(251,191,36,0.05);border-radius:8px">
  <h2 style="margin-top:0">No edge found this round</h2>
  <p>The 5-pass research process did not surface a strategy passing PF≥1.5, n≥50, and INDEPENDENT cross-test for this asset class.</p>
  <p><b>Retry conditions:</b> see Synthesis section above for regime triggers + new sources to chase next round. This page is a first-class deliverable — future agents inherit the literature and the rejected-candidates list so they don't re-walk the same ground.</p>
</section>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Research · {_e(summary.asset_class)} · {_e(summary.run_ts_utc)}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 1200px; margin: 24px auto; padding: 0 16px; background: #0a0a0f; color: #e6e6f0; line-height: 1.5; --text-dim: #a0a0b0; }}
  h1 {{ margin-bottom: 4px; }}
  header {{ padding: 16px; background: rgba(255,255,255,0.03); border-radius: 8px; margin-bottom: 16px; }}
  .verdict-badge {{ display: inline-block; padding: 4px 12px; border-radius: 16px; background: {verdict_color}; color: #0a0a0f; font-weight: 700; }}
  table.data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  table.data-table th, table.data-table td {{ padding: 6px 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.08); vertical-align: top; }}
  table.data-table th {{ background: rgba(255,255,255,0.03); }}
  table.data-table td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .pnl-pos {{ color: #22c55e; }}
  .pnl-neu {{ color: #a0a0b0; }}
  .pnl-neg {{ color: #ef4444; }}
  code {{ background: rgba(255,255,255,0.06); padding: 1px 6px; border-radius: 3px; font-size: 12px; }}
  section {{ margin: 24px 0; }}
  h2 {{ font-size: 16px; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.1); }}
  a {{ color: #60a5fa; }}
  footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.1); color: var(--text-dim); font-size: 12px; }}
</style>
</head>
<body>
<header>
  <h1>Asset Class: {_e(summary.asset_class)}</h1>
  <div>Run: <code>{_e(summary.run_ts_utc)}</code> · Verdict: <span class="verdict-badge">{_e(summary.verdict)}</span></div>
  <div style="margin-top:8px;color:var(--text-dim);font-size:13px">
    Schema {_e(summary.schema_version)} ·
    citations: {summary.n_citations_verified} verified / {summary.n_citations_hallucinated} hallucinated ·
    candidates: {summary.n_candidates} ·
    backtested: {summary.n_backtested} ·
    independent: {summary.n_independent_after_cross_test} ·
    cost: ${summary.cost_usd:.2f} ·
    wall: {summary.wall_time_sec:.0f}s
  </div>
</header>

{_citations_table(citations)}
{_candidates_table(specs)}
{_backtest_table(backtests)}
{_cross_test_table(cross_tests)}
{_synthesis_block(synthesis)}
{no_edge_callout}

<footer>
  Generated by <a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/tools/research">tools/research/orchestrator.py</a> ·
  Raw artifacts: <a href="{_e(artifacts_dir)}/">./</a> ·
  Asset-class banner per CLAUDE.md Goal #1 (Tier-2 floor: PF≥1.5, WR≥50, MDD&lt;20, n≥100).
  <br>
  Numbers in P3 backtest table are v1 STUBs (deterministic from spec_id hash) until BacktestEngine wire-in lands.
</footer>
</body>
</html>
"""


def write_run(
    run_dir: Path,
    summary: RunSummary,
    citations: list[Citation],
    specs: list[StrategySpec],
    backtests: list[BacktestResult],
    cross_tests: list[CrossTestResult],
    synthesis: list[SynthesisRow],
) -> Path:
    """Write all 5 artifacts + index.html into run_dir."""
    from .schemas import to_dict

    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "_summary.json").write_text(
        json.dumps(to_dict(summary), indent=2, default=str), encoding="utf-8"
    )
    (run_dir / "p1_literature.json").write_text(
        json.dumps([to_dict(c) for c in citations], indent=2, default=str),
        encoding="utf-8",
    )
    (run_dir / "p2_candidates.json").write_text(
        json.dumps([to_dict(s) for s in specs], indent=2, default=str),
        encoding="utf-8",
    )
    (run_dir / "p3_backtest.json").write_text(
        json.dumps([to_dict(r) for r in backtests], indent=2, default=str),
        encoding="utf-8",
    )
    (run_dir / "p4_cross_test.json").write_text(
        json.dumps([to_dict(r) for r in cross_tests], indent=2, default=str),
        encoding="utf-8",
    )
    (run_dir / "p5_synthesis.md").write_text(
        _synthesis_to_md(synthesis), encoding="utf-8"
    )

    index_path = run_dir / "index.html"
    index_path.write_text(
        render(summary, citations, specs, backtests, cross_tests, synthesis),
        encoding="utf-8",
    )
    return index_path


def _synthesis_to_md(synthesis: list[SynthesisRow]) -> str:
    lines = ["# Synthesis (P5)", ""]
    for s in synthesis:
        lines.append(f"## `{s.spec_id}` — **{s.verdict}**")
        lines.append("")
        lines.append(s.rationale)
        if s.engine_votes:
            lines.append("")
            lines.append("**Engine votes:** " + ", ".join(f"{e}: {v}" for e, v in s.engine_votes.items()))
        if s.wiring_plan:
            lines.append("")
            lines.append("**Wiring plan:**")
            lines.append("```")
            lines.append(s.wiring_plan)
            lines.append("```")
        lines.append("")
    return "\n".join(lines)
