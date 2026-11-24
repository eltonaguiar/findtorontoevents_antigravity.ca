# Audit Quant Fixes — Round 3 (2026-11-16)

Seat: `inbox/gx10-c9b9/auditpage-v2/glyph-cluster` (worktree `auditpage-v2`)
Branch: `fix/audit-quant-fixes-round3-2026-11-16`
Follow-up to: `docs/audit-quant-review-2026-11-16/FINDINGS.md` (#849), round 1 (#853), round 2 (#858).

## Fixes

### 1. Impossible-probability guard in cross-market consensus

`prediction_market_agents/cross_market_consensus.py::_extract_signals` normalized
`confidence > 1` by `/100` but never rejected values that were still impossible
after normalization (e.g. `500 -> 5.0`) or negative. Such a feed would skew the
weighted long/short consensus. Now any `confidence` outside `[0, 1]` is dropped
with a warning.

### 2. Walk-forward OOS gate required only a ratio

`alpha_engine/money_ready_verdict.py::_simple_wf_oos_ratio` set `ok = ratio >= 0.85`.
That passes when **both** in-sample and out-of-sample PF are below 1 (e.g. IS 0.5 /
OOS 0.45). Now `ok` also requires `oos_pf >= 1.0`, i.e. the out-of-sample leg must
actually be profitable, not merely "not much worse". Field remains shadow /
informational (does not change the verdict).

## Files edited

| Path | Change |
|---|---|
| `prediction_market_agents/cross_market_consensus.py` | drop `confidence` outside `[0, 1]` (impossible odds) |
| `alpha_engine/money_ready_verdict.py` | `_simple_wf_oos_ratio`: also require `oos_pf >= 1.0` |

## Files added

| Path | Purpose |
|---|---|
| `tests/test_cross_market_consensus_guards.py` | 5 tests: valid kept, `%` normalized, negative dropped, impossible dropped, boundaries kept |
| `tests/test_wf_oos_gate.py` | 4 tests: n<30 None, both-unprofitable False, profitable+good-ratio True, poor-ratio False |
| `updates/2026-11-16-audit-quant-fixes-round3.md` | this document |

## Verification

- `pytest tests/test_wf_oos_gate.py tests/test_cross_market_consensus_guards.py tests/test_money_ready_net_pnl_failsafe.py` → **12 passed**.
- Net-of-cost PF note: with symmetric gross wins/losses the net PF is ~0.92, which
  is exactly why the OOS gate now requires `>= 1.0` rather than assuming a 1:1
  gross PF is profitable.

## Investigated and intentionally not changed

- **Kalshi path split**: not a defect. `audit_trail/universal_pick_resolver.py`
  registers both `prediction_market_agents/data/kalshi_signals.json`
  (`pm_kalshi_signals`) and `alpha_engine/data/kalshi_signals.json`
  (`pm_kalshi_re_signals`), and `audit_trail/dashboard_generator.py` registers
  `pm_kalshi_re_signals`. The files are runtime-generated / gitignored, which is
  why they are absent from a fresh clone.
- **`record_resolution` wiring**: `SignalQualityTracker.record_resolution`
  needs market-level fields (`market_id`, `predicted_prob`, `actual_outcome`) that
  the pick resolver does not carry; wiring it requires a market→pick mapping that
  does not exist yet. Left as a remaining item.

## Remaining

- `record_resolution` wiring (Brier/ECE) with a market→pick mapping.
- Circuit-breaker `_flatten_all_positions` stub; `PortfolioKellyVaR` hot path;
  walk-forward embargo; PBO/n_eff; P2 sizing/ML guards.
