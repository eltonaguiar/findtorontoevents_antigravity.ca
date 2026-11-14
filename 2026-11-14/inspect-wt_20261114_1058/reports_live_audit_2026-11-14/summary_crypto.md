# CRYPTO — summary (live data, 2026-11-14 ~15:45Z)

Sources: `live_dashboard_payload.json` (.picks.active_raw n=3,577 CRYPTO, .picks.recent_closed n=1,966 CRYPTO), `live_money_ready.json`, `live_pf_registry.json`, `live_anti_overfit_audit.json`, `live_audit_surface_truth.json`.

**VERDICT: FAIL — crypto stats are not reliable and the class is not profitable on the honest surfaces.**

## Evidence

1. **Zombie picks dominate the "active" feed.** Of ~4,148 active_raw rows (all classes), 3,272 (79%) are EXPIRED with pnl=0.0 and no resolved exit; `inverse_mutations` alone = 2,262 rows (re-emitting BTCUSDT/XRPUSDT/NEARUSDT daily since 2026-07-13, never resolved). CRYPTO median age in active_raw = 2,128h (89 days); oldest 6,421h (267 days).
2. **Garbage entry prices:** BTCUSDT SHORT entry=0.3322 (Oct 8–11), entry=1.334 (Aug 6–7); **XRPUSDT SHORT entry=0.0 emitted 2026-11-14T13:54 by `prediction_market_consensus`** — a fresh, corrupt row.
3. **Three official CRYPTO stats disagree structurally:**
   - pf_registry canonical (n=23,636): WR 41.5%, **PF 0.232**, single-source 97.9%
   - money_ready_verdict intrabar (n=3,705): WR 35.9%, **PF 0.9196**
   - My recomputed last-14d closed (n=471): WR 38.2%, **PF 0.805**, Σ P/L −158.8%
   The registry (largest sample) says catastrophic; money_ready says break-even. A 4x spread between official surfaces on the same class is not a rounding issue — the dedup/policy filters are reshaping reality.
4. **System's own verdicts:** money_ready pf_ok=False, dsr_ok=False; surface_truth verdict=NOT_READY, policy_clean_pf=0.26 on n=21,947; headline "0/9 asset classes money-ready".
5. **Anti-overfit (Nov 14): 80 strategies audited → 69 OVERFIT_LIKELY (86%), 6 EDGE_LIKELY_REAL.**
6. **Open-pick staleness:** fresh rows exist (newest 1.5–2.7h) — the hourly pipeline IS emitting — but incubator_forward BTCUSDT picks from 2026-11-12T12:15–12:19 (10 strategies) still show current_price=None, pnl=0.0 two days later.
7. **PnL plausibility (user's NEARUSDT question):** NEARUSDT SHORT entry 3.543 (2026-11-10) → 3.233 = +8.75% TP_HIT, and LONG entry 3.675 (2026-11-13) → −12.03% SL_HIT are internally consistent with a ~−9% NEAR move in 3 days — plausible for a volatile altcoin. **External price cross-check (Binance) was blocked by the session guard — UNVERIFIED externally.** The "3.16%" the user saw is consistent with these rows but I could not confirm against an external quote.
8. **Kalshi/Polymarket/MTF consensus:** `prediction_market_consensus` appears as best strategy (score 92 in hyro_pick_performance, which is itself 157h stale) and WR ~86%/PF ~24 in the June anti-overfit audit — but it emitted the XRPUSDT entry=0.0 garbage row live. Its picks carry no independently verifiable market data in these files — **UNVERIFIED, and its data hygiene is demonstrably broken.**

## What is real
- Hourly emission and resolution of fresh crypto picks (newest ~1.5–3h) — the pipeline runs.
- The honest surfaces (pf_registry, money_ready, surface_truth) — they self-report the failure.
