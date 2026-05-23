#!/usr/bin/env python3
"""CLI bootstrapper for the earnings calendar cache that PEAD reads from.

Per CLAUDE.md Wire-Up Rule: this script is OPT-IN sidecar tooling. It writes
into ``data/earnings/<TICKER>/latest.json`` so that the already-wired
``vt_equity_earnings_drift_pead`` strategy (alpha_engine/vt_baby_strategies.py:376)
can find a cache entry on disk. It does **not** alter any production code path.

Activation gate (default OFF):
  EARNINGS_FETCHER_ENABLED=1   - required to perform any network/library work.

Without that env var set, the script just ensures ``data/earnings/`` exists
and exits 0. This is so a workflow step can call it unconditionally before
the scanner step without changing production behaviour until both flags
(EARNINGS_FETCHER_ENABLED=1 and UEPS_ENABLE_PEAD=1) are explicitly flipped on.

Why this exists:
  Research/25 (peer w03yqel9) audit confirmed PEAD wires through scanner.py
  -> VT_BABY_STRATEGIES["vt_earnings_pead"] but ``data/earnings/`` is absent
  on disk, so vt_equity_earnings_drift_pead returns []. This bootstraps the
  directory + (optionally) populates a small ticker universe so PEAD can
  emit picks once UEPS_ENABLE_PEAD=1 is flipped.

Default ticker universe is small (S&P core large caps); pass ``--tickers``
or ``--tickers-file`` to override. The fetcher itself uses the existing
``alpha_engine.earnings_calendar_fetcher.EarningsCalendarFetcher`` library
(Finnhub primary -> EDGAR stub -> yfinance fallback), so no new HTTP code.

Examples
--------
  # Bootstrap directory only (no fetch). Safe in CI before any flags flip.
  python tools/earnings_calendar_fetcher.py --bootstrap-only

  # Once gated on, fetch a default universe (yfinance fallback if no key).
  EARNINGS_FETCHER_ENABLED=1 python tools/earnings_calendar_fetcher.py

  # Custom tickers, force-refresh through TTL.
  EARNINGS_FETCHER_ENABLED=1 python tools/earnings_calendar_fetcher.py \
      --tickers AAPL,MSFT,NVDA --force-refresh
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on sys.path so this can run as `python tools/...` from anywhere.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

logger = logging.getLogger("earnings_calendar_fetcher_cli")

# Small, conservative default universe (S&P 500 mega-caps that frequently
# anchor PEAD studies). Kept short on purpose so unattended runs don't
# burn Finnhub free-tier quota or spam yfinance.
DEFAULT_TICKERS: tuple[str, ...] = (
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
    "AVGO", "BRK-B", "JPM", "V", "UNH", "XOM", "JNJ", "WMT",
    "MA", "PG", "HD", "LLY", "COST",
)

CALENDAR_INDEX_FILENAME = "calendar.json"


def _is_enabled() -> bool:
    """Honor the EARNINGS_FETCHER_ENABLED env var. Default OFF."""
    return os.environ.get("EARNINGS_FETCHER_ENABLED", "0").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _ensure_cache_dir(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    keep = cache_dir / ".gitkeep"
    if not keep.exists():
        keep.write_text("", encoding="utf-8")


def _parse_tickers(args: argparse.Namespace) -> list[str]:
    if args.tickers_file:
        path = Path(args.tickers_file)
        if not path.exists():
            raise SystemExit(f"--tickers-file not found: {path}")
        return [
            line.strip().upper()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    if args.tickers:
        return [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    return list(DEFAULT_TICKERS)


def _write_calendar_index(
    cache_dir: Path,
    records_by_ticker: dict,
    *,
    days_ahead: int,
) -> Path:
    """Write a top-level ``calendar.json`` index summarising next-N-days announcements.

    PEAD itself reads ``data/earnings/<TICKER>/latest.json`` (per ticker), but
    the index file is useful for ops dashboards + smoke tests that want a
    one-shot view of what the fetcher cached this run.
    """
    today = datetime.now(timezone.utc).date()
    horizon = today.replace(day=today.day) if False else today  # noqa: E501 (keep import minimal)
    summary: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "days_ahead": int(days_ahead),
        "ticker_count": len(records_by_ticker),
        "tickers": {},
    }
    for ticker, record in records_by_ticker.items():
        # ``record`` is alpha_engine.earnings_calendar_fetcher.EarningsRecord.
        try:
            payload = asdict(record)
        except TypeError:
            payload = dict(record) if isinstance(record, dict) else {}
        summary["tickers"][ticker] = {
            "next_earnings_date": payload.get("next_earnings_date"),
            "next_earnings_estimate": payload.get("next_earnings_estimate"),
            "source": payload.get("source"),
            "history_rows": len(payload.get("history") or []),
        }
    index_path = cache_dir / CALENDAR_INDEX_FILENAME
    index_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return index_path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools/earnings_calendar_fetcher.py",
        description=(
            "Bootstraps data/earnings/ for the PEAD strategy. Default OFF; "
            "set EARNINGS_FETCHER_ENABLED=1 to actually fetch."
        ),
    )
    p.add_argument(
        "--cache-dir",
        default=str(_REPO_ROOT / "data" / "earnings"),
        help="Directory to populate. Default: <repo>/data/earnings",
    )
    p.add_argument(
        "--tickers",
        help="Comma-separated list of tickers (overrides DEFAULT_TICKERS).",
    )
    p.add_argument(
        "--tickers-file",
        help="Path to newline-separated ticker file (one per line, '#' comments).",
    )
    p.add_argument(
        "--days-ahead",
        type=int,
        default=14,
        help="Days-ahead horizon recorded in the calendar index. Default: 14.",
    )
    p.add_argument(
        "--force-refresh",
        action="store_true",
        help="Bypass on-disk TTL and re-fetch from upstream.",
    )
    p.add_argument(
        "--bootstrap-only",
        action="store_true",
        help="Only ensure data/earnings/ exists; do NOT fetch even if enabled.",
    )
    p.add_argument(
        "--ttl-hours",
        type=int,
        default=24,
        help="Per-ticker cache TTL passed to EarningsCalendarFetcher. Default: 24.",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable INFO-level logging.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cache_dir = Path(args.cache_dir)
    _ensure_cache_dir(cache_dir)
    logger.info("Cache dir ready: %s", cache_dir)

    if args.bootstrap_only:
        logger.info("--bootstrap-only set; exiting after dir creation.")
        return 0

    if not _is_enabled():
        # Default-off path: keep the directory but do not network.
        logger.warning(
            "EARNINGS_FETCHER_ENABLED is not '1'; skipping fetch. Set it to '1' to enable."
        )
        # Still write a stub calendar index so downstream consumers don't crash.
        stub_index = cache_dir / CALENDAR_INDEX_FILENAME
        if not stub_index.exists():
            stub_index.write_text(
                json.dumps(
                    {
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "days_ahead": int(args.days_ahead),
                        "ticker_count": 0,
                        "tickers": {},
                        "note": "stub — EARNINGS_FETCHER_ENABLED was not '1' on last run",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        return 0

    # Lazy import so the gating path above doesn't depend on alpha_engine deps.
    from alpha_engine.earnings_calendar_fetcher import EarningsCalendarFetcher

    tickers = _parse_tickers(args)
    if not tickers:
        logger.warning("No tickers resolved; nothing to fetch.")
        return 0

    fetcher = EarningsCalendarFetcher(
        cache_dir=cache_dir,
        ttl_hours=args.ttl_hours,
    )
    logger.info("Fetching earnings for %d tickers (force_refresh=%s)...",
                len(tickers), args.force_refresh)
    records = fetcher.fetch_batch(tickers, force_refresh=args.force_refresh)

    index_path = _write_calendar_index(cache_dir, records, days_ahead=args.days_ahead)
    logger.info("Wrote calendar index: %s", index_path)

    # Final summary to stdout (machine-parseable on one line).
    completed = sum(1 for r in records.values() if getattr(r, "source", "missing") != "missing")
    print(json.dumps({
        "ok": True,
        "ticker_count": len(records),
        "completed": completed,
        "missing": len(records) - completed,
        "cache_dir": str(cache_dir),
        "calendar_index": str(index_path),
    }))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via tests
    raise SystemExit(main())
