# Deep-Dive Fleet — Synthesis & Honest Verdict (2026-06-19)
**Author:** claude-opus · **Mode:** Ultracode (adversarial-verify) · **Inputs:** 5 read-only deep-dive subagents (A1–A5) + 1 main-agent pre-registered backtest (H-126) · **Plan:** `reports/DEEP_DIVE_FLEET_PLAN_2026-06-19.md` (peer-reviewed, 3-model :4000)

> **UPDATE (later 2026-06-19):** H-130 + H-131 crypto-funding hypotheses were RUN (real first-touch) and **BOTH REFUTED** — mean-reversion net PF 0.64 / CI-LB 0.40 / WR 28.7%; carry net PF 0.84 / CI-LB 0.62. Data caveat: `crypto_ohlcv` 1h covers only ~181 days (single negative-funding regime) — window-limited verdicts; FDR families closed. Also found+unmasked a **7-week silent `daily_prices` freeze** (404 endpoint behind green CI, commit `9f501250`). Full infra build plan + sequencing: `reports/MONEY_READY_NEXT_STEPS_BUILD_PLAN_2026-06-19.md`.

## TL;DR
The fleet hunted **new-data** edge across all 6 classes + audited the audit surfaces. **Result: still 0/10 promotable** — but with one genuinely new, adversarially-tested candidate and a clear, ranked set of forward-shadow lanes.

- **The headline near-miss (NEW):** EQUITY cross-sectional **short-term reversal** (Lehmann 1990 / Jegadeesh 1990) is a *real, monotone, OOS-robust* effect on existing `daily_prices` — but it **does NOT clear the bar**: net PF 1.61 point-estimate yet **CI-LB 0.99 < 1.15** once correctly **entry-date-clustered** (the naive `ticker|week` clustering falsely cleared it at 1.24 — a textbook over-stated-significance artifact). Also survivorship-biased (32 survivors) + stale data. → forward-shadow lane, **never sized.**
- **The standing lead is unchanged:** `crypto_rsi5070_us` — net@16bp PF 1.36, **CI-LB 0.95**, n=108, forward-gated ~n≥150. The two best candidates in the whole program now both sit at **CI-LB ≈ 0.95–0.99** — good point estimates, lower bounds just short. That is the honest signature of *weak-but-real edges awaiting independent n*, not of nothing and not of a winner.
- **All other new-data avenues are forward-shadow-only** (need data landed or forward accrual): COT positioning, FX time-series-momentum, FX/crypto carry, crypto funding mean-reversion, equity PEAD. No instant winner exists in any class.
- **Three `/audit` cells are still misleading** ("Proven ML" PF 11.34, "Proven Combo" PF 13.21, "R:R Truth" April daily) — daily/snapshot artifacts labeled "Proven," contradicting the honest banner. Trust fix queued.

---

## 1. The adversarially-verified candidate — H-126 EQUITY short-term reversal

**Pre-registration (M-107, stated before the run):** bottom-quintile trailing-5-day-return names outperform over the next 5 trading days (Lehmann 1990 *Fads, Martingales*; Jegadeesh 1990). Long the losers, exit +5d. **Bar:** net PF CI-LB>1.15 @ n_eff≥80, OOS PF≥1.0, reversal monotone across return-quintiles, single-ticker conc<35%. **Falsify** if any fails.

**Data:** `daily_prices` — 32 tickers with ≥400 daily bars, 2024-02 → **2026-04-29 (stale)**; non-overlapping 5-day steps; cross-sectional quintile by trailing-5d return; outcome = 5-day net hold-return (fixed hold → **no TP/SL first-touch mislabel**, so immune to the daily-resolution inflation pattern).

**Result (EQUITY | n=600 events / 100 entry-date clusters | daily 2024-02→2026-04):**

| Cost (RT) | PF point | **CI-LB (date-clustered)** | WR | OOS PF | Verdict |
|---|---|---|---|---|---|
| 4 bp | 1.61 | **0.988** | 56.5% | 1.45 | sub-bar |
| 8 bp | 1.55 | **0.954** | 56.0% | 1.40 | sub-bar |
| 16 bp | 1.46 | 0.894 | 55.2% | 1.32 | sub-bar |
| 25 bp | 1.35 | 0.828 | 54.2% | 1.23 | sub-bar |
| 40 bp | 1.20 | 0.734 | 51.7% | 1.09 | sub-bar |

**Quintile monotonicity (the real-effect evidence):** Q0 losers +0.58% → Q1 +0.43% → Q2/Q3 +0.25/0.28% → Q4 winners +0.22% (mean fwd-5d net @4bp). Reversal gradient is **monotone** — the effect is genuine.

**Adversarial findings (why the naive PASS was wrong):**
1. **Clustering artifact (decisive):** clustering by `ticker|week` gave n_eff=600==sample_size (no clustering bite) and CI-LB 1.236 → a false PASS. The ~6 losers selected on the *same entry date* move together with the market, so the correct cluster is the **entry date** → n_eff drops to **100** and CI-LB falls to **0.988**. This is the clustering analogue of the daily-resolution-inflation trap: an overstated lower bound from treating correlated observations as independent.
2. **Survivorship bias:** only 32 tickers have ≥400 bars (survivors that mechanically mean-revert); delisted losers don't recover → the live point estimate is optimistic.
3. **Stale + replay:** `daily_prices` ends 2026-04-29; and **replay ⇒ candidate-selection only, never sized** (binding rule).

**Status: FORWARD-SHADOW candidate (H-126), never sized.** Real, monotone, OOS-robust, well-diversified (top ticker AMZN 5.5%) — but CI-LB short of the bar and biased. Same shape as the crypto lead.

---

## 2. Per-class candidate registry (new forward-shadow lanes)

All FORWARD-SHADOW, never sized. Promotion ONLY at: net-of-cost PF **CI-LB>1.15 @ n_eff≥80** on the FORWARD window, time-split-robust, conc<35%.

| ID | Class | Hypothesis (citation) | Feasibility / blocker | Honest status |
|---|---|---|---|---|
| **H-126** | EQUITY | Cross-sectional short-term reversal (Lehmann 1990 / Jegadeesh 1990) | Feasible NOW on `daily_prices` | Replay PF 1.61@4bp but **CI-LB 0.99<1.15** (date-clustered) + survivorship + stale → shadow |
| **H-127** | COMMODITY | COT commercial-hedger positioning extreme (Briese; CFTC) | Fetcher exists; **DB-cold** (must land CFTC COT table + schedule) | forward-shadow; untested honest avenue |
| **H-128** | FOREX | Time-series momentum, macro-gated (Moskowitz-Ooi-Pedersen 2012) | Buildable; **net-cost amplitude is the blocker** (FX moves small vs 2-6bp) | forward-shadow |
| **H-129** | FOREX | Carry (Lustig-Verdelhan 2007; Koijen 2018) | Buildable | forward-shadow, lower priority |
| **H-130** | CRYPTO | Funding-rate **mean-reversion** (Alexander-Heck 2022) — *re-scope of existing H-006, run as REAL `crypto_ohlcv` 1h first-touch backtest, not its synthetic plan* | Feasible HIGH (Binance fapi funding history → 2020; 1h bars 2022-09→2026-06) | forward-shadow; **REFUTED 2026-06-19** (real first-touch): mean-rev net PF 0.64/CI-LB 0.40/WR 28.7%; the 32 prior rows were placeholder stamps. 181d single-regime caveat. |
| **H-131** | CRYPTO | Funding **carry** tilt (Koijen 2018) | Feasible HIGH | **REFUTED 2026-06-19**: carry net PF 0.84/CI-LB 0.62; LONG-perp price drift down swamps carry |
| *(resume)* **H-002** | EQUITY | PEAD / SUE drift (Bernard-Thomas 1989) | **NOT feasible as historical backtest** — no stored announce dates (`quarter_end` only); SUE needs ≥4 quarters → only ~52 events, no time-split | **resume existing H-002 shadow + H-20260612 forward-obs**; do NOT open a new ID |

**Crypto on-chain/whale/social: DEAD avenue** — `crypto_whale_movements`/`crypto_whale_wallets`/`social_sentiment` all 0 rows; `crypto_exchange_netflow` 20 rows (4-day Feb snapshot). No on-chain hypothesis is feasible. Funding rate is the *only* viable new crypto source.

---

## 3. Data-readiness map (A5 — what each candidate can build on)

| Source | Table / feed | State | Effort to use |
|---|---|---|---|
| FRED macro | `alpha_macro` | **FRESH** (daily cron) | LOW — query today |
| SEC insider | `gm_sec_insider_trades` (n=917) | **FRESH** | LOW — query today |
| CFTC COT | fetcher exists | **DB-cold** (disk-cache only) | MED — land table + schedule (gates H-127) |
| Crypto funding/basis | Binance fapi + fetcher | **DB-cold** (disk JSONL, 5 syms) | MED — land + schedule (gates H-130/H-131) |
| Equity earnings | `alpha_earnings`/`stock_earnings` | ⚠️ **STALE — frozen 2026-04-27**; no announce date | HIGH — re-trigger writers + backfill announce dates (gates H-002/PEAD) |
| Equity fundamentals | `alpha_fundamentals` (n=2964) | ⚠️ **STALE — frozen 2026-04-27** | MED — re-trigger writer |
| Equity daily prices | `daily_prices` | usable but ends **2026-04-29** | LOW — re-trigger ingest (gates H-126) |

**⚠️ STALE-TABLE TRAP:** `alpha_earnings`, `stock_earnings`, `alpha_fundamentals` (and `daily_prices` lagging) all froze ~2026-04-27 — writers unscheduled. **Re-trigger before any candidate trusts them.** (Distinct from, but rhyming with, the 6-day `at_signal_outcomes` freeze fixed earlier this session.)

---

## 4. Per-class time-to-market table

"Time-to-market" = calendar time until a candidate clears the bar AND its surface is trustworthy.

| Class | Closest candidate | Gap to bar | ETA / dependency | Proactive activity to close it |
|---|---|---|---|---|
| CRYPTO | `crypto_rsi5070_us` n=108 | CI-LB 0.95→1.15; n 108→150 | ~late-Jun (forward accrual) | Maximize scanner emission breadth (don't change the condition); land funding table → open H-130/H-131 parallel lanes |
| EQUITY | **H-126 reversal** (replay) | CI-LB 0.99→1.15 + survivorship + stale | needs fresh, full-universe (non-survivor) daily data + forward window | Re-trigger `daily_prices` ingest; build forward-shadow lane; widen universe beyond 32 survivors |
| COMMODITY | (no honest lead; futures_momentum decayed) | no measurable edge | gated on COT data | Land CFTC COT table (H-127) |
| FOREX | (consensus REFUTED — daily artifact) | amplitude < net cost | structural | TSMOM/carry forward-shadow (H-128/129); maker-cost study; **fix `fx_signals` zero-SL/TP artifact first** |
| ETF/BOND/FUTURES/MEME | n<20 | insufficient data | gated on emission volume | grow honest n |

**Binding constraint (unchanged):** the dominant cost is **calendar time on FORWARD honest-n accrual + measurement uptime + edge scarcity**. Two leads sit at CI-LB ≈ 0.95–0.99; the fastest honest paths are (a) protect/accelerate the accrual clock (freshness guardian already live), (b) lift n_eff via diversification, (c) lower cost basis (maker fills), (d) open parallel new-data lanes. None of this manufactures absent edge.

---

## 5. Audit-surface honesty — 3 still-misleading cells (A5, SQL-verified)

The honest banner says CRYPTO ~33% WR / PF ~0.74; these cells contradict it with no caveat:

| Cell (`/audit` strategy section) | Displayed | Reality | Fix |
|---|---|---|---|
| "Proven ML Strategies" | 79.4% WR, **PF 11.34** (n=199), DYDX/STRK/INJ 95% WR | single-snapshot / fixed-TP artifact; contradicts honest CRYPTO PF 0.74 | demote "Proven" + add "research-only / not intrabar-resolved" caveat (pattern already on adjacent cells) |
| "Proven + High-Confidence Combo" | 71.3% WR, **PF 13.21** (n=94) | same | same |
| "R:R Truth (CRYPTO, 1916 closed)" | PF 1.66–3.06 | April **daily-resolved** cohort, no first-touch note | add daily-resolution caveat |

The fix pattern already exists on the page (adjacent cells are caveated) — these three just need the same treatment. **Trust fix queued (contents-API against main's template.html).**

**Also flagged (A3):** `fx_signals` has **SL/TP all-zero** — any honest first-touch on it is a degenerate artifact (mirrors A1's finding that the 32 crypto funding rows in `at_signal_outcomes` are placeholder stamps). Both are measurement-integrity bugs, not edges.

---

## 6. What changed vs. circling
This was **100% new-data** (per the peer-reviewed plan) with an academic-replication prior filter — it did NOT re-run the exhausted current-signal sweep. Output = exactly what the plan set as success: **1 new adversarially-tested candidate (H-126) + a ranked set of replicated, data-feasible forward-shadow lanes (H-127..H-131) + an honest "still 0 promotable, here's every nearest miss and why."** No promotion, no sizing. The honest answer remains: **no sizeable, trustworthy edge yet — and that verdict protects money.**
