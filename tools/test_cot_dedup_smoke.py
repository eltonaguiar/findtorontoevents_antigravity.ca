"""Smoke test for COT per-release emit dedup (2026-05-13).

Verifies the new ledger logic in alpha_engine/cot_positioning.py:
  - First call with fresh ledger -> emits N picks
  - Second call (same release dates) -> emits 0 picks
  - Bumping release date -> emits again

Mocks fetch_cot_data_cftc + compute_net_positioning to avoid CFTC API.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alpha_engine import cot_positioning  # noqa: E402


def _fake_compute_net_positioning(reports):
    """Return canned non-NEUTRAL signal."""
    return {
        "signal": "BUY",
        "confidence": 80,
        "reason": "test",
        "percentile_rank": 5.0,
        "current_net": -50000,
        "lookback_weeks": 52,
        "latest_date": reports[0]["report_date_as_yyyy_mm_dd"],
    }


def _fake_fetch(release_date: str):
    def _f(code):
        return [{"report_date_as_yyyy_mm_dd": release_date,
                 "comm_positions_long_all": "1",
                 "comm_positions_short_all": "1"}]
    return _f


def run() -> int:
    with tempfile.TemporaryDirectory() as td:
        ledger = Path(td) / "cot_emitted_releases.json"
        # Use a release date >= 3 days old so lag guard passes
        public_date = (datetime.now(timezone.utc).date() - timedelta(days=10)).isoformat()
        bumped_date = (datetime.now(timezone.utc).date() - timedelta(days=5)).isoformat()

        with patch.object(cot_positioning, "EMITTED_RELEASES_PATH", str(ledger)), \
             patch.object(cot_positioning, "fetch_cot_data_cftc", _fake_fetch(public_date)), \
             patch.object(cot_positioning, "compute_net_positioning", _fake_compute_net_positioning):

            # 1st run — fresh ledger
            picks1 = cot_positioning.cot_positioning_strategy({})
            n1 = len(picks1)
            print(f"Run 1 (fresh ledger, release={public_date}): n={n1}")

            # 2nd run — same release date, should dedup to 0
            picks2 = cot_positioning.cot_positioning_strategy({})
            n2 = len(picks2)
            print(f"Run 2 (same release, ledger primed): n={n2}")

            # Bump release date
            with patch.object(cot_positioning, "fetch_cot_data_cftc",
                              _fake_fetch(bumped_date)):
                picks3 = cot_positioning.cot_positioning_strategy({})
            n3 = len(picks3)
            print(f"Run 3 (new release={bumped_date}): n={n3}")

            # Ledger contents
            data = json.loads(ledger.read_text())
            n_ledger = len(data.get("emitted", []))
            print(f"Ledger rows: {n_ledger}")

        # Assertions
        assert n1 == len(cot_positioning.COT_CONTRACTS), \
            f"Run 1 expected {len(cot_positioning.COT_CONTRACTS)} picks, got {n1}"
        assert n2 == 0, f"Run 2 (dedup) expected 0, got {n2}"
        assert n3 == len(cot_positioning.COT_CONTRACTS), \
            f"Run 3 (new release) expected {len(cot_positioning.COT_CONTRACTS)}, got {n3}"
        assert n_ledger == n1 + n3, \
            f"Ledger expected {n1 + n3} rows, got {n_ledger}"

        print("\nPASS dedup-bulk: First-emit -> N, dup -> 0, bumped release -> N again.")

    # Scenario 2: per-symbol scanner dispatch path (scanner.py:2187-2195 pattern)
    # The scanner calls cot_positioning_strategy(data, sym) once per symbol.
    # Each call reloads the ledger from disk — so cross-call dedup must work.
    with tempfile.TemporaryDirectory() as td:
        ledger = Path(td) / "cot_emitted_releases.json"
        public_date = (datetime.now(timezone.utc).date() - timedelta(days=10)).isoformat()
        with patch.object(cot_positioning, "EMITTED_RELEASES_PATH", str(ledger)), \
             patch.object(cot_positioning, "fetch_cot_data_cftc", _fake_fetch(public_date)), \
             patch.object(cot_positioning, "compute_net_positioning", _fake_compute_net_positioning):
            picks_eur_1 = cot_positioning.cot_positioning_strategy({}, "EURUSD")
            picks_eur_2 = cot_positioning.cot_positioning_strategy({}, "EURUSD")
            picks_gbp_1 = cot_positioning.cot_positioning_strategy({}, "GBPUSD")
        print(f"\nPer-symbol dispatch: EURUSD#1={len(picks_eur_1)} EURUSD#2={len(picks_eur_2)} GBPUSD#1={len(picks_gbp_1)}")
        assert len(picks_eur_1) == 1, f"EURUSD#1 expected 1, got {len(picks_eur_1)}"
        assert len(picks_eur_2) == 0, f"EURUSD#2 expected 0 (dedup via disk reload), got {len(picks_eur_2)}"
        assert len(picks_gbp_1) == 1, f"GBPUSD#1 expected 1, got {len(picks_gbp_1)}"
        print("PASS dedup-per-symbol: scanner dispatch dedups across calls via disk reload.")

    # Scenario 3: direction vocab normalization
    # BUY (cot_positioning_strategy) and LONG (__main__) both canonicalize to LONG.
    # SELL canonicalizes to SHORT.
    with tempfile.TemporaryDirectory() as td:
        ledger = Path(td) / "cot_emitted_releases.json"
        with patch.object(cot_positioning, "EMITTED_RELEASES_PATH", str(ledger)):
            cot_positioning._record_emitted_release("X", "BUY", "2026-05-01", "ts1")
            cot_positioning._record_emitted_release("Y", "SELL", "2026-05-01", "ts2")
            cot_positioning._record_emitted_release("Z", "LONG", "2026-05-01", "ts3")
            data = json.loads(ledger.read_text())
        dirs = {e["symbol"]: e["direction"] for e in data["emitted"]}
        assert dirs == {"X": "LONG", "Y": "SHORT", "Z": "LONG"}, f"got {dirs}"
        print("PASS direction-normalize: BUY/SELL/LONG/SHORT canonicalize to LONG/SHORT.")

    # Scenario 4: rotation prunes rows older than LOOKBACK_WEEKS
    with tempfile.TemporaryDirectory() as td:
        ledger = Path(td) / "cot_emitted_releases.json"
        old_date = (datetime.now(timezone.utc).date() - timedelta(weeks=80)).isoformat()
        fresh_date = (datetime.now(timezone.utc).date() - timedelta(weeks=4)).isoformat()
        ledger.write_text(json.dumps({"emitted": [
            {"symbol": "OLD1", "direction": "LONG", "latest_cot_date": old_date, "emitted_at": "old"},
            {"symbol": "OLD2", "direction": "SHORT", "latest_cot_date": old_date, "emitted_at": "old"},
            {"symbol": "FRESH1", "direction": "LONG", "latest_cot_date": fresh_date, "emitted_at": "fresh"},
        ]}))
        with patch.object(cot_positioning, "EMITTED_RELEASES_PATH", str(ledger)):
            cot_positioning._record_emitted_release("NEW", "BUY",
                                                    (datetime.now(timezone.utc).date()).isoformat(),
                                                    "now")
            data = json.loads(ledger.read_text())
        symbols = {e["symbol"] for e in data["emitted"]}
        assert symbols == {"FRESH1", "NEW"}, f"expected pruning of OLD1/OLD2, got {symbols}"
        print("PASS rotation: rows older than LOOKBACK_WEEKS pruned on write.")

    # Scenario 5 (PR #994 review fix): direction in dedup key allows
    # same-week SHORT->LONG flip to emit as a NEW signal.
    with tempfile.TemporaryDirectory() as td:
        ledger = Path(td) / "cot_emitted_releases.json"
        rel_date = "2026-05-06"
        with patch.object(cot_positioning, "EMITTED_RELEASES_PATH", str(ledger)):
            cot_positioning._record_emitted_release("EURUSD", "SELL", rel_date, "ts1")
            keys = cot_positioning._load_emitted_releases()
            assert ("EURUSD", "SHORT", rel_date) in keys, f"got {keys}"
            assert ("EURUSD", "LONG", rel_date) not in keys, "LONG must not match SHORT entry"
            cot_positioning._record_emitted_release("EURUSD", "BUY", rel_date, "ts2")
            keys2 = cot_positioning._load_emitted_releases()
            assert {("EURUSD", "SHORT", rel_date), ("EURUSD", "LONG", rel_date)} <= keys2, \
                f"both directions should coexist, got {keys2}"
        print("PASS direction-in-key: SHORT and LONG on same (symbol, release) coexist.")

    # Scenario 6 (PR #994 review fix): atomic-write does not leave partial
    # JSON on disk even if interrupted between read and write.
    with tempfile.TemporaryDirectory() as td:
        ledger = Path(td) / "cot_emitted_releases.json"
        with patch.object(cot_positioning, "EMITTED_RELEASES_PATH", str(ledger)):
            cot_positioning._record_emitted_release("X", "LONG", "2026-05-06", "ts")
            # After write, no .tmp file should remain
            assert not (Path(td) / "cot_emitted_releases.json.tmp").exists(), \
                "atomic-write tmp file must be renamed away"
            # Ledger must parse as valid JSON
            data = json.loads(ledger.read_text())
            assert "emitted" in data
        print("PASS atomic-write: no orphan .tmp file; ledger parses clean.")

    print("\nALL SCENARIOS PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
