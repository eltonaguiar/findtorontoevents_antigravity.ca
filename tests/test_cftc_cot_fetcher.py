"""Tests for the tools/cftc_cot_fetcher.py CLI bootstrapper.

Per CLAUDE.md Wire-Up Rule: this fetcher is opt-in sidecar tooling. The
tests cover the CLI surface and the pure ``compute_commercial_net_extreme``
helper. No live HTTP calls are made — all network is mocked.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import the CLI module by file path so we don't require an installed package.
_CLI_PATH = REPO_ROOT / "tools" / "cftc_cot_fetcher.py"
_spec = importlib.util.spec_from_file_location("tools_cftc_cot_cli", _CLI_PATH)
assert _spec and _spec.loader, "could not load tools/cftc_cot_fetcher.py spec"
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)  # type: ignore[union-attr]


# ----- 1. Default OFF behaviour -----

def test_env_var_defaults_to_off(monkeypatch):
    """CFTC_COT_FETCHER_ENABLED unset must mean disabled."""
    monkeypatch.delenv("CFTC_COT_FETCHER_ENABLED", raising=False)
    assert cli._is_enabled() is False


@pytest.mark.parametrize("val", ["0", "false", "no", "off", "", "  "])
def test_env_var_off_values(monkeypatch, val):
    monkeypatch.setenv("CFTC_COT_FETCHER_ENABLED", val)
    assert cli._is_enabled() is False


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "Yes", "on", " 1 "])
def test_env_var_on_values(monkeypatch, val):
    monkeypatch.setenv("CFTC_COT_FETCHER_ENABLED", val)
    assert cli._is_enabled() is True


# ----- 2. Bootstrap-only path creates the directory + .gitkeep -----

def test_bootstrap_only_creates_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("CFTC_COT_FETCHER_ENABLED", raising=False)
    target = tmp_path / "cftc_cot"

    rc = cli.main([
        "--cache-dir", str(target),
        "--bootstrap-only",
    ])

    assert rc == 0
    assert target.exists()
    assert (target / ".gitkeep").exists()
    # Bootstrap-only must NOT write a calendar.json (that's the disabled-stub path).
    assert not (target / cli.CALENDAR_INDEX_FILENAME).exists()


def test_bootstrap_only_is_idempotent(tmp_path, monkeypatch):
    """Re-running bootstrap-only must not error and must keep the dir intact."""
    monkeypatch.delenv("CFTC_COT_FETCHER_ENABLED", raising=False)
    target = tmp_path / "cftc_cot"
    cli.main(["--cache-dir", str(target), "--bootstrap-only"])
    cli.main(["--cache-dir", str(target), "--bootstrap-only"])
    assert (target / ".gitkeep").exists()


# ----- 3. Disabled path writes stub calendar but does not network -----

def test_disabled_path_writes_stub_index_no_network(tmp_path, monkeypatch):
    monkeypatch.delenv("CFTC_COT_FETCHER_ENABLED", raising=False)
    target = tmp_path / "cftc_cot"

    # Sentinel: if any HTTP path runs, fail loudly.
    def _explode(*_a, **_kw):  # pragma: no cover - guard
        raise AssertionError("network was invoked when fetcher is disabled")

    monkeypatch.setattr(cli, "_stdlib_http_get", _explode)

    rc = cli.main(["--cache-dir", str(target)])

    assert rc == 0
    index = target / cli.CALENDAR_INDEX_FILENAME
    assert index.exists(), "disabled run must drop a stub calendar.json"
    payload = json.loads(index.read_text(encoding="utf-8"))
    assert payload["ticker_count"] == 0
    assert payload["tickers"] == []
    assert "candidate_contracts" in payload
    # Default contracts include the Phase 2-F panel-mandated ZN/ES/NQ.
    for required in ("ZN=F", "ES=F", "NQ=F"):
        assert required in payload["candidate_contracts"]
    assert "note" in payload  # stub note is the tell that this was a no-op run.


# ----- 4. compute_commercial_net_extreme: empty + short series -----

def test_signal_empty_input_returns_no_extreme():
    sig = cli.compute_commercial_net_extreme([])
    assert sig["commercial_net"] is None
    assert sig["commercial_net_z"] is None
    assert sig["commercial_net_extreme"] is False
    assert sig["window_n"] == 0


def test_signal_short_series_returns_net_but_no_z():
    """With <10 weekly rows we should return net but not a z-score."""
    rows = [
        {
            "comm_positions_long_all": str(100 + i),
            "comm_positions_short_all": "50",
            "report_date_as_yyyy_mm_dd": f"2026-04-{20 - i:02d}",
        }
        for i in range(5)
    ]
    sig = cli.compute_commercial_net_extreme(rows)
    # rows[0] is the most recent: long=100+0=100, short=50 => net=50.
    assert sig["commercial_net"] == 50
    assert sig["commercial_net_z"] is None
    assert sig["commercial_net_extreme"] is False
    assert sig["window_n"] == 5


# ----- 5. compute_commercial_net_extreme: extreme detection -----

def test_signal_detects_extreme_long():
    """52 baseline weeks + a latest row that is +5 sigma should fire extreme."""
    # Build 52 weeks where commercial_net = 0 +/- small noise around mean=0.
    rows: list[dict] = []
    # Latest row first (DESC order, per fetch contract).
    # mean of the rest will be ~0; std ~10. Latest of +200 -> z ~ 20+.
    rows.append({
        "comm_positions_long_all": "300",
        "comm_positions_short_all": "100",
        "report_date_as_yyyy_mm_dd": "2026-04-25",
    })
    for i in range(51):
        delta = (i % 3) - 1  # -1, 0, +1 cycling
        rows.append({
            "comm_positions_long_all": str(100 + delta),
            "comm_positions_short_all": "100",
            "report_date_as_yyyy_mm_dd": f"2026-04-{25 - i - 1:02d}",
        })

    sig = cli.compute_commercial_net_extreme(rows)
    assert sig["commercial_net"] == 200
    assert sig["commercial_net_z"] is not None
    assert sig["commercial_net_z"] > cli.EXTREME_Z_THRESHOLD
    assert sig["commercial_net_extreme"] is True
    assert sig["window_n"] == 52
    assert sig["report_date"] == "2026-04-25"


def test_signal_detects_extreme_short():
    """A large negative latest-net should also fire extreme."""
    rows: list[dict] = []
    rows.append({
        "comm_positions_long_all": "100",
        "comm_positions_short_all": "300",
        "report_date_as_yyyy_mm_dd": "2026-04-25",
    })
    for i in range(51):
        delta = (i % 3) - 1
        rows.append({
            "comm_positions_long_all": "100",
            "comm_positions_short_all": str(100 + delta),
            "report_date_as_yyyy_mm_dd": f"2026-04-{25 - i - 1:02d}",
        })

    sig = cli.compute_commercial_net_extreme(rows)
    assert sig["commercial_net"] == -200
    assert sig["commercial_net_z"] is not None
    assert sig["commercial_net_z"] < -cli.EXTREME_Z_THRESHOLD
    assert sig["commercial_net_extreme"] is True


def test_signal_normal_range_not_extreme():
    """Latest row inside the noise band must NOT fire extreme."""
    rows: list[dict] = []
    for i in range(52):
        delta = (i % 3) - 1
        rows.append({
            "comm_positions_long_all": str(100 + delta),
            "comm_positions_short_all": "100",
            "report_date_as_yyyy_mm_dd": f"2026-04-{25 - i:02d}",
        })

    sig = cli.compute_commercial_net_extreme(rows)
    assert sig["commercial_net_z"] is not None
    assert abs(sig["commercial_net_z"]) < cli.EXTREME_Z_THRESHOLD
    assert sig["commercial_net_extreme"] is False


# ----- 6. fetch_contract uses the injected http_get + writes the right shape -----

def test_fetch_contract_with_mocked_http(tmp_path):
    fake_rows = [
        {
            "comm_positions_long_all": "150",
            "comm_positions_short_all": "100",
            "report_date_as_yyyy_mm_dd": "2026-04-25",
            "market_and_exchange_names": "10-YEAR U.S. TREASURY NOTES - CHICAGO BOARD OF TRADE",
        },
    ]
    captured: dict = {"url": None}

    def mock_http_get(url: str) -> str:
        captured["url"] = url
        return json.dumps(fake_rows)

    record = cli.fetch_contract(
        "ZN=F",
        cli.DEFAULT_CONTRACTS["ZN=F"],
        http_get=mock_http_get,
    )

    assert record["yf_ticker"] == "ZN=F"
    assert record["source"] == "cftc_socrata_legacy_futures_only"
    assert record["rows"] == fake_rows
    assert record["signal"]["commercial_net"] == 50
    assert "fetched_at" in record
    # CFTC market-name encoding must be in the URL.
    assert captured["url"] is not None
    assert "10-YEAR%20U.S.%20TREASURY%20NOTES" in captured["url"]


def test_fetch_contract_handles_http_error_gracefully():
    """A network error must NOT raise; record.source stays 'missing'."""
    from urllib.error import URLError

    def mock_http_get(url: str) -> str:
        raise URLError("simulated outage")

    record = cli.fetch_contract(
        "ZN=F",
        cli.DEFAULT_CONTRACTS["ZN=F"],
        http_get=mock_http_get,
    )
    assert record["source"] == "missing"
    assert "error" in record
    assert "URLError" in record["error"]


def test_fetch_contract_handles_bad_json():
    def mock_http_get(url: str) -> str:
        return "not json {{{{"

    record = cli.fetch_contract(
        "ZN=F",
        cli.DEFAULT_CONTRACTS["ZN=F"],
        http_get=mock_http_get,
    )
    assert record["source"] == "missing"
    assert "error" in record


# ----- 7. CLI integration: enabled run writes per-contract files + index -----

def test_enabled_run_writes_files(tmp_path, monkeypatch):
    monkeypatch.setenv("CFTC_COT_FETCHER_ENABLED", "1")
    target = tmp_path / "cftc_cot"

    fake_rows = [
        {
            "comm_positions_long_all": str(100 + (i % 3 - 1)),
            "comm_positions_short_all": "50",
            "report_date_as_yyyy_mm_dd": f"2026-04-{25 - i:02d}",
        }
        for i in range(60)
    ]

    def mock_http_get(url: str, user_agent: str = "x") -> str:
        return json.dumps(fake_rows)

    monkeypatch.setattr(cli, "_stdlib_http_get", mock_http_get)

    rc = cli.main([
        "--cache-dir", str(target),
        "--contracts", "ZN=F,ES=F",
    ])
    assert rc == 0

    # Per-contract files using filesystem-safe names.
    assert (target / "ZN_latest.json").exists()
    assert (target / "ES_latest.json").exists()
    # Index file lists both tickers.
    index = json.loads((target / cli.CALENDAR_INDEX_FILENAME).read_text(encoding="utf-8"))
    assert set(index["tickers"]) == {"ZN=F", "ES=F"}
    assert index["ticker_count"] == 2
    # Per-contract payload has the signal block.
    zn = json.loads((target / "ZN_latest.json").read_text(encoding="utf-8"))
    assert "signal" in zn
    assert zn["signal"]["commercial_net"] is not None


# ----- 8. Contract resolution -----

def test_parse_contracts_default():
    out = cli._parse_contracts(None)
    # Phase 2-F mandated trio must be present.
    assert "ZN=F" in out
    assert "ES=F" in out
    assert "NQ=F" in out


def test_parse_contracts_unknown_ticker_rejected():
    with pytest.raises(SystemExit) as exc:
        cli._parse_contracts("FAKE=F")
    assert "FAKE=F" in str(exc.value)


def test_contract_filename_strips_yfinance_suffix():
    assert cli._contract_filename("ZN=F") == "ZN_latest.json"
    assert cli._contract_filename("ES=F") == "ES_latest.json"
    assert cli._contract_filename("6E=F") == "6E_latest.json"
