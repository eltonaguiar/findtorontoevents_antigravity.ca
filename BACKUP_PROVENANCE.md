# Backup: unbacked working-tree changes from `~/repo-clean`

This branch is a **file-level backup**, not a history push.

- **Source:** `/home/eaguiar2015/repo-clean`, branch `main`, HEAD `a99a8989d24`
- **Created:** 2026-11-24
- **Why not a real push:** `repo-clean` is a rewritten-history clone (148,857 commits,
  4.75 GiB pack). Every full-history push to this repository failed with HTTP 500 during
  receive-pack of the ~16 GiB pack — see `PUSH_INSTRUCTIONS.md`, which is part of this backup.
- **What is here:** the 11 files that existed only in that clone's working tree (5 modified,
  6 untracked). Everything else in that tree was already reachable from this repository.
- **What is NOT here:** `repo-clean`'s rewritten commit history and its `.git` (4.8 GiB).
  The pre-rewrite rollback point still lives locally at
  `/home/eaguiar2015/fte-mirror-backup-2026-05-23.git`.
