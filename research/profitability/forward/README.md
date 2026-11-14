# Forward Validation — H10 (frozen)

**Start:** first close after 2026-11-13 (seeded in `ledger.csv`).
**Parameters:** RSI(2) entry <10, exit >50, max hold 5, SPY/QQQ equal weight when both fire,
idle cash at 13-week T-bill, 5 bps per side. **Frozen.** Any change starts a new version.

## Rules

1. Run `python3 forward/update_ledger.py` after each US close (or daily via cron).
2. The script appends one row per new close: target weights, closes, RSI values, cash rate.
3. Do not edit past rows. Do not tune parameters.
4. Minimum evaluation window: **90 calendar days or 30 round trips, whichever is longer**.
5. Evaluate with the same gates plus the reviewer's stricter gates:
   - excess-of-rf Sharpe > risk-matched benchmark (17% core / 83% T-bill at the realized exposure);
   - DSR >=0.95 at effective N>=38;
   - DSR >=0.95 after removing the single best day;
   - 2-day-lag Sharpe >=1.0;
   - max drawdown within the pre-registered envelope.
6. A pass promotes H10 to `PROVISIONAL` (not `PROVED`); `PROVED` requires a second independent
   forward window or out-of-regime confirmation.

## Ledger columns

`signal_date, spy_w, qqq_w, cash_w, spy_close, qqq_close, spy_rsi2, qqq_rsi2, cash_rate_pct, note`

`signal_date` is the close at which the signal is computed; execution is the next session.
