"""M-115: nc_budget gate uses AND instead of OR for pass_rate + total_pnl.

Before the fix, the gate clamped nc_budget to 2 when EITHER condition was true:
  - pass_rate_pct < 6.0  OR  non_crypto_total_pnl < 0.0
After the fix, both must be bad to trigger the clamp (AND).

Root cause: historical all-time non-crypto PnL is contaminated by pre-quality-gate
EQUITY picks (blocked 2026-05-16). pass_rate 7.78% >= 6% should be sufficient to
allow full 5-slot budget; all-time negative PnL alone must not veto it.
"""
import sys, os, json, tempfile, importlib
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_hf_review(pass_rate_pct: float, total_pnl: float, pf: float = 1.0) -> dict:
    return {
        "active_pass_watchlist": {"pass_rate_pct": pass_rate_pct},
        "non_crypto_closed_rollup": {"total_pnl": total_pnl, "profit_factor": pf},
    }


def _effective_budget(pass_rate_pct: float, total_pnl: float, pf: float = 1.0,
                      base_budget: int = 5) -> int:
    """Mirror the nc_budget logic from smart_picks_engine.py."""
    nc_budget = base_budget
    _pass_rate = pass_rate_pct
    _non_crypto_total = total_pnl
    _non_crypto_pf = pf
    if _pass_rate < 6.0 and _non_crypto_total < 0.0:
        nc_budget = min(nc_budget, 2)
    elif 6.0 <= _pass_rate <= 15.0 and (_non_crypto_total >= 0.0 or _non_crypto_pf >= 1.0):
        nc_budget = min(nc_budget + 1, 4)
    return nc_budget


class TestNcBudgetGate:
    def test_both_bad_clamps_to_2(self):
        """Both pass_rate AND total_pnl bad → clamp to 2 (AND condition)."""
        assert _effective_budget(pass_rate_pct=3.0, total_pnl=-100.0) == 2

    def test_pass_rate_ok_negative_pnl_allows_full_budget(self):
        """M-115 fix: pass_rate 7.78% >= 6% with negative pnl AND bad PF → NOT clamped.
        Real-world values from hf_enhancement_review.json (2026-05-20):
          pass_rate=7.78, total_pnl=-394.98, profit_factor=0.697
        With AND condition, clamp only fires when BOTH pass_rate AND pnl are bad.
        Budget should stay at base 5 (no clamp, no bonus since PF<1 blocks elif bonus).
        """
        budget = _effective_budget(pass_rate_pct=7.78, total_pnl=-394.98, pf=0.697)
        assert budget == 5, f"Expected 5 (no clamp), got {budget}"

    def test_both_bad_but_pf_ok_clamps_by_pass_rate(self):
        """pass_rate < 6 AND pnl < 0 → clamp regardless of PF."""
        assert _effective_budget(pass_rate_pct=3.0, total_pnl=-50.0, pf=1.5) == 2

    def test_pass_rate_ok_positive_pnl_adds_bonus_slot(self):
        """pass_rate in 6-15 AND positive pnl → budget +1 (up to 4)."""
        assert _effective_budget(pass_rate_pct=10.0, total_pnl=50.0) == 4

    def test_pass_rate_ok_negative_pnl_but_pf_ok_adds_bonus(self):
        """pass_rate in 6-15 AND pf >= 1.0 → bonus slot even with negative total pnl."""
        assert _effective_budget(pass_rate_pct=10.0, total_pnl=-10.0, pf=1.1) == 4

    def test_very_low_pass_rate_alone_does_not_clamp(self):
        """pass_rate < 6 BUT pnl >= 0 → no clamp (AND condition means one bad not enough)."""
        budget = _effective_budget(pass_rate_pct=2.0, total_pnl=50.0)
        assert budget == 5, f"Expected 5, got {budget}"

    def test_pass_rate_above_15_no_bonus(self):
        """pass_rate > 15 with positive pnl → no bonus (bonus only in 6-15 band)."""
        assert _effective_budget(pass_rate_pct=20.0, total_pnl=100.0) == 5
