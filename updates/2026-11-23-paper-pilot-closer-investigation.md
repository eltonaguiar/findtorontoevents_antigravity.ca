# Paper pilot auto-closer investigation (2026-11-23)

**Question:** does the crypto paper pilot close its own rows automatically, or
does it need a closer that does not exist?
**Claim under test:** the pilot "has produced a process, not evidence" and needs
an auto-closer to reach n>=20/100 before the 2026-12-19 gate.

**Verdict: Hypothesis A — the pilot self-closes. The auto-closer suggestion was
unnecessary and is RETRACTED.** No code was added.

## Evidence (origin/main, clean worktree at 6193d171029)

### What closes a row
`verified_strategies/paper_pilot/crypto_intraday_sim.py`:

- [`exit_check()`](/verified_strategies/paper_pilot/crypto_intraday_sim.py:261) decides exits:
  - intrabar TP/SL on bars strictly after entry (lines 273-277: `SL` when
    `b["low"] <= sl`, `TP` when `b["high"] >= tp`);
  - `CLOSE_STOP` when the close-based stop is breached (lines 284-286);
  - `REVERTED` for vwap_reversion when z >= 0 (lines 287-290);
  - `TIME` when `held_bars >= cfg["max_hold_bars"]` (lines 291-293; max_hold_bars
    are 12 / 10 / 18 in `SLOTS`, lines 63-83).
- [`run_one_shot()`](/verified_strategies/paper_pilot/crypto_intraday_sim.py:338) runs the
  exit loop itself ("exits first", lines 367-401), appends the CLOSE row to the
  log (line 398), deletes the position (line 400) and refreshes guardrails
  (line 401).
- `n_closed` is not an external counter: [`slot_guardrails()`](/verified_strategies/paper_pilot/crypto_intraday_sim.py:298)
  computes `n_closed = len(trades)` from CLOSE rows in the log (line 324), and
  `no_judgment: n<20` comes from `MIN_N_BEFORE_JUDGMENT` (line 327-328).
- State lives in `verified_strategies/paper_pilot/crypto_intraday_sim_state.json`;
  rows in `verified_strategies/paper_pilot/crypto_intraday_sim_paper_log.jsonl`.

### Does the workflow actually run?
`.github/workflows/crypto-intraday-sim.yml` is **on main** with
`cron: '7,37 * * * *'` (lines 17-20), checks out `ref: main` (line 37), runs the
sim `--one-shot` (line 49), then the bridge (line 52), and commits state + log +
`reports/forward_observations.jsonl` with `[skip ci]` (lines 73-92).
It is not branch-only. Proof it fires: `git log origin/main` for the sim files
shows a continuous series of `github-actions[bot] chore(sim): crypto intraday
paper tick + forward bridge [skip ci]` commits since 2026-11-20; the latest is
`9fe5c3a9ed9` at 2026-11-23 01:18:49 +0000, and the state file's `last_run` is
`2026-11-23T01:18:25Z`. So C is false too.

### The 5 closed rows' provenance
All 5 CLOSE rows in the sim log were written by the simulator's own exit loop,
not by a manual or bridge action:

| date | slot | symbol | exit_reason | entry_ts | exit_ts | pnl_pct |
|------|------|--------|-------------|----------|---------|---------|
| 2026-11-20 | bollinger_mr | BTCUSDT | CLOSE_STOP | 2026-11-19T20:00Z | 2026-11-20T12:00Z | -4.08 |
| 2026-11-20 | vwap_reversion | BTCUSDT | CLOSE_STOP | 2026-11-19T16:00Z | 2026-11-20T12:00Z | -5.24 |
| 2026-11-20 | vwap_reversion | ETHUSDT | CLOSE_STOP | 2026-11-19T20:00Z | 2026-11-20T12:00Z | -6.28 |
| 2026-11-22 | bollinger_mr | BTCUSDT | TIME | 2026-11-20T20:00Z | 2026-11-22T12:00Z | +3.31 |
| 2026-11-22 | bollinger_mr | ETHUSDT | TIME | 2026-11-20T20:00Z | 2026-11-22T12:00Z | +5.87 |

Counts: bollinger_mr 3, vwap_reversion 2, btc_4h_rsi_macd 0; 2 positions open.
`tools/pilot_forward_bridge.py` only consumes these CLOSE rows (it lists the
same log at line 67) and appends to `reports/forward_observations.jsonl`; it
never writes the sim log.

### The resolver point
`audit_trail/universal_pick_resolver.py` does not resolve the pilot: its
`SYSTEM_SOURCES` list (line 138 onwards) has no paper-pilot/crypto-intraday
entry. That is true but irrelevant: the pilot is resolved by its own simulator,
not by the dashboard resolver.

## Closure rate and projection (arithmetic, not a forecast)
5 CLOSE rows over 2026-11-19T16:00Z -> 2026-11-23T01:44Z (3.41 days) =
~1.5 closes/day aggregate across 3 slots. Per slot: bollinger_mr ~0.9/day,
vwap_reversion 2 then **HALTED** (trailing DD 11.5% > 10%, so it is frozen until
manual review), btc_4h_rsi_macd 0 so far.
At that aggregate rate: n>=20 aggregate in ~10 days (~2026-12-03);
n>=100 in ~63 days (~2027-01-25), i.e. likely **past the 2026-12-19 gate**.
The sample is 5 rows, so this rate has a very wide CI. Formula: days left =
(target - n_closed) / rate.

## Corrected recommendation
- **RETRACTED:** "the pilot needs an auto-closer." It closes its own rows on
  every scheduled tick; `n_closed` grows by itself.
- Remaining, separate concern (not a closer): at ~1.5 closes/day the pilot is
  likely underpowered for n>=100 by 2026-12-19, and vwap_reversion is HALTED
  (its count is frozen without a manual drawdown review). Those are capacity
  and review questions, not a missing closer.

## Not done
No closer was built (B was not proven). No workflow was merged or disabled.
UNMEASURED: btc_4h_rsi_macd's closure rate (0 closes to date); the true
long-run rate given only 5 closes.
