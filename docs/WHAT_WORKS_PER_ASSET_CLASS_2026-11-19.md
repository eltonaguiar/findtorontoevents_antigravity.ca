# What actually works per asset class — evidence review and test plan

**Date:** 2026-11-19
**Purpose:** answer "how do we get a money-maker per asset class?" with evidence grades, not
narratives, and cross-check the claims our own surfaces make.
**Companion:** `docs/AUDIT_SURFACES_FULL_REVIEW_2026-11-19.md` (surface/metric review).

---

## 0. Method and evidence grades

Each effect is graded on **how it was established**, not on how good the story sounds:

| Grade | Meaning |
|---|---|
| **A** | Replicated across many markets and decades, survives out-of-sample and costs at institutional scale |
| **B** | Robust in the literature but decays, is regime-dependent, or is capacity-constrained |
| **C** | Plausible, but the evidence is a single study, a short sample, or parameter-sensitive |
| **D** | Claim only — no forward data, no out-of-sample test, or statistically underpowered in our repo |

Two rules used throughout:

- **A backtest is a hypothesis, not evidence.** Evidence needs out-of-sample + costs + a
  multiplicity correction. We now have the machinery (`audit3` DSR/BH, `pbo_cscv`,
  `benchmark_closed_ledger`) to enforce that; the gap is wiring (§4 of the surface review).
- **Power first.** At 80% power and two-sided 5%, detecting a mean edge of 0.3 SD needs ~87
  trades; 0.2 SD needs ~196. Any "works" claim on n<30 is a guess.

---

## 1. Cross-check of our own claims against the literature

| Our claim | Where | Literature | Verdict |
|---|---|---|---|
| "Vol scaling is free alpha… +0.3 Sharpe for any momentum strategy" | `/audit2` Doctrine | Vol-managed portfolios do raise Sharpe in published work (Moreira & Muir 2017; Barroso & Santa-Clara 2015 on momentum), but the size is strategy- and sample-dependent, and "any" is not supported | **B, overstated** — and **we never test it**; add the A/B (below) |
| ETF top-3 sector rotation: PF 2.05, Sharpe 0.97, MDD 16.1% (2015–2026) | `reports/etf_abc_backtest_20260513.md` | Monthly sector rotation is a real but modest effect; a PF of 2.05 over ~132 monthly observations on an 11-asset universe needs CPCV/PBO before it is a claim | **C** — run `pbo_cscv` + DSR with `n_trials` = the grid actually searched |
| ETF dual momentum: OOS PF 2.746 | `reports/edge_hunt_ETF_2026-06-05.md` | – | **D** — n=11, below every floor we use (WR_MIN_N=20, CANDIDATE_MIN_N=30) |
| Value screener (Magic Formula/Piotroski/FCF) | `alpha_engine/value_screener.py` | Value and quality are Grade-A factors, but at 3–5 year horizons | **A factor, D in-house** — no committed backtest output; evaluate on annual rebalance, not the trade tribunal |
| Crypto ATH via halving cycles | absent from code, common narrative | Halving N=4; power ≈ 0.06 for any realistic effect | **D** — unfalsifiable with the available sample |
| "A random active mutual fund likely breaks even" | user intuition | Arithmetic: return = beta − fees ± alpha. Index ER 0.015–0.05% vs active ~0.25%+; the median active fund's *net* alpha is negative | **True before fees, false after** — see §2.1 |

---

## 2. Per asset class — what works, what we can test

### 2.1 Mutual funds — the answer is fee arithmetic, not manager skill

**What works:** cheap, broad, tax-efficient index exposure. That is not a strategy; it is a
cost decision. Return ≈ market beta − expense ratio − trading costs. Every extra 10 bp of fee
is a certain loss; manager alpha is an uncertain gain with a negative median.

**Evidence:** Grade A for the arithmetic; Grade A− for "active persistence is weak" (the
industry-standard SPIVA series; I could not re-fetch its page today — 403 — so treat the
specific percentages as external context, not as a number I verified this session).

**Our own screen** (`alpha_engine/data/mutual_fund_metadata_sample.json`) already encodes the
right filters — index flag, expense ratio, load, 12b-1, AUM, turnover, tracking error:

| Fund | Type | ER | Load/12b-1 |
|---|---|---:|---|
| FXAIX | S&P 500 index | **0.015%** | 0 / 0 |
| SWTSX | Total US market index | 0.03% | 0 / 0 |
| VTSAX | Total US market index | 0.04% | 0 / 0 |
| VFIAX | S&P 500 index | 0.05% | 0 / 0 |
| VBTLX | US bond index | 0.05% | 0 / 0 |
| VTIAX | International index | 0.11% | 0 / 0 |
| VGSLX | REIT index | 0.12% | 0 / 0 |
| VWELX | Wellington (active balanced) | 0.25% | 0 / 0 |

**What to test:** fund-vs-benchmark net return over ≥10 years with a survivorship-free
universe. **Gap: we have no NAV history and no such study.** The honest in-house verdict on
mutual funds is "cost screen only; no edge claim".

### 2.2 ETFs — the best evidence we have, and the biggest proof gap

**What works (Grade A for beta, B for factors):** low-cost beta; factor tilts (momentum,
quality, value, low-vol) implemented as ETFs; and monthly sector rotation — which is a
momentum/trend strategy wearing an ETF wrapper.

**Our strongest artifact:** top-3 long-only SPDR sector rotation, monthly, 2015–2026:
PF 2.05, Sharpe 0.97, total +283.7%, MDD 16.1%, robust to five friction scenarios; long-short
and Black-Litterman made it worse. The low turnover (0–1 leg changes/month) is why costs do
not kill it — a genuinely favourable property.

**Why it is still Grade C:** ~132 monthly observations, 11 assets, top-3 selection. That is
exactly the setting where a 2.05 PF can be selection noise. Required: CPCV PBO and DSR with
the real grid size, plus a forward clock.

**The blocker:** the live ETF class is PF 0.80 (single-source `cta_golden_cross` noise) and the
forward pilot has **n=0**. The best cell (`rs-breakout-scout`, n=80, net CI low −0.146) needs
~201 rows to confirm.

### 2.3 Equities — momentum, value, quality, and PEAD

| Effect | Grade | Horizon | What our repo has |
|---|---|---|---|
| Cross-sectional momentum (12-1) | **A** | 1–12 months | Donchian/breakout scouts (a trend proxy, not XS momentum) |
| Value (B/M, E/P) | **A** | 3–5 years | Real screener (`value_screener.py`), opt-in, no backtest |
| Quality (profitability, low accruals) | **A−** | 3–5 years | Piotroski inside the value screener |
| Low volatility / betting-against-beta | **B** | 1–12 months | Absent as a live factor |
| Post-earnings announcement drift | **B (decayed)** | days–weeks | `equity_pead_strategy.py`, shadow only, no backtest |
| Short-term reversal | **B, cost-sensitive** | days | `vwap-reversion-scout`, WEAK at n=25 |

**What works in practice:** 12-1 momentum with a trend filter, monthly rebalance, vol-scaled
sizing. That is also what the ETF sleeve already approximates. **Gap:** no cross-sectional
momentum implementation (only per-symbol breakout), and no factor-neutral construction.

### 2.4 Bonds — carry and duration trend

**What works:** carry (term premium, credit spread) and trend on duration. Grade B: real, but
regime-dependent and prone to correlated drawdowns in recessions (the same finding as in the
Carry paper, where carry strategies across *all* asset classes fail together in global
recessions).

**Our repo:** `bond_strategies.py` has curve slope, UST TSMOM, credit-spread MR, duration
rotation; live via `bond-agent.yml`. The audit says BOND net −0.184% (n=35) — insufficient
sample, not a verdict. **Gap:** no true duration/credit factor construction; the class needs
n≥100 before any claim.

### 2.5 Futures — time-series momentum is the most replicated effect in the book

**What works (Grade A):** time-series momentum / trend following.

- Moskowitz, Ooi & Pedersen (2012, *JFE*): past 12-month excess return predicts future return
  across **58 futures and forward contracts** (equity indices, currencies, commodities,
  sovereign bonds) over 25+ years; profits positive for **every** contract; the effect persists
  ~1 year then partially reverses.
- Hurst, Ooi & Pedersen (2017, *JPM*): the same strategy back to **1880** is consistently
  profitable over 110 years.

**Evidence quality:** this is the strongest single result we can build on — multi-market,
multi-decade, out-of-sample by construction.

**Our repo:** `futures_tsmom` exists and is live, but the audit has FUTURES n=4. The strategy
is right; the sample is empty. **This is the highest-confidence "what works" per unit of
implementation effort.**

### 2.6 Commodities — carry/basis first, momentum second, seasonality last

**What works:** carry (roll yield/basis) is the documented premium — Koijen, Moskowitz,
Pedersen & Vrugt (2018, *JFE*) show carry predicts returns in commodities as it does in
equities, bonds, currencies, Treasuries and credit (Grade A−). Momentum is Grade B;
seasonality is Grade C; COT positioning is Grade C (lag, commercial/Non-commercial ambiguity).

**Our repo:** basis is a **6-month SMA proxy**, not true roll yield; seasonality and COT modules
exist. Commodity class is KILL (n=51, net −3.5%). **Gap:** without true curve data, every
"carry" result is a trend proxy — fix the data before the signal.

### 2.7 Forex — carry and momentum, with crash risk

**What works:** carry (Grade A−, with the well-documented crash risk), cross-sectional
momentum (B), value/PPP (B). Our repo has all three; FOREX class is −0.024% (n=258) and
`fx_prices` ends 2026-02-09, so 211 picks are unmeasurable. **Gap: data freshness, not signal
inventory.**

### 2.8 Crypto — momentum and funding carry, not ATH prediction

**What works:** time-series momentum (B, short sample), funding-rate carry (B), and
valuation/positioning overlays such as MVRV/NUPL (C — regime descriptors, not timing).

**Why "predict the ATH" is not a testable goal here:** halving events N=4 → power ≈ 0.06.
News is not archived in our repo, so any news-driven claim is unfalsifiable. The repo's CRYPTO
class is KILL (n=6,740, net −0.309%, CI entirely below zero).

**Honest version of the question:** a pre-registered regime overlay — "when MVRV-z < −0.5 and
funding < 0, hold BTC at 2× vol-targeted size; exit on MVRV-z > 2 or 30 days" — with a
same-window buy-and-hold leg and a random-entry null. That is testable; "will it hit a new ATH
by month X" is not.

---

## 3. What this implies for our system

**Ranked by evidence × feasibility:**

1. **Futures TSMOM** — Grade-A effect, module already exists, n=4. Register it in the forward
   clock; this is the cheapest path to a defensible result.
2. **ETF sector rotation** — strongest backtest (PF 2.05), but needs PBO/DSR and ~200 forward
   rows. Pre-register it; do not size it.
3. **Equity momentum/breakout** — the pod (`POD-EQUITY-BREAKOUT`) already exists with 8 cells;
   it needs forward rows, not new signals.
4. **Bonds** — carry/trend is real but our n=35 cannot say anything. Get to n≥100.
5. **Commodities** — fix roll data before trusting any carry result.
6. **Mutual funds** — no strategy; publish the cost screen and stop claiming edge.
7. **Crypto** — TSMOM + funding carry only; drop ATH prediction as a research goal.

**Three cheap experiments (one hypothesis each):**

- **Vol-targeting A/B** on the existing EQUITY breakout pod: same entries, size ∝ 1/realized
  vol. Tests audit2's doctrine directly.
- **RVOL ≥ 1.5 overlay** on the same entries: paired bootstrap on the *same trades*, not a new
  universe. Answers "does volume improve the hit rate?" without multiplying the search space.
- **TP/SL pre-registration**: 3–5 configs, not 96. 96 × 67 cells = 6,432 hypotheses, which no
  50-row cell can survive.

## 4. What we still cannot prove

- Mutual funds: no NAV history → no fund study.
- Commodities: no true roll/basis → carry is a proxy.
- Crypto cycles: N=4, no news archive → no ATH model.
- Everything: forward rows. The promotion clock currently holds 430 rows, all H-119.

## 5. Sources

**Verified this session (full abstract read):**
- Moskowitz, Ooi & Pedersen, "Time Series Momentum", *JFE* 2012 — aqr.com.
- Koijen, Moskowitz, Pedersen & Vrugt, "Carry", *JFE* 2018 — aqr.com.
- Hurst, Ooi & Pedersen, "A Century of Evidence on Trend-Following Investing", *JPM* 2017 — aqr.com.

**Not re-verified (page blocked today, cited as external context only):** SPIVA active-vs-index
persistence; Moreira & Muir (2017) vol-managed portfolios; Barroso & Santa-Clara (2015)
momentum risk. Do not quote specific percentages from these in our product until re-fetched.

*Not investment advice. Fund tickers are our own metadata sample, used to illustrate a cost
screen.*
