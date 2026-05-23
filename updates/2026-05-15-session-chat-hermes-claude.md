# Session Chat — 2026-05-15 (Hermes → Claude Code continuation)

**Agent:** Claude Sonnet 4.6 (Claude Code, VS Code extension)
**Branch:** `main` (pushed 8 commits)
**Session type:** Continuation from prior context-window — swarm feedback integration + P0-P5 fixes

---

## Session Summary

Continued from prior session that: wired 6 orphaned baby strategies, fixed EQUITY/ETF score floors,
added FUTURES floor=20 for HG=F/PL=F copper/platinum admission, and ran a 3-engine swarm briefing.

---

## Commits Delivered (8 commits pushed to main)

| SHA | Description |
|-----|-------------|
| `424be87` | fix(scoring): downgrade stale CRYPTO source scores + add missing drag penalties |
| `6ef6f1c` | fix(P0): reclassify HG=F/PL=F as COMMODITY + fix probation double-count |
| `d8606f5` | feat(P4): baby strategy backtest runner with walk-forward + T2 auto-promote |
| `349863d` | fix(FOREX): source penalties from three-axis mutation autopsy |
| `9f46065` | fix(BOND/COMMODITY): extend strategy_filter to include bond/commodity for VT_BABY_STRATEGIES |

(plus 3 rebase commits from origin/main)

---

## Key Fixes

### CRYPTO WR Lift (committed `424be87`)
- `mercury2`: +12 → 0 (live n=144, WR=38.2% — was stale +12 from n=74)
- `copy_trader_highscore`: new -18 penalty (n=99, WR=30.3%)
- `regime_terminal`: new -15 penalty (n=65, WR=32.3%)

### P0 COMMODITY — HG=F copper pick admission (`6ef6f1c`)

Three-part fix for 0 active COMMODITY picks:
1. `multi_asset/scanner.py`: HG=F/PL=F `cat` changed from "futures" → "commodity"
   → `asset_class` stamped as COMMODITY (not FUTURES)
2. `audit_trail/quality_gates.py`: `_is_futures_contract_pick()` exempts HG=F/PL=F
   when `asset_class == "COMMODITY"` → no -20 futures probation double-counting
3. `alpha_engine/config.py`: COMMODITY floor 45 → 30

Score path post-fix: 25(base) + 30(COMMODITY copytrader override) − 16(COMMODITY probation,
no_sample) − 4(concentration) = **35 ≥ floor 30 ✓**

### Baby Backtest Runner (`d8606f5`)

New file: `baby_strategies/backtest_runner.py`
- Walk-forward: signals from `df.iloc[:i]` only (look-ahead safe)
- Cooldown guard: no re-entry while prior trade is open
- Trade simulation: TP/SL/max_hold against forward OHLCV
- Metrics: n, WR, PF, MDD, Sharpe (annualized)
- Tier-2 criteria: n≥30, WR≥50%, PF≥1.5, MDD≤20%, Sharpe≥0.5
- `--promote` flag: appends adapter + `VT_BABY_STRATEGIES` registration
- `--batch`: runs all 210 strategies in one pass

Usage:
```bash
python -m baby_strategies.backtest_runner baby_strategies/equity_two_day_rsi_reversal.py
python -m baby_strategies.backtest_runner --batch --promote
```

### FOREX Rescue (`349863d`)
Report: `reports/forex_mutation_autopsy_20260515.md`

Three-axis findings:
- **Direction**: LONG PF=0.80 (n=119) vs SHORT PF=8.11 (n=29) — LONG is the primary drag
- **Symbol kills**: NZDUSD=X (PF=0.32), EURJPY=X (PF=0.20), EURUSD=X (PF=0.46)
- **Source kills**: `multi_asset_scanner` FOREX WR=0% (n=11)

Source-class overrides applied to `_SOURCE_ASSET_CLASS_OVERRIDES`:
```python
("FOREX", "multi_asset_scanner"): -25   # net -50, below FOREX floor=60
("FOREX", "kimi_riseoftheclaw"): -12    # WR=37.5%, n=56 — main volume drag
("FOREX", "alpha_engine"): -8           # WR=29.2%, n=24
```

Survivors untouched: `alpha_engine_fast` (WR=53.8%), `signal_validation`/MeanReversionBB (PF=2.09),
AUDUSD=X (PF=3.55).

**Pending user approval (NOT auto-applied):**
- Block `dxy-reversal-scout` (WR=20%, PF=0.44)
- Block `fx_smart_carry_trade_momentum` (WR=25%, PF=0.63)
- Block symbols: NZDUSD=X, EURJPY=X, USDCHF=X

### BOND Scanner Filter Fix (`9f46065`)
`alpha_engine/scanner.py`: added "bond" and "commodity" to `VT_BABY_STRATEGIES` load condition.
Previously only `("all","crypto","equity","forex")` — BOND and COMMODITY baby strategies
were unreachable. `vt_bond_yield_curve_momentum` + `vt_copper_platinum_cot_momentum` now fire.

---

## Swarm Output (from prior background run)

Engines: deepseek + cerebras (both HEALTHY, ~11-14KB). xai = ZERO (re-run sent to background).

Both engines independently agreed:
1. P0 root cause: probation penalty (-20) + concentration penalty (-4) dragged HG=F below FUTURES floor
2. Fix: reclassify HG=F/PL=F as COMMODITY at scanner level (implemented)
3. P4 (baby backtest runner) is second-highest leverage item (implemented)
4. FOREX LONG/SHORT directional split is the biggest remaining lever (identified, partial fix)

---

## Current Per-Class Status (post-fixes, dashboard refresh pending)

| Class | PF | WR% | n | Active | Status |
|-------|----|-----|---|--------|--------|
| COMMODITY | 2.49 | 61.5 | 322* | 0→1 pending | HG=F copper pick should now clear gate |
| EQUITY | 1.57 | 51.9 | 420 | 7 | T2-borderline; regime_terminal picks closing naturally |
| ETF | 1.48 | 58.5 | 106 | 3 | T2 candidate |
| CRYPTO | 1.36 | 46.7→? | 8011 | 15 | 3 drag sources penalized; WR lift expected |
| BOND | 0.66 | 54.5 | 11 | 0 | bond_yield_curve_momentum now routed; accumulating |
| FOREX | 0.81 | 52.3 | 342 | 4 | Source penalties applied; LONG bias still issue |

---

## Pending / Requires User Approval

1. **BLOCKED_ASSET_STRATEGY_PAIRS additions** (FOREX strategies):
   - `("FOREX", "dxy-reversal-scout")` — WR=20%, PF=0.44
   - `("FOREX", "fx_smart_carry_trade_momentum")` — WR=25%, PF=0.63

2. **Symbol-level FOREX blocks**: NZDUSD=X, EURJPY=X, USDCHF=X

3. **Walk-forward validation** for COMMODITY/BOND (awaiting live data accumulation)

4. **FOREX LONG direction penalty** — largest remaining lever (SHORT PF=8.11 vs LONG PF=0.80)
   Needs research into which sources generate LONG-only FOREX picks

5. **feat branch reconciliation**: `feat/all-picks-log-status-shard-rotation-2026-05-14` is behind
   main by all session changes. Needs `git rebase main` or retire the branch.

---

## Files Modified This Session

- `audit_trail/quality_gates.py` — _SOURCE_SYSTEM_SCORES + _SOURCE_ASSET_CLASS_OVERRIDES + _is_futures_contract_pick
- `alpha_engine/config.py` — COMMODITY floor 45→30, FUTURES floor=20
- `multi_asset/scanner.py` — HG=F/PL=F cat→"commodity", PL=F added to FUTURES dict
- `alpha_engine/scanner.py` — VT_BABY_STRATEGIES filter + "bond"/"commodity"
- `baby_strategies/backtest_runner.py` — NEW: walk-forward backtest pipeline
- `reports/forex_mutation_autopsy_20260515.md` — NEW: three-axis FOREX autopsy
- `baby_strategies/results/` — NEW: backtest result JSONs

---

*Generated by Claude Sonnet 4.6 (Claude Code) · 2026-05-15*
