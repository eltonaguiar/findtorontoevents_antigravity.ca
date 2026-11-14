# final_v2 — quant-audit-2026-11-14

Second and final pass. `final_2026_11_14/quant-audit-2026-11-14/` adjudicated *claims*; this pass
answers the question those claims were circling: **where, if anywhere, can this system be
profitable, per asset class — and what specifically stands in the way?**

Same rule as last time: every number below was computed by me from an artifact I can point at, and
every claim I could not check is marked unverified rather than guessed.

## Structure

| Folder | Contents |
|---|---|
| `00_executive_summary/` | Verdict table per asset class, the two corrections to my own prior work, the one fix that matters |
| `01_peer_reviews/` | Adjudication of the six peer profitability/audit programs by re-execution |
| `02_per_asset_class/` | Measured per-class statistics, and a separate doc on the specific path to profit for each class |
| `03_ideas_ranked/` | Eight ranked, falsifiable ideas with the gate each must clear |
| `04_verification/` | The two scripts that produce every number here |
| `05_evidence/` | Raw script console output (sha256'd), class stats JSON |

## How to reproduce

```bash
python3 final_v2/quant-audit-2026-11-14/04_verification/per_class_stats.py
python3 final_v2/quant-audit-2026-11-14/04_verification/r_multiples.py
```

Both read the live dashboard payload (`picks.recent_closed`, 3,500 rows) fetched from
`https://findtorontoevents.ca/audit/` on 2026-11-14, 34,584,792 bytes. Change the `P = ...` line at
the top to point at your own copy.

## Two corrections to my own `final_2026_11_14` package

1. **"`resolution_method` is None for all 3,500 rows" was wrong.** The field is `exit_reason`, and it
   is populated: SL_HIT 1,468 / TP_HIT 873 / FORCE_CLOSED 615 / TIME_EXIT 517 / UNKNOWN 22 / EXPIRED 5.
   The exit taxonomy I said was missing was there all along under a different key. The real integrity
   problem is not missing exits — it is *where the exits fill* (see below).
2. **The 100× PnL unit error does not exist in this ledger.** Recomputing `pnl_pct` from
   `entry_price`/`exit_price` (direction-aware) reproduces the stored value within 0.05pp for
   **3,500 of 3,500 rows**, median absolute error 0.000pp. The bug is real elsewhere —
   flaxen-hair correctly finds it in `multi_asset/data/multi_asset_closed.json` — but it is not a
   property of the dashboard ledger, and conclusions drawn as if it were are wrong.

## The single finding that matters

Crypto stops are placed at a mean 1.919% risk and realize 2.990%. `exit_price` differs from
`stop_loss` in 703 of 773 stopped trades, and `pnl_pct` always agrees with `exit_price` (633) or with
the stop (140) — never with neither. The overshoot sums to **+828.0pp against a −837.8pp class total:
98.8% of the crypto loss is stop-fill slippage, not signal failure.**

Run the same signals with fills at the stop price and the class goes from PF 0.768 to ≈1.00.

## Status

**No asset class is profitable after costs. No class is sizing-allowed.** EQUITY is the only class
with a positive after-cost win-rate margin (+2.9pp) and it is not statistically established
(t=1.52, p=0.12). Everything else is structurally short of its own breakeven win rate, by 6 to 16pp.
