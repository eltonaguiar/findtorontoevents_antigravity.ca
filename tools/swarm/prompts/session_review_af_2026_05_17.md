# Session AF Review — 2026-05-17

## Context
Continuation of autonomous trading-edge improvement session on findtorontoevents.ca/audit.
Follows Session AE (M-075 new-strategies shadow tracker + DXY booster ordering doc).

## Deliverables This Session

### 1. FOOLPROOF_ACTION_PLAN Audit + Corrections

Ran a quick-check grep against the action plan open items. Several items were marked MISSING
by the grep but were actually implemented under different code patterns. Updated
`FOOLPROOF_ACTION_PLAN.md` to mark these as done:

- **COT z-score gate** — verified in `audit_trail/quality_gates.py:3562-3573` (+10 for
  cot_z > 1.0 + direction aligned, +5 for cot_z > 0.5, -8 for inverse)
- **COT alignment booster** — DXY inverse (+6) in `alpha_engine/score_booster.py` (M-074);
  COT alignment (+10/+5) in `audit_trail/quality_gates.py:3562-3573`
- **TLT/IEF yfinance pipeline** — verified yfinance returns data for TLT/IEF/LQD without FRED

### 2. bond_connors_rsi2 Backtest (M-076)

Created `tools/bond_connors_rsi2_backtest.py`:
- Fetches TLT/IEF/LQD daily OHLC from yfinance (2005→today)
- Implements Connors RSI(2) mean reversion: entry when RSI(2)<10 AND price>SMA200
- Exit: daily close >= TP (+2%) or <= SL (max(-2%, SMA200)) or 30-bar timeout
- Fixed capital $10k/trade; MDD measured in USD peak-to-trough / trade capital

Results (2005-01-01 → 2026-05-17, n=269 trades):
```
Win Rate:         55.02%   (T2 threshold ≥50% ✓, borderline T1 ≥55%)
Profit Factor:    1.4671   (near T2 threshold of 1.5)
MDD:              16.13%   (T2 threshold <20% ✓)
Sharpe:           2.78     (excellent)
Total PnL:        $7,682 on 269 × $10k trades
```

Per-symbol breakdown:
```
LQD: n=85  WR=57.7%  PF=1.50  (T2 ✓, best performer)
TLT: n=101 WR=55.5%  PF=1.45  (approaching T2)
IEF: n=83  WR=51.8%  PF=1.46  (T2 WR ✓, PF just below 1.5)
```

Output written to `audit_dashboard/data/bond_connors_rsi2_backtest.json`.

## Review Questions

1. **Connors RSI(2) exit logic**: The backtest uses daily close prices to detect TP/SL
   touches, but the actual `bond_strategies.py` implementation emits signals at close and
   assumes TP fills at limit. In live markets, TP may overshoot intraday but close below.
   Does this introduce look-ahead bias or systematic overstatement of wins?

2. **30-bar timeout**: EXPIRED picks are counted as WIN if close > entry, LOSS if close <=
   entry. This is mark-to-market, not neutral. Should timeout trades be excluded from WR/PF
   like the shadow tracker's EXPIRED treatment?

3. **LQD as corporate bond proxy**: LQD has a credit-spread component that doesn't apply
   to pure rate-driven TLT/IEF. Should LQD be excluded or handled separately (credit
   regime overlay)?

4. **n=269 over 21 years = ~13 trades/year**: Connors RSI(2) is a rare signal in an
   uptrend-filtered regime. Is n=269 sufficient for promotion, or should the shadow tracker
   criteria (n_closed≥10 AND WR≥50% AND PF≥1.5) apply here too before live deployment?

5. **FOOLPROOF items marked done**: The COT z-score gate shows `cot_net_z` field being used
   — but does the scanner actually populate `cot_net_z` on picks? If the field is missing
   from most picks, the gate is wired but never firing. Should we verify field fill rate?

## Output Format Required
Provide a JSON assessment:
- verdict: APPROVE, REQUEST_CHANGES, or NEEDS_DISCUSSION
- concerns: list of {severity, area, issue, recommendation}
- action_items: list of {priority, description, file, rationale}
- summary: one paragraph overall assessment
