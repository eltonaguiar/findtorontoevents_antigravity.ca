"""Echoed script source must not count as an emitted error.

Regression context: two consecutive self-hosted runs were scored ERRORS while
concluding success.

  * swarm-sync-v2  run 45762289378 — 4 "ERROR line" matches, all of them the
    literal text of unexecuted handlers (`echo 'ERROR: rebase conflict ...'`)
    that GitHub prints as part of the `run:` block before executing it.
  * strategy-funnel-hourly run 45762068793 — one "ERROR line" from a push that
    was rejected non-fast-forward and then succeeded on attempt 2.

A classifier that cannot tell source from output makes "ERRORS" a synonym for
"this workflow echoes the word ERROR", which is exactly the wrong signal.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gha_latest_run_log_audit import ERRORS as AUDIT_ERRORS  # noqa: E402
from tools.gha_latest_run_log_audit import bucket  # noqa: E402
from tools.gha_selfhosted_batch import classify  # noqa: E402


def _line(msg: str) -> str:
    return f"sync\tSync state files\t2026-11-26T05:32:00.0000000Z {msg}"


ECHO_SOURCE = "\n".join(
    [
        _line("echo 'ERROR: rebase conflict — aborting sync to avoid corrupting state files'"),
        _line("echo 'ERROR: push failed after 3 attempts'"),
        _line("No effective changes after restore — nothing to push"),
    ]
)


def test_echoed_error_handlers_are_not_errors():
    assert classify(ECHO_SOURCE) == ("CLEAN", [])


def test_real_error_line_is_still_an_error():
    verdict, notes = classify(_line("ERROR: disk full on /var"))
    assert verdict == "ERRORS"
    assert notes == ["1x ERROR line"]


def test_healed_push_retry_is_not_an_error():
    log = "\n".join(
        [
            _line("error: failed to push some refs to 'https://github.com/x/y.git'"),
            _line("Updates were rejected because a pushed branch tip is behind"),
            _line("Push failed on attempt 1, backing off 6s..."),
            _line("Pushed successfully on attempt 2"),
        ]
    )
    assert classify(log) == ("CLEAN", [])


def test_unhealed_push_failure_still_errors():
    # no "Pushed successfully" anywhere, so the retry never healed
    log = _line("ERROR: push failed after 3 attempts")
    verdict, _ = classify(log)
    assert verdict == "ERRORS"


def test_error_annotation_is_never_filtered():
    verdict, notes = classify(_line("##[error]Process completed with exit code 1."))
    assert verdict == "ERRORS"
    assert notes == ["1x error annotation"]


def test_log_auditor_skips_echo_lines_but_counts_output():
    counter: dict = {}
    samples: dict = {}
    hits = bucket(ECHO_SOURCE, AUDIT_ERRORS, counter, samples)
    assert hits == 0
    assert counter == {}

    counter2: dict = {}
    hits2 = bucket(_line("ERROR: disk full"), AUDIT_ERRORS, counter2, {})
    assert hits2 == 1
    assert counter2 == {"ERROR line": 1}
