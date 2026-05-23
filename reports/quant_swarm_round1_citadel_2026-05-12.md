# Quant Swarm Round 1 — Citadel/GS Multi-Asset Systematic Lens

**Date:** 2026-05-12
**Persona:** Senior PM, Multi-Asset Systematic Pod (Citadel/GS-style)
**Input:** 55,510 trades, raw WR 11.13%, Week-1 rescue shipped (commits in `reports/rescue_plan_per_asset_class_2026-05-12.md`)
**Mode:** Caveman/terse. NFA.

---

## 1. Per-class verdict (keep / kill / rebuild)

| Class | Verdict | Why |
|---|---|---|
| COMMODITY (CT=F COT) | **KEEP+SIZE** | DSR=1.0 single name, $3.40 net/trade survives cost overlay, capacity ~$5-25k. Real edge. |
| EQUITY | **KEEP / RESHAPE** | T2-candidate PF 1.41/WR 52.7 n=421. Hedge-fund-grade once vol-adjusted top-decile filter + PEAD overlay land. |
| BOND | **REBUILD** | PF 1.72 WR 55.6 but n=18 = noise. FRED fix shipped; need duration/curve carry stack before sizing. |
| ETF | **REBUILD** | n=87 thin. Expand to ≥150 names, treat as risk-parity sleeve not alpha sleeve. |
| FUTURES (CT/GC) | **KEEP NARROW** | CT=F live SHADOW; GC=F mutation queued. Don't drift into ES/NQ momentum — capacity competes with the firm. |
| CRYPTO | **KILL 80%, KEEP 5%** | Sub-T2 PF 1.25 on n=8067. `quan_engine` (PF 0.70 @ 18% vol) + `unknown` (PF 0.35 @ 7%) drag elite strats (PF 2.34-3.97) into the dirt. Aggressive emitter cull, then size only the survivors. |
| FOREX | **KILL or paper-only** | PF 0.27 post-noise on n=1169. Genuinely sub-floor. SHORT-only + 13-21 UTC session pilot is the only credible rebuild. |

Net: raw 11.13% WR is a **mix artifact** — clean strats (cot_positioning 90%, baby cohort) get buried under emitter sludge. Citadel response: **delete the sludge, do not retune it**.

## 2. Hidden-insight queries

Run these before next allocation meeting:

1. **Low-score-high-PnL outliers** — query `audit_dashboard/data/dashboard_data.json` for picks `smart_score<40 AND realized_pnl_pct>+1.0`. Indicates score model is mis-priced on tails — classic Citadel "negative-vega in the scorer" pattern.
2. **High-score-low-PnL** — `smart_score>70 AND realized_pnl_pct<-0.5`. These are confidence-without-edge picks (see `feedback_confidence_is_not_edge.md`); calibration ECE is broken on the top decile.
3. **Dormant edge** — strats with `n_closed<20 AND PF>2.0`. Lopez de Prado deflation says these are 95% noise but the 5% that aren't are where new pods are born. Force a 200-trade SHADOW pilot before either killing or sizing.
4. **Hour-of-day x asset-class heatmap** — cleaned-data baseline says 22 UTC = 61.2% WR vs 08-09 UTC death zone. We're paying carry/spread overnight for nothing.
5. **Symbol-level capacity** — MATIC ghost (660 zero-WR + 755 fake 100% WR) still poisons aggregates. Hard-purge before any portfolio-level Sharpe number is trusted.

## 3. Risk-parity portfolio across our 7 classes

Citadel doesn't equal-weight asset classes; it equal-**risk**-weights. Given current realized vol + edge quality:

| Class | Vol target | Edge-conviction multiplier | **Net weight** |
|---|---|---|---|
| COMMODITY (CT=F COT) | 12% | 1.3× (DSR=1.0) | **22%** |
| EQUITY (top-decile) | 16% | 1.0× | **18%** |
| FUTURES (CT/GC) | 14% | 1.0× | **15%** |
| BOND (treas+IG, post-rebuild) | 6% | 0.8× | **18%** (carry sleeve, levered) |
| ETF (risk-parity sleeve) | 10% | 0.6× | **15%** |
| CRYPTO (post-cull survivors) | 60% | 0.8× | **8%** (vol-cap dominates) |
| FOREX (SHORT-session pilot) | 8% | 0.3× | **4%** (paper-only until PF>0.8 × 60d) |

Cap any single class at 25%. Cap CRYPTO at 10% regardless of edge — capacity & overnight gap risk. This is risk-parity, not signal-weighting.

## 4. ML reality + role in a Citadel-style stack

ML at Citadel is **not** the alpha generator. It is: (a) regime classifier, (b) execution-cost predictor, (c) gate/filter, (d) calibrator. Our stack confuses (a-d) with alpha generation — that's why `quan_engine` and `kimi_signal_tracking` produce PF<0.8 sludge.

Reposition:

- Rule-based strats (cot_positioning, baby_strats, dna_winner SHORT) = **alpha**.
- ML = **filter only**: ml_gatekeeper CRYPTO gate (`c778f8f1696`) is the right pattern. Extend to all classes.
- Drift watchdog (`db5bcfa0f04` KL>0.07 auto-disable) = correct. Mandatory before any model touches a live pick.
- PBO/CPCV gates in CI = PARTIAL today. Until those block prod merges, ML stays sidecar.

## 5. THE ONE THING — Day 1

**Kill `quan_engine` + `unknown` + `kimi_signal_tracking` + `crypto_soc` emitter weight to zero across CRYPTO**, today, before any other work.

Math: those four emitters drag CRYPTO from elite-strat PF 2.34-3.97 down to system PF 1.25 on n=8067. Removing ~25% of CRYPTO volume from the sludge bucket re-prices the entire system WR upward by ~6-10pp without changing a single model parameter. **Zero-cost alpha recovery.** Everything else (rebuilds, paper pilots, risk-parity weights) compounds on top of this — but only after the sludge is gone.

Second priority: enforce the 10-step real_money.html gate as a CI block, not a checklist.

---

NFA. Research surface. Real capital gated on ≥2 classes sustaining T2 for 30 consecutive days.
