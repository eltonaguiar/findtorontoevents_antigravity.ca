# Implementation Plan v2 — Supreme Plan v2 Operational Spec — 2026-05-13

**Supersedes:** [reports/implementation_plan_2026-05-13.md](reports/implementation_plan_2026-05-13.md) (the Grok-authored predecessor, merged via PR #939)
**Driven by:** [updates/2026-05-13-supreme-plan-v2.html](updates/2026-05-13-supreme-plan-v2.html) (the amended Supreme Plan)
**Companion todo list:** 25 items, P0 → P3
**Procedure:** each item gets (a) detailed steps, (b) test plan, (c) acceptance criteria, (d) post-impl verification one-liner

---

## Sequencing (binding order)

The v2 Supreme Plan made one structural change vs v1: **infrastructure (P0.5) gates strategy edges**. So the implementation order is:

1. **P0.5 infrastructure cluster** (5 items) — gate every asset-class promotion
2. **P0 acceptance gates** (4 items) — activate/verify already-shipped work
3. **P1 per-class** (8 items) — apply infra to each class
4. **P2 structural** (3 items) — long-tail health
5. **P3 stretch** (2 items) — quant-library integrations

---

## P0.5 — Infrastructure cluster (DO FIRST)

### P0.5-1 · `alpha_engine/position_sizer.py`

**Why:** `sizing_allowed=true` flags are meaningless without explicit vol-targeting and max-allocation-per-name. One high-conviction coin can torch the book.

**Steps:**
1. Create `alpha_engine/position_sizer.py` with two pure functions:
   - `compute_position_size(pick, portfolio_equity, daily_vol_estimate) -> float` — returns dollar position size
   - `validate_concentration(pick, current_positions) -> tuple[bool, str]` — caps total exposure per name + per asset class
2. Use Charter §7 limits: max 5% single position (long-term) / 1% (swing); 30% per sector / 20% per swing-sector
3. Volatility estimate: 20-day rolling stddev of `pnl_pct` from `recent_closed` keyed on `(asset_class, symbol)`; fall back to per-class default if n<5
4. Target risk per trade: 1% of portfolio for swing, 2% for long-term. Position size = (target_risk / vol_estimate) * portfolio_equity
5. Wire-Up: import from `production_scanner.py` near line 2548 (where `passes_active_gate` is called); apply BEFORE emission to active_picks

**Test plan:**
- `tests/test_position_sizer.py` with 6+ unit tests:
  - Zero-vol fallback → uses class default
  - Concentration cap binds → returns reduced size with reason
  - Long-term 2% per-trade vs swing 1%
  - Sector cap binds across multiple picks
  - Portfolio equity = 0 → returns 0
  - Confidence multiplier (high-conf gets full size; low-conf scaled)

**Acceptance:**
- All tests pass
- No pick can exceed Charter §7 single-position cap regardless of conviction
- Concentration-rejected picks land in active_picks with `size=0` and `reject_reason="concentration_cap"` (not silently dropped — must be auditable on /audit)

**Post-impl one-liner verify:**
```bash
py -c "from alpha_engine.position_sizer import compute_position_size; print(compute_position_size({'asset_class':'CRYPTO','symbol':'BTCUSDT','confidence':0.8}, 10000, 0.04))"
```

### P0.5-2 · Slippage + execution cost model

**Why:** Without per-class slippage deduction, backtest PF is fantasy. COMMODITY PF 3.94 likely loses 0.3-0.5 PF to realistic HG=F futures spreads.

**Steps:**
1. Add `EXECUTION_COST_BPS_BY_CLASS` dict in `alpha_engine/outcome_resolver.py` near line 117 (where `PNL_WIN_THRESHOLD_BY_CLASS` already lives): CRYPTO 8bp, EQUITY 5bp, ETF 4bp, COMMODITY 12bp (futures spreads), FOREX 1bp, BOND 6bp
2. In `outcome_resolver.py` resolve function: after computing raw `pnl_pct`, deduct `2 * EXECUTION_COST_BPS_BY_CLASS[ac] / 100` (round-trip) before classifying as WIN/LOSS
3. Add `_pnl_pct_gross` and `_pnl_pct_net` to the resolved pick so /audit can show both
4. Update `walk_forward_validate` to operate on `pnl_pct_net` by default; expose `pnl_pct_gross` for diagnostics

**Test plan:**
- `tests/test_execution_cost_model.py`:
  - +0.05% gross COMMODITY pick (5bp) → −0.19% net (5bp − 24bp round-trip = −19bp net) — LOSS not WIN
  - +0.50% gross CRYPTO pick → +0.34% net (50bp − 16bp = 34bp) — still WIN
  - CRYPTO walk_forward with vs without slippage: PF must be ≤ no-slippage PF by ≥5%
- Update `tests/test_walkforward_by_class.py::test_returns_walk_forward_metrics` to verify both gross + net keys exist

**Acceptance:**
- Every closed pick has both `_pnl_pct_gross` and `_pnl_pct_net`
- /audit headline switches to NET PF (note in MAJOR GOAL banner)
- Expected mechanical PF degradation per class published in `reports/slippage_impact_2026-05-13.md`

**Post-impl one-liner verify:**
```bash
py -c "import json; d=json.load(open('audit_dashboard/data/dashboard_data.json',encoding='utf-8')); rc=d['picks']['recent_closed']; net=[r for r in rc if r.get('_pnl_pct_net') is not None]; print(f'{len(net)}/{len(rc)} have net pnl tagged')"
```

### P0.5-3 · `alpha_engine/drift_circuit_breaker.py`

**Why:** CRYPTO −31.12pp backtest-live gap is *charted* but not acted on. Need auto-flip on rolling WR breach.

**Steps:**
1. Create `alpha_engine/drift_circuit_breaker.py`:
   - `compute_realized_wr_30d(asset_class) -> float` — read `recent_closed` filtered last 30d
   - `is_sizing_breached(asset_class) -> tuple[bool, str]` — compare to walk_forward backtest WR; trip if `realized < backtest - 2*sigma`
2. Wire into the same place PR #909 added the FOREX hard-cap (`alpha_engine/risk_policy_check.py::is_forex_sizing_allowed`); extend to all classes
3. Emit `block_reason` to dashboard so /audit shows which class is in drift-circuit-breaker state

**Test plan:**
- `tests/test_drift_circuit_breaker.py`:
  - CRYPTO with realized_wr=20%, backtest_wr=50%, sigma=5% → trips (20 < 50-10)
  - EQUITY within band → does not trip
  - No backtest data → does not trip (don't false-positive cold start)
  - Realized n<30 → does not trip (need sample)

**Acceptance:** at least one class trips in the test fixture; surface `block_reason` in `dashboard_data.json::asset_class_health[CLASS].block_reason`

**Post-impl one-liner verify:**
```bash
py -c "from alpha_engine.drift_circuit_breaker import is_sizing_breached; print(is_sizing_breached('CRYPTO'))"
```

### P0.5-4 · Concentration controls in `quality_gates.py`

**Why:** COMMODITY emission universe = 100% HG=F today. A copper crash erases the class.

**Steps:**
1. Extend `quality_gates.py::_concentration_risk` (existing function ~line 2431): add per-class symbol-exposure cap (e.g., no single symbol > 60% of class active picks)
2. Add per-sector cap for EQUITY: no sector > 40% (consume `audit_trail/sector_taxonomy.py` if exists, else map by ticker prefix)
3. Trigger at `passes_active_gate` not just emission gate (so existing positions can still be tracked)

**Test plan:**
- `tests/test_concentration.py`:
  - Class with 100% HG=F → flagged; next HG=F pick rejected
  - Mixed 50/50 → passes
  - Empty class → passes

**Acceptance:** `_concentration_risk` returns reject for any class > 60% single-symbol; integration test on current `active_picks.json` shows expected count of rejects

### P0.5-5 · Verify `portfolio_circuit_breaker.py` wired

**Why:** Charter §7 specifies daily −3% cap; `alpha_engine/portfolio_circuit_breaker.py` exists but wire-up unverified.

**Steps:**
1. Read `portfolio_circuit_breaker.py` end-to-end
2. Trace callers via `grep -r "portfolio_circuit_breaker"` — confirm ≥1 production caller
3. If unwired: add to `production_scanner.py` startup; add daily PnL accumulator to `dashboard_data.json`
4. If wired but unobserved: add visible `circuit_breaker_active` field to dashboard

**Test plan:**
- `tests/test_portfolio_circuit_breaker.py`: synthetic loss day → confirm `active=true`, sizing halted

**Acceptance:** /audit shows portfolio circuit-breaker status field; on test injection it flips to `active=true`

---

## P0 — Activation & acceptance gates (work shipped but inactive)

### P0-A · COT lag-corrected re-run on `cot_paper_pilot.py`

**Steps:** with PR #941 merged (3-day publication-lag guard), re-run `python alpha_engine/cot_paper_pilot.py` on the full 100-pick CT=F history. Document the lag-corrected WR in `reports/cot_paper_pilot_lag_corrected_2026-05-13.md`.

**Acceptance gate (2026-05-23 graduation):** lag-corrected WR ≥ 75% on full 100-pick history; DSR ≥ 0.85. If WR drops to DeepSeek's predicted 45-55%, pilot returns to REHAB and the COMMODITY T1-candidate verdict downgrades to T2.

### P0-B · CRYPTO confidence-inversion independent reproduction

**Steps:** before merging the cloud agent's +56-line `quality_gates.py` gate, run this reproducible query:
```python
import json
from collections import defaultdict
d = json.load(open('audit_dashboard/data/dashboard_data.json', encoding='utf-8'))
rc = d['picks']['recent_closed']
buckets = defaultdict(lambda: {'win':0,'loss':0})
for r in rc:
    if r.get('asset_class') != 'CRYPTO': continue
    outc = r.get('_outcome', '')
    if outc not in ('WIN','LOSS'): continue
    conf = r.get('confidence', 0)
    bucket = ('top' if conf >= 0.85 else 'high' if conf >= 0.70 else 'mid' if conf >= 0.50 else 'low' if conf >= 0.25 else 'bot')
    buckets[bucket][outc.lower()] += 1
for b, c in sorted(buckets.items()):
    n = c['win'] + c['loss']
    wr = 100*c['win']/n if n else 0
    print(f'{b}: n={n} WR={wr:.1f}%')
```
**Acceptance:** If bottom bucket WR ≥ top bucket WR by ≥15pp, the inversion is real and the gate ships. If not, the cloud-agent's claim joins the 5 confidently-wrong claims list.

### P0-C · BOND Layers 2 + 3

**Steps:**
1. **Layer 2:** edit `alpha_engine/forward_validator.py:389` to add `FORWARD_GATE_OVERRIDES: dict[str, int] = {"bond": 10}` constant. In `passes_forward_gate`, look up the asset_class override before falling back to `FORWARD_GATE_MIN_TRADES`.
2. **Layer 3:** in `.github/workflows/bond-agent.yml` after the curated picks write, add a step that merges qualified picks into `alpha_engine/data/active_picks.json` (NOT `bond_picks.json` which is stats-only).

**Test plan:**
- `tests/test_forward_validator_class_override.py` — bond with n=10 passes; n=9 fails
- Workflow dry-run via `gh workflow run bond-agent.yml`

**Acceptance:** within 14 days of ship, `/audit` BOND has ≥ 5 picks from real bond_* strategies (not legacy ZN=F)

### P0-D · Run `multi_asset_cot` verifier (PR #913 shipped tool)

**Steps:** `python tools/verify_multi_asset_cot.py > reports/multi_asset_cot_verdict_2026-05-13.md`. Verdict will be REAL / OUTLIER_DRIVEN / RESOLVER_INFLATED / DATA_GAP.

**Acceptance:** verdict committed; if OUTLIER_DRIVEN, expect COMMODITY headline PF drop from 3.94 → 2.0-2.5 (still T2, but with less inflated framing).

---

## P1 — Per-class strategy work (after P0.5 ships)

Detailed steps in v2 Supreme Plan. Summary:
- **P1-A FOREX composite ranking** — feature-flagged sidecar in `quality_gates.py`, A/B test
- **P1-B EQUITY sample expansion** — gate 85→78
- **P1-C ETF push to T2** — gate-loosen, target PF 1.5
- **P1-D COMMODITY shadow universe** — PA=F + BZ=F + GC=F at 0% sizing 60d
- **P1-E COMMODITY Seasonal Supply-Demand** — USDA data, expected PF 2.2
- **P1-F FOREX SHORT-only rehab** — 36pp WR spread
- **P1-G FUTURES mutation-replay** — SHORT-axis variants
- **P1-H retrain `enhanced_ml_crypto_v3`** — 44-day stale joblib
- **P1-I CT=F regime-gate** — CPCV fold_1 worst=10% WR
- **P1-J AVOID list** — 4 of 5 verified candidates per `quarantine_candidates_verification_2026-05-13.md`

---

## P2 — Structural

- `active_picks_sync` DRY-RUN flip to live (Cerebras-adopted)
- MDD capped-vs-raw fields in dashboard_data.json (PR #914 docs only)
- FRED wire-in for BOND + macro overlay
- DAILY_IDEAS deep-dive brief follow-up

---

## P3 — Stretch quant libs

- Riskfolio-Lib for CVaR / HRP risk budgeting
- VectorBT for 50-100× faster vectorized backtests

---

## Coordination protocol

Per session-handoff §7.6, multi-agent coordination has no protocol. Adopting:
- Create `.work-in-progress/{filename}.claimed_by_{session_id}.json` before editing shared production files (`quality_gates.py`, `production_scanner.py`, `scanner.py`)
- Stale claims (> 4h old): inheritable by next agent
- Net-new files (`position_sizer.py`, `drift_circuit_breaker.py`) skip the claim — no collision risk

---

## Procedural checkpoints

Every item:
1. Detailed implementation step-by-step (above)
2. Test plan (named test file + 3-6 cases)
3. Acceptance criteria (numeric where possible)
4. Post-impl one-liner verification (anyone can re-run)
5. `updates/2026-05-13-{item}.md` doc per AGENTS.md
6. Clean branch + PR (no merging to main directly)
7. **External-model second-opinion when internal swarms converge** (DeepSeek/Loker/GPT-OSS via ~$0.02 round, per Supreme Plan v2 procedural addition)

---

## Pending swarm review

This plan was generated by Opus 4.7. Before implementation begins, swarm-review it for:
- Missed dependencies between items
- Test coverage gaps
- Acceptance-criteria specificity
- Coordination-protocol completeness

Swarm review output appended below this section once received.
