"""Tests for M-040: tools/verify_citations.py phantom-work guard."""
import os
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest

# Import the module under test
sys.path.insert(0, str(Path(ROOT) / "tools"))
from verify_citations import _extract_shas, _extract_file_paths, verify_prompt_file


def _write_prompt(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "test_prompt.md"
    p.write_text(content, encoding="utf-8")
    return p


def test_extract_shas_finds_commit_like_hex():
    text = "Commit: abc1234567 and deadbeef12345678 are referenced"
    shas = _extract_shas(text)
    assert "abc1234567" in shas
    assert "deadbeef12345678" in shas


def test_extract_file_paths_finds_python_paths():
    text = "Edited audit_trail/quality_gates.py and tests/test_foo.py"
    paths = _extract_file_paths(text)
    assert "audit_trail/quality_gates.py" in paths
    assert "tests/test_foo.py" in paths


def test_verify_passes_on_real_existing_file(tmp_path):
    """A prompt citing a file that exists must PASS."""
    prompt = _write_prompt(
        tmp_path,
        textwrap.dedent("""\
            # Real file test
            File: audit_trail/quality_gates.py
        """)
    )
    rc = verify_prompt_file(prompt)
    assert rc == 0, "Should PASS for a real existing file"


def test_verify_fails_on_phantom_file(tmp_path):
    """A prompt citing a non-existent file must FAIL."""
    prompt = _write_prompt(
        tmp_path,
        textwrap.dedent("""\
            # Phantom file test
            See: audit_trail/phantom_nonexistent_file_xyzzy.py
        """)
    )
    rc = verify_prompt_file(prompt)
    assert rc == 1, "Should FAIL for a phantom file"


def test_verify_passes_when_no_citations(tmp_path):
    """A prompt with no file or commit citations must PASS."""
    prompt = _write_prompt(tmp_path, "# No citations here\nJust text.\n")
    rc = verify_prompt_file(prompt)
    assert rc == 0


def test_verify_fails_on_phantom_commit(tmp_path):
    """A prompt citing a 40-char SHA that doesn't exist in git must FAIL."""
    fake_sha = "0" * 40  # All-zeros SHA won't exist
    prompt = _write_prompt(tmp_path, f"Commit: {fake_sha}\n")
    rc = verify_prompt_file(prompt)
    assert rc == 1, "Should FAIL for a non-existent 40-char SHA"
