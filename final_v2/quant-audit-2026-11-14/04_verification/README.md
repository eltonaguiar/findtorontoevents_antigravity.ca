# Verification

Two scripts produce every number in this package. Both are self-contained and read only the live
dashboard payload.

```bash
# per-class statistics, exit mix, source/strategy breakdowns, unit check, duplicates, split-half
python3 per_class_stats.py

# planned risk, R-multiples, timeframe split, stop-fill overshoot, breakeven win rates
python3 r_multiples.py
```

Change `P = "/tmp/peercheck/dashboard_payload.json"` at the top of each to your own copy of the
payload (`https://findtorontoevents.ca/audit/` → `picks.recent_closed`; 34,584,792 bytes on
2026-11-14).

Raw output is committed under `05_evidence/`:

| File | What it is |
|---|---|
| `console_per_class.txt` | Full output of `per_class_stats.py` (sha256 `bc035324…`) |
| `console_r_multiples.txt` | Full output of `r_multiples.py` (sha256 `dd1da95d…`) |
| `class_stats.json` | Per-class statistics in machine-readable form |

## Statistics used, and why

- **PF** = gross wins ÷ |gross losses|, on `pnl_pct` as a percentage. Reported for comparability with
  the dashboard, but see the caveat below.
- **Sign test** = exact two-sided binomial on wins vs non-zero outcomes at p=0.5, computed in log space
  (`lgamma`) to avoid the float overflow you get from `comb(n,i)*0.5**n` at n≈2,000. Zeros excluded
  from the count (11 rows).
- **t-stat** = mean ÷ (population σ ÷ √n) on per-trade `pnl_pct`. Treats trades as independent; they
  are not (overlapping positions, correlated symbols), so these t-values are *optimistic*. Any result
  that fails at this level fails definitively.
- **Split-half** = sorted by `closed_at`, split at the median, PF computed separately. No parameter is
  fitted in either half; this is a stability check, not a walk-forward.
- **Top-5 share** = sum of the 5 largest wins ÷ total gross profit. Concentration risk indicator.
- **R-multiple** = `pnl_pct` ÷ planned risk, where planned risk = |entry − stop| / entry × 100.
  R-multiples are the correct cross-class comparison because they normalise for the risk the system
  declared; PF does not.

## Deliberate limitations, stated rather than hidden

1. **PF is not a clean cross-class statistic here.** `exit_reason` mechanically determines win/loss —
   TP_HIT rows are 99.9% wins and SL_HIT rows 1.0% by construction — so class PF largely ranks exit
   composition. This is why §4 of the analysis uses R-multiples instead. I report PF because the
   dashboard reports PF and the comparison has to be made on its own terms.
2. **The 3,500-row window is capped, not exhaustive.** `performance.by_asset_class` reports 4,945
   closed CRYPTO rows against 1,966 here. Full-ledger PF for CRYPTO is 0.91, same sign as 0.768 —
   the conclusion is robust to the window, but the magnitudes are not comparable across sources.
3. **The stop-fill attribution is an inference from prices, not from logs.** I establish that
   `exit_price` differs from `stop_loss` and that `pnl_pct` matches `exit_price`; I infer
   detect-on-poll rather than a data error because pnl never matches neither. I did not read
   `audit_trail/universal_pick_resolver.py` line-by-line to confirm the fill logic. Marked as
   inference.
4. **`confidence`-vs-win-rate buckets from the peer docs are not re-derived here.** The claim is
   directionally consistent with the ledger but I did not reproduce the 14.4% / 60.3% buckets.
5. **No intraday reconstruction was attempted.** Testing idea #1 properly requires OHLCV at the bar
   resolution of the stops (1.50% median risk on crypto implies minutes-to-hours).
