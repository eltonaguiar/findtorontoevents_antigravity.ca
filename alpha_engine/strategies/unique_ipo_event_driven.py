#!/usr/bin/env python3
"""IPO asset class — delegates to post-listing momentum (lockup SHORT killed in backtest)."""
from __future__ import annotations

from typing import Any

from alpha_engine.winners.ipo_post_listing_winner import generate_ipo_post_listing_winner_picks


def generate_ipo_event_driven_picks() -> list[dict[str, Any]]:
    return generate_ipo_post_listing_winner_picks()


if __name__ == "__main__":
    picks = generate_ipo_event_driven_picks()
    print(f"Generated {len(picks)} IPO picks (REHAB tier; empty if no active window)")
