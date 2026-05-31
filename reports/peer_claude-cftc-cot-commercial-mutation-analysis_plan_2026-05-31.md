# Plan — INCIDENT_COMMODITIES #1: cftc_cot_commercial_signal mutation analysis

**Slug:** cftc-cot-commercial-mutation-analysis
**Date:** 2026-05-31
**AI Provider:** Qwen (`qwen-max` via dashscope-intl)

## Incident
`cftc_cot_commercial_signal` was BLOCKED with "19% WR on n=16" per INCIDENT_COMMODITIES #1.

## Live state read (DB ejaguiar1_stocks.trading_picks, 2026-05-31)
Full lifetime (commodity category):
- Total: 37 picks
- TP_HIT: 3 (2 SHORT, 1 LONG) — avg PnL +3.4%
- LOST: 2 (both SHORT) — avg PnL -5.08%
- TIME_EXIT: 30 (26 SHORT, 4 LONG) — pnl=0 (washes)
- OPEN: 2 SHORT

**Resolved/decisive WR** (TP_HIT + LOST only, excluding TIME_EXIT washes): **3/5 = 60.0%**
**All-closed WR** (treating TIME_EXIT as 0-pnl): 3/35 = 8.6%

The "19% / n=16" figure from the incident is a 7d window snapshot from `HOURLY_AUDIT_2026-05-20_07Z.md` and `weekly_filter_2026-05-17.md` showing 51.6% concentration in this strategy (n=20, WR=5.0%, PF=0.113 -65.79% sum, 7d). Distinct from the lifetime view.

**Key observation:** 30/37 = 81% of picks expire at TIME_EXIT with pnl=0 → strategy is signalling but exits never materialize. TP_HIT cases are 4.5-5% gains (good), LOSSes -4.5 to -5.7% (slightly worse than wins). The mass of zero-pnl TIME_EXITs indicates **wrong holding-period / exit-rule axis**, not entry-axis edge failure.

## Existing safeguards in code (audit_trail/quality_gates.py)
- COT_DEDUP_SYSTEMS includes the strategy with 72h dedup window (~one CFTC cycle).
- M-046 (line 9824): COMMODITY single-source concentration cap (30% default, OFF unless `COMMODITY_SOURCE_CAP=1`).
- Negative score weight applied when paired with multi_asset_copytrader (-10 in `calculate_smart_score`).
- NOT in `PERMANENTLY_KILLED_STRATEGIES` set (line 1370) — still admissible.
- NOT in `BLOCKED_STRATEGIES` set (line 2122) — still admissible.

## File paths to act on
- Docs: `reports/peer_claude-cftc-cot-commercial-mutation-analysis_2026-05-31.md`
- Qwen response: `reports/peer_claude-cftc-cot-commercial-mutation-analysis_qwen_consult_2026-05-31.md`
- Optional code: `audit_trail/quality_gates.py` line 1370 (`PERMANENTLY_KILLED_STRATEGIES`)

## Approach
1. Send Qwen the strategy purpose, full DB breakdown, and the three-axis mutation protocol prompt.
2. Save Qwen's full response verbatim.
3. Compose docs PR with Qwen's analysis + my recommendation.
4. **Defer code change** for human review — small sample (n=5 decisive), and TIME_EXIT pattern suggests exit-rule mutation could rescue the strategy; permanent kill is premature without that test.

## Risk
- Premature retirement loses a fundamental positioning signal (COT data is institutional-grade source).
- Small decisive sample (n=5) makes WR statistically meaningless either way.

## Decision
PROCEED with docs-only PR. Defer code change.
