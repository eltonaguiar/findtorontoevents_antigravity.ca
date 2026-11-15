# Root cause and success criteria — childlike-airport — 2026-11-15T0230Z

The other session's tracker and QA were failing cards for bookkeeping bugs, and our own cards were going to fail the resolver for a horizon bug. Neither is a market edge.

## Their bugs, and the fix

| Bug | What it did | Fix |
|---|---|---|
| QA required `exit_price`, `exit_time`, `resolution_method`, `pnl_pct` on OPEN picks | Every live card was a CRITICAL blank-field fail | Those fields are required only after close |
| QA treated `pnl_pct=0` on an open card as "price moved, data is lying" | Unrealized flat was a kill | Zero PnL is checked only on CLOSED |
| 72h open-position flag ignored the thesis horizon | A 21-day ETF card looked stale on day 4 | Flag only after `max_hold_hours` |
| Cross-source check compared Friday's entry to a later close | Normal next-session drift looked like bad data | Skip when `entry_date` != market `asof` |
| PnL math was long-only and mixed percent with fraction | K4 printed -2001% and K8 fired on noise | Ledger stores percent. Stats recomputed from the ledger. Eliminated ids are not restarted |
| MF gate `min_initial <= $1000` | VFIAX/VTSAX Admiral ($3000) failed a share-class rule, not a quality rule | Threshold is $3000. Missing AUM/min is `insufficient`, not a fake zero |

## Our bug

XLV / LLY / SHY were ranked on the 2026-11-13 close and entered at that same close. That is same-bar leakage. The resolver would also TIME_EXIT them at 96h (ETF/equity) or 120h (bond). The ranking used 63-day momentum. A 4-day exit cannot test that thesis, so a TIME_EXIT or a 4-day ATR stop is not evidence the rule failed.

The 5-year replay of the 4-day version was already breakeven (ETF PF 1.02, equity PF 1.06). That is a no-edge result for the short card, not a verdict on 21-day dual momentum.

Cards now carry `max_hold_hours` 504/504/480, `leakage=SAME_BAR_ENTRY`, `promotable=false`. The resolver honors an explicit hold between 24h and 90 days. Prices were not rewritten. Monday's open is not invented.

## Success criteria

Monitor means the card is a valid experiment. Promote means sizing is allowed. Nothing here is promotable.

| Class | Monitor | Promote | Horizon | Emit now |
|---|---|---|---|---|
| ETF | Next-session entry after `signal_asof`. Benchmark SPY | n>=100, net PF>=1.5 after 10bps, beat SPY, no same-bar entry | 504h | shadow only |
| EQUITY | Same, one name, benchmark SPY | Same | 504h | shadow only |
| BOND | TLT vs SMA200 known at `signal_asof`. SHY is ballast. Benchmark BIL | n>=100, beat BIL, drawdown under 5% | 480h | shadow only |
| CRYPTO | Emit only if close>SMA200 and 21d>0 at `signal_asof`. Benchmark BTC-USD | n>=100, PF>=1.5, PBO<0.3, beat BTC | 48h | no — regime filter failed |
| FOREX | No card. Class frozen | Clean feed, then n>=100 | 72h | no |
| COMMODITY | No card unless 21d>0 and close>SMA200 | n>=100, beat DBC | 504h | no — CL 21d was negative |
| FUTURES | No separate book | n/a | n/a | no |
| MUTUAL_FUND | Screen only. Missing field = insufficient | Never a TP/SL pick | NAV daily | no |
| PREDICTION_MARKET | No card | Rejected | n/a | no |

## What was not claimed

No new OOS proof. No live fill. No mutual-fund NAV pull. The classifier does not read prices after `signal_asof`.
