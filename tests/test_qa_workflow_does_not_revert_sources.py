"""Guard against the QA snapshot workflow reverting source files.

2026-11-22: the QA Market Validation job rewrote
``tools/audit2_forward_summary.py`` back to its pre-#1048 content (deleting
``merge_gate``) and committed it as
``chore(qa): market validation snapshot [skip ci]``, which re-broke CI
collection on main. The cause was ``git reset --soft FETCH_HEAD`` in its retry
loop: ``--soft`` only moves HEAD, so a depth-1 checkout's stale index is what
``git commit`` publishes -- every file as of when the run started.
"""
import pathlib

WF = (pathlib.Path(__file__).resolve().parent.parent
      / ".github/workflows/qa-market-validation.yml")


def test_qa_workflow_does_not_use_a_soft_reset():
    text = WF.read_text()
    assert "git reset --soft" not in text, (
        "a soft reset keeps the shallow checkout's stale index, so the next "
        "commit silently reverts every file that changed on main since the run "
        "started; use `git reset FETCH_HEAD` (mixed) instead"
    )


def test_qa_workflow_stages_only_its_own_artifact():
    text = WF.read_text()
    assert "git add -A" not in text and "git add ." not in text, (
        "the artifact job must never stage the whole tree"
    )
    assert 'git add "$A"' in text
