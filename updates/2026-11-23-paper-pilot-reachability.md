# Paper pilot reachability: can the crypto intraday pilot reach n≥20 before day-30 and n≥100 before day-60?

**Date:** 2026-11-23
**Status:** READ-ONLY diagnosis. Nothing in the pilot was changed.
**Evidence base:** `origin/main` @ `acca431fb8932c1f2deb86f30c2aafe7417e7afe` (2026-11-23T03:06Z).
All file contents cited below were read with `git show origin/main:<path>`, never from the
shared working tree (which sits on `push/phase2-round-2026-11-22`, thousands of commits behind).

---

## 1. What counts toward n

`slot_guardrails()` in [`verified_strategies/paper_pilot/crypto_intraday_sim.py`](../verified_strategies/paper_pilot/crypto_intraday_sim.py:298)
filters the closed rows to ONE slot before counting:

```python
def slot_guardrails(slot: str, closed: list[dict], today: str) -> dict:   # L298
    """Prop-firm style status from CLOSED trades only."""
    trades = [t for t in closed if t.get("slot") == slot]                # L301
    ...
    return {
        "status": status, "reason": reason,
        "n_closed": len(trades), ...                                     # L324
        "judgment": ("no_judgment: n<%d" % MIN_N_BEFORE_JUDGMENT         # L327
                     if len(trades) < MIN_N_BEFORE_JUDGMENT else "reportable"),
    }
```

`closed` itself is every CLOSE row in the log
([`_closed_trades()`](../verified_strategies/paper_pilot/crypto_intraday_sim.py:115), L127:
`if isinstance(obj, dict) and obj.get("event") == "CLOSE"`), and `guards` is built
once per slot (L365: `{slot: slot_guardrails(slot, closed, today) for slot in SLOTS}`).

**The counting unit is the SLOT, not the pod.** `n_closed` and the `no_judgment: n<20`
label are computed per slot, against `MIN_N_BEFORE_JUDGMENT = 20`
([L54](../verified_strategies/paper_pilot/crypto_intraday_sim.py:54)). That is a factor of 3
more stringent than a whole-log count: the pilot needs 20 closed trades *in each slot*
to render a judgement for that slot (60 closes in total for all three), not 20 across the pod.
The state file confirms the same unit: `guardrails.vwap_reversion.n_closed = 2`,
`guardrails.bollinger_mr.n_closed = 3`, `guardrails.btc_4h_rsi_macd.n_closed = 0`
([`crypto_intraday_sim_state.json`](../verified_strategies/paper_pilot/crypto_intraday_sim_state.json), last_run 2026-11-23T02:43:05Z).

Note the downstream pod clock uses a different, stricter bar of its own: the audit3
forward gate is n≥100 on the pod's own hypothesis (the sim's own docstring, L9:
`the audit3 forward gate (n>=100, net PF CI-LB > 1.0, 100% intrabar honesty)`), and the
forward ledger counts per hypothesis id — currently H-2026-11-19-01 = 2, -02 = 3,
-07 = 0 (`reports/forward_observations.jsonl` on main).

---

## 2. The empirical close rate

From `git show origin/main:verified_strategies/paper_pilot/crypto_intraday_sim_paper_log.jsonl`
(12 rows: 7 OPEN, 5 CLOSE). The five CLOSE rows, exactly:

| # | slot | symbol | entry_ts | exit_ts | exit_reason | pnl_pct |
|---|------|--------|----------|---------|-------------|---------|
| 1 | bollinger_mr | BTCUSDT | 2026-11-19T20:00Z | 2026-11-20T12:00:00+00:00 | CLOSE_STOP | -4.0789 |
| 2 | vwap_reversion | BTCUSDT | 2026-11-19T16:00Z | 2026-11-20T12:00:00+00:00 | CLOSE_STOP | -5.2401 |
| 3 | vwap_reversion | ETHUSDT | 2026-11-19T20:00Z | 2026-11-20T12:00:00+00:00 | CLOSE_STOP | -6.2828 |
| 4 | bollinger_mr | BTCUSDT | 2026-11-20T20:00Z | 2026-11-22T12:00:00+00:00 | TIME | 3.3126 |
| 5 | bollinger_mr | ETHUSDT | 2026-11-20T20:00Z | 2026-11-22T12:00:00+00:00 | TIME | 5.8726 |

- First CLOSE: **2026-11-20T12:00Z**. Last CLOSE: **2026-11-22T12:00Z**. Span between first and last close: **48 h**.
- First activity (first OPEN): 2026-11-19T16:00Z → last CLOSE: 68 h elapsed.

Rate as a range, depending on the denominator:

- Over the 68 h from first OPEN to last CLOSE: 5 / 2.83 d ≈ **1.8 closes/day** (whole log).
- Over the 48 h between first and last CLOSE: 5 / 2 d = **2.5 closes/day** (whole log).
- Per slot over the same 68 h: bollinger_mr 3 / 2.83 d ≈ **1.06/day**; vwap_reversion 2 / 2.83 d ≈ **0.71/day**; btc_4h_rsi_macd **0/day**.

**n = 5 is too small for any of these numbers to be a reliable rate.** Three of the five
closes landed on one timestamp (2026-11-20T12:00Z) and two on another (2026-11-22T12:00Z) —
the observed "rate" is essentially two events, and the whole span is ~3 days. Treat it as a
first hint, not a measurement.

---

## 3. The theoretical maximum rate

Inputs from the sim and the workflow, both verified on main:

- `MAX_POSITIONS_PER_SLOT = 2` (L50), `UNIVERSE` has 3 symbols (L45), `INTERVAL = "4h"`, `BAR_MS = 4h` (L46-47).
- `max_hold_bars`: vwap_reversion **12** (L66), bollinger_mr **10** (L73), btc_4h_rsi_macd **18** (L80).
- Exits are evaluated on every tick ([`exit_check`](../verified_strategies/paper_pilot/crypto_intraday_sim.py:261), L292: `if held_bars >= cfg["max_hold_bars"]: return ("TIME", ...)`), including TP/SL intrabar (L273-277) and close-only stops (L285).
- Cron cadence: `'7,37 * * * *'` in [`.github/workflows/crypto-intraday-sim.yml`](../.github/workflows/crypto-intraday-sim.yml) — 48 ticks/day, but bars only advance every 4 h, so the signal cadence is **6 four-hour bars/day**.
- Entries only on the newest completed bar, only for ACTIVE slots (L404-405), max 2 positions per slot (L409).

Ceiling per slot, if every slot closed at its earliest possible bar (TIME exit) with 2 positions
per slot held continuously:

- vwap_reversion: 2 positions × (6 bars/day ÷ 12 bars hold) = **1.0 close/day**
- bollinger_mr: 2 × (6 ÷ 10) = **1.2 close/day**
- btc_4h_rsi_macd: 2 × (6 ÷ 18) = **0.67 close/day**
- Absolute hard ceiling if TP/SL fired immediately on entry: 2 × 6 = **12 close/day per slot** (entries limited to one per symbol per bar).

So the structural maximum for the pod is **≈2.9 TIME closes/day across the three slots
(≈0.67–1.2 per slot)**, and the absolute-if-always-instant ceiling is 12/day/slot.
Compare with the empirical 1.8–2.5/day whole-log: the log is running close to the
structural TIME-exit ceiling already, which is the honest way to read it.

---

## 4. Projections (extrapolations from n=5, weak)

Days remaining from 2026-11-23T03:06Z: **25.9 d to the day-30 gate (2026-12-19)**,
**55.9 d to the day-60 gate (2027-01-18)**.

### Per-slot (the unit that matters for `MIN_N_BEFORE_JUDGMENT = 20`)

| Slot | n now | Empirical rate | Theoretical max | n=20 expected | n=20 at max | n=100 expected | n=100 at max |
|------|-------|----------------|-----------------|---------------|-------------|----------------|--------------|
| vwap_reversion | 2 | 0.71/day (2 in 2.83d) | 1.0/day, **now HALTED → 0** | ~25 d (if unhalted) | ~18 d | ~138 d | ~98 d |
| bollinger_mr | 3 | 1.06/day | 1.2/day | ~16 d | ~14 d | ~92 d | ~81 d |
| btc_4h_rsi_macd | 0 | 0/day (no closes yet) | 0.67/day | ∞ empirically / ~30 d at max | ~30 d | ~150 d at max |

Ranges: n=20 per slot is projected at **~14–30 days** at the theoretical ceiling and
**~16–25+ days** at the empirical rate for the two slots that have closed anything;
n=100 per slot at **~81–150 days** on the ceiling. These are extrapolations from 5
observations over 3 days; the confidence interval on the rate is effectively unbounded.

### Whole-log (for reference only, NOT what the code counts)

At 1.8–2.5 closes/day: n=20 would come at ~8–11 d (2026-12-01 to 2026-12-04) and
n=100 at ~40–55 d (2027-01-02 to 2027-01-17). These figures are exactly the ones that
*mislead*: they look like comfortable YES answers, but they are irrelevant because
the code judges per slot.

---

## 5. Blunt verdicts

**Can the pilot reach n≥20 before the day-30 gate, per slot? MARGINAL.**
- bollinger_mr: YES-ish (16-14 d at observed/ceiling → ~2026-12-07 to 12-09, before 12-19), but only if entries keep firing.
- btc_4h_rsi_macd: MARGINAL/NO at the empirical rate (0 closes so far, first positions opened 2026-11-22T20:00Z); at the ceiling it is ~30 d → ~2026-12-23, *after* the day-30 gate.
- vwap_reversion: **NO** as long as it stays HALTED. It has n=2 and a halted slot stops generating closes (entries are skipped for non-ACTIVE slots, L405). It cannot reach 20.

**Can the pilot reach n≥100 before the day-60 gate, per slot? NO for vwap_reversion, MARGINAL for the others.**
- vwap_reversion: NO (halted, n frozen at 2).
- bollinger_mr: ~81–92 d to n=100 vs 55.9 d remaining → NO unless the rate roughly doubles.
- btc_4h_rsi_macd: ~150 d at the ceiling vs 55.9 d remaining → NO at the ceiling; only a much higher close rate (instant TP/SL, up to 12/day) would fit.

If n≥100 is read as the whole-pod forward gate (100 rows on one hypothesis id, as the
docstring and audit3 say) the answer is NO as well: the best hypothesis has 3 forward rows
today, and the ceiling of ~2.9 closes/day across all slots gives ~160 closes by day-60 in the
absolute best case, but split across three hypothesis ids no single one would accumulate 100.

---

## 6. Halt state

From the committed state file (main), `guardrails.vwap_reversion`:
`"status": "HALTED", "reason": "trailing drawdown 11.5% > 10.0%", "max_dd_pct": 11.5229,
"cum_pnl_pct": -11.5229, "n_closed": 2`. The threshold is `TRAILING_DD_HALT_PCT = 10.0`
(L51), checked at L318 (`if dd > TRAILING_DD_HALT_PCT`). **Verified: 11.5229% > 10.0%**, over by 1.52 pp.
The other two slots are ACTIVE (bollinger_mr dd 4.08%, btc_4h_rsi_macd dd 0).

A halted slot is not resurrected by the code: status is recomputed from the same closed
trades each tick, so it stays HALTED until a human clears it ("manual review", L19). Since
it cannot open new positions while halted, **its n can never grow and it can never reach n≥20**
without operator action.

---

## 7. What this means

The pilot cannot graduate on its current close rate within the gate windows: at least one slot
(vwap_reversion) is structurally frozen at n=2, one (btc_4h_rsi_macd) cannot reach n=20 before
day-30 even at its theoretical ceiling, and none can reach n≥100 before day-60 without roughly
doubling-to-tripling its rate. Whatever is measured on 2026-12-19 will therefore be underpowered.
A judgement made on underpowered data is worse than no judgement: it is a number that looks
decisive and is not.

**The one thing that makes the picture better:** the theoretical ceiling is high per bar.
A slot can close a position in 10-18 bars = 40-72 h, and with TP/SL intrabar checks a
position can close within a single 4 h bar. The structural capacity is ≈2.9 TIME closes/day,
so the thin empirical record is plausibly a start-up artefact (the sim only began firing
entries on 2026-11-19 and btc_4h_rsi_macd only got its first entries on 2026-11-22) rather than
a structural ceiling. That does not change the verdict for vwap_reversion (halted) or for the
n≥100/day-60 question, but it is why n≥20 for bollinger_mr is a plausible YES.

---

## 8. What I am NOT doing

I am not changing `max_hold_bars`, not adding slots, not extending the gate, and not
clearing the vwap_reversion halt. Those are the operator's decisions. This document is
diagnosis only; no code, workflow, log or artifact in the pilot was modified.
