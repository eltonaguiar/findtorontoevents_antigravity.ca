---
tags: [session, audit, resolver, edge]
created: 2026-06-06
goal: "#1"
---

# Session: 2026-06-06 — Edge Reality Check + Measurement-Layer Fixes

## Goal
**#1 Audit performance.** Bridge the gap toward money-ready; scrutinize every win-rate/stat for artifacts (resolver, reverse-split, backfill, coin-flip).

## Headline verdict
**No confirmed money-ready edge in ANY asset class today.** Every apparent edge collapsed under adversarial verification into one of three artifacts: backfill-resolver labeling, single-snapshot batch resolution, or **resolver-version selection bias** (the same CRYPTO June data yields PF 0.51 vs 2.15 depending on which resolver ran — a verdict *inversion*). The failure is the **measurement layer, not strategy supply** — the academically-correct sleeves (TSMOM, residual momentum, carry) are already coded but dormant.

## Delivered

- **Picks Now linked from all audit sub-pages** (ai-tournament, pick_funnel, ai_leaderboard, model, incidents) + FTP-deployed, live-verified. incidents.html generator (`render_incidents_page.py`) patched so it survives regen.
- **Baby-strategy CI backtest trap fixed** — `crypto_data.db` is gitignored & absent on runners; built `tools/build_crypto_data_db_from_mysql.py` to materialize the `klines` SQLite from MySQL `crypto_ohlcv`/`stock_ohlcv`/`fx_prices`. Wired into both backtest workflows. CI run 27056319122 ✓. Also fixed a `SystemExit`-on-import crash that aborted the whole sweep. Recovered 3 DNA strategy files lost to shared-tree churn.
- **Price-failover hardening** — FRED commodity series tagged `is_proxy`/spot (enricher now skips them for futures PnL); OER/Finnhub cross-rate `.get` None-checks; FMP restricted to metals/energy symbols.
- **Picks-now generator honesty** — WR now counts EXPIRED (GBPUSD 58.8%→6.9%); banned sources + backfill rows excluded; per-class TP/SL caps; negative-expectancy demotion.
- **Backfill quarantine** in canonical `build_pf_registry.py` — excludes `backfill_*` resolver labels + NULL-resolved rows (**77.8%** of WON/LOST rows were contamination).
- **Per-class sane-pnl guard** (FX ≤20%, COMMODITY ≤30%, BOND ≤25%, CRYPTO ≤95%, EQUITY/ETF ≤50%) in pf_registry + picks-now — drops reverse-split + feed-bug artifacts (CADJPY=X +428%, NZDUSD=X ±100%).
- **Intrabar re-resolution dry-run tool** (`tools/reresolve_intrabar.py`) — de-biased fixed-horizon replay; CRYPTO orig WR 52.3% → **intrabar-true 42.9%, PF 1.22**, 26.4% of picks had SL touched before TP. `--apply` gated for operator greenlight.
- **Reverse-split investigation** — `stock_ohlcv` (187 syms) is CLEAN of splits; the real contamination is FX feed bugs.
- 27 confirmed audit findings + 4 P0/P1 resolver incidents + academic roadmap → documented in INCIDENT_*/ENHANCEMENT_* tables.

## Blockers / Open

- **GATING DEPENDENCY: `crypto_ohlcv` holds only the last 30 days** of contiguous 1h bars (BTCUSDT = 720 bars). Intrabar re-resolution can't cover the full pick book until ~6–12 months of 1h history is backfilled. Next step (awaiting scope confirm): build deep-history ingestion via Binance→CoinGecko→KuCoin failover.
- `reresolve_intrabar.py --apply` (rewrite artifact labels) — backup-first, awaits operator greenlight.
- Academic sleeves (TSMOM/residual-momentum/carry) wiring — only AFTER resolver is trustworthy.

## Key Stats Changed

| Class | "Reported" | Honest (clean cohort) | Source |
|-------|-----------|----------------------|--------|
| CRYPTO | ~52% WR / "edge" | 42.9% WR / PF 1.22 (intrabar) — coin flip | reresolve_intrabar |
| FOREX | PF 2.30 | no edge (90% backfill + feed bugs) | edge audit |
| EQUITY | — | not durable (single-snapshot) | edge audit |
| COMMODITY | — | PF 0.41, negative expectancy | edge audit |
| pf_registry outcomes | all rows | 77.8% quarantined as backfill | build_pf_registry |
| Money-ready survivors | — | 0 confirmed (luxalgo borderline artifact) | money-ready screen |

## Related

- [[incidents/resolver-intrabar-blocker]]
- [[incidents/ai-tournament-wr-artifact]]
- [[reference/data-sources-price-failover]]
- [[strategies/READY-TO-TRADE-NOW]]
- Reports: `reports/2026-06-06-per-asset-class-edge-reality-and-academic-roadmap.md`, `reports/2026-06-06-money-ready-screen-clean-cohort.md`
