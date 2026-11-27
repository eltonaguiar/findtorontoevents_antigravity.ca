# EDGE-1 deep-dive — funding-carry lead stress-tested and FALSIFIED as "carry"

**Round:** EDGE-1-STRESS · **Date:** 2026-11-27T12:10Z · **Seat:** kilo-glm52-free-auditreviews
**Artifacts:** `reports/realtime_challenge/kilo/edge1_stress.py` (+`.json`, sha 5408c353),
`edge5_overnight_spy.py` (+`.json`), `forward_ledger.py`, `.github/workflows/edge-forward-monitor.yml`
**Bottom line:** the fleet's "first net-positive signal" (funding carry weekly, Sharpe 0.494)
does **not** survive a rigorous re-adjudication. It is **89% price momentum, only 11% funding
carry**, statistically indistinguishable from zero (t=1.46, 95% CI [−10.8, +137]bp), unstable
out of sample, and its "significant" parameter cells are multiple-testing noise.

---

## 1. The claim being tested

The recovered `edge1_funding_carry.py` reported: *"weekly net +27.9 bp/trade, Sharpe 0.494,
n=24"* — the only positive net-expectancy number in the fleet. If real, it is the whole
program's lead. So it earns the hardest test, not a victory lap.

## 2. Three defects found in the original probe (before believing it)

| # | Defect | Effect |
|---|---|---|
| D1 | `grid = all_ts[::rebalance_hours]` steps N *funding bars* (8h each), so "rebalance_hours=24" is actually **~8 calendar days**, not weekly. Label wrong. | mis-scoped holding period |
| D2 | Sharpe annualised `sqrt(52*24/24)=sqrt(52)` (weekly) but the hold is ~8 days → wrong factor (should be `sqrt(365/8)`). | Sharpe overstated |
| D3 | No t-stat, no CI, no permutation, no OOS split. | a point estimate with n=24 was read as signal |

## 3. Re-adjudication (explicit calendar rebalance, correct stats)

Config: hold=7d, k=3 (long cheapest-3 / short dearest-3 of 10), lookback 7d, **fully**
dollar-neutral, inverse-vol weighted, cost 4.5bp/side. Data: 330d, **990 funding records ×
10 symbols, coverage OK**.

```
BASE (H7,k3,L7, 4.5bp):  n=46  mean +63.98bp  sd 297.5  t=1.46
                         Sharpe_ann 1.55  CI95 [-10.8, +137.3]  p_perm 0.157  win 61%
DECOMPOSITION:           carry +6.45bp   |   price +66.53bp   (carry is 8.8% of gross)
OOS first half:          t=1.64  CI-LB -14.4   (not sig)
OOS second half:         t=0.78  CI-LB -73.3   (not sig)
```

**The decisive line is the decomposition:** the strategy collects **+6.45bp of funding** but
earns **+66.53bp from price**. It is a **cross-sectional price-reversal factor** — long coins
whose funding went negative (usually because they fell and shorts crowded) — dressed as carry.
Calling it "funding carry" is wrong; the carry is ~9% of the P&L.

## 4. Cost & parameter robustness

Cost ladder (base config): at **0bp** mean +73bp but **CI-LB −2.0** (still straddles zero at
zero cost — so it is not merely a cost problem, it is underpowered).  CI-LB stays negative
through 20bp.

Parameter sweep (27 combos: hold 7/8/14 × k 2/3/4 × lookback 3/7/14):
**only 2 of 27 cells** clear CI-LB>0 & p<0.05 (`H14_k2_L3`, `H14_k3_L3`). Expected-by-chance at
α=0.05 across 27 tests is ~1.35 false positives; 2 is **at chance**. The "great" H14_k3_L3 cell
(Sharpe 2.7) is **selection**, not signal — and its sibling H14_k3_L7 is t=0.83. This is the
exact multiple-testing trap the audit corpus warns about.

## 5. Verdict

**EDGE-1 FALSIFIED as a carry edge.** Honest status → `OBSERVE_ONLY`.
- It is a noisy price-reversal factor (sd 297bp/period), not a carry trade.
- Not statistically distinguishable from zero even gross; not stable OOS.
- Do **not** size. Keep on the forward ledger purely as a price-factor observation.

This **retracts** the earlier "first net-positive signal" broadcast. Better to retract now than
to compound an overstated claim — that is the whole point of the program.

## 6. EDGE-5 — SPY overnight (a *real* documented anomaly, honestly cost-gated)

Ran the classic overnight-vs-intraday decomposition on SPY 1993–2026 (8,515 days):

```
GROSS overnight (0bp):  +3.34 bp/day  t=4.61  CI-LB +1.98  Sharpe_ann 0.79  ← real, significant
NET    overnight (4bp):  -0.66 bp/day  t=-0.91  (dies at retail ETF cost)
NET @1bp (futures-ish): +2.34 bp/day  t=3.23  CI-LB +0.99  ← would clear at ~1bp execution
buy-and-hold close-close: +3.97 bp/day t=3.12 (net) ← the honest baseline that works
```

**Verdict:** the overnight drift is **gross-real and significant**, but **not capturable with
daily ETF round-trips (4bp)**; it only clears at ~≤2bp execution (index futures, or a single-leg
carry proxy). Status → `CANDIDATE (execution-dependent)`: worth a futures-cost variant, not a
retail-ETF trade. The only thing that clears cost cleanly is **just holding SPY** — the honest
baseline every timing strategy must beat (most don't).

## 6b. EDGE-2 — the mechanism, proven (explicit price reversal vs momentum)

To confirm EDGE-1 is a price factor, I tested the price leg **directly** on the same 10 perps
(weekly H=7, k=3, dollar-neutral, 4.5bp/side):

```
pure REVERSAL (long 7d losers / short winners): n=24  mean +148 bp  t=+1.47  Sharpe 2.16  win 58%
pure MOMENTUM (long winners / short losers):   n=24  mean -166 bp  t=-1.64  Sharpe -2.42 win 38%
```

**Smoking gun.** EDGE-1's positive P&L is exactly the **price-reversal** factor: coins with
negative funding are recent losers → long them → mean-reversion bounce. The funding ranking is a
*proxy for recent price direction*. Even the explicit reversal is **not significant** (t=1.47,
n=24). So **EDGE-1 ≡ EDGE-2 = an underpowered crypto cross-sectional reversal factor**; it needs
far more weekly observations before it can mean anything.


## 6c. Independent corroboration + window instability (base-worktree `edge2_gate_f`)

The base `auditreviews` colleague (same seat, later run) extended EDGE-1 to **730 days** with a
bootstrap CI, 2× cost stress, funding-vs-price decomposition, leg attribution and a PSR/DSR
proxy — a genuinely stronger implementation. It **independently confirms the falsification**:

| window | n | net mean | 95% CI | 2× cost CI-LB | Sharpe | DSR proxy | funding leg | price leg |
|---|---|---|---|---|---|---|---|---|
| stored 12:07Z | 41 | **+46 bp** | [−162, +237] | −171 | 0.51 | 0.666 | +12.9 | +42.4 |
| reproduced 16:45Z | 41 | **−58 bp** | [−306, +164] | −315 | −0.53 | 0.313 | +12.8 | **−61.9** |

Both: **n=41 < 100, CI straddles zero, DSR<1.0 → Gate F INCONCLUSIVE**; funding leg is small and
stable (~+13bp) while the **price leg swings +42 → −62bp**. That sign flip across overlapping
windows is the signature of a **noisy price factor with no carry edge** — exactly EDGE-1's
diagnosis, reproduced by an independent implementation. `OBSERVE_ONLY` stands.

## 7. What this round actually changed

1. **EDGE-1 retracted** from "lead" to OBSERVE_ONLY (price factor, not carry).
2. **EDGE-5 promoted** to CANDIDATE (execution-dependent) — first honest, significant,
   cost-reasoned anomaly, contingent on ~≤2bp fills.
3. **Forward ledger + GHA monitor shipped** (`forward_ledger.py` + `edge-forward-monitor.yml`):
   the program's missing forward clock now exists and accrues daily/weekly, idempotently.
4. **Method law reinforced:** always decompose a "carry" claim into carry vs price; always
   sweep ≥20 parameter cells and show how many clear by chance.

## 8. Next (feeds charter)

- EDGE-5 futures-cost variant (ES/NQ overnight, ~1bp) — pre-register, forward-track.
- EDGE-2 funding EXTREME reversal (high funding → short) as the *reversal* factor it actually is.
- Let the forward ledger run ≥90 days before any promotion; nothing is sized.

*Paper only. Not investment advice. $0 capital sanctioned.*
