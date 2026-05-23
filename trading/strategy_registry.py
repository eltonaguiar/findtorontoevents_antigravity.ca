#!/usr/bin/env python3
"""
Strategy Registry — Institutional Governance Layer
===================================================

Maintains versioned, auditable records of every strategy in the system.
Supports tier lifecycle management (INCUBATOR → CORE → KILL_LIST) with
mandatory sign-off, changelog tracking, and walk-forward / stress-test
result storage.

Registry persisted as JSON at trading/data/strategy_registry.json.

Usage:
    from trading.strategy_registry import StrategyRegistry

    reg = StrategyRegistry()
    reg.register("my_strategy", "My Strategy", "momentum", {"rsi_period": 14})
    reg.update_backtest("my_strategy", {"win_rate": 0.62, "sharpe": 1.8, ...})
    reg.promote("my_strategy", "CORE", approved_by="pm@fund.com", notes="Passed WFV")
    print(reg.export_report())
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Constants ────────────────────────────────────────────────────────

REGISTRY_PATH = Path(__file__).parent / "data" / "strategy_registry.json"

VALID_TIERS = {"CORE", "INCUBATOR", "KILL_LIST"}
VALID_STATUSES = {"active", "paused", "eliminated", "pending_review"}
VALID_FAMILIES = {"funding_carry", "momentum", "mean_reversion", "regime_adaptive", "unknown"}

# Canonical family mapping for known strategies
_FAMILY_MAP: Dict[str, str] = {
    "funding_carry":               "funding_carry",
    "funding_rate_carry":          "funding_carry",
    "funding_rate_arbitrage":      "funding_carry",
    "oi_funding_squeeze":          "funding_carry",
    "autocorrelation_exploiter":   "momentum",
    "ema_crossover":               "momentum",
    "spike_macd_divergence":       "momentum",
    "cross_sectional_momentum":    "momentum",
    "atr_volatility_breakout":     "momentum",
    "multi_timeframe_ema_stack":   "momentum",
    "connors_rsi2":                "mean_reversion",
    "bollinger_squeeze":           "mean_reversion",
    "multi_sigma_reversal":        "mean_reversion",
    "fear_greed_extreme_dca":      "mean_reversion",
    "volume_profile_value_area":   "mean_reversion",
    "adaptive_vr_confluence":      "mean_reversion",
    "rsi_macd_confluence":         "mean_reversion",
    "atr_regime_rsi":              "regime_adaptive",
    "hurst_regime_adaptive":       "regime_adaptive",
    "contrarian_predictions":      "regime_adaptive",
    "smart_money_fvg":             "regime_adaptive",
    "community_ict_fvg_selective": "regime_adaptive",
    "m2_liquidity_lag":            "regime_adaptive",
    "monthly_seasonality":         "momentum",
    "fourier_cycle_detector":      "regime_adaptive",
    "exchange_netflow_reversal":   "momentum",
    "price_touch_recurrence":      "mean_reversion",
    "halloween_effect":            "momentum",
    "altcoin_season_rotation":     "momentum",
    "momentum_mean_rev_blend":     "regime_adaptive",
}

# Default backtest scaffolding for bootstrapped strategies (no data yet)
_EMPTY_BACKTEST: Dict[str, Any] = {
    "win_rate": None,
    "expectancy": None,
    "sharpe": None,
    "max_dd": None,
    "total_trades": None,
    "period": None,
}


# ── Helpers ──────────────────────────────────────────────────────────

def _utcnow() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    """Return today's date as YYYY-MM-DD."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _infer_family(strategy_id: str) -> str:
    """Infer strategy family from known ID mapping, fallback to 'unknown'."""
    return _FAMILY_MAP.get(strategy_id, "unknown")


def _make_record(
    strategy_id: str,
    name: str,
    family: str,
    tier: str,
    status: str,
    params: Dict[str, Any],
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a fresh strategy record with all required fields."""
    now = created_at or _utcnow()
    return {
        "strategy_id": strategy_id,
        "name": name,
        "version": "1.0.0",
        "family": family,
        "tier": tier,
        "status": status,
        "created_at": now,
        "promoted_at": now,  # bootstrapped strategies are already in their tier
        "backtest_results": dict(_EMPTY_BACKTEST),
        "walk_forward_results": None,
        "stress_test_results": None,
        "promotion_sign_off": None,
        "parameters": params,
        "changelog": [
            {
                "date": _today(),
                "action": "registered",
                "details": f"Bootstrapped from core_whitelist.json into tier={tier}",
            }
        ],
    }


# ── Registry ─────────────────────────────────────────────────────────

class StrategyRegistry:
    """
    Institutional strategy registry with full lifecycle governance.

    Maintains versioned records for every strategy, enforces tier
    sign-off, and logs every mutation to an append-only changelog.

    All mutations auto-save to trading/data/strategy_registry.json.
    """

    def __init__(self, registry_path: Optional[str] = None):
        self._path = Path(registry_path) if registry_path else REGISTRY_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = self._load()

    # ── Persistence ──────────────────────────────────────────────────

    def _load(self) -> Dict[str, Any]:
        """Load registry from disk, return empty structure if not found."""
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        return {
            "schema_version": "1.0",
            "created_at": _utcnow(),
            "strategies": {},
        }

    def _save(self) -> None:
        """Persist registry to disk (atomic via temp file)."""
        self._data["last_updated"] = _utcnow()
        tmp = self._path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, self._path)

    # ── Core CRUD ────────────────────────────────────────────────────

    def register(
        self,
        strategy_id: str,
        name: str,
        family: str,
        params: Optional[Dict[str, Any]] = None,
        tier: str = "INCUBATOR",
        status: str = "active",
    ) -> Dict[str, Any]:
        """
        Add a new strategy to the registry.

        If strategy_id already exists the call is a no-op (returns existing
        record). To update fields use the dedicated update_* / promote /
        demote methods.

        Args:
            strategy_id: Unique snake_case identifier.
            name:        Human-readable display name.
            family:      One of funding_carry | momentum | mean_reversion |
                         regime_adaptive.
            params:      Dict of strategy parameters / genes.
            tier:        Initial tier (default INCUBATOR).
            status:      Initial status (default active).

        Returns:
            The strategy record dict.
        """
        if strategy_id in self._data["strategies"]:
            return self._data["strategies"][strategy_id]

        if tier not in VALID_TIERS:
            raise ValueError(f"Invalid tier '{tier}'. Must be one of {VALID_TIERS}")
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {VALID_STATUSES}")
        if family not in VALID_FAMILIES:
            family = "unknown"

        record = _make_record(
            strategy_id=strategy_id,
            name=name,
            family=family,
            tier=tier,
            status=status,
            params=params or {},
        )
        # New registrations get null promoted_at unless bootstrapped
        record["promoted_at"] = None
        record["changelog"] = [
            {
                "date": _today(),
                "action": "registered",
                "details": f"Strategy registered in tier={tier}, status={status}",
            }
        ]

        self._data["strategies"][strategy_id] = record
        self._save()
        return record

    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the full record for a strategy.

        Returns None if strategy_id is not registered.
        """
        return self._data["strategies"].get(strategy_id)

    # ── Result Updates ───────────────────────────────────────────────

    def update_backtest(
        self,
        strategy_id: str,
        results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Store or replace backtest results for a strategy.

        Expected keys in results:
            win_rate (float), expectancy (float), sharpe (float),
            max_dd (float), total_trades (int), period (str).

        Extra keys are accepted and stored as-is.

        Returns:
            Updated strategy record.
        """
        record = self._require(strategy_id)
        old_version = record["version"]
        record["backtest_results"] = dict(results)
        record["version"] = self._bump_patch(old_version)
        record["changelog"].append(
            {
                "date": _today(),
                "action": "backtest_updated",
                "details": (
                    f"win_rate={results.get('win_rate')}, "
                    f"sharpe={results.get('sharpe')}, "
                    f"total_trades={results.get('total_trades')}"
                ),
            }
        )
        self._save()
        return record

    def update_walk_forward(
        self,
        strategy_id: str,
        results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Store walk-forward validation (WFV) results.

        Expected keys in results:
            oos_sharpe (float), pct_positive_folds (float),
            degradation_score (float).

        degradation_score = (IS_sharpe - OOS_sharpe) / IS_sharpe.
        Values > 0.4 indicate overfitting.

        Returns:
            Updated strategy record.
        """
        record = self._require(strategy_id)
        old_version = record["version"]
        record["walk_forward_results"] = dict(results)
        record["version"] = self._bump_patch(old_version)
        record["changelog"].append(
            {
                "date": _today(),
                "action": "walk_forward_updated",
                "details": (
                    f"oos_sharpe={results.get('oos_sharpe')}, "
                    f"pct_positive_folds={results.get('pct_positive_folds')}, "
                    f"degradation={results.get('degradation_score')}"
                ),
            }
        )
        self._save()
        return record

    def update_stress_test(
        self,
        strategy_id: str,
        results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Store stress-test results.

        Expected keys in results:
            worst_case_dd (float), tail_risk_pct (float).

        Returns:
            Updated strategy record.
        """
        record = self._require(strategy_id)
        old_version = record["version"]
        record["stress_test_results"] = dict(results)
        record["version"] = self._bump_patch(old_version)
        record["changelog"].append(
            {
                "date": _today(),
                "action": "stress_test_updated",
                "details": (
                    f"worst_case_dd={results.get('worst_case_dd')}, "
                    f"tail_risk_pct={results.get('tail_risk_pct')}"
                ),
            }
        )
        self._save()
        return record

    # ── Tier Lifecycle ───────────────────────────────────────────────

    def promote(
        self,
        strategy_id: str,
        new_tier: str,
        approved_by: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Promote a strategy to a higher tier with mandatory sign-off.

        Tier progression: INCUBATOR → CORE.
        Moving to KILL_LIST from any tier is a demotion — use demote().

        Promotion automatically:
        - Updates tier and promoted_at timestamp.
        - Records promotion_sign_off (approved_by, date, notes).
        - Bumps the minor version.
        - Appends a changelog entry.
        - Sets status to 'active'.

        Args:
            strategy_id: Strategy to promote.
            new_tier:    Target tier (must be CORE or INCUBATOR).
            approved_by: Identifier of the approver (email, username, etc.).
            notes:       Rationale / supporting evidence.

        Returns:
            Updated strategy record.

        Raises:
            ValueError if new_tier is KILL_LIST (use demote instead).
        """
        if new_tier == "KILL_LIST":
            raise ValueError(
                "Cannot promote to KILL_LIST. Use demote() to move a strategy to KILL_LIST."
            )
        if new_tier not in VALID_TIERS:
            raise ValueError(f"Invalid tier '{new_tier}'. Must be one of {VALID_TIERS}")

        record = self._require(strategy_id)
        old_tier = record["tier"]
        old_version = record["version"]

        record["tier"] = new_tier
        record["status"] = "active"
        record["promoted_at"] = _utcnow()
        record["version"] = self._bump_minor(old_version)
        record["promotion_sign_off"] = {
            "approved_by": approved_by,
            "date": _today(),
            "notes": notes,
        }
        record["changelog"].append(
            {
                "date": _today(),
                "action": "promoted",
                "details": f"{old_tier} → {new_tier} | approved_by={approved_by} | {notes}",
            }
        )
        self._save()
        return record

    def demote(
        self,
        strategy_id: str,
        new_tier: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Demote a strategy to a lower tier or KILL_LIST.

        Demotion:
        - Updates tier.
        - Sets status to 'paused' (INCUBATOR) or 'eliminated' (KILL_LIST).
        - Clears promotion_sign_off (requires fresh approval to re-promote).
        - Bumps minor version.
        - Appends a changelog entry.

        Args:
            strategy_id: Strategy to demote.
            new_tier:    Target tier (INCUBATOR or KILL_LIST).
            reason:      Explanation for demotion.

        Returns:
            Updated strategy record.
        """
        if new_tier not in VALID_TIERS:
            raise ValueError(f"Invalid tier '{new_tier}'. Must be one of {VALID_TIERS}")

        record = self._require(strategy_id)
        old_tier = record["tier"]
        old_version = record["version"]

        record["tier"] = new_tier
        record["status"] = "eliminated" if new_tier == "KILL_LIST" else "paused"
        record["version"] = self._bump_minor(old_version)
        record["promotion_sign_off"] = None  # requires fresh sign-off to re-promote
        record["changelog"].append(
            {
                "date": _today(),
                "action": "demoted",
                "details": f"{old_tier} → {new_tier} | reason={reason}",
            }
        )
        self._save()
        return record

    def set_status(
        self,
        strategy_id: str,
        status: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Update the operational status of a strategy without changing its tier.

        Valid statuses: active, paused, eliminated, pending_review.

        Args:
            strategy_id: Target strategy.
            status:      New status.
            notes:       Optional rationale.

        Returns:
            Updated strategy record.
        """
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {VALID_STATUSES}")

        record = self._require(strategy_id)
        old_status = record["status"]
        record["status"] = status
        record["changelog"].append(
            {
                "date": _today(),
                "action": "status_changed",
                "details": f"{old_status} → {status}" + (f" | {notes}" if notes else ""),
            }
        )
        self._save()
        return record

    # ── Queries ──────────────────────────────────────────────────────

    def get_core_strategies(self) -> List[Dict[str, Any]]:
        """
        Return all strategy records in the CORE tier.

        Sorted by strategy_id for deterministic ordering.
        """
        return sorted(
            [r for r in self._data["strategies"].values() if r["tier"] == "CORE"],
            key=lambda r: r["strategy_id"],
        )

    def get_incubator_strategies(self) -> List[Dict[str, Any]]:
        """Return all INCUBATOR tier strategy records."""
        return sorted(
            [r for r in self._data["strategies"].values() if r["tier"] == "INCUBATOR"],
            key=lambda r: r["strategy_id"],
        )

    def get_kill_list(self) -> List[Dict[str, Any]]:
        """Return all KILL_LIST tier strategy records."""
        return sorted(
            [r for r in self._data["strategies"].values() if r["tier"] == "KILL_LIST"],
            key=lambda r: r["strategy_id"],
        )

    def get_pending_review(self) -> List[Dict[str, Any]]:
        """
        Return strategies awaiting promotion review.

        A strategy is pending_review when:
        - status == 'pending_review', OR
        - tier == 'INCUBATOR' AND status == 'active' AND backtest results
          exist (win_rate is not None) AND no promotion_sign_off on record.
        """
        pending = []
        for record in self._data["strategies"].values():
            if record["status"] == "pending_review":
                pending.append(record)
            elif (
                record["tier"] == "INCUBATOR"
                and record["status"] == "active"
                and record["backtest_results"].get("win_rate") is not None
                and record["promotion_sign_off"] is None
            ):
                pending.append(record)
        return sorted(pending, key=lambda r: r["strategy_id"])

    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """Return all strategy records sorted by tier then strategy_id."""
        tier_order = {"CORE": 0, "INCUBATOR": 1, "KILL_LIST": 2}
        return sorted(
            self._data["strategies"].values(),
            key=lambda r: (tier_order.get(r["tier"], 9), r["strategy_id"]),
        )

    # ── Reporting ────────────────────────────────────────────────────

    def export_report(self) -> Dict[str, Any]:
        """
        Generate a summary dict suitable for a PM dashboard.

        Returns:
            Dict with:
                - generated_at: ISO timestamp
                - schema_version: registry schema version
                - counts: per-tier and per-status breakdowns
                - core: list of CORE strategies with key metrics
                - incubator: list of INCUBATOR strategies with key metrics
                - kill_list: list of strategy IDs on KILL_LIST
                - pending_review: strategies awaiting promotion
                - promotion_criteria: imported from whitelist metadata
        """
        def _summary(record: Dict[str, Any]) -> Dict[str, Any]:
            bt = record.get("backtest_results") or {}
            wf = record.get("walk_forward_results") or {}
            return {
                "strategy_id": record["strategy_id"],
                "name": record["name"],
                "version": record["version"],
                "family": record["family"],
                "tier": record["tier"],
                "status": record["status"],
                "promoted_at": record.get("promoted_at"),
                "backtest": {
                    "win_rate": bt.get("win_rate"),
                    "sharpe": bt.get("sharpe"),
                    "expectancy": bt.get("expectancy"),
                    "max_dd": bt.get("max_dd"),
                    "total_trades": bt.get("total_trades"),
                },
                "oos_sharpe": wf.get("oos_sharpe"),
                "has_wfv": wf.get("oos_sharpe") is not None,
                "has_stress_test": record.get("stress_test_results") is not None,
                "sign_off": record.get("promotion_sign_off") is not None,
            }

        strategies = self._data["strategies"]
        tier_counts: Dict[str, int] = {"CORE": 0, "INCUBATOR": 0, "KILL_LIST": 0}
        status_counts: Dict[str, int] = {}
        for r in strategies.values():
            tier_counts[r["tier"]] = tier_counts.get(r["tier"], 0) + 1
            status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

        core = [_summary(r) for r in self.get_core_strategies()]
        incubator = [_summary(r) for r in self.get_incubator_strategies()]
        kill_ids = [r["strategy_id"] for r in self.get_kill_list()]
        pending = [_summary(r) for r in self.get_pending_review()]

        return {
            "generated_at": _utcnow(),
            "schema_version": self._data.get("schema_version", "1.0"),
            "counts": {
                "total": len(strategies),
                "by_tier": tier_counts,
                "by_status": status_counts,
            },
            "core": core,
            "incubator": incubator,
            "kill_list": kill_ids,
            "pending_review": pending,
            "promotion_criteria": {
                "min_trades": 30,
                "min_win_rate": 0.50,
                "min_expectancy_pct": 0.5,
                "min_sharpe": 1.0,
            },
            "demotion_criteria": {
                "max_drawdown_pct": 5.0,
                "min_win_rate": 0.30,
                "max_consecutive_losses": 5,
            },
        }

    # ── Bootstrap ────────────────────────────────────────────────────

    def auto_register_from_whitelist(
        self,
        whitelist_path: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Bootstrap the registry from an existing core_whitelist.json.

        Reads the three lists (core_strategies, incubator_strategies,
        kill_list) and registers any strategy that is not already present.
        Existing records are never overwritten.

        Args:
            whitelist_path: Path to core_whitelist.json.
                            Defaults to trading/data/core_whitelist.json.

        Returns:
            Dict with counts: {registered, skipped}.
        """
        default_wl = Path(__file__).parent / "data" / "core_whitelist.json"
        wl_path = Path(whitelist_path) if whitelist_path else default_wl

        if not wl_path.exists():
            raise FileNotFoundError(f"Whitelist not found: {wl_path}")

        with open(wl_path, "r", encoding="utf-8") as fh:
            wl: Dict[str, Any] = json.load(fh)

        # (list_key, tier, status)
        sections = [
            ("core_strategies",      "CORE",      "active"),
            ("incubator_strategies", "INCUBATOR", "active"),
            ("kill_list",            "KILL_LIST", "eliminated"),
        ]

        registered = 0
        skipped = 0

        for list_key, tier, status in sections:
            for sid in wl.get(list_key, []):
                if sid in self._data["strategies"]:
                    skipped += 1
                    continue

                family = _infer_family(sid)
                name = sid.replace("_", " ").title()
                now = _utcnow()

                record = _make_record(
                    strategy_id=sid,
                    name=name,
                    family=family,
                    tier=tier,
                    status=status,
                    params={},
                    created_at=now,
                )

                # KILL_LIST entries have no promoted_at
                if tier == "KILL_LIST":
                    record["promoted_at"] = None
                    record["status"] = "eliminated"
                    record["changelog"] = [
                        {
                            "date": _today(),
                            "action": "registered",
                            "details": (
                                "Bootstrapped from core_whitelist.json into "
                                "tier=KILL_LIST (negative forward-test PnL)"
                            ),
                        }
                    ]

                self._data["strategies"][sid] = record
                registered += 1

        if registered > 0:
            self._save()

        return {"registered": registered, "skipped": skipped}

    # ── Internal Helpers ─────────────────────────────────────────────

    def _require(self, strategy_id: str) -> Dict[str, Any]:
        """Return record or raise KeyError if not found."""
        record = self._data["strategies"].get(strategy_id)
        if record is None:
            raise KeyError(
                f"Strategy '{strategy_id}' not found in registry. "
                "Call register() first."
            )
        return record

    @staticmethod
    def _bump_patch(version: str) -> str:
        """Increment the patch component of a semver string."""
        parts = version.split(".")
        if len(parts) != 3:
            return version
        try:
            return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
        except ValueError:
            return version

    @staticmethod
    def _bump_minor(version: str) -> str:
        """Increment the minor component and reset patch."""
        parts = version.split(".")
        if len(parts) != 3:
            return version
        try:
            return f"{parts[0]}.{int(parts[1]) + 1}.0"
        except ValueError:
            return version
