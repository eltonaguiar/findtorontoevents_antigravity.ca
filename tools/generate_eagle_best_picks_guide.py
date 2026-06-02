#!/usr/bin/env python3
"""Generate updates/eagle-best-picks-guide-2026-06-02.html from local JSON + catalogs."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "updates" / "eagle-best-picks-guide-2026-06-02.html"
CATALOG = ROOT / "reports" / "_eagle_catalog_build.json"
SWARM = ROOT / "reports" / "best_picks_swarm_review_2026-06-02.json"


def _esc(s) -> str:
    return html.escape(str(s))


def _load(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def recent_planning_files() -> list[str]:
    paths = []
    for d in [ROOT / "plans", ROOT / "docs" / "plans"]:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            name = p.name
            if any(x in name for x in ("2026-06", "2026-05-3", "2026-05-2", "2026-05-31")):
                paths.append(p.relative_to(ROOT).as_posix())
    for p in sorted((ROOT / "reports").glob("*2026-06-02*")):
        if p.suffix.lower() == ".md" and "EAGLE" not in p.name.upper():
            paths.append(p.relative_to(ROOT).as_posix())
    for p in sorted((ROOT / "updates").glob("2026-06-02*.md")):
        paths.append(p.relative_to(ROOT).as_posix())
    return sorted(set(paths))


def main():
    catalog = _load(CATALOG)
    swarm = _load(SWARM)
    mr = _load(ROOT / "audit_dashboard/data/money_ready_verdict.json")
    lb = _load(ROOT / "audit_dashboard/data/ai_tournament_leaderboard.json")

    eagle_files = catalog.get("eagle") or []
    plans = recent_planning_files()
    swarm_md = swarm.get("swarm_review_markdown") or swarm.get("swarm_error") or "(swarm not run)"

    top_models = []
    for m in (lb.get("models") or [])[:5]:
        top_models.append(m)

    mr_rows = []
    for k, v in sorted((mr.get("classes") or {}).items()):
        if not isinstance(v, dict) or not v.get("n_resolved"):
            continue
        mr_rows.append((k, v))

    eagle_li = "\n".join(
        f'<li><a href="/{_esc(p)}">{_esc(p)}</a></li>' for p in eagle_files
    )
    plan_li = "\n".join(
        f'<li><a href="/{_esc(p)}">{_esc(p)}</a></li>' for p in plans[:80]
    )
    if len(plans) > 80:
        plan_li += f"<li><em>…and {len(plans) - 80} more under docs/plans/</em></li>"

    model_rows = ""
    for m in top_models:
        model_rows += (
            f"<tr><td>{_esc(m.get('model_id'))}</td>"
            f"<td>{m.get('n_resolved')}</td>"
            f"<td>{round((m.get('wr') or 0) * 100, 1)}%</td>"
            f"<td>{m.get('pf')}</td>"
            f"<td>{_esc(m.get('tier'))}</td>"
            f"<td><span class=\"badge paper\">PAPER WATCH</span></td></tr>\n"
        )

    prod_rows = ""
    for k, v in mr_rows:
        prod_rows += (
            f"<tr><td>{_esc(k)}</td><td>{v.get('n_resolved')}</td>"
            f"<td>{round((v.get('wr') or 0) * 100, 1)}%</td>"
            f"<td>{v.get('pf')}</td>"
            f"<td>{_esc(v.get('verdict'))}</td>"
            f"<td><span class=\"badge no\">NO LIVE SIZE</span></td></tr>\n"
        )

    swarm_html = "<pre class=\"swarm\">" + _esc(swarm_md) + "</pre>"

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>EAGLE Best Picks Guide — 2026-06-02</title>
<link rel="canonical" href="https://findtorontoevents.ca/updates/eagle-best-picks-guide-2026-06-02.html">
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 920px; margin: 24px auto; padding: 0 16px; background: #0a0a0f; color: #e6e6f0; line-height: 1.6; }}
  h1 {{ font-size: 22px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; }}
  h2 {{ font-size: 16px; margin-top: 28px; color: #93c5fd; }}
  h3 {{ font-size: 14px; color: #c0c0d0; margin-top: 18px; }}
  .meta {{ color: #6b7280; font-size: 11px; margin-bottom: 16px; }}
  .callout {{ background: rgba(239,68,68,0.08); border-left: 4px solid #ef4444; padding: 12px 14px; border-radius: 0 8px 8px 0; margin: 16px 0; font-size: 13px; }}
  .callout.ok {{ background: rgba(34,197,94,0.08); border-left-color: #22c55e; }}
  code {{ background: rgba(255,255,255,0.06); padding: 1px 5px; border-radius: 3px; font-size: 11px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,0.06); vertical-align: top; }}
  th {{ color: #a0a0b0; font-size: 11px; text-transform: uppercase; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 700; }}
  .paper {{ background: #713f12; color: #fbbf24; }}
  .shadow {{ background: #1e3a5f; color: #93c5fd; }}
  .no {{ background: #7c2d12; color: #fca5a5; }}
  .eli5 {{ background: rgba(34,197,94,0.06); border: 1px solid rgba(34,197,94,0.25); border-radius: 8px; padding: 10px 12px; margin: 8px 0 16px; font-size: 13px; }}
  .eli5 strong {{ color: #86efac; }}
  ul.files {{ columns: 2; font-size: 12px; line-height: 1.5; }}
  ul.files a {{ color: #93c5fd; }}
  pre.swarm {{ white-space: pre-wrap; font-size: 12px; background: rgba(0,0,0,0.35); padding: 12px; border-radius: 8px; overflow-x: auto; }}
</style>
</head>
<body>

<h1>EAGLE Best Picks &amp; Research Index (2026-06-02)</h1>
<p class="meta">Goal #1 · Swarm-reviewed via LiteLLM proxy · Sources: <code>money_ready_verdict.json</code>, <code>ai_tournament_leaderboard.json</code>, <code>EAGLE3_2026-06-02_minimax-m3-free.MD</code>, lab report · <a href="/updates/">← Updates</a> · <a href="/audit/">/audit</a></p>

<div class="callout">
  <strong>Capital rule:</strong> Zero asset classes pass production Money Ready (<code>summary.money_ready: []</code>). Tournament and lab numbers are <em>research surfaces</em> — do not size live capital from them without forward n≥100 + policy-clean gates.
</div>

<h2>1. Three surfaces (do not mix them)</h2>
<table>
  <tr><th>Surface</th><th>What it measures</th><th>Today's verdict</th></tr>
  <tr><td><a href="/audit/">/audit</a> production</td><td>Closed picks after resolver + policy-clean filters</td><td><span class="badge no">0/9 money-ready</span> CRYPTO PF 0.92 n=368; EQUITY PF 0.33 n=52</td></tr>
  <tr><td><a href="/audit/ai-tournament.html">AI tournament</a></td><td>Paper portfolios per LLM model (Wilson WR × bootstrap PF)</td><td><span class="badge paper">Best paper:</span> deepseek_v4 WR 57.7% PF 3.46 n=208</td></tr>
  <tr><td>Verified lab + paper pilot</td><td>OHLCV backtest + walk-forward OOS</td><td><span class="badge shadow">etf_dual_momentum</span> lab PF 1.60 n=104; live ETF n=3</td></tr>
</table>

<h2>2. Best possible picks (evidence-bound)</h2>
<table>
  <tr><th>Pick / sleeve</th><th>Tier</th><th>Why we cite it</th><th>Key stats</th></tr>
  <tr><td><strong>deepseek_v4</strong> tournament book</td><td><span class="badge paper">PAPER WATCH</span></td><td>Top rank on leaderboard with n≥30 gate; not wired to production sizing</td><td>WR 57.7%, PF 3.46, n=208 resolved</td></tr>
  <tr><td><strong>gpt4o</strong> tournament book</td><td><span class="badge paper">PAPER WATCH</span></td><td>#2 rank-eligible model; same caveats as above</td><td>WR 59.7%, PF 3.14, n=134</td></tr>
  <tr><td><strong>CRYPTO SHORT</strong> (BTC/ETH)</td><td><span class="badge paper">PAPER WATCH</span></td><td>EAGLE3: production emits LONG (33% WR) while tournament SHORT is 67% WR n=216 — flip in <code>production_scanner.py</code> is shadow, not promoted</td><td>SHORT 67% vs LONG 33%</td></tr>
  <tr><td><strong>ETF:</strong> EEM, IWM, GLD</td><td><span class="badge paper">PAPER WATCH</span></td><td>EAGLE3 symbol whitelist on tournament resolved picks; production ETF only n=3</td><td>EEM 93%, IWM 75%, GLD 68% (EAGLE3 table)</td></tr>
  <tr><td><strong>EQUITY:</strong> BAC, JPM, MSFT, NVDA</td><td><span class="badge paper">PAPER WATCH</span></td><td>EAGLE3 LONG-only bias in tournament; production EQUITY book fails gates</td><td>Prod EQUITY WR 26.9% PF 0.33</td></tr>
  <tr><td><strong>etf_verified_dual_momentum</strong></td><td><span class="badge shadow">SHADOW PILOT</span></td><td>Only lab Tier-2 pass in multi-class lab; WF OOS PASS; forward log until n≥30</td><td>Lab PF 1.60 WR 53.8% n=104; OOS PF 1.21 n=32</td></tr>
  <tr><td><strong>/audit Smart Picks</strong> (all classes)</td><td><span class="badge no">DO NOT SIZE</span></td><td>Policy-clean money_ready empty; recency panels can diverge from headline WR</td><td>See production table below</td></tr>
</table>

<h2>3. Production /audit stats (why each number is shown)</h2>
<table>
  <tr><th>Class</th><th>n</th><th>WR</th><th>PF</th><th>Verdict</th><th>Action</th></tr>
  {prod_rows}
</table>
<p><em>Source:</em> <code>audit_dashboard/data/money_ready_verdict.json</code> generated {_esc(mr.get('generated_at', '?'))}. We show <strong>n_resolved</strong> because Tier-2 requires enough closed trades; <strong>PF</strong> (profit factor) because it captures tail risk better than WR alone; <strong>verdict</strong> because it bundles DSR/SPA/MDD gates.</p>

<h2>4. Tournament leaderboard (paper only)</h2>
<table>
  <tr><th>Model</th><th>n resolved</th><th>WR</th><th>PF</th><th>Tier</th><th>Action</th></tr>
  {model_rows}
</table>
<p><em>Source:</em> <code>audit_dashboard/data/ai_tournament_leaderboard.json</code>. Rank score = Wilson lower-bound WR × bootstrap lower-bound PF. High PF here does <strong>not</strong> override production NOT_READY.</p>

<h2>5. Feedback points — full explanation + ELI5</h2>

<h3>5.1 Zero money-ready classes</h3>
<p><strong>Full:</strong> <code>money_ready_verdict.json</code> lists <code>summary.money_ready: []</code>. Every class must pass WR, PF, n, DSR, SPA, and drawdown gates simultaneously. CRYPTO and EQUITY have enough n to fail honestly (NOT_READY); others lack n (INSUFFICIENT_DATA).</p>
<div class="eli5"><strong>ELI5:</strong> The report card has no “A” grades yet — so we don’t bet the house on any single asset class from the main dashboard.</div>

<h3>5.2 Tournament ≠ production</h3>
<p><strong>Full:</strong> Tournament picks live in a parallel DB/book with model personas and faster resolution. Production picks flow through <code>production_scanner</code>, battleground, gates, and resolver fixes. A model can show PF 3.4 on paper while production CRYPTO PF is 0.92.</p>
<div class="eli5"><strong>ELI5:</strong> Practice game stats don’t automatically count in the real league — different players, different rules.</div>

<h3>5.3 Why we cite PF and WR together</h3>
<p><strong>Full:</strong> WR alone hides payoff asymmetry (FOREX had pretty WR with bad PF historically). PF &lt; 1 means losers outweigh winners in dollar terms. We require both for Tier-2 per hedge-fund review tier table in CLAUDE.md.</p>
<div class="eli5"><strong>ELI5:</strong> Winning often but with tiny wins and huge losses is still losing money — PF catches that; win rate alone does not.</div>

<h3>5.4 CRYPTO SHORT flip (EAGLE3)</h3>
<p><strong>Full:</strong> EAGLE3 analyzed 216 resolved CRYPTO tournament picks: SHORT 67% WR vs LONG 33%. Production still emits LONG-heavy CRYPTO. EAGLE-4 admissibility can flip direction in scanner — that is a <em>mutation</em>, not proof of live edge until 14d/48h panels confirm.</p>
<div class="eli5"><strong>ELI5:</strong> Our crypto picks were often betting “up” when the scoreboard says “down” worked better — fixing direction is step one, not permission to go all-in.</div>

<h3>5.5 ETF dual momentum shadow sleeve</h3>
<p><strong>Full:</strong> Lab harness reports PF 1.60, n=104, walk-forward OOS PF 1.21 (PASS). Live production ETF class has n=3 — far below promotion threshold. Paper pilot logs to <code>verified_strategies/paper_pilot/etf_dual_momentum_paper_log.jsonl</code>; flag stays OFF until forward criteria in <code>updates/2026-05-31-etf-promotion-path.md</code>.</p>
<div class="eli5"><strong>ELI5:</strong> This ETF strategy passed homework (backtest) but hasn’t enough real homework days (forward trades) to join the live team.</div>

<h3>5.6 Bonferroni / multiple testing</h3>
<p><strong>Full:</strong> Scanning hundreds of symbols × models × directions without multiplicity control inflates false discoveries. EAGLE swarm used DSR/SPA framing; SPA failed on CRYPTO (spa_p 0.59). Treat symbol whitelist rows as <em>hypotheses</em> until pre-registered (M-107).</p>
<div class="eli5"><strong>ELI5:</strong> If you try enough guesses, one looks brilliant by luck — we discount “winners” found after trying many combos.</div>

<h3>5.7 Pick funnel “78% CRYPTO” dispute</h3>
<p><strong>Full:</strong> Funnel headline can disagree with policy-clean DB (duplicate signal-ts, resolver labels, concentration in one source). Always read <code>asset_class_health</code> + 14d/48h recency panels before sizing.</p>
<div class="eli5"><strong>ELI5:</strong> The big marketing number on the funnel page can be wrong — check the detailed scoreboard before trusting it.</div>

<h2>6. LiteLLM swarm review (automated second check)</h2>
{swarm_html}
<p><em>Artifact:</em> <code>reports/best_picks_swarm_review_2026-06-02.json</code> · Re-run: <code>python3 tools/verify_best_picks_swarm.py</code></p>

<h2>7. EAGLE*.MD* file index ({len(eagle_files)} files)</h2>
<ul class="files">
{eagle_li}
</ul>

<h2>8. Recent planning &amp; session docs ({len(plans)} listed)</h2>
<ul class="files">
{plan_li}
</ul>

<h2>9. Reproducers</h2>
<pre><code>python3 tools/verify_best_picks_swarm.py
python3 tools/eagle_swarm_synthesis.py
python3 tools/generate_eagle_best_picks_guide.py
VERIFY_SKIP_FRED=1 python3 tools/multi_class_strategy_lab.py
python3 verified_strategies/paper_pilot/etf_dual_momentum_pilot.py --one-shot
curl -s "https://findtorontoevents.ca/audit/data/money_ready_verdict.json" | python3 -m json.tool | head -40</code></pre>

</body>
</html>
"""
    OUT.write_text(body, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
