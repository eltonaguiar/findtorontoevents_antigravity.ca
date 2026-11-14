# Re-review watcher

Bounded background watcher for new audit artifacts.

## What it watches

- `origin/main` SHA (new commits, with the last 40 commit subjects)
- new audit-like remote branches (`audit|inspect|finpredict|deepai|hilarious|seer`)
- local files under `2026-11-14/`, `audits/`, `updates/`, `recommendations/`, `actions_deepdive/`
  (excluding `.git`, `node_modules`, `bestiejob`, `logs`, `tmp`)
- GitHub Actions failures/cancellations in the last 30 runs (every 5th cycle)

## Run

```bash
# one scan
bash rereview/watch.sh --once

# bounded background watcher (4 hours, 2-minute interval)
WATCH_INTERVAL=120 timeout 14400 bash rereview/watch.sh --loop
```

Output queue: `rereview/REREVIEW_QUEUE.md`
Log: `rereview/watch.log` (gitignored)

## Notes

- The watcher only **detects and queues** changes; it does not edit source or make trading decisions.
- `E:\findtorontoevents_antigravity.ca` is not mounted on this Linux host. The watcher covers the
  Linux checkout and `origin`. If the Windows checkout is synced to `origin`, those changes appear
  via the remote SHA / branch checks.
- State is gitignored under `rereview/state/`.
