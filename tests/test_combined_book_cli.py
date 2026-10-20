"""Tests for the CLI subcommands."""
from combined_book.cli import main


def test_hash_check_reports_current_hash(capsys):
    code = main(["hash-check"])
    out = capsys.readouterr().out
    assert code == 0
    assert "RULES_HASH" in out
