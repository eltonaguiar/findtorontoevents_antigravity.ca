"""Loader + validator for config/portfolio_risk_profiles.json (pure stdlib).

Phase 1 contract: the rest of the AI-model-portfolios subsystem codes against
these helpers. See docs/DESIGN_AI_MODEL_HEDGE_FUND_PORTFOLIOS_2026-05-29.md §4.

    from tools.portfolios.profiles import load_profiles, get_profile
    profiles = load_profiles()          # {'conservative': {...}, 'balanced': {...}, 'aggressive': {...}}
    cons = get_profile('conservative')  # raises ValueError on unknown appetite
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROFILES_PATH = REPO_ROOT / "config" / "portfolio_risk_profiles.json"

REQUIRED_APPETITES = ("conservative", "balanced", "aggressive")

# Keys every appetite block must define (per §4).
REQUIRED_KEYS = (
    "vol_target_annual",
    "kelly_fraction",
    "max_single_position_pct",
    "max_class_exposure_pct",
    "gross_exposure_cap_pct",
    "cash_floor_pct",
    "stop_loss",
    "take_profit",
    "trend_filter_ma_days",
    "max_open_positions",
    "drawdown_breaker_pct",
    "asset_class_allowlist",
)


def load_profiles(path: Path | str | None = None) -> dict:
    """Read and validate the risk-profiles JSON.

    Returns a dict keyed by appetite name (the top-level ``_meta`` block is
    excluded from the returned mapping). Raises ValueError if any required
    appetite or key is missing.
    """
    p = Path(path) if path is not None else PROFILES_PATH
    if not p.exists():
        raise FileNotFoundError(f"risk profiles not found: {p}")

    raw = json.loads(p.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"expected a JSON object at top level of {p}")

    profiles = {k: v for k, v in raw.items() if k != "_meta"}

    missing_appetites = [a for a in REQUIRED_APPETITES if a not in profiles]
    if missing_appetites:
        raise ValueError(
            f"risk profiles missing appetite(s): {missing_appetites} (have {sorted(profiles)})"
        )

    for appetite in REQUIRED_APPETITES:
        block = profiles[appetite]
        if not isinstance(block, dict):
            raise ValueError(f"appetite '{appetite}' must be an object, got {type(block).__name__}")
        missing_keys = [k for k in REQUIRED_KEYS if k not in block]
        if missing_keys:
            raise ValueError(f"appetite '{appetite}' missing key(s): {missing_keys}")
        for nested in ("stop_loss", "take_profit"):
            if not isinstance(block[nested], dict):
                raise ValueError(f"appetite '{appetite}.{nested}' must be an object")
        if not isinstance(block["asset_class_allowlist"], list):
            raise ValueError(f"appetite '{appetite}.asset_class_allowlist' must be an array")

    return profiles


def get_profile(name: str, path: Path | str | None = None) -> dict:
    """Return a single appetite profile, raising a clear error on unknown name."""
    profiles = load_profiles(path)
    key = (name or "").strip().lower()
    if key not in profiles:
        raise ValueError(
            f"unknown risk appetite {name!r}; valid options: {sorted(profiles)}"
        )
    return profiles[key]


if __name__ == "__main__":
    loaded = load_profiles()
    print("profiles OK:", list(loaded))
