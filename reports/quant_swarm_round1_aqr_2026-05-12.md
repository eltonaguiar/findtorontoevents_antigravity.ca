# Quant Swarm Round 1 — AQR Lens (Asness Channel)

**Author:** AQR persona — Value/Momentum/Carry/Defensive/Quality factors across asset classes
**Date:** 2026-05-12
**Universe:** 55,510 trades. 11.13% raw WR. Week 1 rescue shipped.
**Verdict-grade source:** `asset_class_health` (post-resolver-v2).

Caveman terse. AQR-skeptical. Factor first, ML second.

---

## 1. Per-class — factors that live there

| Class | Verdict | Living factor | Action |
|---|---|---|---|
| EQUITY (PF 1.41 / WR 52.7% / n=421) | KEEP | Momentum (12-1 cross-section), Quality (profitability, low-debt) | Rebuild as XS-momo + Quality screen. Asness/Frazzini-Pedersen BAB lens. |
| COMMODITY (PF 1.78 / n=750) | KEEP — lift WR | Momentum (TS), Carry (basis: contango/backwardation), Value (5y-MR) | Miffre 2010 carry+momo double-sort. Already half-proven via cot_positioning CT=F. |
| BOND (PF 1.72 / n=18 LEGACY) | REBUILD | Carry (yield curve slope), Defensive (BAB on duration), Value (real-yield z-score) | FRED unblock first. Curve-slope steepener = canonical AQR bond carry. |
| CRYPTO (PF 1.25 / n=8067 — drag from quan_engine PF 0.70 + unknown 0.35) | SURGICAL KILL drag | Momentum (TS only — XS too small) | Cut quan_engine MATIC ghost (755/1001 fixed-TP). Keep DNA winners 2.34-3.97. No carry factor — funding rate proxy unreliable. |
| ETF (PF 1.24 / n=87) | KEEP — grow n | Momentum + Defensive (low-vol sector rotation) | GEM (Antonacci Dual Momentum) on sector ETFs. |
| FOREX (PF 0.27 / n=1169 — REAL sub-floor) | MUTATE | Carry (interest-rate differential — the original AQR FX factor) | Apply mutate-before-kill. Current strategies are momo-flavored; AQR FX edge has ALWAYS been carry. Re-axis. |
| FUTURES (silent-dead, 6 strats paper-only) | REBUILD via COMMODITY proxy | Same as COMMODITY — Momentum + Carry on rolled contracts | CT=F pilot already DSR 1.0. Expand to GC=F via cot_positioning mutation. Lean has roll engine. |

**Punchline:** every class has a canonical AQR factor home. FOREX failing on momo is unsurprising — FX premia have lived in carry for 30 years (Lustig-Verdelhan 2007; Koijen-Moskowitz-Pedersen-Vrugt 2018 "Carry").

## 2. Hidden-insight queries

- **Score-vs-PnL inversion:** `confidence` rho on ETF/CRYPTO is negative — high-conf picks underperform. Standard AQR finding: agreement = crowded = low forward return. Test if low-confidence/high-trust deciles beat high-confidence at every class.
- **Dormant strats with embedded factor exposure:** the 6 paper-only futures strategies (overnight_gap, dollar_trend, equity_seasonality) carry implicit carry/value/seasonal premia. Audit which one cleanest expresses a single factor and resurrect that one.
- **CRYPTO `quan_engine` 18% volume @ PF 0.70 drag:** the 755 MATICUSDT fixed-2.5% TP rows are a synthetic-data ghost. Strip these before any factor regression — they will poison Sharpe estimates system-wide.
- **BAB across asset classes:** Frazzini-Pedersen 2014 — bet against beta works EQUITY, BOND, FUTURES. We don't have a single BAB-style strategy. Free alpha on the floor.

## 3. Factor strategies to test FIRST (cite source)

1. **Cross-sectional 12-1 momentum, EQUITY.** Jegadeesh-Titman 1993 / Asness-Moskowitz-Pedersen 2013 "Value and Momentum Everywhere." Easiest replication. Use NASDAQ 100 universe we already scan.
2. **Commodity carry + momo double sort.** Miffre 2010 SSRN 1127213 — already in `tools/research/commodity_carry_momo.py`. Wire to production. 21% annualized class-wide alpha is the bar.
3. **FX carry G10.** Lustig-Verdelhan 2007. Long high-rate / short low-rate G10 quintile portfolios. Replaces the failing FOREX momo strats.
4. **BAB cross-asset.** Frazzini-Pedersen 2014. EQUITY first (easiest), then BOND duration BAB, then FUTURES.
5. **Quality minus Junk.** Asness-Frazzini-Pedersen 2013. EQUITY only. Profitability + safety + growth + payout screen — works as ML feature input even if not standalone strategy.

## 4. ML reality — principled hybrid

AQR view (de Prado-Asness consensus): black-box ML on raw price = data mining. Hybrid that survives:

- **Factors as features, ML as combiner.** Compute the 5 factor exposures per name per day. Feed factor exposures (not raw OHLCV) to ML. ML's job: assign factor weights conditional on regime.
- **Purged-CPCV mandatory** (de Prado AFML ch 7). The repo already has `mlfinlab` integration — wire it to the live model trainer, not just sidecar.
- **DSR gate at deployment** (already shipped via `anti_overfit_audit_sidecar.py`). Demand DSR ≥ 0.85 at conservative n_trials=500 — directly per cot_paper_pilot_testing_plan Step 4.
- **Reject anything without economic story.** If you can't name the factor in one sentence, kill the model. This is the Asness rule.

## 5. THE ONE THING — Day 1

**Ship the commodity carry+momo double-sort to production.** `tools/research/commodity_carry_momo.py` already exists. Wire one caller into `calculate_smart_score` per CLAUDE.md Wire-Up Rule. COMMODITY is the closest-to-T2 class with n=750 and a 30-year-replicated academic factor. Miffre 2010 said 21% annualized class-wide; we have PF 1.78 already on momo alone. Add carry and the WR gap closes.

Everything else — BOND FRED unblock, FOREX carry-axis pivot, FUTURES CT=F graduation, EQUITY QMJ — queues behind it. One factor, one class, one PR. AQR way.

---

**Refs:** Asness-Moskowitz-Pedersen 2013 JF; Miffre 2010 SSRN 1127213; Lustig-Verdelhan 2007 AER; Frazzini-Pedersen 2014 JFE; Koijen-Moskowitz-Pedersen-Vrugt 2018 JFE; de Prado AFML 2018 ch 7+14.
