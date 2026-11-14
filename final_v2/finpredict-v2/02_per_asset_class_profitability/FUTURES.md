**PRIORITY: HIGH** — this class has the deepest documented, most replicated risk premia (time-series momentum and carry) and the most capacity, but it is currently **gate-blocked with no real continuous-contract data**. The academic basis is strongest here; the implementation evidence is the thinnest.

**EXPECTED EDGE: TSMOM + CARRY RISK PREMIA — REAL, MODEST, CROWDED** — time-series momentum and curve carry across financial and commodity futures are genuine, economically motivated premia, but they are low-Sharpe, regime-dependent, and widely harvested. The current 13-trade live sample is noise, and the one "PROVEN" trend claim in the peer record is a benchmark-relative failure. An equity-beating edge is **possible but not established**, and it needs continuous futures, not ETF proxies or a single `ES=F` seed.

# FUTURES — Profitability Playbook

**Clock:** 2026-11-14T21:15Z. **Scope:** planning only; no repo source modified. Every number cites the evidence files in §7; unavailable data is marked `UNVERIFIED`.

**Class boundary.** This file covers **financial futures** (equity index, rates, FX) and diversified multi-asset futures. **Physical commodity futures** are covered in `COMMODITY.md`; do not double-count a commodity TSMOM result in both files.

---

## 1. Current evidence — what was tested, what failed, and why

### 1.1 The live `/audit` futures bucket is a seed, not a strategy

| Surface | Value | Reading |
|---|---|---|
| `picks.active_raw` FUTURES | **13 rows**: **3 OPEN `ES=F`** (same ID emitted 3×, entry **7583.0**, Saturday 13:06Z) + **10 EXPIRED** (YM 6, NG 1, GC 1, CL 1, ZN 1) | One instrument, duplicated, emitted on a Saturday |
| Curated active | **1 row**; **3/3 OPEN frozen (100%)** | No live mark-to-market |
| `picks.recent_closed` FUTURES | **0 rows** | Nothing resolves into the primary feed |
| `pf_registry` policy-clean | n=**13**, WR **23.08%**, PF **0.8567**, z **−1.94** | Below 50%, but n is too small to survive correction |
| Intrabar `at_signal_outcomes` | n=**52**, WR **42.3%**, PF **1.094** | Small positive PF, but a different, stale cohort |
| Peer-reported JSON closed feeds | **234** closed FUTURES rows (`childlike-airport`) | **`UNVERIFIED`** — `data/closed_picks.db` is absent; not independently reproduced |
| `summary_picks` | WR **363.9%** (222 W / 357 L vs 61 resolved) | Arithmetically impossible |
| Timestamps | **9/13** date-only `entry_time`; **6/13** date-only `timestamp`; **10 rows >30 d** stale; median raw age **97.7 d** | The resolver cannot parse date-only seeds |
| Governance | FUTURES ∈ `BLOCKED_ASSET_CLASSES` (`audit_trail/quality_gates.py:1724`) | Administratively frozen; "live" is a display artifact |
| Scheduling | `futures-agent.yml` has `0 14 * * 1-5`, `0 22 * * 1-5`, **and `0 22 * * 0` (Sunday)** | The Sunday run fires **before** the 23:00 UTC reopen |

Sources: `01_audit/MASTER_AUDIT.md` §2, §4, §5; `04_peer_reviews/forex_futures_ci_review.md` §3 (payload recount), §4 C1–C5, §8.

### 1.2 The corrected "0 closed ever" claim

`MASTER_AUDIT.md` §2 says FUTURES has "0 rows in `picks.recent_closed`", which is **true for that feed**. It is **not** true that FUTURES has never closed: the full policy-clean history has **n=13** (`pf_registry`) and intrabar has **n=52** (`forex_futures_ci_review.md` §3). Any statement that the class has no closed sample is a population error. Correct wording: **"0 FUTURES rows in the primary dashboard closed feed; n=13 policy-clean and n=52 intrabar elsewhere, all small and/or stale."**

### 1.3 Research evidence — trend claims are benchmark-relative failures

| Candidate | OOS result | Benchmark | Verdict |
|---|---|---|---|
| H5 ETF dual momentum (SPY/EFA/AGG/BIL, 12m monthly) | Sharpe **0.99**, n=**6** | — | Fails **n≥30**; not a futures test |
| H7 SPY/QQQ RSI(2) | Sharpe **1.50**, CAGR **17.6%** | B&H **18.6%** | Fails absolute return; equity proxy only |
| H10 SPY/QQQ RSI(2)+cash | Sharpe **1.83**, CAGR **22.0%** | 18.6% B&H | **NOT_PROVED**: post-hoc, effective N≈38 DSR **0.9365**, 2-day lag **0.696**, contaminated OOS |
| ITERATION-005 diversified vol-targeted trend (10 assets) | Sharpe **2.13**, CI **[1.25, 3.25]**, t=**5.56**, 10/10 assets | B&H same 10 ≈ **2.2** | **PILOT / alpha unproven**: B&H ≥ strategy; **PF 1.40** is a **bar ratio** and fails its own PF>1.5 gate; 2,490 bars / 7.4 y = 336/yr (8% gap); no DSR at N=683; independent TSMOM365 OOS Sharpe **0.57**, null p=**0.200** |

Sources: `HYPOTHESES.md` H5, H7, H10; `04_peer_reviews/FP5_peer_final_folders.md` §2 C9, §9 finding 3.

**Why it failed, stated plainly:** (a) **no continuous futures data** — the repo has `ES=F`/`YM=F` snapshots, not roll-adjusted series; (b) **single-instrument seeds** with duplicate IDs and weekend emissions; (c) **date-only timestamps** that the resolver rejects, so nothing resolves; (d) **ETF proxies** (SPY/QQQ/EFA) cannot express futures carry or roll; (e) **benchmark-relative failure** — the trend strategy's Sharpe is not above simply holding the assets; (f) **multiple testing** — the "PROVEN" label ignored N=683 and used a bar ratio as PF.

---

## 2. Where an edge could actually exist — mechanism and structural basis

| # | Mechanism | Structural / academic basis | Verdict | Data needed |
|---|---|---|---|---|
| F-M1 | **Time-series momentum** (12-month, vol-targeted) | Documented across a broad cross-section of futures markets (Moskowitz, Ooi & Pedersen, "Time Series Momentum", JFE 2012); one of the most replicated managed-futures premia | **Real but modest, crowded, regime-dependent.** Capacity is deep in financial futures. Not proved here | Continuous, roll-adjusted futures series |
| F-M2 | **Carry / curve slope** (roll yield) | Carry across asset classes (Koijen, Moskowitz, Pedersen & Vrugt, "Carry", JFE 2018); FX forward discount, rates curve slope, commodity roll | **Real.** Strongest in FX and commodity, moderate in rates/equity index. Deep capacity in financial futures | Front/second contract prices, policy rates, FX forwards, CTD data |
| F-M3 | **Cross-sectional momentum** | Futures cross-section (12-1 return) is a documented, lower-turnover cousin of TSMOM | **Real but correlated** with F-M1; capacity high | Continuous series |
| F-M4 | **Treasury basis / CTD implied repo** | Cash-futures basis is a financing/balance-sheet premium; documented in the Treasury basis trade literature. Capacity is bounded by dealer balance sheet | **Real but specialized and crowded.** Requires CTD basket, conversion factors, repo | CTD list, conversion factors, repo rates, deliverable basket |
| F-M5 | **Volatility risk premium via futures options** | Short delta-hedged options earn a premium for bearing crash/gamma risk (equity-index VRP literature) | **Real, tail-heavy, untested here** | Options surfaces, margin, Greeks |
| F-M6 | **Single `=F` quote / ETF proxy** | None — a front-month quote or an ETF share is not a diversified futures program | **Likely absent. Do not test.** | — |

**Real but capacity-limited:** F-M4, F-M5. **Real with deep capacity:** F-M1, F-M2, F-M3. **Likely absent:** F-M6.

---

## 3. Hypotheses ranked by evidence × feasibility

### F-1 — Diversified time-series momentum (rank 1)
- **Signal:** 12-month excess return per contract; long if positive, short if negative; vol-target each leg to **10% annualized**; monthly rebalance.
- **Universe:** **16 financial futures** fixed ex ante — equity index (ES, NQ, YM, RTY), rates (ZN, ZB, ZF, ZT), FX (6E, 6J, 6B, 6A, 6C, 6S, 6M), plus DX.
- **Rebalance:** monthly signal, daily mark; vol target updated monthly.
- **Mechanism:** F-M1.
- **Data required:** back-adjusted continuous contracts with an explicit roll rule (panama/ratio), plus raw contracts to verify; CME settlement files or a licensed continuous feed.
- **Cost / capacity:** **$2.50/side** + **1 tick slippage** + roll cost; **2×** stress. Capacity deep (ES/ZN), thinner in 6S/6M.
- **Failure mode to watch:** back-adjustment look-ahead; roll gaps counted as returns; trend crashes at inflection points; **B&H beta** masquerading as alpha (the ITERATION-005 failure); monthly rebalance count <30.

### F-2 — Carry / curve-slope sleeve (rank 2)
- **Signal:** carry rank = annualized curve slope (front vs second) for commodities, policy-rate differential/forward discount for FX, curve slope for rates; long top tercile, short bottom tercile, dollar-neutral.
- **Universe:** financial futures subset (rates + FX) plus a separate commodity sleeve run under `COMMODITY.md` (do not merge without counting both trials).
- **Rebalance:** monthly.
- **Mechanism:** F-M2.
- **Data required:** front/second settlements, FX forwards and policy rates, CTD/repo for rates.
- **Cost / capacity:** as F-1; FX forwards add financing cost; 2× stress.
- **Failure mode to watch:** carry is short crash risk (commodity/FX); sign conventions; ignoring the forward/roll; crowded positioning.

### F-3 — Cross-sectional momentum (rank 3)
- **Signal:** 12-1 return rank; long top quintile, short bottom quintile, dollar-neutral.
- **Universe:** the 16 financial futures.
- **Rebalance:** monthly.
- **Mechanism:** F-M3.
- **Data required:** continuous series.
- **Cost / capacity:** as F-1; lower turnover than TSMOM.
- **Failure mode to watch:** highly correlated with F-1; report incremental SPA and avoid double-counting the same premia.

### F-4 — Treasury basis / CTD implied repo (rank 4)
- **Signal:** implied repo vs actual repo (or cash-futures basis vs carry) above a threshold; long cash/short future or reverse.
- **Universe:** ZN, ZB, ZF, ZT and their CTD baskets.
- **Rebalance:** event-driven around delivery/roll.
- **Mechanism:** F-M4.
- **Data required:** CTD lists, conversion factors, repo rates, deliverable basket, balance-sheet/financing cost.
- **Cost / capacity:** financing is the dominant cost; capital-intensive; capacity bounded by dealer balance sheet.
- **Failure mode to watch:** ignoring balance-sheet cost; specials; delivery squeeze; crowding (the 2024–26 basis trade is widely followed).

### F-5 — Futures-options variance-risk premium (rank 5, highest ceiling / highest tail risk)
- **Signal:** short delta-hedged ATM straddle / systematic put-writing when implied − realized vol is in the top tercile.
- **Universe:** ES, NQ, ZN options.
- **Rebalance:** weekly entry, daily delta hedge.
- **Mechanism:** F-M5.
- **Data required:** options surfaces, Greeks, margin.
- **Cost / capacity:** fees + spread + hedge slippage; capacity by open interest.
- **Failure mode to watch:** one crash erases years of premium; mark-to-market drawdown and margin calls; VRP overlapping windows.

**Not ranked / prohibited:** `=F` single-contract and ETF-proxy tests (F-M6), and any re-run of the "PROVEN" ITERATION-005 claim without a benchmark-relative gate.

---

## 4. Pre-registered next experiment (one only)

### H-F1 — Diversified futures TSMOM, with a pre-registered carry variant

One experiment, two pre-declared sleeves (TSMOM primary, carry secondary). Both are counted in the trial family and the CSCV matrix; the carry sleeve is **not** a post-hoc rescue.

**Hypothesis.** A vol-targeted 12-month TSMOM portfolio of 16 financial futures earns OOS net Sharpe **≥ 1.0** and **≥ 60/40 benchmark + 0.30** in **2024-01-01 .. 2026-11-13**, after 2× costs, a 1-day execution lag, and PBO ≤ 0.10. The carry sleeve must independently clear the same gates; if it does not, the TSMOM result stands alone.

**Data (exact).**
- Continuous futures: Nasdaq Data Link `CHRIS` (`https://data.nasdaq.com/api/v3/datasets/CHRIS/CME_<code>.json`) for front/back continuous series; CME Group settlement files as the primary source; Refinitiv/Barchart as a licensed fallback. Record the dataset, retrieval time, and roll rule in the manifest.
- Rates/carry: FRED policy rates and Treasury yields (`https://fred.stlouisfed.org/`), CME CTD/conversion-factor files.
- FX carry: policy-rate differentials from central banks/FRED; forward points from the licensed futures source.
- Benchmark: 60/40 (SPY/AGG) and an equal-weight long-only futures basket, both total-return and cost-adjusted.
- Universe fixed ex ante: the 16 contracts in F-1; no additions after seeing results.
- Manifest: symbol, contract month, source, rows, first/last date, SHA-256, roll rule.

**Split.** Train **2000-01-01 .. 2023-12-31**; OOS **2024-01-01 .. 2026-11-13**. Lookback, vol target, and rank thresholds chosen on train only. OOS evaluated once; any revision starts a new OOS (`PROTOCOL.md` §4).

**Execution.**
- Signal at close `t`; trade at `t+1` close (or next open). No same-bar execution.
- Monthly rebalance; roll before first notice day using the declared rule; charge the roll.
- **Intrabar stops:** base TSMOM has **no stop** (trend exits on signal). A pre-registered stop variant applies a **2-ATR daily stop with same-bar stop-first** (worst-case fill) and reports gap-through rate. The stop variant is a separate trial in N.
- 1-day execution-lag stress; 5-day lag as an additional sensitivity.

**Costs.** **$2.50/side** commission + **1 tick slippage** per leg + roll cost. **2× total cost** stress. Report gross and net separately.

**Concurrent capital.** **10% annualized vol target per contract**, gross ≤ **200%**, margin-based; report **return on capital (ROC)** and notional return separately. Cap each position at 10% of 20-day ADV.

**Gates (all must pass; any failure = NOT_PROVED).**
1. **OOS net Sharpe ≥ 1.0** and **≥ 60/40 benchmark + 0.30**; the same for the equal-weight futures benchmark.
2. **True DSR ≥ 0.95** at **N = all trials** (TSMOM + carry + stop variant + the cumulative 23 = **N=26**; also report DSR at N=683), using per-period Sharpe and estimated cross-trial variance `V`.
3. **CSCV PBO ≤ 0.10** on a time-indexed **T×S** matrix (T≥1000, S = all sleeves/variants).
4. **SPA / Reality Check** (stationary bootstrap) p < 0.05 across all sleeves.
5. **n ≥ 30** OOS monthly rebalances (2024-01-01 → 2026-11-13 gives ~35).
6. **2× cost** net Sharpe still ≥ 0.5 and still > benchmark.
7. **1-day execution lag** (and 5-day sensitivity) still positive.
8. **Benchmark relative:** the result must beat B&H of the same 15 assets, not just zero.
9. **Independent replication** on a fresh data pull before "PROVISIONAL".

---

## 5. Kill criteria — abandon futures (as a research class) if any holds

1. **Continuous/roll-adjusted data cannot be licensed/verified** — then there is no testable futures edge in this repo; do not substitute ETFs or `=F`.
2. **H-F1 OOS net Sharpe < 0.5**, or fails **SPA** (p ≥ 0.05), or **PBO > 0.10**.
3. **B&H of the same 15 assets explains the result** — the ITERATION-005 failure (Sharpe 2.13 vs B&H ≈2.2). A trend strategy that only matches beta is not an edge.
4. **2× cost turns the strategy negative** — managed futures is turnover-heavy; if it only works at 1× it is not investable.
5. **n < 30** OOS rebalances.
6. **PF < 1.5 / WR < 50% at n ≥ 100** — the project's own Tier-2 charter.
7. **The only "passing" result needs symbol cherry-picking or a post-hoc regime filter** — that is the mega_mutation/VWAP failure.
8. **The class is "unblocked" without a real futures feed** — that is an explicit audit veto.

If killed: keep FUTURES **blocked**, retain the paper-trading monitor only, and do not display `ES=F` seeds as live picks.

---

## 6. What NOT to do

1. **No single `ES=F` seed as a futures program.** The 3 OPEN rows are one ID emitted 3× on a Saturday; the 10 EXPIRED rows are date-only seeds. This is not a book.
2. **No ETF proxies.** SPY/QQQ/EFA are equity funds; they cannot express futures carry or roll. H5/H7/H10 are not futures evidence.
3. **No "0 closed ever" claim.** FUTURES has **0 rows in `recent_closed`**, not zero closes: n=13 policy-clean and n=52 intrabar exist elsewhere. State the population.
4. **No "PROVEN" trend label.** ITERATION-005 had B&H ≈2.2 vs Sharpe 2.13, a PF 1.40 **bar ratio**, 8% missing bars, no DSR at N=683, and independent TSMOM365 OOS 0.57 (null p=0.200). It is a **pilot**, not a proof.
5. **No annualizing a bar-level PF or per-trade return.** The VWAP and ITERATION-005 failures both came from statistic/definition errors. Use trade-level PF, `sqrt(periods_per_year)` from bar frequency.
6. **No notional Sharpe headline.** Report ROC, gross exposure, and margin.
7. **No parameter sweeps on the same 2024–2026 OOS.** Train ≤2023-12-31; evaluate OOS once.
8. **No post-hoc regime filters or symbol cherry-picking.** Fix the 16-contract universe ex ante.
9. **No ignoring roll.** A back-adjusted series without an explicit roll rule embeds a look-ahead; roll cost is part of the strategy.
10. **No unblocking FUTURES to make the dashboard look complete.** Unblock only after a real continuous feed is wired and the resolver parses timestamps.

---

## 7. Evidence index and `UNVERIFIED` markers

**Primary evidence read for this file**
- `final_v2/finpredict-v2/01_audit/MASTER_AUDIT.md` §2, §3, §4, §5, §10 (FUTURES counts, frozen rows, blocked class, vetoes).
- `final_v2/finpredict-v2/03_research/profitability/HYPOTHESES.md` (H5, H7, H10).
- `final_v2/finpredict-v2/03_research/profitability/runs/v3/VERDICT.md`, `runs/v4/VERDICT.md`.
- `final_v2/finpredict-v2/04_peer_reviews/forex_futures_ci_review.md` §1, §3, §4 C1–C5, §8 (n=13/n=52, 234 closed, date-only, Sunday cron).
- `final_v2/finpredict-v2/04_peer_reviews/FP5_peer_final_folders.md` §2 C9, §9 finding 3 (ITERATION-005 correction).
- `research/profitability/NEXT_DATA_REQUIREMENTS.md` — **path correction:** the brief named `03_research/profitability/NEXT_DATA_REQUIREMENTS.md`, which does not exist; the actual file is at the repo root.

**`UNVERIFIED` (do not treat as fact)**
- The **234 closed FUTURES** rows in JSON closed feeds (`childlike-airport`) — peer-reported; `data/closed_picks.db` is absent, so not independently reproduced.
- The **exact age** of the intrabar n=52 cohort — different populations and staleness not resolved.
- **Continuous futures data availability/licensing** — not present in the repo; `UNVERIFIED` until acquired.
- **Capacity** per contract and **margin** schedules — must be captured at run time.
- The ITERATION-005 **Sharpe 2.13 / CI [1.25, 3.25]** is accepted as reported by the peer folder but was not re-run here; its **"PROVEN"** label is rejected, not the arithmetic.
- Whether the 3 OPEN `ES=F` rows are genuinely a single ID or three rows sharing a key — the review confirms the shared ID string; the panel rendering is not re-checked.
