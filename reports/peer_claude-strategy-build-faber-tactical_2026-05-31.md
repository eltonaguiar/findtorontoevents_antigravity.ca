# Strategy Build — Faber Tactical 10-Month MA

**Date:** 2026-05-31
**Builder:** peer-claude (opus 4.7)
**Slug:** faber_tactical
**Build dir:** `/tmp/strategy_builds_2026-05-31/faber_tactical/`

## Academic basis
Mebane Faber, "A Quantitative Approach to Tactical Asset Allocation" (SSRN 962461, 2007 / updated 2013). 5-asset universe (SPY, EFA, VNQ, GLD, IEF), 10-month SMA signal, equal-weight monthly rebalance, cash sleeve when below SMA.

## Files produced
| File | Lines | Purpose |
|---|---|---|
| `strategy.py` | 173 | Signal, weights, Wilson LB, Bonferroni, promotion gate |
| `paper_pilot_harness.py` | 110 | Monthly stepper, JSON ledger (NO trading_picks writes) |
| `tests.py` | 70 | 9 unit tests (sma, signal, gate, wilson, bonferroni, portfolio) |
| `README.md` | 60 | Citation, rules, risk register, wiring plan |
| `grok_consult.txt` | 4 | Verbatim Grok 3 Mini refinement |

## Tests
9/9 passing (`python3 -m unittest tests -v`).

## Statistical gate applied
Per cursor framework + CLAUDE.md money-ready policy:
- `n >= 500` floor (months * sleeves)
- Wilson 95% LB on monthly hit-rate >= 0.50
- Bonferroni alpha = 0.05/7 = 0.00714 (7-strategy build wave)
- Sharpe >= 0.7, MaxDD <= 25%, months_live >= 24

Codified in `strategy.PROMOTION_GATE` / `passes_promotion_gate()`. Test confirms it rejects small-n configs.

## Cross-AI refinement (Grok 3 Mini)
Q: 10mo vs 12mo SMA? Whipsaw band? Biggest forward risk?

Verbatim response:
> (1) 10mo (Faber 2013 update & Clare/Seaton/Smith 2013 both show 10mo edges 12mo OOS Sharpe by ~0.1-0.2 on similar universes; 12mo only wins in-sample).
> (2) price >= SMA * 0.99 (Clare et al. 2013 & Faber later notes confirm 1% band cuts whipsaws ~15-25% with negligible return drag).
> (3) Regime of near-zero serial correlation / frequent reversals (post-2020 vol-suppression + quant crowding) that kills trend persistence; forward Sharpe already <0.4 in 2013-2023 OOS samples.

**Action taken:** Added optional `band` parameter to `faber_signal()` (default 0.0 = canonical Faber; `WHIPSAW_BAND = 0.01` exposed for opt-in). Risk #1 (trend decay) flagged as auto-pause trigger in README when rolling 12mo Sharpe < 0.

## Wire-Up Rule compliance
Opt-in sidecar per CLAUDE.md. Paper ledger to local JSON only — does not touch `ejaguiar1_stocks.trading_picks` during proving window. Wiring plan in README targets `alpha_engine.smart_picks_engine` via `FaberTacticalSource` adapter after 2026-11-30 (6mo live minimum).

## Risk to forward Sharpe
Grok's #1 risk (trend decay post-2020) aligns with CLAUDE.md "0/6 classes T2-passing" today. Faber is multi-asset macro trend — orthogonal to the CRYPTO/intraday stack dominating the current pick funnel, which is the strategic point of including it.

## No production writes
Confirmed: no DB inserts, no `updates/index.html` edits, no FTP deploys, no edits to shared working tree's pick paths. All build artifacts in `/tmp/strategy_builds_2026-05-31/faber_tactical/`.
