"""UEPS pick runner — emits a fresh batch of US Equity Picks for the dashboard.

Production caller for the UEPS sidecar modules (Phases 5-9). Wires:
  * alpha_engine.value_screener.ValueScreener
  * alpha_engine.short_side_screener.ShortSideScreener
  * alpha_engine.value_screener_runner (build_screener_inputs / providers)

This satisfies CLAUDE.md Wire-Up Rule for the dashboard surface — the JSON it
writes is fetched client-side by audit_dashboard/template.html into the
``#ueps-section-mount`` div (added in commit 8a9e7e8a2b).

OUTPUTS:
  1. ``audit_dashboard/data/ueps_picks.json`` — dashboard-scoped artifact
     fetched client-side by ``audit_dashboard/template.html``. Schema:

        {
          "generated_at":   <iso8601 utc>,
          "universe_size":  <int>,
          "long_picks":     [<long_term_value pick dict>, ...],
          "swing_picks":    [<swing pick dict>, ...],
          "short_picks":    [<short pick dict>, ...],
          "summary":        {"n_long": int, "n_short": int, "n_swing": int},
        }

  2. ``alpha_engine/data/active_picks.json`` — shared execution ledger.
     Insert-only sync via ``sync_to_active_picks`` so the 4h cadence does
     not churn ``entry_price``/``created_at`` on existing entries. The
     weekly ``alpha_engine.value_screener_runner`` remains authoritative
     for full refreshes (it replaces matching tickers per its own logic).
     Without this sync, UEPS picks emit into a void — the dashboard JSON
     shows them, but the forward tracker never sees them, and no
     closed-trade stats accumulate.

This script is invoked by ``.github/workflows/ueps-pick-runner.yml`` every 4h
during US market hours.

Per CLAUDE.md "Never run dashboard generators locally": this script does NOT
overwrite any HTML — it only writes a JSON artifact that the dashboard
fetches client-side.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Inline-comment wiring intent: import the existing UEPS modules + the
# value_screener_runner orchestrator so we re-use its provider abstractions.
from alpha_engine.dividend_history_fetcher import DividendHistoryFetcher
from alpha_engine.earnings_calendar_fetcher import EarningsCalendarFetcher
from alpha_engine.fundamentals_fetcher import FundamentalsFetcher
from alpha_engine.short_side_screener import ShortSideScreener
from alpha_engine.value_screener import ValueScreener
from alpha_engine.value_screener_runner import (
    DEFAULT_UNIVERSE,
    build_screener_inputs,
    fetch_market_caps_via_yfinance,
    fetch_prices_via_yfinance,
)
from alpha_engine import adversarial_debate as _adv

logger = logging.getLogger(__name__)

UEPS_PICKS_PATH = Path("audit_dashboard/data/ueps_picks.json")
ACTIVE_PICKS_PATH = Path("alpha_engine/data/active_picks.json")


def _price_provider_factory():
    """Return a per-ticker price provider that lazy-loads yfinance once."""
    cache: dict[str, float | None] = {}

    def provider(ticker: str) -> float | None:
        if ticker in cache:
            return cache[ticker]
        prices = fetch_prices_via_yfinance([ticker])
        cache[ticker] = prices.get(ticker)
        return cache[ticker]

    return provider


def run_screeners(
    universe: list[str],
    *,
    top_n_long: int = 30,
    top_n_short: int = 20,
) -> dict[str, Any]:
    """Run value + short-side screeners over `universe`, return picks payload."""
    fundamentals = FundamentalsFetcher()
    earnings = EarningsCalendarFetcher()
    dividends = DividendHistoryFetcher()
    price_provider = _price_provider_factory()

    logger.info("Fetching market caps for %d tickers…", len(universe))
    market_caps = fetch_market_caps_via_yfinance(universe)

    logger.info("Building screener inputs…")
    inputs = build_screener_inputs(
        universe, fundamentals, earnings, dividends,
        price_provider, market_caps,
    )
    logger.info("Built %d screener inputs (filtered from %d universe).",
                len(inputs), len(universe))

    # Prior-year fundamentals — needed for Piotroski tests 5-9 and Beneish M.
    logger.info("Fetching prior-year fundamentals for Beneish M + full Piotroski…")
    input_tickers = [inp.ticker for inp in inputs]
    prior_map = fundamentals.fetch_batch_prior(input_tickers)
    logger.info("Got prior-year records for %d/%d tickers.", len(prior_map), len(input_tickers))

    long_screener = ValueScreener(
        fundamentals_fetcher=fundamentals,
        earnings_fetcher=earnings,
        dividends_fetcher=dividends,
    )
    long_picks = long_screener.screen_universe(inputs, top_n=top_n_long,
                                               prior_fundamentals_map=prior_map)

    # Shadow adversarial debate (B9) — stamps adversarial_score / adversarial_keep
    # fields on each long pick. Hard no-op when UEPS_ADVERSARIAL_ENABLED is unset.
    # Gated at the module level; never filters picks, only annotates.
    long_picks = _adv.apply_to_picks(long_picks)
    if _adv.is_enabled():
        keep_count = sum(1 for p in long_picks if p.get("adversarial_keep"))
        logger.info(
            "[adversarial] shadow: %d/%d long picks pass debate (margin≥%.2f)",
            keep_count, len(long_picks), _adv.KEEP_MARGIN,
        )

    short_screener = ShortSideScreener(fundamentals_fetcher=fundamentals)
    short_records = [(inp.ticker, inp.fundamentals, None) for inp in inputs]
    short_picks = short_screener.screen_universe(short_records, top_n=top_n_short)

    # Swing picks deferred — swing_screener requires OHLCV windows that the
    # production scanner already maintains. Plumbing that in is a follow-up
    # PR; for now we emit an empty swing list so the dashboard tab renders
    # the empty-state placeholder rather than crashing.
    swing_picks: list[dict[str, Any]] = []

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "universe_size": len(universe),
        "filtered_universe_size": len(inputs),
        "long_picks": long_picks,
        "swing_picks": swing_picks,
        "short_picks": short_picks,
        "summary": {
            "n_long": len(long_picks),
            "n_short": len(short_picks),
            "n_swing": len(swing_picks),
        },
    }


def write_payload(payload: dict[str, Any], path: Path = UEPS_PICKS_PATH) -> None:
    """Persist the payload as JSON at the dashboard-fetched path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )
    logger.info("Wrote %s (long=%d short=%d swing=%d)", path,
                payload["summary"]["n_long"],
                payload["summary"]["n_short"],
                payload["summary"]["n_swing"])


def sync_to_active_picks(
    payload: dict[str, Any],
    active_picks_path: Path = ACTIVE_PICKS_PATH,
) -> int:
    """Promote UEPS picks from `payload` into the shared active_picks.json ledger.

    Insert-only: existing entries matching ``(symbol, source_system)`` are left
    untouched, so ``entry_price`` and ``created_at`` aren't churned every 4h.
    The weekly ``alpha_engine.value_screener_runner`` remains the authoritative
    full-refresh path.

    Without this, ``ueps_picks.json`` is a dashboard-only feed and the picks
    never accumulate forward stats — the gap flagged in
    ``updates/2026-04-29-ueps-emit-verification.md`` §5.

    Returns the count of newly-inserted picks.
    """
    # Imported lazily so unit tests that exercise sync logic in isolation don't
    # drag in EDGAR/yfinance side effects.
    from alpha_engine.value_screener_runner import (
        load_active_picks,
        save_active_picks,
    )

    existing, full_obj = load_active_picks(active_picks_path)
    seen = {
        (str(p.get("symbol", "")).upper(), str(p.get("source_system", "")))
        for p in existing
    }

    generated_at = payload.get("generated_at")
    inserted = 0
    for bucket in ("long_picks", "short_picks", "swing_picks"):
        for pick in payload.get(bucket, []) or []:
            sym = str(pick.get("symbol", "")).upper()
            src = str(pick.get("source_system", ""))
            if not sym or (sym, src) in seen:
                continue
            enriched = dict(pick)
            enriched.setdefault("created_at", generated_at)
            enriched.setdefault("id", f"ueps_{src}_{pick.get('symbol', '')}")
            existing.append(enriched)
            seen.add((sym, src))
            inserted += 1

    save_active_picks(existing, full_obj, active_picks_path)
    logger.info(
        "Synced %d new UEPS picks into %s (ledger now has %d total entries)",
        inserted, active_picks_path, len(existing),
    )
    return inserted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", nargs="*", default=None,
                        help="Override universe (default: S&P 100 baseline)")
    parser.add_argument("--top-long", type=int, default=30)
    parser.add_argument("--top-short", type=int, default=20)
    parser.add_argument("--output", type=Path, default=UEPS_PICKS_PATH)
    parser.add_argument("--active-picks-output", type=Path, default=ACTIVE_PICKS_PATH,
                        help="Path to active_picks.json ledger (synced after write)")
    parser.add_argument("--skip-active-sync", action="store_true",
                        help="Write ueps_picks.json but skip the active_picks.json sync")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run screeners but do not write the JSON")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    universe = args.universe or list(DEFAULT_UNIVERSE)
    payload = run_screeners(
        universe, top_n_long=args.top_long, top_n_short=args.top_short
    )

    if args.dry_run:
        logger.info("Dry run — not writing payload to %s", args.output)
    else:
        write_payload(payload, args.output)
        if args.skip_active_sync:
            logger.info("Skipping active_picks sync (--skip-active-sync)")
        else:
            sync_to_active_picks(payload, active_picks_path=args.active_picks_output)

    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
