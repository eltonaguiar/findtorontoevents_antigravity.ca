# C — Mutual-Fund / Index-Fund Subset: Most Capital-Efficient "Always-On" Sleeve

**Repo grounding.** `multi_asset/portfolio_defs.py` defines a tactical-rotation book
(`tactical_fund_rotation` over `VTSAX`/`VBTLX`-class funds). The untracked `mutual_fund_ranker.py`
prototype (typo'd "mutut") and the multi-asset audit
(`reports/2026-10-22-mutual-fund-multi-asset-audit.md` + `quick_wins/05_mutual_funds/`) already
established the key conclusion: **mutual funds have no intraday mark (end-of-day NAV only), so
they can never be a trading edge.** They *can* be a low-maintenance, positive-expected-return
long-term sleeve — i.e. the beta/cash-carry baseline every "edge" in this repo failed to beat.

This doc names the concrete vehicles that require the least money in, the lowest maintenance
fees, and the least capital, and maps them into the repo as a *benchmark*, not a pick emitter.

---

## 1. The low-fee / low-minimum / low-capital subset

> Expense ratios and minimums are widely-documented figures as of 2026. **Verify current values**
> on the fund sponsor's page before acting; several have been cut in the last 2 years.

### 1a. ETFs — intraday mark, fractional shares, NO minimum (the capital-efficient default)

| Ticker | Name | ER | Minimum | Notes |
|---|---|---|---|---|
| **VTI** | Vanguard Total Stock Market ETF | 0.03% | $0 (fractional from ~$1) | Broker-agnostic; total US market (~3,700 stocks) |
| **VOO** | Vanguard S&P 500 ETF | 0.03% | $0 | 500 large caps |
| **ITOT** | iShares Core S&P Total US Stock Market | 0.03% | $0 | VTI equivalent |
| **SCHB** | Schwab US Broad Market ETF | 0.03% | $0 | VTI equivalent |
| **VXUS** | Vanguard Total International Stock ETF | 0.07% | $0 | ex-US completion |
| **BND** | Vanguard Total Bond Market ETF | 0.03% | $0 | US aggregate bond |
| **AGG** | iShares Core US Aggregate Bond | 0.03% | $0 | BND equivalent (verify: was 0.04%) |
| **SCHZ** | Schwab US Aggregate Bond ETF | 0.03% | $0 | BND equivalent |
| **VGSH** | Vanguard Short-Term Treasury ETF | 0.04% | $0 | 1–3 yr Treasury — the "cash floor" |
| **SGOV** | iShares 0–3 Month Treasury Bond ETF | 0.09% | $0 | T-bill proxy, ~4–5% carry (verify) |
| **BIL** | SPDR Bloomberg 1–3 Month T-Bill | 0.1356% | $0 | Legacy T-bill proxy |

Key property: ETFs trade intraday, settle T+1, support fractional shares at most brokers
(Fidelity, Schwab, Vanguard, Robinhood, SoFi), so **minimum capital = 1 share or ~$1**.

### 1b. Open-end mutual funds — NAV end-of-day, higher minimum, only for auto-invest drip

| Ticker | Name | ER | Minimum | Notes |
|---|---|---|---|---|
| **FZROX** | Fidelity Zero Total Market Index | 0.00% | $0 | Zero-ER; locked to Fidelity (non-portable) |
| **FZILX** | Fidelity Zero International Index | 0.00% | $0 | Zero-ER ex-US |
| **FNILX** | Fidelity Zero Large Cap Index | 0.00% | $0 | Zero-ER large cap |
| **FXAIX** | Fidelity 500 Index | 0.015% | $0 | Ultra-low 500 |
| **FXNAX** | Fidelity US Bond Index | 0.025% | $0 | Aggregate bond |
| **VTSAX** | Vanguard Total Stock Market Admiral | 0.04% | $3,000 | Mutual-fund share class of VTI |
| **VFIAX** | Vanguard 500 Index Admiral | 0.04% | $3,000 | |
| **VBTLX** | Vanguard Total Bond Market Admiral | 0.05% | $3,000 | |
| **VTIAX** | Vanguard Total International Admiral | 0.11% | $3,000 | |
| **SWTSX** | Schwab Total Stock Market Index | 0.03% | $0 | Schwab lowered min to $0 |

### 1c. Target-date funds — one-fund autopilot (higher ER, zero thought)

| Ticker | Name | ER | Minimum |
|---|---|---|---|
| **VFFVX** / Vanguard Target Retirement 20xx | Vanguard Target Index series | ~0.08% | $1,000 |
| **Fidelity Freedom Index 20xx** | Fidelity Freedom Index series | ~0.12% | $0 |
| **Schwab Target 20xx Index** | Schwab Target Index series | ~0.08% | $100 |

### 1d. Treasury-only money market / direct T-bills — the "cash floor"

| Vehicle | ER / cost | Minimum | Current carry |
|---|---|---|---|
| **VUSXX** | Vanguard Treasury Money Market | 0.09% | $3,000 | ~4–5% |
| **SPAXX** | Fidelity Government MM (core sweep) | 0.42% | $0 | ~4–5% |
| **Direct T-bills** (TreasuryDirect) | 0.00% fee | **$100** | ~4–5%, state-tax exempt |

---

## 2. Best default + the 2–3 fund core

**Single best default: `VTI` (Vanguard Total Stock Market ETF, 0.03% ER, $0 min, fractional
shares).** Rationale:
- **Least capital:** fractional shares mean you can start with ~$1–$100; no $3,000 Admiral minimum.
- **Least maintenance:** buy-and-hold one total-market fund; no rebalancing, no NAV timing.
- **Lowest cost that is still portable:** `FZROX` is 0.00% but locked to Fidelity (cannot transfer
  in-kind); `VTI` is 0.03% and broker-agnostic. The 3 bp is worth the portability.

**3-fund "core" (total-market + total-bond + short-Treasury):**

| Sleeve | Vehicle | ER | Role |
|---|---|---|---|
| US equity beta | **VTI** (or FZROX 0.00% if Fidelity-locked) | 0.03% | market beta, ~7–9% nominal |
| Diversifier / ballast | **BND** (or FXNAX 0.025%) | 0.03% | aggregate bond, dampens drawdown |
| Cash floor / carry | **SGOV** or **VGSH** (or VUSXX MM / direct T-bills) | 0.04–0.09% | T-bill carry, ~4–5% current |

Typical weight: 60–80% VTI / 10–20% BND / 10–20% short-Treasury (age/risk dependent). This is a
**set-and-forget allocation**, rebalanced annually — not a signal generator.

---

## 3. Realistic long-run return expectation

- **Market beta (VTI/ITOT/VOO): ~7–9% nominal** long-run historical; the S&P 500 has compounded
  roughly ~10% nominal / ~7% real since 1926, but forward estimates are lower after the last
  bull run — plan on 7–9% nominal, not 10%+.
- **Short Treasury / T-bill (SGOV/VUSXX/direct): ~4–5%** *current* carry — this is a high-tide
  artifact of 2022–2026 rate levels, not a permanent 5%; long-run T-bill is ~0–1% real.
- **Aggregate bond (BND): ~4–5% yield-to-maturity** currently, with duration risk in both
  directions.

**These are NOT trading edges.** They are (a) equity *beta* + (b) fixed-income *carry* — exactly
the baseline that the whole multi-asset audit showed every repo "edge" (`vix_reversal −21.74`,
`penny_deep_oversold −21.35`, `hyperopt_connors_rsi2 −13.87`, `forex_carry_momentum −7.98`) failed
to beat net of costs and selection bias. The honest takeaway of the audit is: **buy the index and
the T-bill; the edges are a multiple-testing artifact** (`research/PROOF_PROTOCOL.md` gates 1–9).

---

## 4. How this fits the repo (minimal code/config)

The correct integration is a **monthly NAV snapshot + benchmark comparison**, NOT a pick emitter.
The existing `tactical_fund_rotation` strategy should be demoted from "research" to a
**benchmark reference sleeve** — it must never emit a trade signal, because end-of-day NAV cannot
produce an intraday edge.

Minimal additive changes (no new deps; yfinance already required):

1. **`multi_asset/portfolio_defs.py`** — add a `BENCHMARK_SLEEVE` dict (not in `STRATEGY_REGISTRY`
   as a tradable):
   ```python
   BENCHMARK_SLEEVE = {
       "equity":  {"symbol": "VTI",  "er": 0.0003, "role": "us_beta",  "weight": 0.70},
       "bond":    {"symbol": "BND",  "er": 0.0003, "role": "ballast",  "weight": 0.15},
       "cash":    {"symbol": "SGOV", "er": 0.0009, "role": "tbill",    "weight": 0.15},
   }
   ```

2. **New `multi_asset/benchmark_snapshot.py`** (or extend `mutual_fund_ranker.py` prototype) —
   once a month, pull close/NAV from yfinance for the 3 sleeves, compute
   ER-adjusted geometric return, and write one row to
   `multi_asset/data/benchmark_sleeve_nav.json`. Fields:
   `date, vti_nav, bnd_nav, sgov_nav, sleeve_nav, ytd_return_pct, vs_spy_pct`.

3. **Comparison, not emission** — a tiny report that plots the sleeve vs SPY (the "beta bar")
   and vs the live closed-feed Σ PnL. This is the *control arm* that quantifies how far every
   signal book lags plain beta + carry. No `live_picks.db` rows, no scanner, no ML-gate class.

4. **Optional dashboards** — add a read-only "Benchmark Sleeve" tile to the audit dashboard that
   renders `benchmark_sleeve_nav.json`; explicitly label it NOT-MONEY-READY / no picks, mirroring
   the existing `benchmark_proof.html` convention.

This keeps the "always-on profitable vehicle" honest: it tracks the one thing the repo can
actually trust — the index + the T-bill — instead of another signal that the audit would
(and did) reject.

---

## TL;DR

- **Best single default:** `VTI` (0.03% ER, $0 min, fractional shares) — least capital in,
  least maintenance, portable; `FZROX` (0.00%, $0) only if locked to Fidelity.
- **3-fund core:** VTI (beta) + BND (ballast) + SGOV/VGSH (T-bill cash floor).
- **Return:** ~7–9% nominal equity beta + ~4–5% current T-bill carry = the true baseline, not an edge.
- **Repo fit:** monthly NAV snapshot + SPY/closed-feed comparison (benchmark), never a pick emitter.
