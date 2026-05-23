"""CLI entry point for the Coinglass DNA Bundle."""
import argparse
import logging
import os

from . import config
from . import ratio_store
from .signal_engine import scan_all
from .paper_portfolio import open_positions_from_picks, monitor_positions, get_portfolio_summary
from .discord_notify import send_signal_alerts, send_portfolio_summary, send_no_picks_alert
from .data_fetcher import fetch_all_ratios

logger = logging.getLogger(__name__)


def cmd_scan():
    logger.info("=== Coinglass DNA Scanner ===")
    picks = scan_all()
    logger.info("Generated %d picks", len(picks))
    if picks:
        send_signal_alerts(picks)
    else:
        # Send heartbeat so users know the system is alive
        try:
            summary = get_portfolio_summary()
            active = summary.get("open_positions", 0)
        except Exception:
            active = 0
        send_no_picks_alert(
            symbols_scanned=len(config.SYMBOLS),
            active_positions=active,
        )
    return picks


def cmd_portfolio(picks=None):
    logger.info("=== Portfolio Monitor ===")
    if picks:
        open_positions_from_picks(picks)
    monitor_positions()
    summary = get_portfolio_summary()
    logger.info("Equity: $%.2f | Open: %d | Win rate: %.1f%%",
                summary["equity"], summary["open_positions"], summary["win_rate"])
    return summary


def cmd_summary():
    logger.info("=== Portfolio Summary ===")
    summary = get_portfolio_summary()
    ratio_snapshot = {}
    for symbol in config.SYMBOLS:
        ratios = fetch_all_ratios(symbol)
        ratio_snapshot[symbol] = ratios
    send_portfolio_summary(summary, ratio_snapshot)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Coinglass DNA Bundle Scanner")
    parser.add_argument("--scan", action="store_true", help="Fetch ratios and generate signals")
    parser.add_argument("--portfolio", action="store_true", help="Monitor paper portfolio")
    parser.add_argument("--summary", action="store_true", help="Send Discord portfolio summary")
    parser.add_argument("--init-db", action="store_true", help="Initialize database only")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")

    if os.environ.get("DISCORD_WEBHOOK_PAPERTRADE"):
        from . import discord_notify
        discord_notify.WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_PAPERTRADE"]

    ratio_store.init_db()

    if args.init_db:
        logger.info("Database initialized at %s", config.DB_PATH)
        return

    picks = None
    try:
        if args.scan:
            picks = cmd_scan()
        if args.portfolio:
            cmd_portfolio(picks)
        if args.summary:
            cmd_summary()

        if not any([args.scan, args.portfolio, args.summary, args.init_db]):
            picks = cmd_scan()
            cmd_portfolio(picks)
    except Exception as exc:
        logger.error("Scanner error (non-fatal): %s", exc)

    ratio_store.prune_old(days=60)
    logger.info("Done.")


if __name__ == "__main__":
    main()
