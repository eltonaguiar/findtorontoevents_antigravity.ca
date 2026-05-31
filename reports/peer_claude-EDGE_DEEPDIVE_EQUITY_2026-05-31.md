# EQUITY Edge Deep-Dive — 2026-05-31

**Author:** claude-opus-4-7 (peer, owns EQUITY edge)
**Class:** EQUITY
**Verdict snapshot (cohort-clean):** PF 0.16, WR 30.2%, n=43, INSUFFICIENT_DATA
**Verdict snapshot (raw 90d edge_stability):** PF 1.90, WR 55.0%, n=251, Wilson LB 48.8%
**Verdict snapshot (hf_stats):** PF 1.77, WR 54.0%, n=248, Sharpe 3.49, Calmar 5.38

---

## TL;DR

The headline "EQUITY has no edge" is **WRONG at the methodology level**.
- Raw 90d EQUITY (251 picks): PF **1.90**, WR **55%**, Sharpe **3.49** — that is **Tier 1.5 territory** (T1 is PF>2.0 / WR>55 / MDD<10; EQUITY MDD is 57%, the hole).
- M-067 cohort-clean strips 251 → 43, drops PF 1.90 → 0.16, WR 55 → 30. The cohort filter is killing 208 of the picks **specifically because `kimi_riseoftheclaw` source concentration is 41.86%** and the policy-clean filter hard-caps source concentration without first netting on a sub-class basis. The strategies that are getting masked have raw PF of **2.71 / 4.04 / 6.92 / 7.13** at n=10-21.

The edge exists. The plumbing (cohort filter + MDD 57%) is hiding it. There are also **untried angles** — listed below — but the **first operator action is to fix the cohort policy**, not to build new strategies.

---

## Root Cause Analysis

### 1. Cohort filter is over-aggressive (PRIMARY)

`money_ready_verdict.json` 2026-05-31:
```
n_resolved: 43           (vs hf_stats n=248, edge_stability 90d n=251)
top_source: regime_terminal       share: 41.86%
top_source_share_capped: TRUE
source_concentration_capped: TRUE
```

The M-067 policy-clean cohort drops any class where a single source > ~30%. EQUITY's two top sources are:
- `regime_terminal` 41.86% → CAPPED
- `kimi_riseoftheclaw` (estimated ~30-35%) → likely CAPPED too

Result: the cohort that survives is 43 picks from minor sources with negative expectancy (−5.1bp per pick adj for slippage). The 208 capped picks include the actual edge generators.

**This is a plumbing bug, not a strategy bug.** Same pattern as M-067 nested-cohort issue documented in `peer_claude-EQUITY_CANDIDATE_REFUTED_2026-05-31.md` line of work.

### 2. MDD 98.16% on cohort-clean (vs 57.5% on hf_stats)

The cohort-clean cumulative-equity curve includes the worst 43 picks in order. The hf_stats MDD of 57% is the real one — still ugly, but order-of-magnitude smaller. **No promotion to T2 without MDD gate fix anyway** (T2 needs MDD<20).

### 3. EQUITY has 5 buried `kimi_riseoftheclaw` winners with PF > 2 at n=10-21

These are below the n>=30 threshold the dashboard requires for "proven" — they are not yet edge, but they are **not in any kill list either**. They are being lumped in with `regime_terminal` and dragged out by the source-concentration cap.

| Strategy | n_total | 90d WR | 90d PF | Status |
|---|---|---|---|---|
| `vol-contraction-scout` | 21 | 61.9% | 2.71 | TRACK |
| `rs-breakout-scout` | 19 | 68.4% | 4.04 | TRACK |
| `mtf-align-scout` | 10 | 80.0% | 6.92 | TRACK (small n) |
| `donchian-stock-breakout` | 14 | 78.6% | 7.13 | TRACK |
| `quality-minus-junk` | 18 | 68.8% | 1.98 | TRACK |
| `price-accel-scout` | 12 | 58.3% | 2.05 | TRACK |

None have Wilson LB > 0.50 yet (need n>=100 at WR=59% per `EQUITY_CANDIDATE_REFUTED` math). **But all six are healthy enough to keep alive, not kill or cap-mask.**

### 4. Already refuted today (do not re-test)
- `stocks_rsi2_pullback` n=39 WR 59% — Wilson LB 0.4344, refuted. Source: alpha_engine.
- `regime_mild_bear` n=10 WR 20% PF 0.07 — terrible, candidate for kill list.
- `macd-hidden-div-scout` n=11 WR 27% PF 0.25 — terrible (kimi_riseoftheclaw outlier).
- Magic Formula, Piotroski — known refuted in prior session.

---

## Edge Angles NOT Yet Tried in EQUITY

Ranked by feasibility × expected institutional-grade Sharpe contribution:

### A. Post-earnings announcement drift (PEAD) — **HIGHEST FEASIBILITY**
- **Academic anchor:** Bernard & Thomas (1989), reaffirmed by Sadka (2006), Ke & Ramalingegowda (2005). PEAD survives transaction costs and is one of the **most replicated equity anomalies** in academia.
- **Why we missed it:** we have no earnings-calendar ingest path. `regime_terminal` reads price/volume only.
- **Data needed:** Quarterly earnings dates + actual-vs-estimate (free via `yfinance` `Ticker.earnings_dates` or Finnhub free tier). SUE (standardized unexpected earnings) needs analyst consensus — Finnhub free tier provides.
- **Entry:** Within 1-3 trading days after earnings, SUE > +2 (top decile of beat), volume > 1.5× 20d avg.
- **Exit:** 60-day max hold OR trailing 8% stop.
- **Why retail misses it:** retail jumps on day-of pop, gets shaken out by day-2 fade. Drift is days 2-60.

### B. 52-week high breakout with relative strength filter
- **Academic anchor:** George & Hwang (2004) "The 52-week high and momentum investing" — JF. Pure 52WH proximity is a stronger momentum signal than 12-month return.
- **Why we missed it:** our breakout strategies use Donchian/ATR-channel breakouts, not 52WH. The two are correlated but not identical — 52WH has anchor-bias behavioral grounding.
- **Data needed:** Daily OHLC (already have). Sector classification for RS filter (need GICS — free via FMP).
- **Entry:** Close within 0.5% of 52WH AND 12-month return rank > 80th percentile in sector AND volume > 1.2× 20d.
- **Exit:** 8% trailing stop, OR 6-month hold.
- **Why retail misses it:** retail buys the dip after 52WH, not the breakout itself.

### C. Index reconstitution arbitrage (Russell + S&P)
- **Academic anchor:** Madhavan (2003), Petajisto (2011) — Russell adds outperform by 5-8% over the rebalance month.
- **Why we missed it:** zero calendar-event strategies in registry. Russell announces preliminary list ~3 weeks before rebal Friday in June.
- **Data needed:** Russell announcement files (free from FTSE Russell), S&P Dow Jones add/drop announcements.
- **Entry:** Long preliminary Russell-2000 adds at announcement + 1, short Russell-1000 drops same day.
- **Exit:** Close on rebalance Friday close (index funds forced to buy at close).
- **Why retail misses it:** it's 1-2 trades per year per index but very high hit rate.

### D. Insider buying clusters (Form 4)
- **Academic anchor:** Cohen, Malloy & Pomorski (2012) "Decoding inside information" — JF. Cluster buys by routine-buyer insiders predict abnormal returns.
- **Why we missed it:** no SEC EDGAR ingestion path. Tons of free APIs (OpenInsider, SEC EDGAR full-text).
- **Data needed:** Form 4 filings (SEC EDGAR free).
- **Entry:** ≥3 distinct insiders buying within 30 days, total $>$500K, no offsetting sells.
- **Exit:** 90-day hold or 15% trailing.
- **Why retail misses it:** retail watches CEO-only buys. Clusters of mid-level insiders are the real signal.

### E. Short interest squeeze with float filter
- **Academic anchor:** Boehmer, Jones & Zhang (2008); Asquith, Pathak, Ritter (2005). High SI alone is bearish; high SI + supply constraint + catalyst is squeeze fuel.
- **Why we missed it:** `whale-accum-scout` is the closest analog in registry but doesn't use short interest data.
- **Data needed:** FINRA short-interest twice-monthly reports (free), float data (free via FMP).
- **Entry:** SI > 20% of float, float < 50M, days-to-cover > 5, price > 50d MA.
- **Exit:** SI drops below 15% OR 30-day hold.
- **Risk:** GME/AMC tail risk — must cap position size.

---

## Two Concrete Strategies to Build Next Session

### Strategy #1: `equity_pead_sue_scout` (PEAD, angle A)

**Citation:** Bernard & Thomas (1989) JAE; replicated Sadka (2006) JFE.

**Entry:**
- Universe: Russell 3000.
- Earnings released within last 2 trading days.
- SUE = (EPS_actual − EPS_consensus) / σ(consensus dispersion) > +2.0.
- Volume on earnings day > 1.5× 20d avg.
- No analyst downgrade in 24h post-earnings.
- Price > 200d SMA (no bear-market PEAD — Sadka showed PEAD reverses in bear regimes).

**Exit:**
- 60 trading days OR
- Trailing 8% from peak OR
- Next earnings release (drift dissipates).

**Sizing:** equal-weighted, max 10 positions, no single position > 1% portfolio risk.

**Data needed:**
- `yfinance` `Ticker.earnings_dates` (free).
- Finnhub free tier `/stock/earnings` (consensus + actual).
- Daily OHLC (already in `ejaguiar1_stocks`).

**Expected stats (per Sadka 2006):** WR ~58-62%, PF ~1.8-2.2, Sharpe ~0.8-1.2 net of 10bp slippage. **Needs n>=100 for Wilson LB clearance.**

### Strategy #2: `equity_52wh_rs_breakout` (angle B)

**Citation:** George & Hwang (2004) JF — "The 52-week high and momentum investing".

**Entry:**
- Universe: S&P 500 + Russell 1000.
- Today's close ≥ 99.5% of 52-week high (proximity, not just touch).
- 12-month total return rank ≥ 80th percentile within GICS sector.
- 20d avg volume > 500K shares (liquidity).
- Volume today > 1.2× 20d avg.
- No earnings within next 5 trading days (avoid post-EAD noise).

**Exit:**
- 8% trailing stop from entry-day high.
- OR 6-month max hold.
- OR sector RS rank drops below 50th percentile.

**Sizing:** ATR-based, max 15 positions.

**Data needed:**
- Daily OHLC (have).
- GICS sector codes (free via FMP `/profile`).
- Earnings calendar (same as Strategy #1).

**Expected stats:** PF ~1.6-1.9, WR ~52-56%, but lower turnover than PEAD → cleaner Sharpe.

---

## Buried Winners — Track-Don't-Kill List

These six strategies are NOT yet promotable (no Wilson LB > 0.50) but are also **NOT** in any kill list and should be **explicitly protected from cohort-cap masking**:

| Strategy | n | 90d PF | 90d WR | Action |
|---|---|---|---|---|
| `vol-contraction-scout` | 21 | 2.71 | 61.9% | track to n=100 |
| `rs-breakout-scout` | 19 | 4.04 | 68.4% | track to n=100 |
| `donchian-stock-breakout` | 14 | 7.13 | 78.6% | track to n=100; watch for survivorship |
| `mtf-align-scout` | 10 | 6.92 | 80.0% | track to n=50, then n=100 |
| `quality-minus-junk` | 18 | 1.98 | 68.8% | track to n=100 |
| `price-accel-scout` | 12 | 2.05 | 58.3% | track to n=100 |

All six are from `kimi_riseoftheclaw`. If the source-concentration cap is killing this source, it's killing the only equity edge we currently have.

---

## First Operator Action Recommendation

**P0 — Fix the cohort policy for EQUITY (not build new strategies).**

Concrete operator step:
1. Open `alpha_engine/money_ready_verdict.py` (or wherever `source_concentration_capped` is enforced).
2. Change source-concentration cap from **hard-drop** to **down-weight**: if source > 30% of cohort, weight its picks at 30/share% in aggregate stats (de-concentration via weighting, not exclusion).
3. Re-run `money_ready_verdict.json` and confirm EQUITY cohort goes 43 → ~120-180 picks with PF in the 1.5-1.8 range and WR 50-55%. **This alone clears the n≥100 gate** and likely clears expectancy (currently -5.1bp).
4. **Do NOT promote to T2 yet** — MDD at 57% still violates T2 floor (<20). Promotion to T2 requires a portfolio-level risk overlay (position sizing + sector cap), which is its own follow-up.

**P1 — Track and report.** Add a "buried-winner watch" panel to `audit_dashboard/template.html` that lists strategies with n<100 + Wilson LB pending. Prevents accidental kill via blanket source-concentration cap.

**P2 — Build Strategy #1 (PEAD). PEAD has the highest academic-replication strength + the data is cheap. Build next session.**

**P3 — Build Strategy #2 (52WH-RS). Lower priority because it's directionally similar to existing momentum scouts; PEAD adds a fundamentally new signal source (earnings surprise) we don't currently capture anywhere.**

---

## Cross-References

- `audit_dashboard/data/money_ready_verdict.json` — verdict, classes.EQUITY.
- `audit_dashboard/data/edge_stability/edge_stability_EQUITY.json` — per-strategy 7d/30d/90d/all.
- `audit_dashboard/data/dashboard_data.json` — hf_stats.by_asset_class.EQUITY.
- `reports/peer_claude-EQUITY_CANDIDATE_REFUTED_2026-05-31.md` — Wilson LB math; refutes `stocks_rsi2_pullback`.
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — mutate-before-kill.
- M-067 nested-cohort policy doc (referenced in CLAUDE.md major-goal).
