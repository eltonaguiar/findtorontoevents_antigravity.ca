"""CLI orchestrator for the Opposite Day sandbox.

Usage:
    python -m sandbox --all
    python -m sandbox --scan --snapshot --close --notify
    python -m sandbox --scan --dry-run
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

from sandbox.engine_adapters import fetch_all_opposite_picks
from sandbox.tracker import Tracker
from sandbox.prices import fetch_prices
from sandbox.pnl import compute_pnl_pct, check_tp_sl
from sandbox.discord_notify import send_notifications

log = logging.getLogger("sandbox")


def phase_scan(tracker: Tracker):
    """Phase 1: Read all engines, create opposite picks for new signals."""
    log.info("=== PHASE 1: SCAN ===")
    picks = fetch_all_opposite_picks()
    log.info("Total opposite picks from adapters: %d", len(picks))
    inserted = tracker.insert_picks(picks)
    log.info("New picks inserted: %d", inserted)
    active = tracker.get_active_picks()
    log.info("Total active opposite picks: %d", len(active))


def phase_snapshot(tracker: Tracker):
    """Phase 2: Record timeline snapshots at 1h/4h/12h/24h checkpoints."""
    log.info("=== PHASE 2: SNAPSHOT ===")
    now = datetime.now(timezone.utc)
    due = tracker.get_due_snapshots(now)
    if not due:
        log.info("No snapshots due this run.")
        return

    symbols = list({pick["symbol"] for pick, _ in due})
    prices = fetch_prices(symbols)
    log.info("Fetched prices for %d/%d symbols", len(prices), len(symbols))

    recorded = 0
    for pick, checkpoint in due:
        sym = pick["symbol"]
        price = prices.get(sym)
        if price is None:
            log.warning("No price for %s - skipping snapshot", sym)
            continue

        opp_pnl = compute_pnl_pct(pick["entry_price"], price, pick["opposite_direction"])
        orig_pnl = compute_pnl_pct(pick["entry_price"], price, pick["original_direction"])
        orig_status = check_tp_sl(
            pick["entry_price"], price,
            pick["original_tp"], pick["original_sl"],
            pick["original_direction"],
        )

        tracker.insert_snapshot(
            pick["pick_id"], checkpoint, price,
            opp_pnl, orig_pnl, orig_status,
        )
        recorded += 1

    log.info("Recorded %d timeline snapshots", recorded)


def phase_close(tracker: Tracker):
    """Phase 3: Close picks that hit TP/SL or expired."""
    log.info("=== PHASE 3: CLOSE ===")
    now = datetime.now(timezone.utc)
    active = tracker.get_active_picks()
    if not active:
        log.info("No active picks to close-check.")
        return

    symbols = list({p["symbol"] for p in active})
    prices = fetch_prices(symbols)

    closed_count = 0
    for pick in active:
        sym = pick["symbol"]
        price = prices.get(sym)
        if price is None:
            continue

        opp_pnl = compute_pnl_pct(pick["entry_price"], price, pick["opposite_direction"])
        orig_pnl = compute_pnl_pct(pick["entry_price"], price, pick["original_direction"])

        status = check_tp_sl(
            pick["entry_price"], price,
            pick["opposite_tp"], pick["opposite_sl"],
            pick["opposite_direction"],
        )

        if status != "ACTIVE":
            tracker.close_pick(pick["pick_id"], status, price, opp_pnl, orig_pnl)
            closed_count += 1
            log.info("  Closed %s %s %s -> %s (%.2f%%)",
                     pick["source_engine"], pick["symbol"],
                     pick["opposite_direction"], status, opp_pnl)

    # Expire old picks
    expired = tracker.get_expired_picks(now)
    for pick in expired:
        price = prices.get(pick["symbol"])
        if price:
            opp_pnl = compute_pnl_pct(pick["entry_price"], price, pick["opposite_direction"])
            orig_pnl = compute_pnl_pct(pick["entry_price"], price, pick["original_direction"])
        else:
            opp_pnl = 0.0
            orig_pnl = 0.0
        tracker.close_pick(pick["pick_id"], "EXPIRED", price or 0, opp_pnl, orig_pnl)
        closed_count += 1
        log.info("  Expired %s %s", pick["source_engine"], pick["symbol"])

    log.info("Closed %d picks this run", closed_count)


def phase_notify(tracker: Tracker, dry_run: bool = False):
    """Phase 4: Post Discord embeds."""
    log.info("=== PHASE 4: NOTIFY ===")
    if dry_run:
        log.info("Dry-run mode - skipping Discord post")
        return
    ok = send_notifications(tracker)
    log.info("Discord notification %s", "sent" if ok else "FAILED")


def main():
    parser = argparse.ArgumentParser(description="Opposite Day Paper-Trade System")
    parser.add_argument("--scan", action="store_true", help="Scan engines for new picks")
    parser.add_argument("--snapshot", action="store_true", help="Record timeline snapshots")
    parser.add_argument("--close", action="store_true", help="Close TP/SL/expired picks")
    parser.add_argument("--notify", action="store_true", help="Send Discord notifications")
    parser.add_argument("--dry-run", action="store_true", help="Skip Discord posting")
    parser.add_argument("--all", action="store_true", help="Run all phases")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    if args.all:
        args.scan = args.snapshot = args.close = args.notify = True

    if not any([args.scan, args.snapshot, args.close, args.notify]):
        log.error("No phases selected. Use --all or --scan --snapshot --close --notify")
        sys.exit(1)

    tracker = Tracker()
    try:
        if args.scan:
            phase_scan(tracker)
        if args.snapshot:
            phase_snapshot(tracker)
        if args.close:
            phase_close(tracker)
        if args.notify:
            phase_notify(tracker, dry_run=args.dry_run)
    finally:
        tracker.close()

    log.info("=== Opposite Day run complete ===")


if __name__ == "__main__":
    main()
