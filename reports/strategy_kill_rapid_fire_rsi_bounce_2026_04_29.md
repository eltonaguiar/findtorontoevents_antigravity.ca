# Strategy kill investigation: rapid_fire x rsi_bounce

**Date:** 2026-04-29
**Author:** Claude Opus 4.7 (orchestrator subagent)
**Decision:** SURGICAL KILL (Stage-5 hard block, composite-pair scope)
**Composite ID:** `(source_system="rapid_fire", strategy="rsi_bounce")`
**Driving evidence:** Phase 2-A CRYPTO panel 8/8 unanimous "kill / quarantine
rapid_fire source" (Accepted) — `reports/HFPA_PHASE-2-findings-CRYPTO-2026-04-29.md`
**Sibling kill (precedent):** PR #509 — `("rapid_fire", "macd_rsi_confluence")`
(commit `d9a9a3a6e2`) — `reports/strategy_kill_rapid_fire_macd_rsi_confluence_2026_04_29.md`

## 1. Composite identification

- **source_system:** `rapid_fire`
- **strategy:** `rsi_bounce`
- This is one of two remaining `rapid_fire` strategy composites visible in
  the closed ledger after PR #509 retired `(rapid_fire, macd_rsi_confluence)`.

## 2. Closed-pick evidence (dashboard data, 2026-04-29 snapshot)

Reproducer (run from repo root):

```bash
python -c "
import json
with open('audit_dashboard/data/dashboard_data.json') as f: d = json.load(f)
closed = d['picks']['recent_closed']
matches = [p for p in closed if p.get('source_system')=='rapid_fire' and 'rsi_bounce' in str(p.get('strategy',''))]
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
| n (closed) | **23** |
| trust_tier=BANNED | 23 / 23 = **100%** |
| Win rate | 47.8% |
| Sum pnl_pct | **-11.37%** |
| Avg pnl_pct | -0.494% / trade |
| Asset class | 100% CRYPTO |
| Direction | 100% LONG (0 SHORT) |
| Timeframe | 100% null |

n=23 sits below the n>=30 candidate threshold from the master plan, but the
trend is consistent with the parent `rapid_fire` source's full 30d window:

| Source | n_30d (excl holdout) | WR | PF | sum |
|---|---:|---:|---:|---:|
| rapid_fire | 155 | 38.71% | **0.736** | **-58.67%** |

This is the single largest negative-EV CRYPTO source in the Phase 2-A
frozen packet (`reports/HFPA_PHASE-2-CRYPTO-frozen-packet-2026-04-29.json`,
`bottom_sources_30d_excl_holdout`).

## 3. Three-axis mutation autopsy (per docs/MUTATION_THREE_AXIS_PROTOCOL.md)

### Axis 1 — Direction

| Direction | n | WR | sum pnl_pct | avg |
|---|---:|---:|---:|---:|
| LONG | **23** | 47.8% | -11.37% | -0.494% |
| SHORT | 0 | n/a | n/a | n/a |

**Verdict:** No SHORT data exists. Inverse-mutation is not viable from
realized data. Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` Step 3 "Inverse
protocol", flipping requires economic-story validation + SANDBOX trust
until forward sample. No signal to test against; building an inverse from
a purely-LONG broken signal is speculation, not evidence-based.

### Axis 2 — Symbol

Top symbols (per dashboard snapshot):

| Symbol | n | WR | sum pnl_pct |
|---|---:|---:|---:|
| XAUTUSDT | 3 | 33.3% | -0.27% |
| AVAXUSDT | 2 | 100.0% | +3.54% |
| XRPUSDT | 2 | 0.0% | -0.06% |
| STOUSDT | 2 | 0.0% | -5.53% |
| ZBTUSDT | 1 | 0.0% | -12.29% |
| ORCAUSDT | 1 | 0.0% | -6.14% |
| ZECUSDT | 1 | 100.0% | +0.63% |
| TAOUSDT | 1 | 0.0% | -0.28% |
| LINKUSDT | 1 | 100.0% | +1.39% |
| ETHUSDT | 1 | 100.0% | +1.62% |
| SOLUSDT | 1 | 100.0% | +0.24% |
| API3USDT | 1 | 0.0% | -4.62% |
| BTCUSDT | 1 | 0.0% | -0.36% |
| UNIUSDT | 1 | 100.0% | +0.28% |
| HBARUSDT | 1 | 100.0% | +3.17% |
| HIGHUSDT | 1 | 100.0% | +11.15% |
| PORTALUSDT | 1 | 100.0% | +7.32% |
| BOMEUSDT | 1 | 0.0% | -11.16% |

**Verdict:** All symbols n<=3. The 100%-WR cohorts (AVAXUSDT, ZECUSDT,
LINKUSDT, ETHUSDT, SOLUSDT, UNIUSDT, HBARUSDT, HIGHUSDT, PORTALUSDT) are
all n=1-2 — fail Bonferroni cleanly. The single biggest single-trade win
(HIGHUSDT +11.15%) is paired with single-trade losses of similar magnitude
(ZBTUSDT -12.29%, BOMEUSDT -11.16%). Per
`docs/MUTATION_THREE_AXIS_PROTOCOL.md` Step 5 (Mutation quality score):
winning subset must be >=10% of total trades **with stable sample size**.
n=1-2 is not stable. NOT VIABLE.

### Axis 3 — Timeframe

| Timeframe | n |
|---|---:|
| (null) | 23 |

**Verdict:** No timeframe metadata exists. TF-axis mutation is impossible.
NOT VIABLE.

## 4. Why mutation isn't viable (synthesis)

All three mutation axes are blocked, identical structural pattern to PR #509:

1. **Direction:** No SHORT evidence (0 picks). Inverse is speculation.
2. **Symbol:** All symbol cohorts are n<=3. No n>=10 cohort with stable
   WR>55% exists; the 100% WR cohorts are n=1-2 cherry-picks that fail
   Bonferroni.
3. **Timeframe:** No TF labels recorded. Cannot gate.

Per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` ladder, this composite has
exhausted Stage 0-4 and arrives at Stage 5 (Hard block) by default — there
is no evidence base on which to attempt rehab.

## 5. Decision: surgical composite kill

Block `(source_system="rapid_fire", strategy="rsi_bounce")` via
`alpha_engine/strategy_blocklist.py::_RETIRED_SYSTEM_STRATEGY_PAIRS`. Use
the composite-pair scope (not strategy-wide) because:

- Other emitters of `rsi_bounce` (e.g. `alpha_engine`) may have different
  distributional behaviour and are not in scope of this finding.
- Other `rapid_fire` strategies (e.g. `macd_crossover`) are not in scope
  of this finding and should not be inadvertently caught.

This matches the precedent set by:

- `("kimi_signal_tracking", "default")` — added 2026-04-19 (the FOREX bleed kill).
- `("copy_trader_intel", "copy_hl_lb_None")` — added 2026-04-20.
- `("alpha_engine", "copy_hl_lb_None")` — added 2026-04-20.
- `("rapid_fire", "macd_rsi_confluence")` — added 2026-04-29 (PR #509, sibling kill).

## 6. Expected impact

- **Stops the second of two remaining toxic `rapid_fire` composites** at
  the feed layer (`feed_hygiene.is_valid_active_pick` rejects on
  `strategy_blocklist.is_blocked_pick`). Combined with PR #509, this
  removes the entire visible-emitter set of the parent `rapid_fire` source
  per the closed ledger.
- **No effect on live `picks.active`** at time of kill — composite has 0
  active picks per the dashboard snapshot. The kill prevents future
  re-emission.
- **No effect on other rapid_fire strategies** (e.g. `macd_crossover`).
- **No effect on `rsi_bounce` from other systems** (composite-scoped).
- **Phase 2-A panel reading:** the 8/8 "kill rapid_fire" recommendation
  becomes operationally complete with this PR (rapid_fire's two visible
  composites are now both retired).

## 7. Rollback

Set environment variable `RAPID_FIRE_RSI_BOUNCE_KILL_DISABLED=1` to
re-enable emission for the composite. Default is unset (= kill active).
Recognised truthy values: `1`, `true`, `yes`, `on` (case-insensitive). All
other values keep the kill active.

Rollback is plumbed through:

- `alpha_engine/strategy_blocklist.py::_rapid_fire_rsi_bounce_kill_active()`
- `alpha_engine/strategy_blocklist.py::_pair_is_blocked()`

The two surgical kills (`rapid_fire×macd_rsi_confluence` and
`rapid_fire×rsi_bounce`) have **independent rollback flags** so an operator
can re-enable one without re-enabling the other (a regression test pins
this independence).

Both `is_blocked_pick()` and `pick_block_reason()` route through
`_pair_is_blocked()` so the rollback flag covers the entire surface.

Test coverage:

- `tests/test_strategy_blocklist_rapid_fire_rsi_bounce.py`
  - Pins composite membership.
  - Confirms default-blocked behaviour + retired-composite reason string.
  - Confirms env-flag rollback path (1/true/yes/on bypass; falsy keeps kill).
  - Confirms scope isolation (other strategies / other systems unaffected).
  - Confirms per-pair rollback independence vs the macd_rsi_confluence kill.

## 8. Reversal conditions (if/when to re-enable)

Re-enable only after **all** of:

1. New evidence base (>=30 closed picks) from a forward-test sandbox under
   the same composite, with WR >= 50% and sum pnl_pct > 0.
2. Documented hypothesis why the prior 23-pick negative edge has reversed
   (regime shift, source-emitter fix, etc.).
3. Per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` review-feedback
   section (Cursor 2026-04-19 #4): record **why** the block was removed in
   this MD so the same mistake isn't re-merged via Copilot.

## 9. References

- Phase 2-A CRYPTO synthesis: `reports/HFPA_PHASE-2-findings-CRYPTO-2026-04-29.md`
- Phase 2-A frozen packet: `reports/HFPA_PHASE-2-CRYPTO-frozen-packet-2026-04-29.json`
- Sibling kill (PR #509): `reports/strategy_kill_rapid_fire_macd_rsi_confluence_2026_04_29.md`
- Investigation protocol: `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
- Mutation protocol: `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- Blocklist module: `alpha_engine/strategy_blocklist.py`
- Test pin: `tests/test_strategy_blocklist_rapid_fire_rsi_bounce.py`
