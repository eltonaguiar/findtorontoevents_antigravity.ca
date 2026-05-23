# Session Review — 2026-05-17 Round 11

You are a quant systems reviewer. Return ONLY valid JSON — no code fences, no preamble, no explanation outside the JSON object.

## Deliverables completed this round:
1. PR #1132 test fix: assertion updated exit_price 51000→51500 (live_price vs nominal TP). 29/29 tests pass.
2. Swarm worker: preamble-before-fence recovery + removed 2000-char cap. Verified 3 unit tests.
3. M-053 stat validation: COMMODITY WR=85.5% (post-filter, n=228) vs 60.2% (raw, n=354). 126 picks excluded by _is_valid_resolved_pick(). FOREX structural issue confirmed (win avg 0.62% vs loss avg 1.00%). EQUITY T2 confirmed (PF=1.65, WR=53.2%, n=393). realized_n_30d=0 across ALL classes.
4. PR #1125 closed stale (cherry-pick failed, finding captured in mutation_investigation doc).
5. PR #1136 merged (oi_change_24h persisted in ml_features_at_entry).
6. PR #1137 (yfinance) CI pending — Gitleaks still running.

## Five questions requiring verdict:

Q1 COMMODITY_BIAS_WARNING: _is_valid_resolved_pick() excludes ~126 picks producing WR=85.5% vs raw 60.2% — a 25pp survivorship gap. Should we add a dashboard warning when post-filter n < 70% of raw n for a class? This would surface the gap to dashboard users.
Options: ADD_DASHBOARD_WARNING | DOCUMENT_ONLY | NO_ACTION
Consideration: The warning adds transparency but may alarm users; DOCUMENT_ONLY captures it in reports without UI noise.

Q2 REALIZED_N30D_FIX: All circuit breaker 'stable' labels are unvalidated because realized_n_30d=0 across all classes. Simple fix: compute realized_n_30d from closed_picks.json where close_date is within 30d of dashboard generation time.
Options: COMPUTE_FROM_CLOSED_PICKS | DEFER | NO_ACTION
Consideration: Fix is 1-2 lines of Python; risk is misclassifying classes if closed_picks schema has gaps.

Q3 FOREX_STRUCTURAL_FIX: WR=57.8% but PF=0.85 due to win avg 0.62% vs loss avg 1.00% asymmetry. Total PnL=-15.84%. Is this fixable by changing TP:SL ratio on FOREX picks, or is it inherent to the underlying copytrader signal structure?
Options: CHANGE_TP_SL_RATIO | MUTATION_ONLY | DEFER
Consideration: TP:SL ratio change is a parameter tweak but may invalidate historical comparison; MUTATION_ONLY means run the 3-axis protocol before any code change; DEFER means leave FOREX disabled and monitor.

Q4 PR_1132_SPLIT: Branch fix/c1bc-d2-resolver currently combines (a) C1 Path B using live_price as exit_price and (b) reverting the gap-aware OHLC fill from _scan_ohlc_for_touch added in PR #1130. These are logically separable concerns.
Options: SPLIT_PRs | KEEP_COMBINED | NO_OPINION
Consideration: Splitting improves reviewability and bisectability; keeping combined avoids coordination overhead for two interdependent changes.

Q5 SWARM_WORKER_VALIDATION: The preamble-before-fence fix (re.search secondary pass + removed 2000-char cap) was shipped with 3 unit tests covering preamble-before-fence, plain-preamble, and clean JSON. Should we run a live kilo/groq test to confirm real engine output now parses, or trust the unit tests?
Options: RUN_TEST | TRUST_UNIT_TESTS | DEFER
Consideration: RUN_TEST catches real-world encoding edge cases unit tests miss; TRUST_UNIT_TESTS is sufficient if tests cover the actual preamble patterns those engines emit.

## Return ONLY this JSON (fill in your answers):
{
  "verdict": "DONE | MOSTLY_DONE | NEEDS_WORK",
  "commodity_bias_warning": "ADD_DASHBOARD_WARNING | DOCUMENT_ONLY | NO_ACTION",
  "realized_n30d_fix": "COMPUTE_FROM_CLOSED_PICKS | DEFER | NO_ACTION",
  "forex_structural_fix": "CHANGE_TP_SL_RATIO | MUTATION_ONLY | DEFER",
  "pr_1132_split_recommendation": "SPLIT_PRs | KEEP_COMBINED | NO_OPINION",
  "swarm_worker_validation": "RUN_TEST | TRUST_UNIT_TESTS | DEFER",
  "remaining_code_actionable": ["list any missed action items from the deliverables above"],
  "summary": "one paragraph verdict on round 11"
}
