from datetime import datetime, timezone
import json

import pytest

from tools.generate_asset_class_freshness_report import (
    build_report,
    _empty_timeframe_lanes,
    _STANDARD_ASSET_CLASSES,
    _STANDARD_TIMEFRAMES,
)


def test_build_report_computes_metrics_and_staleness(tmp_path):
    payload = {
        "picks": {
            "recent_closed": [
                {
                    "asset_class": "EQUITY",
                    "pnl_pct": 0.05,
                    "closed_at": "2026-04-27T00:00:00+00:00",
                    "timestamp": "2026-04-27T00:00:00+00:00",
                },
                {
                    "asset_class": "EQUITY",
                    "pnl_pct": -0.02,
                    "closed_at": "2026-04-26T00:00:00+00:00",
                    "timestamp": "2026-04-26T00:00:00+00:00",
                },
                {
                    "asset_class": "BOND",
                    "pnl_pct": 0.01,
                    "closed_at": "2026-04-20T00:00:00+00:00",
                    "timestamp": "2026-04-20T00:00:00+00:00",
                },
            ]
        }
    }
    fp = tmp_path / "dash.json"
    fp.write_text(json.dumps(payload), encoding="utf-8")
    now = datetime(2026, 4, 28, tzinfo=timezone.utc)
    out = build_report(fp, stale_days=2.0, now=now)

    by = {r["asset_class"]: r for r in out["asset_classes"]}
    assert by["EQUITY"]["n"] == 2
    assert by["EQUITY"]["win_rate_pct"] == 50.0
    assert by["EQUITY"]["profit_factor"] == 2.5
    assert "BOND" in out["stale_asset_classes"]
    assert "EQUITY" not in out["stale_asset_classes"]


# ---------------------------------------------------------------------------
# Regression tests: empty / invalid input payloads (Goal #1, Wave 2).
#
# `build_report(input_path, stale_days, now)` is the only public consumer of
# the on-disk JSON. It does:
#   1. payload = json.loads(input_path.read_text(...))
#   2. picks   = ((payload.get("picks") or {}).get("recent_closed") or [])
#   3. defensive filter: drop non-list / non-dict shapes inside picks
#
# So an empty `{}` and a dict with the `picks` key missing must both produce
# a well-formed empty report. A malformed JSON file MUST raise (the loader
# itself rejects it). A non-mapping top-level (number / string) currently
# raises `AttributeError` because step 2 calls `.get` on `payload`. We pin
# that to today's behaviour so a future change becomes an explicit decision.
# ---------------------------------------------------------------------------


_NOW = datetime(2026, 4, 28, tzinfo=timezone.utc)


def _write(tmp_path, name, text):
    fp = tmp_path / name
    fp.write_text(text, encoding="utf-8")
    return fp


def test_freshness_report_handles_empty_payload(tmp_path, monkeypatch):
    """Empty `{}` payload -> well-formed empty report, no exceptions."""
    fp = _write(tmp_path, "empty_object.json", json.dumps({}))

    out = build_report(fp, stale_days=2.0, now=_NOW)

    assert isinstance(out, dict)
    assert out["asset_classes"] == []
    assert out["stale_asset_classes"] == []
    assert out["stale_days_threshold"] == 2.0
    assert out["input_path"] == str(fp)
    # generated_at is the `now` we passed in -> deterministic.
    assert out["generated_at"] == _NOW.isoformat()


def test_freshness_report_handles_missing_required_keys(tmp_path, monkeypatch):
    """Dict without `picks` / `recent_closed` -> empty rows, no exceptions."""
    # Two structurally-valid-but-key-missing shapes:
    #   a) top-level dict missing `picks` entirely
    #   b) `picks` present but missing `recent_closed`
    for label, payload in (
        ("no_picks_key", {"foo": "bar", "asset_classes": ["EQUITY"]}),
        ("picks_but_no_recent_closed", {"picks": {"active": [{"x": 1}]}}),
    ):
        fp = _write(tmp_path, f"{label}.json", json.dumps(payload))
        out = build_report(fp, stale_days=2.0, now=_NOW)

        assert out["asset_classes"] == [], f"{label}: expected no rows"
        assert out["stale_asset_classes"] == [], f"{label}: expected no stale"


def test_freshness_report_handles_invalid_json_payload(tmp_path, monkeypatch):
    """Malformed JSON -> json.JSONDecodeError (documented failure mode).

    `build_report` calls `json.loads(...)` directly with no try/except, so a
    truncated / non-JSON file raises. We pin the exception type so a future
    softer-handling change becomes a deliberate, reviewed code update.
    """
    fp = _write(tmp_path, "broken.json", "{this is : not, valid json")

    with pytest.raises(json.JSONDecodeError):
        build_report(fp, stale_days=2.0, now=_NOW)


def test_freshness_report_handles_unexpected_top_level_type(tmp_path, monkeypatch):
    """Top-level scalar / list -> raises AttributeError (today's behaviour).

    `build_report` does `payload.get("picks")` after `json.loads(...)`. If the
    JSON top-level is a number, string, or list, `.get` is missing and an
    `AttributeError` is raised. We pin the current behaviour rather than
    masking it -- if/when the script gains a defensive check, this test
    should be updated alongside the code change.
    """
    for label, raw in (
        ("number", "123"),
        ("string", json.dumps("hello")),
        ("list", json.dumps([{"asset_class": "EQUITY", "pnl_pct": 0.1}])),
    ):
        fp = _write(tmp_path, f"{label}.json", raw)
        with pytest.raises(AttributeError):
            build_report(fp, stale_days=2.0, now=_NOW)


# ---------------------------------------------------------------------------
# B3 2026-05-01: empty_timeframe_lanes extension tests
# ---------------------------------------------------------------------------


class TestEmptyTimeframeLanes:
    def test_no_active_picks_all_lanes_empty(self):
        """With zero active picks every standard lane is empty."""
        lanes = _empty_timeframe_lanes([])
        assert len(lanes) == len(_STANDARD_ASSET_CLASSES) * len(_STANDARD_TIMEFRAMES)

    def test_covered_lane_removed(self):
        """A pick covering CRYPTO×SCALP removes that lane from empty list."""
        pick = {"asset_class": "CRYPTO", "timeframe": "SCALP"}
        lanes = _empty_timeframe_lanes([pick])
        empty_pairs = {(l["asset_class"], l["timeframe"]) for l in lanes}
        assert ("CRYPTO", "SCALP") not in empty_pairs
        assert len(lanes) == len(_STANDARD_ASSET_CLASSES) * len(_STANDARD_TIMEFRAMES) - 1

    def test_unknown_asset_class_ignored(self):
        """A pick with a non-standard asset_class doesn't cover any standard lane."""
        pick = {"asset_class": "FOOBAR", "timeframe": "SCALP"}
        lanes = _empty_timeframe_lanes([pick])
        assert len(lanes) == len(_STANDARD_ASSET_CLASSES) * len(_STANDARD_TIMEFRAMES)

    def test_unknown_timeframe_ignored(self):
        """A pick with a non-standard timeframe doesn't cover any standard lane."""
        pick = {"asset_class": "EQUITY", "timeframe": "MONTHLY"}
        lanes = _empty_timeframe_lanes([pick])
        assert len(lanes) == len(_STANDARD_ASSET_CLASSES) * len(_STANDARD_TIMEFRAMES)

    def test_case_insensitive(self):
        """asset_class and timeframe matching is case-insensitive."""
        pick = {"asset_class": "crypto", "timeframe": "scalp"}
        lanes = _empty_timeframe_lanes([pick])
        empty_pairs = {(l["asset_class"], l["timeframe"]) for l in lanes}
        assert ("CRYPTO", "SCALP") not in empty_pairs

    def test_all_lanes_covered(self):
        """When all standard lanes have at least one pick, empty list is empty."""
        picks = [
            {"asset_class": ac, "timeframe": tf}
            for ac in _STANDARD_ASSET_CLASSES
            for tf in _STANDARD_TIMEFRAMES
        ]
        lanes = _empty_timeframe_lanes(picks)
        assert lanes == []

    def test_output_schema(self):
        """Each entry has exactly asset_class and timeframe keys."""
        lanes = _empty_timeframe_lanes([])
        for lane in lanes[:5]:
            assert set(lane.keys()) == {"asset_class", "timeframe"}
            assert lane["asset_class"] in _STANDARD_ASSET_CLASSES
            assert lane["timeframe"] in _STANDARD_TIMEFRAMES


class TestBuildReportEmptyLanes:
    def test_empty_lanes_in_report_output(self, tmp_path):
        """build_report includes empty_timeframe_lanes in output."""
        payload = {
            "picks": {
                "recent_closed": [],
                "active": [{"asset_class": "EQUITY", "timeframe": "SWING"}],
            }
        }
        fp = tmp_path / "dash.json"
        fp.write_text(json.dumps(payload), encoding="utf-8")
        out = build_report(fp, stale_days=2.0, now=_NOW)

        assert "empty_timeframe_lanes" in out
        empty_pairs = {(l["asset_class"], l["timeframe"]) for l in out["empty_timeframe_lanes"]}
        assert ("EQUITY", "SWING") not in empty_pairs
        assert ("EQUITY", "SCALP") in empty_pairs

    def test_empty_lanes_all_empty_when_no_active(self, tmp_path):
        """When picks.active is missing, all lanes are empty."""
        payload = {"picks": {"recent_closed": []}}
        fp = tmp_path / "dash.json"
        fp.write_text(json.dumps(payload), encoding="utf-8")
        out = build_report(fp, stale_days=2.0, now=_NOW)

        expected_count = len(_STANDARD_ASSET_CLASSES) * len(_STANDARD_TIMEFRAMES)
        assert len(out["empty_timeframe_lanes"]) == expected_count

    def test_empty_payload_has_empty_lanes_key(self, tmp_path):
        """Even empty payload produces empty_timeframe_lanes key in output."""
        fp = tmp_path / "empty.json"
        fp.write_text(json.dumps({}), encoding="utf-8")
        out = build_report(fp, stale_days=2.0, now=_NOW)

        assert "empty_timeframe_lanes" in out
        assert isinstance(out["empty_timeframe_lanes"], list)

    def test_existing_tests_still_pass(self, tmp_path):
        """Regression: original build_report metrics not broken by B3 extension."""
        payload = {
            "picks": {
                "recent_closed": [
                    {"asset_class": "EQUITY", "pnl_pct": 0.05,
                     "closed_at": "2026-04-27T00:00:00+00:00",
                     "timestamp": "2026-04-27T00:00:00+00:00"},
                    {"asset_class": "EQUITY", "pnl_pct": -0.02,
                     "closed_at": "2026-04-26T00:00:00+00:00",
                     "timestamp": "2026-04-26T00:00:00+00:00"},
                ],
                "active": [{"asset_class": "EQUITY", "timeframe": "INTRADAY"}],
            }
        }
        fp = tmp_path / "dash.json"
        fp.write_text(json.dumps(payload), encoding="utf-8")
        out = build_report(fp, stale_days=2.0, now=_NOW)

        by = {r["asset_class"]: r for r in out["asset_classes"]}
        assert by["EQUITY"]["n"] == 2
        assert by["EQUITY"]["win_rate_pct"] == 50.0
        # B3 fields present
        assert "empty_timeframe_lanes" in out
        empty_pairs = {(l["asset_class"], l["timeframe"]) for l in out["empty_timeframe_lanes"]}
        assert ("EQUITY", "INTRADAY") not in empty_pairs

