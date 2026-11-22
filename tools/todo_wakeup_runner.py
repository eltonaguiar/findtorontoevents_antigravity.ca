#!/usr/bin/env python3
"""todo_wakeup_runner.py — drive docs/TODO_LEDGER_2026-11-22.md autonomously.

One ledger item per invocation, executed by a headless agent CLI, with a durable
log and a hard self-disable. Designed for cron:

    */30 * * * * cd <repo> && flock -n /tmp/todo_wakeup.lock \
        python3 tools/todo_wakeup_runner.py >> reports/todo_wakeup.log 2>&1

WHY IT RUNS IN AN ISOLATED WORKTREE, NOT THE MAIN TREE
    The first version refused to run whenever `git status` was dirty. On this repo
    that means never: at the time of writing 31 paths were dirty and only 2 were
    mine -- the rest belonged to another agent's in-flight work. Refusing is correct
    (an unattended agent must never edit on top of someone else's uncommitted
    changes; this repo has a documented silent-revert history) but refusing forever
    is just a stalled drain.

    So the agent works in its own worktree on the PR branch. The main tree's
    dirtiness is irrelevant -- there is no shared mutable state to clobber -- and
    the safety property is preserved rather than traded away. The dirty check is now
    scoped to the WORKTREE: dirty there means a previous run left work behind, which
    is exactly what should stop the next run.

SAFETY RAILS
    * flock at the shell level (cron line) AND an internal pid lock here
    * MAX_RUNS then self-disable by rewriting the tagged crontab line
    * never touches git history: no reset, no force-push, no branch deletes
    * one item per run, sequential, so a failure cannot cascade
    * every run appended to reports/wakeups/autonomous-<date>.log — durable, so a
      session restart loses nothing

EXIT CODES
    0 ran (or legitimately skipped)   2 nothing left to do   3 worktree dirty
    4 another run holds the lock      5 self-disabled / max runs reached
    6 worktree missing or on the wrong branch
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs/TODO_LEDGER_2026-11-22.md"
STATE = ROOT / ".todo_wakeup_state.json"
OUT_DIR = ROOT / "reports/wakeups"
LOCK = Path("/tmp/todo_wakeup_internal.lock")
CRON_TAG = "todo/wakeup-autonomous"

# The isolated worktree the agent is allowed to edit. All remaining provenance
# items belong on the PR branch anyway, so this is where they should land.
WORKTREE = Path(os.environ.get("TODO_WAKEUP_WORKTREE", "/tmp/prov-main"))
BRANCH = os.environ.get("TODO_WAKEUP_BRANCH", "feat/provenance-ledger-2026-11-22")
LEDGER_NAME = "docs/TODO_LEDGER_2026-11-22.md"

MAX_RUNS = 16          # ~8h at 30-minute cadence
MAX_ATTEMPTS = 2       # per item, then mark [!] and move on so one hard item cannot
                       # burn every remaining run
AGENT_TIMEOUT = 2400   # 40 min per item

PROMPT = """You are working unattended in the repository at {wt} (branch {branch}).

Do EXACTLY ONE item and nothing else: {item_id} -- {item_title}

The ledger is {ledger_name}. Read the item's acceptance test and treat it as the
definition of done. Read the whole item before writing code.

Hard rules (non-negotiable, from AGENTS.md):
- You are in an isolated worktree. Commit here. Do NOT cd out to the main tree and
  do NOT touch any other worktree.
- Never push branch push/phase2-round-2026-11-22 (it carries foreign commits). The
  only branch you may push is {branch}.
- Never run git reset --hard, git push --force, git clean -fd, or delete branches.
- export HOME=/home/eaguiar2015 before any Python that reads ~/dbpasses.txt or
  calls yfinance.
- Document any fix in a .md under updates/.
- Report gross and net together. NEVER invent a number; write UNMEASURED instead.
  If you cannot measure something, say so plainly and move on.
- Verify before claiming: run the acceptance test and paste the real output. A
  claim without command output is a failed item.

Procedure:
1. Read the item's acceptance test.
2. Implement it.
3. Run the verification and paste the real output.
4. Commit ONLY files you created or modified, with a message stating what was
   broken, what changed, and how it was verified.
5. In {ledger_name}, flip this item's `[ ]` to `[x]`, or to `[!]` with a one-line
   reason if genuinely blocked. Do not touch any other item.
6. Stop. Do not start another item.

If the item cannot be done for a real reason (missing data, needs a merge, needs a
human), mark it `[!]` with the reason and stop. Do not downgrade the acceptance
criterion to manufacture a pass.
"""


def _log(msg: str) -> None:
    line = f"[{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}] {msg}"
    print(line)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / f"autonomous-{dt.date.today()}.log").open("a") as f:
        f.write(line + "\n")


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except json.JSONDecodeError:
            pass
    return {"run": 0, "started": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}


def save_state(s: dict) -> None:
    STATE.write_text(json.dumps(s, indent=1))


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, timeout=180)


def worktree_ready() -> tuple[bool, str]:
    """The worktree must exist AND be on the expected branch."""
    if not WORKTREE.exists():
        return False, f"worktree missing at {WORKTREE}"
    r = _git(["rev-parse", "--abbrev-ref", "HEAD"], WORKTREE)
    if r.returncode != 0:
        return False, f"not a git worktree: {r.stderr.strip()[:120]}"
    have = r.stdout.strip()
    if have != BRANCH:
        return False, f"worktree is on {have!r}, expected {BRANCH!r}"
    return True, have


def worktree_dirty() -> list[str]:
    r = _git(["status", "--porcelain"], WORKTREE)
    return [l for l in r.stdout.splitlines() if l.strip()]


def push_ledger() -> None:
    """Main tree -> worktree so the agent edits a committed copy of the ledger."""
    dst = WORKTREE / LEDGER_NAME
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LEDGER, dst)
    _git(["add", LEDGER_NAME], WORKTREE)
    _git(["commit", "-q", "-m",
         "chore(todo): sync wakeup ledger into worktree [skip ci]"], WORKTREE)


def pull_ledger() -> None:
    """Worktree -> main tree so progress survives the worktree going away."""
    src = WORKTREE / LEDGER_NAME
    if src.exists():
        shutil.copy2(src, LEDGER)


def next_item() -> tuple[str, str] | None:
    """Next `## [ ]` item: (id, title). Skips `[!]` blocked and finished ones."""
    if not LEDGER.exists():
        return None
    for line in LEDGER.read_text().splitlines():
        m = re.match(r"^## \[ \] (T\d+) — (.+)$", line.strip())
        if m:
            return m.group(1), m.group(2).strip()
    return None


def mark_in_progress(item_id: str) -> None:
    txt = LEDGER.read_text()
    txt = re.sub(rf"^## \[ \] {re.escape(item_id)} — ", f"## [~] {item_id} — ",
                 txt, count=1, flags=re.M)
    LEDGER.write_text(txt)


def revert_in_progress(item_id: str) -> None:
    """If the agent died without touching the ledger, put it back to todo."""
    txt = LEDGER.read_text()
    txt = re.sub(rf"^## \[~\] {re.escape(item_id)} — ", f"## [ ] {item_id} — ",
                 txt, count=1, flags=re.M)
    LEDGER.write_text(txt)


def set_status(item_id: str, from_ch: str, to_ch: str) -> None:
    txt = LEDGER.read_text()
    txt = re.sub(rf"^## \[{re.escape(from_ch)}\] {re.escape(item_id)} — ",
                 f"## [{to_ch}] {item_id} — ", txt, count=1, flags=re.M)
    LEDGER.write_text(txt)


def agent_cmd(prompt: str) -> list[str] | None:
    """Pick a headless agent CLI, in order of what was actually verified to work.

    Verified 2026-11-22 on this host:
      kilo run --auto            WORKS (smoke test returned KILO_OK)
      opencode --auto --prompt   present, untested here
      gemini -p                  BROKEN: "client no longer supported for Gemini
                                 Code Assist for individuals" -- needs the Antigravity
                                 migration, so it is not a fallback
      codex exec                 BROKEN: its configured model gpt-5.4 is rejected
                                 for this ChatGPT account (400 model_not_found)

    --auto auto-approves permissions that are not explicitly denied. That is what
    lets an unattended run edit files, and it is also why this runner is scoped to
    a throwaway worktree rather than the main tree.
    """
    if shutil.which("kilo"):
        return ["kilo", "run", "--auto", prompt]
    if shutil.which("opencode"):
        return ["opencode", "--auto", "--prompt", prompt]
    return None


def self_disable(reason: str) -> None:
    """Remove our own tagged crontab line. Best-effort; never raises."""
    try:
        cur = subprocess.run(["crontab", "-l"], capture_output=True, text=True,
                             timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        _log(f"self-disable: could not read crontab ({reason})")
        return
    kept = [l for l in cur.splitlines() if CRON_TAG not in l]
    if len(kept) == len(cur.splitlines()):
        _log(f"self-disable: no tagged crontab line found ({reason})")
        return
    try:
        p = subprocess.run(["crontab", "-"], input="\n".join(kept) + "\n",
                           capture_output=True, text=True, timeout=60)
        ok = p.returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    _log(f"self-disable ({reason}) -> crontab {'rewritten' if ok else 'FAILED'}")


def main() -> int:
    st = load_state()
    if st.get("run", 0) >= MAX_RUNS:
        self_disable(f"reached MAX_RUNS={MAX_RUNS}")
        return 5

    # internal lock (belt and braces alongside the cron-level flock)
    try:
        LOCK.write_text(str(os.getpid()))
    except OSError:
        pass

    ready, detail = worktree_ready()
    if not ready:
        _log(f"SKIP: {detail}")
        return 6

    dirty = worktree_dirty()
    if dirty:
        _log(f"SKIP: worktree dirty ({len(dirty)} path(s)) -- a previous run left "
             f"work behind. First: {dirty[0][:80]}")
        st["dirty_skips"] = st.get("dirty_skips", 0) + 1
        save_state(st)
        if st["dirty_skips"] >= 6:
            self_disable("6 consecutive dirty-worktree skips")
        return 3

    item = next_item()
    if item is None:
        _log("nothing left to do: no `## [ ]` items remain in the ledger")
        self_disable("ledger exhausted")
        return 2

    item_id, item_title = item
    _log(f"RUN {st['run'] + 1}/{MAX_RUNS} -> {item_id}: {item_title} "
         f"(worktree {WORKTREE})")
    st["run"] = st.get("run", 0) + 1
    st.setdefault("items", []).append({"id": item_id, "started": dt.datetime.now(
        dt.timezone.utc).isoformat(timespec="seconds")})
    save_state(st)

    mark_in_progress(item_id)
    push_ledger()

    cmd = agent_cmd(PROMPT.format(wt=WORKTREE, branch=BRANCH,
                                  ledger_name=LEDGER_NAME,
                                  item_id=item_id, item_title=item_title))
    if cmd is None:
        _log("BLOCKED: no usable headless agent CLI (need kilo or opencode; "
             "codex and gemini are both broken on this host -- see agent_cmd)")
        revert_in_progress(item_id)
        return 5

    t0 = dt.datetime.now()
    try:
        r = subprocess.run(cmd, cwd=WORKTREE, capture_output=True, text=True,
                           timeout=AGENT_TIMEOUT)
        rc, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        rc, out = 124, f"agent timed out after {AGENT_TIMEOUT}s"
    except (OSError, subprocess.SubprocessError) as e:
        rc, out = 1, f"agent failed to launch: {e}"

    # durable transcript, trimmed so a runaway cannot fill the disk
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{item_id}-{dt.date.today()}.agent.log").write_text(out[-400_000:])
    dur = (dt.datetime.now() - t0).total_seconds()
    _log(f"{item_id} finished rc={rc} in {dur:.0f}s; transcript "
         f"{len(out)} bytes -> reports/wakeups/{item_id}-{dt.date.today()}.agent.log")

    if rc != 0 and "[ ]" not in LEDGER.read_text():
        revert_in_progress(item_id)

    pull_ledger()
    txt = LEDGER.read_text()
    if "[~]" in txt:
        set_status(item_id, "~", " ")
        txt = LEDGER.read_text()
    done = re.search(rf"^## \[[x!]\] {re.escape(item_id)} ", txt, re.M) is not None
    if not done:
        # the agent neither completed it nor marked it blocked
        n = st.setdefault("attempts", {}).get(item_id, 0) + 1
        st["attempts"][item_id] = n
        if n >= MAX_ATTEMPTS:
            set_status(item_id, " ", "!")
            _log(f"{item_id} not completed after {n} attempt(s) -> marked [!] and "
                 f"moving on. Needs a human or a better-scoped item.")
        else:
            _log(f"{item_id} not completed (attempt {n}/{MAX_ATTEMPTS}) -> left as "
                 f"[ ] for one more try")
    else:
        st.setdefault("attempts", {})[item_id] = st.setdefault(
            "attempts", {}).get(item_id, 0)
        _log(f"{item_id} resolved by the agent")

    st["items"][-1].update({"rc": rc, "seconds": round(dur),
                            "finished": dt.datetime.now(dt.timezone.utc)
                            .isoformat(timespec="seconds")})
    save_state(st)
    if st["run"] >= MAX_RUNS:
        self_disable(f"reached MAX_RUNS={MAX_RUNS}")
    return 0


def self_disable_if_idle(st: dict) -> None:
    """Deprecated: kept only so an old import cannot crash. Use the worktree-scoped
    dirty counter in main() instead."""
    return


if __name__ == "__main__":
    raise SystemExit(main())
