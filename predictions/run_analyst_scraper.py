#!/usr/bin/env python3
"""
Analyst Tracker — Main entry point.

Runs the analyst scraper, then exports JSON data files for the dashboard.
Designed to be called from GitHub Actions or locally.

Usage:
    python social_prediction_tracker/run_analyst_scraper.py [--seed-only] [--validate]
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Ensure the social_prediction_tracker package is importable
sys.path.insert(0, str(Path(__file__).parent))

from db import get_db, export_analyst_json, export_leaderboard_json
from scrapers.analyst_scraper import run as run_scraper, seed_analysts

DATA_DIR = Path(__file__).parent / "data"
ANALYST_LEADERBOARD_JSON = DATA_DIR / "analyst_leaderboard.json"
ANALYST_ACTIVE_JSON = DATA_DIR / "analyst_active_calls.json"
LEADERBOARD_JSON = DATA_DIR / "leaderboard.json"


def export_data() -> None:
    """Export analyst leaderboard and active calls JSON files."""
    conn = get_db()

    # Export analyst-specific JSONs
    export_analyst_json(conn, ANALYST_LEADERBOARD_JSON, ANALYST_ACTIVE_JSON)
    print(f"[export] Analyst leaderboard -> {ANALYST_LEADERBOARD_JSON}")
    print(f"[export] Analyst active calls -> {ANALYST_ACTIVE_JSON}")

    # Also update the main leaderboard (includes all predictors)
    export_leaderboard_json(conn, LEADERBOARD_JSON)
    print(f"[export] Main leaderboard -> {LEADERBOARD_JSON}")

    conn.close()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Analyst Tracker")
    parser.add_argument("--seed-only", action="store_true",
                        help="Only seed analysts into DB, don't scrape")
    parser.add_argument("--validate", action="store_true",
                        help="Also run price validation after scraping")
    args = parser.parse_args()

    if args.seed_only:
        seed_analysts()
        export_data()
        return

    # Run the scraper
    total = run_scraper()

    # Export data
    export_data()

    # Optionally run price validation
    if args.validate:
        print("\n--- Running price validation ---")
        from validation.price_validator import validate_all
        validate_all()
        # Re-export after validation updates stats
        export_data()

    print(f"\nDone. {total} predictions scraped, data exported to {DATA_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
