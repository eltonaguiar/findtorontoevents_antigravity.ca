# Goal #1 Wave 2 — Strict Smart-Gate Wiring + Safety Test Coverage (2026-04-28)

Progress checkpoint covering the past hour. Wave 2 of the integration work for **MAJOR GOAL #1** (phenomenal hedge-fund-grade performance across asset classes on `/audit`).

**Status:** code + tests done in clean worktree `feat/goal1-wave2-strict-gate-2026-04-28` off `origin/main@dc6f953b35`. Two real source bugs surfaced (out of scope for this PR). PR / CI / deploy / Playwright still pending — see "Next" at the bottom.

## Scope (this PR)

| # | Change | File | Behavior when off |
|---|---|---|---|
| 1 | Wire `audit_trail/hf_strict_smart_gate.strict_smart_gate_fail_reason` into `audit_trail/quality_gates.passes_smart_gate` behind env flag `HF_AUDIT_SMART_STRICT=1` | `audit_trail/quality_gates.py` (final block before `return True`) | No-op. Flag unset/`"0"` skips the helper entirely. Helper exception is also swallowed (double fail-safe). |
| 2 | New strict on/off/exception tests | `tests/test_quality_gates.py` (3 tests appended) | n/a (test-only) |
| 3 | DSR-missing legacy-promotion tests | `tests/test_stamp_pick_quality_dsr_gate.py` (4 tests appended) | n/a (test-only) |
| 4 | Hyro import-failure + invalid `KELLY_DD_HALT_MAX` env tests | `tests/test_kelly_dd_halt.py` (4 tests appended) | n/a (test-only) |
| 5 | Empty / malformed payload tests for the freshness report | `tests/test_asset_class_freshness_report.py` (4 tests appended) | n/a (test-only) |

**Wire-Up Rule check.** The strict-gate wiring satisfies the rule: it adds a caller (`passes_smart_gate`, the canonical Smart-Picks gate) for the previously-orphaned `hf_strict_smart_gate.strict_smart_gate_fail_reason`. Production behavior is unchanged when `HF_AUDIT_SMART_STRICT` is unset (the default).

## Wiring detail

The strict block sits at the very end of `passes_smart_gate`, immediately before the existing `return True`. Lazy import + double-nested try/except keeps module-level import cost zero and ensures any failure in the strict path falls back to the prior verdict (pass).

```python
try:
    if os.environ.get("HF_AUDIT_SMART_STRICT", "") == "1":
        try:
            from audit_trail.hf_strict_smart_gate import (
                strict_smart_gate_fail_reason,
            )
            reason = strict_smart_gate_fail_reason(pick)
            if reason:
                logger.debug(f"Smart gate: strict mode rejected ({reason})")
                return False
        except Exception as exc:  # pragma: no cover — fail-safe
            logger.debug(f"Smart gate: strict helper raised, soft-failing: {exc}")
except Exception as exc:  # pragma: no cover — outer fail-safe
    logger.debug(f"Smart gate: strict env-check raised, soft-failing: {exc}")

return True
```

`os` is already imported at module top, so no new top-level imports were added. The strict helper itself **also** consults `config/hf_audit_smart_strict.json`'s internal `enabled` flag — so the gate is double-gated (env flag AND config flag). Default in the JSON ships as `enabled: false`, matching the env default.

## Test evidence (run from worktree root)

| Command | Result |
|---|---|
| `python -m py_compile audit_trail/quality_gates.py` | OK |
| `python -m pytest tests/test_quality_gates.py -v` | **46 passed** (43 baseline + 3 new) |
| `python -m pytest tests/test_stamp_pick_quality_dsr_gate.py -v` | **6 passed** (2 baseline + 4 new) |
| `python -m pytest tests/test_kelly_dd_halt.py -v` | **9 passed** (5 baseline + 4 new) |
| `python -m pytest tests/test_asset_class_freshness_report.py -v` | **5 passed** (1 baseline + 4 new) |

Combined: **66 tests green, 0 failures.**

## Findings (out of scope for this PR — flagged for follow-up)

Two real source bugs surfaced while subagents were writing the safety tests. Both should ship in a separate, narrowly-scoped PR (Wave 2.1) with their own regression tests; pinning them here would mask the bug.

### Bug 1 — PEAD payload type guard

`alpha_engine/vt_baby_strategies.py:354` (`_load_recent_earnings_surprise`):

```python
history = payload.get("history")          # <-- raises AttributeError if payload isn't a dict
```

When the per-symbol cache JSON parses to a top-level string/int/list (corrupted or truncated cache), `payload.get(...)` raises `AttributeError`, and the outer caller `vt_equity_earnings_drift_pead` does **not** wrap this call in try/except (only the downstream `strat.generate_signals(...)` is guarded).

Empirical confirmation: write `"a string"` to a tmp `latest.json`, set `UEPS_ENABLE_PEAD=1`, call PEAD → `AttributeError 'str' object has no attribute 'get'`.

Recommended 2-line fix:

```python
if not isinstance(payload, dict):
    return None
history = payload.get("history")
```

Once the guard lands, the three malformed-cache tests originally requested for `tests/test_vt_baby_strategies_pead.py` (missing file, invalid JSON, unexpected top-level type) become safe to add.

### Bug 2 — Hyro overlay runtime-exception leak

`alpha_engine/kelly_position_sizer.py` (`_apply_hyro_risk_sizer`):

- Lines 181–184: lazy IMPORT `from tools.hyrotrader_risk_sizer import size_pick` is wrapped in try/except → returns legacy `sized_usd` on `ImportError`. Good.
- Lines 190–198: the `size_pick(...)` CALL itself is **not** wrapped. A runtime exception inside `size_pick` (e.g., bad config, division by zero in an exotic edge case) propagates out of `compute_position_size` and crashes the caller.

The "fail-safe legacy fallback" promise is therefore only half-delivered — import safety yes, runtime safety no. Recommended fix is to wrap lines 190–205 in `try: ... except Exception: return sized_usd`. Once that lands, a `test_hyro_overlay_falls_back_to_legacy_size_on_runtime_exception` test mirrors the existing import-failure test cleanly.

Both bugs have been flagged to peer `fd0uag0p` (Goal #1 sprint orchestrator) for triage — they may roll into the next post-merge cycle or a dedicated Wave 2.1 PR.

## Projected benefits by asset class (PROJECTED — not realized)

> All numbers below are projections of the strict gate's expected effect when operators enable `HF_AUDIT_SMART_STRICT=1` AND set `enabled: true` in `config/hf_audit_smart_strict.json`. Default behavior with both flags off ships **zero** behavior change. Realized impact will be measured on the next 2026-04-28 → 2026-05-05 forward window after operator-toggled rollout.

The strict helper's six rejection codes (`audit_strict_elite`, `audit_strict_rr`, `audit_strict_stale`, `audit_strict_trust`, `audit_strict_mtf`, `audit_strict_macro`) target known Goal #1 leakage sources from `reports/hedge_fund_performance_review_*.md` and the action plan in `audit_trail/hf_strict_smart_gate.py:7`.

| Asset class | Today's pain (per CLAUDE.md MAJOR GOALS + reports) | Strict-gate filter that hits it | Projected effect (when enabled) |
|---|---|---|---|
| **CRYPTO** | Edge real (PF 1.140) but MDD lethal — see `reports/deep_dive_crypto_mdd_reduction_2026_04_28.md`. Default `apply_asset_classes` is `["CRYPTO"]` so this is the primary target. | `audit_strict_elite` (≥80), `audit_strict_rr` (≥1.2), `audit_strict_stale` (≤4h non-copy / ≤24h copy), `audit_strict_trust` (≥WATCH), MTF 2/3 | Trim low-elite + stale-signal + low-trust crypto Smart Picks. Projection: PF ≥1.5 reachable when stacked with vol-targeting fix, narrows the path to Tier 2. |
| **EQUITY** | Tier 2 candidate (PF 1.385). Closest of the asset classes to phenomenal — small leakage trims compound. | `audit_strict_macro` (when snapshot populated) | Projection: blocks SPY/sector-LONG picks during macro red-flag windows once equity is opted into `apply_asset_classes`. Estimated +0.05–0.10 PF on equity Smart-only feed. |
| **FOREX** | Blocked on resolver fix (`alpha_engine/outcome_resolver.py:97` + `:384-405`). 63–67% noise share until that lands. | n/a until resolver fixed; strict gate would compound resolver-cleaned data | Projection: deferred until resolver PR lands. Strict gate helps on resolver-clean data but premature now. |
| **COMMODITY** | Same resolver block as Forex. | n/a until resolver fixed | Deferred. |
| **ETF / BOND / FUTURES** | Lower volume on `/audit`, fewer outliers. | All strict filters apply once these classes are added to `apply_asset_classes`. | Projection: marginal trims, low signal-to-noise impact in the short term. |
| **System-wide (all classes)** | Outer 9/11 Ollama Cloud audit verdict (2026-04-21): "surgical fixes, not rebuild." | Strict mode IS one of those surgical fixes. | Projection: trims 5–15% of Smart Picks per cycle when fully on, biased toward removing the lowest-quality tail. Operator toggle gives blast-radius control. |

**Realized vs projected.** This PR ships the wiring only. The strict-mode flag remains OFF by default — all asset classes see zero behavior change at merge time. Realized impact will be observable only after operator-driven rollout AND a fresh 7-day forward-validated window. Track in `reports/hedge_fund_performance_review_*.md` for the cycle that follows the rollout.

## Next steps (still open)

- [ ] Commit + push `feat/goal1-wave2-strict-gate-2026-04-28`
- [ ] Open PR to `main`, monitor checks to green
- [ ] Merge PR
- [ ] `python tools/deploy_to_ftp.py --updates-only`
- [ ] Verify `https://findtorontoevents.ca/updates/index.html` and `https://findtorontoevents.ca/audit/`
- [ ] Run Playwright validation post-deploy, ignore ad-network 403 noise, report critical JS errors
- [ ] Add evidence row to `updates/index.html` linking to the merged PR + this .md
- [ ] (Wave 2.1, separate PR) Land the two source-bug fixes documented above

## Files in this checkpoint

- `audit_trail/quality_gates.py` — wiring (≈12 lines added at end of `passes_smart_gate`)
- `tests/test_quality_gates.py` — 3 new tests (strict off, strict on rejects, strict on swallows exception)
- `tests/test_stamp_pick_quality_dsr_gate.py` — 4 new tests (DSR missing in 4 shapes)
- `tests/test_kelly_dd_halt.py` — 4 new tests (Hyro import failure + 3 env-validation)
- `tests/test_asset_class_freshness_report.py` — 4 new tests (empty / missing keys / bad JSON / wrong type)
- `updates/2026-04-28-goal1-wave2-strict-gate-wiring.md` — this file

Branch: `feat/goal1-wave2-strict-gate-2026-04-28`
Worktree: `.worktrees/goal1-wave2-strict-gate`
Base: `origin/main@dc6f953b35`
