---
description: Alias for /swarm-gh_actions-log-review. Curated review of recent GitHub Actions job logs.
---

User invoked `/swarm-actions-log-review $ARGUMENTS`.

This is an alias for `/swarm-gh_actions-log-review`. Follow the instructions in `.claude/commands/swarm-gh_actions-log-review.md` and run the same pipeline with the same arguments.

```bash
python3 tools/gha_swarm_curated_review.py \
  --since-days 7 \
  --max-workflows 40 \
  --runs-per-workflow 3 \
  --skip-ftp-env \
  $ARGUMENTS
```

Pass `--strict` to only report failed/cancelled/timed_out jobs (noise reduction).

Then read `docs/GHA_SWARM_CURATED_REVIEW.md` and produce the same top-5-failing-jobs summary described in the aliased command.
