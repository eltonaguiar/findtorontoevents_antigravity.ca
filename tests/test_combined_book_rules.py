"""Tests for frozen rules + SHA-256 hashing."""
from combined_book import rules


def test_rules_hash_is_64_hex_chars():
    assert len(rules.RULES_HASH) == 64
    assert all(c in "0123456789abcdef" for c in rules.RULES_HASH)


def test_rules_hash_changes_when_text_changes():
    h1 = rules.compute_rules_hash("rules version 1")
    h2 = rules.compute_rules_hash("rules version 2")
    assert h1 != h2


def test_verify_accepts_matching_hash():
    assert rules.verify_rules_hash(rules.RULES_HASH) is True


def test_verify_rejects_wrong_hash():
    assert rules.verify_rules_hash("0" * 64) is False


def test_frozen_constants_exist():
    assert rules.STARTING_CAPITAL == 100_000.0
    assert rules.PER_SLEEVE_CAP == 0.40
    assert rules.TRADE_COST_BPS == 10.0
    assert rules.KILL_DRAWDOWN == -0.15
    assert rules.VOL_TARGET_MIN == 0.05
    assert rules.VOL_TARGET_MAX == 0.10
    assert "d5bed907932009a96d45521c15102cba2092ec9307dfd8367aedf3f21c9fcfd5" in rules.RULES_REFERENCE_HASH
