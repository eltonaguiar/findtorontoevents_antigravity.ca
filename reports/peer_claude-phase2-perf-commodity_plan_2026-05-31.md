# Phase-2 Performance Audit — COMMODITY — Plan (2026-05-31)

## Scope
- DB: `ejaguiar1_stocks.trading_picks`
- Filter: `category = 'commodity'` AND `closed_at IS NOT NULL`
- Universe (15 symbols): CL=F, CT=F, GC=F, HG=F, KC=F, NG=F, PL=F, SB=F, SI=F, USO, XAUAUD, XAUEUR, ZC=F, ZS=F, ZW=F
- Total commodity rows: 6,516; closed: 712 (post P0 batch 2026-05-31).

## Method
1. **Per-strategy table**: group by `strategy` where closed; require n >= 10 to display, n >= 100 to grade against T2.
2. **Class-aggregate**: one row over all closed commodity picks.
3. **PF/WR computation**: `WON | TP_HIT` counted as win; PF = sum(pnl_pct>0) / |sum(pnl_pct<0)|.
4. **MDD proxy**: equity curve from time-ordered pnl_pct cumsum, peak-to-trough drawdown.
5. **pf_registry cross-check**: load `audit_dashboard/data/pf_registry.json` (commodity block) and diff PF values; flag |Δ| > 10% PF or > 1.0 absolute.
6. **Anomaly flags**: leftover crypto-suffix symbols (USDT/BTC) tagged commodity; CT=F (cotton) concentration > 30% (known from M-067).

## T2 thresholds (graduation bar)
- PF >= 1.5
- WR >= 50%
- MDD < 20%
- n >= 100

## T1 (Renaissance) target
- PF >= 2.0, WR >= 55%, MDD < 10%, n >= 100

## Risk caveats
- Per CLAUDE.md, COMMODITY is FAIL+INSUFF-N (PF 0.31 / WR 11% / n=28, CT=F 57% concentration on 2026-05-24). Post-P0 sample is now ~712; concentration may persist.
- SL-tuning conclusions are unreliable without intrabar price-path replay (per session memory 2026-05-31).
- pf_registry may be stale relative to today's resolver fixes (M-067 + 2026-05-31 batch).

## Output
- Per-strategy markdown table → result file.
- Promotable / Watchlist / Retire candidates.
- pf_registry divergences.
- 1–2 line graduation/kill recommendation.

## Read-only guarantee
No DB writes. No code edits. Only `SELECT` against `trading_picks` + JSON read of `pf_registry.json`. Single docs PR off `origin/main`.
