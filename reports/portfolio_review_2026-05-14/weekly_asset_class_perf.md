# Weekly Asset-Class Performance — 2026-05-07 to 2026-05-14

**Source:** `audit_dashboard/data/dashboard_data.json` (3,500 closed picks; refreshed hourly by pipeline)
**Window:** `closed_at` between `2026-05-07T00:00:00+00:00` and `2026-05-14T23:59:59+00:00` (UTC, inclusive)
**Canonical close timestamp field detected:** `closed_at` (sample-500 hit-count: {'closed_at': 500})
**recent_closed total in payload:** 3500 | **in-window:** 951 | **missing ts:** 15
**Earliest closed_at seen:** 2026-02-21T07:08:50+00:00 | **Latest:** 2026-05-14T03:52:38+00:00

> Note: user prompt cited 56 active picks; dashboard payload at read-time contains **47**. Used 47.
> `performance.asset_class_health.wr_pct / pf / pnl_pct` are NULL in payload (only `resolved_n` populated); all WR/PF/PnL numbers below are computed from `picks.recent_closed`.

## One-page summary (week of 2026-05-07 → 2026-05-14)

| Asset Class | n_week | Wins | WR | PF | Σ PnL% | Top Winner (ΣPnL%) | Top Loser (ΣPnL%) |
|-------------|-------:|-----:|----|----|--------|-----|-----|
| CRYPTO | 842 | 352 | 41.8% | 1.21 | +151.75% | ONDOUSDT (+88.90%) | ARBUSDT (-20.11%) |
| FOREX | 45 | 8 | 17.8% | 1.87 | +5.74% | AUDUSD=X (+3.17%) | NZDUSD=X (-1.58%) |
| EQUITY | 35 | 8 | 22.9% | 1.03 | +1.83% | NVAX (+17.28%) | UBER (-8.06%) |
| ETF | 15 | 8 | 53.3% | 1.60 | +6.07% | QQQ (+5.70%) | IWM (-3.66%) |
| COMMODITY | 14 | 14 | 100.0% | inf | +70.22% | CT=F (+53.04%) | — |
| **TOTAL** | **951** | **390** | **41.0%** | **1.29** | **+235.61%** | — | — |

### Top-line read

- **CRYPTO** dominates volume (842/951 = 88.5%). WR 41.8% / PF 1.21 — borderline.
- **COMMODITY** screen-printed 14/14 wins (PF inf, PnL +70.22%). Cotton (CT=F) alone shipped +53.04% across 10 trades — outlier-grade, expect mean-reversion next week.
- **FOREX** WR 17.8% but PF 1.87 — small-sample asymmetry: 8 wins averaged +1.55%/trade while 37 losses averaged -0.18%/trade. Mostly survivable-loss noise, not a true edge yet.
- **EQUITY** WR 22.9% / PF 1.03 — break-even on PnL but a 27/8 loss skew. NVAX (+17.28%) carried the class.
- **ETF** WR 53.3% / PF 1.60 — cleanest profile of the week but n=15 only.

## CRYPTO — week breakdown

**n_week=** 842 | wins=352 | losses=490 | indet=0 | missing_pnl=0
**WR=** 41.8% | **PF=** 1.21 | **ΣPnL=** +151.75% (Σgains 887.06%, Σ|losses| 735.31%)

**Top winners (by ΣPnL%):**
- `ONDOUSDT` — n=130, wins=61 (47%), ΣPnL +88.90%
- `INJ-USD` — n=2, wins=2 (100%), ΣPnL +20.27%
- `INJUSDT` — n=18, wins=9 (50%), ΣPnL +17.06%

**Top losers (by ΣPnL%):**
- `ARBUSDT` — n=14, wins=3 (21%), ΣPnL -20.11%
- `ADAUSDT` — n=20, wins=4 (20%), ΣPnL -18.24%
- `BTC-USD` — n=5, wins=0 (0%), ΣPnL -9.69%

**Source-system breakdown** (sorted by ΣPnL%):

| source_system | n | wins | WR | PF | Σ PnL% | Σ gains | Σ losses_abs |
|---------------|--:|-----:|----|----|--------|--------:|-------------:|
| `quan_engine` | 180 | 65 | 36.1% | 1.36 | +55.31% | 210.57 | 155.26 |
| `kimi_riseoftheclaw` | 25 | 14 | 56.0% | 2.84 | +51.65% | 79.77 | 28.11 |
| `aggregated_picks` | 23 | 13 | 56.5% | 2.14 | +22.49% | 42.20 | 19.71 |
| `baby_strats_forward` | 151 | 82 | 54.3% | 1.58 | +19.91% | 54.25 | 34.34 |
| `dna_winner_picks` | 25 | 14 | 56.0% | 1.90 | +19.84% | 41.91 | 22.07 |
| `super_signals` | 4 | 4 | 100.0% | inf | +15.15% | 15.15 | 0.00 |
| `signal_engine_mutations` | 44 | 18 | 40.9% | 1.33 | +12.10% | 48.72 | 36.62 |
| `mercury2` | 47 | 18 | 38.3% | 1.24 | +10.37% | 54.05 | 43.68 |
| `signal_validation` | 8 | 5 | 62.5% | 3.16 | +10.25% | 15.00 | 4.75 |
| `mega_mutation` | 26 | 11 | 42.3% | 1.27 | +9.19% | 43.60 | 34.41 |
| `claude_gainer_st` | 13 | 6 | 46.2% | 1.02 | +0.07% | 4.23 | 4.17 |
| `copy_trader_highscore` | 11 | 0 | 0.0% | 0.00 | +0.00% | 0.00 | 0.00 |
| `dna_rapid_fire_mutations` | 3 | 1 | 33.3% | 0.73 | -0.95% | 2.55 | 3.50 |
| `ml_crypto_pred` | 4 | 0 | 0.0% | 0.00 | -7.00% | 0.00 | 7.00 |
| `mutation_lab` | 5 | 0 | 0.0% | 0.00 | -7.44% | 0.00 | 7.44 |
| `regime_terminal` | 26 | 6 | 23.1% | 0.60 | -12.00% | 18.00 | 30.00 |
| `battleground` | 29 | 8 | 27.6% | 0.26 | -12.96% | 4.59 | 17.55 |
| `alpha_engine` | 41 | 13 | 31.7% | 0.73 | -14.50% | 39.50 | 54.00 |
| `luxalgo_filters` | 177 | 74 | 41.8% | 0.92 | -19.75% | 212.96 | 232.70 |

## FOREX — week breakdown

**n_week=** 45 | wins=8 | losses=37 | indet=0 | missing_pnl=0
**WR=** 17.8% | **PF=** 1.87 | **ΣPnL=** +5.74% (Σgains 12.36%, Σ|losses| 6.63%)

**Top winners (by ΣPnL%):**
- `AUDUSD=X` — n=2, wins=2 (100%), ΣPnL +3.17%
- `JPY=X` — n=1, wins=1 (100%), ΣPnL +3.06%
- `GBPUSD=X` — n=2, wins=1 (50%), ΣPnL +2.24%

**Top losers (by ΣPnL%):**
- `NZDUSD=X` — n=3, wins=1 (33%), ΣPnL -1.58%
- `EURUSD=X` — n=2, wins=0 (0%), ΣPnL -1.39%
- `USDMXN=X` — n=1, wins=0 (0%), ΣPnL -0.59%

**Source-system breakdown** (sorted by ΣPnL%):

| source_system | n | wins | WR | PF | Σ PnL% | Σ gains | Σ losses_abs |
|---------------|--:|-----:|----|----|--------|--------:|-------------:|
| `kimi_riseoftheclaw` | 10 | 5 | 50.0% | 2.00 | +4.14% | 8.26 | 4.13 |
| `alpha_engine` | 8 | 3 | 37.5% | 1.64 | +1.60% | 4.10 | 2.50 |
| `signal_validation` | 27 | 0 | 0.0% | 0.00 | +0.00% | 0.00 | 0.00 |

## EQUITY — week breakdown

**n_week=** 35 | wins=8 | losses=27 | indet=0 | missing_pnl=0
**WR=** 22.9% | **PF=** 1.03 | **ΣPnL=** +1.83% (Σgains 54.99%, Σ|losses| 53.15%)

**Top winners (by ΣPnL%):**
- `NVAX` — n=1, wins=1 (100%), ΣPnL +17.28%
- `RIOT` — n=1, wins=1 (100%), ΣPnL +9.43%
- `BNGO` — n=1, wins=1 (100%), ΣPnL +4.84%

**Top losers (by ΣPnL%):**
- `UBER` — n=2, wins=0 (0%), ΣPnL -8.06%
- `MSTR` — n=3, wins=0 (0%), ΣPnL -7.62%
- `AVGO` — n=3, wins=0 (0%), ΣPnL -6.00%

**Source-system breakdown** (sorted by ΣPnL%):

| source_system | n | wins | WR | PF | Σ PnL% | Σ gains | Σ losses_abs |
|---------------|--:|-----:|----|----|--------|--------:|-------------:|
| `kimi_riseoftheclaw` | 17 | 7 | 41.2% | 1.43 | +15.06% | 49.99 | 34.92 |
| `stocksunify2` | 11 | 0 | 0.0% | 0.00 | +0.00% | 0.00 | 0.00 |
| `super_signals` | 1 | 0 | 0.0% | 0.00 | -3.23% | 0.00 | 3.23 |
| `multi_asset_copytrader` | 6 | 1 | 16.7% | 0.33 | -10.00% | 5.00 | 15.00 |

## ETF — week breakdown

**n_week=** 15 | wins=8 | losses=7 | indet=0 | missing_pnl=0
**WR=** 53.3% | **PF=** 1.60 | **ΣPnL=** +6.07% (Σgains 16.18%, Σ|losses| 10.11%)

**Top winners (by ΣPnL%):**
- `QQQ` — n=4, wins=3 (75%), ΣPnL +5.70%
- `SPY` — n=5, wins=3 (60%), ΣPnL +2.11%
- `XLK` — n=4, wins=2 (50%), ΣPnL +1.93%

**Top losers (by ΣPnL%):**
- `IWM` — n=2, wins=0 (0%), ΣPnL -3.66%

**Source-system breakdown** (sorted by ΣPnL%):

| source_system | n | wins | WR | PF | Σ PnL% | Σ gains | Σ losses_abs |
|---------------|--:|-----:|----|----|--------|--------:|-------------:|
| `kimi_riseoftheclaw` | 12 | 7 | 58.3% | 1.71 | +6.13% | 14.82 | 8.68 |
| `super_signals` | 3 | 1 | 33.3% | 0.96 | -0.06% | 1.36 | 1.43 |

## COMMODITY — week breakdown

**n_week=** 14 | wins=14 | losses=0 | indet=0 | missing_pnl=0
**WR=** 100.0% | **PF=** inf | **ΣPnL=** +70.22% (Σgains 70.22%, Σ|losses| 0.00%)

**Top winners (by ΣPnL%):**
- `CT=F` — n=10, wins=10 (100%), ΣPnL +53.04%
- `ZW=F` — n=3, wins=3 (100%), ΣPnL +16.38%
- `NG=F` — n=1, wins=1 (100%), ΣPnL +0.80%

**Source-system breakdown** (sorted by ΣPnL%):

| source_system | n | wins | WR | PF | Σ PnL% | Σ gains | Σ losses_abs |
|---------------|--:|-----:|----|----|--------|--------:|-------------:|
| `multi_asset_cot` | 8 | 8 | 100.0% | inf | +41.62% | 41.62 | 0.00 |
| `multi_asset_copytrader` | 5 | 5 | 100.0% | inf | +27.80% | 27.80 | 0.00 |
| `alpha_engine` | 1 | 1 | 100.0% | inf | +0.80% | 0.80 | 0.00 |

## Currently-active picks by provenance (47 total)

- **swarm-tagged:** 5 (11%)
- **dashboard-direct:** 42 (89%)

**Match rule:** active.pick_id ∈ swarm_picks_data.picks.pick_id, OR `(normalized_symbol, direction)` matches a swarm pick. Symbol normalization strips exchange prefix (`BINANCE:`, `COINBASE:`) and perp suffix (`.P`).

| Asset Class | swarm | direct | swarm % |
|-------------|------:|-------:|--------:|
| CRYPTO | 4 | 13 | 24% |
| EQUITY | 1 | 21 | 5% |
| ETF | 0 | 6 | 0% |
| FOREX | 0 | 2 | 0% |

**Swarm-tagged examples:**
- `BNBUSDT` LONG via `fc_crypto_pro` (match=sym+dir)
- `APTUSDT` LONG via `super_signals` (match=sym+dir)
- `INJUSDT` LONG via `tsmom_strategy` (match=sym+dir)
- `PFE` LONG via `ueps` (match=sym+dir)
- `BTCUSDT` LONG via `alpha_engine` (match=sym+dir)

**Dashboard-direct examples (first 5):**
- `XRPUSDT` LONG via `battleground`
- `SAGAUSDT` LONG via `tsmom_strategy`
- `RLUSDUSDT` LONG via `aggregated_picks`
- `APEUSDT` LONG via `super_signals`
- `ZECUSDT` LONG via `tsmom_strategy`

**Swarm picks in the week's exit window** (independent from `recent_closed`): 5 resolved this week (2 wins / 3 losses). 33 swarm picks have no outcome field yet (still open or unresolved).

Swarm-window picks detail:

| symbol | dir | account | exit_reason | exit_time | pnl_pct |
|--------|-----|---------|-------------|-----------|---------|
| `BINANCE:ONDOUSDT` | LONG | zerounderscore | SL_HIT | 2026-05-12 21:22 | -4.27% |
| `BINANCE:ARBUSDT` | LONG | zerounderscore | SL_HIT | 2026-05-12 21:22 | -4.23% |
| `AMEX:USO` | LONG | theswarm | TP_HIT | 2026-05-12 21:22 | +4.33% |
| `FX:USDJPY` | LONG | theswarm | SL_HIT | 2026-05-12 21:22 | -0.43% |
| `NYMEX:MCL1!` | LONG | theswarm | TP_HIT | 2026-05-12 21:22 | +2.85% |

## Where the week diverges from all-time

**Note:** all-time `wr_pct/pf/pnl_pct` are `FIELD_MISSING` in `asset_class_health` (NULL in payload). We can only compare **sample share** and call out classes where the week's WR is materially out of line with the CLAUDE.md anchor numbers (EQUITY PF 1.41/WR 52.7% n=421; COMMODITY PF 1.78/WR 46.9% n=750; BOND PF 1.72/WR 55.6% n=18; CRYPTO PF 1.25/WR 44.6% n=8067; ETF PF 1.24/WR 55.2% n=87; FOREX PF 0.27/WR 46.4% n=1169).

| Class | Week WR | CLAUDE-anchor WR | Δ WR (pp) | Week PF | Anchor PF | Verdict |
|-------|---------|-------------------|-----------|---------|-----------|---------|
| CRYPTO | 41.8% | 44.6% | -2.8 | 1.21 | 1.25 | in-line |
| FOREX | 17.8% | 46.4% | -28.6 | 1.87 | 0.27 | COLD (-10pp WR shift) |
| EQUITY | 22.9% | 52.7% | -29.8 | 1.03 | 1.41 | COLD (-10pp WR shift) |
| ETF | 53.3% | 55.2% | -1.9 | 1.60 | 1.24 | in-line |
| COMMODITY | 100.0% | 46.9% | +53.1 | inf | 1.78 | HOT (+10pp WR shift) |

**Called-out divergences (|Δ WR| > 10pp):**

- **FOREX**: week WR 17.8% vs anchor 46.4% (-28.6pp); week PF 1.87 vs anchor 0.27 (+1.60). Sample n=45 of all-time 1169 (3.8% of cumulative).
- **EQUITY**: week WR 22.9% vs anchor 52.7% (-29.8pp); week PF 1.03 vs anchor 1.41 (-0.38). Sample n=35 of all-time 421 (8.3% of cumulative).
- **COMMODITY**: week WR 100.0% vs anchor 46.9% (+53.1pp); week PF inf vs anchor 1.78 (+inf). Sample n=14 of all-time 750 (1.9% of cumulative).

**COMMODITY 100% WR caveat:** 14/14 wins on n=14 (Σ PnL +70.22%) — 10 of those are `CT=F` (Cotton) winners totaling +53.04%, plus 3× `ZW=F` (Wheat) +16.38%. Three source_systems claim the wins (`multi_asset_cot` 8/8, `multi_asset_copytrader` 5/5, `alpha_engine` 1/1) — overlap on CT=F symbol; this is likely **one or two underlying signals replayed across three source-system labels**. Do not assume 100% WR will persist; expect regression to anchor ~47%.

## All-time `asset_class_health.resolved_n` cross-reference

| Class | all-time resolved_n | week n | week % of all-time | FIELD_MISSING `wr_pct` | FIELD_MISSING `pf` | FIELD_MISSING `pnl_pct` |
|-------|--------------------:|-------:|-------------------:|--|--|--|
| CRYPTO | 7890 | 842 | 10.7% | yes | yes | yes |
| EQUITY | 416 | 35 | 8.4% | yes | yes | yes |
| FOREX | 331 | 45 | 13.6% | yes | yes | yes |
| COMMODITY | 281 | 14 | 5.0% | yes | yes | yes |
| ETF | 106 | 15 | 14.2% | yes | yes | yes |
| BOND | 11 | 0 | 0.0% | yes | yes | yes |
| FUTURES | 0 | 0 | 0.0% | yes | yes | yes |

Classes in `asset_class_health` with **no week activity in `recent_closed`**: FUTURES, BOND.

## Methodology / caveats

- WR denominator is `wins + losses` (indeterminate rows excluded).
- PF = Σ|gains| / Σ|losses_abs|; PF=`inf` means zero losing trades in the window.
- `pnl_pct` is the field's raw value; we do not re-resolve. Per `feedback_noncrypto_resolver_live_close_bug.md`, non-crypto pnl_pct values may still be polluted by the live-close bug for picks that lacked a hard exit_price at resolution time.
- Swarm provenance match is permissive `(symbol, direction)` only because active picks have no `account` field. False positives possible (a dashboard-direct pick that happens to share sym+dir with a swarm pick would be mis-tagged).
- `performance.asset_class_health.wr_pct / pf / pnl_pct` are **FIELD_MISSING** (NULL) in this payload. CLAUDE.md anchors used instead.
- Active count discrepancy: user prompt cited 56; payload had 47 at read time. May reflect a post-prompt pipeline refresh; numbers above are 47-based.

_Generated by `tools/_weekly_perf_analyzer.py` + `tools/_weekly_perf_writer.py` from `dashboard_data.json` (read at 2026-05-14T03:52:38+00:00 UTC)._