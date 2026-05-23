# Mercury 2 — High-conviction validation pipeline (practical scope)

This doc maps **implemented** repo pieces to the broader Mercury / quant wishlist (typed contracts, stats, CI, Docker). It is not a promise to ship every research idea (Parquet feature stores, Grafana, Ray, etc.) unless separately scheduled.

**Changelog digest:** `docs/RECENT.MD` (2026-04-09 HC quality initiative). If RECENT and this file disagree, **trust the code** (`audit_dashboard/hc_filter.js`, `tools/dashboard_hc_rules.py`) and update RECENT.

---

## Current dashboard HC filter (authoritative)

Implementation: `audit_dashboard/hc_filter.js` (browser + Node), thresholds in `config/hc_gate_params.json`, Python mirror `tools/dashboard_hc_rules.py`.

**Pre-checks (config-driven):**

1. **Score floors:** reject `score < 40`; require `score >= 50` unless `trust_score >= 8` (config: `scoreAbsoluteFloor`, `scoreCompoundFloor`, `scoreCompoundTrustMin`).
2. **Trust tier blocklist** (e.g. SANDBOX, UNPROVEN, PROBATION, DEMOTED).
3. **Forward validation:** `forwardTrades >= forwardTradesMin`, forward WR `>= forwardWRMinPct` (default 45% as fraction 0.45; tune in JSON if pick count is too low).
4. **Trust score:** crypto `>= trustScoreMinCrypto` (default 6); non-crypto `>= trustScoreMinOther` (default 5).
5. **Overconfidence:** `confidence > confidenceMax` with `forwardTrades < confidenceFwdTradesMax` → reject.
6. **Regime × direction:** e.g. SHORT blocked in bull / empty regime (flags in JSON); optional LONG-in-bear, SHORT-in-choppy rules.
7. **Walk-forward:** `wf_verdict === FAILING` rejected when `rejectWalkForwardFailing` is true.
8. **Independent consensus (optional):** if `independentGroupsMin > 0`, require N distinct signal groups from `source_systems` / `agreeing_sources`; S/A + PROVEN may bypass per `tierSABypassIndependentConsensus`.

**Then** stamped HF tier support applies through either the per-asset tier contract or backend bypass-tier reasons already attached to the pick, followed by the shared gates (with optional Gate 8 bypass for S/A when configured).

**Not in the current file:** graduated confidence bands (0.60–0.85), tier-B-only score floor, or a full 6-state regime taxonomy as **hard-coded extra blocks** — those appeared in an alternate branch write-up; do not assume they ship unless present in `hc_filter.js`.

---

## Data quality (closed pick enrichment)

| Area | Location | Notes |
|------|----------|--------|
| Scoring fields preserved to closed | `audit_trail/universal_pick_resolver.py` | `_SCORING_FIELDS` keeps elite/trust/forward/confidence/etc. when resolving picks so HC filters and dashboards are not blind |

---

## Implemented (tooling)

| Area | Location | Notes |
|------|----------|--------|
| Typed pick rows (Pydantic) | `tools/hf_pick_contracts.py` | Opt-in; `pip install -r tools/requirements-hf-validation.txt` |
| Z-test vs baseline, bootstrap WR CI, PF / Sortino on `pnl_pct` | `tools/hf_validation_stats.py` | Stdlib + `math` only |
| Enhanced closed-book report | `tools/validate_hf_by_asset_class.py` | `--json-out`, strategy slices, `--check-contracts` |
| **Dashboard JS parity** | `tools/dashboard_hc_rules.py` + `tools/validate_dashboard_parity.py` | Python mirror of `passesHighConvictionPick`; compares vs `classify_hf_conviction_tier` |
| **Tier significance** | `tools/tier_significance.py` | Bootstrap CI + z vs baseline; optional SciPy `ttest_1samp` |
| CI | `.github/workflows/validate-hf-asset-class.yml` | PR/path filters, nightly, artifact JSON |
| Docker | `tools/Dockerfile.hf-validation` | Slim image; mount repo to run validator |

## Detection & lifecycle (implemented)

| Tool | Purpose |
|------|---------|
| `tools/edge_decay_monitor.py` | Recent vs older-baseline WR per tier (`classify_hf_conviction_tier`); `--fail-on-alert` for CI gates |
| `tools/walk_forward_thresholds.py` | Exploratory score×trust×fwd grid + rolling OOS windows (stdlib) |
| `tools/tier_lifecycle.py` | Heuristic PROMOTE/HOLD/DEMOTE hints from aggregate tier stats |
| `validate_hf_by_asset_class.py` | Emits `sample_adequacy_warnings` when asset class or tier cells are tiny |
| `.github/workflows/edge-decay-check.yml` | Weekday schedule + artifact; optional `fail_on_alert` on manual dispatch |

## Data acquisition (non-crypto)

1. Export **all** closed equity / forex rows (not only HF), run `classify_hf_conviction_tier` on history — target **30+** equity / **20+** forex closes before trusting tier slices.
2. **Futures**: if total `n` stays tiny, treat tier labels as **unvalidated** (validator warns).
3. **ETF**: can be pooled with equity for coarse stats when strategies overlap.

## HC gate config + backtests (Mercury 2 plan)

| Piece | Location | Notes |
|-------|----------|--------|
| Tunable thresholds + signal groups | `config/hc_gate_params.json` | Merged over embedded defaults in `audit_dashboard/hc_filter.js` (Node) / `tools/dashboard_hc_rules.py` |
| Cost assumptions (CSV backtest) | `config/cost_model.json` | Round-trip %% deducted from gross `pnl_pct` |
| CSV + net metrics | `tools/hc_csv_backtest.js` | `node tools/hc_csv_backtest.js tools/fixtures/sample_hc_picks.csv` |
| Train/test split on dashboard closed | `tools/backtest_hc_filter.py` | `python tools/backtest_hc_filter.py` (uses `dashboard_data.json` → `recent_closed`) |
| Closed JSON backtest | `tools/hc_filter_backtest.py` | Python `json.loads` + `passes_high_conviction_pick` |
| Portfolio tier routing | `config/portfolio_mandate.json` | Enforced at TV/bus placement, not inside HC filter |
| Correlation pre-check | `tools/portfolio_correlation_gate.js` | Portfolio-level only |
| Calibration hygiene | `docs/QUANT_AUDIT_v2.md` | Exclude `paper_trading/data/` from calibration |
| Regression tests | `tests/test_hc_filter.js`, `tests/test_dashboard_hc_rules.py` | Gates, WF `FAILING`, optional `independentGroupsMin` |

**Browser:** plain `<script src="hc_filter.js">` does not read the JSON file; defaults are embedded. To tune live UI without redeploy, set `window.__HC_GATE_PARAMS__ = { ... }` *before* the filter runs (shallow merge).

**Quarterly re-validation (no trading disruption):** run validators on a **copy** of closed-picks / CSV in CI or a scheduled job (`workflow_dispatch` + artifact diff). Promote new `hc_gate_params.json` only after backtest metrics beat baseline; keep the previous JSON under `config/hc_gate_params.vNNN.json` for rollback.

**Per-gate monitoring:** offline, slice closed rows by *which gate would fail first* (implement a small `hc_gate_trace.py` that returns fail codes); aggregate win-rate / mean net PnL per code for dashboard tables or a static HTML report — avoid mutating live filter mid-bar.

---

## Plan status (from optimization / RECENT next steps)

| Item | Status | Notes |
|------|--------|--------|
| Regime / direction gates | **Partial** | In `hc_gate_params.json` (bull/empty/choppy/bear flags); not full 6-state machine in JS |
| Per-portfolio differentiation | **Partial** | `config/portfolio_mandate.json`; wire in TV/bus placement |
| Monitoring (edge decay, reports) | **Ongoing** | `edge_decay_monitor`, CI workflow; heat map / gate trace still optional |
| Hyrotrader scoring alignment | **Open** | After HC validation stable |
| Backtest validation | **Runnable** | `backtest_hc_filter.py`, `hc_filter_backtest.py`, `hc_csv_backtest.js` |
| Confidence recalibration | **Open** | Use non–paper-trading sources only (`QUANT_AUDIT_v2.md`) |
| Kill-switch v2 | **Open** | `max(flatStopPct, -2*ATR)` + min hold — separate from HC filter |
| Backend conviction stack / patch | See **code** | `alpha_engine/conviction_stack.py`, `conviction_stack_patch.py` — summarized in `docs/RECENT.MD` |

---

## Suggested next steps (not auto-built)

- **Slack / Discord**: webhook step on `edge_decay_report.json` when `DECAYING` / `CRITICAL`.
- **Mercury 2 risk engine**: execution-time guards remain in `mercury2/risk_engine.py`; validation here is **offline** on closed picks.
- **Optional GATE 8:** time-of-day UTC filter (document thresholds before enable).
- **Gate trace script** for per-gate WR / net PnL attribution.

## Commands

```bash
pip install -r tools/requirements-hf-validation.txt
python tools/validate_hf_by_asset_class.py
python tools/validate_hf_by_asset_class.py --json-out audit_trail/data/hf_asset_class_report.json --check-contracts
python tools/validate_dashboard_parity.py --json-out audit_trail/data/dashboard_hc_parity.json
python tools/tier_significance.py --json-out audit_trail/data/tier_significance.json
python tools/edge_decay_monitor.py --json-out audit_trail/data/edge_decay_report.json
python tools/walk_forward_thresholds.py --json-out audit_trail/data/walk_forward_report.json
python tools/backtest_hc_filter.py
python tools/hc_filter_backtest.py
python tools/audit_pick_schema.py
python tools/hc_rolling_impact.py
python -m pytest tests/test_hf_validation_stats.py tests/test_hf_pick_contracts.py tests/test_dashboard_hc_rules.py -q
node tests/test_hc_filter.js
node tools/hc_csv_backtest.js tools/fixtures/sample_hc_picks.csv
```

Full narrative for 2026-04-09 changes: **`docs/RECENT.MD`**.

python tools/audit_pick_schema.py
python tools/hc_rolling_impact.py

