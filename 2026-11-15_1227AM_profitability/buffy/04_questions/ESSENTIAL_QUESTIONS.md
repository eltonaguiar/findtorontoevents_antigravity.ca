# 04 — Essential Questions Before Any Algorithm Can Be Called Profitable

**Date:** 2026-11-15 · **Author:** Buffy

Fifteen questions. Each one is a **gate**, not a discussion point: if it cannot be answered with an
artefact, the strategy is not profitable — it is untested. The repo can answer 4 of 15 today.

---

## A. Mechanism — why does the money exist?

**Q1. Who is on the other side, and why do they lose?**
Not "the trend was up." Name the counterparty and their constraint: forced seller, index rebalancer,
hedger transferring risk, retail lottery-ticket buyer, market maker earning spread.
*Why it matters:* an edge with no identifiable payer is a pattern fitted to noise.
*Repo state:* documented for COT (hedger/commercial flow), weak for most of the 361.

**Q2. What is the null hypothesis you are beating — exactly?**
Buy-and-hold the same asset? T-bills? A factor-matched portfolio? Random entry with the same holding
period and same TP/SL? Without a stated null, PF 1.15 is meaningless.
*Repo state:* the EQUITY test names SPY. Most others name nothing.

**Q3. Is the edge economic, not just statistical?**
Funding carry must beat the cash floor (measured 3.7–4.8% vs 4.5% T-bill — i.e. **roughly zero**).
A 2 bps edge against 15 bps cost is not an edge.
*Repo state:* `per_class_cost_gate.py` exists but fails **open**.

---

## B. Measurement — is the number real?

**Q4. What fraction of your closed rows carry a verified mark?**
Measured: **48.1% forged**. A statistic computed over the other 51% is a statistic about your resolver.
*Gate:* ≥95% verified before any PF is quoted.

**Q5. Has the outcome been intrabar-replayed?**
A daily-close `TP_HIT` may have hit SL first. The repo's own replay moved CRYPTO 52.3%→42.9% WR and
reclassified **26.4% of TP_HIT to SL_HIT**.
*Gate:* intrabar validation mandatory; assume the lower number until proven.

**Q6. What is the effective N after correlation?**
22,077 CRYPTO rows are not 22,077 independent observations — they are clustered by symbol, hour, and
regime. Effective N is typically 5–20× smaller.
*Gate:* report effective N alongside raw n.

**Q7. How many trials produced this result, and what is the deflated threshold?**
**361 registered strategies.** At α=0.05 that is ~18 false positives expected. DSR must use N=361, not
N=38.
*Gate:* DSR ≥0.95 at the true trial count, published.

---

## C. Robustness — will it survive contact?

**Q8. Does the edge survive a 2-day execution lag?**
If your signal needs same-bar fills, it is a latency claim, not an edge. The plan already lists
"2-day-lag Sharpe ≥ 1.0" — keep it, and apply it to every class.

**Q9. Is the signal monotonic in its input (dose-response)?**
Sharper RSI oversold → larger bounce? If the relationship flips at ±5% parameter perturbation, it is a
knife-edge. The repo's 5-pillar framework calls this the Parameter Stability test (>50% WR drop = FAIL).

**Q10. Which regimes does it work in, and what share of history is that regime?**
A rule that only works in low-vol bull markets is a **long-beta rule** with extra steps. Report
per-regime WR/PF and the historical frequency of each regime.
*Repo state:* `regime_router.py` exists; regime attribution is not published per strategy.

**Q11. What is the decay half-life?**
How quickly does the edge shrink after discovery? COT PF 21.33 → 1.09 recent is a decay observation,
not a stable edge.

**Q12. What is the pre-registered falsifier?**
State in advance: "this is dead if PF < X at n ≥ Y on out-of-sample data after date Z." Written before
the test, not after. Rule M-107 exists for this; it is applied to a minority of hypotheses.

---

## D. Execution — can you actually get it?

**Q13. What is the break-even slippage, and what is your realistic slippage?**
Pillar 3 sets the bar: **break-even <5 bps = FAIL.** Retail round-trip is 2–30 bps depending on class.
This one test disqualifies scalping and most day trading outright.

**Q14. What is the capacity limit?**
At what AUM does your own order flow erase the edge? A CT=F concentration artefact is not scalable even
if it were real.

**Q15. At the intended position size, what is the Monte-Carlo risk of ruin?**
Measured on this ledger: **44.4% over 200 trades**, Kelly fraction **−0.0538** (negative → size zero),
compounded max drawdown **−100%**. A strategy that is "profitable" and also ruins you is not profitable.

---

## E. Scoreboard

| # | Question | Repo can answer? | Artefact |
|---|---|---|---|
| 1 | Counterparty / payer | Partial | COT docs only |
| 2 | Named null / benchmark | Partial | EQUITY vs SPY only |
| 3 | Economic vs statistical | ❌ | cost gate fails open |
| 4 | Verified-mark coverage | ✅ | `asset_class_measurability.json` (48.1% forged) |
| 5 | Intrabar replayed | Partial | `reresolve_intrabar.py`, not applied to cohort |
| 6 | Effective N | ❌ | — |
| 7 | Trial count / DSR | ❌ | 361 known, DSR absent |
| 8 | 2-day lag | ❌ | threshold defined, not run |
| 9 | Dose-response | ❌ | 5-pillar exists, not reported |
| 10 | Regime attribution | Partial | router exists, no per-strategy table |
| 11 | Decay half-life | ❌ | — |
| 12 | Pre-registered falsifier | Partial | M-107 exists, low coverage |
| 13 | Break-even slippage | ❌ | Pillar 3 defined, not computed |
| 14 | Capacity | ❌ | — |
| 15 | Ruin probability | ✅ | 44.4% / Kelly −0.054 |

**4 of 15 answered.** That is the honest explanation for "why can't we find profitability": not a lack
of ideas (361 strategies), but four unanswerable questions standing between the data and a decision.

## The one question that dominates

If you can only fix one: **Q4 — verified-mark coverage.** Every other question consumes marks. At 48%
forged, the other fourteen answers are being computed on a ledger that is half fiction.
