# Per-class data-bias register

**Date:** 2026-11-22 · **Owner:** buffy · **Item:** C21
**Purpose:** one table naming, for every asset class, the data defect that could reverse a
verdict — and whether the direction of the bias flatters or penalises the strategies tested.

The rule this register exists to enforce: **a broken series cannot refute a strategy**, and a
flattering one cannot confirm it. Each row states the defect, its measured evidence, and which
way it pushes.

| Class | Defect | Evidence | Bias direction | Standing |
|---|---|---|---|---|
| **EQUITY** | Survivorship / point-in-time | 79-symbol panel: **0 series end before panel end, 0 start after** — the signature of a current-constituent universe. The measured gap is **0.0 pp/yr by construction**, a zero lower bound, not a measurement. | **Upward** (panel flattered), magnitude `UNMEASURED` | KILLs are conservative. Any survivor is `UNSAFE` |
| **EQUITY** | Thin cell counts | `H-200:NVDA` has **n=13 trades** → `INSUFFICIENT_N`; a CI on 13 trades is not a CI | Both | Excluded from any "best cell" election |
| **ETF** | Dividend adjustment method | `SHY` gained **+10.4% over 5y** while short rates rose ~4% — only possible with coupons reinvested, so `Close` behaves adjusted; the **method is unmeasured** | Unknown, likely small | Absolute CAGRs carry the caveat; relative/null comparisons do not |
| **COMMODITY** | Roll artefacts | `CL=F` has a **negative close (−37.63, 2020-04-20)** making `pct_change` meaningless; `ZC=F` prints **~−23.6% on 07-15 in three separate years**; `NG=F` has recurring same-month-day spikes across six years | **Upward** (gaps inflate momentum) | Closed **NO CANDIDATE** by two independent witnesses on two constructions; `DATA_INTEGRITY_FAIL` stands |
| **COMMODITY / FUTURES** | No second contract | Only one continuous front-month series on disk; roll yield `(front − second)/second` needs two | n/a | Term-structure carry is `BLOCKED_DATA`. Synthesising a second month is forbidden — it invents the signal |
| **FOREX** | No central volume; weekend spreads | 10 FX pairs carry zero-volume rows (shape artefact, not delisting). Cost probe ran on a **Sunday** — markets closed, spread `UNMEASURED` | Cost understated | FX verdicts are conditional on an assumed round trip. FX carry survives it (break-even 468.5 bp ≫ any plausible cost) |
| **FOREX** | Rate publication lag | Carry uses **30-day-lagged** policy rates | Conservative (correct) | No look-ahead in the carry signal |
| **BOND** | Dividend method + one regime | Same adjusted-`Close` issue as ETF. Window contains **one** sustained rising-rate episode (DGS10 3.30% → 5.31% → 5.04%) | One regime cannot distinguish robust from lucky | Verdict `UNKNOWN` (data), not `KILL` |
| **CRYPTO** | Cost measured on one snapshot | Spot taker **10 bp/side** (Binance/BinanceUS/KuCoin), 26 bp Kraken, depth walked $1k–$1M on **one Sunday**; **perp spread assumed equal to spot** | Perp leg understated | Best-measured class, still conditional on the perp assumption |
| **CRYPTO** | Survivorship in funding history | 6.2–7.2 years of real 8h funding exists only for **coins that still trade** | **Upward** | Funding carry flagged **UNSAFE** — a marginal survivor is exactly what this flips |
| **PENNY_STOCK** | Flat cost constant | **30 bp** round trip charged; measured slippage absent, and ADV-driven haircut not applied | Cost understated for illiquid names | Any penny verdict is conditional |
| **MEME** | Flat cost constant | Same 30 bp constant, no measured slippage | Cost understated | Conditional |
| **MUTUAL_FUND** | Cost never populated | `0.08` configured and never written; NAV execution lag unverified | Unknown | No unconditional verdict possible |
| **INDEX** | Taxonomy leak | INDEX is an ETF alias that leaks rows out of the denominator; **no cost model exists** | Denominator distortion | Excluded from class counts pending a fix |
| **SPORTS** | Out of scope | No cost model, no measured data | n/a | No verdict |

## What this register changes

**11 of 12 classes have an `UNMEASURED` transaction cost.** Only CRYPTO has a measured number,
and even there the perp leg's spread is assumed. So every non-crypto verdict in this programme is
**conditional on an assumption**, and the ones that survive are the ones whose break-even cost is
so far from plausible cost that the assumption cannot matter: FX carry (468.5 bp), equity breakout
(killed on the random null and negative selection alpha, not cost), 12-1 momentum and the N1 rules
(null-percentile kills), crypto intraday mean-reversion (break-even **0 bp**).

**One rule for reading any future result from this repo:** a KILL measured on flattered data is
conservative and can be banked. A positive or marginal result measured on the same data is
`UNSAFE` until a point-in-time universe exists — and no point-in-time universe exists here, which
is why the register's most important entry is the first one.
