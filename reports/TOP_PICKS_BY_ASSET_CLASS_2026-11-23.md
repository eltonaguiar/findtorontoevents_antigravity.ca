# Top-ranked picks per asset class, and the overall ranking

**As of 2026-11-23.** Paper only. Zero capital sanctioned. **Not investment advice.**

---

## 0. Two things to read before the tables

**One: I could not load the system vault.** The operating documents I was pointed at — `vault/00_System/00_Constitution.md`, `01_Data_Contract.md`, `03_Measurement_SOP.md`, `04_Operating_Protocol.md`, `05_Banned_Patterns.md`, the three `MEMORY/*.md` files, `LIVE_DASHBOARD.md`, `07_Methodology/08_AI_Coding_Agent_Protocol.md`, `03_Data/01_DATA_SOURCES.md`, and the two `raw/` reports — **do not exist anywhere on this filesystem.** No `vault/` directory exists in this repo. I searched the whole of `/home/eaguiar2015` for each by name. So this document is written against the rules I *could* verify (`CLAUDE.md`, `AGENTS.md`, the hypothesis-registry rule, `reports/hedge_fund_performance_review_*` tier table), and I have not silently substituted my own constitution for yours.

**Two: "top pick" here does not mean "highest expected return."** It means *the choice with the best evidence behind it*. In this estate that is almost always a **cost** fact, not a return forecast. Cost facts are certain; return forecasts here are not evidence at all. Every table says which basis it is using, and you should refuse to read a fee ranking as a performance claim.

---

## 1. The overall answer: what is worth spending money on

Ranked by *strength of evidence*, not by excitement.

| Rank | What | Why it ranks here | Strength |
|---|---|---|---|
| **1** | **Avoiding the 150 bp FX conversion** | Measured, binary, and 150× larger than every other equity cost combined. This is the single highest-value decision available. | **MEASURED** — `reports/equity_cost_hml.json` |
| **2** | **Refusing active mutual funds** | 17.6× the lifetime fee of an index ETF for no measurable alpha. Certain arithmetic. | **MEASURED** — fee arithmetic below |
| **3** | **Broad index ETF, held** | Ranked as a *vehicle*, not an edge. It is the cheapest way to own beta. It has **no measured alpha** and I do not claim one. | **VEHICLE / no alpha claim** |
| **4** | **T-bills at the 4.32% hurdle** | The thing every strategy must beat. 0 of 6 classes do. Holding the hurdle is a legitimate position, not a failure to invest. | **MEASURED** — `tools/capacity_model.py` |
| **5** | **Everything else** | No class has both n ≥ 100 and PF > 1. | **UNPROVEN** |

**The reason for this ordering:** the top four are *decisions about cost and structure*, where the arithmetic is checkable and does not decay. The fifth is *return prediction*, where 20 registered hypotheses have been refuted and the binding constraint is multiple-testing debt at ≈0.002 DSR per trial. Ranking anything from #5 highly would be asserting a number I cannot defend.

### The one crisp statistical claim

> **Zero classes have both n ≥ 100 and profit factor > 1.**

Three classes clear n ≥ 100 — CRYPTO (n=22,985, PF 0.258), FOREX (n=468, PF 0.175), EQUITY (n=218, PF 0.606). All three are below 1.0. Every class above PF 1.0 has n ≤ 35. Source: `audit_dashboard/data/dashboard_data.json → performance.asset_class_health`, generated `2026-11-22T04:00:19Z`.

---

## 2. A contradiction in the payload you must know about

The same 25.8 MB payload carries **two** per-class panels that disagree — and for FOREX they disagree on the *sign*:

| Class | `asset_class_health` | `by_asset_class` (raw) |
|---|---|---|
| FOREX | n=468, WR 33.1%, **PF 0.175** | closed=95, WR 23.2%, **PF 1.64** |
| CRYPTO | n=22,985, WR 41.0%, PF 0.258 | closed=5,044, WR 39.7%, PF 0.86 |
| ETF | n=33, WR 63.6%, PF 1.886 | closed=16, WR 37.5%, PF 1.44 |
| COMMODITY | n=35, WR 31.4%, PF 0.326 | closed=19, WR 15.8%, PF 0.09 |

Both FOREX rows are internally consistent (raw: 22 wins × 0.96 = 21.1; 73 losses × 0.18 = 13.1; PF = 1.61 ✓). They differ because they are measuring different things over different denominators — the health panel's n (468) is ~5× the raw panel's closed count (95).

**Consequence:** any ranking built on one panel is refutable by the other. I therefore do **not** rank the classes on profit factor. The n≥100-and-PF>1 statement survives both panels (every PF from either panel is < 1 for the three large-n classes, except FOREX's raw 1.64 — which I flag as unresolved rather than adopt, because adopting it would be picking the panel that gives the answer I prefer). Resolving this is an open P1 and should be done before any capital decision.

---

## 3. Per-class rankings

Each table names instruments. **The "basis" column is the whole argument** — if it says fee or liquidity, there is no return forecast behind the pick.

### 3.1 EQUITY — basis: cost only. Measured round trip **0.98 bp**.

| # | Instrument | Basis | Evidence |
|---|---|---|---|
| 1 | Low-cost US total-market index ETF (VOO / VTI), **held in a USD account** | 0.98 bp RT; FX avoided | MEASURED |
| 2 | Same, CAD-listed equivalent (VFV/XEQT) | Avoids 150 bp conversion; pays a small MER premium for it | MEASURED tradeoff |
| 3 | Individual liquid large caps (ADV > $250 M) | 0.98 bp RT; participation 0.008% at $20k | MEASURED |
| 4 | Anything requiring CAD↔USD round trips per trade | **150 bp RT** — 150× worse | MEASURED |
| 5 | — | No 5th pick is defensible. There is no measured equity edge to justify a concentrated pick. | — |

Equity signals remain **unproven**: PF 0.606, WR 38.5%, n=218 (stressed). The HML value test that ran today returned **KILL** — gross +0.11%/yr, net **+0.02%/yr** against a 4.32% hurdle, SE 6.65% (`reports/hml_result.json`). Note the repo constant `pod_equity_breakout_backtest = 25.0 bp` is wrong in *both* directions: it is 25× too high for a USD-account round trip and 6× too low for one that crosses FX.

### 3.2 ETF — basis: fee + no alpha claim

| # | Instrument | Basis | Evidence |
|---|---|---|---|
| 1 | Broad-market index ETF | Lowest lifetime cost (~$1,050 per $100k/10yr) | MEASURED |
| 2 | Same, as the *only* thing you hold | Removes the turnover that costs 150 bp a go | MEASURED |
| 3 | — | ETF's PF 1.886 is **n=33**. That is not an edge, it is 33 trades. Sharpe 0.44 is the *asset's*, not a signal's — this is a beta reading, not alpha. | UNPROVEN |

Freebuff's correction is the right frame and I adopt it: ETF and INDEX showed **positive absolute** CI lower bounds while running **negative excess against their own benchmarks**. ETF passes as a fee decision and fails as a signal.

### 3.3 MUTUAL FUND — basis: fees, and this is where the arithmetic bites

| # | Instrument class | Lifetime fee, $100k/10yr | Assumed MER | Basis |
|---|---|---|---|---|
| 1 | Direct index (no wrapper) | **$0** management fee | 0.000%/yr | computed — transaction/spread costs excluded |
| 2 | Index ETF | **≈ $1,050** | 0.105%/yr | computed |
| 3 | **Index mutual fund** (low-MER) | **≈ $4,520** | 0.452%/yr | computed |
| 4 | Active mutual fund | **≈ $18,520** | 1.852%/yr | computed |
| 5 | — | **MUTUAL_FUND has n = 0.** No performance measurement exists at all. | — | UNMEASURED |

**These are `assumed MER × balance × years`, simple (not compounded).** The MERs are illustrative levels typical of Canadian retail products — **not scraped from fund documents** — so treat the *ratios* as the finding (index MF **4.3×** an index ETF; active MF **17.64×**) and the absolute dollars as replaceable. Compounding is deliberately omitted because including it would make the expensive products look worse, i.e. this choice is conservative against my own conclusion. Reproduce with `python3 tools/fee_arithmetic.py`; artifact `reports/fee_arithmetic_2026-11-23.json`.

**Yes — mutual funds can legitimately be among the winners, but only for reasons that are not performance.** Two reasons people are right to use them, and one that decides the ranking:

- **Minimums and maintenance fees** make the small-account case. A fund with a $1,000 minimum and a $25/yr admin fee is a *4.5%/yr* drag at $550 — catastrophic, and invisible in any MER comparison. At $50,000 the same fee is 5 bp. **The fee is fixed, the account is not: this is an account-size decision, not a fund-quality decision.**
- **Automatic contributions** have real behavioural value that beats fee arithmetic for many people. I will not pretend a spreadsheet beats that.
- **But at equal account size, an index mutual fund costs 4.3× an index ETF and 90× direct over ten years.** An active fund costs **17.6×** the index ETF. So a mutual fund earns a top-3 ranking only if the fixed-fee/small-balance or automation effect actually applies to you. If it does not, it is the most expensive way to buy the same beta.

### 3.4 BOND — basis: unmeasured, and previously mis-attributed

| # | Instrument | Basis | Evidence |
|---|---|---|---|
| 1 | T-bills / short GICs at the 4.32% hurdle | The hurdle itself is the return | MEASURED |
| 2 | Short-duration aggregate bond ETF (ZAG/XBB) | Liquidity; no alpha claim | VEHICLE |
| 3 | — | **No bond cost has ever been measured in this repo.** | UNMEASURED |

**Correction I owe you, repeated here because it is a live hazard:** the BOND cost of **42.64 bp** I previously quoted is claim C-013 — *"delta-neutral funding carry, 42.64 bp retail-taker round trip"* — which is **CRYPTO**. `cost_measurement_20261122.json` contains **no bond entry at all**. A number on the wrong asset class is exactly what survives into someone's trading decision. BOND health is n=2 (100% WR on two trades — meaningless).

### 3.5 COMMODITY — basis: no measurement, worst measured performance

| # | Instrument | Basis | Evidence |
|---|---|---|---|
| 1 | Broad commodity ETF (PDBC/GSG) | Diversified; no alpha claim | VEHICLE |
| 2 | Gold (GLD / CAD-hedged) | Store-of-value role only | VEHICLE |
| 3 | — | PF 0.326, WR 31.4%, n=35 (health) / PF 0.09, WR 15.8%, n=19 (raw). Both bad. No cost measurement exists. | UNPROVEN |

### 3.6 FOREX — basis: **the sign is undetermined**; do not size

| # | Position | Basis | Evidence |
|---|---|---|---|
| 1 | No position | Net **−0.68 bp** at the 4.98 bp cost of record; **−3.23 bp** at freebuff's 7.533 bp | UNRESOLVED |
| 2 | — | −0.68 bp is inside noise. The sign of the edge is not established. | — |

The deciding cost **7.533 bp is not in this repo** — `grep -o "7\.533" reports/fx_meanrev_cost_sweep/*` returns nothing; only the 4.3038 bp break-even is committed. So the FOREX verdict is currently auditable from the COMS bus, not from the repository. One weekday London/NY top-of-book run decides it, and the output must land in `reports/`.

### 3.7 CRYPTO — basis: cost known, edge refuted

| # | Instrument | Basis | Evidence |
|---|---|---|---|
| 1 | BTC / ETH spot, buy-and-hold | Cheapest to trade: 10 bp/side on binance/binanceus/kucoin | MEASURED cost |
| 2 | Same, on kraken | 26 bp/side → 52 bp RT. Reproduces. | MEASURED |
| 3 | Anything needing frequent rotation | RT 20.0–52.0 bp **per round trip**; at daily rotation that is ~50%/yr of cost | MEASURED |
| 4 | — | PF 0.258, WR 41.0%, n=22,985. The largest sample in the estate is the *worst* performer. | UNPROVEN |

My earlier 12.60 bp figure was a mid-band choice labelled MEASURED. It is not measured; it is a choice inside the 20.0–52.0 bp band. Corrected.

### 3.8 MEMECOIN — do not. Basis: measured, and it is terrible

PF **0.023**, WR **10.0%**, n=10. Ten trades, one winner, and the profit factor says gross loss is ~43× gross profit. There is no cost measurement, no mechanism, and no capacity. **This is the only class where I will say plainly: no position.**

### 3.9 OPTIONS — no infrastructure exists

**Zero** occurrences of "OPTION" in the entire 25.8 MB dashboard payload. There is no options pick pipeline, no cost measurement, no greeks, no settlement model. Naming "top 5 options" would be pure invention, so I am not doing it. To make options rankable you would first need: a cost model (spread + commission + assignment), an exercise/expiry model, and a defined underlying-price source. All three are absent.

### 3.10 CHEAP_STOCKS / PENNY_STOCK / FUTURES

CHEAP_STOCKS PF 0.390 (n=2), PENNY_STOCK PF 0.178 (n=4), FUTURES PF 1.271 (n=17). All insufficient-n. **No picks.**

---

## 4. "Could we have predicted the top gainers?" — measured, and the answer is no

This was the substantive new question, so I tested it rather than asserted it. Two hypotheses were **pre-registered before the backtest ran** (`reports/hypothesis_registry.json`, H-237 and H-238), per the registry rule.

**Setup:** 118 liquid US large caps, 1,506 daily bars, 2020-11-23 → 2026-11-20. Rank each period by trailing return, hold the top decile equal-weight. Benchmark = **the universe's own mean return**, so beta cannot masquerade as skill. Cost charged **every rebalance** at the measured 0.98 bp.

| Test | n | Excess/rebalance | 95% CI lower | Verdict |
|---|---|---|---|---|
| **H-237 daily chase** (rank 1d → hold 1d) | 1,504 | +1.61 bp | **−4.38 bp** | **REFUTED** |
| **H-238 weekly swing** (rank 5d → hold 5d) | 1,496 | −2.24 bp | **−22.75 bp** | **REFUTED** |
| sens: 5d look → 1d hold | 1,500 | +1.00 bp | −4.81 bp | REFUTED |
| sens: 1m look → 1m hold | 1,464 | −22.13 bp | −93.95 bp | REFUTED |
| sens: 3m look → 1m hold | 1,422 | −30.55 bp | −117.61 bp | REFUTED |
| sens: daily top 2% only | 1,504 | +5.43 bp | −5.28 bp | REFUTED |

**Six variants, six refutations.** The Jensen alpha tells the same story: daily chase **+6.48%/yr with CI [−10.41%, +21.27%]**, weekly swing **−3.11%/yr with CI [−17.10%, +12.53%]**. Neither interval excludes zero.

**The honest verdict: there is no evidence we could have predicted next-day, next-week, or next-month top gainers** on this universe over this window. Note also that the universe is names liquid *today*, which **inflates** long-only results — so a FAIL here is strong evidence while a PASS would have been weak.

### The bug that almost produced a fake answer

The first run reported a **+880% annual alpha**. That is not an edge; it is a defect. Three of them:

1. **Look-ahead** — the strategy ranked names using day *d*'s return and then captured day *d*'s return. Ranking on a bar and then trading that same bar manufactures performance out of nothing. Fixed by entering at *d+1*.
2. **A double shift** — `fwd = logret.shift(-hold).rolling(hold).sum().shift(-(hold-1))`. The extra shift moved the result by `hold-1` and misaligned every multi-day test.
3. **A hurdle test that rewards beta** — comparing raw net return to 4.32% "passed" a book with beta 1.24 in a bull market. This is the *same* trap freebuff identified and that the two-hurdle gate was built to stop. The deciding field is now the universe-relative CI, which is beta-free.

Each fix is commented in `tools/top_gainer_test.py` with the reason. Runner: `tools/top_gainer_test.py`; artifact: `reports/top_gainer_test.json`.

### What this does *not* say

It does not say momentum is dead everywhere. It says: on 118 large caps, at the measured cost, with the universe mean as the benchmark, **the extreme-gainer slice has no demonstrable edge**, and the daily version costs 2.85%/yr in turnover to find that out. The reverse-engineering you asked for is now done, and the answer is that the screen most retail "top gainer" dashboards sell does not survive honest measurement.

---

## 5. The ML algorithms — what exists, what they showed

There is a large ML surface in this repo (gatekeeper, consensus, tournament, walk-forward validators). What it has **not** produced is a class that clears both n ≥ 100 and PF > 1. The ML layers are best read as **filters that reduce bad picks**, not as alpha generators — and the `system_clean_metrics` / `backtest_vs_forward` panels exist precisely because forward results have been worse than backtest. Any "ML says buy X" claim should be rejected unless it names the class, the n, the cost basis, and the forward (not backtest) window.

---

## 6. What would change this ranking

| Change | Effect |
|---|---|
| Resolve the FOREX panel contradiction (§2) | Could move FOREX from "undetermined" to a real verdict, either way |
| Measure the 7.533 bp FOREX cost into `reports/` | Decides the FOREX sign |
| A class reaching n ≥ 100 **with** PF > 1 **and** a beta-adjusted alpha CI excluding zero | The first genuine promotion candidate |
| Cheaper trial budget (currently ≈0.002 DSR/trial) | Raising statistical power is the actual constraint, not more strategies |

---

## 7. Provenance

| Number | Source |
|---|---|
| EQUITY 0.98 bp / 151 bp FX | `reports/equity_cost_hml.json` |
| HML KILL, net +0.02%, SE 6.65% | `reports/hml_result.json`, `tools/hml_pit_backtest.py` — note this run charged **4.9746 bp** RT, not the newer 0.98 bp; at 0.98 bp the net improves marginally and is still far below the 4.32% hurdle |
| Per-class n/WR/PF | `audit_dashboard/data/dashboard_data.json → performance.asset_class_health`, gen. `2026-11-22T04:00:19Z` |
| Contradicting raw panel | same payload → `performance.by_asset_class` |
| Top-gainer results | `reports/top_gainer_test.json`, `tools/top_gainer_test.py` |
| Fee arithmetic | `reports/fee_arithmetic_2026-11-23.json`, `tools/fee_arithmetic.py` — **ASSUMED MERs**, simple not compounded |
| Hurdle 4.32% | `tools/capacity_model.py:49` |
| Registry verdicts | `reports/hypothesis_registry.json` — H-237, H-238, n=122, 20 REFUTED |

Zero capital sanctioned. Paper only. Not investment advice.
