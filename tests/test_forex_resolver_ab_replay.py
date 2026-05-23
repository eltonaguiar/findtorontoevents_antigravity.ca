"""Tests for tools/forex_resolver_ab_replay.py.

Stdlib-only assertions — no pandas, no numpy.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import date
from pathlib import Path

import pytest

# Make tools/ importable.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import forex_resolver_ab_replay as ab  # noqa: E402


# ----------------------------------------------------------------------------
# JPY filter
# ----------------------------------------------------------------------------

class TestJpyFilter:
    def test_yfinance_jpy_pairs_match(self):
        for sym in ("USDJPY=X", "EURJPY=X", "CADJPY=X", "GBPJPY=X", "AUDJPY=X", "JPYUSD=X"):
            assert ab.is_jpy_pair(sym), f"{sym} should be JPY"

    def test_non_jpy_pairs_do_not_match(self):
        for sym in ("EURUSD=X", "GBPUSD=X", "AUDCAD=X", "NZDUSD=X", "EURGBP=X"):
            assert not ab.is_jpy_pair(sym), f"{sym} should NOT be JPY"

    def test_empty_or_none(self):
        assert ab.is_jpy_pair("") is False
        assert ab.is_jpy_pair(None) is False  # type: ignore[arg-type]


# ----------------------------------------------------------------------------
# Stat computation
# ----------------------------------------------------------------------------

class TestComputeStats:
    def test_empty_returns_zeros(self):
        s = ab.compute_stats([])
        assert s["n"] == 0
        assert s["pf"] == 0.0
        assert s["sharpe"] == 0.0
        assert s["wr_pct"] == 0.0

    def test_pf_with_mixed_wins_losses(self):
        # gross_win=3.0, gross_loss=-1.0 → PF=3.0
        s = ab.compute_stats([1.0, 2.0, -1.0])
        assert s["n"] == 3
        assert s["gross_win"] == pytest.approx(3.0)
        assert s["gross_loss"] == pytest.approx(-1.0)
        assert s["pf"] == pytest.approx(3.0)
        assert s["wr_pct"] == pytest.approx(2 / 3 * 100.0)

    def test_pf_no_losses_is_inf(self):
        s = ab.compute_stats([0.5, 1.0, 2.0])
        assert math.isinf(s["pf"])
        assert s["pf"] > 0

    def test_pf_no_wins_is_zero(self):
        s = ab.compute_stats([-0.5, -1.0])
        assert s["pf"] == 0.0
        assert s["wr_pct"] == 0.0

    def test_sharpe_zero_std_returns_zero_not_div_error(self):
        # All identical → std=0 → Sharpe must be 0, not raise.
        s = ab.compute_stats([0.5, 0.5, 0.5, 0.5])
        assert s["std_pnl_pct"] == pytest.approx(0.0)
        assert s["sharpe"] == 0.0

    def test_sharpe_basic(self):
        # mean=0.5, pstdev of [0,1,0,1] = 0.5 → sharpe = 1.0 * sqrt(252)
        s = ab.compute_stats([0.0, 1.0, 0.0, 1.0])
        assert s["sharpe"] == pytest.approx(math.sqrt(ab.TRADING_DAYS), rel=1e-6)


# ----------------------------------------------------------------------------
# Noise filter
# ----------------------------------------------------------------------------

class TestNoiseFilter:
    def test_drops_below_threshold(self):
        picks = [
            {"pnl_pct": 0.001},   # 0.1bp — below 5bp
            {"pnl_pct": 0.05},    # 5bp — keep
            {"pnl_pct": -0.06},   # 6bp — keep
            {"pnl_pct": 0.0},     # noise
            {"pnl_pct": -0.04},   # 4bp — drop
        ]
        kept = ab.apply_noise_filter(picks, ab.PCT_PER_BP * 5)
        assert len(kept) == 2

    def test_zero_threshold_keeps_all(self):
        picks = [{"pnl_pct": 0.001}, {"pnl_pct": 0.0}, {"pnl_pct": -0.5}]
        kept = ab.apply_noise_filter(picks, 0.0)
        assert len(kept) == 3


# ----------------------------------------------------------------------------
# Acceptance criteria
# ----------------------------------------------------------------------------

def _stats_with(n=50, pf=2.0, sharpe=0.5):
    """Stub a stats dict directly — bypass compute_stats."""
    return {
        "n": n,
        "wr_pct": 50.0,
        "sum_pnl_pct": 0.0,
        "mean_pnl_pct": 0.0,
        "std_pnl_pct": 0.0,
        "gross_win": 0.0,
        "gross_loss": 0.0,
        "pf": pf,
        "sharpe": sharpe,
    }


class TestAcceptance:
    def test_jpy_collapse_rejects_overall_even_when_others_pass(self):
        sub_a = {
            "overall": _stats_with(n=100, pf=1.0, sharpe=0.0),
            "non_jpy": _stats_with(n=60, pf=1.0, sharpe=0.0),
            "jpy": _stats_with(n=40, pf=1.0, sharpe=0.0),
        }
        sub_b = {
            "overall": _stats_with(n=80, pf=2.0, sharpe=0.6),
            "non_jpy": _stats_with(n=50, pf=6.0, sharpe=0.7),
            "jpy": _stats_with(n=30, pf=0.5, sharpe=-0.3),  # JPY collapse
        }
        verdict = ab.evaluate_acceptance(sub_a, sub_b)
        # Overall + non_jpy clear thresholds, but JPY < 1.0 → REJECTED.
        assert verdict["per_cohort"]["jpy"]["verdict"] == "REJECTED"
        assert verdict["overall_verdict"] == "REJECTED"
        assert "jpy" in verdict["overall_reason"]

    def test_all_pass(self):
        sub_a = {
            "overall": _stats_with(n=100, pf=0.8, sharpe=0.0),
            "non_jpy": _stats_with(n=60, pf=0.8, sharpe=0.0),
            "jpy": _stats_with(n=40, pf=0.8, sharpe=0.0),
        }
        sub_b = {
            "overall": _stats_with(n=80, pf=2.0, sharpe=0.6),
            "non_jpy": _stats_with(n=50, pf=6.0, sharpe=0.7),
            "jpy": _stats_with(n=30, pf=1.5, sharpe=0.3),
        }
        verdict = ab.evaluate_acceptance(sub_a, sub_b)
        assert verdict["overall_verdict"] == "ACCEPTED"
        assert all(
            verdict["per_cohort"][c]["verdict"] == "ACCEPTED"
            for c in ("overall", "non_jpy", "jpy")
        )

    def test_insufficient_sample(self):
        sub_a = {
            "overall": _stats_with(n=20, pf=1.0, sharpe=0.0),
            "non_jpy": _stats_with(n=15, pf=1.0, sharpe=0.0),
            "jpy": _stats_with(n=5, pf=1.0, sharpe=0.0),
        }
        sub_b = {
            "overall": _stats_with(n=15, pf=10.0, sharpe=2.0),
            "non_jpy": _stats_with(n=10, pf=10.0, sharpe=2.0),
            "jpy": _stats_with(n=5, pf=10.0, sharpe=2.0),  # passes PF but n too small
        }
        verdict = ab.evaluate_acceptance(sub_a, sub_b)
        for c in ("overall", "non_jpy", "jpy"):
            assert verdict["per_cohort"][c]["verdict"] == "INSUFFICIENT_SAMPLE"
        assert verdict["overall_verdict"] == "INSUFFICIENT_SAMPLE"

    def test_sharpe_lift_failure_rejects_overall(self):
        # All sub-books pass PF, but Sharpe lift below +0.5 → REJECTED.
        sub_a = {
            "overall": _stats_with(n=100, pf=1.0, sharpe=0.5),
            "non_jpy": _stats_with(n=60, pf=1.0, sharpe=0.5),
            "jpy": _stats_with(n=40, pf=1.0, sharpe=0.5),
        }
        sub_b = {
            "overall": _stats_with(n=80, pf=2.0, sharpe=0.6),  # lift only +0.1
            "non_jpy": _stats_with(n=50, pf=6.0, sharpe=0.7),
            "jpy": _stats_with(n=30, pf=1.5, sharpe=0.6),
        }
        verdict = ab.evaluate_acceptance(sub_a, sub_b)
        assert verdict["sharpe_pass"] is False
        assert verdict["overall_verdict"] == "REJECTED"
        assert "Sharpe" in verdict["overall_reason"]


# ----------------------------------------------------------------------------
# Date filtering / pick filtering
# ----------------------------------------------------------------------------

class TestFilterPicks:
    def _mk(self, **kw):
        base = {
            "asset_class": "FOREX",
            "symbol": "EURUSD=X",
            "direction": "LONG",
            "pnl_pct": 0.1,
            "closed_at": "2026-04-15T12:00:00+00:00",
        }
        base.update(kw)
        return base

    def test_filters_by_asset_class(self):
        picks = [self._mk(), self._mk(asset_class="EQUITY")]
        out = ab.filter_picks(picks, "FOREX", date(2026, 1, 1), date(2026, 12, 31))
        assert len(out) == 1

    def test_drops_invalid_pnl(self):
        picks = [self._mk(pnl_pct=None), self._mk(pnl_pct="bad"), self._mk()]
        out = ab.filter_picks(picks, "FOREX", date(2026, 1, 1), date(2026, 12, 31))
        assert len(out) == 1

    def test_date_window_inclusive_bounds(self):
        picks = [
            self._mk(closed_at="2026-04-01T00:00:00Z"),
            self._mk(closed_at="2026-04-15T00:00:00Z"),
            self._mk(closed_at="2026-04-30T00:00:00Z"),
            self._mk(closed_at="2026-05-01T00:00:00Z"),  # out
            self._mk(closed_at="2026-03-31T00:00:00Z"),  # out
        ]
        out = ab.filter_picks(picks, "FOREX", date(2026, 4, 1), date(2026, 4, 30))
        assert len(out) == 3

    def test_falls_back_to_timestamp_then_entry_time(self):
        picks = [
            self._mk(closed_at=None, timestamp="2026-04-15T00:00:00Z"),
            self._mk(closed_at=None, timestamp=None, entry_time="2026-04-10"),
        ]
        out = ab.filter_picks(picks, "FOREX", date(2026, 4, 1), date(2026, 4, 30))
        assert len(out) == 2


# ----------------------------------------------------------------------------
# End-to-end: build a fixture, run, check report
# ----------------------------------------------------------------------------

class TestEndToEnd:
    def _build_fixture(self, tmp_path: Path) -> Path:
        # Build a synthetic dashboard_data.json with FOREX picks split JPY / non-JPY.
        non_jpy = []
        for i in range(40):
            # Profitable non-JPY: alternating big wins + small losses
            non_jpy.append({
                "asset_class": "FOREX",
                "symbol": "EURUSD=X",
                "direction": "LONG",
                "pnl_pct": 0.5 if i % 2 == 0 else -0.05,
                "closed_at": f"2026-04-{(i % 28) + 1:02d}T12:00:00Z",
            })
        jpy = []
        for i in range(35):
            # Roughly break-even JPY
            jpy.append({
                "asset_class": "FOREX",
                "symbol": "USDJPY=X",
                "direction": "LONG",
                "pnl_pct": 0.1 if i % 2 == 0 else -0.1,
                "closed_at": f"2026-04-{(i % 28) + 1:02d}T12:00:00Z",
            })
        # Some sub-1bp noise that should be dropped by Sub-B
        noise = [
            {"asset_class": "FOREX", "symbol": "EURUSD=X", "direction": "LONG",
             "pnl_pct": 0.001, "closed_at": "2026-04-10T00:00:00Z"}
            for _ in range(20)
        ]
        # Out-of-window pick
        out_of_window = {
            "asset_class": "FOREX", "symbol": "EURUSD=X", "direction": "LONG",
            "pnl_pct": -10.0, "closed_at": "2025-01-01T00:00:00Z",
        }
        # Non-FOREX pick that should be excluded
        equity = {
            "asset_class": "EQUITY", "symbol": "AAPL", "direction": "LONG",
            "pnl_pct": 1.0, "closed_at": "2026-04-15T00:00:00Z",
        }
        data = {
            "picks": {
                "recent_closed": non_jpy + jpy + noise + [out_of_window, equity],
            }
        }
        path = tmp_path / "dashboard_data.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_run_produces_report_with_expected_sections(self, tmp_path):
        picks_path = self._build_fixture(tmp_path)
        output = tmp_path / "out.md"
        argv = [
            "--picks-source", str(picks_path),
            "--start-date", "2026-04-01",
            "--end-date", "2026-04-30",
            "--noise-bps", "5",
            "--output", str(output),
        ]
        args = ab.parse_args(argv)
        result = ab.run(args)

        assert output.exists()
        text = output.read_text(encoding="utf-8")
        # Required sections
        assert "# FOREX Resolver A/B Replay" in text
        assert "## Verdict" in text
        assert "## Sample" in text
        assert "## Stats per cohort" in text
        assert "## Acceptance criteria check" in text
        assert "## Sample-size shifts" in text
        assert "## Top symbols by drag" in text
        assert "## Recommendation" in text
        # Excluded equity pick must not appear
        assert "AAPL" not in text
        # Out-of-window pick must not appear
        assert "-10.0000" not in text
        # Confirm the noise filter dropped sub-bp picks (Sub-A > Sub-B for overall)
        assert result["sub_a"]["overall"]["n"] > result["sub_b"]["overall"]["n"]

    def test_noise_drops_sub_bp_picks(self, tmp_path):
        picks_path = self._build_fixture(tmp_path)
        argv = [
            "--picks-source", str(picks_path),
            "--start-date", "2026-04-01",
            "--end-date", "2026-04-30",
            "--noise-bps", "5",
            "--output", str(tmp_path / "out.md"),
        ]
        result = ab.run(ab.parse_args(argv))
        # 20 noise picks (0.001 = 0.1bp) all in non_jpy bucket
        sub_a_overall = result["sub_a"]["overall"]["n"]
        sub_b_overall = result["sub_b"]["overall"]["n"]
        assert sub_a_overall - sub_b_overall == 20
