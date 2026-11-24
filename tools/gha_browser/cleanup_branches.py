#!/usr/bin/env python3
"""Safe remote-branch cleanup executor for eltonaguiar/findtorontoevents_antigravity.ca.

Reads candidate branch names (one per line, with or without origin/ prefix) and
deletes ONLY branches that pass every safety rail. Dry-run by default.

Usage: cleanup_branches.py candidates.txt [--execute] [--min-age-days 45]

Safety rails (a branch is SKIPPED unless all pass):
  R1 protected pattern:  main, HEAD, gh-pages, sam-repo/*, ghactions-v*, hermes/*,
                         wired-in/*, wired*, anything checked out in a worktree
  R2 activity:           last commit younger than --min-age-days
  R3 unmerged work:      `git cherry origin/main <branch>` shows any '+' commit
  R4 explicit allowlist: branch must be listed in candidates.txt (no wildcards run)
"""
import datetime
import subprocess
import sys

REPO = "/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/ghactions"
PROTECTED_PREFIXES = ("main", "HEAD", "gh-pages", "sam-repo/", "ghactions-v", "hermes/",
                      "wired-in/", "wired", "origin/main", "origin/HEAD", "origin/gh-pages",
                      "origin/sam-repo/", "origin/ghactions-v", "origin/hermes/",
                      "origin/wired-in/", "origin/wired")


def git(*args, timeout=120):
    try:
        return subprocess.run(("git",) + args, capture_output=True, text=True, cwd=REPO,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        r = subprocess.CompletedProcess(args, 124, "", "timeout")
        return r


def worktree_branches():
    out = git("worktree", "list", "--porcelain").stdout
    return {line.split("/", 1)[1] for line in out.splitlines()
            if line.startswith("branch: refs/heads/")}


def norm(b):
    b = b.strip().replace("origin/", "", 1) if b.strip().startswith("origin/") else b.strip()
    return b


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    execute = "--execute" in sys.argv
    min_age = 45
    if "--min-age-days" in sys.argv:
        min_age = int(sys.argv[sys.argv.index("--min-age-days") + 1])
    if not args:
        print(__doc__)
        return
    wt = worktree_branches()
    now = datetime.datetime.now(datetime.timezone.utc)
    delete, skip = [], []
    for raw in open(args[0]):
        if not raw.strip() or raw.startswith("#"):
            continue
        b = norm(raw)
        full = f"origin/{b}"
        if any(full == p or b == p or full.startswith(p) or b.startswith(p.replace("origin/", ""))
               for p in PROTECTED_PREFIXES) or b in wt:
            skip.append((b, "R1 protected/worktree"))
            continue
        d = git("log", "-1", "--format=%ad", "--date=iso-strict", full).stdout.strip()
        try:
            age = (now - datetime.datetime.fromisoformat(d)).days
        except Exception:
            skip.append((b, "R1 unknown/missing"))
            continue
        if age < min_age:
            skip.append((b, f"R2 active ({age}d)"))
            continue
        rc = git("log", "--cherry-pick", "--right-only", "--no-merges", "--oneline",
                 f"origin/main...{full}", timeout=40)
        if rc.returncode == 124:
            skip.append((b, "R3 unverifiable (history too large) — HOLD"))
            continue
        plus = sum(1 for l in rc.stdout.splitlines() if l.strip())
        if plus:
            skip.append((b, f"R3 {plus} unmerged commit(s)"))
            continue
        delete.append((b, f"{age}d old, 0 unmerged"))

    print(f"{'EXECUTE' if execute else 'DRY-RUN'} — delete {len(delete)}, skip {len(skip)}\n")
    for b, why in delete:
        sha = git("rev-parse", f"origin/{b}").stdout.strip()[:12]
        print(f"  DELETE {b:55} sha={sha} ({why})")
        if execute:
            r = git("push", "origin", "--delete", b)
            print("        ->", "ok" if r.returncode == 0 else r.stderr.strip()[:80])
    print()
    for b, why in skip:
        print(f"  skip   {b:55} ({why})")


if __name__ == "__main__":
    main()
