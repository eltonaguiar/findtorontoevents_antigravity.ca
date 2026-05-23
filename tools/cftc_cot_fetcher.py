#!/usr/bin/env python3
"""CLI bootstrapper for the CFTC Commitments of Traders (COT) cache.

Per CLAUDE.md Wire-Up Rule: this script is OPT-IN sidecar tooling. It
populates ``data/cftc_cot/<contract>_latest.json`` with the latest weekly
COT report and a ``commercial_net_extreme`` z-score signal so a future
gate-wiring PR can look up the signal at scan time without re-fetching.

It does NOT alter any production code path today; no callers exist in
``alpha_engine/``, ``audit_trail/``, or ``tools/`` against this module.

Background — Phase 2-F FUTURES panel (6/6 unanimous, 2026-04-29):
  - FUTURES n=2 all-time -> INSUFFICIENT (empty-awaiting-routing class)
  - 6/6 panel: whitelist ZN=F, ES=F, NQ=F (already in FUTURES_SYMBOLS)
  - 6/6 panel: wire CFTC COT ``commercial_net_extreme`` (free, weekly)

The CFTC publishes the legacy COT report every Friday at ~3:30pm ET. The
"commercial_net_extreme" signal:
    commercial_net = commercial_long - commercial_short
    z = (commercial_net - 52w_mean) / 52w_std
    extreme if abs(z) >= 2

Activation gate (default OFF):
  CFTC_COT_FETCHER_ENABLED=1   - required to perform any network work.

Without that env var set, the script just ensures ``data/cftc_cot/``
exists and writes a stub ``calendar.json`` listing the contracts that
would be fetched, then exits 0. This is so a workflow step can call it
unconditionally before the live wire-up PR without changing production
behaviour.

Examples
--------
  # Bootstrap directory only (no fetch). Safe in CI before flag flip.
  python tools/cftc_cot_fetcher.py --bootstrap-only

  # Once gated on, fetch the default contract universe.
  CFTC_COT_FETCHER_ENABLED=1 python tools/cftc_cot_fetcher.py

  # Custom contracts.
  CFTC_COT_FETCHER_ENABLED=1 python tools/cftc_cot_fetcher.py \
      --contracts ZN=F,ES=F,NQ=F
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError

# Ensure repo root is on sys.path so this can run as `python tools/...` from anywhere.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

logger = logging.getLogger("cftc_cot_fetcher_cli")

# CFTC's public Socrata API exposes the legacy COT report as JSON. The
# ``futures_only_report`` dataset is updated every Friday afternoon and
# requires no API key for moderate request volumes.
#
# Reference: https://publicreporting.cftc.gov/resource/6dca-aqww.json
# Docs:      https://www.cftc.gov/dea/futures/dea_cot_reports.htm
CFTC_LEGACY_FUTURES_ONLY_URL = (
    "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
    "?$where=market_and_exchange_names%20like%20'{name_like}%25'"
    "&$order=report_date_as_yyyy_mm_dd%20DESC"
    "&$limit={limit}"
)

# Default ZN/ES/NQ + a small basket of liquid CFTC-reported contracts.
# Map yfinance ticker -> CFTC market_and_exchange_names prefix.
DEFAULT_CONTRACTS: dict[str, str] = {
    "ZN=F": "10-YEAR U.S. TREASURY NOTES",
    "ZB=F": "U.S. TREASURY BONDS",
    "ZT=F": "2-YEAR U.S. TREASURY NOTES",
    "ES=F": "E-MINI S&P 500",
    "NQ=F": "NASDAQ-100",
    "YM=F": "DJIA",
    "GC=F": "GOLD",
    "SI=F": "SILVER",
    "HG=F": "COPPER",
}

# Number of weekly rows to pull for the rolling z-score window. 60 gives a
# little headroom around the 52-week target so we tolerate sparse weeks.
ROLLING_WINDOW_WEEKS = 52
DEFAULT_FETCH_LIMIT = 60

CALENDAR_INDEX_FILENAME = "calendar.json"
EXTREME_Z_THRESHOLD = 2.0


def _is_enabled() -> bool:
    """Honor the CFTC_COT_FETCHER_ENABLED env var. Default OFF."""
    return os.environ.get("CFTC_COT_FETCHER_ENABLED", "0").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _ensure_cache_dir(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    keep = cache_dir / ".gitkeep"
    if not keep.exists():
        keep.write_text("", encoding="utf-8")


def _stdlib_http_get(url: str, user_agent: str = "cftc_cot_fetcher/1.0") -> str:
    """Plain stdlib HTTP GET. Injectable in tests via the ``http_get`` arg."""
    from urllib.request import Request, urlopen
    req = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _coerce_int(val: Any) -> int | None:
    """CFTC Socrata returns positions as strings; coerce safely."""
    if val is None:
        return None
    try:
        return int(float(str(val).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None


def compute_commercial_net_extreme(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute commercial_net + 52-week z-score signal from raw CFTC rows.

    Rows must be sorted DESCENDING by report date (most recent first).
    Returns a dict with the latest row's signal + window stats; safe on
    short series (returns ``z=None``, ``extreme=False`` when n<10).
    """
    nets: list[int] = []
    dates: list[str] = []
    for row in rows[:ROLLING_WINDOW_WEEKS]:
        long_v = _coerce_int(row.get("comm_positions_long_all"))
        short_v = _coerce_int(row.get("comm_positions_short_all"))
        if long_v is None or short_v is None:
            continue
        nets.append(long_v - short_v)
        dates.append(str(row.get("report_date_as_yyyy_mm_dd") or ""))

    if not nets:
        return {
            "commercial_net": None,
            "commercial_net_z": None,
            "commercial_net_extreme": False,
            "window_n": 0,
            "report_date": None,
        }

    latest_net = nets[0]
    latest_date = dates[0] if dates else None

    if len(nets) < 10:
        # Not enough history for a meaningful z-score yet.
        return {
            "commercial_net": latest_net,
            "commercial_net_z": None,
            "commercial_net_extreme": False,
            "window_n": len(nets),
            "report_date": latest_date,
        }

    mean = statistics.fmean(nets)
    # statistics.pstdev is population stdev; safer than sample on a fixed window.
    std = statistics.pstdev(nets)
    if std <= 0:
        z: float | None = None
    else:
        z = (latest_net - mean) / std

    extreme = bool(z is not None and abs(z) >= EXTREME_Z_THRESHOLD)
    return {
        "commercial_net": latest_net,
        "commercial_net_z": z,
        "commercial_net_extreme": extreme,
        "window_n": len(nets),
        "report_date": latest_date,
        "window_mean": mean,
        "window_std": std,
    }


def fetch_contract(
    yf_ticker: str,
    market_name_prefix: str,
    *,
    http_get: Callable[[str], str] | None = None,
    limit: int = DEFAULT_FETCH_LIMIT,
) -> dict[str, Any]:
    """Fetch a single contract's COT history + compute commercial_net_extreme.

    Returns a dict suitable for writing to ``data/cftc_cot/<contract>_latest.json``.
    Network failures surface as ``source='missing'`` with an ``error`` field
    rather than raising — callers can decide whether to retry.
    """
    http_get = http_get or _stdlib_http_get
    # CFTC market_and_exchange_names columns include the exchange suffix; we
    # filter via SQL ``LIKE`` so the prefix alone is enough.
    name_like = market_name_prefix.replace(" ", "%20")
    url = CFTC_LEGACY_FUTURES_ONLY_URL.format(name_like=name_like, limit=int(limit))

    record: dict[str, Any] = {
        "yf_ticker": yf_ticker,
        "market_name_prefix": market_name_prefix,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "missing",
        "rows": [],
        "signal": {
            "commercial_net": None,
            "commercial_net_z": None,
            "commercial_net_extreme": False,
            "window_n": 0,
            "report_date": None,
        },
    }
    try:
        body = http_get(url)
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record
    except Exception as exc:  # noqa: BLE001 - catch-all so the CLI never crashes here
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record

    try:
        rows = json.loads(body)
    except (TypeError, ValueError) as exc:
        record["error"] = f"json decode failed: {exc}"
        return record

    if not isinstance(rows, list):
        record["error"] = "CFTC response was not a list"
        return record

    record["source"] = "cftc_socrata_legacy_futures_only"
    record["rows"] = rows
    record["signal"] = compute_commercial_net_extreme(rows)
    return record


def _parse_contracts(raw: str | None) -> dict[str, str]:
    """Resolve a comma-separated --contracts list against DEFAULT_CONTRACTS."""
    if not raw:
        return dict(DEFAULT_CONTRACTS)
    out: dict[str, str] = {}
    for tok in raw.split(","):
        tok = tok.strip().upper()
        if not tok:
            continue
        if tok not in DEFAULT_CONTRACTS:
            raise SystemExit(
                f"--contracts: '{tok}' has no CFTC market-name mapping; "
                f"add it to DEFAULT_CONTRACTS in tools/cftc_cot_fetcher.py first."
            )
        out[tok] = DEFAULT_CONTRACTS[tok]
    return out


def _contract_filename(yf_ticker: str) -> str:
    """ZN=F -> 'ZN_latest.json' (filesystem-safe, contract-stable)."""
    safe = yf_ticker.replace("=F", "").replace("=", "_").replace("/", "_")
    return f"{safe}_latest.json"


def _write_calendar_index(
    cache_dir: Path,
    records: dict[str, dict[str, Any]],
    *,
    note: str | None = None,
) -> Path:
    """Write a top-level ``calendar.json`` index summarising this run."""
    summary: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tickers": list(records.keys()),
        "ticker_count": len(records),
        "extreme_count": sum(
            1 for r in records.values()
            if (r.get("signal") or {}).get("commercial_net_extreme")
        ),
    }
    if note:
        summary["note"] = note
    index_path = cache_dir / CALENDAR_INDEX_FILENAME
    index_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return index_path


def _write_stub_calendar(cache_dir: Path, contracts: Iterable[str]) -> Path:
    """Disabled-path: write a calendar with empty tickers list (no fetch)."""
    summary: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tickers": [],
        "ticker_count": 0,
        "extreme_count": 0,
        "candidate_contracts": list(contracts),
        "note": "stub - CFTC_COT_FETCHER_ENABLED was not '1' on last run",
    }
    index_path = cache_dir / CALENDAR_INDEX_FILENAME
    index_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return index_path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools/cftc_cot_fetcher.py",
        description=(
            "Bootstraps data/cftc_cot/ with weekly CFTC COT reports + "
            "commercial_net_extreme z-score signal. Default OFF; set "
            "CFTC_COT_FETCHER_ENABLED=1 to actually fetch."
        ),
    )
    p.add_argument(
        "--cache-dir",
        default=str(_REPO_ROOT / "data" / "cftc_cot"),
        help="Directory to populate. Default: <repo>/data/cftc_cot",
    )
    p.add_argument(
        "--contracts",
        help="Comma-separated yfinance tickers (e.g. ZN=F,ES=F,NQ=F). "
             "Each must have a CFTC market-name mapping.",
    )
    p.add_argument(
        "--bootstrap-only",
        action="store_true",
        help="Only ensure data/cftc_cot/ exists; do NOT fetch even if enabled.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_FETCH_LIMIT,
        help=f"Rows per contract from CFTC (>=ROLLING_WINDOW_WEEKS=52). "
             f"Default: {DEFAULT_FETCH_LIMIT}.",
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

    contracts = _parse_contracts(args.contracts)

    if args.bootstrap_only:
        logger.info("--bootstrap-only set; exiting after dir creation.")
        # Bootstrap-only intentionally does NOT write a calendar.json so
        # ops can distinguish "dir created, never run" from "dir created,
        # disabled run with stub". Mirrors PR #499 PEAD bootstrap pattern.
        return 0

    if not _is_enabled():
        logger.warning(
            "CFTC_COT_FETCHER_ENABLED is not '1'; skipping fetch. "
            "Set it to '1' to enable."
        )
        stub_index = cache_dir / CALENDAR_INDEX_FILENAME
        if not stub_index.exists():
            _write_stub_calendar(cache_dir, contracts.keys())
        return 0

    records: dict[str, dict[str, Any]] = {}
    for yf_ticker, market_name in contracts.items():
        logger.info("Fetching CFTC COT for %s (%s)...", yf_ticker, market_name)
        record = fetch_contract(yf_ticker, market_name, limit=args.limit)
        records[yf_ticker] = record
        out_path = cache_dir / _contract_filename(yf_ticker)
        out_path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")

    index_path = _write_calendar_index(cache_dir, records)
    logger.info("Wrote calendar index: %s", index_path)

    completed = sum(1 for r in records.values() if r.get("source") != "missing")
    print(json.dumps({
        "ok": True,
        "ticker_count": len(records),
        "completed": completed,
        "missing": len(records) - completed,
        "extreme_count": sum(
            1 for r in records.values()
            if (r.get("signal") or {}).get("commercial_net_extreme")
        ),
        "cache_dir": str(cache_dir),
        "calendar_index": str(index_path),
    }))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via tests
    raise SystemExit(main())
