# Part 5 · P0–P3 Findings — Population Freeze, Window Detector, Equity-Momentum Falsification

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 07:00 EST
**Method:** local `audit_dashboard/data/` payloads, measured (no recalled numbers).

---

## P0 — Canonical population manifest (frozen)

| Field | Value |
|---|---|
| Schema | `audit3.v1` |
| Ledger `generated_at` | 2026-11-20T01:57:23Z |
| Population | `canonical` |
| Rows scored | **8,769** |
| Population total | 16,372 |
| Canonical rows sha256 | `63609da5…acf502c08` |
| Excluded | invalid_row 7,394 · mirror_duplicate 95 · non_performance_exit 43 · resolver_breakeven_fallback 71 |
| Cells | 362 (WEAK 59 · KILL 8 · INSUFFICIENT_N 295) |
| Ledger file sha256 | `a70f336e3c4d9b07…` |

**Rule adopted:** every subsequent claim cites `63609da5…` so a window swap is detectable.

---

## P2 — Window-selection detector (the freebuff retraction pattern, reproduced)

Per class: full-population net expectancy vs the ledger's recency window (last 25% of trades).

| Class | n | FULL net% | RECENT-window net% | Sign flip? | Verdict |
|---|---|---|---|---|---|
| CRYPTO | 6,874 | −0.3159 | −0.7185 | – | KILL |
| **EQUITY** | 942 | **+0.1577** | **−0.9526** | **FLIP** | WEAK |
| ETF | 590 | −0.0043 | −0.3281 | – | WEAK |
| **FOREX** | 279 | −0.1382 | **+0.1305** | **FLIP** | WEAK |
| COMMODITY | 45 | −3.5104 | −3.4210 | – | KILL |
| **BOND** | 35 | −0.1845 | **+0.0197** | **FLIP** | WEAK |
| FUTURES | 4 | +1.2853 | +1.2853 | – | INSUFFICIENT_N |

**3 of 7 classes flip sign** depending on window. This is exactly the mechanism that turned CRYPTO's "PROVEN PF 1.313" into "0.2656 gross-negative" for freebuff.

**Direct consequence for our own Part 4:** the claim "EQUITY is the only class with positive alpha" holds **only on the full population**; the recency window is **−0.95%**. That claim is therefore **window-fragile** and is hereby downgraded from "positive signal" to "not established".

---

## P3 — Equity-momentum falsification (our Part 4 headline)

27 variants of the 30-name large-cap momentum sleeve, 20bp cost:

| Metric | min | median | max |
|---|---|---|---|
| Profit factor | 2.21 | 2.51 | 2.94 |
| Sharpe | 0.99 | 1.16 | 1.30 |
| Max drawdown | 17.4% | 26.6% | 35.9% |

**Gate scorecard under the desk standard:**

| Gate | Result |
|---|---|
| G0 population integrity | ❌ **FAIL** — fixed 30 **ex-post survivors**, no delisted names → survivorship-biased **upper bound** |
| G1 honest resolution | ⚠ unknown (backtest uses its own bars) |
| G2 net CI > 0 | ⚠ not bootstrapped in the file |
| G3 2× cost stress | ❌ **NOT RUN** (only 20bp; need 40bp) |
| G4 multiplicity | ⚠ weak (4 raw T2 passes vs ~1.35 expected false) |
| G5 split-half | ❌ **NOT COMPUTED** |
| G6 concentration | n/a (basket) |
| G7 mechanism | ✅ PASS — many outcomes, 30 symbols (not a payoff grid) |
| G8 forward | ❌ **0 forward rows** |

**Honest verdict: WEAK / hypothesis — NOT CANDIDATE, NOT edge.**

### But one genuinely encouraging fact
**All 27 variants have PF > 2.2** (median 2.51). Unlike a single lucky cell, the momentum effect is **robust to lookback/skip/top-N choice**. That parameter robustness — not the headline PF 2.94 — is the real reason to forward-test it.

Compare B&H SPY: Sharpe 0.946, MDD 23.9%. The sleeve's median Sharpe 1.16 with similar MDD is only modestly better — **the naive case that this beats the market is weaker than the 2.94 PF implies.**

---

## What this changes

1. **Part 4 headline corrected:** equity momentum is a *robust but survivorship-biased hypothesis*, not "the closest thing to edge proved".
2. **EQUITY class positive-alpha claim retracted** (window-fragile).
3. **Next required evidence (P3 remainder):** delisted-inclusive universe, 40bp stress, split-half, bootstrap CI. Only then can it become CANDIDATE.
4. **Forward testing still justified** — because of parameter robustness — but as a *falsification* exercise, sized as paper.

---
*Not investment advice. This document exists to disprove our own prior claim; two claims were downgraded as a result.*
