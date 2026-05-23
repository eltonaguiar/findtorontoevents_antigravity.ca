"""Value-screener runner — wires UEPS into the production pick flow.

Called by `.github/workflows/value_screener_weekly.yml` (Mon 06:00 UTC).

Flow:
  1. Load universe (S&P 500 baseline; passed in or fetched).
  2. For each ticker: pull fundamentals (EDGAR primary + yfinance fallback).
  3. Pull current price (from existing repo's price providers — caller-injectable).
  4. Score via ValueScreener.screen_universe (Magic Formula × Piotroski × Acquirer's × SafetyGate).
  5. Append emitted long_term_value picks to alpha_engine/data/active_picks.json.
  6. Write a screening report to reports/value_screener_runs/{date}.md.

This is the FIRST production caller for the UEPS sidecar modules. It satisfies
the CLAUDE.md Wire-Up Rule for `value_screener.py`, `fundamentals_fetcher.py`,
`earnings_calendar_fetcher.py`, `dividend_history_fetcher.py`,
`long_term_pick_contract.py`, and `short_side_screener.py`.

Per `docs/PERFORMANCE_CHARTER.md` §10 sample-size discipline: emitted picks
carry the "Building (n=N/100)" tag in the dashboard until the strategy
accumulates 100 closed picks. The picks are PAPER ONLY at this stage — no
sized-up live capital until walk-forward backtest validates Tier 2 thresholds
per §2.

Universe source defaults to a small built-in S&P 100 list for the first run.
Phase 13 backfill will replace that with the EDGAR companyfacts.zip universe.
"""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from alpha_engine.dividend_history_fetcher import DividendHistoryFetcher
from alpha_engine.earnings_calendar_fetcher import EarningsCalendarFetcher
from alpha_engine.fundamentals_fetcher import FundamentalsFetcher
from alpha_engine.short_side_screener import ShortSideScreener
from alpha_engine.value_screener import ScreenerInput, ValueScreener

logger = logging.getLogger(__name__)

ACTIVE_PICKS_PATH = Path("alpha_engine/data/active_picks.json")
REPORTS_DIR = Path("reports/value_screener_runs")

# Default universe — S&P 100 baseline. Phase 13 expands to full EDGAR universe.
DEFAULT_UNIVERSE: list[str] = [
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "AMD",
    "NFLX", "DIS", "BA", "JPM", "GS", "V", "MA", "PYPL", "JNJ", "PFE",
    "ABBV", "AVGO", "HD", "LLY", "TMO", "ORCL", "KO", "PEP", "WMT", "COST",
    "CVX", "XOM", "MRK", "TXN", "QCOM", "ADBE", "CRM", "INTC", "CSCO", "IBM",
    "ACN", "BMY", "LIN", "DHR", "MDT", "UNH", "T", "VZ", "CMCSA", "MCD",
    "NKE", "ABT",
]


# Caller-injectable price provider (sandbox-safe — tests pass a stub).
PriceProvider = Callable[[str], float | None]


# ---------------------------------------------------------------------------
# Equity price + market-cap providers — defaults route through the failover
# chain so GHA runners that fail to install yfinance still emit picks. The
# legacy `fetch_*_via_yfinance` helpers are preserved (yfinance demoted to
# tier 5 inside the chain) so dev boxes that have it installed continue to
# work end-to-end. See `alpha_engine/equity_price_failover.py` for the chain
# definition + the AI-consultation research note at
# `updates/long_term_value_project_2026-04-27/research/22_equity_price_failover_research.md`.
# ---------------------------------------------------------------------------
try:
    from alpha_engine.equity_price_failover import (
        fetch_market_caps_default as _failover_market_caps_default,
        fetch_prices_default as _failover_prices_default,
    )
    _EQUITY_FAILOVER_AVAILABLE = True
except Exception as _e:  # pragma: no cover — import-time guardrail
    logger.warning("equity_price_failover unavailable, falling back to yfinance-only: %s", _e)
    _EQUITY_FAILOVER_AVAILABLE = False


def fetch_market_caps_via_yfinance(tickers: list[str]) -> dict[str, float | None]:
    """Failover-chain market-cap lookup. yfinance is the LAST resort.

    Name preserved for back-compat with `tools/run_ueps_pickers.py` and
    existing tests; the implementation now consults Finnhub → FMP →
    Polygon → SEC EDGAR (shares × price) → yfinance via
    `alpha_engine.equity_price_failover.fetch_market_caps_default`.
    """
    if _EQUITY_FAILOVER_AVAILABLE:
        return _failover_market_caps_default(tickers)
    # Fallback path retained verbatim from the original implementation so
    # environments with neither failover nor yfinance still degrade gracefully.
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance unavailable — market caps cannot be fetched")
        return dict.fromkeys(tickers, None)
    out: dict[str, float | None] = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info or {}
            out[t] = info.get("marketCap")
        except Exception as e:
            logger.warning("Market cap fetch failed for %s: %s", t, e)
            out[t] = None
    return out


def fetch_prices_via_yfinance(tickers: list[str]) -> dict[str, float | None]:
    """Failover-chain price lookup. yfinance is the LAST resort.

    Name preserved for back-compat. Routes through Stooq → Finnhub → Tiingo
    → Twelve Data → Alpha Vantage → FMP → yfinance.
    """
    if _EQUITY_FAILOVER_AVAILABLE:
        return _failover_prices_default(tickers)
    try:
        import yfinance as yf
    except ImportError:
        return dict.fromkeys(tickers, None)
    out: dict[str, float | None] = {}
    for t in tickers:
        try:
            ticker = yf.Ticker(t)
            hist = ticker.history(period="5d")
            if not hist.empty:
                out[t] = float(hist["Close"].iloc[-1])
            else:
                out[t] = None
        except Exception as e:
            logger.warning("Price fetch failed for %s: %s", t, e)
            out[t] = None
    return out


def load_active_picks(path: Path = ACTIVE_PICKS_PATH) -> tuple[list[dict], dict | None]:
    """Load existing active_picks.json. Returns (picks_list, full_obj_if_dict)."""
    if not path.exists():
        return ([], None)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load %s: %s", path, e)
        return ([], None)
    if isinstance(data, dict):
        return (data.get("picks", []), data)
    if isinstance(data, list):
        return (data, None)
    return ([], None)


def save_active_picks(picks: list[dict], full_obj: dict | None,
                      path: Path = ACTIVE_PICKS_PATH) -> None:
    """Persist updated picks list, preserving the wrapper dict if present."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if full_obj is not None:
        full_obj["picks"] = picks
        full_obj["last_updated"] = datetime.now(timezone.utc).isoformat()
        payload = full_obj
    else:
        payload = picks
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def remove_existing_long_term_value_picks(picks: list[dict],
                                          ticker_set: set[str]) -> list[dict]:
    """Remove prior `long_term_value` picks for tickers we're about to re-emit.

    This prevents duplicate stacking week-over-week. Other pick types are
    preserved untouched.
    """
    return [
        p for p in picks
        if not (p.get("pick_type") == "long_term_value"
                and p.get("symbol", "").upper() in ticker_set)
    ]


def build_screener_inputs(
    tickers: list[str],
    fundamentals_fetcher: FundamentalsFetcher,
    earnings_fetcher: EarningsCalendarFetcher | None,
    dividends_fetcher: DividendHistoryFetcher | None,
    price_provider: PriceProvider,
    market_caps: dict[str, float | None],
) -> list[ScreenerInput]:
    """Build per-ticker input objects for the value screener.

    Mirror-pair dedup: tickers sharing the same EDGAR CIK (e.g., GOOG + GOOGL)
    represent the same underlying company.  Only the first ticker seen for a
    given CIK is retained — secondary share classes are silently skipped so the
    portfolio doesn't double-count a single company's fundamentals.
    """
    inputs: list[ScreenerInput] = []
    seen_ciks: set[str] = set()
    for t in tickers:
        record = fundamentals_fetcher.fetch(t)
        if not record.is_complete():
            logger.info("Skipping %s — incomplete fundamentals", t)
            continue

        # Dedup by EDGAR CIK — skip secondary share classes of already-seen companies.
        if record.cik:
            if record.cik in seen_ciks:
                logger.info("Skipping %s — CIK %s already in universe (mirror share class)", t, record.cik)
                continue
            seen_ciks.add(record.cik)

        price = price_provider(t)
        if price is None or price <= 0:
            logger.info("Skipping %s — no current price", t)
            continue

        mc = market_caps.get(t)
        if mc is None or mc < 300_000_000:
            logger.info("Skipping %s — market_cap below $300M floor (mc=%s)", t, mc)
            continue

        earnings = earnings_fetcher.fetch(t) if earnings_fetcher else None
        dividends = dividends_fetcher.fetch(t) if dividends_fetcher else None

        inp = ScreenerInput(
            ticker=t,
            current_price=price,
            market_cap=mc,
            fundamentals=record,
            earnings=earnings,
            dividends=dividends,
        )
        inputs.append(inp)
    return inputs


def write_run_report(
    inputs: list[ScreenerInput],
    long_picks: list[dict],
    short_picks: list[dict],
    report_dir: Path = REPORTS_DIR,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = report_dir / f"{run_date}.md"

    lines: list[str] = [
        f"# Value Screener Run — {run_date}",
        "",
        f"- Universe size scored: **n={len(inputs)}**",
        f"- LONG picks emitted: **n={len(long_picks)}**",
        f"- SHORT picks emitted: **n={len(short_picks)}**",
        "",
        "## LONG candidates",
        "",
    ]
    if long_picks:
        lines.append("| Ticker | Score | F-Score | Magic Rank | Acquirer's M | Altman Z'' | Beneish M | IV target |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for p in long_picks[:30]:
            snap = p.get("fundamental_snapshot", {})
            lines.append(
                f"| {p.get('symbol', '?')} | {p.get('score', '?')} | "
                f"{snap.get('piotroski_f', '?')} | {snap.get('magic_formula_rank', '?')} | "
                f"{snap.get('acquirers_multiple', '?')} | {snap.get('altman_z_double_prime', '?')} | "
                f"{snap.get('beneish_m', '?')} | {p.get('intrinsic_value', '?')} |"
            )
    else:
        lines.append("_No LONG candidates passed the SafetyGate this run._")

    lines.extend(["", "## SHORT candidates", ""])
    if short_picks:
        lines.append("| Ticker | Triggers | Beneish M | Altman Z'' | Sloan |")
        lines.append("|---|---|---|---|---|")
        for p in short_picks[:30]:
            snap = p.get("fundamental_snapshot", {})
            extra = p.get("extra", {})
            lines.append(
                f"| {p.get('symbol', '?')} | {extra.get('total_triggers', '?')} | "
                f"{snap.get('beneish_m', '?')} | {snap.get('altman_z_double_prime', '?')} | "
                f"{snap.get('sloan_accruals_decile', '?')} |"
            )
    else:
        lines.append("_No SHORT candidates met the ≥2-of-3 trigger this run._")

    lines.extend([
        "",
        "## Methodology",
        "",
        f"- LONG composite (per `findings/SYNTHESIS.md` §3): `0.55 × ValueComposite + 0.45 × QualityComposite × SafetyGate`",
        f"- SHORT trigger (per `findings/SYNTHESIS.md` §3): Beneish M ≥ -1.78 OR Altman Z'' < 1.10 OR Sloan top decile, ≥2-of-3",
        f"- Sample-size discipline (per `docs/PERFORMANCE_CHARTER.md` §10): n=value reported on every aggregate stat",
        f"- Tier classification deferred until n≥100 closed picks per strategy",
        "",
        f"_Run timestamp: {datetime.now(timezone.utc).isoformat()}_",
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote run report: %s", report_path)
    return report_path


def run(
    universe: list[str] | None = None,
    *,
    top_n_long: int = 30,
    top_n_short: int = 20,
    fundamentals_fetcher: FundamentalsFetcher | None = None,
    earnings_fetcher: EarningsCalendarFetcher | None = None,
    dividends_fetcher: DividendHistoryFetcher | None = None,
    price_provider: PriceProvider | None = None,
    market_cap_provider: Callable[[list[str]], dict[str, float | None]] | None = None,
    active_picks_path: Path = ACTIVE_PICKS_PATH,
    dry_run: bool = False,
) -> dict[str, int]:
    """Execute one weekly value-screening pass.

    Returns dict with `n_universe`, `n_long_emitted`, `n_short_emitted`.
    """
    universe = universe or DEFAULT_UNIVERSE
    fundamentals_fetcher = fundamentals_fetcher or FundamentalsFetcher()
    earnings_fetcher = earnings_fetcher or EarningsCalendarFetcher()
    dividends_fetcher = dividends_fetcher or DividendHistoryFetcher()
    price_provider = price_provider or (
        lambda ticker: fetch_prices_via_yfinance([ticker]).get(ticker)
    )
    market_cap_provider = market_cap_provider or fetch_market_caps_via_yfinance

    logger.info("Fetching market caps for %d tickers…", len(universe))
    market_caps = market_cap_provider(universe)

    logger.info("Building screener inputs…")
    inputs = build_screener_inputs(
        universe, fundamentals_fetcher, earnings_fetcher, dividends_fetcher,
        price_provider, market_caps,
    )
    logger.info("Built %d screener inputs (filtered from %d universe).", len(inputs), len(universe))

    # Fetch prior-year fundamentals so Piotroski tests 5-9 and Beneish M use
    # real XBRL data instead of the placeholder −2.5.
    logger.info("Fetching prior-year fundamentals for Beneish M + full Piotroski…")
    input_tickers = [inp.ticker for inp in inputs]
    prior_map = fundamentals_fetcher.fetch_batch_prior(input_tickers)
    logger.info("Got prior-year records for %d/%d tickers.", len(prior_map), len(input_tickers))

    long_screener = ValueScreener(
        fundamentals_fetcher=fundamentals_fetcher,
        earnings_fetcher=earnings_fetcher,
        dividends_fetcher=dividends_fetcher,
    )
    long_picks = long_screener.screen_universe(inputs, top_n=top_n_long,
                                               prior_fundamentals_map=prior_map)

    # SHORT side from same fundamentals
    short_screener = ShortSideScreener(fundamentals_fetcher=fundamentals_fetcher)
    short_records = [(inp.ticker, inp.fundamentals, None) for inp in inputs]
    short_picks = short_screener.screen_universe(short_records, top_n=top_n_short)

    if dry_run:
        logger.info("Dry run — not writing to %s", active_picks_path)
    else:
        existing_picks, full_obj = load_active_picks(active_picks_path)
        ticker_set = {p["symbol"].upper() for p in long_picks + short_picks if p.get("symbol")}
        cleaned = remove_existing_long_term_value_picks(existing_picks, ticker_set)
        new_picks = cleaned + long_picks + short_picks
        save_active_picks(new_picks, full_obj, active_picks_path)
        logger.info("Wrote %d picks to %s", len(new_picks), active_picks_path)

    write_run_report(inputs, long_picks, short_picks)

    return {
        "n_universe": len(universe),
        "n_filtered_universe": len(inputs),
        "n_long_emitted": len(long_picks),
        "n_short_emitted": len(short_picks),
    }


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    summary = run()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
