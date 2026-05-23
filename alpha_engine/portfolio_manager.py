"""
Portfolio Manager -- Three parallel risk profiles with independent P&L tracking.

Each portfolio (conservative / moderate / aggressive) has its own:
  - Position limits and concentration rules
  - Circuit breaker with graduated recovery (per Google/Gemini review)
  - TournamentEngine instance for independent tier tracking
  - Capital and drawdown tracking

Graduated recovery protocol:
  1. Drawdown >= circuit_breaker_pct  -> FROZEN (no new positions)
  2. After 24h cooldown              -> half_size mode (50% position sizing)
  3. After 7 days no new drawdown    -> full size restored
  4. Frozen 2x in 30 days           -> hard freeze (manual review required)
"""

import time
from typing import Optional

from alpha_engine.tournament_engine import TournamentEngine

# ---- Portfolio configurations ------------------------------------------------

PORTFOLIO_CONFIGS = {
    "conservative": {
        "min_families": 3,
        "max_positions": 10,
        "max_per_symbol": 1,
        "max_same_direction": 4,
        "circuit_breaker_pct": 0.05,
        "starting_capital": 10_000.0,
        "kelly_cap": 0.03,
    },
    "moderate": {
        "min_families": 2,
        "max_positions": 20,
        "max_per_symbol": 2,
        "max_same_direction": 6,
        "circuit_breaker_pct": 0.10,
        "starting_capital": 10_000.0,
        "kelly_cap": 0.05,
    },
    "aggressive": {
        "min_families": 2,
        "max_positions": 30,
        "max_per_symbol": 3,
        "max_same_direction": 8,
        "circuit_breaker_pct": 0.15,
        "starting_capital": 10_000.0,
        "kelly_cap": 0.08,
    },
}

# Time constants for graduated recovery
COOLDOWN_SECONDS = 24 * 3600          # 24 hours before half-size
FULL_RECOVERY_SECONDS = 7 * 24 * 3600  # 7 days for full recovery
HARD_FREEZE_WINDOW = 30 * 24 * 3600    # 30-day window for double-freeze check


class Portfolio:
    """Single portfolio with position tracking and graduated circuit breaker."""

    def __init__(self, name: str, config: dict, tournament: TournamentEngine):
        self.name = name
        self.config = config
        self.tournament = tournament

        self._starting_capital = config["starting_capital"]
        self._pnl = 0.0
        self._peak_capital = self._starting_capital

        # Position tracking
        self._positions: list[dict] = []  # [{symbol, direction}, ...]

        # Circuit breaker state
        self.freeze_count = 0
        self.last_freeze_at: Optional[float] = None
        self._freeze_history: list[float] = []  # timestamps of all freezes
        self.half_size_mode = False
        self._hard_frozen = False

    # ---- Capital properties --------------------------------------------------

    @property
    def current_capital(self) -> float:
        return self._starting_capital + self._pnl

    @property
    def drawdown_pct(self) -> float:
        if self._peak_capital <= 0:
            return 0.0
        return max(0.0, (self._peak_capital - self.current_capital) / self._peak_capital)

    # ---- Circuit breaker -----------------------------------------------------

    def freeze(self, now: Optional[float] = None) -> None:
        """Record a freeze event."""
        now = now or time.time()
        self.last_freeze_at = now
        self.freeze_count += 1
        self._freeze_history.append(now)
        self.half_size_mode = False

        # Check for hard freeze: 2+ freezes within 30 days
        recent = [t for t in self._freeze_history if now - t < HARD_FREEZE_WINDOW]
        if len(recent) >= 2:
            self._hard_frozen = True

    def is_frozen(self, now: Optional[float] = None) -> bool:
        """Check frozen status with graduated recovery.

        Returns True if portfolio cannot open new positions.
        Side effect: may transition to half_size_mode during check.
        """
        # Hard freeze requires manual review -- always frozen
        if self._hard_frozen:
            return True

        # Check if currently in drawdown breach
        if self.drawdown_pct >= self.config["circuit_breaker_pct"]:
            if self.last_freeze_at is None:
                self.freeze(now)
            return True

        # Not in drawdown breach -- check recovery from previous freeze
        if self.last_freeze_at is None:
            return False

        now = now or time.time()
        elapsed = now - self.last_freeze_at

        if elapsed < COOLDOWN_SECONDS:
            # Still in 24h cooldown
            return True

        if elapsed < FULL_RECOVERY_SECONDS:
            # 24h-7d: half-size mode (not frozen, but reduced sizing)
            self.half_size_mode = True
            return False

        # Past 7 days with no new drawdown: full recovery
        self.half_size_mode = False
        self.last_freeze_at = None
        return False

    # ---- Position management -------------------------------------------------

    def can_open_position(self, symbol: str, direction: str) -> bool:
        """Check whether a new position is allowed under portfolio limits."""
        if self.is_frozen():
            return False

        # Max total positions
        if len(self._positions) >= self.config["max_positions"]:
            return False

        # Max per symbol
        symbol_count = sum(1 for p in self._positions if p["symbol"] == symbol)
        if symbol_count >= self.config["max_per_symbol"]:
            return False

        # Max same direction
        dir_count = sum(1 for p in self._positions if p["direction"] == direction)
        if dir_count >= self.config["max_same_direction"]:
            return False

        return True

    def open_position(self, symbol: str, direction: str) -> None:
        """Record a new open position."""
        self._positions.append({"symbol": symbol, "direction": direction})

    def close_position(self, symbol: str, direction: str) -> None:
        """Remove a position (first matching)."""
        for i, p in enumerate(self._positions):
            if p["symbol"] == symbol and p["direction"] == direction:
                self._positions.pop(i)
                return

    # ---- Confluence gate -----------------------------------------------------

    def accepts_confluence(self, family_count: int) -> bool:
        """Check if signal meets this portfolio's minimum family diversity."""
        return family_count >= self.config["min_families"]

    # ---- P&L -----------------------------------------------------------------

    def record_pnl(self, pnl_dollar: float) -> None:
        """Update running P&L and peak capital."""
        self._pnl += pnl_dollar
        if self.current_capital > self._peak_capital:
            self._peak_capital = self.current_capital

    # ---- Serialization -------------------------------------------------------

    def to_dict(self) -> dict:
        """Snapshot for JSON export."""
        return {
            "name": self.name,
            "current_capital": round(self.current_capital, 2),
            "starting_capital": self._starting_capital,
            "pnl": round(self._pnl, 2),
            "drawdown_pct": round(self.drawdown_pct, 4),
            "peak_capital": round(self._peak_capital, 2),
            "open_positions": len(self._positions),
            "max_positions": self.config["max_positions"],
            "frozen": self.is_frozen(),
            "hard_frozen": self._hard_frozen,
            "half_size_mode": self.half_size_mode,
            "freeze_count": self.freeze_count,
            "min_families": self.config["min_families"],
            "kelly_cap": self.config["kelly_cap"],
            "circuit_breaker_pct": self.config["circuit_breaker_pct"],
        }


class PortfolioManager:
    """Manages 3 parallel portfolios with independent TournamentEngine instances."""

    def __init__(self, db_path: str = "data/tournament.db"):
        self.portfolios: dict[str, Portfolio] = {}
        for name, config in PORTFOLIO_CONFIGS.items():
            tournament = TournamentEngine(db_path=db_path, portfolio=name)
            self.portfolios[name] = Portfolio(name, config, tournament)

    def route_signal(self, confluence_signal: dict) -> list[tuple[str, "Portfolio"]]:
        """Return list of (name, Portfolio) that accept this confluence signal.

        The confluence_signal must have 'family_count' (int) indicating
        how many distinct indicator families contributed.
        """
        family_count = confluence_signal.get("family_count", 0)
        result = []
        for name, portfolio in self.portfolios.items():
            if portfolio.accepts_confluence(family_count):
                result.append((name, portfolio))
        return result

    def get_comparison(self) -> dict[str, dict]:
        """Return snapshots of all 3 portfolios for dashboard comparison."""
        return {name: p.to_dict() for name, p in self.portfolios.items()}
