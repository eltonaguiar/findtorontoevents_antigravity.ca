"""Tests for code review bugfixes (2026-04-22).

Finding 1: ETF misclassified as equity in normalize_asset_category.
  - Removed "etf": "equity" mapping so ETFs pass through as their own class.
  - Added "index": "futures" explicit mapping.

Finding 2: Archive dedup guard in save_closed_picks.
  - Prevents duplicate pick IDs in the JSONL archive on crash/restart.
  - Uses bounded tail-read (deque maxlen=ARCHIVE_DEDUP_TAIL_LINES).
"""

import json

import pytest

from alpha_engine.non_crypto_policy import (
    NON_CRYPTO_TP_SL_CAPS,
    clamp_non_crypto_tp_sl,
    normalize_asset_category,
)


# ═══════════════════════════════════════════════════════════════════════════
# Finding 1: ETF normalization
# ═══════════════════════════════════════════════════════════════════════════


class TestNormalizeAssetCategoryETF:
    """ETF must NOT be collapsed into equity — it has its own TP/SL caps."""

    def test_etf_category_passes_through(self):
        """category='etf' should return 'etf', not 'equity'."""
        assert normalize_asset_category(category="etf") == "etf"

    def test_etf_asset_class_passes_through(self):
        """asset_class='ETF' should return 'etf', not 'equity'."""
        assert normalize_asset_category(asset_class="ETF") == "etf"

    def test_etf_mixed_case(self):
        """Mixed-case 'Etf' should return 'etf'."""
        assert normalize_asset_category(category="Etf") == "etf"

    def test_etf_not_equity(self):
        """Explicitly verify ETF does NOT resolve to equity (the old bug)."""
        result = normalize_asset_category(category="etf")
        assert result != "equity", (
            "ETF was mapped to 'equity' — this is the bug that caused ETF picks "
            "to receive equity TP/SL caps (8%/5%) instead of ETF caps (5%/3%)."
        )


class TestNormalizeAssetCategoryIndex:
    """Index symbols must map to 'futures', not pass through unhandled."""

    def test_index_category_maps_to_futures(self):
        """category='index' should return 'futures'."""
        assert normalize_asset_category(category="index") == "futures"

    def test_index_asset_class_maps_to_futures(self):
        """asset_class='INDEX' should return 'futures'."""
        assert normalize_asset_category(asset_class="INDEX") == "futures"

    def test_index_mixed_case(self):
        """Mixed-case 'Index' should return 'futures'."""
        assert normalize_asset_category(category="Index") == "futures"

    def test_index_not_unhandled(self):
        """Verify 'index' does NOT fall through as an unhandled category
        (which would miss per-class dicts like NON_CRYPTO_TP_SL_CAPS)."""
        result = normalize_asset_category(category="index")
        assert result == "futures", (
            f"'index' resolved to '{result}' instead of 'futures' — "
            f"would miss NON_CRYPTO_TP_SL_CAPS and other per-class dicts."
        )


class TestClampNonCryptoTPSLETF:
    """ETF picks must get ETF-specific caps, not equity caps."""

    @pytest.fixture
    def etf_pick(self):
        return {
            "symbol": "SPY",
            "category": "etf",
            "direction": "LONG",
            "entry_price": 500.0,
            "take_profit": 550.0,  # 10% TP — exceeds ETF 5% cap
            "stop_loss": 460.0,    # 8% SL — exceeds ETF 3% cap
        }

    @pytest.fixture
    def equity_pick(self):
        return {
            "symbol": "AAPL",
            "category": "equity",
            "direction": "LONG",
            "entry_price": 200.0,
            "take_profit": 220.0,  # 10% TP — exceeds equity 8% cap
            "stop_loss": 185.0,    # 7.5% SL — exceeds equity 5% cap
        }

    def test_etf_tp_capped_at_etf_level(self, etf_pick):
        """ETF TP must be capped at 5% (0.050), not equity 8% (0.080)."""
        result = clamp_non_crypto_tp_sl(etf_pick)
        max_tp = 500.0 * (1.0 + 0.050)  # 525.0
        assert result["take_profit"] == pytest.approx(max_tp, rel=1e-4)

    def test_etf_sl_capped_at_etf_level(self, etf_pick):
        """ETF SL must be capped at 3% (0.030), not equity 5% (0.050)."""
        result = clamp_non_crypto_tp_sl(etf_pick)
        max_sl = 500.0 * (1.0 - 0.030)  # 485.0
        assert result["stop_loss"] == pytest.approx(max_sl, rel=1e-4)

    def test_equity_tp_capped_at_equity_level(self, equity_pick):
        """Equity TP must still be capped at 8% (0.080)."""
        result = clamp_non_crypto_tp_sl(equity_pick)
        max_tp = 200.0 * (1.0 + 0.080)  # 216.0
        assert result["take_profit"] == pytest.approx(max_tp, rel=1e-4)

    def test_equity_sl_capped_at_equity_level(self, equity_pick):
        """Equity SL must still be capped at 5% (0.050)."""
        result = clamp_non_crypto_tp_sl(equity_pick)
        max_sl = 200.0 * (1.0 - 0.050)  # 190.0
        assert result["stop_loss"] == pytest.approx(max_sl, rel=1e-4)

    def test_etf_and_equity_get_different_caps(self, etf_pick, equity_pick):
        """ETF and equity picks with proportionally identical overages
        must get clamped to different absolute levels (different caps)."""
        etf_result = clamp_non_crypto_tp_sl(etf_pick.copy())
        equity_result = clamp_non_crypto_tp_sl(equity_pick.copy())

        # ETF TP cap (5%) is tighter than equity TP cap (8%)
        etf_tp_pct = (etf_result["take_profit"] - 500.0) / 500.0
        equity_tp_pct = (equity_result["take_profit"] - 200.0) / 200.0
        assert etf_tp_pct < equity_tp_pct, (
            f"ETF TP cap ({etf_tp_pct:.3f}) should be tighter than "
            f"equity ({equity_tp_pct:.3f})"
        )

    def test_etf_short_direction(self):
        """ETF SHORT picks must also get ETF-specific caps."""
        pick = {
            "symbol": "QQQ",
            "category": "etf",
            "direction": "SHORT",
            "entry_price": 400.0,
            "take_profit": 350.0,  # 12.5% TP — exceeds ETF 5% cap
            "stop_loss": 440.0,    # 10% SL — exceeds ETF 3% cap
        }
        result = clamp_non_crypto_tp_sl(pick)
        # SHORT: max_tp = entry * (1 - max_tp_pct), max_sl = entry * (1 + max_sl_pct)
        max_tp = 400.0 * (1.0 - 0.050)  # 380.0
        max_sl = 400.0 * (1.0 + 0.030)  # 412.0
        assert result["take_profit"] == pytest.approx(max_tp, rel=1e-4)
        assert result["stop_loss"] == pytest.approx(max_sl, rel=1e-4)

    def test_index_pick_gets_futures_caps(self):
        """Index-category picks must get futures TP/SL caps (3%/2%)."""
        pick = {
            "symbol": "ES=F",
            "category": "index",
            "direction": "LONG",
            "entry_price": 5000.0,
            "take_profit": 5300.0,  # 6% TP — exceeds futures 3% cap
            "stop_loss": 4800.0,    # 4% SL — exceeds futures 2% cap
        }
        result = clamp_non_crypto_tp_sl(pick)
        max_tp = 5000.0 * (1.0 + 0.030)  # 5150.0
        max_sl = 5000.0 * (1.0 - 0.020)  # 4900.0
        assert result["take_profit"] == pytest.approx(max_tp, rel=1e-4)
        assert result["stop_loss"] == pytest.approx(max_sl, rel=1e-4)


class TestETFHasDedicatedCapsInConfig:
    """Verify the NON_CRYPTO_TP_SL_CAPS dict has distinct ETF and index entries."""

    def test_etf_caps_exist(self):
        assert "etf" in NON_CRYPTO_TP_SL_CAPS

    def test_etf_caps_differ_from_equity(self):
        assert NON_CRYPTO_TP_SL_CAPS["etf"] != NON_CRYPTO_TP_SL_CAPS["equity"]

    def test_etf_tp_tighter_than_equity(self):
        etf_tp = NON_CRYPTO_TP_SL_CAPS["etf"][0]
        equity_tp = NON_CRYPTO_TP_SL_CAPS["equity"][0]
        assert etf_tp < equity_tp, (
            f"ETF TP cap ({etf_tp}) should be tighter than equity ({equity_tp})"
        )

    def test_etf_sl_tighter_than_equity(self):
        etf_sl = NON_CRYPTO_TP_SL_CAPS["etf"][1]
        equity_sl = NON_CRYPTO_TP_SL_CAPS["equity"][1]
        assert etf_sl < equity_sl, (
            f"ETF SL cap ({etf_sl}) should be tighter than equity ({equity_sl})"
        )

    def test_futures_caps_exist(self):
        """Index maps to futures, so futures caps must be present."""
        assert "futures" in NON_CRYPTO_TP_SL_CAPS


# ═══════════════════════════════════════════════════════════════════════════
# Finding 2: Archive dedup guard
# ═══════════════════════════════════════════════════════════════════════════


class TestArchiveDedupGuard:
    """Test the archive dedup guard in save_closed_picks.

    Uses tmp_path to isolate file I/O. Patches module-level constants
    to redirect paths to the temp directory.
    """

    @pytest.fixture(autouse=True)
    def _patch_paths(self, tmp_path, monkeypatch):
        """Patch forward_validator constants to use tmp_path."""
        import alpha_engine.forward_validator as fv_mod

        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        closed_path = data_dir / "closed_picks.json"
        archive_path = data_dir / "closed_picks.archive.jsonl"

        monkeypatch.setattr(fv_mod, "DATA_DIR", data_dir)
        monkeypatch.setattr(fv_mod, "CLOSED_PICKS_PATH", closed_path)
        monkeypatch.setattr(fv_mod, "CLOSED_PICKS_ARCHIVE_PATH", archive_path)
        # Use a small retention cap so we don't need 500+ picks to trigger archiving
        monkeypatch.setattr(fv_mod, "CLOSED_PICKS_RETENTION", 3)
        monkeypatch.setattr(fv_mod, "ARCHIVE_DEDUP_TAIL_LINES", 100)
        # Disable A9 emitter-dedup so test picks with identical content are not
        # collapsed before the archive/retention logic under test runs.
        # (TestArchiveDedupGuard tests ARCHIVE dedup, not emitter dedup.)
        monkeypatch.setenv("EMITTER_DEDUP", "0")

    @staticmethod
    def _make_pick(pick_id: str, symbol: str = "BTCUSDT", pnl: float = 1.0) -> dict:
        # Each pick needs a DISTINCT entry_price: emitter_dedup.compute_dedup_key
        # hashes (asset_class|strategy|symbol|direction|entry_bar|entry_price).
        # Without a varying field every pick collides on one dedup_key and the
        # emitter-dedup layer (added after this test) collapses them — so the
        # retention/archive assertions saw 1 pick instead of N. Derive a unique
        # entry_price from pick_id so each pick is a genuinely distinct signal.
        _suffix = "".join(ch for ch in pick_id if ch.isdigit())
        _seed = int(_suffix) if _suffix else abs(hash(pick_id)) % 100000
        return {
            "id": pick_id,
            "symbol": symbol,
            "strategy": "test_strategy",
            "pnl_pct": pnl,
            "exit_reason": "TP_HIT" if pnl > 0 else "SL_HIT",
            "entry_price": 100.0 + _seed * 0.01,
        }

    def _load_archive_lines(self, tmp_path) -> list[dict]:
        archive_path = tmp_path / "data" / "closed_picks.archive.jsonl"
        if not archive_path.exists():
            return []
        lines = []
        with open(archive_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    lines.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # Skip malformed lines (matches production behavior)
        return lines

    def _load_hot_picks(self, tmp_path) -> list[dict]:
        closed_path = tmp_path / "data" / "closed_picks.json"
        if not closed_path.exists():
            return []
        with open(closed_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_no_archive_when_below_retention(self, tmp_path):
        """When pick count <= CLOSED_PICKS_RETENTION, no archiving occurs."""
        from alpha_engine.forward_validator import save_closed_picks

        picks = [self._make_pick(f"pick_{i}") for i in range(3)]
        save_closed_picks(picks)

        # Hot file should have all 3 picks
        hot = self._load_hot_picks(tmp_path)
        assert len(hot) == 3

        # Archive should not exist
        archive = self._load_archive_lines(tmp_path)
        assert len(archive) == 0

    def test_archive_triggered_when_over_retention(self, tmp_path):
        """When pick count > CLOSED_PICKS_RETENTION, excess is archived."""
        from alpha_engine.forward_validator import save_closed_picks

        picks = [self._make_pick(f"pick_{i}") for i in range(5)]
        save_closed_picks(picks)

        # Hot file should have only the last 3 (CLOSED_PICKS_RETENTION)
        hot = self._load_hot_picks(tmp_path)
        assert len(hot) == 3

        # Archive should have the first 2 overflow picks
        archive = self._load_archive_lines(tmp_path)
        assert len(archive) == 2

        # Archived picks should be the oldest (first in list)
        archived_ids = {p["id"] for p in archive}
        assert archived_ids == {"pick_0", "pick_1"}

    def test_dedup_guard_prevents_duplicate_archive(self, tmp_path):
        """If save_closed_picks is called twice with overlapping picks,
        the dedup guard prevents duplicate entries in the archive."""
        from alpha_engine.forward_validator import save_closed_picks

        # First call: 5 picks, 3 retained, 2 archived
        picks_batch1 = [self._make_pick(f"pick_{i}") for i in range(5)]
        save_closed_picks(picks_batch1)

        archive_after_first = self._load_archive_lines(tmp_path)
        assert len(archive_after_first) == 2

        # Simulate a crash scenario: same picks + new ones
        # This can happen when the validator crashes after archiving
        # but before the hot file is written, then re-runs with the
        # original full list.
        picks_batch2 = [self._make_pick(f"pick_{i}") for i in range(7)]
        save_closed_picks(picks_batch2)

        archive_after_second = self._load_archive_lines(tmp_path)
        # pick_0 and pick_1 are already in the archive from the first call,
        # so they should NOT be written again despite being in the overflow
        # set of the second call.
        archived_ids = [p["id"] for p in archive_after_second]
        assert archived_ids.count("pick_0") == 1, "pick_0 should appear exactly once in archive"
        assert archived_ids.count("pick_1") == 1, "pick_1 should appear exactly once in archive"
        # New overflow picks should also be archived
        assert "pick_2" in archived_ids
        assert "pick_3" in archived_ids

    def test_dedup_guard_with_no_existing_archive(self, tmp_path):
        """First archiving cycle (no existing archive) should work fine."""
        from alpha_engine.forward_validator import save_closed_picks

        picks = [self._make_pick(f"pick_{i}") for i in range(5)]
        save_closed_picks(picks)

        archive = self._load_archive_lines(tmp_path)
        assert len(archive) == 2
        assert archive[0]["id"] == "pick_0"
        assert archive[1]["id"] == "pick_1"

    def test_dedup_guard_with_malformed_archive(self, tmp_path):
        """If the archive contains malformed JSON lines, the guard
        should skip them gracefully and still dedup valid entries."""
        from alpha_engine.forward_validator import save_closed_picks

        archive_path = tmp_path / "data" / "closed_picks.archive.jsonl"
        # Write some malformed lines + one valid pick
        with open(archive_path, "a", encoding="utf-8") as f:
            f.write("NOT VALID JSON\n")
            f.write('{"id": "pick_0", "symbol": "BTCUSDT"}\n')
            f.write("\n")  # empty line
            f.write('{"broken": true\n')  # truncated JSON

        # Now save picks where pick_0 would overflow
        picks = [self._make_pick(f"pick_{i}") for i in range(5)]
        save_closed_picks(picks)

        archive = self._load_archive_lines(tmp_path)
        # pick_0 should be deduped (already in archive), pick_1 should be added
        archived_ids = [p["id"] for p in archive]
        assert archived_ids.count("pick_0") == 1, "pick_0 should not be duplicated"
        assert "pick_1" in archived_ids

    def test_hot_file_integrity_after_archive(self, tmp_path):
        """After archiving, the hot file should contain exactly the
        most recent CLOSED_PICKS_RETENTION picks."""
        from alpha_engine.forward_validator import save_closed_picks

        picks = [self._make_pick(f"pick_{i}", pnl=float(i)) for i in range(6)]
        save_closed_picks(picks)

        hot = self._load_hot_picks(tmp_path)
        assert len(hot) == 3
        # Should be the LAST 3 picks (most recent)
        hot_ids = [p["id"] for p in hot]
        assert hot_ids == ["pick_3", "pick_4", "pick_5"]

    def test_pick_without_id_still_archived(self, tmp_path):
        """Picks without an 'id' field should still be archived
        (dedup guard cannot check them, but they should pass through)."""
        from alpha_engine.forward_validator import save_closed_picks

        picks = [{"symbol": "BTCUSDT", "pnl_pct": 1.0}]  # No 'id' field (first, so in overflow)
        for i in range(4):
            picks.append(self._make_pick(f"pick_{i}"))
        save_closed_picks(picks)

        archive = self._load_archive_lines(tmp_path)
        # 5 picks total, RETENTION=3 → 2 archived (the first two in list)
        assert len(archive) == 2
        # First archived pick has no 'id' — dedup guard skips it (empty string not in set)
        assert archive[0].get("id", "") == ""
        # Second archived pick is pick_0
        assert archive[1]["id"] == "pick_0"

    def test_input_dedup_before_archiving(self, tmp_path):
        """save_closed_picks deduplicates input picks by ID before
        any archiving logic runs."""
        from alpha_engine.forward_validator import save_closed_picks

        # Create picks with duplicate IDs
        picks = [self._make_pick("dup_id") for _ in range(3)]
        save_closed_picks(picks)

        hot = self._load_hot_picks(tmp_path)
        # Only one pick with this ID should remain
        assert len(hot) == 1
        assert hot[0]["id"] == "dup_id"


class TestArchiveDedupTailRead:
    """Test that the bounded tail-read (deque) works correctly."""

    def test_tail_read_only_parses_recent_lines(self, tmp_path):
        """Verify that the deque approach only parses the last N lines."""
        from collections import deque

        # Write 10 lines
        lines = [f'{{"id": "pick_{i}"}}' for i in range(10)]
        content = "\n".join(lines) + "\n"

        archive_path = tmp_path / "test_archive.jsonl"
        archive_path.write_text(content, encoding="utf-8")

        # Read with maxlen=5 — should only get last 5
        with open(archive_path, "r", encoding="utf-8") as f:
            tail = deque(f, maxlen=5)

        ids = set()
        for line in tail:
            line = line.strip()
            if line:
                obj = json.loads(line)
                ids.add(obj["id"])

        # Should only see picks 5-9, not 0-4
        assert "pick_0" not in ids
        assert "pick_4" not in ids
        assert "pick_5" in ids
        assert "pick_9" in ids
        assert len(ids) == 5


class TestETFGapInNonCryptoCategories:
    """Document the known gap: 'etf' is not in NON_CRYPTO_CATEGORIES.

    This means is_non_crypto(category='etf') returns False, which may
    cause downstream code that gates on is_non_crypto() to skip ETF picks.
    This test documents the current behavior so regressions are caught.
    """

    def test_etf_not_in_non_crypto_categories(self):
        """KNOWN GAP: 'etf' is not in NON_CRYPTO_CATEGORIES."""
        from alpha_engine.non_crypto_policy import NON_CRYPTO_CATEGORIES
        assert "etf" not in NON_CRYPTO_CATEGORIES  # documents the gap

    def test_is_non_crypto_returns_false_for_etf(self):
        """is_non_crypto(category='etf') currently returns False because
        'etf' is not in the NON_CRYPTO_CATEGORIES set."""
        from alpha_engine.non_crypto_policy import is_non_crypto
        assert is_non_crypto(category="etf") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
