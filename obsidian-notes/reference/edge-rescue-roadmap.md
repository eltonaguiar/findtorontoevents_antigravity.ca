---
tags: [reference, roadmap, edge, money-ready]
created: 2026-06-09
status: active
---

# Edge Rescue Roadmap — From Coin-Flip to Statistical Edge

> Live page: `findtorontoevents.ca/audit/edge_validation_roadmap.html`
> Sources: `reports/2026-06-06-per-asset-class-edge-reality-and-academic-roadmap.md`, `reports/2026-06-06-money-ready-screen-clean-cohort.md`

## The honest state (2026-06-09)
**No asset class has a confirmed money-ready edge.** Every apparent edge is an artifact — backfill labels, single-snapshot batches, resolver-version selection bias (same CRYPTO data → PF 0.51 vs 2.15 by resolver), 70–95% TIME_EXPIRED, or reverse-split/feed-bug pnl (CADJPY +428%). Clean-cohort screen: **0 survivors**. The failure is the **measurement layer**, not strategy supply.

## Verified DB facts
- `bt_backtest_trades` = 32,676,918 rows (`ejaguiar1_backtests`) — mostly synthetic backtests.
- `eagle2_consensus_picks` = 15 rows (`ejaguiar1_backtests`) — tiny production-consensus signal.
- FOREX money_ready: WR 24% / PF 0.077 / n=25 — not winning.
- `crypto_ohlcv` = ~30 days of contiguous 1h bars only (gating limit for intrabar truth).

## Shipped this session (read-side honesty)
- Backfill quarantine in `build_pf_registry.py` (77.8% of WON/LOST rows excluded).
- Per-class sane-pnl guard (drops reverse-split/feed-bug artifacts) in pf_registry + picks-now.
- picks-now: EXPIRED-honest WR, banned-source + backfill exclusion, TP/SL caps, neg-expectancy demotion.
- `tools/reresolve_intrabar.py` (de-biased dry-run): CRYPTO 52.3% → 42.9% WR / PF 1.22, 26.4% TP→SL.

## The forward plan (SAVE-1..5 — in `ENHANCEMENT_OVERALL`)
1. **SAVE-1** Backfill deep OHLCV history (`crypto_ohlcv`/`stock_ohlcv`, ~6–12mo) — gating dependency.
2. **SAVE-2** Make intrabar OHLC replay the PRODUCTION resolver (all classes) + `reresolve_intrabar --apply` (backup-first).
3. **SAVE-3** Re-baseline on clean+intrabar cohort → paper-pilot survivors only (n≥100/3mo/PF>1.5/WR>52%/intrabar/multi-source).
4. **SAVE-4** Wire dormant academic sleeves (TSMOM / residual-momentum / carry) — ONLY after SAVE-2.
5. **SAVE-5** ROI dashboard + 6-month kill switch on paid AI spend.

> **Rule:** real capital only after a sleeve holds the full bar on a FORWARD (post-fix) cohort for ≥4 weeks.

## Related
- [[sessions/2026-06-06-edge-audit-and-resolver-fix]]
- [[incidents/resolver-intrabar-blocker]]
- [[strategies/READY-TO-TRADE-NOW]]
- [[reference/performance-tiers]]
