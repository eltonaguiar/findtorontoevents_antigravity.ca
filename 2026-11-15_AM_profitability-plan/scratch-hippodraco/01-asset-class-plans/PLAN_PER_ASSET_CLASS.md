# Per-Asset-Class Plan to Reach Profitability
**Date:** 2026-11-15  
**Scope:** All asset classes the system has attempted to predict (CRYPTO, EQUITY US, COMMODITY/FUTURES, ETF, BOND, FOREX, MUTUAL FUNDS, PENNY/MEME).  
**Core rule:** Nothing advances to capital until it cleans measurement, passes clean out-of-sample gates, and beats a transparent benchmark. All classes currently return `sizing_allowed: false`.

---

## Phase gating (applies to every class)

| Phase | Goal | Entry gate | Exit / promotion gate |
|-------|------|------------|-----------------------|
| **P0 Measurement integrity** | Recompute PnL from entry/exit vs real market data; flag blanks, stale opens, missing exits, cost leakage | Dashboard `generated_at` < 2h old; DB reachable via `tools/db_env.py` | Zero fabricated-flat rows (exit==entry unconfirmed); zero blank `entry_price`/`current_price` on displayed picks |
| **P1 Clean cohort screen** | Recompute WR/PF with mandatory filters (no backfill labels, no banned sources, sane-pnl guard, EXPIRED=non-win, intrabar validation) | ≥1 survivor with n≥50 clean, ≥3 months, PF>1.5, WR>52% EXPIRED-inclusive, intrabar-validated, multi-source | As of 2026-06-09: **0 survivors** — do not proceed to P2 until Gate P1 passes |
| **P2 Benchmark test** | Pre-registered test vs transparent benchmark (SPY total return for equity/ETF) | n≥100 forward, PF≥1.15 after costs, clean OOS | Beat benchmark with statistical significance (DSR≥0.95, correct nb_trials) |
| **P3 Paper pilot** | ≥4 weeks forward paper trading, no real capital | Positive expectancy, PF trending ≥1.3, no July-style (−64pp) month | PF≥1.5, WR≥50%, MDD<20% at stated sizing (T2 charter) |
| **P4 Live sizing** | ¼ Kelly (≈2.5%/trade), DD-halt, concentration caps | T2 certified | Kill if any month PF<0.5 twice, or 3-month rolling PF<1.0 |

---

## Plan per asset class

### 1. EQUITY (US) — highest-priority research slot
**Current state:** Recent PF ~0.70; historical snapshot PF ~1.41, WR ~53%, n~400+. Only class with a pre-registered benchmark test path vs SPY total return and some positive cost-margin signals. Only proven sleeve: `stocks_rsi2_pullback` (75.7% WR, p=6×10⁻⁶, Sharpe 4.84, SPY/QQQ).

**Plan:**
1. **P0:** Fix measurement — recompute equity PnL from real Nasdaq daily close; remove fabricated-flat `TIME_EXIT` rows (exit==entry stamped same second); backfill `entry_time` for 1,745 blank rows (~49.9% of `recent_closed`).
2. **P1:** Clean cohort screen with mandatory filters; isolate `stocks_rsi2_pullback` and any other sleeve passing PF>1.5/n≥100.
2. **P2:** Pre-registered SPY total-return benchmark test (equity-specific). Require n≥500 forward, PF≥1.15 after costs, clean OOS, DSR≥0.95 with correct `nb_trials` (all strategies tested that season, not nb_trials=1).
3. **P3:** Paper pilot ≥4 weeks; size at ¼ Kelly; daily −2% soft-stop; rolling 30d DD halt at 30%.
4. **P4:** Live only if T2 certified (PF≥1.5, WR≥50%, MDD<20% on forward record).

**Success definition:** A systematic equity sleeve that beats SPY total return on clean OOS with published n. Probability: moderate.

---

### 2. ETF — most promising current class, but n at floor
**Current state:** Sparse upstream; historical PF ~1.24, WR ~55%, n~87; zero live picks; SPY sometimes miscategorized as equity. Profitable approach shows ETF n=120, PF 1.21 (+26.5pp), WF consistency 100%, OOS WR 75%, decay +23% — cleanest OOS profile.

**Plan:**
1. **P0:** Fix classifier so SPY is not miscategorized as equity; fix ETF PnL normalization (NAV close-to-close, expense-ratio drag modeled).
2. **P1:** Expand ETF universe (XLF, XLE, XLK, plus broad-market and bond ETFs) to clear n≥150 for OOS_READY. Apply mandatory filters.
3. **P2:** Benchmark vs SPY / appropriate ETF benchmark; require PF≥1.3 maintained, n≥150.
4. **P3:** Paper pilot; size conservatively (ETFs have expense-ratio drag and lower vol).

**Success definition:** ETF sleeve with PF≥1.3, n≥150, clean OOS vs benchmark. Probability: moderate. **Not yet proven.**

---

### 3. CRYPTO — highest volume, currently sub-T2
**Current state:** Recent PF ~0.74, WR ~33%. Historical elite PF 2.3–4 but overall dragged lower. Intrabar replay drops CRYPTO 52.3%→42.9% WR / PF 1.22; 26.4% of TP_HITs hit SL first. Toxic crypto sources excluded by the profitable-approach gate (CRYPTO appears once in the entire forward set).

**Plan:**
1. **P0:** Blocking dependency — backfill `crypto_ohlcv` to ≥180 days of 1h bars (currently ~30d). Without this, intrabar re-resolution cannot run and no crypto edge is trustworthy.
2. **P1:** Run `tools/reresolve_intrabar.py --apply` after backfill; apply mandatory filters; exclude backfill labels and banned sources.
3. **P2:** Benchmark vs BTC-USD / sector basket; require PF≥1.5 after costs (fees/funding/slippage tiers), n≥100, intrabar-validated.
4. **P3:** Paper pilot; size small (crypto round-trip cost ~30bp = 30% of average trade per cost model; 3x cost gate is strict).

**Success definition:** Crypto sleeve passing clean OOS vs BTC-USD benchmark with realistic costs. Probability: low until OHLCV backfill completes.

---

### 4. COMMODITY / FUTURES — better historical PF, low n
**Current state:** Historical PF ~1.78, WR ~47%, n~750; better historical PF but still unproven. FUTURES is "dead" (5.9% WR, −96% PnL, zombie tile; real futures hidden under COMMODITY). COMMODITY generator maps crypto proxies (RNDR→silver, XLM→oil) — no real feed exists.

**Plan:**
1. **P0:** Do NOT blind-unblock FUTURES/COMMODITY. Fix symbol→instrument mapping (no crypto proxies labelled COMMODITY). Get real commodity feed + contract specs (multiplier, tick value, margin, roll schedule).
2. **P1:** Rebuild COMMODITY closed set with real instruments; apply mandatory filters; n is too small (~18-46 clean) — accumulate ≥50 post-dedup before any edge claim.
3. **P2:** Benchmark vs appropriate continuous futures / cash commodity; model contango/backwardation, storage/roll where relevant.
4. **P3:** Paper pilot only after real feed + costs (commissions + slippage in ticks + financing).

**Success definition:** Real-instrument commodity sleeve with PF≥1.5, n≥50, clean OOS. Probability: low until feed/mapping fixed. **Blind unblock is vetoed.**

---

### 5. BOND — very sparse, thin
**Current state:** PF ~1.72, WR ~56%, n=18; accumulating; n far below floor. FRED data unblock needed for scanner wire-up.

**Plan:**
1. **P0:** Set `FRED_API_KEY` in repo secrets (yield curves, VIX, DXY) — unblocks BOND scanner (0 picks since ~Apr 2026).
2. **P1:** Decide bond-ETF vs true-bond scope; if ETFs, model distributions + expense ratio; build EOD/NAV pipeline (not intraday TP/SL).
3. **P2:** Benchmark vs TLT/IEF/AGG total return; require n≥50 (working toward 100), PF>1.5 after costs.
4. **P3:** Paper pilot; size small (bond vol is lower but drawdowns can be sharp in rate regimes).

**Success definition:** Bond sleeve with clean OOS vs total-return benchmark, n≥100 eventually. Probability: low until n accumulates.

---

### 6. FOREX — active but poor; weakest class
**Current state:** Recent PF ~0.85; historical PF 0.27 (sub-floor); high n but catastrophic clean PF (true 14d WR ~5%, PF 0.077). Mutation-before-kill protocol in progress.

**Plan:**
1. **P0:** Do not promote. Apply mutation protocol — evaluate LONG-direction block (SHORT-axis shows 57% WR vs LONG 21% on `ig_contrarian_sentiment`, 36pp spread, but no strategy passes DSR≥0.5).
2. **P1:** Enforce realistic costs (spread ~1-2 pips = ~4bp/side + rollover/funding if overnight). Most retail FX pipelines underestimate spread impact on mean-reversion.
3. **P2:** Benchmark vs flat cash (direction signals) or explicit carry-adjusted benchmark; require PF≥1.5 after costs, n≥100, intrabar-validated.
4. **P3:** Only promote if mutation produces a clean directional filter with WR≥50% and PF≥1.5.

**Success definition:** Forex sleeve passing clean OOS vs flat-cash benchmark with spread-aware costs. Probability: very low. **Do not unblock while drift_alert TRUE.**

---

### 7. MUTUAL FUNDS — zero coverage (infrastructure does not exist)
**Current state:** No MF class; class id −1 (dropped by ML gate); no NAV data source; no scanner/strategy; no dashboard tile. `findmutualfunds2` folder exists but empty of production path.

**Plan:**
1. **P0:** Register `MUTUAL_FUND` class (`ASSET_CLASS_MAP` id 7, `_CAT_MAP`, `_LOWER_TO_UPPER`, `MUTUAL_FUND_SYMBOLS` frozenset: VFIAX, VTSAX, FXAIX, VWINX, VFSTX, PRBLX, PIMIX, VWELX, etc.). Add `is_mutual_fund()` helper. Add dashboard tile (`_PER_ASSET_CLASSES`, `_CANONICAL`).
2. **P1:** Source NAV data (CSV/JSON feed; yfinance fallback). Freshness gate: stale if NAV > 24h (T+1 settlement), NOT crypto <1h bar. PnL on NAV close-to-close; fixed % stop/target in `MF_RISK`, not equity ATR.
3. **P2:** Build `alpha_engine/mutual_fund_scanner.py` + `mutual_fund_strategies.py` stubs (mirror bond structure). Empty signals only — do not surface until forward n≥100 resolved rows.
4. **P3:** Benchmark vs appropriate index (Vanguard/Fidelity index benchmark); require PF>1.5 after costs (expense ratio + load drag), n≥100.

**Success definition:** MF sleeve with clean OOS vs index benchmark. Probability: near 0% until infrastructure exists; low-to-moderate after. **MF is an allocation/cost-discipline play, not an ML prediction edge.**

---

### 8. PENNY / MEMECOIN — weak, blocked
**Current state:** MEMECOIN PF 0.50 over 1,869 trades (class-wide quarantined); PENNY deep-oversold BLOCKED by Gate 0.

**Plan:** Remain blocked. Do not promote. Focus research capital elsewhere.

---

## Cross-cutting "do nots" (carried from veto list)
- No mass DELETE of ghost rows; mark/quarantine instead.
- No fabricated outcomes (UPDATE TIME_EXIT→LOST with pnl_pct=0.0).
- No blind unblock of FUTURES/COMMODITY without real feed.
- No ML confidence inversion without retrain + bundle parity + A/B tests.
- No promoting from `pick_summary_stats_14d` alone, tournament leaderboard WR, or single-snapshot claims.

---
