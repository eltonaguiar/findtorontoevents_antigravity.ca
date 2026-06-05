# Edge Hunt — 6 Subagents, All Asset Classes (2026-06-05)

## What we did

Deployed **6 parallel subagents** (CRYPTO, EQUITY, ETF, FOREX, COMMODITY, BOND) to find the fastest defensible path to real-money statistical edge — without waiting months for forward n→100 alone.

Each agent grounded stats in:
- `audit_dashboard/data/pf_registry.json`
- `audit_dashboard/data/money_ready_verdict.json`
- Live MySQL (`at_pick_outcomes`, `trading_picks`)
- Earnings cache (`data/earnings/*/latest.json`), UEPS, backtest reports, paper pilots

## Headline

**0/6 classes are MONEY_READY** (correct gate behavior).

**Only two sleeves are tradeable at micro size this week:**

| Sleeve | Class | n | WR | PF | Source |
|--------|-------|---:|---:|---:|--------|
| `crypto_liquidity_wick_reversal_v1` | CRYPTO | 30 | 60% | 1.55 | pf_registry policy_clean |
| `MeanReversionBB` | EQUITY | 214 | 55.6% | 1.88 | `at_pick_outcomes` (not in pf_registry!) |

## Critical gap

**MeanReversionBB** clears Tier-2 on n/WR/PF in `at_pick_outcomes` but **does not appear in `pf_registry.json`** — so `money_ready_verdict` `top_sleeves` cannot surface it. Class EQUITY still shows INSUFFICIENT_DATA (n=45 policy_clean, poisoned by `regime_terminal`).

**Action:** Extend `_top_money_ready_sleeves()` to merge resolver-grade `at_pick_outcomes` stats OR backfill MeanReversionBB into pf_registry recompute.

## Per-class reports

- `reports/edge_hunt_ALL_CLASSES_2026-06-05.md` — synthesis
- `reports/edge_hunt_{CRYPTO,EQUITY,ETF,FOREX,COMMODITY,BOND}_2026-06-05.md`

## Week-1 playbook

1. **CRYPTO:** 0.25× on `crypto_liquidity_wick_reversal_v1` only; paper `mega_mutation` (unblock ~Jun 12).
2. **EQUITY:** Block `regime_terminal`; isolated MeanReversionBB paper book at 0.25×.
3. **ETF:** Keep `etf_verified_dual_momentum` pilot; no live sizing until Jul checkpoint.
4. **FOREX:** Extend carry backtest n≥30; stay HARD_DISABLE.
5. **COMMODITY / BOND:** 0% sizing; wire orphan bond backtests + term_cot paper.

## Reproduce

```bash
python3 tools/strategy_tier_tracker.py --min-n 15
PYTHONPATH=. python3 alpha_engine/money_ready_verdict.py --json
```
