<!--
    Pull-request template. Delete sections that don't apply.
    Keep this template short — the signal:noise ratio matters.
-->

## Summary

<!-- 1-3 bullets on what changes and why -->

## Type

- [ ] **Bug fix** — concrete production issue with repro steps
- [ ] **Feature** — new capability wired into a production caller
- [ ] **Docs / analysis** — markdown only, no code
- [ ] **Opt-in sidecar** — module exists but no production caller yet (requires `## Wiring Plan` section below)
- [ ] **Refactor** — no behavior change

## Wire-up check (required for integration modules)

If this PR adds a file matching any of these patterns, fill in the section below OR check "Opt-in sidecar" above:

- `alpha_engine/*_integration.py`, `alpha_engine/*_agent.py`, `alpha_engine/fingpt_*.py`
- `tools/*_bridge.py`, `tools/*_integration.py`
- Any file importing `mlfinlab`, `skfolio`, `skforecast`, `flaml`, `pyod`, `interpret`, `feature_engine`, `imbalanced-learn`, `vectorbt`, `bt`, `finrl`, `fingpt`

**Production caller(s) added in this PR:**

<!-- paste `grep -rln "<new_module>" audit_trail/ alpha_engine/ tools/` output, OR list the files you modified that now import the new module -->

```
(grep output here)
```

## Wiring Plan (required if "Opt-in sidecar")

- **Target caller file**: `audit_trail/...` or `alpha_engine/...`
- **Target function**: `calculate_smart_score` / `passes_active_gate` / etc.
- **Wire-up PR**: `#____` (future) or target date
- **Shadow-period validation plan**: how you'll measure impact before enforce

## Test plan

- [ ] Unit tests added (`tests/test_*.py`)
- [ ] `pytest tests/` runs clean
- [ ] If touching production gates: shadow-mode first, with env flag gating

## Data caveats

- [ ] This PR does NOT validate against `audit_trail/data/dashboard_payload.json` without acknowledging the FLAT_CLOSE_BUG (20% non-crypto pollution, see `feedback_noncrypto_resolver_live_close_bug.md`)
- [ ] Claims of "PF uplift" / "+X WR" cite the specific dataset + window, NOT just self-reported confidence

## References

- [ ] Closes #___
- [ ] Related memory note: `feedback_*.md` / `reference_*.md`
- [ ] Project governance: `CLAUDE.md` → Wire-Up Rule

<!--
  Reviewer notes:
  - Breadth-only integration PRs ("module imports + tests pass") get closed with a pointer here.
  - See `reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md` for why this rule exists (20/21 orphan rate, zero production impact).
-->
