# Cerebras qwen-3-235b Review of Latest Planning .MD Files (2026-05-18)

Model: cerebras/qwen-3-235b-a22b-instruct-2507 (single-shot, 11 docs, 67106 chars / 20240 prompt tokens).
Reason chosen: largest-context + fastest available model on our keys; Mercury/Inception key dead (401).

---

1. **CODE-REVIEW THE DOCS: Contradictions, Stale Claims, Gaps**  
- `MASTER_ENHANCEMENT_PLAN_2026_05_18.md` claims CRYPTO is the "one active bet" (funding-arb), but `STRATEGIC_FORK_SYNTHESIS` and `PLAN_VET_DEBATE` flag it as overconfident and execution-risky — contradiction in risk posture.  
- `CORRECTED_GAMEPLAN` states FOREX verdict is "WATCH" due to active gate, but `MASTER_ENHANCEMENT_PLAN` and `FOREX_HARD_DISABLE_RATIONALE` enforce hard-disable — contradiction in asset status.  
- `ROADMAP_TO_EDGE` says COMMODITY PF=1.11 (sub-floor), but `EDGE_VERDICT` notes COMMODITY policy-clean PF≈2.30 at n≈47 — stale/inconsistent PF reporting.  
- All docs cite `pf_registry.json` as canonical, but `CORRECTED_GAMEPLAN` uses dashboard tiles for live verdicts — gap in source-of-truth alignment.  
- `MASTER_ENHANCEMENT_PLAN` and `ROADMAP_NO_EDGE_TO_MONEY_READY` both list "fix non-crypto outcome resolver" as P0, but no doc specifies *how* to fix the resolver logic — gap in implementation spec.  
- `STRAND_B_PLAN` requires real data and pre-registration, but `PLAN_VET_DEBATE` notes both STRAND B modules *currently fail vetting* — stale claim of readiness.

2. **CONSOLIDATED ACTION ITEMS (Deduplicated, Priority-Ordered)**  

**CROSS-CUTTING**  
- **Fix non-crypto outcome resolver** / Why: EQUITY/FOREX/FUTURES/ETF/BOND resolve to `pnl_pct=0.0`, blinding all analysis / Owner: `roadmap_no_edge_to_money_ready_2026_05_18.md` → Phase 0 / Master Plan Phase: 0  
- **Quarantine `ml_enhanced` family** / Why: Drags CRYPTO PF; 147/149 unquarantined / Owner: `MASTER_ENHANCEMENT_PLAN_2026_05_18.md` P0 / Master Plan Phase: Gates  
- **Promote post-cost expectancy to hard gate** / Why: Gross PnL inflates edge; net edge must survive ≥60% after cost / Owner: `MASTER_ENHANCEMENT_PLAN_2026_05_18.md` P0 / Master Plan Phase: Gates  
- **Wire `at_pick_audit_trail` writer** / Why: Traceability required for funnel transparency / Owner: `MASTER_ENHANCEMENT_PLAN_2026_05_18.md` P1 / Master Plan Phase: Measurement  
- **Fix duplicate re-emission at writer** / Why: 83% downstream drop; root cause of data inflation / Owner: `MASTER_ENHANCEMENT_PLAN_2026_05_18.md` P0 / Master Plan Phase: Measurement  
- **Add cost model (net-of-cost + per-class slippage)** / Why: Gates and harness run on gross/placeholder; funding-arb needs continuous cost model / Owner: `PLAN_VET_DEBATE_2026_05_18.md` A1 / Master Plan Phase: Gates  
- **Default `/audit` tiles to `pf_registry.json`** / Why: Dashboard tiles are inflated; `pf_registry` is policy-clean / Owner: `MASTER_ENHANCEMENT_PLAN_2026_05_18.md` P0 / Master Plan Phase: UX  

**CRYPTO**  
- **Test funding-rate/basis arbitrage (delta-neutral)** / Why: Only structural bet with budget fit; must clear harness + cost gate / Owner: `MASTER_ENHANCEMENT_PLAN_2026_05_18.md` P0 / Master Plan Phase: Per-asset-class  
- **Cull sub-PF-1 source systems** / Why: Drag from unfiltered volume and `LOST`-status tail / Owner: `roadmap_no_edge_to_money_ready_2026_05_18.md` Phase 2 / Master Plan Phase: Per-asset-class  

**EQUITY**  
- **Wire paid data API (Polygon/Alpha Vantage)** / Why: Resolver logic blocked on yfinance unreliability / Owner: `MASTER_ENHANCEMENT_PLAN_2026_05_18.md` A3 / Master Plan Phase: Measurement  
- **Gather n≥100 clean resolved picks** / Why: Current n=31; insufficient for verdict / Owner: `CORRECTED_GAMEPLAN_2026_05_18.md` Phase 3 / Master Plan Phase: Per-asset-class  

**COMMODITY**  
- **Correct COT 3-day lag + enforce <35% concentration** / Why: COT look-ahead leakage; CT=F concentration kills PBO / Owner: `CORRECTED_GAMEPLAN_2026_05_18.md` PR-1 / Master Plan Phase: Measurement  

**ETF**  
- **Wire VIX<25 gate** / Why: PF 2.05 when VIX<25 vs 0.72 otherwise / Owner: `CORRECTED_GAMEPLAN_2026_05_18.md` PR-2 / Master Plan Phase: Per-asset-class  

**FOREX / FUTURES / BOND**  
- **Keep hard-disabled** / Why: No edge; FOREX bleed ongoing / Owner: `MASTER_ENHANCEMENT_PLAN_2026_05_18.md` P0 / Master Plan Phase: Per-asset-class  
- **Gather n≥20 (BOND)** / Why: Only 1 closed pick; below floor / Owner: `CORRECTED_GAMEPLAN_2026_05_18.md` Phase 3 / Master Plan Phase: Per-asset-class  

3. **SINGLE HIGHEST-LEVERAGE ACTION**  
**Fix the non-crypto outcome resolver** — because 5 of 6 asset classes are statistically invisible due to `pnl_pct=0.0` placeholders. Without real resolved PnL, no class can be measured, no gate can function, and no edge can be validated. This blocks *all* downstream progress (trials, triage, promotion) and is the root of inflated dashboard claims. Fixing it enables honest per-class performance assessment — the foundation of world-class picks.