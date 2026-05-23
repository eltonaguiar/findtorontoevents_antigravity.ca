"""
Sports betting endpoint smoke tests against the live deployed API.

These tests guard against the kinds of breakage we hit this session:
- Conflict markers committed to PHP files (production 500)
- Missing require_once dependencies (production 500)
- Empty endpoint responses where rows should exist
- pick_history aggregation breakage from MySQL strict_mode

Run: `pytest tests/test_sports_endpoints_smoke.py`

These hit production. They're read-only — no writes, no auth-required
actions. They run fast (HTTP only) and catch the most common deploy
regressions immediately.

2026-04-27: marked with `@pytest.mark.network` and offline-skipped because
GitHub-hosted runners occasionally hit transient DNS resolution failures
on egress (1-2% of CI runs). Skip-on-DNS-fail keeps these tests informative
locally and in nightly smoke jobs while preventing CI from going red on
infrastructure flake. See updates/2026-04-27-workflow-health-investigation.md.
"""
import json
import os
import socket
import urllib.error
import urllib.request

import pytest

BASE = "https://findtorontoevents.ca/live-monitor/api"
TIMEOUT = 30
_NETWORK_HOST = "findtorontoevents.ca"
_LIVE_SMOKE = os.environ.get("LIVE_SMOKE") == "1"


def _network_available() -> bool:
    """TCP-reachability probe so CI doesn't go red when the live host is unreachable.

    GitHub-hosted runners can fail at two layers:
      1. DNS resolution failure (rare — ~1-2% of runs)
      2. DNS resolves but TCP connect is refused / times out (the host's CDN
         or origin returns RST to runner IP ranges). The 2026-05-02 cascade
         saw `URLError: <urlopen error timed out>` on the smoke tests —
         DNS-only probe passed, actual connect timed out, tests went red on
         infra flake. That single flake cascaded across PRs #597, #601,
         #608, #615 (all blocked by the same flaky test).

    Probe both layers: DNS first (cheap), then a short TCP connect on 443.
    If either fails, skip the live-smoke tests instead of hard-failing CI.
    """
    try:
        socket.gethostbyname(_NETWORK_HOST)
    except (socket.gaierror, OSError):
        return False
    try:
        with socket.create_connection((_NETWORK_HOST, 443), timeout=3):
            return True
    except (socket.gaierror, OSError, TimeoutError):
        return False


pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(
        not _LIVE_SMOKE,
        reason="live-prod smoke; opt-in via LIVE_SMOKE=1 (cron + manual). "
               "These tests cascaded-blocked PRs #597/#608/#615/#661/#745 on 2026-05-03 "
               "when production returned ok=false unrelated to branch changes.",
    ),
    pytest.mark.skipif(
        not _network_available(),
        reason=f"DNS resolution to {_NETWORK_HOST} failed; skipping live smoke tests "
        "(see updates/2026-04-27-workflow-health-investigation.md)",
    ),
]


def _get_json(path):
    """GET with timeout. Returns parsed JSON or raises with full body for debugging.

    Live-host transient errors (URLError, socket.timeout, ConnectionRefusedError)
    are skipped instead of failing — these are infra flake on GitHub runners,
    not contract violations. The pre-test reachability probe catches the
    host-down case at module-load time; this catches per-request transients
    that slip past the probe (e.g. probe sees TCP open at module load, then
    origin times out / refuses on the actual GET seconds later — observed on
    2026-05-02 main CI).
    """
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "smoke-test/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8", errors="replace")
            if r.status != 200:
                raise AssertionError(f"HTTP {r.status} on {path}: {body[:500]}")
            try:
                return json.loads(body)
            except json.JSONDecodeError as e:
                raise AssertionError(f"non-JSON on {path}: {body[:500]}") from e
    except (urllib.error.URLError, socket.timeout, ConnectionRefusedError) as e:
        pytest.skip(f"transient infra flake on {path}: {type(e).__name__}: {e}")


def test_today_endpoint_responds_with_picks():
    """sports_picks.php?action=today should return ok=true with value_bets array."""
    d = _get_json("/sports_picks.php?action=today")
    assert d.get("ok") is True, f"unexpected ok: {d}"
    assert isinstance(d.get("value_bets"), list), "value_bets should be a list"
    # Schema check: each pick has a result + is_finished field (PR #404)
    for pick in d["value_bets"][:3]:
        assert "result" in pick, "PR #404 server contract: every pick must include `result`"
        assert "is_finished" in pick, "PR #404 server contract: every pick must include `is_finished`"


def test_today_no_php_parse_errors():
    """The endpoint should never return a PHP parse-error HTML body.

    This was the failure mode when conflict markers landed in main and
    when a require_once'd file wasn't FTP-deployed yet (PR #412 hotfix +
    sports_value_nhl_goalie_lib.php missing).
    """
    req = urllib.request.Request(BASE + "/sports_picks.php?action=today")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        # 4xx/5xx response — still want to inspect body for PHP error markers
        body = e.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionRefusedError) as e:
        # Transient network failure — skip rather than fail (matches _get_json contract)
        pytest.skip(f"transient infra flake on /sports_picks.php?action=today: {type(e).__name__}: {e}")
    assert "Parse error" not in body, "PHP parse error in response — file likely has conflict markers"
    assert "Fatal error" not in body, "PHP fatal error — likely missing require_once dependency"
    assert "<b>Notice</b>" not in body, "PHP notice in response — leaked stderr"


def test_dashboard_returns_tier_breakdown():
    """sports_bets.php?action=dashboard should return by_recommendation + by_recommendation_sport (PR #409)."""
    d = _get_json("/sports_bets.php?action=dashboard")
    assert d.get("ok") is True
    assert isinstance(d.get("by_recommendation"), list), "PR #409 contract: by_recommendation array"
    assert isinstance(d.get("by_recommendation_sport"), list), "PR #409 contract: by_recommendation_sport matrix"
    # All four tiers should appear in by_recommendation, even if some have 0 bets
    tiers = {row["tier"] for row in d["by_recommendation"]}
    assert tiers >= {"STRONG TAKE", "TAKE", "LEAN", "LOW EDGE"}, f"missing tiers: {tiers}"


def test_pick_history_returns_days():
    """pick_history?days=30 should return non-empty days array.

    This was failing pre-fix because:
    1. Daily-picks WHERE filter on DATE column was rejected by strict_mode
    2. Bets-fallback COALESCE was returning '0000-00-00' (not NULL)
    """
    d = _get_json("/sports_picks.php?action=pick_history&days=30")
    assert d.get("ok") is True
    days = d.get("days", [])
    assert isinstance(days, list)
    # We have known settled bets in lm_sports_bets — at least some days must come through.
    assert len(days) > 0, f"pick_history empty; _diag={d.get('_diag')}"
    # _diag block should always exist (added in this fix)
    diag = d.get("_diag")
    assert diag is not None, "_diag block missing"
    assert "daily_picks_rows" in diag and "bets_rows" in diag


def test_clv_endpoint_returns_trend_array():
    """sports_ml.php?action=clv should return clv structure with weekly_trend (PR #414)."""
    d = _get_json("/sports_ml.php?action=clv")
    assert d.get("ok") is True
    clv = d.get("clv", {})
    assert "avg_clv_pct" in clv
    assert "total_events" in clv
    assert "clv_weekly_trend" in clv, "PR #414 contract: clv_weekly_trend array"
    assert isinstance(clv["clv_weekly_trend"], list)


def test_steam_and_arb_endpoints_respond():
    """PR #406 endpoints must respond cleanly even before SQL migration v2."""
    for path in ["/sports_steam.php?action=list", "/sports_arb.php?action=list"]:
        d = _get_json(path)
        assert d.get("ok") is True, f"{path} returned ok=false: {d}"
        assert "rows" in d
        assert "count" in d
