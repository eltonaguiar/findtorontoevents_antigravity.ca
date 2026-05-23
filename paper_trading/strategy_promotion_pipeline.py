"""CI-Based Strategy Promotion Pipeline — CODERED Fix 5.

Three-tier system with statistical confidence intervals:
  - Incubator: n=0–9 picks, micro-capital (0.25x risk)
  - Probation:  n≥10 picks, CI must include >50% WR (0.5x risk)
  - Standard:   n≥30 picks, lower-bound 95% CI >50% WR (1.0x risk)
  - Killed:     on PERMANENTLY_KILLED list (0x risk — no new positions)

Promotion/demotion is evaluated every scanner run based on rolling forward
performance from paper_trading/data/closed_picks.json.
"""
import json
import logging
import math
import pathlib
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Tuple

logger = logging.getLogger("paper_trading")

DATA_DIR = pathlib.Path(__file__).parent / "data"

# ── Tier definitions ──
TIER_INCUBATOR = "incubator"
TIER_PROBATION = "probation"
TIER_STANDARD = "standard"
TIER_KILLED = "killed"

TIER_MULTIPLIERS: Dict[str, float] = {
    TIER_INCUBATOR: 0.25,
    TIER_PROBATION: 0.50,
    TIER_STANDARD: 1.00,
    TIER_KILLED: 0.00,
}

# ── Promotion thresholds ──
Z_SCORE = 1.96  # 95% confidence

# Standard: need n≥30 AND Wilson lower-bound >50%
STANDARD_MIN_TRADES = 30
STANDARD_MIN_WR_LOWER_BOUND = 0.50

# Probation: need n≥10 AND Wilson CI must overlap >50% (upper-bound >50%)
PROBATION_MIN_TRADES = 10
PROBATION_MIN_WR_UPPER_BOUND = 0.50

# Demotion: probation WR <40% → drop to incubator
PROBATION_DEMOTION_WR = 0.40

# ── Quality gate: killed strategies ──
try:
    from audit_trail.quality_gates import PERMANENTLY_KILLED_STRATEGIES as _KILLED
    _KILLED_LOWER = {s.lower() for s in _KILLED}
except ImportError:
    _KILLED_LOWER = set()

# ── Cache for tier map (invalidated on closed_picks.json change) ──
_tier_cache: Dict[str, str] = {}
_tier_cache_mtime: float = 0.0


def wilson_score_interval(wins: int, n: int, z: float = Z_SCORE) -> Tuple[float, float]:
    """Wilson score interval for binomial proportion (95% CI).

    More accurate than normal approximation for small n.
    Returns (lower_bound, upper_bound) in [0, 1].
    """
    if n == 0:
        return 0.0, 0.0
    p_hat = wins / n
    z2 = z * z
    denominator = 1 + z2 / n
    center = p_hat + z2 / (2 * n)
    spread = z * math.sqrt((p_hat * (1 - p_hat)) / n + z2 / (4 * n * n))
    lower = max(0.0, (center - spread) / denominator)
    upper = min(1.0, (center + spread) / denominator)
    return lower, upper


def _load_and_group_picks() -> Dict[str, List[dict]]:
    """Load closed_picks.json and group by strategy name."""
    path = DATA_DIR / "closed_picks.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            picks = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

    groups: Dict[str, List[dict]] = defaultdict(list)
    for p in picks:
        if not isinstance(p, dict):
            continue
        strat = p.get("strategy", p.get("algorithm", ""))
        if strat:
            groups[strat].append(p)
    return dict(groups)


def evaluate_strategy(strategy_name: str, trades: List[dict]) -> str:
    """Evaluate a single strategy and return its tier.

    Evaluation priority (highest first):
      1. Killed  — on PERMANENTLY_KILLED list
      2. Standard  — n≥30 AND Wilson lower-bound >50%
      3. Probation — n≥10 AND Wilson upper-bound >50% (CI overlaps 50%)
      4. Incubator — default (not enough data or fails probation)
    """
    # 1. Quality gate: killed strategies
    if strategy_name.lower() in _KILLED_LOWER:
        return TIER_KILLED

    n = len(trades)
    wins = sum(1 for t in trades if float(t.get("pnl_pct", 0) or 0) > 0)
    wr = wins / n if n > 0 else 0.0
    lower, upper = wilson_score_interval(wins, n)

    # 2. Standard tier
    if n >= STANDARD_MIN_TRADES and lower > STANDARD_MIN_WR_LOWER_BOUND:
        return TIER_STANDARD

    # 3. Probation tier (CI overlaps 50%)
    if n >= PROBATION_MIN_TRADES and upper > PROBATION_MIN_WR_UPPER_BOUND:
        # Demotion check: if WR < 40%, drop to incubator despite n≥10
        if wr < PROBATION_DEMOTION_WR:
            return TIER_INCUBATOR
        return TIER_PROBATION

    # 4. Incubator (default)
    return TIER_INCUBATOR


def generate_tier_map() -> Dict[str, str]:
    """Generate {strategy_name: tier} for all strategies with closed picks.

    Cached with file mtime invalidation so it's cheap to call every scan.
    """
    global _tier_cache, _tier_cache_mtime

    # Invalidate cache if closed_picks.json changed
    path = DATA_DIR / "closed_picks.json"
    try:
        mtime = path.stat().st_mtime if path.exists() else 0.0
    except OSError:
        mtime = 0.0

    if _tier_cache and _tier_cache_mtime == mtime:
        return _tier_cache

    groups = _load_and_group_picks()
    tier_map: Dict[str, str] = {}

    for strat, trades in groups.items():
        tier = evaluate_strategy(strat, trades)
        tier_map[strat] = tier

        n = len(trades)
        wins = sum(1 for t in trades if float(t.get("pnl_pct", 0) or 0) > 0)
        wr = wins / n * 100 if n > 0 else 0
        lower, upper = wilson_score_interval(wins, n)

        if tier != TIER_INCUBATOR:
            logger.info(
                "CODERED Fix 5: %s → %s tier (n=%d, WR=%.1f%%, CI=[%.1f%%, %.1f%%])",
                strat, tier, n, wr, lower * 100, upper * 100,
            )

    # Always log summary
    summary = defaultdict(int)
    for t in tier_map.values():
        summary[t] += 1
    logger.info(
        "CODERED Fix 5: Tier map — standard=%d, probation=%d, incubator=%d, killed=%d",
        summary.get(TIER_STANDARD, 0), summary.get(TIER_PROBATION, 0),
        summary.get(TIER_INCUBATOR, 0), summary.get(TIER_KILLED, 0),
    )

    _tier_cache = tier_map
    _tier_cache_mtime = mtime
    return tier_map


def get_tier_multiplier(strategy_name: str, tier_map: Dict[str, str] = None) -> float:
    """Get position sizing multiplier for a strategy based on its tier.

    Returns multiplier (0.0–1.0). Unknown strategies default to incubator (0.25x).
    """
    if tier_map is None:
        tier_map = generate_tier_map()
    tier = tier_map.get(strategy_name, TIER_INCUBATOR)
    return TIER_MULTIPLIERS.get(tier, 0.0)


def get_promotion_report() -> dict:
    """Return a summary dict suitable for Discord reporting.

    Structure:
        {
            "title": "Strategy Promotion Pipeline",
            "standard": [{name, n, wr, ci_lower, ci_upper}, ...],
            "probation": [{name, n, wr, ci_lower, ci_upper}, ...],
            "incubator": [{name, n, wr, ci_lower, ci_upper}, ...],
            "killed": [{name, n, wr, ci_lower, ci_upper}, ...],
            "summary": str,
            "evaluated_at": ISO timestamp,
        }
    """
    tier_map = generate_tier_map()
    groups = _load_and_group_picks()

    report = {
        "title": "Strategy Promotion Pipeline",
        "standard": [],
        "probation": [],
        "incubator": [],
        "killed": [],
        "summary": "",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

    for strat, tier in sorted(tier_map.items()):
        trades = groups.get(strat, [])
        n = len(trades)
        wins = sum(1 for t in trades if float(t.get("pnl_pct", 0) or 0) > 0)
        wr = wins / n * 100 if n > 0 else 0
        lower, upper = wilson_score_interval(wins, n)
        entry = {
            "name": strat,
            "trades": n,
            "win_rate": f"{wr:.1f}%",
            "ci_lower": f"{lower * 100:.1f}%",
            "ci_upper": f"{upper * 100:.1f}%",
        }
        if tier in report:
            report[tier].append(entry)

    counts = {t: len(report[t]) for t in [TIER_STANDARD, TIER_PROBATION, TIER_INCUBATOR, TIER_KILLED]}
    report["summary"] = (
        f"Standard: **{counts[TIER_STANDARD]}** | "
        f"Probation: **{counts[TIER_PROBATION]}** | "
        f"Incubator: **{counts[TIER_INCUBATOR]}** | "
        f"Killed: **{counts[TIER_KILLED]}**"
    )
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    report = get_promotion_report()
    print(json.dumps(report, indent=2))
