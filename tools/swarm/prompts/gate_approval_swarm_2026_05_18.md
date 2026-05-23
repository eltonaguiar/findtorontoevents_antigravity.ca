# Gate Approval Decision — findtorontoevents.ca Trading System

You are a quantitative trading risk analyst reviewing 5 pending gate approvals for a live trading signal system.
The system tracks picks (LONG/SHORT signals) across CRYPTO, COMMODITY, EQUITY, ETF, FOREX, BOND, FUTURES asset classes.
Performance data is real — these are resolved closed picks from a live tracker.

For EACH gate below, give a clear APPROVE ENFORCE / REJECT / MODIFY recommendation with one-paragraph rationale.
Focus on: statistical validity, expected impact on live verdicts, risk of Type I (false block) vs Type II (false pass) errors.

---

## Gate 1: RR_HIGH_GATE_ENFORCE=1 (M-109 — Risk/Reward High Gate)

**Evidence:** Walk-forward harness (n=2,575 picks with valid RR field):
- RR <= 1.0: WR = 53.7% (baseline)
- RR 1.0-1.5: WR = 44.2%
- RR 1.5-2.0: WR = 30.9%
- RR 2.0-3.0: WR = 18.4%
- RR 3.5+: WR = 5.7%

Correlation: higher risk_reward PREDICTS LOSERS. Gate hard-rejects picks with RR > 1.5.
Currently in shadow mode (stamps _rr_high_flag=True but does NOT reject).
Enforcing would affect ~15% of current open picks.

**Question:** Should we promote from shadow to enforce?

---

## Gate 2: ML_ENHANCED_CRYPTO_QUARANTINE=1 (M-105)

**Evidence:**
- CRYPTO ml_enhanced_* family: 617 total resolved picks, raw PF = 0.754 (sub-1.0, losing)
- After bad actors already blocked: 281 surviving picks, PF = 2.83 (selection-biased — bad variants removed)
- ml_enhanced picks = 281/291 = 96.6% of CRYPTO MONEY_READY picks
- Enforcing quarantine: CRYPTO verdict drops from MONEY_READY to NOT_READY
- The 16 worst ml_enhanced variants (n>=10, PF<1.2) are already blocked
- The surviving 112 variants have NOT been individually audited

**Question:** Should we quarantine all remaining ml_enhanced CRYPTO picks (enforce=1)?

---

## Gate 3: MDD_GATE_ENFORCE=1 (I-3 — Max Drawdown + CVaR Gate)

**Evidence (rolling equity curve from sequential pick returns):**
- COMMODITY: MDD = 61.6% (threshold = 20%) — FAIL
- CRYPTO: MDD = 89.6% (threshold = 20%) — FAIL
- ETF: MDD = 8.2% — PASS
- EQUITY: insufficient n

Note: MDD computed as peak-to-trough on sequential (chronological) pick returns.
Enforcing: COMMODITY and CRYPTO both downgrade from MONEY_READY to NOT_READY.

**Question:** Should we enforce MDD <= 20% as a hard gate?
Consider: is sequential equity-curve MDD appropriate for a diversified daily pick signal system where picks are NOT sized sequentially?

---

## Gate 4: Block ("FUTURES", "futures_momentum")

**Evidence:**
- futures_momentum strategy, FUTURES class: 201 picks total
- WR = 2.0%, PF = 0.035, sum_PnL = -553%
- 197/201 exits are SL_HIT_REPLAY (stop-loss hit every time)
- All symbols: CT=F 0%, HG=F 0%, SI=F 2.2%
- No viable sub-cohort found (no slice with WR>15% and n>=20)
- Investigation doc exists: reports/deep_dive_futures_2026_05_18.md

**Question:** Should ("FUTURES", "futures_momentum") be added to BLOCKED_ASSET_STRATEGY_PAIRS?

---

## Gate 5: Block LONG direction for 3 strategies

**Evidence (from mutation evidence doc):**

| Strategy | Direction | n | WR | PF |
|----------|-----------|---|----|----|
| myfxbook_retail_contrarian | LONG | 121 | 14.0% | 0.19 |
| myfxbook_retail_contrarian | SHORT | 38 | 57.9% | 2.31 |
| cta_cross_asset_tsmom | LONG (COMMODITY) | 71 | 12.7% | 0.14 |
| cta_cross_asset_tsmom | SHORT (COMMODITY) | 12 | 41.7% | 1.22 |
| forex_carry_momentum | LONG | 181 | 5.0% | 0.04 |
| forex_carry_momentum | SHORT | 44 | 47.7% | 0.93 |

Note: forex_carry_momentum SHORT has PF=0.93 < 1.0 even for SHORT. Only LONG is catastrophic.

**Question:** Should LONG direction be blocked for these 3 strategies via BLOCKED_DIRECTION_TRIPLES?
Consider: forex_carry_momentum SHORT PF<1.0 — is blocking LONG enough, or should the whole strategy be killed?

---

## Response Format

For each gate:

GATE N: [APPROVE ENFORCE / REJECT / MODIFY]
Rationale: one paragraph

If MODIFY: specific change recommended

Then a final EXECUTION ORDER section if multiple gates are approved, ranked by priority.
