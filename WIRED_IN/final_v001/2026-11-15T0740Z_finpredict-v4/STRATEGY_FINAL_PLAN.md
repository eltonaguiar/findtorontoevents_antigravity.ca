# STRATEGY FINAL PLAN — per asset class

**Folder**: `WIRED_IN/final_v001/2026-11-15T0740Z_finpredict-v4/`
**Purpose**: the concrete, runnable plan to find and prove a profitable strategy per asset class, feeding `findtorontoevents.ca/audit`.

---

## How to read this

Every asset class has exactly one **outcome** it may reach:
- `PROMISING` — wealth/Sharpe beat confirmed, protocol not yet complete.
- `PROVEN` — passes all 10 gates + pre-registered forward test.
- `REJECT` — failed on evidence; dead for this cycle.
- `BLOCKED` — cannot be tested (no data / structural).

There is no `promising` that stays "could be". It either advances to `PROVEN` or drops to `REJECT`.

---

## 1. CRYPTO — BTC sma200

**Current**: `PROMISING`. Wealth 1.94 vs 1.67, Sharpe 0.57 vs 0.46. 0/11 gates. Clean OOS last 40%, 10bp, `shift(1)`.

**Plan (steps in order):**
1. Bootstrap CI: resample weekly strategy returns 10k×; report 5th percentile of net PF and net Sharpe. Require PF_lower > 1.0, Sharpe_lower > 0.
2. Walk-forward: 60% train / 40% OOS; sweep sma∈{180..220}; stability heatmap; require ≥60% profitable folds and mean OOS PF > 1.2.
3. Deflated Sharpe: DSR > 0.95 with nb_trials = count of all crypto configs tried (~20).
4. Bonferroni: α_adj = 0.05/20 = 0.0025 per crypto hypothesis.
5. Shuffle control: permute BTC returns; strategy must NOT reproduce edge (edge gone in permuted series).
6. Regime split: bull/bear/sideways; positive net expectancy in majority of regimes.
7. Pre-registered forward test: paper trade n≥100 (≈2 yr at 52 wk), thresholds PF≥1.3, WR≥55%, bootstrap 5th%>0.
8. Reproducibility: fixed seeds; versioned data; runnable `experiments/crypto_sma200_oos_protocol.py`.

**Exit**: if any of 1-6 fails → `REJECT`, stop. If 1-6 pass → run 7. If 7 passes → `PROVEN`, sizing allowed.

---

## 2. COMMODITY — GLD sma200

**Current**: `PROMISING (window-sensitive)`. Wealth 2.12 vs 2.01, Sharpe 1.14 vs 0.93. Apply 1% wealth-margin gate.

**Plan**: identical sequence to BTC, plus **stability across windows** (re-run last 30%/40%/50% OOS; require beat in ≥2 of 3 windows). If window-sensitive → `REJECT`.

---

## 3. EQUITIES

**3a. Baseline sleeve (product)**
- Rule: equal-weight SPY/QQQ/VTI when each above 200dMA, else SGOV. Never hold TLT/BND below their 200dMA.
- Verdict: `DD_OVERLAY` — beats SPY on risk, near wealth-neutral. This is the **baseline benchmark** for the audit dashboard.

**3b. Forward alpha candidate — vwap-reversion-scout**
- Prior: +1.96pp excess, t=1.99, 28 picks.
- Pre-register clock (per buffy `FORWARD_TEST.md`): need n≈155 (≈3 yr at 48/yr), |t|≥3.54 (multiplicity bar) or PF+boostrap CI.
- No promotion off interim look. Do not increase exposure before the clock fills.

---

## 4. BONDS — REJECT (final)

Evidence: TLT Sharpe −0.95 vs −0.46, BND −0.21 vs +0.10; both lose wealth. Emitter already killed live TLT/BND STRONG_BUY below 200dMA. **No active bond strategy** this cycle; SGOV remains the defensive allocation. Do not re-test.

---

## 5. FOREX — BLOCKED

Evidence: `^DXY n=0`; no clean validated long history for majors. **Blocked on data**, not signal. When a clean feed exists, pre-register the protocol first. No live forex today.

---

## 6. PREDICTION MARKETS — REJECT (structural)

Zero-sum, adverse selection, fees, size mismatch, PBO=0.603. Shadow-only; not part of the profitability claim.

---

## 7. Order of execution (what to build/run first)

| # | Action | Owner | What it unblocks |
|---|---|---|---|
| 1 | Add 10-gate protocol to BTC and GLD backtest | finpredict | `PROVEN` candidates |
| 2 | Stand up vwap forward clock + qa_ledger wiring | finpredict | equity alpha test |
| 3 | Wire `sma200_wealth_gate_backtest.json` into audit verdict panel | finpredict | `findtorontoevents.ca/audit` |
| 4 | Keep `sizing_allowed:false` everywhere until a class is `PROVEN` | all | safety |

---

## 8. Definition of "done"

A class is **done** when it is `PROVEN` (all 10 gates + forward test) and its overhead is live on the audit dashboard with a verdict panel, benchmark comparison, and `sizing_allowed` flag. Everything else is `REJECT` or `BLOCKED`, recorded in `DECISION_LOG.md`.
