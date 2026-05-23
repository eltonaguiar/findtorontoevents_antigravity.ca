# Cursor ↔ Claude Fact-Check & Agreement

**Date:** April 14, 2026  
**Last Updated:** 9:56 PM EDT  

## Context

Cursor and Claude (Antigravity bot) independently analyzed the trading system's performance and initially produced contradictory results. After mutual fact-checking and self-correction, both agents converged on a shared set of verified findings.

## Data Sources Used

| File | Content | Use For |
|------|---------|---------|
| `audit_trail/data/universal_resolved_picks.json` | 4,309 crypto-only picks, 3 clean exit reasons | **Per-system metrics (authoritative for crypto)** |
| `audit_dashboard/data/dashboard_data.json` | 3,500 multi-asset picks, 232 exit reasons | **Asset-class breakdown (only multi-asset file)** |
| `alpha_engine/data/closed_picks.json` | 4,157 picks, 82% quan_engine_scalp, 738 MATIC ghosts | **Do NOT use for system-wide analysis** |

## Where Both Agents Agree (Verified)

### System-Level (from universal_resolved_picks.json)

| System | n | WR | PF | Cum PnL | Cursor | Claude | Agree? |
|--------|---|-----|-----|---------|--------|--------|--------|
| quan_engine | 733 | 72.6% | 6.39 | +1,101% | 72.6% / 6.39 | 72.4% / 6.35 | YES |
| predictions | 344 | 66.0% | 2.72 | +396% | 66.0% / 2.72 | 66.0% / 2.72 | YES |
| ml_crypto_pred | 437 | 31.6% | 0.70 | -181% | 31.6% / 0.70 | 31.6% / 0.70 | YES |
| claude_gainer_st | 84 | 21.4% | 0.55 | -41% | 21.4% / 0.55 | 21.4% / 0.55 | YES |
| kimi_signal_tracking | 380 | 33.4% | 0.91 | -46% | 33.4% / 0.91 | 32.7% / 0.90 | YES (minor delta) |
| signal_validation | 140 | 57.1% | 2.11 | +108% | 57.1% / 2.11 | 57.6% / 2.16 | YES |
| luxalgo_filters | 217 | 43.3% | 1.43 | +73% | 43.3% / 1.43 | 43.7% / 1.46 | YES |
| dna_winner_picks | 327 | 44.6% | 1.48 | +116% | 44.6% / 1.48 | 44.6% / 1.48 | YES |
| battleground | 40 | 20.0% | 0.56 | -14% | 20.0% / 0.56 | *(different)* | PARTIAL |

### Structural Findings (Both Agree)

1. **Timeouts are net positive** — force-closing winners (universal: PF=2.50 on timeouts)
2. **Production book is 99.5%+ crypto** — non-crypto filter stack has no data to operate on
3. **dashboard_data.json has tag-aliasing** at the per-system level (PR #160 pattern)
4. **closed_picks.json has 738 MATIC ghosts** — universal has zero
5. **Ledger overlap is <2.5%** — they contain almost entirely different picks
6. **Trend is U-shaped**, not monotonically declining (newest third recovered)
7. **kimi_signal_tracking correctly blocked** — both verify PF=0.91, losing
8. **claude_gainer_st is losing** — both verify PF=0.55, -41% (dashboard showed 2.20 due to tag-aliasing)
9. **91% of cumulative PnL comes from 2 systems** — quan_engine + predictions

### Defensible Actions (Both Agree)

| Action | Cursor | Claude | Evidence |
|--------|--------|--------|----------|
| Boost luxalgo_filters | YES | YES | PF 1.43, n=217, +73% |
| Boost signal_validation | YES | YES | PF 2.11, n=140, +108% (currently wrongly blocked) |
| Boost dna_winner_picks | YES | YES | PF 1.48, n=327, +116% |
| Boost predictions | — | YES | PF 2.72, n=344, +396% |
| Investigate hold-time extension | YES | YES | Timeouts are net positive on both ledgers |
| Keep kimi_signal_tracking blocked | YES | YES | PF 0.91, -46% |
| Do NOT boost claude_gainer_st | YES | YES | PF 0.55, -41% (tag-aliasing artifact) |

### Where Agents Disagree

| Topic | Cursor | Claude | Resolution |
|-------|--------|--------|------------|
| battleground WR | 20.0% (strict match) | 42.5% (broader match?) | **Needs investigation** — Claude may match variants, Cursor strict exact |
| revival_all reliability | Not assessed | PF 32.48 flagged as inflation suspect | **Agree to flag** — n=81, suspiciously high |

## Bug Fixes in This PR

1. **`validation_metrics.js:81`** — `{ cost }` → `{ total: cost }` (transaction costs never applied)
2. **`dashboard_generator.py:9287`** — permutation win/loss uses `_outcome_bucket_from_pnl()` instead of raw `pnl > 0` (zero-PnL counted as losses)
3. **`quality_gates.py:838`** — unblock `signal_validation` (stale block: was 10 trades/0% WR, now 140 trades/57.1% WR/PF 2.11)
