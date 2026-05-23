"""Tests for the tools/earnings_calendar_fetcher.py CLI bootstrapper.

These tests cover the CLI surface only; the underlying library is exercised
in tests/test_earnings_calendar_fetcher.py.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import the CLI module by file path so we don't require an installed package.
import importlib.util

_CLI_PATH = REPO_ROOT / "tools" / "earnings_calendar_fetcher.py"
_spec = importlib.util.spec_from_file_location("tools_earnings_cli", _CLI_PATH)
assert _spec and _spec.loader, "could not load tools/earnings_calendar_fetcher.py spec"
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)  # type: ignore[union-attr]


@dataclass
class _FakeRecord:
    ticker: str
    next_earnings_date: str | None = None
    next_earnings_estimate: float | None = None
    history: list = field(default_factory=list)
    fetched_at: str = ""
    source: str = "missing"
    cache_hit: bool = False


# ----- 1. Default OFF behaviour -----

def test_env_var_defaults_to_off(monkeypatch):
    """EARNINGS_FETCHER_ENABLED unset must mean disabled."""
    monkeypatch.delenv("EARNINGS_FETCHER_ENABLED", raising=False)
    assert cli._is_enabled() is False


@pytest.mark.parametrize("val", ["0", "false", "no", "off", "", "  "])
def test_env_var_off_values(monkeypatch, val):
    monkeypatch.setenv("EARNINGS_FETCHER_ENABLED", val)
    assert cli._is_enabled() is False


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "Yes", "on", " 1 "])
def test_env_var_on_values(monkeypatch, val):
    monkeypatch.setenv("EARNINGS_FETCHER_ENABLED", val)
    assert cli._is_enabled() is True


# ----- 2. Bootstrap-only path creates the directory + .gitkeep -----

def test_bootstrap_only_creates_directory(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("EARNINGS_FETCHER_ENABLED", raising=False)
    target = tmp_path / "earnings"

    rc = cli.main([
        "--cache-dir", str(target),
        "--bootstrap-only",
    ])

    assert rc == 0
    assert target.exists()
    assert (target / ".gitkeep").exists()
    # Bootstrap-only must NOT write a calendar.json (that's the disabled-stub path).
    assert not (target / cli.CALENDAR_INDEX_FILENAME).exists()


# ----- 3. Disabled path writes stub calendar index but does not network -----

def test_disabled_path_writes_stub_index_no_network(tmp_path, monkeypatch):
    monkeypatch.delenv("EARNINGS_FETCHER_ENABLED", raising=False)
    target = tmp_path / "earnings"

    # Sentinel: if the lazy import or any HTTP call happens, fail loudly.
    def _explode(*_a, **_kw):  # pragma: no cover - guard
        raise AssertionError("network/library was invoked when fetcher is disabled")

    monkeypatch.setattr(
        "alpha_engine.earnings_calendar_fetcher.EarningsCalendarFetcher",
        _explode,
    )

    rc = cli.main(["--cache-dir", str(target)])

    assert rc == 0
    index = target / cli.CALENDAR_INDEX_FILENAME
    assert index.exists(), "disabled run must still drop a stub calendar.json"
    payload = json.loads(index.read_text(encoding="utf-8"))
    assert payload["ticker_count"] == 0
    assert payload["tickers"] == {}
    assert "note" in payload  # stub note is the tell that this was a no-op run.


# ----- 4. Schema of the calendar index when enabled -----

def test_calendar_json_schema_when_enabled(tmp_path, monkeypatch):
    """When enabled, the writer produces a structurally valid calendar.json."""
    monkeypatch.setenv("EARNINGS_FETCHER_ENABLED", "1")
    target = tmp_path / "earnings"
    target.mkdir(parents=True, exist_ok=True)

    fake_records = {
        "AAPL": _FakeRecord(
            ticker="AAPL",
            next_earnings_date="2026-05-01",
            next_earnings_estimate=2.10,
            history=[
                {"date": "2026-01-30", "eps_actual": 2.18, "eps_estimate": 2.10, "surprise_pct": 3.81},
            ],
            fetched_at="2026-04-29T00:00:00+00:00",
            source="finnhub",
        ),
        "MSFT": _FakeRecord(
            ticker="MSFT",
            next_earnings_date=None,
            history=[],
            source="missing",
        ),
    }

    index_path = cli._write_calendar_index(target, fake_records, days_ahead=14)
    payload = json.loads(index_path.read_text(encoding="utf-8"))

    # Top-level shape
    for key in ("generated_at", "days_ahead", "ticker_count", "tickers"):
        assert key in payload
    assert payload["days_ahead"] == 14
    assert payload["ticker_count"] == 2

    # Per-ticker shape
    assert set(payload["tickers"].keys()) == {"AAPL", "MSFT"}
    aapl = payload["tickers"]["AAPL"]
    assert aapl["source"] == "finnhub"
    assert aapl["next_earnings_date"] == "2026-05-01"
    assert aapl["history_rows"] == 1
    msft = payload["tickers"]["MSFT"]
    assert msft["source"] == "missing"
    assert msft["history_rows"] == 0


# ----- 5. Enabled path uses the library, never opens raw sockets here -----

def test_enabled_path_routes_through_library(tmp_path, monkeypatch):
    """End-to-end happy path: env=1, library fetcher patched, exits 0 + writes index."""
    monkeypatch.setenv("EARNINGS_FETCHER_ENABLED", "1")
    target = tmp_path / "earnings"

    class _FakeFetcher:
        def __init__(self, *a, **kw):
            self.kw = kw

        def fetch_batch(self, tickers, *, force_refresh=False):
            return {
                t.upper(): _FakeRecord(
                    ticker=t.upper(),
                    next_earnings_date="2026-05-15",
                    history=[{"date": "2026-02-01", "eps_actual": 1.0, "eps_estimate": 0.95, "surprise_pct": 5.26}],
                    source="finnhub",
                )
                for t in tickers
            }

    monkeypatch.setattr(
        "alpha_engine.earnings_calendar_fetcher.EarningsCalendarFetcher",
        _FakeFetcher,
    )

    rc = cli.main([
        "--cache-dir", str(target),
        "--tickers", "AAPL,MSFT",
        "--days-ahead", "7",
    ])
    assert rc == 0
    index = target / cli.CALENDAR_INDEX_FILENAME
    assert index.exists()
    payload = json.loads(index.read_text(encoding="utf-8"))
    assert payload["ticker_count"] == 2
    assert payload["days_ahead"] == 7
    assert payload["tickers"]["AAPL"]["source"] == "finnhub"


# ----- 6. Tickers file parsing (comments + blanks) -----

def test_parse_tickers_file(tmp_path):
    f = tmp_path / "tickers.txt"
    f.write_text(
        "# header comment\nAAPL\n\nmsft\n  nvda  \n# trailing comment\n",
        encoding="utf-8",
    )
    parser = cli.build_arg_parser()
    args = parser.parse_args(["--tickers-file", str(f)])
    out = cli._parse_tickers(args)
    assert out == ["AAPL", "MSFT", "NVDA"]


def test_parse_tickers_default(tmp_path):
    parser = cli.build_arg_parser()
    args = parser.parse_args([])
    out = cli._parse_tickers(args)
    # Default universe is non-empty and uppercased.
    assert out, "default ticker universe should not be empty"
    assert all(t.upper() == t for t in out)


# ----- 7. .gitkeep is restored if missing -----

def test_gitkeep_idempotent(tmp_path):
    target = tmp_path / "earnings"
    cli._ensure_cache_dir(target)
    keep = target / ".gitkeep"
    assert keep.exists()
    # Run again — should be a no-op, no exception.
    cli._ensure_cache_dir(target)
    assert keep.exists()
