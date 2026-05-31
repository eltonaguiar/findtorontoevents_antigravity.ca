# Phase-2 Performance Audit — EQUITY (Plan)

Date: 2026-05-31
Author: peer Claude (Opus 4.7)
Mode: READ-ONLY (no DB mutations, no production-code PRs)

## Scope
Asset class **EQUITY** in `ejaguiar1_stocks.trading_picks`, unioning `category IN ('equity','stock','stocks')`. Initial pop scan:
- equity: 2,001
- stock:  23
- stocks: 264
- Total: **2,288 rows**

Status mix (all 3 cats):
- ACTIVE 130, OPEN 371 (unresolved → excluded)
- TIME_EXIT 1,576 (closed-by-clock; pnl_pct decides win/loss)
- LOST 130, TP_HIT 57, EXPIRED 24 (closed)

Note: schema uses `TP_HIT` not `WON`. The template's `status='WON' OR status='TP_HIT'` will still work (WON simply matches 0 rows here). However, TIME_EXIT with `pnl_pct > 0` is also a structural "win". I will report **both** definitions:
- **Strict-WR** = TP_HIT / closed (matches dashboard's "explicit-target hit" semantics)
- **PnL-WR** = `SUM(pnl_pct>0) / closed` (matches the PF computation and the hedge-fund T2 threshold's intent)

## T2 / T1 Thresholds
- T2: PF ≥ 1.5, WR ≥ 50%, MDD < 20%, n ≥ 100
- T1: PF ≥ 2.0, WR ≥ 55%, MDD < 10%, n ≥ 100

## Queries
1. **Class aggregate** (single row, all 3 cats).
2. **Per-strategy aggregate** with HAVING n ≥ 10; sorted by PF desc.
3. **Closed-only** filter: `closed_at IS NOT NULL AND status IN ('TP_HIT','LOST','TIME_EXIT','EXPIRED')`.
4. **MDD proxy**: cumulative pnl_pct ordered by `closed_at`, peak-to-trough drawdown across the class equity curve (equal-weight, 1 unit per pick — a per-trade-pnl curve, not a portfolio-equity curve; documented as a proxy).
5. **pf_registry cross-check**: load `audit_dashboard/data/pf_registry.json` (and `alpha_engine/data/pf_registry.json` if present) → compare per-strategy PF; flag divergences > 10%.

## Risk caveats
- TIME_EXIT semantics: a TIME_EXIT with `pnl_pct≈0.00` is a flat exit; treating it as a loss inflates the loss count for tight-TP / long-hold strategies. I report it honestly in both buckets.
- The strict-WR (TP_HIT only) will look very low (TP_HIT=57 / closed≈1,787 → ~3%) because most equity picks are TIME_EXIT. **PnL-WR is the relevant tier-axis number** for EQUITY in this dataset.
- MDD computed on a per-trade pnl-sum curve is **not** equivalent to portfolio MDD (no compounding, no concurrent-trade overlap). It is a directional proxy.
- Concentration risk: pre-M-067 EQUITY n was 33 (per CLAUDE.md). Current n=2,288 is post-M-067 — verify the dominant `source_system` / `strategy` shares.
- Crypto-suffix leak check: post-PR #166 EQUITY mistag backfill, scan for symbols ending in `USDT/USDC/BTC/ETH` still tagged EQUITY.
- pf_registry may be stale relative to live `trading_picks`; >10% divergence is a leakage / feature-pipeline flag.

## Output
`reports/peer_claude-phase2-perf-equity_result_2026-05-31.md` → server-side PR off origin/main.
