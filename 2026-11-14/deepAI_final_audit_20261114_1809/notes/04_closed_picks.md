# Notes — Closed picks (recent realized performance)

Source: `.picks.recent_closed` from live `dashboard_payload.json` (16:15:51Z), 3,500 rows,
P/L as stored by the system (slippage-adjusted). Recomputed by this audit.

## 7 days
| Class | n | WR | PF | Σ P/L |
|---|---|---|---|---|
| CRYPTO | 332 | 34.9% | 0.64 | −218.3pp |
| EQUITY | 19 | 73.7% | 3.63 | +67.8 |
| ETF | 15 | 66.7% | 3.21 | +25.2 |
| FOREX | 25 | 32.0% | 0.56 | −3.9 |
| COMMODITY | 6 | 33.3% | 0.38 | −6.5 |
| BOND | 4 | 25.0% | 0.05 | −3.4 |
| **ALL** | **401** | **37.7%** | **0.79** | **−139.0** |

## 14 days
CRYPTO n=564 WR 38.7% PF 0.79 (−195.1) · EQUITY n=53 52.8% 1.20 (+25.5) · ETF n=43 39.5% 0.84 (−9.8)
· FOREX n=43 51.2% 1.48 (+5.2) · COMMODITY n=7 42.9% 0.60 (−4.2) · BOND n=5 40.0% 0.32 (−2.4)
**ALL n=715 WR 40.6% PF 0.84 Σ −180.8**

## 30 days
CRYPTO n=1,034 39.6% 0.80 (−352.7) · EQUITY n=100 41.0% 0.84 (−41.2) · ETF n=81 39.5% 0.72 (−29.8)
· FOREX n=43 51.2% 1.48 (+5.2) · COMMODITY n=7 42.9% 0.60 (−4.2) · BOND n=8 37.5% 0.67 (−1.3)
**ALL n=1,273 WR 40.1% PF 0.80 Σ −424.0**

## Reading
- Crypto drives the whole result: it is 79% of closed volume and is loss-making at every horizon.
- The positive windows (EQUITY 7d PF 3.63, ETF 7d PF 3.21) are n=15–19 and decay to PF 0.84 / 0.72
  at 30 days → consistent with noise, not edge.
- FOREX is the only class positive at 14/30d (PF 1.48, n=43) — but n is small and the class's own
  long-horizon surface says PF 0.66 (money_ready, n=612) and NOT_READY.
- **One genuine positive:** `mega_mutation::crypto` — n=18 in-window WR 72.2% PF 3.20; peer n=295
  WR 64.1% PF 3.16 PASS_ALL_AXES. This is the only candidate worth forwarding to a pilot.

## Peer cross-reference
- `reports/2026-06-05-PER-CLASS-T2-INVENTORY-POST-FILTER.md`: "0/9 classes are money-ready. Only
  `mega_mutation::crypto` is T1-confirmed (5/5 PASS_ALL_AXES)."
- `reports/REAL_MONEY_NO_SURVIVORS_2026-06-05.md`: "NO surviving real-money candidates"; all 4
  crypto sleeves refuted at intrabar resolver gate.
