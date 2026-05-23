# A/B Test Portfolio Definitions

**Created:** Mar 24, 2026 | **Purpose:** Prove which pick methodology achieves the best risk-adjusted returns

Each portfolio starts with **$500**, uses **Quarter Kelly position sizing**, and tracks the same metrics for apples-to-apples comparison. Positions are checked every 30 minutes for TP/SL hits.

---

## Portfolio A: "Golden Filter" (THE HYPOTHESIS)

**What it is:** Only picks from the 5 most proven Hyperliquid whale traders, filtered by score and multi-timeframe confirmation.

**Exact methodology:**
1. **Trader filter:** Pick must come from one of these 5 verified whale wallets (ranked by total PnL from 341 closed trades):
   - `whale_20.7M` — 57.2% WR, +353.64% PnL, SHORT specialist (69.8% SHORT WR)
   - `NMTD_25M` — 53.1% WR, +100.70% PnL, concentrated on ZEC/AAVE/TRUMP
   - `whale_123M_87roi` — 60.0% WR, +78.11% PnL, $500K on-chain verified
   - `whale_58M_287roi` — 83.3% WR, +11.88% PnL, ultra-fast scalper
   - `lb_NMTD` — 50.0% WR, +10.33% PnL, fast scalper
2. **Score filter:** Elite score must be >= 70 (top quartile = 75.3% WR verified from 2000 closed picks)
3. **MTF gate:** 2 of 3 timeframes (1H, 4H, 1D) must agree with pick direction (EMA9/20 + SMA50 + MACD majority vote)
4. **TP/SL:** 3% take profit / 2% stop loss (1.5:1 R:R)
5. **Sizing:** Quarter Kelly based on realized WR (starts at 55% assumed, adapts after 10 trades)

**Why "Golden":** Backtested at **75.4% WR on 69 picks** using this exact filter combo. Named for the "golden intersection" of trader quality + score quality + timeframe alignment.

**Data sources:**
- Picks: `copy_trader_intel/data/active_picks.json` (strategies matching top 5 trader names)
- MTF: `alpha_engine/mtf_gate.py` (fetches 1H/4H/1D candles from Binance)
- Scores: From pick's `score` or `elite_score` field

---

## Portfolio B: "Golden + RSI Gate"

**What it is:** Same as Portfolio A, plus an RSI overbought/oversold filter to avoid chasing extended moves.

**Additional filter on top of A:**
- Block LONGs when RSI(14) on 1H candles > 70 (overbought — price stretched, likely to reverse)
- Block SHORTs when RSI(14) on 1H candles < 30 (oversold — price compressed, likely to bounce)

**Why test this:** Our DOGE LONG entered at RSI 73 and lost -1.80%. This filter would have blocked it. The question: does it also block good trades?

**TP/SL:** Same as A (3%/2%)

---

## Portfolio C: "Golden + Wide Stops"

**What it is:** Same as Portfolio A, but with wider TP/SL to avoid "shakeout" stop-loss hits.

**Difference from A:**
- TP: **5%** (instead of 3%) — allows bigger winners to run
- SL: **3%** (instead of 2%) — survives normal crypto volatility without premature exit

**Why test this:** Our TP/SL research found `MAX_STOP_DISTANCE_PCT` was silently capping stops at 2% (now fixed to 12%). The 8 LONGs batch-closed at 13:06 had average loss of only 0.76% — stops were in the noise zone. Wider stops may keep us in winning trades longer.

**Trade-off:** Wider SL means bigger individual losses, but potentially fewer false exits.

---

## Portfolio D: "Golden + Tight Stops"

**What it is:** Same as Portfolio A, but with tighter TP/SL for faster trade resolution.

**Difference from A:**
- TP: **2%** (instead of 3%) — captures gains quickly
- SL: **1.5%** (instead of 2%) — cuts losses fast

**Why test this:** Tests the opposite hypothesis from C. If the market is choppy (ADX < 15), tight stops might capture many small wins before they reverse. This is the "scalping" approach to the Golden Filter.

**Trade-off:** More TP hits but also more SL hits. Net effect unknown — that's what we're testing.

---

## Portfolio E: "SHORT Only"

**What it is:** Same as Portfolio A, but only takes SHORT direction picks.

**Why test this:** Our data shows:
- SHORTs: 61.0% WR, +2.49% avg PnL (228 picks)
- LONGs: 40.7% WR, -0.18% avg PnL (113 picks)
- BROKIE portfolio: SHORTs 6/7 green (86%), LONGs 0/3 green (0%)

If SHORTs consistently outperform, a SHORT-only approach might maximize WR even in a BULLISH regime (because individual alts can fall while BTC rises).

**TP/SL:** Same as A (3%/2%)

---

## Portfolio F: "All Copy Traders" (Broader Baseline)

**What it is:** Takes picks from ALL copy traders (not just top 5), with a lower score threshold and no MTF gate.

**Exact methodology:**
1. **Trader filter:** Any copy trader strategy (copy_hl_*, bitget_copy_*, etc.)
2. **Score filter:** Score >= 50 (lower bar than Golden's >= 70)
3. **MTF gate:** NONE — no multi-timeframe confirmation required
4. **TP/SL:** 3% / 2%

**Why test this:** Tests whether the top-5 trader filtering actually adds value. If F performs close to A, the filtering isn't worth the reduced trade count. If A significantly beats F, the top-5 selection is validated.

---

## Portfolio G: "Current Smart Picks" (CONTROL)

**What it is:** Uses whatever the existing Smart Picks engine selects — the 5-dimension scoring system with regime match (40%), elite quality (20%), freshness (15%), TP upside (15%), currently winning (10%).

**Data source:** `alpha_engine/data/smart_picks.json` — the current 10-11 picks per batch

**Why this is the control:** This is what we're trying to BEAT. If any portfolio can't outperform G, the new approach isn't worth implementing. Current Smart Picks have ~64% median snapshot WR but only 1 resolved batch (0% WR, -8.10% PnL).

**TP/SL:** Uses whatever TP/SL the Smart Picks engine assigns (variable per pick)

---

## Portfolio H: "Rocket Scanner"

**What it is:** Uses picks from the rocket scanner, which reverse-engineers the patterns of our best-performing trades (+8-13% winners) and scans 120 pairs for the same setup.

**Methodology:**
1. Scan top 120 USDT pairs by 24h volume on Binance
2. Compute RSI, MACD, EMA9/20/50, volume spikes, accumulation/distribution on 1H candles
3. Backtest each pattern over 30 days (720 bars) with 3% and 5% TP targets
4. Rank by composite (WR × avg_return + signal_score)
5. Cross-reference with copy trader consensus

**Data source:** `alpha_engine/data/rocket_picks.json`

**Current rockets:**
- XLMUSDT LONG (61.9% WR backtest)
- AVAXUSDT LONG (51.4% WR, 4 whale consensus)
- FETUSDT LONG (50.7% WR, 7.88% avg MFE)
- ETHFIUSDT SHORT (51.5% WR)
- ONDOUSDT LONG (50.0% WR, 3 whale consensus)

**TP/SL:** Uses rocket scanner's computed TP/SL (variable, based on backtested average move)

---

## Metrics Compared Across All 8 Portfolios

| Metric | What it Measures |
|---|---|
| **Win Rate** | Closed trades only — % that hit TP before SL |
| **Average Win %** | Mean PnL of winning trades |
| **Average Loss %** | Mean PnL of losing trades |
| **Profit Factor** | Gross wins / gross losses (>1.0 = profitable) |
| **Max Drawdown** | Largest peak-to-trough equity decline |
| **Sharpe Ratio** | Risk-adjusted return (when enough data) |
| **Open Positions** | Current number of active trades |
| **Composite Score** | `return% × (1 - maxDD/100) × (WR/100 + 0.5)` |

---

## How to Interpret Results

- **A beats G** → Golden Filter is better than current Smart Picks (validates the hypothesis)
- **A beats F** → Top-5 trader filtering adds value over broad copy trading
- **B beats A** → RSI gate helps (implement it)
- **C beats D** → Wider stops win (confirms shakeout thesis)
- **E beats A** → SHORT-only is superior (regime-dependent)
- **H beats G** → Rocket scanner outperforms Smart Picks

The first portfolio to reach **10 closed trades with >60% WR** should be considered for production deployment.

---

*Updated: Mar 24, 2026 | Runs every 30 minutes via cron*
