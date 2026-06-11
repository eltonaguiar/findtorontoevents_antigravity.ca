# Strategy Engineering Sweep — 2026-06-11 (80 designs, 8 real backtests)

**Operator ask:** engineer 10 brand-new strategies per asset class that could break the sub-coin-flip era; heavy scrutiny + backtesting.
**Method:** 24-agent workflow — per class: 10 hypothesis-grade designs (M-107 falsification pre-registered, constrained to data we actually hold, targeting our PROVEN failure modes: entry selection, TIME_EXIT drag, LONG-bias) → adversarial kill-pass → the top survivor REAL-backtested with the repo's honest harness (entry-anchored first-touch, SL-wins-ties, strictly pre-entry features, per-symbol-day dedup, net of costs 16bp RT crypto / 4bp equity / 2bp FX).

## Headline: 0 of 8 top picks pass the bar (n≥30, NET PF≥1.5, time-split, concentration)

| Class | designed→survived | top pick | n | WR | net PF | verdict |
|---|---|---|---|---|---|---|
| CRYPTO | 10→6 | eu_us_handoff_continuation | **970** | 37.4% | **1.18** | FAIL (closest) |
| EQUITY | 10→3 | first-hour range break | 63 | 41.3% | 0.50 | FAIL |
| FOREX | 10→5 | g10 dollar-neutral xs-mom | 1625 | 46.3% | 0.86 | FAIL (11y daily) |
| COMMODITY | 10→6 | metals overnight gap fade | 35 | 42.9% | 0.48 | FAIL |
| ETF | 10→5 | sector RS long/short weekly | 1640 | 49.5% | 0.94 | FAIL (multi-yr daily) |
| BOND | 10→3 | first-hour overshoot fade | 56 | 44.6% | 0.84 | FAIL |
| FUTURES | 10→7 | xs RS long/short weekly | 2549 | 49.9% | 0.87 | FAIL (8y daily) |
| MEMECOIN | 10→2 | altseason-gated long | 115 | 35.7% | 0.86 | FAIL |

Full designs + kill reasons + per-trade backtest artifacts: `reports/strategy_bt_<class>_2026-06-11.json` (workflow wf_8e797dd5).

## What this PROVES (and why it's valuable, not disappointing)
1. **The null is robust to fresh idea generation.** 80 disciplined designs spanning session structure, cross-sectional momentum/reversal, event anchoring, regime gating, market-neutral hedging — and the honest harness rejects every top pick at the hedge-fund bar. Combined with the 1,278-slice historical audit and σ-geometry NULL, the evidence now triangulates from three independent directions: **there is no large easily-harvestable edge in our data/universe at our cost assumptions.** Sub-coin-flip history was measurement + selection; honest measurement reveals small-or-no edges, not hidden big ones.
2. **One genuine small edge surfaced**: CRYPTO eu_us_handoff is time-stable (both halves net PF>1.0 across 5 months), extremely diversified (top symbol 1.3%), and its RSI-band mechanism is real (ablation −0.13 PF). Its LONG leg alone: **PF 1.38, +46bp/trade, n=536**. The 1.0×hourly-ATR stop fires on 51% of trades and structurally caps WR — the designer's own noted follow-up (LONG-only, wider stop) is the single highest-value next test.
3. **Cost realism is decisive**: FOREX/ETF/FUTURES weekly rotations land at PF 0.86-0.94 NET — gross they hover near 1.0-1.1; the wins are smaller than round-trip costs. Any future design with sub-20bp expected wins must be killed at design time (now in the scrutineer rubric).
4. **MEMECOIN confirmed do-not-trade from a second direction** (even altseason-gating fails: 35.7%/0.86).

## Pre-registered next steps
- Run the CRYPTO LONG-only wider-stop variant (in flight). Promote to forward-shadow ONLY if net PF≥1.5 + R1 + R2 on the same harness; else record and stop.
- The 43 scrutiny survivors stay on file as a hypothesis pool (each carries falsification criteria); do NOT batch-backtest them — selection across 43 would need Bonferroni ~0.001 and our data can't support it. Revisit per-class when honest n and data depth grow.
- Tournament-resolver honesty port (due-diligence item #1) remains the larger per-model lever.

## FOLLOW-UP RESULT (pre-registered variant; family now CLOSED)
LONG-only 2.0×ATR variant: n=536, 44.2%/net PF 1.328 (control 1.0×: 37.7%/1.380). **"Wider stop caps WR" confirmed; "and therefore caps PF" refuted** — bigger stopped losses offset the WR gain. Both configs are PARTIAL-grade (PF≥1.3, time-stable, top-symbol 1.9%) but neither reaches 1.5; Feb-2026 carries ~61% of total net (regime concentration caveat).
**FINAL DISPOSITION (pre-registered, no further tuning):** `crypto_eu_us_handoff LONG (1.0×ATR)` enters FORWARD-OBSERVATION only — re-run the identical replay in ~4 weeks restricted to entries AFTER 2026-06-10 (pure out-of-sample window); promote to shadow-emission only if fresh-window net PF≥1.3 at n≥80. Else archive. Artifact: reports/strategy_bt_crypto_handoff_v2_2026-06-11.json.
