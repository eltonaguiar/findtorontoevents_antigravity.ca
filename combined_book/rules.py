"""Frozen rules for the standalone combined-book pilot.

Any change to RULES_MARKDOWN changes RULES_HASH and starts a new pilot.
"""
from pathlib import Path
import hashlib

# --- Frozen constants (recorded in RULES.md) ---
STARTING_CAPITAL = 100_000.0
REBALANCE_CADENCE = "monthly"
PER_SLEEVE_CAP = 0.40
TRADE_COST_BPS = 10.0

# Go-live gate thresholds
GO_LIVE_N_MONTHS = 100
GO_LIVE_PF = 1.5
GO_LIVE_WR = 0.50
GO_LIVE_MAX_DD = -0.20

# Kill thresholds
KILL_DRAWDOWN = -0.15
KILL_AFTER_MONTHS = 24
KILL_PF = 1.0
KILL_WR = 0.50
KILL_SHARPE = 0.0
KILL_BOOTSTRAP_P = 0.5

# Pre-registered volatility-cap selection rule range
VOL_TARGET_MIN = 0.05
VOL_TARGET_MAX = 0.10

# External pilot's reference rules hash (informational; ours differs)
RULES_REFERENCE_HASH = "d5bed907932009a96d45521c15102cba2092ec9307dfd8367aedf3f21c9fcfd5"

RULES_MARKDOWN = """\
# Combined-Book Paper-Trade Rules (frozen)

- Starting capital: $100,000 (fixed).
- Rebalance cadence: monthly.
- Per-sleeve weight cap: 40%.
- Sleeve combination: inverse-volatility weights.
- Trade cost: 10 bps per trade (trend sleeve).
- Target book volatility cap: 5% annualized, selected by the pre-registered rule:
  pick the highest target in 5%-10% whose pre-2016 backtest max drawdown stays within
  the -15% kill limit. 6% hit -16.5%, so 5% wins. Run on pre-2016 data only.
- Put-write sleeve: tradeable proxy XYLD; backtest series CBOE PUT index.
- Trend sleeve may hold net-short bond stance; borrow cost modeled or flagged unmodeled.
- Uninvested cash earns 0%.
- Go-live gate (all must pass): >=100 months; PF >= 1.5; win rate >= 50%; worst DD
  no deeper than -20%. Reported alongside: Wilson 95% CI, binomial p-value,
  bootstrapped PF (seeded), Sharpe vs SPY, random-entry percentile, Deflated Sharpe.
- Kill criteria (either kills): live paper DD worse than -15%; OR at >=24 months any of
  PF < 1.0, win rate < 50%, Sharpe <= 0, bootstrap P(PF <= 1) > 0.5.
"""


def compute_rules_hash(rules_text: str) -> str:
    return hashlib.sha256(rules_text.encode("utf-8")).hexdigest()


RULES_HASH = compute_rules_hash(RULES_MARKDOWN)


def verify_rules_hash(expected: str | None = None) -> bool:
    target = expected if expected is not None else RULES_HASH
    return compute_rules_hash(RULES_MARKDOWN) == target
