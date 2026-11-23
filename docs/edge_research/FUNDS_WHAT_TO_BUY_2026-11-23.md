# What a human should actually buy — index funds / ETFs (CORRECTED per subq review)

**Date:** 2026-11-23T10:27Z · **Author:** Kilo. **Buying analysis (beta), not an edge claim.**
Real data 2021-11-15→2026-11-13 (1,254 daily returns). Tool: `tools/fund_deep_dive.py` (runs end-to-end, verified).
**Not investment advice. Bull-heavy 5-yr window; taxes unmodelled.**

## Corrections applied (subq review)
- **Sharpe/Sortino are now EXCESS OF CASH** (SGOV daily). The old 0.71/0.73 figures were return/vol, mislabelled — true
  excess Sharpe is ~**0.50**. SGOV is relabelled **n/a** (it *is* cash; its ratio is undefined).
- **CAGR now carries a block-bootstrap 95% CI** (21-day blocks, 2,000 draws).
- **Portfolios use true monthly rebalancing** (daily over-stated 60/40 by 0.13 pp/yr).
- **FXAIX-vs-SPY arithmetic restated honestly** (below) and **CIs added** — the gap is inside the noise.
- **Sample split** into first ~3y / last ~2y.
- Futures **out of scope** (needs front-month/roll/yield data, not adjusted closes).
- Tax drag and minimums stated; BND judged by trailing only (forward YTM is the right forward input — not available here).

## Measured (excess-of-cash Sharpe)
| instrument | MER | net CAGR | **CAGR 95% CI** | vol | **Sharpe(rf)** | Sortino(rf) | max DD |
|---|---:|---:|---|---:|---:|---:|---:|
| Fidelity 500 Index (FXAIX) MF | 0.015% | 11.66% | **[0.1, 25.4]** | 17.2% | **0.506** | 0.501 | −24.5% |
| SPDR S&P 500 (SPY) ETF | 0.0945% | 11.49% | [−0.0, 25.2] | 17.3% | 0.498 | 0.714 | −24.5% |
| Fidelity ZERO Total Mkt (FZROX) MF | 0.00% | 10.74% | [−0.8, 25.0] | 17.6% | 0.450 | 0.641 | −25.1% |
| Vanguard Total Mkt (VTI) ETF | 0.03% | 10.50% | [−1.0, 24.8] | 17.7% | 0.438 | 0.625 | −25.4% |
| Vanguard Total Stock (VTSAX) MF | 0.04% | 10.48% | [−1.0, 24.8] | 17.6% | 0.439 | 0.624 | −25.4% |
| Vanguard Total Bond (BND) ETF | 0.03% | −0.32% | [−4.6, 4.3] | 6.1% | −0.648 | −0.889 | −17.3% |
| iShares 0-3mo T-bill (SGOV) ETF | 0.09% | 3.81% | [3.6, 4.3] | 0.2% | n/a (cash) | n/a | −0.03% |

**Read the CIs first: every equity fund's 5-yr CAGR CI spans roughly 0→25%.** They **overlap enormously**, so **no fund
ranking here is statistically distinguishable** — including FXAIX vs SPY. The fee ordering is *directional*, not proven.

## Portfolios — true monthly rebalance (net)
| portfolio | net CAGR | max DD | Sharpe(rf) | daily-rebal (over-stated) |
|---|---:|---:|---:|---:|
| 100% SPY | 11.49% | −24.5% | 0.498 | same |
| 80/20 SPY/BND | 9.18% | −22.5% | — | 9.28% (+0.10 pp) |
| **60/40 SPY/BND** | **6.85%** | **−20.7%** | — | 6.98% (+0.13 pp) |

## FXAIX vs SPY — honest arithmetic
Same index (identical −24.5% MaxDD). FXAIX net CAGR **+0.17 pp/yr** higher. Its **MER is 0.0795 pp/yr lower** (0.015% vs
0.0945%). So the **sign is consistent with fees**, but the observed magnitude (~0.17) **exceeds** the fee gap (~0.08) —
the extra ~0.09 pp is tracking/dividend-timing noise — and, with CIs this wide, the difference is **not distinguishable
from zero**. **Correct claim: "FXAIX is structurally cheaper on the same index; the observed out-performance is within
noise."** Split sample: FXAIX beat SPY in **both** halves (+0.18 pp first-3y, +0.14 pp last-2y) — consistent, but still
inside CI.

## Decision table (what a retail reader needs)
| fund | vehicle | MER | min | tax (taxable acct) | best fit |
|---|---|---:|---|---|---|
| FXAIX | index MF | 0.015% | $0 (Fidelity) | cap-gains distributions possible | **growth, tax-sheltered** |
| FZROX | index MF | 0.00% | $0 (Fidelity) | same | **growth, tax-sheltered** |
| SPY/VOO | ETF | 0.0945%/0.03% | 1 share* | most tax-efficient | growth, **taxable** |
| VTI | ETF | 0.03% | 1 share* | most tax-efficient | growth, taxable |
| VTSAX | index MF | 0.04% | $3,000 | cap-gains possible | growth, sheltered |
| BND | ETF | 0.03% | 1 share* | efficient | bonds |
| SGOV | ETF | 0.09% | 1 share* | efficient | cash |
\*fractional shares common at major brokers.

## Bottom line
1. **Core:** a broad low-cost index fund — same beta as the programme's signals, cheaper. **FXAIX (0.015%)/FZROX (0.00%)** in
   a tax-sheltered account; **SPY/VOO/VTI ETF** in a taxable account (tax efficiency).
2. **No fund is provably better than another on this 5-yr sample** — the CIs overlap. Choose on **cost and tax**, which are
   deterministic, not on trailing 5-yr returns.
3. **Risk:** 100% equity had a **−24.5% drawdown**. If you can't hold through it, **60/40** (6.85%/yr, −20.7% DD).
4. **Forward anchors (not trailing CAGR):** cash ≈ **3.8%** (SGOV), bonds = current **YTM** (not last 5 yrs), equity =
   earnings yield — trailing CAGR is a bad forecast input.
5. **Out of scope:** futures (needs contract/roll data); options; individual stocks.

*Paper only. Not investment advice.*

---

## F4 RETRACTION acknowledged — "a mutual fund beats its own ETF" is withdrawn
The programme retired claim F4 ("a low-cost index mutual fund can beat its own ETF") after an adversarial review pointed
out that **two agreeing implementations can share the same error**, and that the decisive test is to compare the
fund-vs-ETF gap against the **spread across several ETFs tracking the same index** (SPY/VOO/IVV). I accept the retraction.

**What I now assert (and only this):**
1. **Fee drag is real and deterministic.** Same index ⇒ lower MER strictly lowers cost. FXAIX 0.015% vs SPY 0.0945% =
   **7.95 bp/yr** structural fee advantage; VOO/IVV at 0.03% sit near FXAIX. **Buy the cheapest same-index vehicle.**
2. **The *out-performance magnitude* is not proven.** My corrected numbers already show overlapping bootstrap CIs
   (FXAIX [0.1,25.4] vs SPY [−0.0,25.2]); the observed +0.17 pp/yr (~17bp) EXCEEDS the 7.95bp/yr fee gap (fee UNDER-predicts; excess unattributed, within noise).
   **Do not claim the fund "beat" the ETF; claim it is structurally cheaper.**
3. **Their ETF-spread test is the right one and I could not run it** — my data has only SPY, no VOO/IVV. So I state the
   **fee ordering** (a cost fact), not a measured vehicle edge. If VOO/IVV series are supplied, run the spread test before
   any "beats" language returns.

**Net effect on the recommendation:** unchanged. Choose on **cost and tax** (deterministic), not on trailing returns
(indistinguishable). This is now stated without the over-strong "mutual fund beats ETF" framing.


---
## CORRECTION 2026-11-23T10:41Z — Sortino convention fixed (peer-reviewed)
My Sortino divided downside deviation by the COUNT OF NEGATIVE DAYS; the standard (Sortino–Price) divides by **N (all
periods)**. My version **understated Sortino by ~30%**. Corrected values (excess-of-cash): FXAIX **0.722** (was 0.501),
SPY 0.714, FZROX 0.641, VTSAX 0.624, VTI 0.625, BND −0.889. Sharpe was unaffected. Also clarified: the fee gap
(7.95bp/yr) **under-predicts** the observed ~17bp/yr gap (the excess is unattributed tracking noise, still within CIs).

---

## CORRECTION 2026-11-23T21:36Z — the value "+0.11%→+2.89%" is UNCONFIRMED (yfinance default is adjusted)
On verifying the toolchain, **yfinance 1.3.0's `history()["Close"]` is already adjusted** (auto_adjust None→True). The
value pipeline's price fetch used `history(period="5d")` **with the default**, so its prices were **already total-return** —
**not** price-only. Therefore my claim that the +0.11% value result is a price-only artifact that "corrects to +2.89%" is
**not established**: it only holds if the value *backtest* used raw prices, which I have not confirmed.

**What stands:** the *measured dividend drag* on a genuinely raw feed is real — **~2.78%/yr** for a value universe (VTV 2.78,
DVY 3.78, VBR 2.23, SPY 1.94). That is the cost **if** a pipeline uses raw Close.
**What is retracted:** the specific "+0.11% → +2.89%" correction, pending proof of which price source the value test used.
The genuine raw-price exposure in the repo is **62 files** that explicitly use `auto_adjust=False` or raw Stooq/chart-API
Close (see `updates/2026-11-23-repo-total-return-audit.md`), not the value pipeline's default path.
