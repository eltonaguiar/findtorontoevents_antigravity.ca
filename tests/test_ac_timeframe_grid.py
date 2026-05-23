"""Tests for B2: _build_ac_timeframe_grid in audit_trail/dashboard_generator.py."""
import pytest
from audit_trail.dashboard_generator import _build_ac_timeframe_grid, _AC_TF_GRID_ASSET_CLASSES, _AC_TF_GRID_TIMEFRAMES


def _pick(asset_class="CRYPTO", trade_timeframe="SWING", pick_id="p1"):
    return {"asset_class": asset_class, "trade_timeframe": trade_timeframe, "id": pick_id}


class TestBuildAcTimeframeGridStructure:
    def test_empty_picks_returns_all_base_classes(self):
        result = _build_ac_timeframe_grid([])
        assert result["classes"] == _AC_TF_GRID_ASSET_CLASSES
        assert result["timeframes"] == _AC_TF_GRID_TIMEFRAMES

    def test_empty_picks_all_cells_zero(self):
        result = _build_ac_timeframe_grid([])
        for ac in result["classes"]:
            for tf in result["timeframes"]:
                assert result["cells"][f"{ac}|{tf}"]["count"] == 0

    def test_empty_picks_all_empty_lanes(self):
        result = _build_ac_timeframe_grid([])
        expected = len(_AC_TF_GRID_ASSET_CLASSES) * len(_AC_TF_GRID_TIMEFRAMES)
        assert len(result["empty_lanes"]) == expected

    def test_single_pick_increments_cell(self):
        result = _build_ac_timeframe_grid([_pick("CRYPTO", "SWING", "abc")])
        assert result["cells"]["CRYPTO|SWING"]["count"] == 1
        assert "abc" in result["cells"]["CRYPTO|SWING"]["pick_ids"]

    def test_total_by_class_correct(self):
        picks = [_pick("EQUITY", "INTRADAY", f"e{i}") for i in range(3)]
        picks += [_pick("CRYPTO", "SCALP", f"c{i}") for i in range(2)]
        result = _build_ac_timeframe_grid(picks)
        assert result["totals_by_class"]["EQUITY"] == 3
        assert result["totals_by_class"]["CRYPTO"] == 2
        assert result["totals_by_class"]["FOREX"] == 0


class TestBuildAcTimeframeGridEdgeCases:
    def test_null_timeframe_goes_to_unknown_bucket(self):
        result = _build_ac_timeframe_grid([{"asset_class": "CRYPTO", "trade_timeframe": None, "id": "x"}])
        assert "UNKNOWN" in result["timeframes"]
        assert result["cells"]["CRYPTO|UNKNOWN"]["count"] == 1

    def test_missing_timeframe_key_goes_to_unknown(self):
        result = _build_ac_timeframe_grid([{"asset_class": "EQUITY", "id": "y"}])
        assert "UNKNOWN" in result["timeframes"]
        assert result["cells"]["EQUITY|UNKNOWN"]["count"] == 1

    def test_unknown_tf_not_added_when_all_timeframes_known(self):
        picks = [_pick("CRYPTO", "SCALP"), _pick("EQUITY", "POSITION")]
        result = _build_ac_timeframe_grid(picks)
        assert "UNKNOWN" not in result["timeframes"]

    def test_extra_observed_asset_class_appended(self):
        result = _build_ac_timeframe_grid([_pick("SPORTS", "INTRADAY", "s1")])
        assert "SPORTS" in result["classes"]
        # Extra classes come after base classes
        idx_sports = result["classes"].index("SPORTS")
        idx_last_base = result["classes"].index(_AC_TF_GRID_ASSET_CLASSES[-1])
        assert idx_sports > idx_last_base

    def test_empty_lanes_excludes_nonzero_cells(self):
        picks = [_pick("CRYPTO", "SWING")]
        result = _build_ac_timeframe_grid(picks)
        empty_keys = {(e["asset_class"], e["timeframe"]) for e in result["empty_lanes"]}
        # CRYPTO|SWING should NOT be in empty_lanes
        assert ("CRYPTO", "SWING") not in empty_keys
        # CRYPTO|SCALP should be in empty_lanes
        assert ("CRYPTO", "SCALP") in empty_keys

    def test_pick_without_id_still_counted(self):
        result = _build_ac_timeframe_grid([{"asset_class": "BOND", "trade_timeframe": "POSITION"}])
        assert result["cells"]["BOND|POSITION"]["count"] == 1
        assert result["cells"]["BOND|POSITION"]["pick_ids"] == []

    def test_multiple_picks_same_cell_accumulate(self):
        picks = [_pick("FOREX", "INTRADAY", f"f{i}") for i in range(5)]
        result = _build_ac_timeframe_grid(picks)
        assert result["cells"]["FOREX|INTRADAY"]["count"] == 5
        assert len(result["cells"]["FOREX|INTRADAY"]["pick_ids"]) == 5
