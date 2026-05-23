# USDCHF=X Concentration Investigation — 2026-05-01

**Verdict:** SINGLE_FLUKE / CLAIM_FALSIFIED (with a side-finding of resolver artefacts on a *different* feed)

The "USDCHF=X carries 261% of total PnL" headline could not be reproduced against either ledger. The pair is materially small in both data planes, and removing it does not flip the system's profit factor. There is, however, a real resolver artefact on the same symbol in a non-aggregated feed (KIMI_RISEOFTHECLAW) which deserves a separate quarantine review.

## Numbers (read-only, no production files modified)

### `audit_dashboard/data/dashboard_data.json` → `picks.recent_closed` (n=3,500)
- USDCHF=X picks: **56**
- USDCHF=X sum pnl_pct: **+4.89**
- recent_closed total sum pnl_pct: **+491.86**
- **USDCHF share: 0.99% (NOT 261%)**
- System PF (with USDCHF): **1.293**
- System PF (ex-USDCHF): **1.291** ← virtually identical

### `alpha_engine/data/closed_picks.json` (n=7,415, raw)
- USDCHF=X picks: **10** (8 wins, 2 losses, sum +0.057)
- System total sum pnl_pct: **−8.02** → USDCHF share **−0.7%** of book

The dashboard-headline `summary.profit_factor=0.98` is computed across `valid_closed_picks=8919`, a wider population than `recent_closed`. Even there, USDCHF=X cannot dominate: the alpha_engine system alone owns 12,135 closed picks with PF 1.6 and `toxic_symbol=None`. The toxic-concentration flag (`audit_trail/dashboard_generator.py:8715-8736`, ≥70% share of |PnL|) flags only 2 systems, neither of which is USDCHF: `multi_asset_cot` (CT=F 96.4%) and `mercury2_fast` (BTCUSDT 91.7%).

## Per-(strategy, direction) breakdown for USDCHF=X (recent_closed, n=56)

| Strategy | Dir | N | WR% | PF | sum pnl_pct | Window |
|---|---|---|---|---|---|---|
| forex_rsi2_mean_reversion | SHORT | 28 | 60.7 | 5.12 | +5.516 | 03-26 → 04-06 |
| forex_rsi2_mean_reversion | LONG | 15 | 73.3 | 11.42 | +0.013 | 04-15 → 04-27 |
| non_crypto_consensus | LONG | 7 | 85.7 | 55.00 | +0.005 | 04-15 → 04-27 |
| fx_smart_carry_trade_momentum | LONG | 4 | 25.0 | 0.83 | −0.103 | 04-03 → 05-01 |
| carry_trade_momentum | LONG | 1 | 0.0 | 0.00 | −0.542 | 03-13 |
| unknown | LONG | 1 | 100.0 | inf | +0.004 | 03-16 |

The +5.516 from `forex_rsi2_mean_reversion SHORT` is the only material slice, and 31/56 of all USDCHF closes resolve as `FORCE_CLOSED` with 30 wins / 1 loss (gross +6.40 vs −0.0004) — a single 5.0% outlier (entry 0.79425 → exit 0.7545375, status=WON, exit_reason=FORCE_CLOSED, 2026-03-26 17:30) accounts for nearly the entire USDCHF SHORT pnl. Win distribution is asymmetric (max +5.0, median +0.011) vs loss distribution (median −0.071, min −0.542) — i.e. one tail event, not a robust edge.

## Same-strategy / different-symbol replication

`forex_rsi2_mean_reversion` works **broadly** across FX, not just on USDCHF — strongest tickers are USDCAD (+5.65), AUDUSD (+5.60), USDCHF (+5.53), USDJPY (+3.62). EURJPY=X is the real bleed (−8.71 over 50 picks). Strategy-level n=615, WR 47.9%, PF 1.54; ex-USDCHF n=572, WR 46.4%, PF 1.39 — still solidly Tier-2-ish. No "single-symbol overfit" smell.

`fx_smart_carry_trade_momentum` is mostly noise across all FX (4-7 picks per symbol, mixed signs, n=25 total) — too thin to read.

## Resolver-bug check (`alpha_engine/outcome_resolver.py:97`, `:384-405`)

The bug per `feedback_noncrypto_resolver_live_close_bug.md` is mitigated as of 2026-04-28: line 97 now uses asset-class-gated thresholds (FOREX threshold ≥ 5bp, not 0.1bp). USDCHF picks in `alpha_engine/data/closed_picks.json` resolve through `_replay_intraday()` (TP/SL replay against bars, lines 372-398) — wins are TP_HIT_REPLAY at 0.78–0.80%, losses are SL_HIT_REPLAY at −0.30%. These look real, not noise-flicker.

**Side-finding (NOT the user's headline, but worth flagging):** `KIMI_RISEOFTHECLAW/data/closed_picks.json` has 38 USDCHF=X picks where `exit_reason="SL hit at $X (stop was $Y, live=$X)"` is applied even when the live price never breached the stop — 9 of these get `status=WON` despite being `SL_HIT` (e.g. entry 0.78794, exit 0.787970, "SL hit" but live > entry → labelled WON). Net of all 38: PF 0.045, sum −4.60. This feed is NOT in the dashboard headline aggregation (KIMI_RISEOFTHECLAW is not registered in `systems[]`) so it does not affect the 0.98 PF, but it is an independent resolver bug that should be tracked separately.

## Recommendation

- **Strip from aggregates: NO.** USDCHF=X is 0.99% of recent_closed PnL, not 261%. Removing it shifts PF by 0.002. The "261% of book" hypothesis is falsified.
- **Quarantine the strategy: NO.** `forex_rsi2_mean_reversion` works across 12 FX pairs, not just USDCHF. Standard tail-trim (cap any single-pick pnl_pct contribution at 95th-pct, ~1.5%) would absorb the one 5.0% FORCE_CLOSED outlier without touching the strategy.
- **Keep.** Re-run the headline PF calculation against the full 8,919-row population the dashboard headline uses (rather than recent_closed n=3,500); if a different ledger is producing the 261% number, that ledger is the bug — not the symbol.
- **File a separate ticket** for KIMI_RISEOFTHECLAW resolver labelling SL-hit-equals-WON; do not fold into this investigation.

## Evidence files (read-only)
- `e:\findtorontoevents_antigravity.ca\audit_dashboard\data\dashboard_data.json` (recent_closed slice)
- `e:\findtorontoevents_antigravity.ca\alpha_engine\data\closed_picks.json` (10 USDCHF, raw)
- `e:\findtorontoevents_antigravity.ca\KIMI_RISEOFTHECLAW\data\closed_picks.json` (38 USDCHF, side-finding)
- `e:\findtorontoevents_antigravity.ca\audit_trail\dashboard_generator.py:8715-8736` (toxic-concentration flag logic)
- `e:\findtorontoevents_antigravity.ca\alpha_engine\outcome_resolver.py:97-109,372-398` (asset-class-gated thresholds + replay logic)
