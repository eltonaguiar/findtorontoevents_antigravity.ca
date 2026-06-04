"""Performance-metric invariant guards for the /audit dashboard payload.

Locks down the bugs documented in reports/AUDIT_STAT_VALIDATION_2026-05-22.md so
they cannot silently regress (or, for the still-broken ones, so the suite
auto-flips to green the moment they are fixed).

Source of truth: audit_dashboard/data/dashboard_data.json (the live payload).
Per CLAUDE.md we never run the dashboard generator locally — these are pure
schema/value checks against the committed payload.

Conventions follow tests/test_audit_dashboard_payload.py and
tests/test_dashboard_payload_contract.py:
  * stdlib + pytest only, no production imports
  * payload loaded once at module level; pytest.skip (not fail) when absent
  * one invariant per test_ function for independent failure reporting

Bug-status legend (2026-05-22 audit):
  * FIXED  -> card math now uses compounded headline. Tests assert normally.
  * BROKEN -> by_asset_class coherence + status-vs-pnl writer bug NOT fixed.
              Those tests are xfail(strict=False): they document the bug and
              auto-promote to PASS once the underlying code is corrected.

Run:
    python3 -m pytest tests/test_audit_metric_invariants.py -v
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Payload load (graceful skip on missing / unparseable file)
# ---------------------------------------------------------------------------

PAYLOAD_PATH = (
    Path(__file__).resolve().parent.parent
    / "audit_dashboard"
    / "data"
    / "dashboard_data.json"
)

KNOWN_BUG_REASON = "known bug — see reports/AUDIT_STAT_VALIDATION_2026-05-22.md"


def _load_payload():
    if not PAYLOAD_PATH.exists():
        pytest.skip(
            f"dashboard_data.json missing at {PAYLOAD_PATH} — run the audit "
            "pipeline or pull origin/main copy before running locally.",
            allow_module_level=True,
        )
    try:
        with PAYLOAD_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        pytest.skip(f"dashboard_data.json is not valid JSON: {exc}", allow_module_level=True)


PAYLOAD = _load_payload()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _by_asset_class():
    bac = PAYLOAD.get("performance", {}).get("by_asset_class")
    if not isinstance(bac, dict) or not bac:
        pytest.skip("performance.by_asset_class absent or empty")
    return bac


def _asset_class_health():
    ach = PAYLOAD.get("performance", {}).get("asset_class_health")
    if not isinstance(ach, dict) or not ach:
        pytest.skip("performance.asset_class_health absent or empty")
    return ach


def _recent_closed():
    rc = PAYLOAD.get("picks", {}).get("recent_closed")
    if not isinstance(rc, list):
        pytest.skip("picks.recent_closed absent or not a list")
    if not rc:
        pytest.skip("picks.recent_closed empty")
    return rc


def _flat_count(row: dict) -> int:
    """A 'flat'/breakeven bucket may or may not be present under several names."""
    for k in ("flat", "flats", "breakeven", "ties"):
        if k in row and isinstance(row[k], (int, float)):
            return int(row[k])
    return 0


_WIN_TOKENS = {"WON", "WIN", "W"}
_LOSS_TOKENS = {"LOST", "LOSS", "L"}


def _status_str(row: dict):
    return row.get("status") or row.get("_outcome") or row.get("outcome")


def _is_win_status(s) -> bool:
    return str(s).strip().upper() in _WIN_TOKENS


def _is_loss_status(s) -> bool:
    return str(s).strip().upper() in _LOSS_TOKENS


# ---------------------------------------------------------------------------
# 1. by_asset_class coherence
#    1a (KNOWN BUG — xfail): `closed` disagrees with the wins+losses+flat it
#       should derive from.  FUTURES closed=214 but w+l=2; CRYPTO closed=10330
#       but w+l=5997 — divergence of 2-4x.  For a closed-trade bucket the
#       resolved count and `closed` must be equal.
#    1b (FIXED — assert normally): win_rate must reconstruct from
#       wins/(wins+losses+flat) — this invariant currently holds.
# ---------------------------------------------------------------------------

# Some closed picks may legitimately be unresolved/pending even though they
# left the active set; allow a small slack before flagging incoherence.
CLOSED_VS_RESOLVED_REL_SLACK = 0.05  # 5%


@pytest.mark.xfail(reason=KNOWN_BUG_REASON, strict=False)
def test_by_asset_class_closed_matches_wins_losses():
    """`closed` must agree with wins + losses + flat for every asset class.

    The audit found `closed` inflated 2-4x above the win/loss counts it is
    supposedly derived from — numbers no card can reconstruct from any trade
    list.  Once the aggregation is fixed this test auto-promotes to PASS.
    """
    bac = _by_asset_class()
    incoherent = []
    for cls, row in bac.items():
        if not isinstance(row, dict):
            continue
        closed = row.get("closed")
        wins = row.get("wins")
        losses = row.get("losses")
        if not all(isinstance(v, int) for v in (closed, wins, losses)):
            continue
        if closed == 0:
            continue
        resolved = wins + losses + _flat_count(row)
        slack = max(1, int(closed * CLOSED_VS_RESOLVED_REL_SLACK))
        if abs(closed - resolved) > slack:
            incoherent.append(
                (cls, f"closed={closed} vs wins+losses+flat={resolved}")
            )
    assert not incoherent, (
        "by_asset_class rows where 'closed' disagrees with wins/losses/flat: "
        f"{incoherent}"
    )


def test_by_asset_class_win_rate_reconstructs_from_wins_losses():
    """win_rate must equal wins/(wins+losses+flat)*100 within tolerance.
    Buckets with zero resolved trades are exempt (0/0 -> 0.0 by convention)."""
    bac = _by_asset_class()
    tol = 1.0  # percentage points
    mismatched = []
    for cls, row in bac.items():
        if not isinstance(row, dict):
            continue
        wr = row.get("win_rate")
        wins = row.get("wins")
        losses = row.get("losses")
        if wr is None or not all(isinstance(v, int) for v in (wins, losses)):
            continue
        denom = wins + losses + _flat_count(row)
        if denom <= 0:
            continue  # 0/0 — win_rate is conventionally 0.0, not a violation
        expected = wins / denom * 100.0
        if abs(float(wr) - expected) > tol:
            mismatched.append(
                (cls, f"stated wr={wr} vs reconstructed={expected:.2f}")
            )
    assert not mismatched, (
        "by_asset_class win_rate does not reconstruct from wins/losses: "
        f"{mismatched}"
    )


# ---------------------------------------------------------------------------
# 2. summary PnL sanity  (FIXED — assert normally)
#    The honest headline is the compounded equal-weight return, NOT the naive
#    arithmetic sum (~2225) which inflates by ~40x.
# ---------------------------------------------------------------------------

def test_summary_compounded_ew_exists():
    summary = PAYLOAD.get("summary")
    if not isinstance(summary, dict):
        pytest.skip("summary block absent")
    assert "total_pnl_pct_compounded_rolling_100" in summary, (
        "summary.total_pnl_pct_compounded_ew missing — this is the honest "
        "headline return; the dashboard must not fall back to the naive sum."
    )


def test_headline_total_pnl_is_the_compounded_value():
    """summary.total_pnl_pct (the headline) must be the rolling-100 compound,
    never the naive raw sum."""
    summary = PAYLOAD.get("summary")
    if not isinstance(summary, dict):
        pytest.skip("summary block absent")
    headline = summary.get("total_pnl_pct")
    compounded = summary.get("total_pnl_pct_compounded_rolling_100")
    if headline is None or compounded is None:
        pytest.skip("total_pnl_pct or total_pnl_pct_compounded_rolling_100 absent")
    assert math.isclose(float(headline), float(compounded), rel_tol=1e-6, abs_tol=1e-6), (
        f"headline total_pnl_pct={headline} is NOT the rolling-100 compound "
        f"{compounded}. The honest headline must be the compounded figure "
        "(see audit 2026-06-04: EW deprecated, replaced by rolling-100)."
    )


def test_raw_sum_is_not_the_headline():
    """If total_pnl_pct_sum_raw is present it must be clearly distinct from
    the headline — it is a diagnostic sum, NOT a return."""
    summary = PAYLOAD.get("summary")
    if not isinstance(summary, dict):
        pytest.skip("summary block absent")
    raw = summary.get("total_pnl_pct_sum_raw")
    headline = summary.get("total_pnl_pct")
    if raw is None or headline is None:
        pytest.skip("total_pnl_pct_sum_raw or total_pnl_pct absent")
    # The raw sum vastly exceeds the honest return; they must not be equal.
    assert not math.isclose(float(raw), float(headline), rel_tol=1e-3), (
        f"summary.total_pnl_pct ({headline}) equals the naive sum "
        f"total_pnl_pct_sum_raw ({raw}) — the headline must be the "
        "compounded value, not the inflated arithmetic sum."
    )


def test_compounded_ew_within_sane_band():
    """The compounded headline must be finite and within a plausible band
    (-100% wipeout floor to +10000% ceiling)."""
    summary = PAYLOAD.get("summary")
    if not isinstance(summary, dict):
        pytest.skip("summary block absent")
    compounded = summary.get("total_pnl_pct_compounded_rolling_100")
    if compounded is None:
        pytest.skip("total_pnl_pct_compounded_rolling_100 absent")
    val = float(compounded)
    assert math.isfinite(val), f"compounded EW return is not finite: {val}"
    assert -100.0 <= val <= 10000.0, (
        f"compounded EW return {val}% outside sane band [-100, 10000] — "
        "suggests the compounding/capping logic regressed."
    )


# ---------------------------------------------------------------------------
# 3. asset_class_health internal consistency  (FIXED — assert normally)
#    n == resolved_n; wr_pct/win_rate agree; pf/profit_factor agree; n >= 0.
# ---------------------------------------------------------------------------

def test_asset_class_health_n_equals_resolved_n():
    ach = _asset_class_health()
    mismatched = []
    for cls, row in ach.items():
        if not isinstance(row, dict):
            continue
        n = row.get("n")
        resolved_n = row.get("resolved_n")
        if n is None or resolved_n is None:
            continue
        if int(n) != int(resolved_n):
            mismatched.append((cls, f"n={n} != resolved_n={resolved_n}"))
    assert not mismatched, (
        f"asset_class_health n != resolved_n: {mismatched}"
    )


def test_asset_class_health_n_non_negative():
    ach = _asset_class_health()
    bad = []
    for cls, row in ach.items():
        if not isinstance(row, dict):
            continue
        for key in ("n", "resolved_n"):
            v = row.get(key)
            if v is not None and (not isinstance(v, int) or v < 0):
                bad.append((cls, key, v))
    assert not bad, f"asset_class_health n/resolved_n must be int>=0: {bad}"


def test_asset_class_health_wr_alias_agrees():
    """wr_pct must equal win_rate when both are present."""
    ach = _asset_class_health()
    mismatched = []
    for cls, row in ach.items():
        if not isinstance(row, dict):
            continue
        wr = row.get("win_rate")
        wr_pct = row.get("wr_pct")
        if wr is None or wr_pct is None:
            continue
        if not math.isclose(float(wr), float(wr_pct), rel_tol=1e-6, abs_tol=1e-6):
            mismatched.append((cls, f"win_rate={wr} != wr_pct={wr_pct}"))
    assert not mismatched, (
        f"asset_class_health win_rate vs wr_pct disagree: {mismatched}"
    )


def test_asset_class_health_pf_alias_agrees():
    """pf must equal profit_factor when both are present."""
    ach = _asset_class_health()
    mismatched = []
    for cls, row in ach.items():
        if not isinstance(row, dict):
            continue
        pf = row.get("profit_factor")
        pf_alias = row.get("pf")
        if pf is None or pf_alias is None:
            continue
        if not math.isclose(float(pf), float(pf_alias), rel_tol=1e-6, abs_tol=1e-6):
            mismatched.append((cls, f"profit_factor={pf} != pf={pf_alias}"))
    assert not mismatched, (
        f"asset_class_health profit_factor vs pf disagree: {mismatched}"
    )


# ---------------------------------------------------------------------------
# 4. status vs pnl_pct contradiction  (KNOWN BUG — xfail)
#    Resolver writer bug: status=WON with pnl_pct<0 (or LOST with pnl_pct>0).
#    The audit confirmed 20+ contradicting rows. We assert the contradiction
#    RATE is below a small threshold; once the resolver is fixed this passes.
# ---------------------------------------------------------------------------

CONTRADICTION_RATE_THRESHOLD = 0.001  # 0.1% — effectively zero tolerance


@pytest.mark.xfail(reason=KNOWN_BUG_REASON, strict=False)
def test_status_vs_pnl_sign_contradiction_rate():
    rc = _recent_closed()
    resolved = 0
    contradictions = []
    for i, row in enumerate(rc):
        if not isinstance(row, dict):
            continue
        status = _status_str(row)
        pnl = row.get("pnl_pct")
        if pnl is None or status is None:
            continue
        win = _is_win_status(status)
        loss = _is_loss_status(status)
        if not (win or loss):
            continue  # UNRESOLVED / other — not a resolved row
        resolved += 1
        try:
            pnl_val = float(pnl)
        except (TypeError, ValueError):
            continue
        if win and pnl_val < 0:
            contradictions.append((i, row.get("symbol"), status, pnl_val))
        elif loss and pnl_val > 0:
            contradictions.append((i, row.get("symbol"), status, pnl_val))
    if resolved == 0:
        pytest.skip("no resolved rows in recent_closed")
    rate = len(contradictions) / resolved
    assert rate <= CONTRADICTION_RATE_THRESHOLD, (
        f"status-vs-pnl_pct contradiction rate {rate:.4%} "
        f"({len(contradictions)}/{resolved}) exceeds "
        f"{CONTRADICTION_RATE_THRESHOLD:.2%} — resolver writer bug. "
        f"examples: {contradictions[:5]}"
    )


# ---------------------------------------------------------------------------
# 5. recent_closed bounded + required fields  (FIXED — assert normally)
# ---------------------------------------------------------------------------

# MAX_CLOSED_PICKS = 3500 in dashboard_generator.py:231. Allow a small headroom
# for off-by-one / future bumps, but the array must not be unbounded.
RECENT_CLOSED_HARD_CEILING = 4000


def test_recent_closed_is_bounded():
    rc = _recent_closed()
    assert len(rc) <= RECENT_CLOSED_HARD_CEILING, (
        f"picks.recent_closed has {len(rc)} rows — exceeds the "
        f"{RECENT_CLOSED_HARD_CEILING} ceiling (MAX_CLOSED_PICKS=3500). "
        "An unbounded array bloats the payload and the cards."
    )


def test_recent_closed_rows_have_required_fields():
    rc = _recent_closed()
    incomplete = []
    for i, row in enumerate(rc):
        if not isinstance(row, dict):
            incomplete.append((i, "non-dict"))
            continue
        # pnl_pct must be present
        if "pnl_pct" not in row:
            incomplete.append((i, row.get("symbol"), "missing pnl_pct"))
            continue
        # an outcome label under any accepted key
        if _status_str(row) is None:
            incomplete.append((i, row.get("symbol"), "missing status/_outcome"))
            continue
        # identity fields
        missing = [k for k in ("asset_class", "symbol") if not row.get(k)]
        if missing:
            incomplete.append((i, row.get("symbol"), f"missing {missing}"))
    assert not incomplete, (
        f"recent_closed rows missing required fields: {incomplete[:5]} "
        f"(total {len(incomplete)})"
    )
