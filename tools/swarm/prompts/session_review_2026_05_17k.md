# Session Review — 2026-05-17 Round 11

## Context
Quant/systems review. Final round of the 2026-05-17 extended session (rounds 1-10 previously reviewed). This round covers work done after goal session j was marked ACHIEVED.

## Session Deliverables (this round)

### 1. PR #1132 Test Fix — SHIPPED
- Branch: `fix/c1bc-d2-resolver`
- Fix: updated `test_crypto_unaffected_by_v2_path` assertion from `exit_price==51000.0` to `exit_price==51500.0`
- Rationale: C1 Path B/C correctly uses `live_price` (the actual observed fill price) instead of nominal TP as exit. The old assertion expected TP price, but that was the ghost-row artifact being fixed.
- Updated test comment to explain new semantics
- 29/29 tests pass; 91/91 quality_gates pass
- Force-pushed rebased branch to origin (branch was behind main by 67 commits from other merged work)

### 2. Swarm Worker 2000-char Cap Removed — SHIPPED to main
- `tools/swarm/worker_runner.py`: two fixes from `reports/swarm_largetext_audit_2026-05-17.md` (FIX 1)
  - `_strip_code_fences()`: added secondary `re.search` pass for preamble-before-fence patterns (kilo/groq emit "Here's the JSON:\n```json\n{...}\n```"). Old code used `re.match` which only fires when the WHOLE string is a code fence.
  - Removed `raw[:2000]` cap in parse-fail fallback. `commentary_text` now carries full engine output. Added `_parse_status="non_json_fallback"` for downstream detection.
- Impact: eliminates 8-item plan answers cut at item 4, half-reviews from kilo/groq/deepseek-r1 engines that wrap JSON in code fences or have reasoning preambles.
- Verified with 3 unit tests: preamble-before-fence, plain-preamble, clean JSON all pass.
- Commit: eb323248b9 (rebased to 47eb687f5f)

### 3. M-053 Stat Validation — COMPLETE
- 2-engine swarm (deepseek + claude) validated dashboard_data.json numbers
- **COMMODITY WR=85.5% SUSPICIOUS**: Both engines flag survivorship bias. Raw data: n=354, WR=60.2%. Dashboard: n=228, WR=85.5%. 126 picks excluded by `_is_valid_resolved_pick()` filter (likely losers with corrupt/missing pnl_pct). The NG=F (0% WR, n=24) and CL=F (19% WR, n=47) picks are in the raw data but many lack valid pnl_pct → excluded from health calc.
- **FOREX WR/PF paradox explained**: wins average 0.62% return vs losses averaging 1.00% (tight-TP / wide-SL). Total PnL=-15.84%. Classic structural issue, not a data artifact.
- **Verified tier classification**: EQUITY T2 confirmed (PF=1.65, WR=53.2%, n=393). ETF T1 candidate (n=75, below charter floor).
- **Systemic risk**: realized_n_30d=0 across ALL classes — circuit breaker layer has no live 30d data, all 'stable' labels are unvalidated.

### 4. PR #1125 Closed as Stale
- Cherry-pick failed: files the PR edits (`reports/DAILY_IDEAS_COMMODITY_CLAUDE_May162026.MD`, `DAILY_IDEAS_PROMPTS.MD`) were deleted/restructured in main.
- Core finding (multi_asset_cot direction is SHORT) already captured in `reports/mutation_investigation_2026_05_17.md` and `BLOCKED_DIRECTION_TRIPLES`.

### 5. PR #1136 Confirmed Merged
- `feat(scanner): persist oi_change_24h into ml_features_at_entry` — merged by another agent. OI data now accumulates for future ML feature addition.

### 6. PR #1137 (yfinance) — CI Pending
- Tests 3.11 + 3.12 pass; Gitleaks still running.

## Swarm Questions

1. **COMMODITY survivorship bias**: `_is_valid_resolved_pick()` excludes ~126 picks (likely losers) producing WR=85.5% vs raw WR=60.2%. Should we add a warning to the dashboard when post-filter n < 70% of raw n for a class? This would surface the gap to dashboard users.

2. **realized_n_30d=0 cold-start**: All circuit breaker 'stable' labels are unvalidated. Is there a simple fix (e.g., compute realized_n_30d from closed_picks.json where close_date is within 30d of dashboard generation)?

3. **FOREX structural fix**: WR=57.8% but PF=0.85 due to win/loss size asymmetry. Is this fixable by changing TP:SL ratio on FOREX picks, or is it inherent to the underlying strategies (copytrader signal)?

4. **PR #1132 status**: The test fix is on the branch. The underlying C1 Path B/C PR needs to be re-reviewed — it also reverts the gap-aware OHLC fill from `_scan_ohlc_for_touch` that was added in PR #1130. Should the C1 Path B (live_price as exit) and the OHLC revert be in separate PRs?

5. **Swarm worker fix validation**: The preamble-before-fence recovery change was shipped. Should we run a known-fenced-output test to confirm kilo/groq responses now parse correctly (vs the previous 2000-char truncation)?

## Format
```json
{
  "verdict": "DONE | MOSTLY_DONE | NEEDS_WORK",
  "commodity_bias_warning": "ADD_DASHBOARD_WARNING | DOCUMENT_ONLY | NO_ACTION",
  "realized_n30d_fix": "COMPUTE_FROM_CLOSED_PICKS | DEFER | NO_ACTION",
  "forex_structural_fix": "CHANGE_TP_SL_RATIO | MUTATION_ONLY | DEFER",
  "pr_1132_split_recommendation": "SPLIT_PRs | KEEP_COMBINED | NO_OPINION",
  "swarm_worker_validation": "RUN_TEST | TRUST_UNIT_TESTS | DEFER",
  "remaining_code_actionable": ["any items missed"],
  "summary": "one paragraph"
}
```
