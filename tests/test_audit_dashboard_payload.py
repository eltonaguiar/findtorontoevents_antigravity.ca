"""Schema/shape tests for audit_dashboard/data/dashboard_data.json.

Closes the test-coverage gap noted in reports/verify_2026-05-09_t2h.md step 2D:
only 3 audit/hyrotrader-prefixed test files existed; this adds focused unit
tests that validate the live payload shape without invoking the dashboard
generator (forbidden per CLAUDE.md rule "Never run dashboard generators
locally").

Tests skip cleanly when the data file is absent (CI sandboxes / fresh clones).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"

# Concept families known to alpha_engine.concept_registry / dashboard_generator
# inline fallback (see audit_trail/dashboard_generator.py:6382-6402).
KNOWN_CONCEPT_FAMILIES = frozenset({
    "long_term_value",
    "skyrocket",
    "tradingagents",
    "penny_stock",
    "meme_coin",
    "mercury2",
    "reverse_engineer",
    "standard",
})

skip_no_payload = pytest.mark.skipif(
    not PAYLOAD.exists(),
    reason=f"dashboard_data.json absent at {PAYLOAD}; run pipeline to generate",
)


@pytest.fixture(scope="module")
def payload() -> dict:
    if not PAYLOAD.exists():
        pytest.skip("dashboard_data.json absent")
    with PAYLOAD.open(encoding="utf-8") as fh:
        return json.load(fh)


@skip_no_payload
def test_payload_has_required_top_level_keys(payload):
    required = {
        "summary",
        "picks",
        "performance",
        "leaderboard",
        "hf_decay_watchlist",
        "fwd_vs_bt_divergence",
        "macro_context",
        "walkforward",
        "systems",
        "metadata",
        "generated_at",
    }
    missing = required - set(payload.keys())
    assert not missing, f"top-level keys missing from dashboard_data.json: {missing}"


@skip_no_payload
def test_summary_block_shape(payload):
    summary = payload["summary"]
    assert isinstance(summary, dict)
    required_fields = {
        "total_pnl_pct",
        "total_pnl_pct_compounded_ew",
        "profit_factor",
        "overall_win_rate",
        "expectancy",
        "wins",
        "losses",
        "total_active_picks",
        "total_closed_picks",
    }
    missing = required_fields - set(summary.keys())
    assert not missing, f"summary missing fields: {missing}"

    # Sanity: counts must be non-negative ints
    for k in ("wins", "losses", "total_active_picks", "total_closed_picks"):
        v = summary.get(k)
        assert isinstance(v, int) and v >= 0, f"summary.{k} should be int>=0, got {v!r}"


@skip_no_payload
def test_picks_active_shape(payload):
    picks_block = payload.get("picks", {})
    assert isinstance(picks_block, dict)
    active = picks_block.get("active", [])
    assert isinstance(active, list)
    if not active:
        pytest.skip("no active picks in payload")

    required = {"symbol", "direction", "strategy", "asset_class", "source_system", "concept_family"}
    incomplete = []
    for i, pick in enumerate(active):
        if not isinstance(pick, dict):
            incomplete.append((i, "non-dict"))
            continue
        missing = [k for k in required if not pick.get(k)]
        if missing:
            incomplete.append((i, pick.get("symbol"), missing))
    assert not incomplete, f"active picks missing required fields: {incomplete[:5]}"


@skip_no_payload
def test_leaderboard_rows_shape(payload):
    lb = payload.get("leaderboard", [])
    assert isinstance(lb, list)
    if not lb:
        pytest.skip("leaderboard empty")

    required = {
        "strategy",
        "asset_class",
        "asset_classes",
        "fwd_trades",
        "fwd_wr",
        "fwd_pf",
        "health",
    }
    # Aggregate "*_group" rollup rows are exempt from per-asset-class fields.
    bad = []
    for i, row in enumerate(lb):
        if not isinstance(row, dict):
            bad.append((i, "non-dict"))
            continue
        strat = str(row.get("strategy") or "")
        is_aggregate = strat.endswith("_group")
        row_required = required - ({"asset_class", "asset_classes"} if is_aggregate else set())
        missing = [k for k in row_required if k not in row]
        if missing:
            bad.append((i, strat, missing))
    assert not bad, f"leaderboard rows missing keys: {bad[:5]}"

    # asset_classes must be a list on at least one row that has it
    has_ac = next((r for r in lb if "asset_classes" in r), None)
    if has_ac is not None:
        assert isinstance(has_ac["asset_classes"], list), \
            f"leaderboard.asset_classes should be list, got {type(has_ac['asset_classes']).__name__}"


@skip_no_payload
def test_asset_class_health_shape(payload):
    perf = payload.get("performance", {})
    assert isinstance(perf, dict)
    ach = perf.get("asset_class_health", {})
    assert isinstance(ach, dict)
    if not ach:
        pytest.skip("asset_class_health empty")

    required = {"profit_factor", "win_rate", "resolved_n", "sample_tier"}
    bad = []
    for cls, row in ach.items():
        if not isinstance(row, dict):
            bad.append((cls, "non-dict"))
            continue
        missing = required - set(row.keys())
        if missing:
            bad.append((cls, missing))
    assert not bad, f"asset_class_health rows missing keys: {bad}"


@skip_no_payload
def test_fwd_vs_bt_divergence_threshold(payload):
    fvb = payload.get("fwd_vs_bt_divergence", {})
    assert isinstance(fvb, dict)
    rows = fvb.get("rows", [])
    assert isinstance(rows, list)

    wr_z_thr = fvb.get("wr_z_threshold")
    pf_ratio_thr = fvb.get("pf_ratio_threshold")
    assert wr_z_thr is not None, "fwd_vs_bt_divergence.wr_z_threshold missing"
    assert pf_ratio_thr is not None, "fwd_vs_bt_divergence.pf_ratio_threshold missing"

    # Default thresholds per dashboard_generator
    assert wr_z_thr <= -2.0, f"wr_z_threshold should be <= -2.0, got {wr_z_thr}"
    assert pf_ratio_thr < 0.6 + 1e-9, f"pf_ratio_threshold should be < 0.6, got {pf_ratio_thr}"

    # Every flagged row must satisfy at least one trigger
    bad = []
    for r in rows:
        wr_z = r.get("wr_z")
        pf_ratio = r.get("pf_ratio")
        wr_trip = wr_z is not None and wr_z <= wr_z_thr
        pf_trip = pf_ratio is not None and pf_ratio < pf_ratio_thr
        if not (wr_trip or pf_trip):
            bad.append((r.get("strategy"), wr_z, pf_ratio))
    assert not bad, f"divergence rows that don't trip either threshold: {bad[:5]}"


@skip_no_payload
def test_concept_family_taxonomy(payload):
    active = payload.get("picks", {}).get("active", [])
    if not active:
        pytest.skip("no active picks")
    unknown = []
    for p in active:
        cf = p.get("concept_family")
        if cf is not None and cf not in KNOWN_CONCEPT_FAMILIES:
            unknown.append((p.get("symbol"), p.get("strategy"), cf))
    assert not unknown, f"active picks with unknown concept_family: {unknown[:5]}"


@skip_no_payload
def test_hf_decay_watchlist_shape(payload):
    hf = payload.get("hf_decay_watchlist", {})
    assert isinstance(hf, dict), f"hf_decay_watchlist should be dict, got {type(hf).__name__}"
    assert "rows" in hf, "hf_decay_watchlist.rows missing"
    assert isinstance(hf["rows"], list)


@skip_no_payload
def test_walkforward_shape(payload):
    wf = payload.get("walkforward", {})
    assert isinstance(wf, dict)
    # Should have by_class breakdown OR a generated_at timestamp at minimum
    assert "by_class" in wf or "generated_at" in wf, \
        f"walkforward missing both by_class and generated_at: keys={list(wf.keys())}"


@skip_no_payload
def test_hf_stats_by_asset_class_shape(payload):
    """P0.5/#5 — hf_stats.by_asset_class contract (closes payload test gap)."""
    hf_stats = payload.get("hf_stats")
    assert isinstance(hf_stats, dict), \
        f"hf_stats should be dict, got {type(hf_stats).__name__}"
    bac = hf_stats.get("by_asset_class")
    assert isinstance(bac, dict), \
        f"hf_stats.by_asset_class should be dict, got {type(bac).__name__}"
    if not bac:
        pytest.skip("hf_stats.by_asset_class is empty")

    required = {"profit_factor", "win_rate", "n"}
    bad = []
    for cls, row in bac.items():
        if not isinstance(row, dict):
            bad.append((cls, "non-dict"))
            continue
        missing = required - set(row.keys())
        if missing:
            bad.append((cls, missing))
    assert not bad, f"hf_stats.by_asset_class rows missing keys: {bad}"

    # Sanity ranges
    for cls, row in bac.items():
        if not isinstance(row, dict):
            continue
        pf = row.get("profit_factor")
        wr = row.get("win_rate")
        n = row.get("n")
        if pf is not None:
            assert isinstance(pf, (int, float)) and pf >= 0, \
                f"hf_stats.by_asset_class[{cls}].profit_factor invalid: {pf}"
        if wr is not None:
            assert isinstance(wr, (int, float)) and 0 <= wr <= 100, \
                f"hf_stats.by_asset_class[{cls}].win_rate out of range: {wr}"
        if n is not None:
            assert isinstance(n, int) and n >= 0, \
                f"hf_stats.by_asset_class[{cls}].n should be int>=0: {n}"
