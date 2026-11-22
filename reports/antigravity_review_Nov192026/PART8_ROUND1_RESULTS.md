# PART 8 — Round 1 Results: detector calibration + all-class battery + lag audit
**Author:** githubcopilot-mercury3AI · **Date:** 2026-11-22 · **Status:** RESULTS (round 1 of Part 8)

> ## ⚠️ CORRECTIONS APPLIED 2026-11-22 — read `PART11_PEER_REVIEW_RESPONSE_AND_CORRECTIONS.md`
> **COMMODITY and FUTURES rows in this document are labelled `DATA_INTEGRITY_FAIL` and WITHDRAWN.**
> Verified in my own cached series: **CL=F carries a negative close (−37.63)** — which makes `pct_change()` meaningless — plus 112 monthly moves >8%; NG=F has 163 such moves. Yahoo `=F` continuous contracts are not roll-adjusted. Any Sharpe/CAGR/MDD for COMMODITY or FUTURES in this document is therefore contaminated and must not be cited. Method: rebuild ratio- or difference-back-adjusted continuous contracts with explicit roll dates first.
> The S&P 500 / ETF / mutual-fund / bond / index / FX / crypto rows are unaffected (cash instruments, no rolling contracts) — **except that all MaxDD figures here are month-end sampled and understate daily drawdown** (SPY: −50.8% month-end vs −55.2% daily).

**Reproducers:** `/tmp/p6/calibrate.py` · `/tmp/p6/engine3.py` · `/tmp/p6/engine4_lag.py` · data `MANIFEST2` sha `fd075cd4…`

---

## 1. The headline, stated before the caveats

A single, boring, **published-in-2007** rule — hold the asset class when its equal-weight index is above its 10-month simple moving average, otherwise hold T-bills — reproduces across **8 of 10 asset classes** under *honest* execution, and cuts maximum drawdown by **~60% in equities** while giving up essentially nothing in CAGR.

| class | BH Sharpe | BH CAGR% | BH MaxDD% | **TREND Sharpe** | **TREND CAGR%** | **TREND MaxDD%** | MDD cut |
|---|---:|---:|---:|---:|---:|---:|---:|
| **EQUITY** | 0.566 | 8.44 | −50.59 | **0.796** | **8.48** | **−20.67** | **59%** |
| **ETF** | 0.632 | 6.59 | −33.54 | **0.887** | **6.75** | **−11.92** | **64%** |
| **INDEX** | 0.596 | 8.04 | −52.33 | **0.741** | **7.69** | **−21.63** | **59%** |
| **MUTUAL_FUND** | 0.714 | 7.72 | −39.91 | **0.983** | **7.49** | **−12.82** | **68%** |
| BOND | 0.572 | 3.48 | −20.03 | 0.700 | 3.10 | −12.04 | 40% |
| COMMODITY | 0.581 | 9.02 | −46.72 | 0.681 | 8.96 | −33.66 | 28% |
| FUTURES | 0.751 | 7.30 | −14.38 | 0.689 | 5.11 | −10.44 | 27% |
| FOREX | 0.070 | 0.20 | −17.42 | 0.239 | 0.61 | −10.24 | 41% |
| PENNY_STOCK¹ | 0.441 | 11.78 | −79.50 | 0.637 | 22.38 | −38.37 | 52% |
| CRYPTO | 0.692 | 37.45 | −78.92 | 0.286 | 2.18 | −63.36 | 20% |

Signals from month-end close, **executed at the next trading day's close**; yfinance adjusted close (dividends in); 20bp per unit turnover. ¹ PENNY_STOCK is survivorship-biased upward and its real OTC spreads are 5–20× the cost modelled — see §5.

**What this is:** drawdown control with no return cost in equities/ETFs. **What this is not:** alpha. CAGR is not higher than buy-and-hold in 6 of 10 classes, and in FUTURES/CRYPTO it is materially lower. This is the same shape as the peer's TAA retraction — *"risk control, not alpha"* — but here the effect survives the timing test that killed the earlier claim.

---

## 2. P8.0 — Detecting whether our own detector works

Before trusting any kill, I calibrated the gate (`tools/edge_stability_harness.py`: `eff ≥ 0.30`, same sign, ≥3 scored windows, n≥80/window) against **planted** edges.

| true eff | n=80/window, 3 win | n=200, 3 win | n=500, 3 win | n=80, 6 win |
|---|---:|---:|---:|---:|
| **0.00** (no edge) | **0.000** | 0.000 | 0.000 | 0.000 |
| 0.13 | 0.018 | 0.000 | 0.000 | 0.135 |
| 0.21 | 0.040 | 0.015 | 0.007 | 0.318 |
| **0.26** | **0.100** | **0.055** | **0.033** | 0.525 |
| 0.34 | 0.190 | 0.240 | 0.273 | 0.750 |
| 0.44 | 0.372 | 0.568 | 0.765 | 0.932 |
| 0.66 | 0.838 | 0.980 | 1.000 | 1.000 |

**Findings, all measured, 400 draws per cell:**
1. **False-positive rate is 0.0%** at true eff = 0 — the gate does not hallucinate edges. That is genuinely good and should be kept.
2. **True-positive rate is terrible near its own threshold.** A real edge at eff=0.26 is detected **10%** of the time at the gate's own minimum sample size. An edge at eff=0.21: **4%**.
3. **Detection gets worse with more data per window** (0.100 → 0.055 → 0.033 for eff=0.26), because with more data `eff` is estimated more precisely *below* the 0.30 bar. The gate is effectively a low-power test of "is true eff ≥ 0.30".
4. **Arithmetic check:** MDE at n=80/arm (α=0.05, power=0.80) = **0.443 > 0.30**. The gate demands an effect 1.5× smaller than its own sample size can resolve.

⇒ **"11 killed / 0 admissible" is not evidence that the 11 effects are absent.** It is evidence that this gate cannot distinguish a 0.26 effect from zero. Any verdict that rested *only* on `eff<0.30` must be re-adjudicated with a correctly powered test (Part 7 §B3: pooled cluster-robust estimation, not per-window sign counting). This is a **process defect in our own kill pipeline**, not a market fact.

**Effect injection (pipeline sanity):** superimposing a known monthly drift on real SPY bars, the engine recovers it **exactly** — `recovered − injected` is constant at 0.9170%/mo (= SPY's baseline mean) for injections of 0, 0.5, 1, 2, 4 %/mo. No sign error, no magnitude error, no cost leakage. The pipeline can see what it claims to see.

---

## 3. The lag audit — a peer found a real defect in my code, and it did not change the conclusion

A delegated reviewer raised the sharpest possible objection: *"signal computed from the close of month t−1 and traded at that same close is same-close (lag-0) execution — the exact defect that retracted the TAA Sharpe 0.88 claim."*

**It was right about my first implementation.** `engine3.py` set `w[t]` from data through the t−1 close and earned `r[t]` (t−1 close → t close) — i.e. traded at the very close it used. I re-ran everything under three conventions:

| class | L0 same-close (not implementable) | L1 +1 extra month (conservative) | **L1d: next-day close (honest)** | L1d − L0 |
|---|---:|---:|---:|---:|
| EQUITY | 0.809 | 0.665 | **0.796** | −0.013 |
| ETF | 0.800 | 0.846 | **0.887** | +0.087 |
| INDEX | 0.684 | 0.623 | **0.741** | +0.057 |
| MUTUAL_FUND | 0.938 | 0.846 | **0.983** | +0.045 |
| BOND | 0.554 | 0.406 | **0.700** | +0.146 |
| COMMODITY | 0.759 | 0.661 | **0.681** | −0.078 |
| FUTURES | 0.828 | 0.601 | **0.689** | −0.139 |
| FOREX | 0.134 | −0.154 | **0.239** | +0.105 |
| PENNY_STOCK | 0.512 | 0.554 | **0.637** | +0.125 |
| CRYPTO | 0.140 | 0.199 | **0.286** | +0.146 |

(Sharpe, 20bp; signals at month-end close, L1d executed at the next trading day's close.)

**Result: the effect is not look-ahead.** Under the *most* honest of the three conventions, 7 of 10 classes are equal or better than the same-close version and the worst decay is −0.139 (FUTURES). This is the **opposite** of the TAA case, where the claim reproduced *only* at lag-0 and died under a 1-day lag. The L1 (+1 month) column shows the genuine risk: it is a *timing-sensitive* effect, and a slow implementation loses up to 0.23 Sharpe (FUTURES 0.828→0.601).

**I adopt the criticism and keep the result, with the correction recorded.** The number published is L1d, not L0.

---

## 4. What died, and what that tells us

- **Cross-sectional momentum long/short was catastrophic nearly everywhere** — FUTURES −17.99% CAGR, PENNY_STOCK −94.26%, CRYPTO −70.59%, COMMODITY −14.22%. On 4–17 name universes with monthly rebalancing, XS momentum has no breadth and no room to pay 20bp of turnover. **Do not build on it at this universe size.**
- **1-month cross-sectional reversal** was also negative in most classes, mildly positive only in PENNY_STOCK (10.49% CAGR, −95.6% MaxDD — uninvestable).
- **CRYPTO trend fails:** TREND Sharpe 0.286 vs BH 0.692 with 37.45% CAGR. Crypto's trend filter destroys return. Buy-and-hold beat every overlay.
- **FOREX has essentially nothing** (BH Sharpe 0.070; best construction 0.239). Consistent with the repo's H-006/H-008 kills.

---

## 5. Contamination disclosures (mandatory)

| issue | effect on §1 table |
|---|---|
| **PENNY_STOCK survivorship** | Universe = names still listed today ⇒ biased **upward**. The 20bp turnover cost is also far below real OTC spreads (100–500bp). Treat the 22.38% CAGR as an upper bound on a biased sample, not a result. |
| **INDEX / MUTUAL_FUND survivorship** | Indices are survivors by construction; the fund list (VWELX, DODGX, SEQUX, PRWCX) are *notable survivors* — a random 1980 fund list would look worse. Fund returns are net of fees (correct), but the *choice* of funds is ex-post. |
| **FUTURES continuous contracts** | Yahoo's `=F` series are front-month stitched; roll gaps are in the price series but **roll yield is not modelled explicitly**, so the futures numbers are not a tradeable P&L. |
| **Monthly sampling** | 234–467 monthly observations, overlapping 10-month windows ⇒ effective independent N is far smaller than n. PSR/DSR computed on monthly returns partially, not fully, corrects this. |
| **Multiplicity** | 5 constructions × 10 classes = 50 trials. DSR used K=5–6 *within* class; the cross-class selection (picking the best class) is **not** deflated. Treat the best class as a hypothesis. |
| **Publication decay** | The 10-month SMA rule is Meb Faber's (2007) and is in every retail playbook. Per McLean-Pontiff (~58% decay) expect *some* forward erosion — though risk-management rules decay less than mispricing rules, because their mechanism is behavioural/volatility, not arbitrage. |

---

## 6. Verdict per class (round 1)

| class | tier | why |
|---|---|---|
| **EQUITY** | **CANDIDATE (risk-control)** | 0.796 vs 0.566 Sharpe, identical CAGR, 59% MDD cut, honest timing, cost-robust to 40bp. Not alpha. |
| **ETF** | **CANDIDATE (risk-control)** | 0.887 vs 0.632, CAGR +0.16, 64% MDD cut. Strongest of the ten. |
| **MUTUAL_FUND** | **CANDIDATE (risk-control)** | 0.983 vs 0.714, 68% MDD cut — the overlay applied to *funds* works too. |
| **INDEX** | **CANDIDATE (risk-control)** | 0.741 vs 0.596 on 8 global indices, 1988–2026. |
| BOND | WEAK | 0.700 vs 0.572 but CAGR −0.38; duration beta dominates. |
| COMMODITY | WEAK | 0.681 vs 0.581, MDD cut only 28%; roll yield not modelled. |
| FUTURES | INSUFFICIENT_N | 112 months only; decay under L1 is largest of all classes. |
| FOREX | REJECTED | 0.239 best; nothing here. |
| PENNY_STOCK | INSUFFICIENT (biased) | survivorship + spread arithmetic unresolved. |
| CRYPTO | REJECTED | trend destroys return; buy-and-hold wins. |

**No class reaches `PROVEN_T2`.** That requires ≥100 forward observations, which do not exist yet. Nothing in this document is a recommendation to trade.

---

## 7. Next (round 2)

1. **PBO / CSCV** on the trend family (`tools/pbo.py`) — is the best class a grid artifact?
2. **Regime split**: does the MDD cut concentrate in 2008/2020/2022 (i.e. is it just three events)?
3. **Whipsaw accounting**: switches per decade, months in cash, and the cost of being wrong at the turn.
4. **Delisted-inclusive equity universe** — the single largest remaining bias.
5. **Correctly-powered re-adjudication** of the sign-split kills (H-008, H-010, H-006, H-020) with pooled cluster-robust estimation.
6. **Forward harness** accruing daily so the 100-observation clock starts now, not later.

---
*Not personalized investment advice.*
