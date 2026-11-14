# B — Asset-Class Ranking by Realistic Profitability Potential

**Scope:** READ-ONLY synthesis. Every number below is copied from the session's research artifacts (named inline) or derived arithmetically from them. Nothing is invented. "Realistic profitability" = net-of-cost, benchmark-relative, harvestable **today** — not the PF 10–56 fantasies already falsified in this repo.

**Evidence read:** `final_v2/finpredict/per-asset-class/PROFITABILITY_ROADMAP.md`; v2 `01_audit/recommendations/per_asset_class/*.md`; v2 `02_per_asset_class_profitability/*.md`; v2 `03_research/profitability/{HYPOTHESES,SCORECARD}.md`; `final_2026_11_14/quant-audit-2026-11-14/05_final/VERDICT.md`; `final_2026_11_14/hilarious-seer/04-profitable-approach/synthesis_and_next_steps.md` + `05-research/tradingview_winner_archetypes.md`.

---

## Cross-cutting honest floor (applies to every class)

- Production ledger is **0/166 cells money-ready**; single-source gate alone kills all 166 (`VERDICT.md` §1).
- The only premia with real support are **low-vol risk premia** — trend/momentum, carry, value — with **net Sharpe ~0.3–1.0**; benchmark-relative alpha is unproven for most claims (`PROFITABILITY_ROADMAP.md`).
- 23 pre-registered candidates (v1–v4) → **0 PROVED**; the honest result is a negative (`SCORECARD.md`).

---

## Per-class scoring

### CRYPTO
- **Documented edge:** funding/basis carry (H21–H23) is the only mechanism to reach **DSR 1.0** with 2× cost survival, but it is **capital-marginal**: notional Sharpe 6.42–14.24 yet capital-adjusted return **3.7–4.8% vs 4.5% cash** (only BTC-only clears cash at 4.8%, with n=10<30); a run-length block null moves its p-value **0.002 → 1.000** (`CRYPTO.md` §1.1, `FP5`). Trend TSMOM: H1 **0.60 vs BTC B&H 0.56** (no edge); breadth H15 **0.20**; XS momentum H13 **−0.18**, reversal H14 **−0.36** (all NOT_PROVED). Roadmap trend Sharpe **0.5–2.1** (bear-inclusive → bull-flattered).
- **Capital:** low ($1 fractional, liquid majors).
- **Maintenance:** high — frozen prices (83% OPEN), 94–98% single-source concentration, 683-strategy zoo, PnL-unit bug.
- **Capacity:** low–mid for carry (capital-intensive); trend is high-capacity but shows no benchmark-relative edge.
- **Data quality:** poor today (single-source artifact, frozen marks), **but a keyless clean feed (Binance spot + funding) genuinely exists** — the one class where clean backtesting is possible *now*.

### EQUITY
- **Documented edge:** cross-sectional momentum (12-1), value (HML), quality, low-vol — decades of peer-reviewed support; realistic **net Sharpe ~0.4–0.8** for a diversified factor portfolio (`PROFITABILITY_ROADMAP.md`). Index mean-reversion H7 **1.50 Sharpe but 17.6% < 18.6% B&H**; H10 **1.83** was contaminated (post-hoc OOS, ~82.5% of the gain is T-bill carry, 2-day-lag Sharpe 0.696) (`EQUITY.md` §1.2). Live policy-clean EQUITY is significantly **negative**: WR 42.95%, PF 0.7022, z −3.03.
- **Capital:** low ($1 fractional).
- **Maintenance:** low–med (monthly factor rebalance).
- **Capacity:** high.
- **Data quality:** clean backtesting **possible today** (keyless point-in-time via yfinance); caveat: current Nasdaq panel is price-only, **no dividends**.

### FUTURES
- **Documented edge:** time-series momentum + carry — the canonical managed-futures CTA premia, most replicated in the literature; realistic **~0.5–1.0**. ITERATION-005 diversified trend **2.13 Sharpe vs B&H 2.2** (alpha unproven, PF 1.40 is a bar ratio failing its own PF>1.5 gate); independent TSMOM365 OOS **0.57, null p=0.200** (`FUTURES.md` §1.3).
- **Capital:** high (margin).
- **Maintenance:** high — gate-blocked, no continuous-contract feed, weekend emissions.
- **Capacity:** highest of any class.
- **Data quality:** poor today — no roll-adjusted continuous series; only `ES=F`/`YM=F` snapshots and crypto proxies; 0 closed in primary feed.

### BOND
- **Documented edge:** duration/trend + carry; curve carry/roll-down (H-BD-1) is real but **~0.3–0.6**. Policy-clean **n=1**, vacuous green PASS (`BOND.md`).
- **Capital:** low–med. **Maintenance:** med (FRED disabled `SKIP_FRED='1'`). **Capacity:** high.
- **Data quality:** poor — no price backfill, FRED skipped, resolver misses 12/14 bond ETFs.

### FOREX
- **Documented edge:** G10 carry + TSMOM, real but **~0.2–0.5 net** (below the project's own 1.0 gate) (`FOREX.md`).
- **Capital:** low. **Maintenance:** high — 0/277 rows pass the advertised block (dead `evaluate_non_crypto_candidate`, zero call sites), 78.8% OPEN frozen, 217d-stale feed.
- **Capacity:** low–mid. **Data quality:** poor — date-only/unparseable timestamps, 49/277 rows are currency-ETFs/`EURUSDT` mislabeled.

### COMMODITY
- **Documented edge:** roll yield/curve carry + momentum, real but capacity-limited, **~0.3–0.7** (`COMMODITY.md`).
- **Capital:** high. **Maintenance:** high — blocked, generator emits **crypto proxies** (RNDR/ARB as "silver", XLM/DOT as "oil").
- **Capacity:** capacity-limited. **Data quality:** poor — no futures-curve data in repo; licensing gap `UNVERIFIED`.

### ETF
- **Documented edge:** none survived. All 8 v3 breadth candidates failed; flagship H16 **0.98 vs 1.18 benchmark, SPA p=0.488**; policy-clean PF 1.8358 is **n=15** and collapses to **PF 0.0216** under intrabar marking (`ETF.md`).
- **Capital:** low. **Maintenance:** low. **Capacity:** high.
- **Data quality:** clean-ish (price-only, no dividends). Cheap beta vehicle, **zero alpha**.

### MUTUAL FUNDS
- **Documented edge:** none as a signal class — monthly NAV, T+1, no intraday mark, no TP/SL. Only "edge" is fee arithmetic (expense ratio), which is a product decision, not alpha. **NOT_BUILT** (`MUTUAL_FUNDS.md`). Excluded from the ranking per scope.

---

## Ranking (realistic profitability potential, net-of-cost, benchmark-relative)

| Rank | Class | Realistic net Sharpe | Verdict |
|---|---|---|---|
| **1** | **EQUITY** | 0.4–0.8 (factors) + positive beta | Only positive expected return harvestable cheaply today |
| **2** | **CRYPTO** | 0.5–2.1 trend; carry DSR 1.0 but marginal | Most researched; only DSR-1.0 mechanism; clean keyless data now |
| 3 | FUTURES | 0.5–1.0 | Deepest premia + capacity, but data-blocked |
| 4 | BOND | 0.3–0.6 | Real curve carry, but n=1 + FRED off |
| 5 | FOREX | 0.2–0.5 | Real carry but below gate; broken data |
| 6 | COMMODITY | 0.3–0.7 | Real roll yield, but no curve data |
| 7 | ETF | none | All breadth families failed benchmark-relative |
| — | MUTUAL FUNDS | none | No intraday edge possible |

---

## RECOMMENDATION — top 2 to focus on FIRST (beyond mutual funds)

### #1 — EQUITY (equity-index + diversified factor portfolio)

The only class in this session with a **positive long-run expected return that can be harvested cheaply and cleanly today**: buy-and-hold equity beta plus the cross-sectional factor premia (momentum 12-1, value HML, quality, low-vol) that carry decades of independent peer-reviewed support at a realistic **net Sharpe 0.4–0.8**. It is near-zero maintenance (monthly rebalance), has a **$1 fractional minimum**, high capacity, and clean point-in-time backtesting is possible now via yfinance (the only fix needed is adding dividend-adjusted total returns, since the current Nasdaq panel is price-only). Critically, the repo's failures here were **index mean-reversion (H7/H10) and sector rotation proxies — not the individual-stock cross-section**, which has never been tested. This is the highest realistic Sharpe-per-unit-effort in the session.

**Biggest risk:** benchmark-relative alpha is unproven — the repo's own index RSI(2) approaches failed to beat buy-and-hold (H7 17.6% vs 18.6%), and live policy-clean EQUITY is significantly negative (PF 0.7022, z −3.03). A factor portfolio must be measured **risk-matched vs the benchmark**, not on absolute return, or it will reproduce the same beta-not-alpha failure.

### #2 — CRYPTO (funding carry, with trend as the secondary sleeve)

Crypto is where the session's research is most mature and where **clean keyless data exists today** (Binance spot + funding), making it the cheapest next research increment. It holds the **only mechanism to reach DSR 1.0** — delta-neutral funding/basis carry (H21–H23) — and trend is flagged as the strongest evidence in the per-class roadmap (Sharpe 0.5 bear-inclusive to 2.1 bull-flattered). Both are real, economically-motivated risk premia, and the honest negative result so far is *specific* (carry is capital-marginal; momentum/reversal showed no net edge in 2024–26), not structural, so a narrowly scoped re-test has a defined question to answer.

**Biggest risk:** the premium may be **economically absent net of costs** — funding carry returns only **3.7–4.8% on capital vs 4.5% cash** (block-null p → 1.000), and trend is benchmark-relative-unproven (H1 0.60 vs BTC B&H 0.56). Crypto is the most likely class to end as another honest NOT_PROVED; it is ranked #2 on **data-readiness and depth of prior work**, not on a validated equity-beating edge.

---

## Runner-up worth naming

**FUTURES** has the deepest documented, most replicated premia (TSMOM + carry) and the most capacity, but it is gate-blocked with **no continuous-contract data** — it is the highest-*ceiling* class, not the *first* class. Focus effort there only after a real futures feed is licensed; the roadmap explicitly vetoes unblocking it on ETF/`ES=F` proxies.
