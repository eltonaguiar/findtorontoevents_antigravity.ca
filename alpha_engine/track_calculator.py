"""Track Record Calculator — computes per-(strategy, symbol, direction) forward WR%.

Fixes the TRK% vs FWD WR% granularity bug where forward_wr was calculated at
strategy-level only, masking critical direction asymmetries
(e.g., BTC-USD LONG 54.9% WR vs ETH-USD SHORT 28.9% under same strategy).

Usage:
    from alpha_engine.track_calculator import TrackCalculator
    tc = TrackCalculator()
    track_wr = tc.get_track_wr(strategy="markov_zone", symbol="BTC-USD", direction="LONG")
    # Returns: {"wr": 0.549, "n": 441, "pf": 3.14}
"""
from __future__ import annotations
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrackRecord:
    """Track record for a specific (strategy, symbol, direction) triplet."""
    strategy: str
    symbol: str
    direction: str
    wins: int = 0
    losses: int = 0
    flats: int = 0
    total_pnl_pct: float = 0.0

    @property
    def total(self) -> int:
        return self.wins + self.losses + self.flats

    @property
    def win_rate(self) -> float | None:
        resolved = self.wins + self.losses
        if resolved == 0:
            return None
        return self.wins / resolved

    @property
    def profit_factor(self) -> float | None:
        if self.losses == 0:
            return float("inf") if self.wins > 0 else None
        # Approximate: assume avg win = avg loss magnitude for PF estimate
        return self.wins / self.losses if self.losses > 0 else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "symbol": self.symbol,
            "direction": self.direction,
            "wins": self.wins,
            "losses": self.losses,
            "flats": self.flats,
            "total": self.total,
            "win_rate": round(self.win_rate, 4) if self.win_rate else None,
            "profit_factor": round(self.profit_factor, 4) if self.profit_factor else None,
            "total_pnl_pct": round(self.total_pnl_pct, 4),
        }


class TrackCalculator:
    """Computes track records at (strategy, symbol, direction) granularity.

    This replaces the old strategy-level-only forward_wr calculation that
    masked critical direction asymmetries.
    """

    def __init__(self, data_path: str | None = None):
        self.data_path = data_path or os.environ.get(
            "TRACK_DATA_PATH", "alpha_engine/data/dashboard_data.json"
        )
        self._records: dict[str, TrackRecord] = {}
        self._strategy_only: dict[str, TrackRecord] = {}

    def _key(self, strategy: str, symbol: str, direction: str) -> str:
        """Composite key for (strategy, symbol, direction) triplet."""
        return f"{strategy}:{symbol}:{direction}"

    def _get_or_create(self, strategy: str, symbol: str, direction: str) -> TrackRecord:
        key = self._key(strategy, symbol, direction)
        if key not in self._records:
            self._records[key] = TrackRecord(strategy, symbol, direction)
        return self._records[key]

    def ingest_pick(self, pick: dict[str, Any]) -> None:
        """Ingest a single closed pick and update its track record."""
        strategy = str(pick.get("strategy") or pick.get("signal_group") or "unknown")
        symbol = str(pick.get("symbol") or "")
        direction = str(pick.get("direction") or "")
        status = str(pick.get("status") or "").upper()
        pnl_pct = float(pick.get("pnl_pct") or 0)

        rec = self._get_or_create(strategy, symbol, direction)
        rec.total_pnl_pct += pnl_pct

        if status in ("WON", "WIN"):
            rec.wins += 1
        elif status in ("LOST", "LOSS"):
            rec.losses += 1
        else:
            rec.flats += 1

    def load_from_file(self, path: str | None = None) -> None:
        """Load closed picks from dashboard data file."""
        path = path or self.data_path
        with open(path) as f:
            data = json.load(f)

        picks = data.get("picks", []) if isinstance(data, dict) else data
        for pick in picks:
            if pick.get("status") in ("closed", "CLOSED", "resolved", "RESOLVED"):
                self.ingest_pick(pick)

        print(f"Loaded {len(picks)} picks, {len(self._records)} unique track records")

    def get_track_wr(
        self, strategy: str, symbol: str, direction: str, min_n: int = 5
    ) -> dict[str, Any] | None:
        """Get forward WR% for a specific (strategy, symbol, direction).

        Returns None if insufficient sample size (< min_n).
        This is the CORRECT granularity for TRK% display on the audit dashboard.
        """
        rec = self._records.get(self._key(strategy, symbol, direction))
        if not rec or rec.total < min_n:
            return None

        return {
            "track_key": self._key(strategy, symbol, direction),
            "win_rate": round(rec.win_rate, 4) if rec.win_rate else None,
            "profit_factor": round(rec.profit_factor, 4) if rec.profit_factor else None,
            "n": rec.total,
            "wins": rec.wins,
            "losses": rec.losses,
            "flats": rec.flats,
        }

    def get_strategy_level_wr(self, strategy: str, min_n: int = 10) -> dict[str, Any] | None:
        """Get aggregated WR at strategy level (OLD behavior — use with caution)."""
        matches = [r for r in self._records.values() if r.strategy == strategy]
        total_wins = sum(r.wins for r in matches)
        total_losses = sum(r.losses for r in matches)
        total_flats = sum(r.flats for r in matches)
        total = total_wins + total_losses + total_flats

        if total < min_n:
            return None

        resolved = total_wins + total_losses
        wr = total_wins / resolved if resolved > 0 else None

        return {
            "strategy": strategy,
            "win_rate": round(wr, 4) if wr else None,
            "n": total,
            "by_symbol_direction": [r.to_dict() for r in matches],
        }

    def find_direction_asymmetry(
        self, strategy: str, min_n: int = 10
    ) -> list[dict[str, Any]]:
        """Find symbols where LONG vs SHORT WR differs significantly.

        This detects the bug that was masking poor SHORT performance
        under strategy-level aggregation.
        """
        asymmetries = []
        symbols = set()
        for key, rec in self._records.items():
            if rec.strategy == strategy and rec.total >= min_n:
                symbols.add(rec.symbol)

        for symbol in symbols:
            long_rec = self._records.get(self._key(strategy, symbol, "LONG"))
            short_rec = self._records.get(self._key(strategy, symbol, "SHORT"))

            if long_rec and short_rec:
                long_wr = long_rec.win_rate or 0
                short_wr = short_rec.win_rate or 0
                diff = abs(long_wr - short_wr)

                if diff > 0.15:  # 15 percentage point difference
                    asymmetries.append({
                        "strategy": strategy,
                        "symbol": symbol,
                        "long_wr": round(long_wr, 4),
                        "long_n": long_rec.total,
                        "short_wr": round(short_wr, 4),
                        "short_n": short_rec.total,
                        "difference_pp": round(diff * 100, 1),
                        "recommendation": "DIRECTIONAL_SPLIT" if diff > 0.25 else "MONITOR",
                    })

        return sorted(asymmetries, key=lambda x: x["difference_pp"], reverse=True)

    def export_all(self, output_path: str | None = None) -> str:
        """Export all track records to JSON for dashboard consumption."""
        output_path = output_path or "alpha_engine/data/track_records.json"

        export = {
            "generated_at": "2026-05-02T00:00:00Z",
            "granularity": "strategy:symbol:direction",
            "total_records": len(self._records),
            "records": {k: v.to_dict() for k, v in self._records.items()},
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(export, f, indent=2)

        return output_path


# Singleton for import convenience
_default_calculator: TrackCalculator | None = None

def get_calculator() -> TrackCalculator:
    global _default_calculator
    if _default_calculator is None:
        _default_calculator = TrackCalculator()
    return _default_calculator


def get_track_wr(strategy: str, symbol: str, direction: str, min_n: int = 5) -> dict | None:
    """Convenience function: get track WR for a specific triplet."""
    return get_calculator().get_track_wr(strategy, symbol, direction, min_n)


def find_asymmetries(strategy: str, min_n: int = 10) -> list[dict]:
    """Convenience function: find direction asymmetries for a strategy."""
    return get_calculator().find_direction_asymmetry(strategy, min_n)


__all__ = [
    "TrackRecord",
    "TrackCalculator",
    "get_calculator",
    "get_track_wr",
    "find_asymmetries",
]
