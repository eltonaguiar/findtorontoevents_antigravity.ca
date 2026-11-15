# 01 — Per-Asset-Class Plan to Reach Profitability

**Date:** 2026-11-15 · **Author:** Buffy · **Basis:** measured ledger (2026-11-14T22:34Z) + repo corpus

Every class gets the same four answers: **what would the money actually be** (mechanism), **where it
stands today** (measured), **the smallest honest test**, and **the kill criterion**. A class with no
identified mechanism does not get a test — it gets retired.

The sequencing rule: **no class advances past step 2 until L0 (ledger truth) passes.** A backtest on
an unmarked ledger measures the resolver, not the market.

---

## 0. Universal preconditions (apply to all classes)

| Gate | Threshold | Current |
|---|---|---|
| Verified marks | ≥95% of closed rows | 51.9% (3,618 / 6,968) |
| Intrabar re-resolution | applied, not just daily close | not applied to the verified cohort |
| Cost model | per-class bps, subtracted before ranking | exists (`per_class_cost_gate.py`), fail-open |
| Pre-registration | hypothesis in registry before backtest (M-107) | partial |
| Deflated Sharpe | reported with raw Sharpe | absent |
| Promotion gates | fail **closed** | `MONEY_READY_FDR_GATE`, `MONEY_READY_SINGLE_SOURCE_GATE` default OFF |

---

## 1. EQUITY — first slot, only class with a positive cost margin

**Mechanism.** Short-horizon mean reversion after multi-day declines (RSI-2 / Connors family): forced
sellers (fund redemptions, stop cascades, tax-loss windows) transact on a schedule unrelated to
value. The buyer of that flow earns the liquidity concession. This is a documented, capacity-limited
premium — not a pattern.

**Measured.** 835 closed · 97 forged (12%) · **738 verified** · WR 47% · PF 1.15 · Sharpe/trade 0.054.
Best data situation of any class after ETF: contamination is low enough that the number is probably
real, and it is *sub-threshold* (needs PF ≥1.15 after costs — currently 1.15 before costs).

**Smallest honest test.** `stocks_rsi2_pullback` against SPY total return, 24 months, pre-registered:
- n ≥ 500 verified closures, ≥3 distinct months at n≥30
- intrabar-replayed; EXPIRED counted as non-win
- PF ≥ 1.15 **after** 8 bps round-trip, WR ≥ 52%, OOS halves both positive
- DSR ≥ 0.95 given 361 trials; 2-day-lag Sharpe ≥ 1.0 (execution delay)

**Kill criterion.** Fails PF/WR after costs on either half → retire the family. Do not re-tune: this
strategy was already killed once at n=10 and resurrected at n=78 by better data, not by fitting.

**Effort:** 2–3 days of measurement work; the strategy already exists and emits.

---

## 2. ETF — the measurement anchor, not the alpha candidate

**Mechanism (allocation).** Equity risk premium + low fees. 90.2% of SPY's rolling 10-year windows were
positive over 407 months; CAGR 8.71%, vol 14.74%, maxDD −52.2%. This is **beta** and needs no strategy.

**Mechanism (tactical, unproven here).** Trend persistence / 200-day MA (Faber): cross-asset time-series
momentum has documented OOS support in the literature, and it is the one ETF idea worth pre-registering.

**Measured.** 575 closed · 9 forged (**2%**) · **566 verified** · WR 44% · PF 1.04 · Sharpe/trade 0.014.
**This is the cleanest ledger in the system and it shows a coin flip.** Because the data is trustworthy
here, this negative is the most reliable finding in the entire audit.

**Smallest honest test.** `etf_200dma_trend` pre-registered: monthly bars, 2010–2026, SPY/QQQ/IWM/TLT/GLD,
2× ATR stop, costs 3 bps, vs SPY buy-and-hold benchmark. Target PF >1.3 at n≥150 verified. Also fix
`etf_rsi2_pullback`, which closed 33 picks at exactly 0.0% and therefore **has never been tested**.

**Kill criterion.** Trend rule fails to beat buy-and-hold after costs → keep ETFs as pure beta, stop
emitting ETF picks entirely.

**Note.** The 2026-05-31 peer audit found ETF closure rate 0.13/day → time-to-n=100 was ~770 days. That
bottleneck was the resolver, not the strategy; fixing L0 changes this class more than any other.

---

## 3. CRYPTO — highest volume, worst signal-to-noise, conditional only

**Mechanism (plausible).** Perp funding-rate extremes and liquidation cascades create short-horizon
mean reversion; on-chain flows can front-run exchange inflows. Real but crowded, and dominated by
market makers with better latency.

**Measured.** 5,135 closed · 3,021 forged (**59%**) · **2,114 verified** · WR 40% · PF 1.02 ·
Sharpe/trade 0.005. One emitter is 48.2% of the ledger (HHI 0.385). Verified PF ~1.02 = break-even
before 15–30 bps costs.

**Smallest honest test.** Not before the fill fix. `kimi_riseoftheclaw` stop-fill defect accounts for
98.8% of class loss; the Nov-14 review's own estimate is that fixing it moves PF to **≈1.00**, i.e. to
break-even, not to profit. Then: POSITION horizon, n≥100, PF≥1.3, WR≥55%, after costs.

**Kill criterion.** Post-fix PF <1.15 at n≥300 verified → retire the class rather than keep mining it.
The 2026-06-09 skill addendum already found the intrabar replay drops CRYPTO 52.3%→42.9% WR, PF 1.22,
with 26.4% of TP_HIT reclassified to SL_HIT. Assume the lower number until proven otherwise.

**Effort:** high. This is the class where the repo has spent the most and measured the least.

---

## 4. FOREX — good per-trade Sharpe, fatal cost structure

**Mechanism.** Carry (rate differentials) and central-bank-driven trend. Both real; both already
arbitraged at retail size.

**Measured.** 355 closed · 197 forged (**56%**) · **158 verified** · WR 46% · PF 1.16 ·
**Sharpe/trade 0.061 — the best per-trade figure in the system.** But only 158 verified marks, and FX
round-trip is 10–20 bps against an edge measured in single-digit bps.

**Smallest honest test.** `cta_cross_asset_tsmom` (all-time n=189, WR 53.4%, PF 3.57 in the raw DB) after
quarantining the six known-bad `TP_HIT` rows (CADJPY exit 611.23 vs entry 115.77; USDJPY exit 1.358 from
entry 158.58). Re-stated PF is estimated 2.0–2.5, still unverified.

**Kill criterion.** After the outlier scrub, if PF <1.3 net of 15 bps → **retire FOREX**. The repo's own
2026-05-13 plan already had FOREX "BLOCKED" and the Nov-14 plan calls it structural. Two independent
audits agree; stop spending here.

---

## 5. BOND — negative and thin; benchmark only

**Measured.** 35 closed · 0 forged · 35 verified · WR 37% · PF 0.59 · Sharpe/trade **−0.248**.

**Mechanism.** Carry + duration timing on the curve. Needs FRED (blocked on `FRED_API_KEY`).

**Verdict.** Not a research priority. Use duration as a **hedge sleeve** (TLT/SHY) sized by risk rules,
not as a pick class. Revisit only at n≥100 verified with FRED wired.

---

## 6. COMMODITY — cannot be judged (n=7)

**Measured.** 23 closed · 16 forged (70%) · **7 verified** · PF 0.60. The historical "PF 3.94 / 1.78"
figures came from `multi_asset_cot` with PF 21.33 on n=144, which is a one-symbol concentration artefact
(CT=F cotton), and 230/354 rows were COT duplicates.

**Verdict.** Unmeasurable. No test until n≥50 post-dedup. Do not quote the old PF.

---

## 7. FUTURES — zero verified marks; plumbing-blocked

**Measured.** 10 closed · 10 forged (**100%**) · **0 verified**.

**Verdict.** Nothing to rank. The class is 91.8% e-mini index futures, which is equity beta wearing a
different label. If revived, start with a genuinely futures-native edge (VIX term structure / roll
yield), not more e-mini mean reversion.

---

## 8. MEMECOIN / PENNY_STOCK / SPORTS / INDEX_STOCK / PREDICTION — retire or label

| Class | Measured | Action |
|---|---|---|
| MEMECOIN | n=10, WR 10%, PF 0.023; 29 strategies quarantined | **RETIRE** — label DORMANT on dashboard |
| PENNY_STOCK | n=4, WR 50%, PF 0.178; 7 of 8 lifetime picks were >$5 mid-caps mistagged | **RETIRE** + add price<$5 guard so mistags cannot re-enter |
| SPORTS | never verdicted; `_sportsbet` DB only | out of scope for capital; keep as separate product |
| INDEX_STOCK | referenced in `portfolio_gates.py`, `edge_stability.py`; no ledger | unify into EQUITY or delete |
| PREDICTION (Polymarket/Kalshi) | signals only, no ledger | treat as **feature inputs**, not a class |

---

## 9. MUTUAL_FUND — allocation wrapper, not a pick class

Structurally cannot host this pipeline: NAV struck once daily after close, fills at next unknown NAV,
no intrabar TP/SL, 30-day frequent-trading limits. There is no `MUTUAL_FUND` code path in the repo
except a table-recon script.

**What it can be:** the deployment vehicle. Monthly clock, cost filter (ER ≤0.10–0.20%, no load, no
12b-1), high AUM, low turnover. Fee drag is first-order: 0.60% vs 0.03% ER costs **~10% of terminal
value over 20 years**.

---

## 10. Order of work

| Slot | Class | Why now | Blocking dependency |
|---|---|---|---|
| 1 | **ETF beta sleeve** | Reference return; needs no edge; already measured | none |
| 2 | **EQUITY** | Only positive cost margin, 738 verified marks | L0 pass |
| 3 | **ETF tactical** | Cleanest data → cleanest experiment | L0 pass, intrabar |
| 4 | **CRYPTO** | Highest spend, only diagnosed defect | fill fix + L0 |
| 5 | **FOREX** | Best Sharpe/trade, worst cost ratio | outlier scrub |
| — | BOND, COMMODITY, FUTURES | unmeasurable | n≥50 verified |
| — | MEME, PENNY, SPORTS, INDEX, MF-picks | no mechanism | **retire** |
