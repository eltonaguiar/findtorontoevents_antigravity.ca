# H-035: Crypto 8h Funding-Settlement Pressure Timing

**Tested:** 2026-05-19  
**Symbols:** ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']  
**Records:** 460 settlement events  
**Harness:** eff≥0.3, ≥3 windows, min_n=10/window, net of 30bps


## SHORT Leg Result

- **Verdict:** WEAK
- **Windows scored:** 4
- **Admissible windows:** 2
- **Same sign:** False
- **Effs:** [0.547, -0.496, 0.07, 0.066]
- **Pooled WR:** 40.7%

| Window | N | WR | Avg Net | Eff | Admissible |
|--------|---|-----|---------|-----|------------|
| 2026-03-13 | 22 | 45.5% | -0.48% | 0.547 | ✅ |
| 2026-03-27 | 33 | 33.3% | -0.67% | -0.496 | ✅ |
| 2026-04-10 | 41 | 34.1% | -0.28% | 0.070 | ❌ |
| 2026-04-24 | 28 | 50.0% | -0.00% | 0.066 | ❌ |

## LONG Leg Result

- **Verdict:** WEAK
- **Windows scored:** 4
- **Admissible windows:** 2
- **Same sign:** False
- **Effs:** [-0.626, 0.138, -0.231, 0.321]
- **Pooled WR:** 34.1%

| Window | N | WR | Avg Net | Eff | Admissible |
|--------|---|-----|---------|-----|------------|
| 2026-03-13 | 22 | 40.9% | -0.08% | -0.626 | ✅ |
| 2026-03-27 | 33 | 24.2% | -0.19% | 0.138 | ❌ |
| 2026-04-10 | 41 | 39.0% | -0.42% | -0.231 | ❌ |
| 2026-04-24 | 28 | 32.1% | -0.29% | 0.321 | ✅ |