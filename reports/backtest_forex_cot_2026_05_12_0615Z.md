# Backtest -- FOREX COT Positioning Reversal

**Generated:** 2026-05-12 06:15 UTC
**Strategy:** alpha_engine/forex_cot_reversal.py (PR-L)
**Signal source:** SYNTHETIC (random.Random(42))

> **PROD GUARD:** FOREX sizing currently OFF in prod (PR #909, hard-cap until live PF >= 0.8). This is research-only -- do NOT promote to live size on PASS alone.

## Per-pair results

| Pair | Source | Signals | n | WR% | PF | MDD% | Exp% | Verdict |
|---|:---|---:|---:|---:|---:|---:|---:|:---|
| EURUSD | synthetic | 58 | 58 | 43.1 | 1.471 | 3.55 | 0.098 | WARN |
| GBPUSD | synthetic | 63 | 63 | 39.68 | 1.298 | 3.61 | 0.077 | WARN |
| USDJPY | synthetic | 77 | 77 | 37.66 | 1.042 | 10.44 | 0.014 | WARN |
| AUDUSD | synthetic | 46 | 46 | 36.96 | 1.215 | 4.17 | 0.076 | WARN |

## Overall

- **n:** 244
- **WR:** 39.34%
- **PF:** 1.217
- **MDD:** 10.44%
- **Expectancy/trade:** 0.062%
- **Verdict:** WARN  (PASS = PF>=1.5, WARN = 1.0-1.5, FAIL = <1.0)

**Reminder:** Even on PASS, FOREX live size = 0 until the system-wide FOREX PF >= 0.8 (CLAUDE.md / PR #909).