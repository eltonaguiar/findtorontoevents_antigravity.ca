# Strategy kill investigation: rapid_fire x macd_rsi_confluence

**Date:** 2026-04-29
**Author:** Claude Opus 4.7 (orchestrator)
**Decision:** SURGICAL KILL (Stage-5 hard block, composite-pair scope)
**Composite ID:** `(source_system="rapid_fire", strategy="macd_rsi_confluence")`
**Driving evidence:** `reports/ai_round2_synthesis_2026_04_29.md` (5/5 unanimous P0)

## 1. Composite identification

- **source_system:** `rapid_fire`
- **strategy:** `macd_rsi_confluence`
- Strategy-wide variants observed in closed ledger: only `macd_rsi_confluence` (no `_v2`, no `_inverse`).

## 2. Closed-pick evidence (dashboard data, 2026-04-29 snapshot)

Reproducer (run from repo root):

```bash
python -c "
import json
with open('audit_dashboard/data/dashboard_data.json') as f: d = json.load(f)
closed = d['picks']['recent_closed']
matches = [p for p in closed if p.get('source_system')=='rapid_fire' and 'macd_rsi_confluence' in str(p.get('strategy',''))]
print(f'n={len(matches)}')
banned = sum(1 for p in matches if p.get('trust_tier') == 'BANNED')
print(f'BANNED: {banned}/{len(matches)}')
total_pnl = sum((p.get('pnl_pct') or 0) for p in matches)
wins = sum(1 for p in matches if (p.get('pnl_pct') or 0) > 0)
print(f'WR: {100*wins/max(len(matches),1):.1f}%, sum pnl: {total_pnl:+.2f}%')
"
```

| Metric | Value |
|---|---:|
| n (closed) | **133** |
| trust_tier=BANNED | 133 / 133 = **100%** |
| Win rate | 36.8% |
| Sum pnl_pct | **-48.88%** |
| Avg pnl_pct | -0.367% / trade |
| Asset class | 100% CRYPTO |
| Direction | 100% LONG (0 SHORT) |
| Timeframe | 100% null |

**Share of BANNED-tier closures:** ~39% (per round 2 panel). This single composite is the dominant BANNED leak.

## 3. Three-axis mutation autopsy (per docs/MUTATION_THREE_AXIS_PROTOCOL.md)

### Axis 1 — Direction

| Direction | n | WR | sum pnl_pct | avg |
|---|---:|---:|---:|---:|
| LONG | **133** | 36.8% | -48.88% | -0.367% |
| SHORT | 0 | n/a | n/a | n/a |

**Verdict:** No SHORT data exists. Inverse-mutation is not viable from realized
data. Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` Step 3 "Inverse protocol",
flipping requires **economic-story validation + SANDBOX trust until forward
sample**. There is no signal to test against; building an inverse from a
purely-LONG broken signal is speculative, not evidence-based.

### Axis 2 — Symbol

Top 10 symbols (per dashboard snapshot):

| Symbol | n | WR | sum pnl_pct |
|---|---:|---:|---:|
| XAUTUSDT | 7 | 42.9% | -2.37% |
| XRPUSDT | 6 | 50.0% | -3.17% |
| ORDIUSDT | 5 | 40.0% | +4.81% |
| LINKUSDT | 5 | 40.0% | -2.71% |
| SOLUSDT | 4 | 0.0% | -6.77% |
| LTCUSDT | 4 | 75.0% | +3.48% |
| DOGEUSDT | 4 | 25.0% | -1.16% |
| ZECUSDT | 4 | 75.0% | +6.04% |
| APTUSDT | 4 | 75.0% | +0.73% |
| TAOUSDT | 4 | 75.0% | +3.71% |

**Verdict:** All n <= 7 per symbol. The four "75% WR" symbols are all n=4.
Per round 2 panel statistical caveat, 6-way intersections (and even single
small-n cherry-picks) "do NOT survive Bonferroni." A symbol-allowlist
mutation built on n=4 cohorts is overfit by construction. Per
`docs/MUTATION_THREE_AXIS_PROTOCOL.md` Step 5 (Mutation quality score):
winning subset must be >=10% of total trades **with stable sample size**.
n=4 is not stable.

### Axis 3 — Timeframe

| Timeframe | n |
|---|---:|
| (null) | 133 |

**Verdict:** No timeframe metadata exists. TF-axis mutation is impossible.
Cannot route to a TF bucket that has edge because no TF labels are present.

## 4. Why mutation isn't viable (synthesis)

All three mutation axes are blocked:

1. **Direction:** No SHORT evidence (0 picks). Inverse is speculation.
2. **Symbol:** All symbol cohorts are n<=7. No n>=10 cohort with stable WR>55%
   exists; the 75% WR cohorts are n=4 cherry-picks that fail Bonferroni.
3. **Timeframe:** No TF labels recorded. Cannot gate.

Per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` ladder, this composite has
exhausted Stage 0-4 and arrives at Stage 5 (Hard block) by default — there is
no evidence base on which to attempt rehab.

## 5. Decision: surgical composite kill

Block `(source_system="rapid_fire", strategy="macd_rsi_confluence")` via
`alpha_engine/strategy_blocklist.py::_RETIRED_SYSTEM_STRATEGY_PAIRS`. Use the
composite-pair scope (not strategy-wide) because:

- Other emitters of `macd_rsi_confluence` (e.g. `alpha_engine`) may have
  different distributional behaviour.
- Other `rapid_fire` strategies (e.g. `macd_crossover`) are not in scope of
  this finding and should not be inadvertently caught.

This matches the precedent set by:

- `("kimi_signal_tracking", "default")` — added 2026-04-19 (the FOREX bleed kill).
- `("copy_trader_intel", "copy_hl_lb_None")` — added 2026-04-20 (defense-in-depth).
- `("alpha_engine", "copy_hl_lb_None")` — added 2026-04-20 (defense-in-depth).

## 6. Expected impact

- **Stops 39% of all BANNED-tier closures** at the feed layer
  (`feed_hygiene.is_valid_active_pick` rejects on
  `strategy_blocklist.is_blocked_pick`).
- **No effect on live `picks.active`** at time of kill (this composite has 0
  active picks per the round 2 finding — it is purely a closed-ledger leak
  source). The kill prevents future re-emission.
- **No effect on other rapid_fire strategies** (e.g. `macd_crossover`, which
  has historical SHORT wins).
- **No effect on `macd_rsi_confluence` from other systems** (composite-scoped).

## 7. Rollback

Set environment variable `RAPID_FIRE_MACD_KILL_DISABLED=1` to re-enable
emission for the composite. Default is unset (= kill active). Recognised
truthy values: `1`, `true`, `yes`, `on` (case-insensitive). All other values
keep the kill active.

Rollback is plumbed through:

- `alpha_engine/strategy_blocklist.py::_rapid_fire_macd_kill_active()`
- `alpha_engine/strategy_blocklist.py::_pair_is_blocked()`

Both `is_blocked_pick()` and `pick_block_reason()` route through
`_pair_is_blocked()` so the rollback flag covers the entire surface.

Test coverage:

- `tests/test_strategy_blocklist_rapid_fire_macd.py`
  - Pins composite membership.
  - Confirms default-blocked behaviour.
  - Confirms env-flag rollback path.
  - Confirms falsy values do **not** bypass.
  - Confirms scope isolation (other strategies / systems unaffected).

## 8. Reversal conditions (if/when to re-enable)

Re-enable only after **all** of:

1. New evidence base (>=30 closed picks) from a forward-test sandbox under
   the same composite, with WR >= 50% and sum pnl_pct > 0.
2. Documented hypothesis why the prior 133-pick negative edge has reversed
   (regime shift, source-emitter fix, etc.).
3. Per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` review-feedback section
   (Cursor 2026-04-19 #4): record **why** the block was removed in this MD
   so the same mistake isn't re-merged via Copilot.

## 9. References

- Round 2 synthesis: `reports/ai_round2_synthesis_2026_04_29.md` (P0 #6)
- Investigation protocol: `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
- Mutation protocol: `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- Blocklist module: `alpha_engine/strategy_blocklist.py`
- Test pin: `tests/test_strategy_blocklist_rapid_fire_macd.py`
