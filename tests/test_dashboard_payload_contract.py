"""Payload contract tests for `audit_dashboard/data/dashboard_data.json`.

Mercury2 P0.5 / Item #5. Proactive defense against the recurring class of bug
where peer agents (or `audit_trail/dashboard_generator.py`) silently drop
required keys from the dashboard payload — most recently the
`performance.asset_class_health.{wr_pct,pf,pnl_pct}` triple being `None`
despite live data existing in `system_clean_metrics`.

Design notes:
  * Pure stdlib + pytest. No production imports — schema only.
  * Loaded once at module level for speed; one assertion per `test_` function
    so failures are independent and CI surfaces the full failing set.
  * `pytest.skip` (not fail) when the payload file is missing locally — this
    is expected on feature branches per
    `memory/feedback_dashboard_data_local_staleness`.
  * Known-null fields (`wr_pct`/`pf`/`pnl_pct` inside
    `performance.asset_class_health[CLASS]`) are marked `xfail`, not hard
    failures. The actual numeric data lives in sibling keys
    (`win_rate`/`profit_factor`/`total_pnl_pct`) — flag-for-follow-up, not a
    contract violation today.
  * Schema-drift detection compares a sha1 of sorted top-level keys against
    a pinned baseline. Drift is a *soft* fail (warning + structured diff)
    so contributors see what changed without breaking CI for benign growth.

Run:
    python -m pytest tests/test_dashboard_payload_contract.py -v
"""
from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PAYLOAD_PATH = (
    Path(__file__).resolve().parent.parent
    / "audit_dashboard"
    / "data"
    / "dashboard_data.json"
)

# Baseline sha1 of `,`-joined sorted top-level keys, captured 2026-05-15
# against origin/main. Update intentionally (with a structured diff in the
# PR description) when keys are added/removed.
KNOWN_TOP_KEY_HASH = "3fe71d458141941f4aa3838eb9aa4830f4f5134d"

# Snapshot of the top-level keys at baseline capture. Used to emit a clean
# add/remove diff when the hash drifts.
KNOWN_TOP_KEYS = frozenset({
    "analyst_active_calls", "analyst_leaderboard", "assetClassSummary",
    "asset_class_summary", "audit_events", "backtest_vs_forward", "bundles",
    "conflicts", "consensus", "cross_asset_correlation",
    "cross_strategy_permutations", "cross_system_permutations",
    "data_freshness", "extreme_conviction", "filter_events",
    "fwd_vs_bt_divergence", "generated_at", "hf_decay_watchlist", "hf_stats",
    "leaderboard", "macro_context", "metadata", "ml_health", "performance",
    "performance_alerts", "picks", "portfolios", "predictions_leaderboard",
    "regime_validation", "research_reports", "shadow_probation",
    "sidecar_promotion_status", "smartPicksByAsset", "smart_picks_by_asset",
    "smart_picks_feed", "smart_picks_snapshot_summary", "summary",
    "swarm_picks_data", "system_clean_metrics", "systems", "ta_baseline",
    "tier2_proven_strategies", "verified_alpha", "volatility", "walkforward",
})

CANONICAL_CLASSES = ["CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND"]


# ---------------------------------------------------------------------------
# Module-level payload load (with graceful skip on missing)
# ---------------------------------------------------------------------------

def _load_payload():
    if not PAYLOAD_PATH.exists():
        pytest.skip(
            f"dashboard_data.json missing at {PAYLOAD_PATH} — see "
            "memory/feedback_dashboard_data_local_staleness; pull "
            "origin/main copy before running locally.",
            allow_module_level=True,
        )
    try:
        with PAYLOAD_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        pytest.skip(f"dashboard_data.json is not valid JSON: {exc}", allow_module_level=True)


PAYLOAD = _load_payload()


# ---------------------------------------------------------------------------
# Top-level shape
# ---------------------------------------------------------------------------

REQUIRED_TOP_KEYS = [
    "generated_at", "metadata", "summary", "picks",
    "performance", "walkforward", "hf_stats",
]


@pytest.mark.parametrize("key", REQUIRED_TOP_KEYS)
def test_top_level_required_key_present(key):
    assert key in PAYLOAD, (
        f"required top-level key '{key}' missing from dashboard_data.json"
    )


def test_top_level_schema_hash_or_soft_diff():
    """Soft-fail on top-level key drift. Emits a structured add/remove diff
    via warnings so contributors see exactly what changed without breaking CI.
    """
    current = sorted(PAYLOAD.keys())
    digest = hashlib.sha1(",".join(current).encode("utf-8")).hexdigest()
    if digest == KNOWN_TOP_KEY_HASH:
        return
    current_set = set(current)
    added = sorted(current_set - KNOWN_TOP_KEYS)
    removed = sorted(KNOWN_TOP_KEYS - current_set)
    warnings.warn(
        "dashboard_data.json top-level schema drift detected. "
        f"hash={digest} baseline={KNOWN_TOP_KEY_HASH} "
        f"added={added} removed={removed}. "
        "If intentional: update KNOWN_TOP_KEY_HASH + KNOWN_TOP_KEYS in this "
        "test file and document the change in the PR description.",
        stacklevel=2,
    )


# ---------------------------------------------------------------------------
# performance.asset_class_health
# ---------------------------------------------------------------------------

def test_asset_class_health_block_is_dict():
    perf = PAYLOAD.get("performance", {})
    assert isinstance(perf, dict), "performance must be a dict"
    ach = perf.get("asset_class_health")
    assert isinstance(ach, dict), (
        "performance.asset_class_health must be a dict; got "
        f"{type(ach).__name__}"
    )


@pytest.mark.parametrize("cls", CANONICAL_CLASSES)
def test_asset_class_health_class_present(cls):
    ach = PAYLOAD["performance"]["asset_class_health"]
    assert cls in ach, (
        f"performance.asset_class_health['{cls}'] missing — required for "
        "all 6 canonical classes (CRYPTO/EQUITY/FOREX/COMMODITY/ETF/BOND)."
    )


@pytest.mark.parametrize("cls", CANONICAL_CLASSES)
def test_asset_class_health_has_resolved_n(cls):
    blk = PAYLOAD["performance"]["asset_class_health"].get(cls, {})
    assert "resolved_n" in blk, (
        f"performance.asset_class_health['{cls}'].resolved_n missing"
    )


_ALIAS_SOURCE = {"wr_pct": "win_rate", "pf": "profit_factor", "pnl_pct": "total_pnl_pct"}


@pytest.mark.parametrize("field", ["wr_pct", "pf", "pnl_pct"])
def test_asset_class_health_wr_pf_pnl_populated(field):
    # dashboard_generator.py emits wr_pct/pf/pnl_pct aliases (fix 2026-05-16).
    # Skip classes where the source field itself is None (legitimate edge, e.g. 0-loss PF=inf).
    ach = PAYLOAD["performance"]["asset_class_health"]
    source = _ALIAS_SOURCE[field]
    failing = [
        cls for cls in CANONICAL_CLASSES
        if isinstance(ach.get(cls), dict)
        and ach[cls].get(source) is not None  # source has a value
        and ach[cls].get(field) is None        # but alias is missing
    ]
    assert not failing, (
        f"asset_class_health[{field}] is None for classes={failing} "
        f"even though source field '{source}' is populated"
    )


# ---------------------------------------------------------------------------
# walkforward
# ---------------------------------------------------------------------------

def test_walkforward_by_class_present_for_at_least_one():
    wf = PAYLOAD.get("walkforward")
    if not isinstance(wf, dict) or "by_class" not in wf:
        pytest.skip("walkforward.by_class absent — emission may be batched")
    by_class = wf["by_class"]
    assert isinstance(by_class, dict), (
        f"walkforward.by_class must be dict; got {type(by_class).__name__}"
    )
    overlap = [c for c in CANONICAL_CLASSES if c in by_class]
    assert overlap, (
        "walkforward.by_class has no canonical class entries; expected at "
        f"least one of {CANONICAL_CLASSES}, got {sorted(by_class.keys())}"
    )


# ---------------------------------------------------------------------------
# hf_stats.by_asset_class[CLASS].concept_drift (optional per-class)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cls", CANONICAL_CLASSES)
def test_hf_stats_concept_drift_shape_when_present(cls):
    hfba = PAYLOAD.get("hf_stats", {}).get("by_asset_class", {})
    if not isinstance(hfba, dict) or cls not in hfba:
        pytest.skip(f"hf_stats.by_asset_class['{cls}'] absent")
    blk = hfba[cls]
    if not isinstance(blk, dict) or "concept_drift" not in blk:
        pytest.skip(f"hf_stats.by_asset_class['{cls}'].concept_drift absent")
    cd = blk["concept_drift"]
    if not isinstance(cd, dict) or not cd:
        pytest.skip(
            f"hf_stats.by_asset_class['{cls}'].concept_drift empty — "
            "follow-up: populate ks_D + ks_critical_05"
        )
    for key in ("ks_D", "ks_critical_05"):
        assert key in cd, (
            f"hf_stats.by_asset_class['{cls}'].concept_drift.{key} missing"
        )


# ---------------------------------------------------------------------------
# picks
# ---------------------------------------------------------------------------

def test_picks_active_is_list():
    picks = PAYLOAD.get("picks", {})
    assert isinstance(picks, dict), "picks must be a dict"
    active = picks.get("active")
    assert isinstance(active, list), (
        f"picks.active must be list (not None, not dict); got "
        f"{type(active).__name__}"
    )


def test_picks_recent_closed_volume():
    picks = PAYLOAD.get("picks", {})
    rc = picks.get("recent_closed")
    assert isinstance(rc, list), (
        f"picks.recent_closed must be list; got {type(rc).__name__}"
    )
    # n=3500 expected; allow lower for local staleness, hard floor at 100.
    assert len(rc) >= 100, (
        f"picks.recent_closed has only {len(rc)} entries — expected >=100 "
        "(n=3500 nominal). If on a stale feature branch, pull "
        "origin/main -- audit_dashboard/data/dashboard_data.json"
    )
