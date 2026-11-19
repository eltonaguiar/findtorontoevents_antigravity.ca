<AGENT: B> COMPLETE — wrote B_backtest_logic.md

# SUB-AGENT B — BACKTEST LOGIC (NO FUTURE BIAS)

Scope: define the exact Python/pandas backtest rules for the copy-trader / verified-source
picks identified in SUB-AGENT A, with strict no-future-bias guards, hard TP/SL stops,
and UTC-to-EST audit. Output: reports/subscriptions/2026-11-18-copytrader-llm-audit/B_backtest_logic.md

---

## 1. CORE RULES (NO FUTURE BIAS)

### 1.1 Bar/granularity alignment
- The backtest consumes a per-symbol OHLCV bar frame (chosen per asset class: 1m for
  scalping, 5m for swing, 1h for swing). The entry bar is the bar where the signal's
  `entry_time` falls. The exit bar is the LAST bar before or at `exit_time`.
- For each pick, walk the price series forward starting AT `entry_time`. Do NOT
  reference any bar whose timestamp is strictly after `entry_time` as valid entry data.
- `entry_timestamp` is a hard floor: the position may only START on or after this bar.

### 1.2 Exit bar rule (the critical no-future-bias guard)
- A bar is a VALID exit bar ONLY if `bar.timestamp < exit_time`.
- Any bar with `bar.timestamp >= exit_time` is DISCARDED — it must NOT be used as an
  exit bar, even if the bar's close crosses the TP/SL level.
- Equivalently, the exit condition is:
  ```
  exit_bar = bars[(bars.timestamp >= entry_time) & (bars.timestamp < exit_time)]
  ```
  and the tested exit condition iterates over that filtered set only.
- A pick with NO bar satisfying `bar.timestamp < exit_time` is marked MISSING_EXIT
  and excluded from win/loss statistics.

### 1.3 Return formula
```
return_pct = (exit_px / entry_px - 1) * 100 * leverage
```
- `entry_px` = the bar CLOSE at the entry bar (or the mark price at `entry_time`
  for open-ended live signals; if the open is used, that must be stated explicitly).
- `exit_px` = the bar CLOSE of the exit bar (hard stop hit), NOT a forward-filled
  or next-bar value that would introduce future bias.
- `leverage` = position leverage as recorded in the source pick metadata (e.g. 50x
  for Shallow-Pair-Frog OKX; 10x for most Bybit; 3x for BTX/coinglass-type low-
  leverage senders).

### 1.4 Hard TP/SL as stops (no target-based softening)
- TP and SL are applied as hard barriers on the bar prices, evaluated at close:
  - LONG: `exit if bar.close <= stop_loss OR bar.close >= take_profit`
  - SHORT: `exit if bar.close >= stop_loss OR bar.close <= take_profit`
- If neither TP nor SL is hit before `exit_time`, the position runs to `exit_time`
  and the final `exit_px` is the close of the bar at `exit_time` (or the mark price
  at that timestamp for live signals).
- The exit_reason must be logged as: `TP_HIT`, `SL_HIT`, or `TIME_EXIT`.

### 1.5 Leverage / transaction costs
- Apply leverage only to the returns (as above). Do NOT multiply PnL by leverage
  inside the position-sizing step.
- Revolver model: `PnL_dollar = (exit_px - entry_px) * size * leverage * sign`.
  For the correctness audit only the percentage form is required.

---

## 2. TASKS PER PICK

For every pick in the verified-source list (SUB-AGENT A), run:

1. **Timestamp audit** — parse `signal_time` / `entry_date` / `open_time` and
   `closed_at` / `exit_date` separately. Classify each as:
   - `CLEAN` (well-formed ISO-8601 with explicit UTC offset +5 / -5 timezone info)
   - `TIMEZONE_AMBIGUOUS` (naive datetime or no offset)
   - `NEGATIVE_HOLD` (closed_at < entry_time)
   - `UNRESOLVED` (raw data missing)
2. **EST conversion** — `est = utc - 5` (EST standard) for 2026-11-17/18 and any
   date in Nov–Feb; `est = utc - 4` (EDT) for Mar–Oct. A pick whose UTC timestamp
   falls in a boundary month must be checked against BOTH offsets.
3. **Bar filter** — retain bars where `bar.timestamp >= entry_time_est` AND
   `bar.timestamp < exit_time_est`. Any bar with `bar.timestamp >= exit_time_est`
   is flagged as a FUTURE BAR and must not be used.
4. **Backtest run** — apply the return formula + hard TP/SL stops against the
   filtered bar set. Record entry_bar_idx, exit_bar_idx, exit_reason, return_pct.
5. **Reconciliation** — compare the backtest result against the source pick's
   recorded `pnl_pct` / `history_wr` / `history_trades` and flag:
   - `TIMESTAMP_MISMATCH` if UTC->EST shifted the entry across a bar boundary
   - `EXIT_AFTER_EXIT_TIME` if a future bar was used
   - `NO_MISSING_EXIT_BAR` if the filtered set is empty
   - `RECORD_SKEW` if recorded PnL / WR does not match the backtest

---

## 3. EST / TIMEZONE CONVERSION AUDIT (PER PICK)

### 3.1 Offset assignment
- Signal dates 2026-03-01 .. 2026-11-30 inclusive: `UTC -> EDT = UTC - 4`.
  Verification: "Summer (Mar-Oct): EDT = UTC-4".
- Signal dates 2026-11-01 .. 2026-11-30 inclusive (and 11-18 today): `UTC -> EST = UTC - 5`.
  Verification: "Winter (Nov-Feb): EST = UTC-5".
- The 2026-11-17/18 picks in this task MUST use UTC-5. Anything else is a bug.

### 3.2 Generated signal vs live closed position
- `signal_time` / `timestamp` in the pick files is the creation time of the signal.
- `open_time` / `closed_at` / `exit_date` are the position lifecycle timestamps.
- The audit must check that `entry_time_est` == `signal_time_est` for live signals,
  and that `exit_time_est` == `closed_at_est` for closed positions.
- A discrepancy between the recorded `open_time` and the computed `entry_time`
  using the pick's `entry_date` is a RECORD SKEW.

### 3.3 Correct-by-construction rule
- **All** backtest timestamps must be converted to a UTC "epoch seconds" value FIRST,
  THEN shifted to EST with an explicit `offset_hours` field. Never do string
  manipulation like `dt - timedelta(hours=5)` on a naive local-time string.
- The output schema must carry both `entry_time_utc` and `entry_time_est` and the
  `offset_hours` used, so the audit is reproducible.

---

## 4. FUTURE-BIAS DETECTION LOGIC (EXACT CODE)

### 4.1 The bug to avoid
```python
# WRONG — uses bars at or after exit_time as exit candidates
exit_mask = (bars.timestamp >= entry_time) & (bars.timestamp <= exit_time)
```
This permits a bar at `exit_time` itself (or later) to terminate the position,
which shifts the exit price forward of the true `exit_time`. It also misaligns the
signal's own recorded `exit_time` when it is stored in UTC but interpreted as EST.

### 4.2 The correct guard
```python
# CORRECT — bars at or after exit_time are excluded from the exit set
exit_mask = (bars.timestamp >= entry_time) & (bars.timestamp < exit_time)
exit_bars = bars[exit_mask]
if len(exit_bars) == 0:
    report_no_exit_bar(pick)   # MISSING_EXIT
else:
    exit_bar = exit_bars.iloc[-1]   # last bar strictly before exit_time
    # apply TP/SL against exit_bar only
```

### 4.3 Side-channel checks
- A pick whose backtest uses bars later than `exit_time` must be flagged
  `FUTURE_BIAS_DETECTED` and excluded from the firm review set.
- A pick whose backtest uses bars earlier than `entry_time` must be flagged
  `PAST_ENTRY_USED` and excluded.
- A pick whose `exit_time` is earlier than `entry_time` must be flagged
  `NEGATIVE_HOLD`.

---

## 5. PYTHON / PANDAS LOGIC SPECIFICATION

### 5.1 Core backtest function
```python
import pandas as pd

def backtest_pick(pick, bars_df, tp=None, sl=None, leverage=1.0, frame='1h'):
    """
    bars_df: DataFrame with DatetimeIndex or 'timestamp' column in UTC.
    pick: dict with entry_time (UTC), exit_time (UTC), entry_px, tp, sl, leverage.
    Returns: dict with return_pct, exit_reason, entry_bar_idx, exit_bar_idx, bias_flags
    """
    # 1. Normalise timestamps to epoch seconds (UTC)
    bars_df = bars_df.copy()
    bars_df['ts'] = pd.to_datetime(bars_df['timestamp'], utc=True).view('int64') / 1e9
    entry_utc = pd.to_datetime(pick['entry_time'], utc=True).timestamp()
    exit_utc  = pd.to_datetime(pick['exit_time'],  utc=True).timestamp()

    # 2. No-future-bias bar filter
    bias_flags = []
    entry_bar = bars_df[bars_df['ts'] < entry_utc]          # past bars only for entry anchor
    exit_bars = bars_df[(bars_df['ts'] >= entry_utc) & (bars_df['ts'] < exit_utc)]
    if len(exit_bars) == 0:
        return {'return_pct': None, 'exit_reason': 'NO_MISSING_EXIT_BAR',
                'bias_flags': ['NO_MISSING_EXIT_BAR']}
    if len(bars_df[bars_df['ts'] >= exit_utc]) > 0:
        bias_flags.append('FUTURE_BAR_PRESENT')
    if len(bars_df[bars_df['ts'] < entry_utc]) == 0:
        bias_flags.append('PAST_ENTRY_USED')

    # 3. Hard stops (evaluate at the exit bar close)
    e = exit_bars.iloc[-1]
    c = e['close']
    if pick['direction'] == 'LONG':
        exit_px = c
        if sl is not None and c <= sl:
            exit_reason = 'SL_HIT'
        elif tp is not None and c >= tp:
            exit_reason = 'TP_HIT'
        else:
            exit_reason = 'TIME_EXIT'
    else:  # SHORT
        exit_px = c
        if sl is not None and c >= sl:
            exit_reason = 'SL_HIT'
        elif tp is not None and c <= tp:
            exit_reason = 'TP_HIT'
        else:
            exit_reason = 'TIME_EXIT'

    # 4. Return formula with leverage
    return_pct = (exit_px / pick['entry_px'] - 1.0) * 100.0 * leverage
    return {'return_pct': return_pct, 'exit_reason': exit_reason,
            'entry_bar_idx': entry_bars.index[-1] if len(entry_bars) else None,
            'exit_bar_idx': e.name, 'bias_flags': bias_flags}
```

### 5.2 Main loop
```python
def audit_all_picks(picks, bars_by_symbol, timezone='EST'):
    """
    timezone: 'EST' -> offset -5 (Nov-Feb), 'EDT' -> offset -4 (Mar-Oct)
    """
    results = []
    for p in picks:
        sym = p['symbol']
        if sym not in bars_by_symbol:
            results.append({'id': p['id'], 'status': 'NO_BARS', 'error': 'symbol not in universe'})
            continue
        bars = bars_by_symbol[sym]
        res = backtest_pick(p, bars, p.get('take_profit'), p.get('stop_loss'), p.get('leverage'))
        # 5. Timestamp/EST reconciliation
        entry_utc = pd.to_datetime(p['entry_time'], utc=True).timestamp()
        exit_utc  = pd.to_datetime(p['exit_time'],  utc=True).timestamp()
        offset = -5 if timezone == 'EST' else -4
        entry_est = pd.to_datetime(p['entry_time'], utc=True) + pd.Timedelta(hours=offset)
        exit_est  = pd.to_datetime(p['exit_time'],  utc=True) + pd.Timedelta(hours=offset)
        if abs(entry_utc - entry_est.timestamp()) > 3600:
            res['bias_flags'].append('TIMESTAMP_MISMATCHENTRY')
        if abs(exit_utc  - exit_est.timestamp()) > 3600:
            res['bias_flags'].append('TIMESTAMP_MISMATCHEXIT')
        results.append({**res, 'entry_time_utc': entry_utc, 'entry_time_est': entry_est,
                        'exit_time_utc': exit_utc, 'exit_time_est': exit_est,
                        'offset_hours': offset, 'symbol': sym})
    return results
```

### 5.3 Pick ingestion (no manual retyping)
- Pick definitions live in the JSON files under `copy_trader_intel/data/` and
  `alpha_engine/data/` (see SUB-AGENT A output for the source mapping).
- The loader MUST read each pick from its source file; it must NOT be hand-coded
  with the values from SUB-AGENT A's report. The report's per-row values are for
  human review only.

---

## 6. WIN/LOSS / PF / MAX_DRAWDOWN COMPUTATION

- `win = return_pct > 0` (TP/SL resolved), `loss = return_pct < 0`, `flat = None`.
- `win_rate = wins / closed_trades` over the pick's full history.
- `profit_factor = total_win_pnl / abs(total_loss_pnl)`.
- `max_drawdown` computed on the run curve via `peak-to-trough` over the
  backtest equity path; reported per-pick and per-source-group.
- For P&L-based pick records where the source's `pnl_pct` is unknown (`null`),
  the backtest IS the PnL record and the audit compares the new `return_pct`
  against the source's `history_wr` / `history_trades` only.

---

## 7. VERIFICATION CHECKLIST

- [ ] Every pick has `entry_time` and `exit_time` parsed and assigned an explicit
      `offset_hours` (EST=-5 or EDT=-4).
- [ ] No bar with `ts >= exit_utc` is read as an exit candidate.
- [ ] `entry_time_utc` and `exit_time_utc` are stored in the audit record.
- [ ] All picks flagged `FUTURE_BAR_PRESENT` or `TIMESTAMP_MISMATCH` are listed in
      the final report with their pick ID and the specific offending timestamp.
- [ ] The backtest uses the SAME leverage recorded in the source pick metadata
      (e.g. 50x for Shallow-Pair-Frog; 10x Bybit; 3x for BTX-type).

---

## 8. OUTPUT SCHEMA (for SUB-AGENT C's results file)

Each pick in `C_backtest_results.json` must carry:
- `id`, `symbol`, `platform`, `trader_label`, `category` (a/b/c/d/e)
- `entry_time_utc`, `entry_time_est`, `exit_time_utc`, `exit_time_est`, `offset_hours`
- `entry_px`, `exit_px`, `return_pct`, `leverage`, `exit_reason`
- `entry_bar_idx`, `exit_bar_idx`, `bias_flags`, `verified` (boolean)
- `status` (CLOSED / OPEN / NO_BARS / FUTURE_BIAS_DETECTED / TIMESTAMP_MISMATCH)

---

## 9. KNOWN DATA QUALITY ITEMS TO HANDLE

- `myfxbook_olivierdanvel_picks.json`: entry/TP/SL all 0, timestamp 2026-11-17T23:55:43Z
  -> 18:55 EST. EXCLUDE from backtest (synthetic placeholder, status PENDING).
- `cta_picks.json` / `non_crypto_consensus_picks.json`: `entry_date` is YYYY-MM-DD only
  (naive). Use `timestamp` for hour-level EST audit; fall back to day-level if only
  the date is present.
- `okx_futures_picks.json`: `open_time` = null. Use `timestamp` only; flag
  `TIMESTAMP_MISMATCH` for hour-level audit where open_time is missing.
- `bybit_picks.json`: `open_time` mixes ISO-8601 UTC and naive strings. Parse with
  `utc=True`; naive strings become `TIMEZONE_AMBIGUOUS` and are flagged.
- `closed_trades.json` / `highscore_active_picks.json` / `clone_*.json`: these are
  the trader's OWN historical picks, not the source signal feed. The backtest for
  these must use the same rules, but the audit result is labeled with
  `source_system: copy_trader_clones` (class c), distinct from the live feed classes a/b/d/e.
