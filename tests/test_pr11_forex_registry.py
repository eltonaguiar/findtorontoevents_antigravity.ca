"""PR #11: forex_carry_ppp must be registered in the scanner's FOREX_STRATEGIES.

It is intentionally kept OUT of NON_CRYPTO_STRATEGY_POLICY so the policy
fail-closes it as `strategy_on_probation` — it generates forward-record signals
but cannot emit live picks (correct for FOREX, a failing class).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# forex_strategies.py uses bare sibling imports (from config import ..., from
# forex_carry_ppp import ...), so the alpha_engine dir must be on sys.path.
sys.path.insert(0, str(ROOT / "alpha_engine"))

from alpha_engine.forex_strategies import FOREX_STRATEGIES


def test_forex_carry_ppp_registered():
    assert "forex_carry_ppp" in FOREX_STRATEGIES
    assert callable(FOREX_STRATEGIES["forex_carry_ppp"])
