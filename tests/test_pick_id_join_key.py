"""Cross-system pick-id join keys (2026-11-19).

The DB stores `v1::<writer>::<id>`; the canonical view stores the bare id. Joining
on `split("::")[-1]` fixes that pair but breaks `writer::symbol::timestamp` ids,
which are legitimately namespaced — it produced 85 false collisions on 8,613 rows.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.resolved_closed_view import canonical_row  # noqa: E402
from alpha_engine.symbol_identity import pick_id_join_key  # noqa: E402


def test_version_writer_prefix_is_stripped():
    assert (
        pick_id_join_key("v1::signal_validation::sig_20260220_084510_AVAX-USD")
        == "sig_20260220_084510_AVAX-USD"
    )


def test_db_and_canonical_forms_collapse_to_one_key():
    db_side = "v1::signal_validation::sig_20260220_084510_AVAX-USD"
    canon_side = "sig_20260220_084510_AVAX-USD"
    assert pick_id_join_key(db_side) == pick_id_join_key(canon_side)


def test_writer_symbol_timestamp_ids_are_preserved():
    pid = "pt_funding_rate_carry::BARDUSDT::2026-03-05T13:30:16"
    assert pick_id_join_key(pid) == pid


def test_distinct_trades_do_not_collapse():
    a = pick_id_join_key("pt_funding_rate_carry::BARDUSDT::2026-03-05T13:30:16")
    b = pick_id_join_key("pt_funding_rate_carry::MANTRAUSDT::2026-03-05T13:30:16")
    assert a != b


def test_bare_ids_untouched():
    for pid in ("aggregated_picks_BTCUSDT_LONG_crypto_rsi_scout_20261119T145300Z",
                "Classic Momentum_penny_stocks_RIVN_2026-02-16",
                "sig_20260220_022455_AVAX-USD"):
        assert pick_id_join_key(pid) == pid


def test_empty_and_none():
    assert pick_id_join_key(None) == ""
    assert pick_id_join_key("") == ""
    assert pick_id_join_key("   ") == ""


def test_idempotent():
    pid = "v1::fallback::XLP|LONG|equity_sector_rotation_winner||EQUITY"
    once = pick_id_join_key(pid)
    assert pick_id_join_key(once) == once


def test_does_not_strip_only_one_of_two_prefixes_incorrectly():
    """A writer whose own id starts with `v2::` keeps its inner namespace."""
    assert pick_id_join_key("v1::writer::v2::inner") == "v2::inner"


def test_canonical_row_exposes_join_key():
    row = canonical_row({
        "id": "v1::signal_validation::sig_1",
        "symbol": "ADA-USD",
        "asset_class": "crypto",
        "direction": "LONG",
        "strategy": "MeanReversionBB",
        "pnl_pct": 1.0,
        "entry_price": 1.0,
        "closed_at": "2026-11-19T15:33:26Z",
    })
    assert row["id"] == "v1::signal_validation::sig_1"
    assert row["join_key"] == "sig_1"
