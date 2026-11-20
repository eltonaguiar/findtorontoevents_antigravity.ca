# Full review — findtorontoevents.ca/audit, /audit2, /audit3, and the asset-class methodologies

**Date:** 2026-11-19
**Live data:** `/audit3/audit3_ledger.json` generated `2026-11-19T18:32:40Z`; `/audit2/audit2_forward.json`
`2026-11-19T18:32:39Z`; pages fetched 18:40–18:52Z.
**Code base:** `eltonaguiar/findtorontoevents_antigravity.ca`, `main` at the time of writing
(`6abfa22364e` + `77718be66922` + `c4ec1ecb6b7` + `aa59b42a56a` are mine and landed).
**Provenance labels used below:** `[V]` = I printed the value from the file/page myself this
session; `[I]` = section inventory with a file:line reference from a parallel read-only
inventory, not independently re-derived line by line.

---

## 0. Method (the part other agents should critique)

The review is a fixed five-step protocol applied to every section and every metric:

1. **Live probe.** Does the URL return 200, what is the byte size, what does the page say it
   is, and what does it `fetch()`? A page's own `<title>` and data-source list is the first
   honesty test. (Result: `/audit2` is live again — it was 404 in earlier sessions; `/audit3`
   is the tribunal.)
2. **Data provenance.** For each number: which file/endpoint produces it, is that artifact
   committed or generated, what is its `generated_at`, and does the producer actually exist?
   A number whose producer is absent is a claim, not a measurement.
3. **Metric audit.** For every metric: definition, denominator, sample size, whether a
   confidence interval exists, and whether it can distinguish skill from beta.
4. **Multiplicity audit.** How many hypotheses were searched before this cell was displayed?
   If the page shows 359 cells and the corpus is 8,613 rows, the reader is looking at the
   maximum of 359 draws; a PF is meaningless without the correction.
5. **Falsification test.** State what observation would prove the claim wrong, and whether
   the harness can produce it. If not, the claim is unfalsifiable and must not be labelled
   "proven".

Every finding below is either a **defect** (contradicts its own data), a **gap** (metric or
harness absent), or a **policy question** (a judgement call the owner must make).

---

## 1. `/audit` — every section, and what is wrong with it

31 user-visible sections in document order `[I]`, grouped by provenance:

### 1.1 Hardcoded literals (no producer, no timestamp)

| Section | Hardcoded content | Problem |
|---|---|---|
| `#truth-layer-reality-banner` | "11.13% WR / PF 0.46; 2026-05-29 n=73,817" | Six months stale, no `generated_at`, no link to the current ledger |
| `#ml-calibration-inversion-banner` | 14.4% / 60.3% WR, dated 2026-05-15 | Stale; cannot be re-derived |
| `#crypto-disputed-banner` | PF 9–18, n=229 / 31.3% | Stale; conflicts with audit3's CRYPTO KILL |
| `#tab-ueps` | "0.0%", PASS rows with Current `-` | Hardcoded PASS at zero observations |
| `#tab-dashboards`, `#tab-links`, `#tier-trust-legend` | static lists | No n, no timestamp |
| `#asset-class-quality-strip` | BOND green `thresholdPass:true` at 0 active | Green at zero — the exact failure the audit exists to catch |

### 1.2 Sections that read a file with no producer

| Fetch target | Status |
|---|---|
| `data/strategy_tribunal_latest.json` | **absent from `main`** (verified: 0 paths in `git ls-tree`) and not produced by `audit-dashboard.yml` → the Strategy Kill Tribunal panel renders from nothing |
| `data/stock_forex_prices.json` | no producer/deploy found |
| `data/strong_signals.json` | absent at all three fetch paths |
| `data/dashboard_data.json` | untracked, workflow-generated; the repo cannot reproduce the headline cards |
| `data/stock_prices.json` | untracked, FTP-only |

### 1.3 Sections with real data but no sample size or no benchmark

`#walkforward-by-class-card` (folds only, no n), `#summary-cards` (partial n),
`#asset-class-quality-strip` (no trade n), `#tab-mlhealth` (AUC/staleness only),
`#agreement-matrix` (no n), `#tab-verifiedalpha` (partial).

### 1.4 Redundant with `/audit3` (and sometimes contradictory)

`#strategy-tribunal-panel` vs audit3 Kill list · `#major-goal-banner` (0/10) vs audit3
Asset classes · `#theory-tracker-panel` vs audit3 Hypothesis status ·
`#tab-permutations` vs audit3cells · `#agreement-matrix` vs audit3 Source families ·
`#forward-clock` duplicates audit2's Forward evidence clock.

The banner says "0/10 money-ready — COMMODITY is the only WATCH" while a static span says
"COMMODITY — FAIL+INSUFF-N". Both cannot be the current truth.

**Verdict for `/audit`:** it is a *marketing dashboard* wrapped around a measurement engine.
Its live tiles are useful; its banners are stale assertions and several tiles render green at
zero. Nothing on it should be used to size a position. The only trustworthy blocks are those
labelled with n and a timestamp, and even those are not multiplicity-corrected.

---

## 2. `/audit2` — every section, and why it matters

Live: 200, 6,916 B, `<title>audit2 — candidate & methodology library</title>`. Sections `[V]`:

| # | Section | What it is | Gap |
|---|---|---|---|
| 1 | **Doctrine** | four claims: public OHLCV is arbitraged; vol scaling is free alpha; expression > signal; trial budget binds | Assertions, no citation and no test in-repo. "Vol scaling adds Sharpe 0.3+" is a testable claim the repo never tests |
| 2 | **`#coverage`** — Verdicts (from audit3_ledger.json) | per-class verdict, n, net expectancy, 95% CI, 2× cost OK, DSR, `required_n` | Renders correctly; all classes WEAK/KILL, CIs include zero |
| 3 | **`#pods`** — Candidate & observe pods | 9 registered pods; `pre_registered` may confer confirmatory, `observe` cannot | Registry is a **static snapshot** because `reports/` is not web-served — the page cannot show live pod status |
| 4 | **Forward evidence clock** | forward rows after registration, from `audit2_forward.json` | **Only 430 rows, all `H-119`; `by_hypothesis["H-119"].pods = []`** `[V]`. The clock has never ticked for any pod |
| 5 | **Trial budget & benchmarks** | class benchmark leg, gate, cost gate | No numeric trial budget displayed per class |
| 6 | **`#measures`** — Measures library | measurement kit (walk-forward, DSR, cost) | Lists methods; does not show whether each ran |
| 7 | **`#traps` / `#retired`** | graveyard with reasons | Good practice; not machine-checked |
| 8 | **`#provenance`** | freshness + sources | Honest disclaimer, but the static-registry caveat undercuts "freshness" |

**Verdict for `/audit2`:** the correct *shape* — it is the only surface wired to promotion —
but its forward clock is empty, so every pod sits at the start line. It also publishes a
doctrine (vol scaling) it never tests, which is the same sin as `/audit`'s banners in a
more sophisticated wrapper.

---

## 3. `/audit3` — sections and the full metric glossary

Sections `[V]`: KPI row → Asset classes → Gates → Kill list → Strategy×direction cells →
Symbol×direction cells → Section×asset class → Source families → Evidence registry →
Sources/records → Asset-class truth vs stored column → Hypothesis status → Known gaps.

### 3.1 Ledger metrics, defined and judged

| Metric | Definition | What it proves | What it cannot prove | Current `[V]` |
|---|---|---|---|---|
| `n` | resolved rows in the cell | sample size | that rows were independent | 359 cells; 292 have n<20 |
| `wr` / `wr_ci` | win rate, Wilson CI | directional frequency | profitability (no payoff) | CRYPTO 40.4% |
| `pf` | gross profit / gross loss | payoff asymmetry | significance | CRYPTO 0.838, EQUITY 1.089 |
| `p_value` / `p_wr` | binomial vs 50% | whether WR differs from coin flip | edge after costs | many cells |
| `q_value` | BH FDR within namespace | multiplicity-corrected significance | out-of-sample persistence | **all classes q=1.0** |
| `p_harm` / `harm_q` | one-sided harm test | evidence of negative edge | – | used for KILL |
| `net_expectancy_pct` | mean net PnL after class slippage | the only profitability number that matters | that it generalises | CRYPTO −0.309% |
| `net_ci_pct` | bootstrap (circular block) CI | precision of net | – | every class includes 0 |
| `net_ci_pct_2x` / `stress_2x_ok` | same at 2× slippage | cost sensitivity | – | **all 8 confirmatory cells fail** |
| `dsr` / `sr0` / `sharpe` | deflated Sharpe vs 658-trial null | overfit-adjusted skill | forward validity | max 0.103 in pod cells |
| `dsr_local` | DSR vs bucket width | CANDIDATE-tier breadth | promotion | 66 cells scored |
| `split_half` | both halves mean>0 | stability | – | 41 unstable |
| `recency` / `recent_ok` | recent-window performance | decay | – | shown per cell |
| `required_n` / `mde_pct` | rows to confirm at 80% power | the path to proof | that the effect is real | EQUITY class 7,389 |
| `top_symbol_share` / `top_source_share` | concentration | fragility | – | single-source flags |
| `alpha_gate` | selection alpha at scope | beta-vs-skill | – | 37 strategy / 390 proxy / 7 class |
| `bh_family_n` | BH family size | multiplicity context | – | per namespace |
| `raw_verdict` vs `verdict` | pre/post persistence | churn | – | persistence gate |

### 3.2 Live integrity findings (19:05Z, after peer cross-check)

Five facts a peer (buffy/review-main) raised, each re-derived from the 18:32:40Z ledger:

1. **`raw_verdict == verdict` for 359/359 cells.** The persistence gate is a no-op on this
   run — the page's "repeated looks" protection has nothing to compare against.
2. **Only 3 of 67 cells with n≥20 have net-CI lower bound > 0**: `macd_rsi_m048` SHORT
   (n=24, +3.03%/trade), `strong consensus` SHORT (n=24, PF 1,098 — an artifact), and
   `forex_rsi2_mean_reversion` LONG (n=24, +0.895%). All three are WEAK at the n≥30 floor.
3. **11 WEAK cells carried `reasons == []`** — including the best-looking cells (ETF
   `rs-breakout-scout`, EQUITY `donchian-stock-breakout`). Their actual blocker is the CI
   straddling zero, which the verdict logic never stated. Fixed: every WEAK now names the
   blocking condition.
4. **"0 CANDIDATE" is cell-scoped.** The symbol bucket holds **FOREX / AUDJPY / LONG,
   n=33, net CI [0.242, 0.942]** — a CANDIDATE the KPI row does not count. The summary now
   publishes `n_candidate_symbols` and a `summary_scope` note.
5. **`selection_alpha.gate` does carry `applied/tested/demoted/scopes`**; it is nested under
   `gate`, not top-level, which is why a reader scanning the block's keys misses it.

### 3.3 Section-level defects

- **`required_n` is published but never acted on.** A reader sees "EQUITY needs 7,389 rows
  (has 939)" and the page still presents EQUITY as the best class. That is fine as a ranking
  but must be stated as "closest", not "good".
- **Class-level `required_n` is unreachable** for ETF (1,745,345) and FOREX (8,734). Any
  class-level "money-ready" goal is therefore a category error; only per-cell/pod promotion
  is feasible.
- **The evidence registry** lists backtests already in the repo — but several of those
  backtests are the unwired ones in §5, so "evidence" includes code that no gate consumes.

---

### 3.4 Denominator and coverage — the number changed between runs

> **RESOLVED 2026-11-20.** PR #984 reconciled the denominator: the live ledger now reports
> `scored_rows` 8,769 = `valid_closed_picks` 8,769, `scored_share_of_valid_pct` **100.0** with
> status **ok** (it was `null`/`not_comparable`), and `scored_share_of_total_pct` 53.56 % of 16,372
> closed rows. The finding below is kept as the record of why the reconciliation was needed.


The live 18:32:40Z ledger reports `coverage.denominator.mode="canonical"`,
`loaded_from_sidecar=true`, **8,613 of 14,637 closed rows (58.84%)** with the note
"scores the published canonical view; /audit counts the same rows". The repo's committed
copy from 04:04Z reports `mode="payload_slice"`, `loaded_from_sidecar=false`,
`fallback_reason="no_canonical_block"`, **3,500 of 16,330 (21.43%)** and explicitly says
"NOT the same denominator as /audit".

Both are "the audit3 ledger", and they disagree by 5,113 scored rows and 1,693 total rows.
Even in canonical mode `scored_share_of_valid_pct` is `null` because the ratio would exceed
100% — canonical rows and the payload summary are still different sources. Until one
denominator is pinned and published with the ledger, no cross-surface tile comparison is
auditable. This supersedes my earlier payload-slice claim: the live ledger has moved to
canonical, and the movement itself is the finding.

## 4. Cross-surface contradictions (fix before adding features)

| Claim | Where | Contradiction |
|---|---|---|
| Money-ready count | `/audit` banner 0/10, `/audit3` headline 0/9, audit2 echoes ledger | three denominators in one product |
| COMMODITY | `/audit` "only WATCH" vs static "FAIL+INSUFF-N" vs audit3 KILL (n=51, PF 0.096) | KILL is the correct one |
| ETF WR | `/audit` policy-clean 1.9% (n=52) vs `/audit3` 43.2% (n=586) | different populations, never reconciled on the page |
| Kill counts | `/audit` "42 kills" vs audit3 8 KILL cells / 10 kill symbols | different objects, same word |
| Forward clock | `/audit` `forward_clock.js` vs `/audit2` clock | two renderers, one data source, no shared denominator |

---

## 5. Backtesting methodologies in the repo — what exists, what is actually wired `[I]`

**Wired (a workflow or gate calls them):**
`alpha_engine/walk_forward_backtester.py:561` (rolling IS/OOS + 10 anti-overfit checks) ·
`alpha_engine/walkforward_validator.py:81` (per-strategy rolling) ·
`alpha_engine/eagle_gates.py:344` (WFE ≥0.85×IS, survival ≥60%) ·
`alpha_engine/anti_overfit_validator.py:56` (CPCV PBO) and `:227` (DSR) ·
`tools/pbo_cscv.py:42` · `tools/whites_reality_check.py:150` (SPA) ·
`alpha_engine/money_ready_verdict.py:1096` (BH/Bonferroni) ·
`alpha_engine/execution_cost.py:38` · `tools/per_class_cost_gate.py:207` (3× cost) ·
`tools/triple_barrier_labeler.py:63` · `alpha_engine/meta_labeler.py:343` ·
`tools/ma_strategy_forward_tracker.py:286` (5% synthetic total-loss survivorship).

**Exists but unwired (no non-test caller):** `monte_carlo_validator.py` (permutation MC),
`alpha_engine/rigorous_backtest_harness.py` (block bootstrap / PBO / purged WF),
`alpha_engine/statistical_rigor.py`, `verified_strategies/pipeline/*` (promotion path),
`crypto_ml_edge/validation.py`, `benchmark_closed_ledger.py` (random-entry MC + paired
bootstrap — manual only), `compute_backtest_forward_correlation.py`,
`tools/verify_realized_30d.py`, `tools/build_cpcv_pbo_results.py` /
`build_walkforward_oos_results.py` / `build_bootstrap_ci_results.py`.

**Assessment.** The statistical machinery is better than the product suggests. The failure is
*plumbing*: the strongest tests (random-entry null, paired benchmark bootstrap, CPCV builders)
are manual, and the pages read the weaker per-run gates. **Recommendation: wire
`benchmark_closed_ledger` and `verify_realized_30d` into the weekly workflow and surface
their output on `/audit2`, because a random-entry null is the single most persuasive "is this
skill?" test and it already exists.**

---

## 6. Asset classes — deep dive and what "proper" looks like

### 6.1 Mutual funds — the honest answer to "a random fund probably breaks even"

That intuition is **half right and half expensive**. A fund's return is
`market beta − fees ± manager alpha`; the median active manager's alpha is negative after
fees (SPIVA-style persistence), so "break-even" is true only *before* costs, and the
expected outcome of a random active fund is to underperform its benchmark by roughly its
expense ratio plus trading costs. The repo already encodes the correct screen in
`alpha_engine/data/mutual_fund_metadata_sample.json` `[V]`:

| Fund | Type | Expense ratio | Load / 12b-1 | AUM |
|---|---|---:|---|---:|
| FXAIX | S&P 500 index | **0.015%** | 0 / 0 | $400B |
| VTSAX | Total US market index | 0.04% | 0 / 0 | $1.4T |
| SWTSX | Total US market index | 0.03% | 0 / 0 | $180B |
| VFIAX | S&P 500 index | 0.05% | 0 / 0 | $500B |
| VBTLX | US bond market index | 0.05% | 0 / 0 | $300B |
| VTIAX | International stock index | 0.11% | 0 / 0 | $400B |
| VGSLX | REIT index | 0.12% | 0 / 0 | $50B |
| VWELX | Wellington (active, balanced) | 0.25% | 0 / 0 | $100B |

**Best "if I had to pick" set:** the low-cost index rows — FXAIX/VTSAX/SWTSX for US equity,
VTIAX for international, VBTLX for bonds, VGSLX for REITs. VWELX is the only active fund in
the sample and is cheap for active (0.25%) but carries manager risk. `[V]` for the data;
fund selection is not personalised advice.

**Proper method to prove it:** compare each fund to its benchmark over ≥10 years on *net*
returns, with the benchmark's own expense ratio subtracted, and check survivorship (the repo's
sample is 8 survivors — a survivorship-biased universe by construction). The repo only has
NAV plumbing (`mutual_fund_nav.py:191`, "No picks are emitted here" `[V]`) and no fund-vs-index
study. **Gap: no mutual-fund backtest exists at all; the metadata file is a screen, not
evidence.**

### 6.2 ETFs — the low-hanging fruit, and whether it can be proven

This is the strongest evidence in the repo:

- `reports/etf_abc_backtest_20260513.md` `[V]`: naive **top-3 long-only** rotation across 11
  SPDR sectors, 2015–2026, **PF 2.05, Sharpe 0.97, total +283.7%, MDD 16.1%**; survives five
  friction scenarios; long-short (PF 0.937) and Black-Litterman do **not** improve it.
  Conclusion in that report: "Ship the naive top-3 long-only ETF rotation."
- `reports/edge_hunt_ETF_2026-06-05.md` `[V]`: the **live** ETF class was PF 0.80 with
  `cta_golden_cross` as a single-source artifact; dual-momentum walk-forward OOS PF 2.746 on
  **n=11**; forward pilot **n=0**, `recommend_scanner_enable: false`.

**So: yes, a historical edge can be backtested and replicated; no, it is not proven forward.**
The backtest is monthly-rebalanced (low turnover), which is why friction does not kill it —
that is a genuinely favourable property. The proof gap is the forward clock, not the method.

**Pre-registerable next test:** top-5 long-only asset-class ETF rotation (14-ETF universe, 9-month momentum), monthly, absolute filter,
with a same-window SPY buy-and-hold benchmark leg and a random-entry null. `required_n` for
the current ETF pod cell (rs-breakout, n=80) is ~201, so a 12-month forward run at monthly
cadence cannot reach it; a weekly-cadence variant is needed to accumulate rows.

### 6.3 Value stocks — genuine fundamentals, opt-in only

`alpha_engine/value_screener.py` (789 lines) `[V]` is real: it scores
Magic Formula × Acquirer's Multiple × FCF yield, a Piotroski quality composite, and an
Altman Z''/Beneish safety gate, fed by SEC EDGAR XBRL via `fundamentals_fetcher.py` (522 lines,
P/E, P/B, EV/EBITDA, FCF yield, ROIC, D/E). **This is not a price proxy.**

**The gap is wiring:** it is an opt-in weekly sidecar, and the always-on equity "value"
strategy (`equity_strategies.py::quality_value_composite`) is price/technical only (52-week
range, vol, trend R²). So "value" in the live equity feed is not value. There is **no DCF and
no Graham net-net/NCAV** implementation (those exist only as AI-persona prose).

**Proper method:** value needs long horizons (3–5y) and survivorship-free fundamentals; the
repo's `required_n` machinery is built for short-horizon trades and will call every value
signal INSUFFICIENT_N. Evaluate value in its own framework (annual rebalance, benchmark =
Russell 1000 Value / S&P 500), not in the trade-level tribunal.

### 6.4 Bonds, futures, commodities, forex

All four have live emitters `[I]`: `bond_strategies.py` (curve slope, TSMOM, credit-spread MR,
duration rotation), `futures_strategies.py` (TSMOM, RSI2, vol-regime breakout),
`commodities_strategies.py` (seasonal, basis/carry proxy, COT contrarian),
`forex_strategies.py` (carry, cross-sectional momentum, 200d MR). Dead modules exist
(`unique_term_structure_roll_yield.py`, `forex_carry_ppp.py` — no caller).

But the **audit verdicts are brutal**: BOND −0.184% net (n=35), FUTURES n=4,
COMMODITY KILL −3.507% (n=51), FOREX −0.024% (n=258). The modules exist; the edges do not
survive costs and multiplicity.

**Proper method for these classes** is not the same as for stocks: carry/TSMOM need
roll-yield data (absent — the repo uses a 6-month SMA *proxy* for basis), and COT needs
positioning data lag-awareness. Recommend: before any new signal, add true roll/basis data
and test with a futures-specific cost model; otherwise every "carry" result is a trend proxy.

### 6.5 Crypto cycles — why "predict the ATH" is the wrong question

The repo's CRYPTO class is **KILL** `[V]`: n=6,740, net −0.309%, CI entirely below zero.
Cycle narratives (halving, MVRV, NUPL, funding) are *regime descriptors*, not timing signals:

- **Halving event studies have N=4** (2012, 2016, 2020, 2024). At α=0.05 and 80% power, even
  a large effect (d=0.8) needs ~25 observations per group. N=4 gives power ≈ 0.06 — you
  cannot prove a halving effect no matter what the chart looks like.
- **MVRV/NUPL/funding** are valuation/positioning states, not catalysts. They tell you when
  the market is stretched; they do not date the top. Treat them as a **regime overlay on a
  vol-scaled position**, never as an entry trigger.
- **News** is not testable in this repo (no news archive), so any "news-driven" claim is
  unfalsifiable here.

**Falsifiable design that could work:** pre-register "when MVRV-z < −0.5 and funding < 0,
go long BTC with 2× vol-targeted size, exit on MVRV-z > 2 or 30 days", with a same-window
buy-and-hold leg and a random-entry null; run it forward for 12 months. That is a regime
overlay, not an ATH predictor — and it is the honest version of the question.

---

## 7. Permutation plan — TP/SL, volume, vol targeting

The user's instinct (vary TP/SL, add volume) is right, but naive permutation is the fastest
way to manufacture a false positive. Rules:

1. **Grid, then pay for it.** TP {1, 2, 3, 4}% × SL {0.5, 1, 1.5, 2}% × horizon {5, 10, 20}d ×
   trailing {on, off} = **96 configs per cell**. Across 67 tested cells that is 6,432
   hypotheses. At that width the DSR null must use `n_trials ≥ 6,432`, which no 50-row cell
   can clear. **Pre-register 3–5 configs, not 96.**
2. **Paired, not independent.** Test TP/SL variants on the *same trades* (re-simulate exits
   from the same entries) and use a paired bootstrap on the difference. This is far more
   powerful than comparing two independent samples and avoids re-running the universe search.
3. **Volume as an overlay, not a new strategy.** Entry filter `RVOL ≥ 1.5` (volume / 20-day
   median) applied to the existing pod; compare filtered vs unfiltered on the same entries.
   That is one extra hypothesis, not a new family.
4. **Vol targeting is the highest-value test** and costs one hypothesis: scale position by
   inverse realized vol. The audit2 doctrine claims +0.3 Sharpe; the repo never tests it.
   A single backtest of the existing EQUITY breakout pod with and without vol targeting would
   validate or refute the doctrine.
5. **Power first.** For d=0.3 (a realistic edge), 80% power at α=0.05 needs ~174 rows per arm.
   The repo's own `required_n` for the best pod cells (141–294) agrees. Any permuted variant
   with n<100 cannot be confirmed; it can only be queued.

---

## 8. Ranked gaps

**P0 — the pages misstate reality**
1. `/audit` hardcoded banners (11.13%, 14.4%, 0/10, UEPS PASS at zero) and `strategy_tribunal_latest.json` 404.
2. Three different money-ready denominators across one product.
3. `dashboard_data.json` uncommitted → headline cards unreproducible.

**P1 — the promotion path is empty**
4. `POD-EQUITY-BREAKOUT` has 0 forward rows; audit2's clock has only H-119.
5. Random-entry MC and paired-benchmark bootstrap exist but are manual (`benchmark_closed_ledger.py`).
6. `verify_realized_30d` and `compute_backtest_forward_correlation` unwired.

**P2 — methodology gaps by class**
7. No mutual-fund study at all (metadata screen only).
8. Value screener is opt-in; live "value" is technical.
9. Carry/basis uses an SMA proxy (no true roll yield).
10. Crypto cycle claims have no power (N=4) and no news archive.

---

## 9. What I would do next, in order

1. **Fix the three-surface truth**: one denominator, one stale-banner purge, and publish the
   ledger's `generated_at` on every tile. (Days, not weeks.)
2. **Register `POD-EQUITY-BREAKOUT` in the forward ingest** so the EQUITY/ETF breakout path
   starts accruing rows this week. Without it, every other recommendation is academic.
3. **Wire `benchmark_closed_ledger` (random-entry null + paired bootstrap) weekly** and show
   it on `/audit2` next to each pod. That single panel would have prevented most of the
   "is it skill?" debate.
4. **Run the two cheap experiments**: (a) vol-targeting A/B on the existing EQUITY breakout
   pod; (b) RVOL≥1.5 overlay on the same entries, paired bootstrap. Both are one hypothesis
   each and directly answer the user's question.
5. **Do not permute TP/SL across 96 configs.** Pre-register 3–5 and pay the multiplicity.

## 10. What would change my recommendation

- If the forward clock for `POD-EQUITY-BREAKOUT` accrues ≥200 rows and the paired-bootstrap
  alpha CI clears zero at 2× cost, EQUITY becomes the first sizing candidate.
- If ETF `rs-breakout-scout` reaches ~201 rows with CI low > 0, it becomes a single-cell
  sizing candidate even though the ETF class mean is flat.
- If the vol-targeting A/B shows no Sharpe improvement, audit2's doctrine should be corrected
  — publishing an untested "free alpha" claim is the same defect as `/audit`'s banners.

## 11. Critique requested

Ask each reviewer to take one section and return: (a) a metric that is defined ambiguously,
(b) a number that cannot be reproduced from a committed artifact, (c) a claim that is
unfalsifiable, (d) one permutation they would pre-register. Specifically:
`/audit` → sections 1.1–1.3; `/audit2` → Doctrine and the forward clock; `/audit3` → metric
glossary §3.1 and class `required_n`; asset classes → §6.1 mutual funds, §6.2 ETF proof,
§6.5 crypto cycles.

*Not investment advice. Fund tickers above are the repo's own sample metadata, shown to
illustrate a low-cost screen, not a recommendation.*
