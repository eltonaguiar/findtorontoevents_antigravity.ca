# Statistical soundness — whole-system verdict (live data, 2026-11-14 ~15:45Z)

Sources: `live_pf_registry.json`, `live_money_ready.json`, `live_anti_overfit_audit.json`, `live_audit_surface_truth.json`, `live_dashboard_payload.json` (.picks.recent_closed n=3,500), `alpha_engine/config.py` (June snapshot: 361 families) + baby_strategies (285).

**VERDICT: FAIL — the system is not statistically sound as an investment product. It is a massive strategy-generation machine whose honest self-audits say so, surrounded by presentation surfaces that overstate it.**

## 1. Multiple-testing exposure
- Strategy universe: 361 core families + 285 baby-strategy files + mutation engines (June counts; live count in `evidence_live_audit.json`). At p=0.05, pure chance expects ~260 lucky PF>1.5 survivors across that universe.
- Live anti-overfit audit (Nov 14, n=80 audited): **69 OVERFIT_LIKELY (86%), 6 EDGE_LIKELY_REAL, 5 UNDETERMINED.** Worse ratio than June (31/38 = 82%).
- The 6 "real-edge" survivors need per-strategy scrutiny (n, WR, autocorr) before believing any.

## 2. The surfaces contradict each other — that alone fails an audit
Same asset classes, same day, three official numbers:
- CRYPTO: registry PF 0.232 (n=23,636) | money_ready PF 0.9196 (n=3,705) | my 14d recompute 0.805 (n=471)
- ETF: registry PF 1.84 (n=15) | money_ready PF 0.0216, WR 2.2% (n=45) | my 14d 0.928 (n=37)
- EQUITY: registry 0.707 (n=493) | money_ready 0.939 (n=250) | my 14d 1.172 (n=42)
- FOREX: registry 1.214 (n=456) | money_ready 0.660 (n=612) | my 14d 1.483 (n=43)
No reconciliation layer; each surface appears to choose its own window/filter. Registry `counts` show the filters remove 34,540→22,941 rows (flicker 3,872, dupes 129, policy 1,777, not-closed 5,821) — the pipeline is honest about dropping artifacts, but the resulting numbers still don't agree with the other surfaces.

## 3. Recomputed realized performance (my own math, last 14d, n=604 total)
CRYPTO n=471 PF 0.805 Σ−158.8% | EQUITY n=42 PF 1.172 Σ+19.5% | FOREX n=43 PF 1.483 Σ+5.2% | ETF n=37 PF 0.928 Σ−3.5% | BOND n=4 PF 0.05 Σ−3.4% | COMMODITY n=7 PF 0.604 Σ−4.2%.
Aggregate: dominated by crypto losses; net negative. No class with n≥100 shows PF>1.3 in any honest long-horizon surface (registry/money_ready).

## 4. Data integrity failures that bias stats
- 79% of active_raw rows (3,272/4,148) are EXPIRED pnl=0 zombies (inverse_mutations 2,262).
- Garbage entry prices in live data: BTCUSDT entry 0.3322 and 1.334; XRPUSDT entry 0.0 emitted 1.5h before fetch.
- 3,872 spot-flicker (|pnl|<0.02bps) closed rows dropped — 13% of all "closed" rows were zero-delta artifacts.
- Registry single-source concentration: CRYPTO 97.9%, EQUITY 97.6%, COMMODITY 91.3% — the "class" stats are mostly ONE source each.
- 11% closed rows had unresolved exits or replay duplicates in June DB health; 3,509 non-canonical FORCE_CLOSED_TOXIC statuses.

## 5. The system's own verdicts (can't be dismissed as my opinion)
- surface_truth (11h old): "**0/9 asset classes money-ready** on policy-clean closed picks. Do not size on Smart Picks / tournament / leaderboard inflated WR."
- money_ready: pf_ok=False for every class; dsr_ok=True only EQUITY.
- Verdicts: CRYPTO NOT_READY, FOREX NOT_READY, EQUITY NOT_READY, COMMODITY WATCH, FUTURES/ETF INSUFFICIENT_DATA.

## 6. What would make it sound (for the master-plan agent)
1. One canonical ledger; every surface computed from it; publish the filter diff.
2. Kill zombie re-emission (inverse_mutations) and garbage-price emission (entry≤0).
3. Promote only the ≤6 EDGE_LIKELY_REAL strategies to a forward-only pilot with n≥100 before any display tier.
4. Fix hyro_pick_performance deploy break; kill or build mutual-fund ranker honestly.
5. Pre-register strategy count; apply deflated Sharpe/White reality check properly (fix `arch` dep).
