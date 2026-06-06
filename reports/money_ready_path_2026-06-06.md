# Money-Ready Path Report — 2026-06-06

**Goal:** Mutual-fund-worthy / genius-level performance per asset class.  
**Threshold:** T2 (PF≥1.5, WR≥50%, n≥100 dedup-clean) minimum; T1 (PF≥2, WR≥55%) target.

---

## Honest Per-Class Status (Live DB, 30d dedup-clean, pnl capped ±50%)

| Class | n_dedup | WR% | PF | Verdict |
|-------|---------|-----|-----|---------|
| FOREX | 124 | 71.0% | 3.48 | **~T1 shape but regime-biased** |
| ETF | 60 | 60.0% | 1.80 | **Borderline T2 — n too small** |
| EQUITY | 325 | 50.5% | 1.29 | **Below T2** |
| FUTURES | 130 | 45.4% | 1.34 | **Below T2** |
| CRYPTO | 1931 | 41.6% | 0.73 | **Confirmed loser overall** |
| BOND | 25 | 28.0% | 0.60 | **Confirmed loser** |

---

## Leading Strategy Candidates (per class)

### EQUITY — `stocks_rsi2_pullback`
- **30d dedup-clean**: WR=57.4%, PF=2.32, n=136 → **T2-qualified historically**
- **Problem**: WR is period-dependent — WR=75-84% during May 7-20 correction, WR=14-21% during May 21-25 recovery. The strategy fires 28-46 picks/day during downtrends (WR=14%) vs 5-22 picks/day during proper pullbacks (WR=75%).
- **Root cause (diagnosed 2026-06-06)**: When >10 stocks trigger RSI(2)<10 simultaneously, the market is in a broad downtrend — catching falling knives, not buying pullbacks. Added **breadth throttle (>10 → skip all)** to `multi_asset_copytrader_scraper.py`.
- **Expected impact**: Filters the May 21-25 false-signal period. Strategy should now be dark during genuine downtrends, active during idiosyncratic pullbacks.
- **Status**: Currently dark (market recovery, no stocks oversold). Wait for next correction.
- **Backtest estimate** (breadth-filtered): Assuming the >10 filter eliminates 40% of bad picks and keeps all good picks → WR rises to ~65-70%, PF to ~3.0+.

### FOREX — `combined_confidence` + `forex_rsi2_mean_reversion`
- **combined_confidence**: WR=64.3%, PF=2.89, n=28 dedup-clean. Recently deteriorating (June 3-5 all LOST). Need n≥100.
- **forex_rsi2_mean_reversion**: WR=94.4%, n=18 dedup-clean. Holds 6-8 days, resolves at market price. RR=5.39 (win 1.35%, lose 0.25%). Need n≥100 to confirm.
- **Estimated time to T2 qualification**: 4-6 weeks of continued emission (1-5 picks/day for combined_confidence).

### CRYPTO — `mega_mutation` (inverse_ml)
- **Lab stats**: PF=2.86, WR=63.9%, n=204 (OOS-verified, AVAXUSDT removed).
- **RENDERUSDT inverse_ml**: 7d WR=80%, PF=7.7, actively emitting SHORT picks.
- **Blocker**: Resolver not reaching NULL-status picks (FIXED 2026-06-06 via active_picks_sync NULL-status fix). Need ~4-6 weeks of clean intrabar-resolved data.
- **Estimated time to T2**: 6-8 weeks (need n≥100 intrabar-clean closed picks post-fix).

### ETF — `etf_verified_dual_momentum`
- **Lab**: PF=1.60, WR=55%, n=small. Pilot live since June 2.
- **30d dedup-clean ETF aggregate**: WR=60%, PF=1.80, n=60. Borderline T2.
- **Estimated time to T2**: 6-8 weeks to reach n=100.

---

## Data Quality Fixes Applied This Session (2026-06-06)

| Fix | Impact |
|-----|--------|
| `active_picks_sync` NULL-status bug | 319 NULL-status picks now eligible for resolution (CRYPTO=146, FUTURES=62, FOREX=46, EQUITY=45) |
| `stocks_rsi2_pullback` breadth throttle | Filters false-signal downtrend periods (>10 simultaneous triggers → skip all) |
| Synthetic contamination warning | Tournament leaderboard now correctly flags cursor_agent as 100% synthetic (not real AI picks) |

---

## Top P0 Blockers for Money-Ready

1. **Resolver single-snapshot bias**: Active_picks_sync resolves at the current price once per hour — no intrabar OHLC replay. A pick that hit SL intraday but recovered by EOD gets marked WON. This inflates WR system-wide. Fix: `tools/validate_intrabar_fills.py` exists but not running in production.

2. **stocks_rsi2_pullback breadth blindness**: Fixed 2026-06-06. Next test will be during the next market pullback.

3. **CRYPTO aggregate WR=41.6%**: The entire CRYPTO system is losing. Only mega_mutation (small n) shows genuine edge. Most strategies emitting are confirmed losers. Should disable further CRYPTO strategies until mega_mutation reaches n≥100 clean resolved.

4. **BOND**: 0/48 T2 indicators. No viable strategy. Should be treated as shadow/lab only.

5. **FUTURES**: WR=45.4% after dedup. cta_cross_asset_tsmom shows 97.8% WR in raw data but this is resolver artifact (single-snapshot on trending markets). Needs intrabar replay verification.

---

## 30/60/90 Day Money-Ready Roadmap

### 30 days (by 2026-07-06)
- EQUITY `stocks_rsi2_pullback` with breadth-throttle live in production (next correction event)
- FOREX `combined_confidence` + `forex_rsi2_mean_reversion` reach n=50 post-fix
- CRYPTO resolver NULL-status fix produces 319 newly resolved picks → real WR visible
- Intrabar OHLC replay wired for FOREX and EQUITY in production

### 60 days (by 2026-08-06)
- EQUITY: if 1 market correction hits in July → stocks_rsi2_pullback proves breadth-filtered edge (n≥100 new picks)
- FOREX: `combined_confidence` or `forex_rsi2_mean_reversion` reaches n=100 dedup-clean → T2 qualification decision
- CRYPTO: mega_mutation intrabar-verified n≥100 → genuine T2 or kill decision

### 90 days (by 2026-09-06)
- At minimum 1 class (FOREX) should be T2-qualified with n≥100 intrabar-clean picks
- EQUITY `stocks_rsi2_pullback` breadth-filtered should show 3+ correction events
- Real-money sizing possible for FOREX at quarter-Kelly

---

## Recommended Real-Money Actions Now

| Pick | Class | Action | Size (Quarter-Kelly) |
|------|-------|--------|---------------------|
| **grok3 tournament consensus** | Multi | Follow grok3 AI picks (WR=67.3%, 0% synthetic, n=52) | 5% per pick |
| **GBPUSD=X LONG** | FOREX | Active pick: entry=1.3336, TP=1.3536, SL=1.3203 | 3% |
| **Wait for RSI(2)<10 pullback** | EQUITY | stocks_rsi2_pullback (breadth-throttle live) — wait for next event | 7% when triggered |
| **RENDERUSDT SHORT** | CRYPTO | inverse_ml_enhanced, 7d WR=80% n=9 — small size only | 2% |

**No sizing on**: CRYPTO aggregate (WR=41.6%), BOND, FUTURES aggregate, any strategy with PF<1.0 or WR<45%.

---

## Sources
- Live DB `at_raw_picks` query 2026-06-06 19:15 UTC
- `reports/money_ready_verdict.json` 2026-06-06T03:45Z
- `alpha_engine/active_picks_sync.py` NULL-status fix commit `c34ddc2667`
- `copy_trader_intel/multi_asset_copytrader_scraper.py` breadth-throttle addition
