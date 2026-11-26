"""The batch dispatcher must refuse workflows that push their own HEAD.

Regression context (2026-11-26): `strategy-funnel-hourly.yml` was dispatched from
a throw-away branch whose `runs-on:` had been rewritten to the self-hosted
runner. The workflow commits generated data and pushes with `safe_push.sh`,
which pushes HEAD — so the pinned workflow file travelled with the data commit
and main received commit 4ca05240, leaving an hourly production workflow pinned
to a runner that can go offline.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gha_selfhosted_batch import pushes_own_head  # noqa: E402


def _wf(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "wf.yml"
    p.write_text(body)
    return p


def test_detects_safe_push(tmp_path):
    p = _wf(tmp_path, "steps:\n  - run: bash .github/scripts/safe_push.sh\n")
    assert pushes_own_head(p) is True


def test_detects_plain_git_push(tmp_path):
    p = _wf(tmp_path, "steps:\n  - run: git push origin HEAD:main\n")
    assert pushes_own_head(p) is True


def test_allows_read_only_workflow(tmp_path):
    p = _wf(tmp_path, "steps:\n  - run: python tools/gha_queue_audit.py --out r.json\n")
    assert pushes_own_head(p) is False


def test_missing_file_is_not_treated_as_push(tmp_path):
    assert pushes_own_head(tmp_path / "nope.yml") is False


def test_real_repo_workflows_classify_correctly():
    # the one that actually leaked a pin
    assert pushes_own_head(REPO_ROOT / ".github/workflows/strategy-funnel-hourly.yml") is True
    # read-only monitors must stay dispatchable
    assert pushes_own_head(REPO_ROOT / ".github/workflows/gha-queue-audit.yml") is False
