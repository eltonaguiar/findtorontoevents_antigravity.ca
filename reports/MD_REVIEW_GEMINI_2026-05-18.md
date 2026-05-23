# Giant-File MD Review — Gemini 2.5 Pro — 2026-05-18

**Reviewer:** Gemini 2.5 Pro (~1M context — one-shot review, no chunking).
**Input:** 274KB bundle of the latest 2026-05-18 strategy/edge/audit `.MD` files
(19 files: MASTER_ENHANCEMENT_PLAN, PATH_TO_PROVEN_EDGE, EDGE_VERDICT,
forward_signal_research, new_signal_research, EDGE_HARVEST, PLAN_VET_*,
HOURLY_AUDIT_05Z, roadmap_no_edge_to_money_ready, kilo_fork2_vetting,
OWNERSHIP_DECISION, audit_pick_flow_case_study, whites_reality_check,
C008_elite_source_audit, CLAUDE_DESKTOP1/2/3, DAILY_IDEAS).
**Anchor plan:** `reports/MASTER_ENHANCEMENT_PLAN_2026_05_18.md`.
**Gate referenced throughout:** `edge_stability_harness` — eff≥0.30, same-sign, ≥3/5 walk-forward windows.
**System state per Gemini:** 0 admissible edges.

---

## 1. Contradictions & stale claims

- **`whites_reality_check_m105_deduped.md` is dangerously stale/artifact-driven.** Claims 16/36 strategies pass SPA with extreme PFs (e.g. `ml_enhanced_FETUSDT_1d_B_lightgbm`). Contradicts `EDGE_VERDICT` + `MASTER_ENHANCEMENT_PLAN`, which kill the `ml_enhanced_*` family as placeholder-stat artifact (near-zero avg_loss inflates mean; SPA can't detect).
- **CRYPTO funding-rate arb is DEAD, not the "Phase 3 bet."** `MASTER_ENHANCEMENT_PLAN` hypes funding-rate arbitrage as the one active bet. `PATH_TO_PROVEN_EDGE` (Update, later 2026-05-18) ran the deep retest and KILLED H-006 (n=4,838, sign-unstable).
- **FUTURES sample size mismatch.** `roadmap_no_edge_to_money_ready` says FUTURES "Below n≥50 floor"; `HOURLY_AUDIT_05Z` shows FUTURES at n=129 / 30d, PF=0.104.
- **On-chain net-flow code is bogus.** `EDGE_HARVEST` promotes order-book imbalance + exchange net-flow as the "one retail bet"; `kilo_fork2_vetting` FAILS `alpha_engine/onchain_crypto.py` because it proxies exchange flow with generic blockchain TX volume — violates Strand B data rules.

## 2. Per-asset-class action items

**CRYPTO**
1. P0 — Fix duplicate re-emissions bug dropping 83% of data; zero-copy dedup stage + 60-day clean backfill before testing new signals.
2. P0 — Quarantine `ml_enhanced` — ban the 147 unquarantined artifact variants.
3. P1 — Pre-register real Glassnode `transfers_volume_exchanges_net` + order-book imbalance; test on the regime-conditional harness.

**EQUITY**
1. P0 — Fix non-crypto resolver: integrate paid data (Polygon/Alpha Vantage) to replace `pnl_pct=0.0` placeholder. Do not test signals on unmeasurable assets.
2. P1 — Test PEAD: pre-register SUE + 15-min reversal, ex-microcap universe, 100bps slippage, run harness.

**COMMODITY**
1. P0 — Enforce COT leakage gates: 3-day publication lag + CT=F <35% concentration cap.
2. P1 — Test inventory-surprise: acquire EIA API key (resolves H-004 UNTESTED), interact with roll-yield, run walk-forward.

**ETF**
1. P1 — Re-test 12-1 momentum (H-003) on the regime-conditional harness — it failed sign-stability 49+/36- on n=30,864; isolated regimes may stabilize the sign.

**FOREX**
1. P0 — Hard disable (`FOREX_HARD_DISABLE=1` global). Retail spread/HFT = negative-EV trap. No further research.

**BOND**
1. P0 — Archive / hard stop. H-008 (2s10s slope momentum) failed decisively on a continuous book (n=57,117). Dealer-dominated, coarse retail data.

## 3. Master-plan gaps

- **No cost model** — gates/harness evaluate gross/placeholder PnL; no net-of-cost expectancy + per-class slippage inside the walk-forward.
- **No terminal state / timebox** — plan is a one-way ratchet; no hard deadline, no "shut down" condition if no edge found.
- **No position-sizing gate** — passing the harness grants admissibility but no capital-allocation/scaling protocol.
- **Blindly trusting free APIs** — plan bottlenecks on existing architecture; misses the option to just buy Polygon/Alpha Vantage for EQUITY to validate the resolver fast.

## 4. Top 5 ranked actions (system state: 0 admissible edges)

1. **P0 — Fix the non-crypto outcome resolver.** Highest leverage. EQUITY/FOREX/FUTURES/ETF/BOND resolve to `pnl_pct=0.0`. Integrate paid API data to make the system measurable.
2. **P0 — Deploy a cost model to the harness.** Hard post-cost expectancy gate (`EXPECTANCY_GATE_ENABLED=1`). Gross-PnL testing creates artifact survivors.
3. **P0 — Fix the duplicate re-emission bug.** Stop dropping 83% of downstream data; fix the writer, backfill 60 days clean, reconcile vs exchange REST.
4. **P1 — Ship the regime-conditional harness upgrade.** Add `evaluate_by_regime` — current harness kills regime-dependent edge by forcing sign stability across conflicting regimes.
5. **P0 — Sanitize the dashboard.** "Money Ready" → honest empty; nuke `ml_enhanced`, strip COT strategies from the COMMODITY tile.

---

_Generated via the `consult-gemini` skill — `gemini -p ... --output-format json` over the 274KB bundle in one shot._
