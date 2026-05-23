# Real-Money Edge Plan — Review Synthesis (2026-05-13)

**Reviewing:** `C:/Users/zerou/.cursor/plans/real_money_edge_plan_ed80c0d8.plan.md`
**Reviewer:** Claude Opus 4.7 (1M ctx) + 4-engine swarm (xai/deepseek/groq/cerebras)
**Cost:** $0.0698

## Swarm consensus (4/4 engines)

| Question | Consensus |
|---|---|
| Plan still relevant? | **Mostly** (4/4) |
| Real-money-ready gate status? | **Nearly met** (4/4) |
| TODOs obsolete? | **None** (4/4: all 5 still apply) |
| Top action? | **Operator: run `tools/verify_multi_asset_cot_db.py`** (4/4) |
| #2 action? | **Dev: apply COT 3-day publication-lag patch + retest COMMODITY** (4/4) |
| #3 action? | **Dev/Operator: enable VIX+YC combined gate (PR #960) in shadow → production** (4/4) |

## Plan TODO status

| TODO | Status | Revision needed |
|---|---|---|
| `snapshot-audit-baseline` | Binding | Add COT timing-leakage results + multi_asset_cot DB verifier result |
| `enable-class-gates` | Binding | Wire drift/walkforward gates per plan; PR #960 VIX+YC partially does this for EQUITY/ETF |
| `fast-track-strong-classes` | Binding | **Major revision:** COMMODITY Tier-1 contingent on COT fix; EQUITY VIX+YC is new strongest candidate |
| `contain-weak-classes` | Binding | FOREX sizing OFF done; BOND (n=11) needs explicit containment beyond ignore |
| `db-lineage-and-backtests` | Binding | Prioritize multi_asset_cot DB verify ahead of broader lineage card |

## What this session added that plan did NOT anticipate

**4/4 engines flagged missing items:**

1. **COT timing leakage discovery** (PR #941) — COMMODITY PF 3.92 likely overstated by 3-day publication lag. Real WR estimated 45-55% (vs claimed 67.4%). Plan's "primary alpha candidate" framing may not survive fix.

2. **VIX+YC combined regime gate** (PR #960) — session's best risk-adjusted strategy:
   - VIX<22 AND YC>0: PF 4.98 / Sharpe 2.08 / MDD 16.8% / n=79
   - VIX<20 AND YC>0: PF 5.87 / Sharpe 2.29 / MDD 7.2% / n=77
   - 3 of 4 TIER-1 criteria pass at VIX<20 AND YC>0
   - **3/4 engines: this is the most important addition** to plan

3. **Regime-gate methodology pattern** (6/7 hit rate) — monthly-rebalance momentum + regime overlay (VIX/YC) consistently delivers TIER-1 PF. Lead-lag-correlation strategies (gasoline, BOND credit-spread, BOND duration, Donchian+VIX, WTI-Brent continuous) consistently fail (0/4). **Plan should codify this as strategy-construction methodology.**

## Real-money-ready gate analysis

**Plan's gate:**
> At least 2 asset classes sustain Tier-2 (PF≥1.5, WR≥50, n≥100, drawdown within charter) for consecutive monitoring windows and pass drift/divergence checks.

**Current state:**
- EQUITY: PF 1.55 / WR 53.2% / n=447 — **MEETS Tier-2 floor** ✓
- COMMODITY: PF 3.87 / WR 67.4% / n=420 — Tier-1 IF COT timing-leakage fix doesn't crash it; **PENDING verification**
- All other classes below Tier-2

**Gate status:** **NEARLY MET.** Need either (a) COMMODITY to survive COT fix, OR (b) deploy VIX+YC overlay as second sized-up class. Drift alert still TRUE (not addressed); plan's "auto-paper-only if drift TRUE" gate not implemented.

## Concrete next 3 actions (4/4 swarm consensus)

| # | Action | Owner | Blocker |
|---|---|---|---|
| 1 | Run `tools/verify_multi_asset_cot_db.py` against `ejaguiar1_stocks.picks` | operator | needs `DB_PASS_STOCKS` env |
| 2 | Apply COT 3-day publication-lag patch (per PR #941); re-run COMMODITY backtest | dev | PR #941 follow-up |
| 3 | Enable PR #960 VIX+YC gate in shadow env (`YC_REGIME_GATE_ENABLED=1`); monitor 7d | operator | None |

## What plan should ADD (4/4 consensus)

1. **Regime-gate overlay methodology** as a strategy-construction rule:
   - Monthly-rebalance momentum + (VIX threshold OR YC inversion) overlay
   - Reject any "X leads Y by N days" proposal without cross-correlation matrix first
2. **COT publication-lag check** as mandatory pre-promotion gate for COMMODITY
3. **Drift-alert auto-paper-only enforcement** — currently TRUE in dashboard but no code path acts on it
4. **`multi_asset_cot` PF 21.86 fabrication check** — DB verifier shipped, run pending

## Plan recommendation: REVISE in-place, do NOT replace

Plan's structure (Phase 1-4) is sound. Add 3 new items + revise 3 existing TODOs:

**Add:**
- `cot-publication-lag-patch` (P0)
- `vix-yc-gate-shadow-7d` (P0)
- `regime-overlay-methodology-doc` (P1)

**Revise:**
- `snapshot-audit-baseline`: include COT leakage + multi_asset_cot verifier output
- `fast-track-strong-classes`: COMMODITY tier-1 conditional; EQUITY+VIX+YC is now strongest
- `contain-weak-classes`: BOND explicit paper-only beyond ignore

## Cumulative session evidence

**Production filters added** (helps "enable-class-gates" todo):
- NS-C (CRYPTO UTC death-zone)
- FX1 (FOREX JPY-cross block)
- NS-D (ml_crypto_pred LONG reject)
- NS-F (CRYPTO LONG-in-BEAR reject)
- VIX-regime sidecar (EQUITY+ETF) + YC combined variant

**Backtests shipped that inform "fast-track" + "contain":**
- 4 TIER-1 candidates (EQUITY VIX, ETF VIX, EQUITY YC, EQUITY VIX+YC combined)
- 1 PARTIAL WIN (WTI-Brent event)
- 3 falsifications (BOND overlays, gasoline-XLP, Donchian+VIX)
- 9 backtests total, hit rate 56%

**Memory deltas:**
- COMMODITY: PF 3.92 → 3.87 (slight drop); status STILL pending COT lag fix
- EQUITY: PF 1.60 → 1.55 (slight drop); Tier-2 still
- ETF: PF 1.48 → 1.34 (dropped, now Tier-3 not near-Tier-2)
- CRYPTO: PF 1.39 → 1.36 (slight drop)
- FOREX: PF 0.28 → 0.29 (unchanged, sizing OFF)

## Cross-reference

- `C:/Users/zerou/.cursor/plans/real_money_edge_plan_ed80c0d8.plan.md` — original plan
- `reports/supreme_plan_review_2026-05-13.md` — parallel plan review (Supreme Edge plan)
- `reports/money_maker_ready_20260512T204049Z.md` — current per-class snapshot
- `docs/PERFORMANCE_CHARTER.md` v1.0 — canonical tier thresholds
- `reports/equity_vix_yc_combined_super_breakthrough_20260513.md` — VIX+YC backtest
- `reports/cot_timing_leakage_audit_2026-05-13.md` — COT fix per PR #941
- `tools/verify_multi_asset_cot_db.py` — DB verifier (operator runs)

NFA. No production change made in this review.
