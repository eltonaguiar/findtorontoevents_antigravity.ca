# Per-Asset-Class Candidate Trade Sets — 2026-05-18

**Goal:** answer "find a profitable set of trades for each asset class" from the
canonical deduped ledger (`pf_registry.json::by_asset_class_strategy_policy_clean_net`).
**Method:** rank strategies per class by profit factor on policy-clean,
net-of-slippage data; exclude known artifacts (`ml_enhanced_*` placeholder-stat
family, `multi_asset_copytrader` CT=F COT-leakage, `copy_trader_intel` 0%-WR).

## Honest framing — read first

A "profitable set of trades" here means **a cohort that made money in the
historical deduped ledger**. That is NOT the same as proven edge. The
`edge_stability_harness` exists precisely to test whether in-sample profit
survives forward — and 11 pre-registered hypotheses failed it
(`EDGE_HUNT_EXHAUSTED_2026-05-18.md`). So everything below is labelled
**IN-SAMPLE profitable / forward-UNPROVEN**. Paper-trade it; the forward result
is the real verdict.

## CRYPTO — candidate set EXISTS (in-sample)

| cohort | n | PF | WR | total pnl% | assessment |
|--------|---|----|----|-----------|------------|
| `mega_mutation` | 72 | 2.19 | 56.9% | +110.4% | **best balance** — healthy avg-win/avg-loss ≈1.66 (not a placeholder artifact); n too small for a harness verdict (~1 window) |
| `ensemble` | 410 | 1.47 | 41.5% | +184.9% | most data; harness-tested earlier = **zero per-window separation** (volume, not edge) — profit is regime-dependent |
| `st_rsi_vol_bounce` | 16 | 2.43 | 56.2% | +5.9% | speculative — n=16 |
| `crypto_soc_micro_noise_filter_a09` | 18 | 2.63 | 61.1% | +9.3% | speculative — n=18 |

Excluded: `UNKNOWN` n=24 PF 145 / WR 4.2% — classic one-giant-win placeholder
artifact, not tradeable.

**CRYPTO candidate set:** trade `mega_mutation` picks (highest PF at usable n),
secondarily `ensemble`. Paper only. The forward win-rate over the next ~8-10
weeks IS the test — if `mega_mutation` holds PF>1.5 across ≥5 walk-forward
windows it becomes the first real edge; if it sign-flips it joins the kill log.

## COMMODITY / EQUITY / ETF / BOND / FUTURES — NO candidate set exists

Zero profitable non-artifact cohorts at even n≥15 in the canonical ledger:

| class | best non-artifact cohort | verdict |
|-------|--------------------------|---------|
| COMMODITY | none n≥15 (only `multi_asset_copytrader` = CT=F COT-leakage artifact) | no set |
| EQUITY | none n≥15 | no set |
| ETF | none n≥15 | no set |
| BOND | none n≥15 | no set |
| FUTURES | none n≥15 | no set |
| FOREX | `alpha_engine` n=39 PF 0.56 WR 28.2% | losing — no set |

**Root cause is pick VOLUME, not strategy.** These classes have not generated
enough clean, deduped, resolved picks to even form a 15-trade cohort. You cannot
filter a profitable set out of a near-empty bucket. The fix is upstream:

1. **Non-crypto forward-resolution is broken** (UNCLAIMED P0) — picks are
   emitted but never resolved to WON/LOST, so they never enter the clean ledger.
   Fix this first or these classes stay empty forever.
2. Expand the non-crypto traded universe + emission rate.
3. Only after n≥100 clean resolved picks per class can a candidate set be
   ranked at all.

## Bottom line

- **CRYPTO:** a candidate set exists — `mega_mutation` + `ensemble`. In-sample
  profitable, forward-unproven. Paper-trade and let the harness verdict accrue.
- **Other 5 classes:** there is nothing to select. The honest action is not
  "find a strategy" — it is **fix the non-crypto resolution pipeline** so clean
  picks accumulate. Until then, per-class profitable sets for COMMODITY/EQUITY/
  ETF/BOND/FUTURES cannot exist regardless of strategy work.

*Source: `audit_dashboard/data/pf_registry.json` policy-clean-net view.
Cross-ref: `EDGE_HUNT_EXHAUSTED_2026-05-18.md`, `DEEP_DIVE_MONEYREADY_2026-05-18.md`.*
