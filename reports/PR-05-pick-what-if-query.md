# PR-5: Add Filtered Pick "What-If" Simulation Query

| Field | Value |
|---|---|
| **Branch** | `feat/pick-what-if-query-2026-0518` |
| **Target** | `main` |
| **Class** | ALL (cross-class analytics) |
| **M-Code** | M-110 (pick lifecycle observability) |
| **Status** | New feature |
| **Author** | `quant-dev-5` |
| **Reviewers** | `strat-lead`, `data-platform-lead`, `frontend-lead` |

---

## 1. Problem Statement

### 1.1 Opacity of Filtered Picks
The system rejects ~65% of all generated picks across the 7 asset classes. These rejections are logged in `pick_lifecycle_log` with filter reasons such as:
- `COT_LAG_REJECT` (PR-1, COMMODITY)
- `VIX_REGIME_REJECT` (PR-2, ETF)
- `POST_COST_EXPECTANCY_REJECT` (PR-3, global)
- `ML_VARIANT_QUARANTINED` (PR-4, CRYPTO)
- `FWDWR_GATE_REJECT` (FOREX, existing)
- `CRYPTO_SHORT_REGIME` (existing)

**However, there is no way for strategists, risk managers, or the research team to ask:**
> *"This pick was filtered due to [reason]. But what if it had been allowed? What would its P&L have been?"*

This creates a feedback loop black hole. We cannot:
1. Validate that our gates are not over-filtering (Type II error).
2. Discover that a previously bad variant has improved and should be promoted.
3. Provide empirical evidence to the risk desk when requesting gate threshold adjustments.
4. Run counterfactual A/B tests on gate policies.

### 1.2 Live Data Context
From `pf_registry.json` (2026-05-18T00:27:46Z):

| Class | Generated | Filtered | Filtered % | Top Filter Reason |
|---|---|---|---|---|
| CRYPTO | 5,540 | 3,598 | 64.9% | `ML_VARIANT_QUARANTINED` |
| COMMODITY | 412 | 252 | 61.2% | `COT_POSITIONING_KILL` |
| ETF | 380 | 275 | 72.4% | `VIX_REGIME_REJECT` (after PR-2) |
| FOREX | 1,440 | 1,047 | 72.7% | `FWDWR_GATE_REJECT` |
| BOND | 15 | 14 | 93.3% | `INSUFF_DATA` |
| FUTURES | 89 | 77 | 86.5% | `INSUFF_DATA` |
| **TOTAL** | **7,876** | **5,263** | **66.8%** | — |

Over 5,000 picks per quarter are filtered with no counterfactual tracking. At an average post-cost expectancy of $180 per pick, this represents ~$947K/quarter in unobserved opportunity cost (or waste prevention, if the gates are correct).

### 1.3 Existing Infrastructure
- `pick_lifecycle_log` table exists with columns:
  - `pick_id`, `symbol`, `strategy`, `variant`, `timestamp`, `filter_reason`, `filter_metadata`, `expected_outcome` (null for rejected picks), `actual_outcome` (null for rejected picks)
- `what_if_simulator.py` does **not** exist — this is a greenfield module.
- Historical price data is available in `market_data.ohlcv` with full tick history.

---

## 2. Solution

### 2.1 Core What-If Engine
Create `what_if_simulator.py` with the following architecture:

```python
class WhatIfSimulator:
    def simulate_filtered_pick(self, pick_id: str, override_gates: list[str]) -> WhatIfResult:
        """
        1. Load pick from pick_lifecycle_log.
        2. Replay the pick as if the specified gates had not rejected it.
        3. Compute full P&L path using market_data.ohlcv.
        4. Return WhatIfResult with hypothetical P&L, drawdown, and regime context.
        """
```

**Algorithm:**
1. Fetch pick record from `pick_lifecycle_log`.
2. Verify pick was actually filtered (not executed). If executed, return error.
3. Identify which gate rejected it (from `filter_reason`).
4. If `override_gates` contains that gate (or `"all"`), proceed to simulation.
5. Compute hypothetical entry price at `pick_timestamp` (slippage model applied).
6. Compute exit price based on the strategy's exit rules using historical OHLCV.
7. Calculate gross P&L, net P&L (after costs), max drawdown, and holding period.
8. Return `WhatIfResult` with full path data for charting.

### 2.2 CLI Command
Add `cli/commands/what_if.py`:

```bash
# Single pick simulation
python -m cli what-if simulate --pick-id PICK-2026-0518-004421 \
  --override-gates POST_COST_EXPECTANCY_REJECT,VIX_REGIME_REJECT

# Batch simulation for a class
python -m cli what-if batch --class CRYPTO \
  --filter-reason ML_VARIANT_QUARANTINED \
  --limit 100 \
  --output-format json

# Gate efficacy report
python -m cli what-if efficacy --class ALL --start-date 2026-01-01 --end-date 2026-05-01
```

### 2.3 API Endpoint
Add `api/routes/what_if.py` (FastAPI):

```python
@router.post("/what-if/simulate")
async def simulate_what_if(req: WhatIfRequest) -> WhatIfResponse:
    ...

@router.get("/what-if/efficacy")
async def get_gate_efficacy(
    asset_class: str,
    start_date: date,
    end_date: date,
    filter_reason: str | None = None
) -> GateEfficacyReport:
    ...
```

### 2.4 Gate Efficacy Analytics
The efficacy report computes:

| Metric | Definition |
|---|---|
| `gate_precision` | % of what-if-simulated picks that would have been losers (should be high) |
| `gate_recall` | % of actual losers that the gate caught (should be high) |
| `opportunity_cost` | Sum of P&L from filtered picks that would have been winners |
| `waste_prevented` | Sum of P&L from filtered picks that would have been losers |
| `net_value` | `waste_prevented - opportunity_cost` (positive = gate is valuable) |

This enables data-driven gate threshold tuning.

### 2.5 Integration with pick_lifecycle_log
- Add `what_if_result` JSONB column to `pick_lifecycle_log`.
- When a simulation is run, cache the result for 24 hours.
- Add `what_if_run_count` integer column (increment on each query).

---

## 3. Files Changed

| File | Lines | Change |
|---|---|---|
| `what_if_simulator.py` | +340 | New module: core simulation engine, P&L computation, drawdown tracking |
| `cli/commands/what_if.py` | +198 | New CLI: `simulate`, `batch`, `efficacy` subcommands |
| `api/routes/what_if.py` | +156 | New API: POST `/what-if/simulate`, GET `/what-if/efficacy` |
| `api/models/what_if.py` | +89 | Pydantic models: `WhatIfRequest`, `WhatIfResponse`, `GateEfficacyReport` |
| `pick_lifecycle_log.py` | +31 / -4 | Add `what_if_result` and `what_if_run_count` columns; cache logic |
| `quality_gates.py` | +22 / -3 | Export gate metadata (reason codes, descriptions) for API docs |
| `config/api.yaml` | +14 / -2 | Rate limits: 100 sims/min per user; 1000 batch max |
| `tests/unit/test_what_if_simulator.py` | +267 | New test suite: single sim, batch, caching, slippage, costs |
| `tests/integration/test_what_if_api.py` | +134 | API e2e: endpoints, auth, rate limiting, efficacy report |
| `tests/integration/test_what_if_e2e.py` | +98 | Full pipeline: known filtered pick → sim → compare to actual (if later executed) |
| `alembic/versions/028_add_what_if_columns.py` | +35 | DB migration: `what_if_result` JSONB, `what_if_run_count` int |
| `docs/api/what_if.md` | +88 | API documentation for frontend and external consumers |

---

## 4. Test Plan

### 4.1 Unit Tests (`tests/unit/test_what_if_simulator.py`)

| Test Case | Input | Expected |
|---|---|---|
| `test_simulate_known_filtered_pick` | Pick `PICK-2026-0415-001` filtered for `POST_COST_EXPECTANCY_REJECT` | Returns `WhatIfResult` with computed gross/net P&L |
| `test_simulate_requires_override_match` | Pick filtered for `VIX_REGIME_REJECT`, override only `POST_COST_EXPECTANCY_REJECT` | Error: gate mismatch |
| `test_simulate_with_slippage` | Same pick, slippage model enabled | Entry/exit prices differ from mid by slippage estimate |
| `test_simulate_with_costs` | Same pick, costs enabled | Net P&L < gross P&L by commission + market impact |
| `test_batch_simulation` | 50 CRYPTO picks filtered for `ML_VARIANT_QUARANTINED` | Returns list of 50 `WhatIfResult` with aggregate PF |
| `test_cache_hit` | Re-simulate same pick_id within 24h | Returns cached result; `what_if_run_count` increments |
| `test_cache_miss_after_ttl` | Re-simulate after 24h | Recomputes; old cache invalidated |
| `test_efficiency_report` | 100 filtered picks, 30 would-be winners, 70 would-be losers | `gate_precision=70%`, `waste_prevented` = sum(70 losers), `opportunity_cost` = sum(30 winners) |
| `test_invalid_pick_id` | Non-existent pick_id | 404 error |
| `test_already_executed_pick` | Pick that was actually executed | 400 error: "Pick was not filtered" |

### 4.2 Integration Tests (`tests/integration/test_what_if_api.py`)
- Test authenticated API access (401 without token, 200 with token).
- Test rate limiting: 101st request within 60s returns 429.
- Test `POST /what-if/simulate` with valid pick_id returns 200 and correct schema.
- Test `GET /what-if/efficacy` returns report with all required fields.
- Test batch endpoint with `limit=1000` passes, `limit=1001` returns 400.

### 4.3 Integration Tests (`tests/integration/test_what_if_e2e.py`)
- Identify 10 picks that were filtered in Jan 2026 but whose signals later resolved (market moved).
- Run what-if simulation.
- Compare simulated P&L against the actual market movement that occurred.
- Assert correlation > 0.85 between simulated and actual outcomes.

### 4.4 Manual / QA
- [ ] Run `python -m cli what-if efficacy --class CRYPTO --start-date 2026-01-01 --end-date 2026-05-01` and verify output.
- [ ] Hit API endpoint via Swagger UI; confirm response schema matches docs.
- [ ] Verify `what_if_result` is cached in DB and `what_if_run_count` increments.
- [ ] Confirm rate limiting works (use `ab -n 150 -c 10` against `/what-if/simulate`).

---

## 5. Acceptance Criteria

- [ ] `what_if_simulator.py` exists and can simulate any filtered pick from `pick_lifecycle_log`.
- [ ] CLI commands `what-if simulate`, `what-if batch`, and `what-if efficacy` work and produce correct output.
- [ ] API endpoints return correct JSON schema with 200/400/404/429 status codes.
- [ ] Simulation includes slippage, commission, and market impact (configurable on/off).
- [ ] `gate_precision` and `gate_recall` are computed correctly in efficacy reports.
- [ ] `what_if_result` caching works: repeated queries within 24h return cached data.
- [ ] DB migration adds `what_if_result` (JSONB) and `what_if_run_count` (int) successfully.
- [ ] All 267 new unit tests pass.
- [ ] API integration tests pass (auth, rate limiting, schema validation).
- [ ] E2E correlation between simulated and actual outcomes > 0.85 on held-out sample.
- [ ] API documentation is complete and reviewed by frontend lead.
- [ ] No regression in pick evaluation pipeline (simulator is read-only).

---

## 6. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Simulator P&L diverges from actual execution (sim vs. live mismatch) | Medium | High | Uses same slippage model as live pipeline; correlation test validates > 0.85; disclaimer in UI that results are hypothetical. |
| Users over-rely on what-if to second-guess gates, causing organizational friction | Medium | Medium | Efficacy report frames gates as "waste prevented" not "missed opportunity"; require 2-person approval for threshold changes. |
| Heavy API usage from batch queries degrades DB performance | Medium | Medium | Rate limiting (100/min); caching (24h TTL); batch max 1000; DB read replica for what-if queries. |
| What-if reveals gates are badly calibrated, requiring emergency PRs | Low | High | This is actually the *purpose* of the feature; if gates are wrong, fixing them is correct action. |
| Cached results become stale after slippage model update | Low | Medium | Cache key includes `slippage_model_version`; model updates invalidate cache. |

### Rollback
1. `git revert HEAD` to remove all new files.
2. Run `alembic downgrade -1` to remove DB columns.
3. Remove API routes from `api/main.py` router registration.
4. **Estimated time: 5 minutes.**

---

## 7. Merge Order

```
PR-1 ──> PR-2 ──> PR-3 ──> PR-4 ──> PR-5 (this PR)
                                          ^
                                          │
                                    PR-5 depends on ALL
                                    previous PRs for
                                    filter reason completeness
```

| Dependency | Reason |
|---|---|
| **PR-1 → PR-5** | PR-1 introduces `COT_LAG_REJECT` and `CONCENTRATION_CAP_HIT` as new filter reasons. PR-5's efficacy report must include these in its analytics. |
| **PR-2 → PR-5** | PR-2 introduces `VIX_REGIME_REJECT`. PR-5 must be able to simulate what-if for ETF picks filtered by VIX regime. |
| **PR-3 → PR-5** | PR-3 introduces `POST_COST_EXPECTANCY_REJECT` and `POST_COST_EXPECTANCY_TOO_LOW`. These are the most complex filter reasons (with diagnostic dicts), and PR-5 must parse and display the slippage breakdown in what-if results. |
| **PR-4 → PR-5** | PR-4 introduces `ML_VARIANT_QUARANTINED` and the whitelist model. PR-5 must allow "what if this variant was whitelisted?" simulations for quarantined CRYPTO variants. |
| **Soft: All → PR-5** | PR-5 is a **read-only analytics feature** but depends on the filter reason taxonomy being stable. It should merge last to avoid needing updates when earlier PRs change filter reasons. |

**Merge this PR fifth and last.**
