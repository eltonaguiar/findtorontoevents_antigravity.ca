"""
Token Unlock Event-Driven Strategy — SKELETON (S0)

STATUS: S0 (hypothesis only). NO LIVE EMISSION until S4.

Strategy Factory v1.1, Tier 1 #1.

Thesis: Scheduled on-chain token unlocks create a mechanically-known supply
shock. Large investor-tier unlocks (>5% float) have historically produced
negative cumulative abnormal returns in the T-72h..T+24h window; small
investor-tier unlocks (<2% float) have produced post-event relief bounces.

See:
- docs/hypotheses/token_unlock_event_driven.md
- docs/event_studies/token_unlock_calibration_plan.md

This file intentionally contains NO business logic. All methods raise
NotImplementedError. Do not import into any live scheduler.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# S0 lifecycle guard
# ---------------------------------------------------------------------------
S0_STATUS: str = "HYPOTHESIS_ONLY"
LIVE_EMISSION_ALLOWED: bool = False  # flips True only at S4


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------
class UnlockCategory(Enum):
    """Recipient class for a vesting release."""
    INVESTOR = "investor"          # seed / strategic / VC tranches
    TEAM = "team"                  # founders / core contributors
    FOUNDATION = "foundation"      # treasury / ecosystem
    AIRDROP = "airdrop"            # retroactive / community distribution
    TGE = "tge"                    # token generation event / initial listing
    STAKING_REWARD = "staking"     # protocol-emitted rewards
    UNKNOWN = "unknown"


class Direction(Enum):
    LONG = 1
    SHORT = -1


@dataclass(frozen=True)
class Unlock:
    """A scheduled token unlock event."""
    asset: str                     # e.g. "ARB", "APT"
    unlock_ts: datetime            # UTC block-time of release
    token_amount: float            # native token units released
    pct_of_float: float            # fraction of current circulating supply
    category: UnlockCategory
    source: str                    # "tokenunlocks.app" | "cryptorank" | "onchain"
    contract_address: Optional[str] = None
    recipient_label: Optional[str] = None


@dataclass(frozen=True)
class Signal:
    """Event-scoped trade signal. Not emitted before S4."""
    asset: str
    direction: Direction
    entry_ts: datetime
    exit_ts: datetime
    risk_pct: float                # fraction of equity at risk
    unlock_ref: Unlock
    rationale: str


# ---------------------------------------------------------------------------
# Strategy skeleton
# ---------------------------------------------------------------------------
class TokenUnlockEventStrategy:
    """
    Skeleton for the token-unlock event-driven strategy.

    Lifecycle:
        S0 — hypothesis doc + calibration plan (THIS COMMIT).
        S1 — event-study calibration via tools/backtest_token_unlock.py.
        S2 — feature engineering (funding, regime, size bucket).
        S3 — walk-forward backtest with costs.
        S4 — paper trading; live emission gated on paper PnL.

    Parameters (final values set at S2):
        entry_lead_hours:  default 72
        exit_lag_hours:    default 24
        min_pct_float_short: default 0.05
        max_pct_float_long:  default 0.02
        max_concurrent:      default 3
        risk_per_trade:      default 0.005
    """

    def __init__(
        self,
        entry_lead_hours: int = 72,
        exit_lag_hours: int = 24,
        min_pct_float_short: float = 0.05,
        max_pct_float_long: float = 0.02,
        max_concurrent: int = 3,
        risk_per_trade: float = 0.005,
    ) -> None:
        self.entry_lead_hours = entry_lead_hours
        self.exit_lag_hours = exit_lag_hours
        self.min_pct_float_short = min_pct_float_short
        self.max_pct_float_long = max_pct_float_long
        self.max_concurrent = max_concurrent
        self.risk_per_trade = risk_per_trade
        self._status = S0_STATUS

    # ------------------------------------------------------------------
    # Data ingestion
    # ------------------------------------------------------------------
    def fetch_upcoming_unlocks(self, days_ahead: int) -> List[Unlock]:
        """
        Return scheduled unlocks within [now, now + days_ahead].

        S1 will implement against tokenunlocks.app public JSON with
        fallback to CryptoRank and on-chain contract reads (Sablier /
        Hedgey / OZ VestingWallet).
        """
        raise NotImplementedError("S0 skeleton — implemented at S1.")

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    def classify_unlock(self, u: Unlock) -> UnlockCategory:
        """
        Classify an unlock's recipient tier.

        Inputs used at S1:
            - recipient_label string match (regex dictionary)
            - known vesting-contract address map
            - issuer-published allocation tables
        """
        raise NotImplementedError("S0 skeleton — implemented at S1.")

    # ------------------------------------------------------------------
    # Signal logic
    # ------------------------------------------------------------------
    def compute_expected_direction(self, u: Unlock) -> Optional[Direction]:
        """
        Map (category, pct_of_float) → expected trade direction.

        Hypothesis mapping (S0):
            INVESTOR, pct >= min_pct_float_short   → SHORT
            INVESTOR, pct <= max_pct_float_long    → LONG (relief bounce)
            TEAM / FOUNDATION                      → None (asymmetric; test-only)
            AIRDROP / TGE                          → None (separate regime)
            else                                   → None
        """
        raise NotImplementedError("S0 skeleton — implemented at S1.")

    def generate_signal(self, u: Unlock, now: datetime) -> Optional[Signal]:
        """
        Produce an event-scoped Signal if `now` is within the entry
        window and validation passes.

        GUARD: while LIVE_EMISSION_ALLOWED is False this method must
        never return a non-None Signal to any live scheduler.
        """
        if not LIVE_EMISSION_ALLOWED:
            return None
        raise NotImplementedError("S0 skeleton — implemented at S4.")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate_event_window(self, u: Unlock, candles: list) -> bool:
        """
        Pre-trade sanity checks on the T-7d..T-72h window:

        - Liquidity: 30d median 24h perp volume >= $20M.
        - Pre-emption: |return(T-7d..T-72h)| / |expected CAR| < 0.30.
          If pre-emption share too large, skip (front-run already occurred).
        - Macro guard: no Fed/CPI event inside T-24h..T+24h.
        - Correlation guard: not already holding correlated exposure.
        """
        raise NotImplementedError("S0 skeleton — implemented at S2.")


__all__ = [
    "S0_STATUS",
    "LIVE_EMISSION_ALLOWED",
    "UnlockCategory",
    "Direction",
    "Unlock",
    "Signal",
    "TokenUnlockEventStrategy",
]
