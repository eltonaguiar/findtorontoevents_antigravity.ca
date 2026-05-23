# Session Review — 2026-05-17 Round 12 (Final)

You are a quant systems reviewer. Evaluate the session deliverables and answer all 5 swarm questions with a structured JSON verdict.

## Session Deliverables
1. GSD Scanner CI Fix — added `if: github.ref == 'refs/heads/main'` to "Commit updated picks" step in `crypto-ml-edge.yml`. Commit `7a4046914a`. Clears PR #1132 scan: FAILURE.
2. PR #1132 CI Re-Running — `fix/c1bc-d2-resolver` rebased onto main, force-pushed. CI in progress. Combines: (a) live_price as exit for C1 Path B/C, (b) OHLC gap-aware fill revert from `_scan_ohlc_for_touch`. 29/29 tests pass locally.
3. PR #1137 MERGED — 6 undeclared deps (yfinance, pymysql, redis, etc.)
4. PR #1125 Closed as Stale — core SHORT finding preserved in `reports/mutation_investigation_2026_05_17.md`
5. PR #1139 Open (tracking-only) — CRYPTO recovery (PF=0.21→1.142), EQUITY 7d PF=0.682 with 11/22 picks pnl=0 status=OPEN (unresolved)

## Still Blocked (external)
- MySQL ghost-row purge (655k rows) — PA console required
- UEPS_ENABLE_PEAD=1 prod .env verification — PA console required
- Issue #1095 FRED_API_KEY secret — manual GH secret required

## Time-Gated
- META_LABEL_GATE_ENFORCE=1: ~2026-06-16 (WR≥55% × 30 days)
- EQUITY_CONVICTION_TIERS=1: 2026-06-15
- NUQL_GATE_ENFORCE=1: 2026-06-16
- FOREX_COPYTRADER_ENABLE=1: when non-JPY-cross n≥30

## Swarm Questions

**Q1 — PR #1132 split?**
The PR combines two logically independent changes: (a) live_price as exit for C1 B/C, (b) OHLC gap-aware fill revert from `_scan_ohlc_for_touch`. 29/29 tests pass, CI already running. Should it be SPLIT into separate PRs or KEEP_COMBINED? Consider: splitting adds CI re-run cost + rebase churn; keeping combined risks conflating unrelated regressions if one change later needs revert.

**Q2 — EQUITY 7d pnl=0 filter?**
7d window shows PF=0.682. 11 of 22 picks have pnl_pct==0 AND status==OPEN (unresolved — exit not yet triggered). These dilute the settled-trade signal. Options: FILTER_UNRESOLVED (exclude pnl=0+OPEN from 7d metric so it reflects only settled trades), DASHBOARD_NOTE (add banner "X picks unresolved — metric understates real PF"), or DEFER (do nothing, accept noisy metric).

**Q3 — PR #1139 disposition?**
Tracking-only hourly audit PR (no code changes). 5 direction-asymmetry candidates documented, but ALL already appear in BLOCKED_DIRECTION_TRIPLES in quality_gates.py. Options: MERGE (preserve audit trail in git history), CLOSE (findings already actioned, PR is redundant noise), DEFER (leave open as reference).

**Q4 — Swarm worker live validation?**
The preamble-before-fence fix (secondary re.search pass recovering JSON inside triple-backtick fences after prose preamble) was shipped with unit tests on synthetic strings only. Should we RUN_TEST with a known-fenced real engine response before next scheduled swarm run, TRUST_UNIT_TESTS (synthetic coverage is sufficient), or DEFER?

**Q5 — Circuit breaker min_n?**
Charter drift circuit breaker WON/LOST fix landed (was reading wrong field). On next dashboard gen, realized_n_30d will be non-zero for classes with recent closed picks. What is the minimum n before a circuit breaker verdict should be considered reliable? Default is 30. For small-n classes like BOND (n=18 total) and ETF (n=87 total, ~20-25/30d), is 30 appropriate, too high, or too low? Recommend a specific integer and rationale.

## Required Output Format
Respond ONLY with valid JSON (no prose before or after):
```json
{
  "verdict": "DONE | MOSTLY_DONE | NEEDS_WORK",
  "pr_1132_split_recommendation": "SPLIT_PRs | KEEP_COMBINED | NO_OPINION",
  "equity_7d_pnl0_filter": "FILTER_UNRESOLVED | DASHBOARD_NOTE | DEFER",
  "pr_1139_disposition": "MERGE | CLOSE | DEFER",
  "swarm_worker_live_validation": "RUN_TEST | TRUST_UNIT_TESTS | DEFER",
  "circuit_breaker_min_n": 20,
  "remaining_code_actionable": ["list any code-actionable items missed in session"],
  "summary": "one paragraph covering session completeness and top open risk"
}
```
