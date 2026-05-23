# PR-2: Wire VIX < 25 Gate for ETF Class

| Field | Value |
|---|---|
| **Branch** | `feat/etf-vix-gate-2026-0518` |
| **Target** | `main` |
| **Class** | ETF |
| **Paper Signal** | `VIX<25` environment filter |
| **Status** | WATCH → target MONEY_READY |
| **Author** | `quant-dev-2` |
| **Reviewers** | `strat-lead`, `risk-lead` |

---

## 1. Problem Statement

### 1.1 ETF Class Stuck in WATCH Status
The ETF class in `pf_registry.json` (2026-05-18T00:27:46Z) shows:
```json
{
  "class": "ETF",
  "n_resolved": 105,
  "win_rate": 0.571,
  "profit_factor": "~1.2 (dash)",
  "status": "WATCH",
  "note": "PF suppressed by high-volatility regime picks"
}
```
Win rate is deceptively high at 57.1%, but the class is only at WATCH because the PF is unreliable and regime-sensitive. Live trading without a volatility gate risks deploying into environments where the strategy has negative expectancy.

### 1.2 Paper Analysis: Extreme Regime Sensitivity
Internal paper-trading analysis (2026-Q1, strat-lead memo #ETF-2026-0412) shows a stark bifurcation:

| Regime | VIX Range | Trades | WR | PF |
|---|---|---|---|---|
| Low Volatility | VIX < 25 | 61 | 68.9% | **2.05** |
| High Volatility | VIX >= 25 | 44 | 41.0% | **0.72** |
| **Combined** | All | 105 | 57.1% | **~1.2** |

**Key insight:** The blended PF of ~1.2 is entirely carried by the low-vol regime. High-vol picks are systematically unprofitable (PF < 1.0). The gate is simple, has a clear economic rationale (mean-reversion strategies fail in trending/volatile markets), and is the single highest-impact change to unlock ETF class.

### 1.3 Current State
- The `vix_feed.py` module already publishes real-time VIX spot and continuous futures.
- `quality_gates.py` has a **dormant** gate function `check_vix_environment()` (~L3124) that returns a boolean but is **not wired into the ETF pick lifecycle**.
- The ETF class config in `asset_class_limits.yaml` has `vix_gate_enabled: false`.

---

## 2. Solution

### 2.1 Wire Existing Gate into ETF Lifecycle
1. **In `quality_gates.py` (~L3124, `check_vix_environment`):**
   - Promote from `@advisory` to `@active_gate` decorator for the ETF class.
   - Keep threshold at `VIX < 25` (configurable via `asset_class_limits.yaml`).
   - Gate returns:
     - `PASS` if `vix_spot < 25` and `vix_3d_ma < 27` (3-day smoothing to avoid whipsaw)
     - `REJECT` otherwise, with `filter_reason = "VIX_REGIME_REJECT"`
   - Add metric emission: `etf_vix_gate_reject_total{reason="vix_too_high"}`.

2. **In `pick_evaluator.py` (`evaluate_pick()`):**
   - Add `check_vix_environment(pick)` as the **first** gate in the ETF class gate chain (before `passes_active_gate`, before `passes_ml_quarantine`).
   - Rationale: Volatility regime is a cheap, fast filter. Running it first avoids wasted compute on deeper analysis.

3. **In `asset_class_limits.yaml`:**
   - Change `vix_gate_enabled: false` → `true` for ETF class.
   - Add `vix_threshold: 25.0` and `vix_ma_period: 3`.

### 2.2 VIX Feed Resilience
1. **In `vix_feed.py`:**
   - Add stale-data detection: if VIX feed is > 60 seconds old, gate defaults to `REJECT` (fail-closed).
   - Add fallback to `VIX_FUTURES_CONTINUOUS` if spot feed is down.
   - Emit `vix_feed_stale` alert if fallback is active for > 5 minutes.

---

## 3. Files Changed

| File | Lines | Change |
|---|---|---|
| `quality_gates.py` | +28 / -8 | Promote `check_vix_environment` to active gate for ETF class; add 3-day MA logic; metric emission |
| `pick_evaluator.py` | +12 / -3 | Insert VIX gate as first ETF filter; update gate chain order |
| `vix_feed.py` | +55 / -11 | Stale-data detection; fallback to futures; `REJECT` on stale default |
| `asset_class_limits.yaml` | +6 / -1 | Enable gate; set `vix_threshold: 25.0`; add `vix_ma_period: 3` |
| `pf_registry.json` | +4 / -2 | Update ETF status gate annotations |
| `tests/unit/test_etf_vix_gate.py` | +156 | New test suite: VIX threshold, MA smoothing, stale feed, fallback |
| `tests/integration/test_etf_e2e.py` | +78 | End-to-end: verify only VIX<25 picks pass; PF >= 1.8 expected |

---

## 4. Test Plan

### 4.1 Unit Tests (`tests/unit/test_etf_vix_gate.py`)

| Test Case | Input | Expected |
|---|---|---|
| `test_gate_passes_when_vix_24` | `vix_spot=24.0`, `vix_3d_ma=23.5` | `PASS` |
| `test_gate_rejects_when_vix_25` | `vix_spot=25.0`, `vix_3d_ma=24.0` | `REJECT`, reason `VIX_REGIME_REJECT` |
| `test_gate_rejects_when_vix_ma_high` | `vix_spot=24.0`, `vix_3d_ma=28.0` | `REJECT` (smoothing protects against whipsaw) |
| `test_gate_rejects_on_stale_feed` | VIX feed timestamp > 60s old | `REJECT`, metric `vix_feed_stale` emitted |
| `test_gate_uses_futures_fallback` | Spot feed down, futures VIX=22 | `PASS` using futures |
| `test_gate_chain_order` | ETF pick with VIX=30 | VIX gate runs first; deeper gates are skipped |
| `test_pf_projection_post_gate` | 50 historical picks with gate retroactively applied | PF >= 1.8, n >= 30 |

### 4.2 Integration Tests (`tests/integration/test_etf_e2e.py`)
- Replay all 105 historical ETF picks with the VIX gate enabled.
- Expected result: ~61 picks pass (VIX<25), ~44 are filtered.
- Assert PF of passing picks >= 1.8 (consistent with paper PF=2.05 minus slippage).
- Assert no picks are accepted when VIX >= 25.

### 4.3 Manual / QA
- [ ] Deploy to paper-trading environment; verify ETF pick count drops on high-VIX days.
- [ ] Confirm `etf_vix_gate_reject_total` metric appears in Grafana dashboard.
- [ ] Simulate stale VIX feed (stop `vix_feed.py`); confirm gate rejects all ETF picks within 60s.

---

## 5. Acceptance Criteria

- [ ] `check_vix_environment` is an active (hard) gate for ETF class, not advisory.
- [ ] ETF picks are rejected when `vix_spot >= 25` or `vix_3d_ma >= 27`.
- [ ] Stale VIX feed (> 60s) causes automatic `REJECT` (fail-closed behavior).
- [ ] VIX futures fallback works when spot feed is unavailable.
- [ ] ETF class PF in `pf_registry.json` improves from ~1.2 to >= 1.5 within 30 days of deployment (paper trading).
- [ ] No ETF picks are accepted during VIX >= 25 regimes.
- [ ] All 156 new unit tests pass.
- [ ] Integration backtest shows PF >= 1.8 on VIX-filtered subset.
- [ ] No regression in other classes (gate is ETF-only).

---

## 6. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| VIX spike during market open causes flurry of rejections, missing valid picks | Medium | Medium | 3-day MA smoothing prevents whipsaw; threshold is configurable live. |
| VIX feed outage halts all ETF trading | Low | High | Fail-closed default is correct behavior; risk desk is alerted via `vix_feed_stale` metric. |
| Threshold of 25 is too conservative / not conservative enough | Medium | Medium | Config is hot-swappable; A/B test framework (ticket #4401) will optimize threshold post-launch. |
| ETF volume dries up in low-VIX regime, leaving too few picks | Low | Low | Historical analysis shows 61/105 picks in low-VIX regime — sufficient for weekly rotation. |

### Rollback
1. Change `vix_gate_enabled: true` → `false` in `asset_class_limits.yaml` (live config reload, no restart needed).
2. If code revert needed: `git revert HEAD`.
3. Estimated rollback time: **30 seconds** (config) or **3 minutes** (code revert + restart).

---

## 7. Merge Order

```
PR-1 (independent) ──┐
                     ├──> PR-3 ──> PR-4 ──> PR-5
PR-2 (this PR) ──────┘      ^
                              │
                        PR-2 is independent of PR-1
                        but should merge before PR-3
                        to establish ETF baseline
```

| Dependency | Reason |
|---|---|
| **None for code** | PR-2 touches entirely different code paths (ETF/VIX) from PR-1 (COMMODITY/COT). No file overlap. |
| Soft: PR-2 before PR-3 | PR-3's global slippage model uses class-level PF baselines. ETF should have its VIX-gated PF established before PR-3 hard-gates on post-cost expectancy. |
| Soft: PR-2 before PR-5 | PR-5's what-if query should reflect the new `VIX_REGIME_REJECT` filter reason in `pick_lifecycle_log`. |

**Merge this PR second (or in parallel with PR-1).**
