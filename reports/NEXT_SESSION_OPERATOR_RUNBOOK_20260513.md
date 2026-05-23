# Next-Session Operator Runbook — 2026-05-13

**Purpose:** any operator (or peer Claude on different PC) picks up cold and executes the next-best actions. Per swarm 4/4 consensus on real-money-plan review.

## Session-state summary

**Date:** 2026-05-13
**Shipped:** 7 production PRs (NS-C / FX1 / NS-D / NS-F / VIX-gate / VIX-ETF-extend / VIX+YC combined) + 10 backtests + 4 plan/synthesis reports
**Tier-1 candidates discovered (4):**
- EQUITY top-5 momentum + VIX<20: PF 5.37 / Sharpe 2.19 / MDD 7.3%
- ETF sector top-3 + VIX<22: PF 3.32 / Sharpe 1.68 / MDD 11.8%
- EQUITY top-5 momentum + YC>0: PF 3.12 / Sharpe 1.44 (n=101 only TIER-1 PF passes)
- **EQUITY top-5 momentum + VIX<20 AND YC>0 (SUPER): PF 5.87 / Sharpe 2.29 / MDD 7.2%**

## Real-money-ready gate status

Per plan (`C:/Users/zerou/.cursor/plans/real_money_edge_plan_ed80c0d8.plan.md`):
> ≥ 2 asset classes sustain Tier-2 (PF≥1.5, WR≥50, n≥100, MDD within charter)

**Live state:**
- EQUITY: PF 1.55 / WR 53.2% / n=447 — ✓ MEETS
- COMMODITY: PF 3.87 / WR 67.4% / n=420 — Tier-1 IF COT timing-leakage fix doesn't crash it (PENDING)
- All others: below Tier-2

**Verdict: NEARLY MET.** Need either (a) COMMODITY survives COT fix, OR (b) deploy VIX+YC overlay as the 2nd Tier-2+ class (already backtested PF 4.98).

## Next 3 actions (priority order, 4/4 swarm consensus)

### Action 1 (operator) — Verify multi_asset_cot PF 21.86 claim
**Status:** verifier shipped, needs execution
**Command:**
```bash
DB_PASS_STOCKS=<password> python tools/verify_multi_asset_cot_db.py
```
**Output:** `reports/multi_asset_cot_db_verify.json` + console summary
**Decision tree:**
- If raw DB PF ≈ 21.86 → multi_asset_cot is real edge → ELIGIBLE for size-up
- If raw DB PF << 21.86 (e.g., resolver-denominator artifact like kimi_signal_tracking 0.28→8.38) → BLOCK strategy from real-money sizing; add to BLACKLISTED_STRATEGIES

**Blocker:** operator needs DB_PASS_STOCKS env (post-2026-05-12 rotation).

### Action 2 (dev) — Re-run COMMODITY backtest after COT lag patch
**Status:** PR #941 merged 2026-05-13 02:31 UTC; backtest re-run pending
**Command:**
```bash
python tools/verify_cot_positioning_post_patch.py  # if exists; otherwise build
```
**Decision tree:**
- COT-corrected WR ≥ 50% AND PF ≥ 1.5 → COMMODITY Tier-2 confirmed → REAL-MONEY READY GATE MET
- COT-corrected WR ≈ 45-55% per deepseek estimate → COMMODITY drops to TIER-3 → need VIX+YC as 2nd class

**Action follow-up if needed:** verify `cot_positioning_CT_locked` 89.8% WR claim per `reports/cot_timing_leakage_audit_2026-05-13.md`.

### Action 3 (operator) — Shadow-mode VIX+YC combined gate (PR #960)
**Status:** PR #960 merged 2026-05-13 19:08 UTC; default OFF
**Command (in shadow env, NOT production):**
```bash
export VIX_REGIME_GATE_ENABLED=1
export YC_REGIME_GATE_ENABLED=1
# Run for 7 days; observe `_hf_quality_gate_reason = vix_yc_regime_combined` audit entries
```
**Decision tree:**
- 7d shadow log shows ~35-40% skip rate matching backtest projection → OK to flip in production
- Shadow shows < 20% or > 60% skip rate → backtest universe-bias suspect; HOLD

**Production flip:** same env vars in production after shadow validation.

## Pending operator actions (3)

| # | Action | Effort | Blocker |
|---|---|---|---|
| OP1 | Run `tools/verify_multi_asset_cot_db.py` | 5 min | DB_PASS_STOCKS env |
| OP2 | Flip VIX+YC gate in shadow env, observe 7d | 7 days passive | None |
| OP3 | Rotate `MYSQL_PASSWORD` GH secret to match new DB password | 10 min | Operator GH access |
| OP4 | Close LINK-L + ETH-L paper positions on TV (per prior cycle directive) | 5 min | TV access |

## Pending dev actions

| # | Action | Effort | Owner |
|---|---|---|---|
| DEV1 | Re-run COMMODITY backtest post-PR #941 lag patch | 4h | Dev (Codex/Claude) |
| DEV2 | Build `tools/verify_cot_post_patch.py` if not exists | 2h | Dev |
| DEV3 | Update real-money plan TODOs per `reports/real_money_plan_review_synthesis_20260513.md` | 1h | Dev |
| DEV4 | Document regime-gate methodology rule (monthly-rebal momentum + VIX/YC) in `docs/PERFORMANCE_CHARTER.md` | 2h | Dev |

## Locked-in patterns this session (high-conviction)

1. **Regime-gate works on monthly-rebalance momentum: 4/4 hit rate** (EQUITY VIX/YC/combined + ETF VIX)
2. **Regime-gate FAILS on event-based signals: 0/2** (Donchian, MA crossover) — event signals self-regulate
3. **Lead-lag-correlation proposals FAIL: 0/4** (gasoline, BOND credit-spread, BOND duration, WTI-Brent continuous-corr)
4. **Free-tier yfinance structurally broken** for: fundamentals point-in-time (Piotroski), FRED OAS spreads (BOND), 10y-2y exact curve (use 10y-5y proxy instead)

## Session backups

`C:/Users/zerou/backup-vix-gate-20260513/` (40+ files): includes all gate modules, tests, swarm outputs, prompt files. Survived 2 peer-reset incidents.

## Cross-references

- `C:/Users/zerou/.cursor/plans/real_money_edge_plan_ed80c0d8.plan.md` — original plan
- `reports/real_money_plan_review_synthesis_20260513.md` — this session's plan review
- `reports/SESSION_RESUMPTION_SUMMARY_20260513.md` — earlier summary
- `reports/equity_vix_yc_combined_super_breakthrough_20260513.md` — best risk-adjusted strategy
- `docs/PERFORMANCE_CHARTER.md` v1.0 — canonical tier thresholds
- `tools/verify_multi_asset_cot_db.py` — DB verifier (Action 1)
- `audit_trail/vix_regime_gate.py` — combined gate sidecar (Action 3)

NFA. No active trades placed this session.
