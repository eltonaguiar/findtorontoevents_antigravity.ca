# Per-asset-class research and backtest plan — 10 classes, 5 phases each

**Date:** 2026-11-22 · **Harness:** `tools/per_class_edge_harness.py` · **Registry:** H-200 … H-221 (pre-registered)
**Companion:** `reports/2026-11-22-edge-proof-project-plan.md` (G0–G8 proof standard, forward sleeve, kill rules)

---

## 0. Why this plan exists

The first sweep was wrong in a way worth naming: it ran six classes and, in the
peer's version, silently dropped any class under a minimum row count. BOND, ETF,
FUTURES, PENNY_STOCK, MUTUAL_FUND and INDEX disappeared instead of appearing with
an honest `INSUFFICIENT_N` label. **A missing class reads as "no problem"; an
`INSUFFICIENT_N` label reads as "we do not know yet".** Those are different
claims and only one of them is true.

This plan covers **10 classes**, each with its own research phase, backtest phase,
validation phase and decision gate. The same statistical contract applies to all
of them (see §1), so a result is comparable across classes and cannot be promoted
because it looks good in isolation.

---

## 1. The shared validation contract (applies to every class)

| Check | Threshold | Where it comes from |
|---|---|---|
| Population declared before scoring | N frozen in the pre-registration file | G0 / M-107 |
| Trade count | n ≥ 30 to speak at all; n ≥ 196 for a μ = 0.2 R claim | sample-size table, project plan §1 |
| Net expectancy | block-bootstrap 95 % CI lower bound > 0 | G2 |
| Cost stress | CI lower bound still > 0 at **2× cost** | G3 |
| Stability | both chronological halves > 0 | G5 |
| Multiplicity | DSR ≥ 0.95 with n_trials = **22** (every cell in this sweep) | G4 |
| Benchmark | excess vs same-window buy-and-hold > 0 | G6-adjacent (beta check) |
| Overfitting | PBO(CSCV) reported; anything > 0.5 means the winner is not selectable | Bailey et al. |

Two calibration facts that justify being this strict. In a published simulation
study of backtest-overfitting detectors, uncorrected tests are not merely
conservative or aggressive — they are wrong by an order of magnitude: a t-test on
the winner false-positives **54 %** of the time with no alpha, a winner-only
bootstrap **72 %**, PSR > 0.95 **76 %**. The corrected family lands where it
should: Holm 8 %, Benjamini–Yekutieli 2 %, White Reality Check 6 %, Hansen SPA
4 %, **Deflated Sharpe 2 %**, **PBO(CSCV) 0 %**. A desk that quotes a raw
p-value on its best cell is quoting noise.

---

## Phase EQ — EQUITY (large-cap US)

**Evidence base.** Post-earnings-announcement drift (PEAD) is the best-documented
equity anomaly and the closest thing to the pattern described as "beats earnings
and keeps grinding up". It has decayed: recent work finds it weak and sensitive to
the normal-return benchmark for S&P 500 names, near-mild-mean-reversion at short
horizons, and reduced when event-based news pre-empts the surprise. But a 2025
study revives it with **12 quarters of standardized unexpected earnings** rather
than the latest surprise — Sharpe ratios roughly double, and the gains are
strongest exactly in large caps where the latest print is priced instantly and
older prints are not.

- **EQ.1 Research:** pull earnings dates + surprise % per name (yfinance
  `earnings_dates`), build SUE history, check coverage per name before claiming.
- **EQ.2 Backtest:** three mechanisms, all pre-registered — `tsmom_12_1` (H-200),
  `xsmom_top3_6m` (H-201), `pead_sue20d` (H-203, enter next open, hold 20
  sessions, 10 bps).
- **EQ.3 Validation:** the §1 contract, plus a long-only-vs-benchmark decomposition
  (if the cell is just beta to SPY, excess-vs-bench ≤ 0 kills it).
- **Gate:** no EQUITY promotion without PEAD coverage ≥ 80 % of the universe and
  excess-vs-SPY > 0 after 2× cost.

## Phase ET — ETF

**Evidence base.** Cross-sectional ETF momentum and trend are the cheapest way to
express a sector/asset-class view: 10 bps round trip, deep liquidity, no
single-name blow-up risk. The risk is that momentum in ETFs is largely re-labelled
beta rotation and dies in the whipsaw regime.

- **ET.1 Research:** sector/country/commodity ETF universe, survivorship check
  (delisted ETFs), turnover budget per rebalance.
- **ET.2 Backtest:** `tsmom_12_1` (H-204), `xsmom_top3_6m` (H-205), 21-day
  rebalance, 10 bps.
- **ET.3 Validation:** §1 + correlation of the cell's returns to SPY; if
  correlation > 0.9 the "edge" is SPY with extra steps.
- **Gate:** needs excess-vs-SPY > 0 and a drawdown no worse than SPY's.

## Phase CR — CRYPTO

**Evidence base.** Our full-population result is the anchor fact: 22,864
policy-clean crypto picks at **PF 0.2656** and **−0.0464 %/trade gross**. That is
not a tuning problem. Directional crypto is quarantined until a *non-directional*
mechanism (funding/basis, liquidity provision) is registered. The directional
cells here exist only to be measured and closed.

- **CR.1 Research:** funding-rate history and basis by venue; verify we have
  per-venue funding data before proposing a carry mechanism (H-151 was already
  refuted at −0.2054 %/mo, t = −0.63).
- **CR.2 Backtest:** `tsmom_6m` (H-206), `xsmom_top3_3m` (H-207) at 20 bps.
- **CR.3 Validation:** §1 + a first-touch exit reconciliation, because 54 % of
  crypto exits change under intrabar resolution.
- **Gate:** directional crypto stays quarantined unless a cell clears G2+G3 **and**
  survives first-touch resolution. Expectation: it will not.

## Phase FX — FOREX

**Evidence base.** Trend/carry in FX is real in the literature but the cost
structure is the whole game: our own per-class panel shows gross PF 1.203 against
net 0.857 — 35 PF points of cost. Any FX claim must state the execution
assumption explicitly.

- **FX.1 Research:** interest-rate differentials for carry, swap/roll costs, and
  what a realistic retail spread actually is per pair.
- **FX.2 Backtest:** `tsmom_ls` per pair (H-208) and portfolio, `xsmom_top2_3m`
  (H-209), 5 bps round trip.
- **FX.3 Validation:** §1 + a cost ladder (1×, 2×, 3×) so the break-even spread is
  published rather than assumed.
- **Gate:** no FX promotion while net < gross by more than the claimed edge.

## Phase CM — COMMODITY

**Evidence base.** Our panel shows PF 0.165, which is more likely a
pricing/roll-construction bug than a signal. Commodity futures returns require
continuous-contract handling; a naive adjusted close bakes in roll noise.

- **CM.1 Research:** roll methodology (back-adjusted vs ratio-adjusted), contract
  months, whether the series we have is even tradable.
- **CM.2 Backtest:** `tsmom_12_1` on front month (H-210), `xsmom_top2_6m` (H-211),
  15 bps.
- **CM.3 Validation:** §1 + a data-integrity check (no synthetic continuation
  gaps; roll dates identified).
- **Gate:** the 0.165 number must be explained before any commodity statistic is
  quoted again. Either it is a bug or it is a finding — both matter.

## Phase BD — BOND

**Evidence base.** Duration trend works in rate cycles and fails in chop. Our
panel: gross 0.904 / net 0.726. Bond ETFs are a proxy, not the instrument; the
real exposure is rate futures.

- **BD.1 Research:** duration/curve exposure, rate-futures alternative (ZB/ZN),
  and whether ETF NAV vs price introduces a tracking artifact.
- **BD.2 Backtest:** `tsmom_12_1` on TLT (H-212), `xsmom_top2_6m` (H-213), 10 bps.
- **BD.3 Validation:** §1 + explicit statement of whether the series is total
  return (coupons included). A price-only bond series understates carry and
  misstates everything.
- **Gate:** no bond claim on a price-only series.

## Phase FU — FUTURES

**Evidence base.** Index and rate futures are the cleanest trend instruments we
can access (deep liquidity, cheap, no single-name risk). Managed-futures trend is
one of the most replicated anomalies in the literature; the open question is
whether the replication survives our cost and stability gates.

- **FU.1 Research:** continuous-contract construction, contract multipliers,
  margin/rollover mechanics, and session-time alignment (futures trade nearly 24h).
- **FU.2 Backtest:** `tsmom_6m` on ES front (H-214), `xsmom_top2_6m` across the
  futures set (H-218), 10 bps.
- **FU.3 Validation:** §1 + roll-gap audit + a session-alignment check.
- **Gate:** the most likely class to produce a real, cheap, scalable candidate —
  which is exactly why it gets the strictest roll audit.

## Phase PS — PENNY STOCK

**Evidence base.** The class where the naive result is most likely to be a
liquidity illusion. Sub-$5 names have wide spreads, thin books, and survivorship
bias that flatters any long-only backtest. Our harness deliberately does **not**
model market impact here — that caveat is recorded in the registration (H-215).

- **PS.1 Research:** real spread/size data per name, delisting rates, and which of
  the eight tickers still trade (some of the original list is already gone).
- **PS.2 Backtest:** `tsmom_12_1` (H-215), `xsmom_top2_6m` (H-219) at 10 bps
  *knowing the cost is understated*.
- **PS.3 Validation:** §1 + a liquidity haircut (add 50–100 bps) and a
  survivorship-bias note. Any result that dies at 100 bps is not an edge, it is
  an execution fantasy.
- **Gate:** no penny-stock promotion without a modelled spread and size cap.

## Phase MF — MUTUAL FUND

**Evidence base.** Mutual-fund NAVs are struck once a day and cannot be traded
intraday; you buy at the close. Trend on NAV is therefore a *slow* signal, and
the honest question is whether the fund's own style drift explains the return.

- **MF.1 Research:** NAV-only pricing, redemption fees, and the fact that some
  tickers (e.g. VFIAX) are share classes with minimums.
- **MF.2 Backtest:** `tsmom_12_1` on a NAV series (H-216), `xsmom_top2_6m`
  (H-220), 10 bps.
- **MF.3 Validation:** §1 + next-day execution only (no same-close fills).
- **Gate:** the only acceptable claim is a *fund-selection* rule, not a trading
  edge.

## Phase IX — INDEX

**Evidence base.** Index levels are not tradable directly — you express the view
via futures or ETFs. A positive "index trend" result is a statement about the
signal, not about a portfolio we can hold.

- **IX.1 Research:** index vs tradable proxy mapping (^GSPC→SPY, ^NDX→QQQ,
  ^RUT→IWM) and the tracking difference.
- **IX.2 Backtest:** `tsmom_12_1` on index level (H-217), `xsmom_top2_6m` (H-221),
  10 bps, purely as a signal test.
- **IX.3 Validation:** §1 + confirmation on the tradable proxy (a signal that only
  works on the non-tradable index is an artifact).
- **Gate:** never promote an index cell directly; promote the proxy version.

---

## 2. Execution order and effort

| Order | Phase | Why here | Effort |
|---|---|---|---|
| 1 | FUTURES | cheapest, cleanest, most likely real trend | 1 day |
| 2 | EQUITY | only gross-positive class in our own panel; PEAD has real literature | 2 days |
| 3 | ETF | cheap, but beta-contaminated — needs the correlation test | 1 day |
| 4 | INDEX | signal test to validate the trend family | ½ day |
| 5 | BOND | depends on getting a total-return series right | 1 day |
| 6 | COMMODITY | data bug must be explained first | 1 day |
| 7 | FOREX | cost ladder first, or it is uninterpretable | 1 day |
| 8 | MUTUAL_FUND | slow, low-value, but must be covered | ½ day |
| 9 | PENNY_STOCK | highest illusion risk, needs liquidity modelling | 1–2 days |
| 10 | CRYPTO | quarantined; measured only to close the question | ½ day |

## 3. What "done" means for this plan

Every class reports one of four labels, with the numbers behind it:

- **PASSES_G2_G3_G5** — survives net expectancy, 2× cost, and both halves; still
  needs DSR ≥ 0.95 and a forward pod before anyone calls it an edge.
- **FAILS_COST_OR_STABILITY** — has a signal, cannot pay for it. Publish the
  break-even cost.
- **REFUTED_OR_WEAK** — no signal at this resolution. Say so plainly.
- **INSUFFICIENT_N** — not enough data to speak. Never silently dropped.

A plan that ends with ten `INSUFFICIENT_N`/`REFUTED_OR_WEAK` labels and one
honest candidate is a successful plan. A plan that ends with ten "promising"
classes and no forward evidence is how desks lose money.
