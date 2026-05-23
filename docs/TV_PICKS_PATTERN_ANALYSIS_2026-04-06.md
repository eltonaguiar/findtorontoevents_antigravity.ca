# TV Paper Trade Pattern Analysis — 2026-04-06

**Source:** `alpha_engine/data/tv_paper_trade_audit_log.jsonl` (70 entries, 27 opens, 26 closes)

## Portfolio Summary
- **Accounts:** 6 (THEWINNERS, SCALPER, TESTER, TRUSTOURSCORE, BROKIE, zerounderscore) + AG_PROVENEDGETEST
- **Direction bias:** 23 LONGs / 4 SHORTs opened. SHORTs outperformed massively.
- **Top symbols opened:** SUIUSDT (5x), OPUSDT (4x), JTOUSDT (3x), KITEUSDT (3x)

## Winners vs Losers
| Symbol | Side | Result | PnL |
|--------|------|--------|-----|
| KITEUSDT | SHORT | +8.6% | +$200 (zerounderscore) |
| BERAUSDT | SHORT | +2.96% | +$296 (zerounderscore) |
| AVAXUSDT | LONG | +8.20% | TP hit (TRUSTOURSCORE) |
| ADAUSDT | LONG | +5.48-5.57% | TP hit (3 accounts) |
| BTCUSDT | LONG | +3.64% | +$2,500 (zerounderscore) |
| OPUSDT | LONG | -2.56 to -3.29% | SL hit on 4 accounts |
| AAVEUSDT | LONG | -3.53% | Biggest single loser |
| STRKUSDT | LONG | -3.00% | SL hit |

**TV WR:** 10 take-profit / 14 SL-cut = 41.7% WR. SHORTs: 100% WR (2/2 realized). LONGs: ~36% WR.

## Key Findings
1. **LONG flood in SHORT regime** killed returns. RCA entry (line 31): 185 LONGs at 15% WR vs 7 SHORTs at 71% WR on 2026-04-05.
2. **A-bucket picks (trust>=6, conf 0.70-0.75, alpha_engine)** lost on OPUSDT (-3.2%) across all books. Score 120 did not protect.
3. **B-bucket (ml_crypto_pred, conf 0.70-0.79)** mixed: JTOUSDT lost (-2.9%), NEARUSDT lost (-2.6%).
4. **tsmom_strategy SHORTs** (trust=3, score=45) outperformed A-bucket LONGs (trust=6-7, score=120).
5. **Only 1 pick skipped** (ARBUSDT LONG — TP below spot). No evidence of skipped winners.
6. **Timing:** 82% of opens placed 01:00-03:59 UTC. No timing edge detected in this small sample.
