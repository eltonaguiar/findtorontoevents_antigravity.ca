# Marking the FX picks tempers the carry thesis (AUDJPY long was −5.31%)

**Date:** 2026-11-23T08:07Z · **Author:** Kilo · Paper only.
Prototype: `tools/fx_resolver_prototype.py` → `reports/fx_resolver_prototype.json`.

## What I did
Since the FX fix is "within existing infrastructure", I built the resolver prototype: for each open `=X` pick, mark it at
the **next observed quote** of the same symbol (Mar 21 → Nov 20 2026), labelled `MARK_TO_NEXT_QUOTE` (not a strategy exit).

## Result — the FX book lost money over this window
| symbol | side | entry (2026-03-21) | mark (2026-11-20) | return |
|---|---|---|---:|---:|
| EURUSD | long | 1.1575 | 1.0970 | **−5.23%** |
| GBPUSD | short | 1.3345 | 1.3086 | +1.94% |
| AUDUSD | long | 0.7024 | 0.6655 | **−5.25%** |
| USDCHF | short | 0.7878 | 0.8433 | **−7.05%** |
| **AUDJPY** | **long** | **111.828** | **105.887** | **−5.31%** |
| USDJPY | long | 159.22 | 159.22 | ~0% |

**4 of 6 negative; mean ≈ −3.6%.** USD strengthened broadly over Mar–Nov 2026, so almost every FX long lost.

## Why this matters — it corrects my own carry pitch
I named **AUDJPY carry** as "the one real mechanism + nearest DSR miss" (DSR 0.815). Marking the actual position shows that
its one resolvable instance **lost 5.31%**. So:
- The **mechanism** (G10 carry) is real, but its **realised outcome on our own book over this window was negative** — a
  carry unwind / USD-strength regime dominated.
- The nearest-miss DSR was computed on a **different** (rsi2) sample, not on these carry marks; the two should not be
  conflated. I was at risk of over-selling "FX carry" as the answer. It is the best *candidate to test*, not a winner.
- **Honest status:** FX carry = plausible mechanism, negative realised marks so far. Closing the picks is still the right
  next step — but the first truth it reveals is that the carry position lost.

## Verdict impact
None on the top-line (still 0 investable), but it **removes FX carry from the "promising" column** until a proper,
resolver-produced sample clears DSR. The nearest thing this programme has to a real mechanism has, so far, lost money.

*Paper only. Not investment advice.*
