"""Tests for audit3 as an emission gate: denylist, symbol identity, namespaces.

Three properties the 2026-11-19 review demanded and this change delivers:

1. a KILL cell blocks the emitter, direction-aware, and fails open on a stale or
   missing ledger so an audit file can never halt the scanner;
2. BTC-USD and BTCUSDT score as one instrument instead of two verdicts;
3. only cells matching a pre-registered pod may reach PROVEN_T2.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine.audit3_denylist import denied_reason, summary  # noqa: E402
from alpha_engine.audit3_tribunal import build_report  # noqa: E402
from alpha_engine.symbol_identity import canonical_symbol, direction_key  # noqa: E402

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)


# ── symbol identity ────────────────────────────────────────────────────────
def test_crypto_spellings_are_one_instrument():
    for raw in ("BTC-USD", "BTCUSDT", "BTC/USD", "btc", "BTC-USD ", "BTCUSD"):
        assert canonical_symbol(raw, "CRYPTO") == "BTC", raw


def test_forex_and_equity_are_not_mangled():
    assert canonical_symbol("EURUSD=X", "FOREX") == "EURUSD"
    assert canonical_symbol("AUDCAD", "FOREX") == "AUDCAD"
    assert canonical_symbol("BRK-B", "EQUITY") == "BRK.B"
    assert canonical_symbol("SPY", "ETF") == "SPY"


def test_direction_spellings():
    assert direction_key("BUY") == "LONG"
    assert direction_key("SELL") == "SHORT"
    assert direction_key("L") == "LONG"
    assert direction_key("") == "UNKNOWN"


# ── denylist ───────────────────────────────────────────────────────────────
def _ledger(path: Path, generated_at: datetime, include_symbol_kill: bool = True):
    kills = []
    if include_symbol_kill:
        kills.append({"scope": "symbol", "asset_class": "CRYPTO", "strategy": "BTC-USD",
                      "direction": "LONG", "n": 25, "net_expectancy_pct": -1.8,
                      "harm_q": 0.02})
    payload = {
        "schema": "audit3.v1",
        "generated_at": generated_at.isoformat(),
        "cells": [
            {"asset_class": "CRYPTO", "strategy": "s1", "direction": "LONG", "n": 40,
             "net_expectancy_pct": -0.5, "harm_q": 0.01, "verdict": "KILL"},
            {"asset_class": "CRYPTO", "strategy": "s1", "direction": "SHORT", "n": 40,
             "net_expectancy_pct": 0.4, "verdict": "PROVEN_T2"},
        ],
        "kill_tribunal": {"kills": kills},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_kill_cell_blocks_emission_but_not_the_surviving_direction(tmp_path):
    path = _ledger(tmp_path / "led.json", NOW)
    long_pick = {"strategy": "s1", "direction": "LONG", "symbol": "ETHUSDT",
                 "asset_class": "CRYPTO"}
    short_pick = {"strategy": "s1", "direction": "SHORT", "symbol": "ETHUSDT",
                  "asset_class": "CRYPTO"}
    assert denied_reason(long_pick, path, now=NOW)
    assert denied_reason(short_pick, path, now=NOW) == ""


def test_symbol_kill_matches_across_spellings(tmp_path):
    path = _ledger(tmp_path / "led.json", NOW)
    for spelling in ("BTC-USD", "BTCUSDT", "btc/usd"):
        assert denied_reason({"strategy": "other", "direction": "LONG",
                              "symbol": spelling, "asset_class": "CRYPTO"},
                             path, now=NOW), spelling
    assert denied_reason({"strategy": "other", "direction": "SHORT",
                          "symbol": "BTCUSDT", "asset_class": "CRYPTO"},
                         path, now=NOW) == ""


def test_stale_or_missing_ledger_fails_open(tmp_path):
    stale = _ledger(tmp_path / "stale.json", NOW - timedelta(days=30))
    assert denied_reason({"strategy": "s1", "direction": "LONG", "symbol": "ETHUSDT"},
                         stale, now=NOW) == ""
    assert denied_reason({"strategy": "s1", "direction": "LONG", "symbol": "ETHUSDT"},
                         str(tmp_path / "absent.json"), now=NOW) == ""
    assert summary(stale)["armed"] is False


def test_kill_switch_disables_denylist(tmp_path, monkeypatch):
    path = _ledger(tmp_path / "led.json", NOW)
    monkeypatch.setenv("AUDIT3_DENYLIST_DISABLED", "1")
    assert denied_reason({"strategy": "s1", "direction": "LONG", "symbol": "ETHUSDT"},
                         path, now=NOW) == ""


# ── class gate ─────────────────────────────────────────────────────────────
def _class_ledger(path: Path, generated_at: datetime):
    payload = {
        "schema": "audit3.v1",
        "generated_at": generated_at.isoformat(),
        "cells": [
            {"asset_class": "CRYPTO", "strategy": "s1", "direction": "LONG", "n": 40,
             "net_expectancy_pct": -0.5, "harm_q": 0.01, "verdict": "KILL"},
            {"asset_class": "CRYPTO", "strategy": "s1", "direction": "SHORT", "n": 40,
             "net_expectancy_pct": 0.4, "verdict": "CANDIDATE"},
        ],
        "kill_tribunal": {"kills": [
            {"scope": "class", "asset_class": "CRYPTO", "direction": "-", "n": 1851,
             "net_expectancy_pct": -0.51, "harm_q": 0.01},
        ]},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_class_gate_admits_only_separately_cleared_cells(tmp_path, monkeypatch):
    monkeypatch.delenv("AUDIT3_DENYLIST_CLASS_GATE", raising=False)
    monkeypatch.delenv("AUDIT3_DENYLIST_DISABLED", raising=False)
    path = _class_ledger(tmp_path / "cls.json", NOW)
    unknown = {"strategy": "never_scored", "direction": "LONG",
               "symbol": "ETHUSDT", "asset_class": "CRYPTO"}
    survivor = {"strategy": "s1", "direction": "SHORT",
                "symbol": "ETHUSDT", "asset_class": "CRYPTO"}
    assert denied_reason(unknown, path, now=NOW), "unscored cell in a killed class must not emit"
    # s1 SHORT is CANDIDATE: it separately cleared a positive gate, so the class
    # aggregate cannot override it.
    assert denied_reason(survivor, path, now=NOW) == ""
    assert denied_reason(dict(unknown, paper_trade=True), path, now=NOW) == ""


def test_class_gate_modes(tmp_path, monkeypatch):
    path = _class_ledger(tmp_path / "cls2.json", NOW)
    survivor = {"strategy": "s1", "direction": "SHORT", "symbol": "ETHUSDT",
                "asset_class": "CRYPTO"}
    weak = {"strategy": "never_scored", "direction": "LONG", "symbol": "ETHUSDT",
            "asset_class": "CRYPTO"}
    monkeypatch.setenv("AUDIT3_DENYLIST_CLASS_GATE", "off")
    assert denied_reason(weak, path, now=NOW) == ""
    monkeypatch.setenv("AUDIT3_DENYLIST_CLASS_GATE", "all")
    assert denied_reason(weak, path, now=NOW)
    assert denied_reason(survivor, path, now=NOW)


def test_class_gate_ignores_un_killed_classes(tmp_path, monkeypatch):
    monkeypatch.delenv("AUDIT3_DENYLIST_CLASS_GATE", raising=False)
    path = _class_ledger(tmp_path / "cls3.json", NOW)
    eq = {"strategy": "never_scored", "direction": "LONG", "symbol": "AAPL",
          "asset_class": "EQUITY"}
    assert denied_reason(eq, path, now=NOW) == ""


def test_health_check_fails_loudly(tmp_path, monkeypatch):
    import importlib.util
    monkeypatch.delenv("AUDIT3_DENYLIST_DISABLED", raising=False)
    spec = importlib.util.spec_from_file_location(
        "a3_health", ROOT / "tools" / "audit3_denylist_health.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    stale = _ledger(tmp_path / "stale.json", NOW - timedelta(days=9))
    assert mod.main(["--ledger", stale, "--max-age-days", "2"]) == 1
    fresh = _ledger(tmp_path / "fresh.json", datetime.now(timezone.utc))
    assert mod.main(["--ledger", fresh, "--max-age-days", "2"]) == 0
    assert mod.main(["--ledger", str(tmp_path / "nope.json")]) == 1


# ── namespaces ─────────────────────────────────────────────────────────────
def _rows(n: int = 120) -> list[dict]:
    """Strong positive-expectancy cell spread over symbols and sources."""
    symbols = ("AAAUSDT", "BBBUSDT", "CCCUSDT", "DDDUSDT")
    sources = ("src_a", "src_b")
    rows = []
    for i in range(n):
        win = i % 3 != 0
        rows.append({
            "id": f"r{i}", "asset_class": "CRYPTO", "strategy": "cellA",
            "symbol": symbols[i % 4], "direction": "LONG",
            "source_system": sources[i % 2],
            "pnl_pct": 3.0 if win else -0.6,
            "status": "WON" if win else "LOST",
            "closed_at": f"2026-01-{(i % 28) + 1:02d}T00:00:00Z",
        })
    return rows


def test_discovery_cell_cannot_be_promoted():
    rep = build_report(_rows(), "x.json", None, confirmatory={"pods": []})
    cell = rep["cells"][0]
    assert cell["namespace"] == "discovery"
    assert cell["verdict"] == "CANDIDATE"
    assert any("discovery namespace" in r for r in cell["reasons"])
    assert rep["summary"]["n_proven"] == 0


def test_pre_registered_pod_can_promote():
    manifest = {"path": "m.json", "available": True,
                "pods": [{"id": "POD-A", "status": "pre_registered",
                          "strategies": ["cellA"], "asset_classes": ["CRYPTO"],
                          "directions": ["LONG"]}]}
    rep = build_report(_rows(), "x.json", None, confirmatory=manifest)
    cell = rep["cells"][0]
    assert cell["namespace"] == "confirmatory"
    assert cell["pod"] == "POD-A"
    assert cell["verdict"] == "PROVEN_T2"
    assert rep["multiplicity"]["n_pods"] == 1


def test_post_hoc_and_declined_pods_cannot_promote():
    rows = _rows()
    for status in ("post_hoc", "declined", "withdrawn", "observe"):
        manifest = {"path": "m.json", "available": True,
                    "pods": [{"id": "P", "status": status, "strategies": ["cellA"]}]}
        rep = build_report(rows, "x.json", None, confirmatory=manifest)
        assert rep["cells"][0]["namespace"] == "discovery", status
        assert rep["summary"]["n_proven"] == 0, status
    ok = {"path": "m.json", "available": True,
          "pods": [{"id": "P", "status": "pre_registered", "strategies": ["cellA"]}]}
    rep = build_report(rows, "x.json", None, confirmatory=ok)
    assert rep["cells"][0]["namespace"] == "confirmatory"
    assert rep["cells"][0]["verdict"] == "PROVEN_T2"


def test_bh_families_are_separate():
    rows = _rows()
    # a second, weak strategy so the discovery family is not a single cell
    for i, r in enumerate(rows[:40]):
        r2 = dict(r, id=f"w{i}", strategy="cellB", pnl_pct=0.1 if i % 2 else -0.2)
        rows.append(r2)
    manifest = {"path": "m.json", "available": True,
                "pods": [{"id": "POD-A", "status": "pre_registered", "strategies": ["cellA"]}]}
    rep = build_report(rows, "x.json", None, confirmatory=manifest)
    sizes = {ns: v["n_tested"] for ns, v in rep["multiplicity"]["families"].items()}
    assert sizes.get("confirmatory") == 1
    assert sizes.get("discovery") == 1


def test_symbols_are_grouped_canonically():
    rows = []
    for i in range(12):
        rows.append({"id": f"a{i}", "asset_class": "CRYPTO", "strategy": "s1",
                     "symbol": "BTC-USD", "direction": "LONG", "pnl_pct": -1.0,
                     "status": "LOST", "closed_at": "2026-01-01T00:00:00Z"})
        rows.append({"id": f"b{i}", "asset_class": "CRYPTO", "strategy": "s1",
                     "symbol": "BTCUSDT", "direction": "LONG", "pnl_pct": 0.5,
                     "status": "WON", "closed_at": "2026-01-02T00:00:00Z"})
    rep = build_report(rows, "x.json", None)
    btc = [c for c in rep["symbols"] if c["symbol"] == "BTC"]
    assert len(btc) == 1, [c["symbol"] for c in rep["symbols"]]
    assert btc[0]["n"] == 24
    assert not [c for c in rep["symbols"] if c["symbol"] in ("BTC-USD", "BTCUSDT")]
