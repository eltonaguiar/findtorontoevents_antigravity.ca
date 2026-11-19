"""The intraday stop must shadow exactly the measured slices and nothing else."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine.intraday_stop import (  # noqa: E402
    alpha_effect, annotate_buckets, annotate_pick, annotate_picks, is_shadow_only,
)


def test_policy_shadows_only_the_measured_slices():
    assert is_shadow_only("CRYPTO", "INTRADAY") is True
    assert is_shadow_only("crypto", "intraday") is True
    assert is_shadow_only("ETF", "INTRADAY") is True
    # the surviving slice must never be shadowed
    assert is_shadow_only("CRYPTO", "POSITION") is False
    # classes with no measured intraday harm keep the money path
    assert is_shadow_only("EQUITY", "INTRADAY") is False
    assert is_shadow_only("CRYPTO", "SWING") is False
    assert is_shadow_only("CRYPTO", "") is False


def test_annotate_keeps_the_row_and_flags_it():
    pick = {"id": "p1", "asset_class": "CRYPTO", "trade_timeframe": "INTRADAY",
            "score": 91, "symbol": "BTCUSDT"}
    out = annotate_pick(pick)
    assert out["money_path"] is False and out["shadow"] is True
    assert out["shadow_reason"] == "intraday_stop:CRYPTO/INTRADAY"
    assert out["score"] == 91 and out["symbol"] == "BTCUSDT"   # nothing is deleted
    kept = annotate_pick({"asset_class": "CRYPTO", "timeframe": "POSITION"})
    assert kept["money_path"] is True and kept["shadow"] is False


def test_annotate_picks_counts_without_dropping():
    picks = [
        {"asset_class": "CRYPTO", "trade_timeframe": "INTRADAY"},
        {"asset_class": "CRYPTO", "trade_timeframe": "POSITION"},
        {"asset_class": "ETF", "timeframe": "INTRADAY"},
        {"asset_class": "EQUITY", "timeframe": "INTRADAY"},
    ]
    summary = annotate_picks(picks)
    assert len(picks) == 4                       # shadow, not deleted
    assert summary == {"total": 4, "shadow": 2, "money_path": 2,
                       "policy_id": summary["policy_id"],
                       "by_slice": summary["by_slice"]}
    assert summary["by_slice"]["CRYPTO/INTRADAY"]["shadow"] == 1
    assert summary["by_slice"]["ETF/INTRADAY"]["shadow"] == 1


def test_annotate_buckets_covers_the_money_path_lists():
    payload = {"active": [{"asset_class": "CRYPTO", "trade_timeframe": "INTRADAY"}],
               "smart_picks": [{"asset_class": "CRYPTO", "trade_timeframe": "POSITION"}],
               "recent_closed": [{"asset_class": "ETF", "timeframe": "INTRADAY"}]}
    out = annotate_buckets(payload)
    assert out["total"] == 3 and out["shadow"] == 2 and out["money_path"] == 1
    assert payload["active"][0]["shadow"] is True
    assert payload["smart_picks"][0]["money_path"] is True


def test_alpha_effect_reports_the_measured_improvement():
    rows = ([{"class": "CRYPTO", "timeframe": "INTRADAY", "alpha": -0.4}] * 40
            + [{"class": "CRYPTO", "timeframe": "POSITION", "alpha": 2.0}] * 10)
    eff = alpha_effect(rows)
    assert eff["rows_scored"] == 50
    assert eff["shadow"]["n"] == 40 and eff["shadow"]["mean_alpha_pct"] == -0.4
    assert eff["money_path"]["n"] == 10 and eff["money_path"]["mean_alpha_pct"] == 2.0
    # book = (10 x +2.0 + 40 x -0.4) / 50 = +0.08%/pick with the bad slice in;
    # removing it lifts the book to +2.0%/pick, i.e. +1.92%/pick of measured alpha
    assert eff["book_mean_alpha_pct_without_stop"] == 0.08
    assert eff["book_mean_alpha_pct_with_stop"] == 2.0
    assert eff["improvement_pct_per_pick"] == 1.92
    assert eff["per_class"]["CRYPTO"]["shadow"]["n"] == 40


def test_sizing_list_is_partitioned_not_deleted():
    payload = {"smart_picks": [
        {"id": "a", "asset_class": "CRYPTO", "trade_timeframe": "INTRADAY"},
        {"id": "b", "asset_class": "CRYPTO", "trade_timeframe": "POSITION"},
    ]}
    out = annotate_buckets(payload)
    assert [p["id"] for p in payload["smart_picks"]] == ["b"]
    assert [p["id"] for p in payload["shadow_picks"]] == ["a"]
    assert payload["shadow_picks"][0]["shadow_reason"] == "intraday_stop:CRYPTO/INTRADAY"
    assert out["moved_to_shadow_picks"] == 1
    # a second pass must not move the same row twice or lose it
    again = annotate_buckets(payload)
    assert again["moved_to_shadow_picks"] == 0
    assert [p["id"] for p in payload["shadow_picks"]] == ["a"]
