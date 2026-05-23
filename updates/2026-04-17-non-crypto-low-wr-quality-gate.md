# Non-Crypto Low Win-Rate Investigation + Mitigation

Date: 2026-04-17

## Problem
Non-crypto sections on the audit dashboard were showing weak quality in some clusters (especially specific strategies/symbols), pulling down confidence in equity/forex/commodity picks.

## Investigation
Using `audit_trail/data/dashboard_payload.json` recent closed picks, non-crypto closed sample was analyzed by asset class, source system, strategy, and symbol.

Observed baseline from this snapshot:
- FOREX: 793 picks, 47.0% WR
- COMMODITY: 443 picks, 40.9% WR
- EQUITY: 327 picks, 52.0% WR
- ETF: 70 picks, 51.4% WR

Key underperformers (examples from this snapshot):
- Source systems: `multi_asset_scanner` (12.0% WR on 25), `cta_replicator` (33.3% WR on 90)
- Strategies: `ema_stack_momentum` (16.7%), `dxy-reversal-scout` (20.0%), `carry-trade-momentum` (26.7%), `cta_commodity_momentum_term` (31.8%), `cta_cross_asset_tsmom` (37.5%)
- Symbols: `SOFI` (12.5%), `JNJ` (20.0%), `NIO` (20.0%), `FXA` (20.0%), `NZDJPY=X` (25.0%)

## Changes Made
File changed:
- `copy_trader_intel/non_crypto_consensus.py`

What was added:
1. Historical non-crypto quality-gate loader from `audit_trail/data/dashboard_payload.json`.
2. Automatic strategy blocklist:
   - block strategy if trades >= 20 and WR < 35%.
3. Automatic symbol blocklist:
   - block symbol if trades >= 30 and WR < 30%.
4. Quality-gate applied before consensus voting.
5. Runtime observability logs:
   - dropped counts (strategy/symbol)
   - sample blocked strategy/symbol names.

## Validation
- `py_compile` passed for `copy_trader_intel/non_crypto_consensus.py`.
- Runtime test: `python copy_trader_intel/non_crypto_consensus.py` completed successfully.
- Console output confirms quality-gate execution and blocked list reporting.

## Why this helps
This prevents repeatedly promoting historically toxic non-crypto strategy/symbol clusters into consensus output, while preserving adaptive behavior (blocklists are derived from latest closed-pick history, not hardcoded static bans).
