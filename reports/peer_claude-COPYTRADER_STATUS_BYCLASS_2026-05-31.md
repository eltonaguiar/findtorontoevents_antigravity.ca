# CopyTrader Data Feed Status — By Asset Class
Date: 2026-05-31 22:15 UTC
Author: peer_claude (read-only audit; no DB writes)
Trigger: user concern — "status of copytrader data feeds … which were supposed to get us proper trades by edge"
Source: `trading_picks` live DB (ejaguiar1_stocks), GHA run history, repo grep

## TL;DR

- **Total copytrader (strategy × source_system × category) feeds with picks**: **87**
- **Silent feeds (>48h since last pick)**: **74 of 87 (~85%)**
- **Silent by asset class**: CRYPTO 34, FOREX 18, COMMODITY 10, EQUITY 5, INDEX 3, BOND 3, FUTURES 1
- **Root cause #1**: most of the silent feeds are **single-pick legacy strategies** (n=1–10) emitted once in Mar–Apr and never re-fired — these aren't broken scrapers, they're **stale per-symbol leaf strategies** that the meta-scraper stopped emitting. Real broken-scraper count is smaller.
- **Genuinely broken feeds** (had a sustained run, then went silent): `forex_copy_trader` (last 165h ago), `copy_trader_consensus` (215h), `copy_trader_myfxbook` (1587h ≈ 66d), `copy_trader_binance` (1598h), `copy_trader_bitget` (1598h), `copy_trader_clones` (1762h).
- **The MONITOR-flagged sources (`copy_trader_highscore`, `fc_crypto_pro`) are NOT writing to `trading_picks` at all** — they emit to JSON sidecars only (`copy_trader_intel/data/scored_picks.json`, `data/fc_crypto_pro_picks.json`). Their GHA workflows are green-and-fast (18–46s success runs every 2h), but the JSON outputs are stale (May 25 and May 29 respectively). Empty output → no pick.

## Healthy feeds (<24h, producing picks now)

| source_system | last_pick (UTC) | total picks | hrs silent |
|---|---|---:|---:|
| multi_asset_copytrader | 2026-05-31 21:24 | 16,460 | 0 |
| copy_trader_polymarket | 2026-05-31 21:40 | 1,142 | 0 |
| copy_trader_bybit | 2026-05-31 17:25 | 16 | 4 |
| copy_trader_intel | 2026-05-31 10:39 | 561 | 11 |

GHA: `copy-trader-forward-test.yml`, `copy-trader-intelligence.yml`, `copytrader-tracker.yml` — all green, last runs <2h, durations 7–34m (intelligence) / 30s (tracker). No workflow failure pattern.

## Silent feeds by asset class

### CRYPTO — 34 silent (worst class)

Real PM whales that went silent (the high-conviction copy-trade names):
- `copy_pm_comtruise` (56h), `copy_pm_justdance` (128h), `copy_pm_elpolloloco` (820h), `copy_pm_jnsttrdrbnusfnd` (92h), `copy_pm_pm_fb1c3c1a` (470h) — Polymarket whales stopped trading or scraper-resolver lost the address.
- `copy_hl_whale_7.7M_acct` (673h ≈ 28d), `copy_hl_whale_168roi_monthly` (1034h ≈ 43d), `copy_hl_whale_433roi` (1762h ≈ 73d) — Hyperliquid whale clones; the resolver/binding to live HL addresses appears stale.
- `binance_smart_money` (1598h), `bitget_copy_elbullmino` (1598h) — `copy_trader_binance` + `copy_trader_bitget` source_systems are **dead** (single source emission ~Mar 26, no workflow runs producing picks since).
- Several `ml_enhanced_*USDT_*` strategies routed via `multi_asset_copytrader` and `copy_trader_intel` are one-shot (n=1) from Mar/Apr — these are leaf strategies that should fold up into a parent feed.

### FOREX — 18 silent

- `forex_copy_trader` source_system **last pick 2026-05-25 00:49** (165h silent, n=229). This is the most-likely "we were getting forex copytrader edge and it died" candidate.
- `myfxbook_retail_contrarian` × `forex_copy_trader` last 165h ago — same source death.
- `copy_trader_myfxbook` last pick 2026-03-26 (1587h ≈ 66d silent). Entire MyFXBook fade strategy family (NZDCHF, NOKJPY, CADCHF, ZARJPY, etc.) has been dark for two months.
- IG sentiment + `forex_zscore_200d_fade` + `forex_carry_momentum` all 232–757h silent.

### COMMODITY — 10 silent

- Active: `futures_bb_mean_reversion` (n=248) + `futures_momentum` (n=2053) under `multi_asset_copytrader` — picks 0h ago.
- Silent: `cftc_cot_commercial_signal` (280h), `cta_golden_cross_200` (1300h), `futures_ema_stack_momentum` (1416h), `cta_commodity_momentum_term` (1435h), `cot_positioning` (1762h), `cta_cross_asset_tsmom` (1762h). Mix of one-shots + a possibly-broken CFTC-COT scraper (>2 weeks silent).

### EQUITY — 5 silent (mostly one-shot leaf strats)

- `stocks_rsi2_pullback` × `copy_trader_intel` (255h, n=1), `stocks_rsi2_pullback` × `forex_copy_trader` (972h, n=1), `cta_golden_cross_200` × `copy_trader_intel` (1762h, n=1), `stocks_rsi2_pullback_wide` × `copy_trader_intel` (1762h, n=1), and an empty-strategy row with category `EQUITY` (49h, n=1) — junk row.

### INDEX — 3 silent

- `futures_connors_rsi2` (80h), `futures_bb_mean_reversion` (115h), `futures_momentum` (912h). All `multi_asset_copytrader`. INDEX is a small surface; these are likely just symbol-rotation lulls.

### BOND — 3 silent

- `futures_momentum` (288h), `futures_bb_mean_reversion` (295h), `futures_ema_stack_momentum` (1418h). Matches `asset_class_health` BOND INSUFF-N (n=8). The bond futures contract list in `multi_asset_copytrader` may be too narrow / `ZN`/`ZB` symbols stopped resolving.

### FUTURES — 1 silent

- `futures_connors_rsi2` (484h). One-shot.

## Root causes (ranked)

1. **STALE_LEAF_STRATEGIES (~55% of silent count)**: many "silent feeds" are 1–10-pick one-shot leaf strategies emitted by `multi_asset_copytrader` / `copy_trader_intel` in Mar–Apr that never fired again because the symbol rotated out of the universe. Not a broken pipe — a registry-pruning issue.
2. **DEAD_SOURCE_SYSTEMS**: `copy_trader_myfxbook` (66d dark), `copy_trader_binance` (67d), `copy_trader_bitget` (67d), `copy_trader_clones` (73d). These four `source_system`s have not emitted **any** pick in 2+ months. Need to confirm whether the scrapers were retired on purpose or silently died (no GHA workflows matching these names found — likely retired).
3. **forex_copy_trader stalled 2026-05-25**: 165h ago and growing. This is the **highest-impact freshly-silent feed**. No matching GHA workflow file by that name; probably emitted by `copy-trader-intelligence.yml` (green, no failure) — so the workflow runs but the scraper inside hits empty results. Needs log-dive into `copy-trader-intelligence.yml` recent runs for the FOREX path.
4. **JSON-sidecar feeds not landing in DB**: `copy_trader_highscore` (scored_picks.json May 25 stale) and `fc_crypto_pro` (May 29 stale) emit to JSON, not `trading_picks`. The `/audit` MONITOR list reads the JSON mtimes, hence the "167h"/"144h" silent flag. Workflows are green-and-short (sub-30s success) → **early-exit path producing zero qualifying picks**, not infra failure.
5. **Polymarket whale binding rot**: 5 of the top crypto silent feeds are `copy_pm_*` whale addresses. Either the whales stopped trading, or the resolver lost the wallet binding (Polymarket UI redesigns periodically break the address scraper).

## Recommendations

- **Don't kill the source_system**, kill the **leaf strategy registry** — prune any `(category, strategy, source_system)` triple with `n<=10` and `last_pick > 30d` from active scoring. This drops the apparent silent-feed count from 74 → ~30 without touching live infrastructure.
- **Triage `forex_copy_trader` (FOREX, 165h silent)** — pull the last 7 days of `copy-trader-intelligence.yml` step logs (`gh run view --log`) for the FOREX scraper step. If the upstream MyFXBook / IG endpoints changed, file a P1.
- **Confirm `copy_trader_myfxbook` / `_binance` / `_bitget` / `_clones` are intentionally retired** — if yes, blocklist them in `BLOCKED_SOURCE_SYSTEMS` so the MONITOR page stops flagging them.
- **Wire JSON-sidecar feeds (`copy_trader_highscore`, `fc_crypto_pro`) into `trading_picks`** OR change the MONITOR page to read both DB + JSON sources so it doesn't false-flag a working JSON-only feed as silent when the workflow is healthy and the file is just empty.
- **Polymarket whale-list refresh job**: schedule a weekly Polymarket leaderboard re-scrape to re-bind the top-N copy targets; current bindings are sticky and rot when whales go inactive.

## Files / evidence

- DB query: `SELECT category, strategy, source_system, MAX(created_at), COUNT(*) FROM trading_picks WHERE strategy LIKE '%copy_trader%' OR strategy LIKE '%copytrader%' OR strategy LIKE '%fc_crypto%' OR source_system LIKE '%copy_trader%' OR source_system LIKE '%fc_crypto%' GROUP BY ...` — 87 rows.
- GHA: `copy-trader-forward-test.yml`, `copy-trader-intelligence.yml`, `copytrader-tracker.yml`, `fc-crypto-pro.yml` — all green, last runs <2h. No failure pattern.
- Stale JSON: `copy_trader_intel/data/scored_picks.json` mtime 2026-05-25, `data/fc_crypto_pro_picks.json` mtime 2026-05-29.
- `alpha_engine/quarantine_manifest.json` line 103: `copy_trader_highscore` entry exists but is empty `{}`.
- `alpha_engine/audit_sync.py` lines 47/143/443/537: source defined, no DB-write path for highscore — it stays in JSON.
