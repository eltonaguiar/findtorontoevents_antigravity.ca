# Master Paper-Pilot Harness

**Owner:** alpha-engine peer fleet  
**Source:** `/tmp/strategy_builds_2026-05-31/master_paper_pilot_harness.py`  
**Cron:** `.github/workflows/paper-pilot-daily.yml` — `30 13 * * *` UTC  
**Status JSON:** `reports/peer_claude-master_paper_pilot_status_<YYYY-MM-DD>.json`

## What it is

A single orchestrator that runs the 7 cursor-statistical-framework paper
pilots built on 2026-05-31. Each strategy keeps its own sidecar JSON of
picks and trades — **no writes to `trading_picks` or any `ejaguiar1_*`
DB** (M-107 / cursor framework rules). The master harness:

1. Imports each strategy's `paper_pilot_harness.py`.
2. Gates by cadence (daily vs. monthly month-end-weekday).
3. Invokes the strategy's `run_once()` / `tick()` / `main()` entrypoint.
4. Re-aggregates picks → applies the cursor statistical gates uniformly.
5. Writes an aggregate status JSON to `reports/`.
6. Commits and uploads the status JSON.

## Strategies integrated (7)

| Strategy           | Asset class    | Cadence  | Sidecar                                                  |
|--------------------|----------------|----------|----------------------------------------------------------|
| `connors_rsi2`     | CRYPTO + EQUITY| daily    | `connors_rsi2/paper_state.json`                          |
| `faber_tactical`   | MULTI          | monthly  | `faber_tactical/faber_paper_ledger.json`                 |
| `fx_carry`         | FOREX          | monthly  | `fx_carry/paper_picks/fx_carry_paper_picks.json`         |
| `magic_formula`    | EQUITY         | monthly  | `magic_formula/paper_state.json`                         |
| `piotroski`        | EQUITY         | monthly  | `piotroski/paper_state.json`                             |
| `post_ipo_drift`   | EQUITY         | daily    | `post_ipo_drift/state/`                                  |
| `tsmom`            | MULTI          | monthly  | `tsmom/tsmom_trades.json`                                |

Monthly strategies are gated to the last weekday of the calendar month
(`is_month_end()`), so the daily cron does not over-trade them.

## Cursor statistical framework (enforced uniformly)

| Knob                       | Value                                                  |
|----------------------------|--------------------------------------------------------|
| Wilson CI                  | lower-bound at 95% (z = 1.96)                          |
| Bootstrap PF CI            | 1000 resamples, 95% interval, seed 17                  |
| Family-wise alpha          | 0.05                                                   |
| Bonferroni per-test alpha  | `0.05 / 7 = 0.007142857`                              |
| Graduation n-floor         | `n_closed >= 500`                                      |
| Significance test          | one-sided exact binomial vs break-even WR              |

### Promotion gates (all four must pass to graduate)

1. `n_closed >= 500`
2. `wilson_lb_wr > break_even_wr` (break-even derived from observed
   avg-win / avg-loss)
3. `pf_ci_lo > 1.0` (bootstrap PF 95% lower-bound clears 1.0)
4. `p_value < 0.007142857` (Bonferroni-adjusted significance)

Until all four pass, `status = "paper_pilot"`. When all four pass,
`status = "graduated"` — and only then is the strategy eligible for
live-money sizing review.

## Operations

### Manual run

```bash
# Run everything that's due today.
python /tmp/strategy_builds_2026-05-31/master_paper_pilot_harness.py

# Re-aggregate stats only (no strategy invocation).
python master_paper_pilot_harness.py --status

# Force-run all 7 ignoring cadence (useful for backfill).
python master_paper_pilot_harness.py --force

# One strategy only.
python master_paper_pilot_harness.py --strategy connors_rsi2
```

### CI

The `paper-pilot-daily` workflow runs at 13:30 UTC. On `workflow_dispatch`
you can override:

- `force` — `true` to bypass cadence gate
- `strategy` — name of a single strategy to run

The workflow:

1. Stages the strategy build artifacts from `tools/strategy_builds_2026-05-31/`
   (if present in the repo) to `/tmp/strategy_builds_2026-05-31/`. If the
   tools-mirror is absent, the run continues with whatever sidecar state
   already exists at the `/tmp/` path on the runner.
2. Runs the master harness.
3. Commits the per-day status JSON to `main`.
4. Uploads the status JSON as a 30-day artifact.

### Output schema (status JSON)

```json
{
  "as_of": "2026-05-31",
  "framework": {
    "wilson_z": 1.96,
    "bootstrap_resamples": 1000,
    "bonferroni_family_alpha": 0.05,
    "bonferroni_per_test_alpha": 0.00714285,
    "n_strategies": 7,
    "graduation_n_floor": 500
  },
  "strategies": {
    "connors_rsi2": {
      "n_closed": 0,
      "wins": 0,
      "win_rate": null,
      "wilson_lb_95": null,
      "pf": 0.0,
      "pf_ci_95": [0.0, 0.0],
      "p_value": 1.0,
      "gates": {
        "n_floor_500": false,
        "wilson_lb_wr_gt_be": false,
        "pf_ci_lo_gt_1": false,
        "p_bonferroni": false
      },
      "status": "paper_pilot"
    }
  },
  "summary": {
    "n_strategies": 7,
    "n_graduated": 0,
    "total_picks_tracked": 0
  }
}
```

## Design rules (do NOT relax without authorization)

1. **No DB writes.** Picks live in JSON sidecars. The cursor framework
   exists specifically because `trading_picks` is a known contamination
   surface (M-067 / M-107 policy-clean cohort doc).
2. **Cadence respect.** Monthly strategies do not run on non-month-end
   days. Daily-cron mis-runs of monthly strategies inflate the
   trade count and violate the n-floor's epistemic meaning.
3. **Bonferroni stays at 7.** If you add an 8th strategy, the alpha
   drops to `0.05 / 8`. Don't lower the family alpha to compensate —
   accept the stricter per-test bar.
4. **Graduation is multi-gate.** Never promote on a single metric
   crossing. All four gates required, simultaneously, for >=1 status
   snapshot before any live-money discussion.
5. **Failures are non-fatal.** One broken strategy module never blocks
   the others. The master traps exceptions and reports them in
   `run_log` rather than aborting the cycle.

## Related docs

- `docs/AGENT_QUICKSTART_AUDIT_AND_STRATEGIES.md` — repo tour
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — mutate-before-kill rule
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — kill-list governance
- `reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md` — origin of the
  Wire-Up Rule (every module needs a caller)
