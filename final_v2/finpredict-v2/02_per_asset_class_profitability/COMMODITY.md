**PRIORITY: LOW** — the class is administratively gate-blocked, the current generator sends **crypto proxies** under commodity labels, there is no futures-curve data in the repo, and the only "honest" intrabar sample is a frozen 2026-03 cohort. Priority rises to **MEDIUM only after real curve data is licensed and the proxy rows are purged**.

**EXPECTED EDGE: ROLL YIELD / CURVE CARRY — REAL BUT CAPACITY-LIMITED** — the commodity-futures risk premia (roll yield, TSMOM, hedging pressure) are documented and economically motivated, but they are modest, crowded, and capacity-limited. In the current implementation they are **likely absent**, because the tested rows carry no commodity exposure (RNDR/ARB labelled "silver", XLM/DOT labelled "oil") and ETF/`=F` proxies cannot reproduce a curve.

# COMMODITY — Profitability Playbook

**Clock:** 2026-11-14T21:15Z. **Scope:** planning only; no repo source modified. Every number cites the evidence files in §7; unavailable data is marked `UNVERIFIED`.

---

## 1. Current evidence — what was tested, what failed, and why

### 1.1 The live `/audit` commodity bucket is not a commodity strategy

| Surface | Value | Reading |
|---|---|---|
| `picks.active_raw` COMMODITY | **44 rows**, all `=F`, all `contract_type=commodity_future`; **27 OPEN / 16 EXPIRED** | It is a futures-symbol seed bucket, not a physical-commodity book |
| Curated active | **2 rows**; **18/27 (67%) frozen** at 0% / null; **16 rows >30 d stale** | No mark-to-market |
| `picks.recent_closed` COMMODITY | **7 rows**, WR **42.9%**, sum PnL **−4.2%**, median close age **4.9 d** | Tiny, mixed population |
| `pf_registry` policy-clean | n=**14**, WR **14.29%**, PF **0.1718**, single-source **0.642857** | n is too small to certify anything; WR is far below 50% |
| `summary_picks` | WR **240.2%** (1,447 resolved vs 3,476 W / 3,466 L) | Arithmetically impossible; `sync_summary_picks_json.py:63-65,161` |
| Governance | COMMODITY ∈ `BLOCKED_ASSET_CLASSES = {"FOREX","COMMODITY","FUTURES","BOND"}` (`audit_trail/quality_gates.py:1724`) | The class is **administratively frozen**; a "live" bucket is a display artifact |
| Provenance | `alpha_engine/commodity_signal_generator.py:231-238` maps **RNDR/ARB → "silver"**; `:250` maps **XLM/DOT → "oil"** | Several labelled "COMMODITY" rows carry **no commodity exposure** |

Sources: `01_audit/MASTER_AUDIT.md` §2, §3, §4; `04_peer_reviews/crypto_commodity_review.md` §1, §2 rows 1, 7, 8, 9, 17; `04_peer_reviews/forex_futures_ci_review.md` §3.

### 1.2 The one positive-looking number is stale and cannot be used

| Cohort | n | WR | PF | Status |
|---|---:|---:|---:|---|
| Policy-clean registry | 14 | 14.29% | 0.1718 | Current, but n too small |
| Intrabar `at_signal_outcomes` | **229** | **40.17%** | **1.0256** | **Frozen**: v4 reports last resolved **2026-03-04**; age is reported inconsistently as **80.4 d** vs **254 d**, both `UNVERIFIED` |
| Recent closed feed | 7 | 42.9% | — | Mixed population, sum −4.2% |

The intrabar **n=229 / PF 1.0256** is the number that made the earlier plan call COMMODITY a "WATCH". That is a **frozen historical cohort**, not a live edge: `at_signal_outcomes` has not resolved since 2026-03-04 (`crypto_commodity_review.md` §3 M3/C3, §8). Presenting it as the "honest" current statistic repeats the exact stale-data failure the audit is trying to fix.

### 1.3 What was tested and failed (research program)

The repo's 23-candidate program contains **no dedicated commodity-futures candidate**. Every commodity-adjacent test used ETF or equity proxies, and all failed:

| ID | Proxy test | OOS result | Why it says nothing about commodities |
|---|---|---|---|
| H16 | ETF XS momentum (50 ETFs) | Sharpe **0.98** vs benchmark **1.18**; SPA **0.488** | Broad ETF universe, no curve; underperformed its own benchmark |
| H17 | ETF short-term reversal | Sharpe **0.76** vs **1.18** | Same proxy limitation |
| H18 | ETF TSMOM breadth (20 ETFs) | Sharpe **1.00**, WF **0.37** | No roll yield; ETF contango bleed unmodeled |
| H19 | Country rotation | Sharpe **0.76**, n=22 | Not a commodity test |

Sources: `03_research/profitability/runs/v3/VERDICT.md`; `HYPOTHESES.md` H16–H19.

There is also a **COT over-emission and `CT=F` DSR=1.0 falsification** in the peer record: the commodity series is contaminated by duplicate daily emissions and a degenerate DSR (`crypto_commodity_review.md` §3 M3). Any PF/DSR computed on that series is not evidence.

**Why it failed, stated plainly:** (a) no curve — roll yield is invisible to spot/ETF proxies; (b) label contamination — crypto proxies under commodity names; (c) duplicate emission — COT/`CT=F` rows were over-emitted, so n and DSR are inflated; (d) a frozen intrabar cohort was mistaken for current performance; (e) the class is blocked, so nothing could trade even if the signal were real.

---

## 2. Where an edge could actually exist — mechanism and structural basis

| # | Mechanism | Structural / academic basis | Verdict | Data needed |
|---|---|---|---|---|
| CO-M1 | **Roll yield / curve carry** (long backwardated, short contangoed) | Storage theory and the normal-backwardation/hedging-pressure literature; documented commodity futures risk premium (Gorton & Rouwenhorst, "Facts and Fantasies about Commodity Futures", FAJ 2006; Erb & Harvey, "The Strategic and Tactical Value of Commodity Futures", FAJ 2006; carry across asset classes: Koijen, Moskowitz, Pedersen & Vrugt, JFE 2018) | **Real but capacity-limited.** Strongest documented commodity mechanism. Cannot be tested without front/second contract settlements | Front + second contract settlement prices, roll dates, contract multipliers |
| CO-M2 | **Time-series momentum** (12-month) | Documented cross-asset trend (Moskowitz, Ooi & Pedersen, "Time Series Momentum", JFE 2012); commodity trend is one of the oldest managed-futures premia | **Real but modest and crowded.** Needs continuous, roll-adjusted futures — not ETFs | Continuous back-adjusted contracts; roll methodology |
| CO-M3 | **Cross-sectional carry + momentum** | Commodity cross-section sorts on curve slope and past return; combines CO-M1/CO-M2 | **Real but capacity-limited**, and highly correlated with the two above | Same curve + continuous series |
| CO-M4 | **Hedging pressure / positioning** (COT) | Keynesian normal backwardation; de Roon, Nijman & Veld ("Hedging Pressure Effects in Futures Markets", JF 2000) | **Real but weekly, crowded, and already contaminated here** by over-emission | CFTC COT (weekly), open interest, one row per contract/week |
| CO-M5 | **Seasonality / inventory** (EIA, USDA) | Inventory and storage-cycle seasonality (Working's storage theory); weather/planting cycles in grains | **Likely small and data-mined.** Many calendar cells → high multiple-testing risk | EIA petroleum/gas inventories, USDA WASDE/planting, point-in-time |
| CO-M6 | **ETF/`=F` spot proxies** | None — an ETF is a fund share, not a futures curve | **Likely absent. Do not test.** USO-style products bleed contango; `=F` is a single front-month quote | — |

**Real but capacity-limited:** CO-M1, CO-M2, CO-M3, CO-M4. **Likely absent:** CO-M5 at short horizons, CO-M6 entirely.

**Capacity reality.** Commodity futures capacity is bounded by open interest and by the size of the commodity-index/CTA complex. A strategy that works at $10–50m can fail at $500m; report capacity per contract, not just Sharpe.

---

## 3. Hypotheses ranked by evidence × feasibility

### CO-1 — Roll-yield carry, long backwardation / short contango (rank 1)
- **Signal:** annualized roll yield `y = ln(F_front / F_second) × 12 / months_between_expiries`. Long the top tercile (highest positive roll), short the bottom tercile, dollar-neutral, equal weight.
- **Universe:** 20 liquid commodity futures fixed ex ante (energy: CL, NG, HO, RB; metals: GC, SI, HG, PL; grains/oilseeds: ZC, ZS, ZW, ZM, ZL; softs: KC, SB, CC, CT, LE, HE, OJ).
- **Rebalance:** monthly, on the first business day after the nearby contract's roll window; hold one month.
- **Mechanism:** harvest the curve slope paid to holders of backwardated contracts; CO-M1.
- **Data required:** front and second contract **settlement** prices, expiry/roll calendar, contract multipliers. Sources: CME/ICE settlement files; Nasdaq Data Link `CHRIS/CME_*` continuous contracts (verify front/second mapping); Barchart OnDemand or Refinitiv for a licensed alternative. **No free, verified source is in the repo** → `UNVERIFIED` until licensed.
- **Cost / capacity:** commission **$2.50/side** + **1 tick slippage** + explicit roll cost (two legs per roll). Stress at 2×. Report capacity per contract from open interest; cap 10% of a contract's ADV.
- **Failure mode to watch:** roll-yield sign errors (contango vs backwardation inverted); using adjusted continuous prices that embed the roll (double-counting); liquidity mirage in softs; the strategy is short volatility of the curve — a demand shock inverts it fast.

### CO-2 — TSMOM on continuous commodity futures (rank 2)
- **Signal:** 12-month excess return sign per contract; long if positive, short if negative; vol-target each leg to 10% annualized.
- **Universe:** same 20 contracts.
- **Rebalance:** monthly signal, daily mark.
- **Mechanism:** trend risk premium; CO-M2.
- **Data required:** **back-adjusted continuous** series with an explicit roll rule (panama/ratio), plus the raw contracts to verify. Same licensing gap as CO-1.
- **Cost / capacity:** $2.50/side + 1 tick + roll; 2× stress. Capacity high in energy/metals, low in softs.
- **Failure mode to watch:** back-adjustment look-ahead; roll gaps counted as returns; trend crashes at inflection points; confusing commodity beta with alpha (long-only commodity beta is not TSMOM).

### CO-3 — Cross-sectional carry + momentum composite (rank 3)
- **Signal:** z-score of roll yield + z-score of 12-1 momentum; long top quintile, short bottom quintile.
- **Universe:** 20 contracts.
- **Rebalance:** monthly.
- **Mechanism:** combine CO-M1 and CO-M2; the two are not perfectly correlated.
- **Data required:** as CO-1 + CO-2.
- **Cost / capacity:** as CO-1; higher turnover than either leg, so costs matter more.
- **Failure mode to watch:** the composite is just carry or just momentum with extra parameters; report each leg separately and the incremental SPA p-value.

### CO-4 — Hedging-pressure / COT positioning (rank 4)
- **Signal:** commercial net positioning as a percentile of its 3-year range; long when commercials are net long (hedging pressure), short when net short.
- **Universe:** same 20, but only contracts with clean weekly COT.
- **Rebalance:** weekly, Tuesday COT released Friday → trade the following Monday (3-day lag).
- **Mechanism:** hedgers pay speculators to bear price risk; CO-M4.
- **Data required:** CFTC Commitments of Traders, one row per `(contract, report_date)`; enforce **one pick per `(symbol,strategy,direction)/day`** to stop the over-emission defect (`crypto_commodity_review.md` §3 M3).
- **Cost / capacity:** as CO-1; weekly turnover is high.
- **Failure mode to watch:** COT is stale and widely followed; positioning is endogenous to price; duplicate-emission inflation (the exact defect already found).

### CO-5 — Seasonality / inventory (rank 5, lowest)
- **Signal:** long/short commodity calendar spreads around verified inventory/seasonal windows (e.g. EIA draw season, USDA planting).
- **Universe:** energy and grains only.
- **Rebalance:** event/calendar-driven.
- **Mechanism:** storage-cycle seasonality; CO-M5.
- **Data required:** point-in-time EIA/USDA releases; inventory levels; calendar-spread prices.
- **Cost / capacity:** calendar spreads have tighter liquidity; 2× stress.
- **Failure mode to watch:** data mining across 12 months × 20 commodities; a "seasonal" that is one year's weather; use a pre-registered calendar and a Bonferroni count over every month/contract cell tested.

**Not ranked:** ETF/`=F` proxy strategies (CO-M6). They cannot express the mechanism and are prohibited in §6.

---

## 4. Pre-registered next experiment (one only)

### H-CO1 — Roll-yield carry on real commodity futures curves

Run this **only after** the curve data is licensed and the crypto-proxy/`=F` rows are purged. If the data cannot be licensed, the correct outcome is "not testable" — not a proxy backtest.

**Hypothesis.** A dollar-neutral long-backwardation / short-contango portfolio of 20 commodity futures earns a positive net-of-cost OOS Sharpe and beats a long-only equal-weight commodity benchmark in **2024-01-01 .. 2026-11-13**, after 2× costs, a 1-day execution lag, and PBO ≤ 0.10.

**Data (exact).**
- Front and second contract **settlement** prices and expiry dates: CME Group / ICE settlement files; licensed continuous series from Nasdaq Data Link `CHRIS` (`https://data.nasdaq.com/api/v3/datasets/CHRIS/CME_<code>.json`) or Refinitiv/Barchart as fallback. Record the exact dataset and retrieval time in the manifest.
- COT: CFTC `https://www.cftc.gov/dea/futures/deacmesf.htm` (or the CFTC public API), weekly.
- Cash: 13-week T-bill (Treasury.gov), same series as v4.
- Universe fixed ex ante: the 20 contracts in CO-1; no additions after seeing results.
- Manifest: symbol, contract month, source, rows, first/last date, SHA-256, roll rule.

**Split.** Train **2010-01-01 .. 2023-12-31** (enough full cycles); OOS **2024-01-01 .. 2026-11-13**. Signal parameters (lookback, tercile cut, vol target) chosen on train only. OOS evaluated once; any revision starts a new OOS (`PROTOCOL.md` §4).

**Execution.**
- Signal at settlement `t`; trade at `t+1` settlement (or next open if settlement is unavailable). No same-bar execution.
- Monthly rebalance; roll positions **before** first notice day using the declared roll rule; charge the roll explicitly.
- **Intrabar stops: not used for carry.** Carry is a curve position, not a stop-driven trade. For the CO-2 TSMOM overlay, if a stop is used, apply a 2-ATR daily stop with **same-bar stop-first** (worst-case fill) and report the gap-through rate.
- 1-day execution-lag stress; 5-day lag as an additional sensitivity.

**Costs.** Commission **$2.50/side**, **1 tick slippage** per leg, plus roll cost (2 legs per roll). **2× total cost** stress. Report gross and net separately; never label gross as net.

**Concurrent capital.** 100% gross notional, **10% per commodity**, margin-based; report **return on capital (ROC)** and notional return separately. Cap each position at 10% of the contract's 20-day ADV.

**Gates (all must pass; any failure = NOT_PROVED).**
1. **OOS net Sharpe ≥ 1.0** and **≥ long-only commodity benchmark + 0.30**.
2. **True DSR ≥ 0.95** at **N = all trials** (H-CO1 + the cumulative 23 = **N=24**; also report DSR at N=683 as a sensitivity), using per-period Sharpe and estimated cross-trial variance `V`.
3. **CSCV PBO ≤ 0.10** on a time-indexed **T×S** matrix (T≥1000, S = all candidate weightings).
4. **SPA / Reality Check** (stationary bootstrap) p < 0.05 across all variants.
5. **n ≥ 30** OOS monthly rebalances.
6. **2× cost** net Sharpe still ≥ 0.5 and still > benchmark.
7. **1-day execution lag** (and 5-day sensitivity) still positive.
8. **Capacity sanity:** results hold at 10% ADV per contract.
9. **Independent replication** on a fresh data pull before "PROVISIONAL".

**Explicitly not part of this experiment:** ETF proxies, `=F` quotes, crypto-proxy labels, COT duplicate emissions, seasonality cells. Those are separate hypotheses and separate trial counts.

---

## 5. Kill criteria — abandon commodity (as a research class) if any holds

1. **Curve data cannot be licensed/verified** — then there is no testable commodity edge in this repo, and the class stays blocked. Do not substitute ETFs.
2. **H-CO1 OOS net Sharpe < 0.5**, or fails SPA (p ≥ 0.05), or PBO > 0.10.
3. **Long-only commodity beta explains the result** — i.e. the "alpha" disappears when benchmarked to an equal-weight long-only commodity portfolio.
4. **2× cost turns the strategy negative** — curve carry is turnover-heavy; if it only works at 1× cost it is not investable.
5. **n < 30** OOS rebalances after pooling carry + momentum variants.
6. **The only "passing" result requires seasonality cells or symbol cherry-picking** — that is data mining, not an edge.
7. **The generator still emits crypto proxies** (`RNDR/ARB` as silver, `XLM/DOT` as oil) or `=F` seeds — the class cannot be certified on synthetic exposure.

If killed: keep COMMODITY **blocked and labelled quarantined**; do not unblock it to "make the dashboard look complete" (explicit veto in `MASTER_AUDIT.md` §10).

---

## 6. What NOT to do

1. **No ETF proxies for commodity exposure.** USO/GLD/DBC are fund shares; contango bleed and fees are not a futures curve. The v3 ETF tests (H16–H18) cannot be relabelled as commodity evidence.
2. **No `=F` single-quote seeds.** The 44 raw rows are all `=F`; one front-month quote cannot express roll yield or a curve position.
3. **No crypto proxies under commodity labels.** `commodity_signal_generator.py:231-238,250` maps RNDR/ARB to "silver" and XLM/DOT to "oil". Purge these rows or relabel them CRYPTO; never certify them as COMMODITY.
4. **No COT over-emission.** Enforce one pick per `(symbol,strategy,direction)/day`; the `CT=F` DSR=1.0 artifact came from duplicate daily rows (`crypto_commodity_review.md` §3 M3).
5. **No publishing the frozen intrabar n=229 as current.** Last resolved 2026-03-04; age 80.4 d vs 254 d is `UNVERIFIED`. A frozen cohort is not a live edge.
6. **No parameter sweeps on the same curve window.** Fit on train only; the 2024-01-01+ OOS is evaluated once.
7. **No post-hoc seasonality/regime filters.** Pre-register the calendar and count every month × contract cell in the multiple-testing family.
8. **No symbol cherry-picking.** The 20-contract universe is fixed ex ante; no adding CL or GC after seeing a good run.
9. **No notional Sharpe headline.** Report ROC and capacity; a commodity carry Sharpe on low vol is not comparable to an equity Sharpe.
10. **No unblocking the class to display signals.** COMMODITY is in `BLOCKED_ASSET_CLASSES`; unblocking without a real curve feed is an explicit audit veto.

---

## 7. Evidence index and `UNVERIFIED` markers

**Primary evidence read for this file**
- `final_v2/finpredict-v2/01_audit/MASTER_AUDIT.md` §2, §3, §4, §5, §10 (blocked classes, proxy generator, summary WR, vetoes).
- `final_v2/finpredict-v2/03_research/profitability/HYPOTHESES.md`; `runs/v3/VERDICT.md` (ETF proxy tests H16–H19).
- `final_v2/finpredict-v2/04_peer_reviews/crypto_commodity_review.md` §1, §2 rows 7–9/17, §3 M1–M3, §8.
- `final_v2/finpredict-v2/04_peer_reviews/forex_futures_ci_review.md` §3 (FUTURES/COMMODITY raw-row recount).
- `research/profitability/NEXT_DATA_REQUIREMENTS.md` — **path correction:** the brief named `03_research/profitability/NEXT_DATA_REQUIREMENTS.md`, which does not exist; the actual file is at the repo root.
- Literature named in §2 is cited by author/title/journal; no numeric result from the literature is asserted.

**`UNVERIFIED` (do not treat as fact)**
- The **age** of the intrabar `at_signal_outcomes` cohort: v4 reports 80.4 d (`dashboard_data_report.md:86-89`, 115,782 min) and ~254 d (`INDEX.md:68`, last resolved 2026-03-04); both cannot be right, neither was re-queried.
- The **234 closed FUTURES / commodity population** figures in peer folders — different populations (JSON feeds vs SQLite vs MySQL) and not independently reproduced; `data/closed_picks.db` is absent.
- **Front/second contract mapping** and any continuous-series dataset: not present in the repo; availability and licensing are `UNVERIFIED` until acquired.
- **Capacity** per commodity contract: not computed here; must come from open interest/ADV at run time.
- The **COT/`CT=F` DSR=1.0** falsification is peer-reported (`crypto_commodity_review.md` §3 M3), not re-run in this worktree.
- The claim that "commodity futures are a hedge against inflation" is a macro hypothesis, not tested here; do not use it to justify a signal.
