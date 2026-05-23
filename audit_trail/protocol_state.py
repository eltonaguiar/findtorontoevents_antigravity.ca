"""Protocol State Machine — per-asset-class gate tracking.

Tracks which protocol level each asset class is at, so the dashboard and
production scanner can enforce the right gates per class.

State transitions:
    BLOCKED → REHAB → OOS_READY → SHADOW → LIVE_MICRO → LIVE_SCALE → KILL

Criteria per state (ALL must be met to advance):
    BLOCKED:   DSR<0.5 OR PBO>0.5 OR PF<1.0 OR n<20
    REHAB:     DSR≥0.5 AND PF>1.0 AND n≥20, but failing at least one OOS_READY gate
    OOS_READY: DSR≥0.95 AND PBO<0.50 AND PF>1.5 AND n≥50
    SHADOW:    OOS_READY + 30d paper pilot with Sharpe>0.7×backtest
    LIVE_MICRO:Shadow passed + $500 real money, <5% DD, profitable
    LIVE_SCALE:Micro validated 30d, decision = scale or kill
    KILL:      Failed irrecoverably (PF<0.5 on n≥30, or manual kill)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("protocol_state")

# ── State definitions ──
STATE_BLOCKED = "BLOCKED"
STATE_REHAB = "REHAB"
STATE_OOS_READY = "OOS_READY"
STATE_SHADOW = "SHADOW"
STATE_LIVE_MICRO = "LIVE_MICRO"
STATE_LIVE_SCALE = "LIVE_SCALE"
STATE_KILL = "KILL"

STATE_ORDER = [
    STATE_BLOCKED, STATE_REHAB, STATE_OOS_READY,
    STATE_SHADOW, STATE_LIVE_MICRO, STATE_LIVE_SCALE, STATE_KILL,
]

# ── Criteria thresholds ──
OOS_READY_DSR_MIN = 0.95
OOS_READY_PBO_MAX = 0.50
OOS_READY_PF_MIN = 1.5
OOS_READY_MIN_TRADES = 50

REHAB_DSR_MIN = 0.50
REHAB_PF_MIN = 1.0
REHAB_MIN_TRADES = 20

SHADOW_MIN_DAYS = 30
SHADOW_SHARPE_RATIO = 0.70  # paper Sharpe must be ≥ 0.7 × backtest Sharpe

MICRO_MAX_DD = 0.05  # 5% max drawdown
MICRO_MIN_DAYS = 30


class AssetClassState:
    """State tracker for a single asset class."""

    def __init__(
        self,
        asset_class: str,
        state: str = STATE_BLOCKED,
        dsr: float | None = None,
        pbo: float | None = None,
        pf: float | None = None,
        n_trades: int = 0,
        sharpe: float | None = None,
        paper_sharpe: float | None = None,
        backtest_sharpe: float | None = None,
        shadow_start: str | None = None,
        micro_start: str | None = None,
        micro_dd: float = 0.0,
        micro_pnl_pct: float = 0.0,
        notes: str = "",
    ):
        self.asset_class = asset_class
        self.state = state
        self.dsr = dsr
        self.pbo = pbo
        self.pf = pf
        self.n_trades = n_trades
        self.sharpe = sharpe
        self.paper_sharpe = paper_sharpe
        self.backtest_sharpe = backtest_sharpe
        self.shadow_start = shadow_start
        self.micro_start = micro_start
        self.micro_dd = micro_dd
        self.micro_pnl_pct = micro_pnl_pct
        self.notes = notes
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "asset_class": self.asset_class,
            "state": self.state,
            "criteria": {
                "dsr": self.dsr,
                "pbo": self.pbo,
                "pf": self.pf,
                "n_trades": self.n_trades,
                "sharpe": self.sharpe,
                "paper_sharpe": self.paper_sharpe,
                "backtest_sharpe": self.backtest_sharpe,
            },
            "transitions": {
                "shadow_start": self.shadow_start,
                "micro_start": self.micro_start,
                "micro_dd": self.micro_dd,
                "micro_pnl_pct": self.micro_pnl_pct,
            },
            "notes": self.notes,
            "last_updated": self.last_updated,
        }

    def evaluate(self) -> str:
        """Re-evaluate state based on current criteria. Returns new state."""
        old_state = self.state

        # KILL is terminal
        if self.state == STATE_KILL:
            return STATE_KILL

        # Check BLOCKED first (most common)
        if self._is_blocked():
            self.state = STATE_BLOCKED
            self.notes = self._blocked_reason()
            return self.state

        # Check REHAB
        if self._is_rehab():
            self.state = STATE_REHAB
            return self.state

        # Check OOS_READY
        if self._is_oos_ready():
            self.state = STATE_OOS_READY
            return self.state

        # Check SHADOW
        if self._is_shadow():
            self.state = STATE_SHADOW
            return self.state

        # Check LIVE_MICRO
        if self._is_live_micro():
            self.state = STATE_LIVE_MICRO
            return self.state

        # Check LIVE_SCALE
        if self._is_live_scale():
            self.state = STATE_LIVE_SCALE
            return self.state

        # Default: stay in current state
        return self.state

    def _is_blocked(self) -> bool:
        if self.dsr is not None and self.dsr < OOS_READY_DSR_MIN:
            return True
        if self.pbo is not None and self.pbo > OOS_READY_PBO_MAX:
            return True
        if self.pf is not None and self.pf < OOS_READY_PF_MIN:
            return True
        if self.n_trades < OOS_READY_MIN_TRADES:
            return True
        return False

    def _blocked_reason(self) -> str:
        reasons = []
        if self.dsr is not None and self.dsr < OOS_READY_DSR_MIN:
            reasons.append(f"DSR={self.dsr:.3f}<{OOS_READY_DSR_MIN}")
        if self.pbo is not None and self.pbo > OOS_READY_PBO_MAX:
            reasons.append(f"PBO={self.pbo:.3f}>{OOS_READY_PBO_MAX}")
        if self.pf is not None and self.pf < OOS_READY_PF_MIN:
            reasons.append(f"PF={self.pf:.2f}<{OOS_READY_PF_MIN}")
        if self.n_trades < OOS_READY_MIN_TRADES:
            reasons.append(f"n={self.n_trades}<{OOS_READY_MIN_TRADES}")
        return "; ".join(reasons) if reasons else "unknown"

    def _is_rehab(self) -> bool:
        # Has some edge but failing at least one OOS_READY gate
        if self.dsr is not None and self.dsr >= REHAB_DSR_MIN:
            if self.pf is not None and self.pf >= REHAB_PF_MIN:
                if self.n_trades >= REHAB_MIN_TRADES:
                    # Passes rehab but not OOS_READY
                    if self.pbo is not None and self.pbo > OOS_READY_PBO_MAX:
                        return True
                    if self.dsr < OOS_READY_DSR_MIN:
                        return True
                    if self.pf < OOS_READY_PF_MIN:
                        return True
                    if self.n_trades < OOS_READY_MIN_TRADES:
                        return True
        return False

    def _is_oos_ready(self) -> bool:
        if self.dsr is not None and self.dsr >= OOS_READY_DSR_MIN:
            if self.pbo is not None and self.pbo <= OOS_READY_PBO_MAX:
                if self.pf is not None and self.pf >= OOS_READY_PF_MIN:
                    if self.n_trades >= OOS_READY_MIN_TRADES:
                        return True
        return False

    def _is_shadow(self) -> bool:
        if self.state == STATE_OOS_READY or self.state == STATE_SHADOW:
            if self.paper_sharpe is not None and self.backtest_sharpe is not None:
                if self.backtest_sharpe > 0:
                    ratio = self.paper_sharpe / self.backtest_sharpe
                    return ratio >= SHADOW_SHARPE_RATIO
                return self.paper_sharpe > 0
        return False

    def _is_live_micro(self) -> bool:
        if self.state in (STATE_SHADOW, STATE_LIVE_MICRO):
            if self.micro_start is not None:
                # Must have been in micro for at least MICRO_MIN_DAYS
                try:
                    start_dt = datetime.fromisoformat(self.micro_start)
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    elapsed = (datetime.now(timezone.utc) - start_dt).total_seconds() / 86400
                    if elapsed >= MICRO_MIN_DAYS:
                        if self.micro_dd <= MICRO_MAX_DD and self.micro_pnl_pct > 0:
                            return True
                except (ValueError, TypeError):
                    pass
        return False

    def _is_live_scale(self) -> bool:
        if self.state == STATE_LIVE_MICRO:
            # After micro validation, manual decision needed
            # This state is set by operator, not auto-detected
            return False
        return self.state == STATE_LIVE_SCALE


class ProtocolStateMachine:
    """Manages protocol states for all asset classes."""

    STATE_FILE = Path("audit_dashboard/data/protocol_state.json")

    def __init__(self):
        self.classes: dict[str, AssetClassState] = {}

    def load(self) -> None:
        """Load persisted state from JSON file."""
        if self.STATE_FILE.exists():
            try:
                with open(self.STATE_FILE, "r") as f:
                    data = json.load(f)
                for ac_name, ac_data in data.items():
                    state = AssetClassState(ac_name)
                    state.state = ac_data.get("state", STATE_BLOCKED)
                    crit = ac_data.get("criteria", {})
                    state.dsr = crit.get("dsr")
                    state.pbo = crit.get("pbo")
                    state.pf = crit.get("pf")
                    state.n_trades = crit.get("n_trades", 0)
                    state.sharpe = crit.get("sharpe")
                    state.paper_sharpe = crit.get("paper_sharpe")
                    state.backtest_sharpe = crit.get("backtest_sharpe")
                    trans = ac_data.get("transitions", {})
                    state.shadow_start = trans.get("shadow_start")
                    state.micro_start = trans.get("micro_start")
                    state.micro_dd = trans.get("micro_dd", 0.0)
                    state.micro_pnl_pct = trans.get("micro_pnl_pct", 0.0)
                    state.notes = ac_data.get("notes", "")
                    state.last_updated = ac_data.get("last_updated", "")
                    self.classes[ac_name] = state
            except Exception:
                logger.warning("Could not load protocol state, starting fresh")

    def save(self) -> None:
        """Persist state to JSON file."""
        self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            ac: st.to_dict() for ac, st in self.classes.items()
        }
        with open(self.STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def update(
        self,
        asset_class: str,
        dsr: float | None = None,
        pbo: float | None = None,
        pf: float | None = None,
        n_trades: int | None = None,
        sharpe: float | None = None,
        paper_sharpe: float | None = None,
        backtest_sharpe: float | None = None,
    ) -> AssetClassState:
        """Update criteria for an asset class and re-evaluate state."""
        if asset_class not in self.classes:
            self.classes[asset_class] = AssetClassState(asset_class)

        state = self.classes[asset_class]
        if dsr is not None:
            state.dsr = dsr
        if pbo is not None:
            state.pbo = pbo
        if pf is not None:
            state.pf = pf
        if n_trades is not None:
            state.n_trades = n_trades
        if sharpe is not None:
            state.sharpe = sharpe
        if paper_sharpe is not None:
            state.paper_sharpe = paper_sharpe
        if backtest_sharpe is not None:
            state.backtest_sharpe = backtest_sharpe

        new_state = state.evaluate()
        state.last_updated = datetime.now(timezone.utc).isoformat()
        self.save()
        return state

    def start_shadow(self, asset_class: str) -> None:
        """Manually transition to SHADOW state."""
        if asset_class not in self.classes:
            self.classes[asset_class] = AssetClassState(asset_class)
        self.classes[asset_class].state = STATE_SHADOW
        self.classes[asset_class].shadow_start = datetime.now(timezone.utc).isoformat()
        self.save()

    def start_micro(self, asset_class: str) -> None:
        """Manually transition to LIVE_MICRO state."""
        if asset_class in self.classes:
            self.classes[asset_class].state = STATE_LIVE_MICRO
            self.classes[asset_class].micro_start = datetime.now(timezone.utc).isoformat()
            self.save()

    def scale(self, asset_class: str) -> None:
        """Transition to LIVE_SCALE."""
        if asset_class in self.classes:
            self.classes[asset_class].state = STATE_LIVE_SCALE
            self.save()

    def kill(self, asset_class: str, reason: str = "") -> None:
        """Transition to KILL."""
        if asset_class in self.classes:
            self.classes[asset_class].state = STATE_KILL
            self.classes[asset_class].notes = reason
            self.save()

    def get_state(self, asset_class: str) -> dict | None:
        """Get state dict for an asset class."""
        if asset_class in self.classes:
            return self.classes[asset_class].to_dict()
        return None

    def get_all_states(self) -> dict[str, dict]:
        """Get all states as dict."""
        return {
            ac: st.to_dict() for ac, st in self.classes.items()
        }

    def get_dashboard_summary(self) -> dict:
        """Get summary suitable for dashboard sidebar display."""
        summary = {}
        for ac, st in self.classes.items():
            summary[ac] = {
                "state": st.state,
                "blocked_reason": st.notes if st.state == STATE_BLOCKED else None,
                "last_updated": st.last_updated,
            }
            if st.dsr is not None:
                summary[ac]["dsr"] = round(st.dsr, 3)
            if st.pf is not None:
                summary[ac]["pf"] = round(st.pf, 2)
            if st.n_trades:
                summary[ac]["n"] = st.n_trades
        return summary


# Global singleton
_protocol_machine: ProtocolStateMachine | None = None


def get_protocol_machine() -> ProtocolStateMachine:
    """Get or create the global protocol state machine singleton."""
    global _protocol_machine
    if _protocol_machine is None:
        _protocol_machine = ProtocolStateMachine()
        _protocol_machine.load()
    return _protocol_machine


def evaluate_asset_class(asset_class: str, **criteria) -> dict:
    """Convenience function: update criteria and return new state."""
    machine = get_protocol_machine()
    state = machine.update(asset_class, **criteria)
    return state.to_dict()


if __name__ == "__main__":
    # Demo / smoke test
    print("Protocol State Machine Demo")
    print("=" * 50)

    # Initialize from dashboard_data.json if available
    dd_path = Path("audit_dashboard/data/dashboard_data.json")
    if dd_path.exists():
        with open(dd_path) as f:
            dd = json.load(f)
        hf = dd.get("hf_stats", {})
        by_ac = hf.get("by_asset_class", {})

        machine = get_protocol_machine()

        for ac_name, ac_data in by_ac.items():
            # Map dashboard fields to our criteria
            criteria = {}
            if "dsr" in ac_data:
                criteria["dsr"] = ac_data["dsr"]
            if "pbo" in ac_data:
                criteria["pbo"] = ac_data["pbo"]
            pf_data = ac_data.get("profit_factor")
            if pf_data and "point_estimate" in pf_data:
                criteria["pf"] = pf_data["point_estimate"]
            n_data = ac_data.get("closed_picks")
            if n_data:
                criteria["n_trades"] = n_data
            sr_data = ac_data.get("sharpe_ratio")
            if sr_data and "point_estimate" in sr_data:
                criteria["sharpe"] = sr_data["point_estimate"]

            result = machine.update(ac_name.upper(), **criteria)
            print(f"  {ac_name.upper():12s} → {result.state:14s} (DSR={result.dsr}, PBO={result.pbo}, PF={result.pf}, n={result.n_trades})")

        print(f"\nSaved to: {machine.STATE_FILE}")
        print(f"\nDashboard summary:")
        print(json.dumps(machine.get_dashboard_summary(), indent=2))
    else:
        print(f"Dashboard data not found at {dd_path}")
        print("Initialize manually or run after dashboard generation.")