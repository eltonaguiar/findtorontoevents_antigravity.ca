# Audit Quant Fixes — Round 2 (2026-11-16)

Seat: `inbox/gx10-c9b9/auditpage-v2/glyph-cluster` (worktree `auditpage-v2`)
Branch: `fix/audit-quant-fixes-2026-11-16`
Follow-up to: `docs/audit-quant-review-2026-11-16/FINDINGS.md` (PR #849) and round-1 fixes (PR #853).

## What this round fixes

Two root-cause defects that made prediction-market (PM) picks unreachable, plus the
hard shadow pin that was missing.

### 1. PM picks were rejected at ingest (root cause of "PM wired but 0 picks")

`alpha_engine/feed_hygiene.py::is_valid_active_pick` rejected any pick whose
`strategy == source_system` as "anonymous by convention". PM consensus picks are
produced with `strategy="prediction_market_consensus"` and
`source_system="prediction_market_consensus"`, so **every PM pick was dropped at
ingest** and never reached `active_picks.json` / the dashboard.

Evidence: `prediction_market_agents/orchestrator.py::merge_into_active_picks` logged
`1 picks merged` then `feed_hygiene ... 0 valid, 1 rejected (other=1)` and saved `[]`.

Fix: exempt prediction-market source systems from the self-named-strategy rule. The
rule still applies to non-PM sources, and the retired-strategy blocklist
(`is_blocked_pick`) is still enforced afterwards.

### 2. PM picks had no hard shadow pin

Neither merge path stamped `forward_test_only` / `sizing_allowed=False`. Fix: both
`alpha_engine/prediction_market_consensus.py::merge_into_active_picks` and
`prediction_market_agents/orchestrator.py::merge_into_active_picks` now force
`forward_test_only=True`, `sizing_allowed=False`, `shadow=True`. The consensus path
forces the flags on the merged copy so a producer cannot forget them.

## Files edited

| Path | Change |
|---|---|
| `alpha_engine/feed_hygiene.py` | `is_valid_active_pick`: PM sources exempt from the `strategy == source_system` anonymous rejection |
| `alpha_engine/prediction_market_consensus.py` | `merge_into_active_picks`: force `forward_test_only`/`sizing_allowed=False`/`shadow` on merged picks |
| `prediction_market_agents/orchestrator.py` | pick builder: stamp the same three shadow fields |
| `tests/test_feed_hygiene_additional_fixes.py` | added 2 tests (PM/Polymarket self-named accepted) |
| `tests/test_prediction_market_consensus.py` | added 1 test (merge stamps shadow pin) |

## Files added

| Path | Purpose |
|---|---|
| `tests/test_prediction_market_shadow_pin.py` | asserts the orchestrator merge stamps the hard shadow pin |
| `updates/2026-11-16-audit-quant-fixes-round2.md` | this document |

## Verification

- `tests/test_feed_hygiene_additional_fixes.py` + `test_prediction_market_shadow_pin.py` + `test_prediction_market_consensus.py`: **28 passed**.
- Related suites `test_feed_hygiene_schema.py`, `test_resolver_hygiene_check.py`, `test_commodity_kill_switch.py`, `test_polymarket_momentum_agent.py`: **59 passed**.
- Repro before fix: PM pick with `source_system="prediction_market_consensus"` → `active_picks.json` stays `[]`.
- Repro after fix: same pick is retained and carries `forward_test_only=True`, `sizing_allowed=False`, `shadow=True`.

## Impact

- Display/attribution only; no emitter, resolver, sizing, or workflow changes.
- Non-PM picks are unaffected (self-named rejection still applies; blocklist still runs).
- PM picks that were previously dropped will now appear in `active_picks.json` as
  shadow/paper rows. They remain unsized (`sizing_allowed=False`) and are expected to
  show `0t` closed until the forward tracker resolves them.

## Remaining (not in this PR)

- `SignalQualityTracker.record_resolution` wiring into `universal_pick_resolver.py`
  so Brier/ECE are computed on resolved PM picks.
- Kalshi path split (`alpha_engine/data/` vs `prediction_market_agents/data/`) and the
  3 registered-but-missing PM data files.
- Circuit-breaker `_flatten_all_positions` stub; walk-forward embargo; PBO/n_eff;
  `PortfolioKellyVaR` hot-path wiring; P2 sizing/ML/PM guards.
