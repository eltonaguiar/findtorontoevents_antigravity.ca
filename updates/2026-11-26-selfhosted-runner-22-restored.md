# Self-hosted runner 22 restored + batch protocol (2026-11-26)

## The runner was not deregistered — it was stopped

`gx10-arm64-native` (runner id 22, labels `self-hosted, Linux, ARM64, gx10`) was
configured at 03:32Z and went offline at 03:47Z. The agent log shows why:

```
03:47:43Z: Job collect-and-update completed with result: Canceled
03:47:43Z: job renew has been cancelled, stop renew job ...
03:47:43Z: Runner execution been cancelled.
```

**A cancelled job terminates the listener.** The runner then reports `offline`
with `busy=true` and refuses to start:

```
√ Connected to GitHub
A session for this runner already exists.
Runner connect error: Error: Conflict. Retrying until reconnected.
```

Because the job was still marked `in_progress` server-side, the session could not
be released. Cancelling the orphaned run (`45755533757`) freed it and the agent
reconnected on its own:

```
04:54:59Z: Runner reconnected.
04:54:59Z: Listening for Jobs
```

## Second cause of flapping: duplicate listeners on the same runner

At 04:52Z two `run.sh` processes existed for the same agent directory — one mine,
one started by a peer. The second logged `A session for this runner already
exists`, and the runner oscillated between `online` and `offline`. **One listener
per agent directory.** Killing the duplicate wrapper left a single listener.

## Batch protocol implemented (`tools/gha_selfhosted_batch.py`)

The operator's rule — 1-2 workflows at a time, validate the log, switch back to
the cloud runner, next batch — is now a tool:

```bash
python3 tools/gha_selfhosted_batch.py --list          # runners + runner-capable workflows
python3 tools/gha_selfhosted_batch.py -w meme-scanner.yml
python3 tools/gha_selfhosted_batch.py -w a.yml -w b.yml   # max 2, then it trims
```

Two dispatch paths, both leaving nothing pinned:

- **workflow takes a `runner` input** (`alpha-engine-live`, `audit-dashboard`,
  `dynamic-alpha-engine`, `rsi5070-forward-snapshot`, `_dynamic-runner-template`):
  `gh workflow run … -f runner=self-hosted` on `main`. Nothing to revert.
- **everything else**: a throw-away `selfhosted-batch/<ts>-<wf>` branch is created
  from `origin/main` in a scratch worktree (`GHA_BATCH_WORKDIR`, default
  `/tmp/ghrun`), `runs-on:` is rewritten to `[self-hosted, Linux, ARM64]` on that
  branch only, the run is dispatched against the branch, and the branch is deleted.
  **`main` never contains a self-hosted pin**, so an offline runner can never wedge
  a scheduled job.

After each run the tool downloads the log and classifies it (`CLEAN` / `ERRORS` /
`BLOCKED_ENV`), appending to `reports/GHA_SELFHOSTED_BATCH.jsonl` so a batch in
flight is visible to everyone.

## Results (first two batches)

| Workflow | Run | Conclusion | Log | Runner |
|---|---|---|---|---|
| `master-picks-health.yml` | 45758445642 | success | CLEAN | runner 25 `gx10-arm64-linux` |
| `meme-scanner.yml` | 45758600705 | success | CLEAN | self-hosted pool |

Both were in the 175 "never executed" set before this. Neither left a branch or a
pin behind (`git ls-remote 'selfhosted-batch/*'` → 0; `origin/main` has no
`self-hosted` in those files).

## Collision hazard that needs a decision

Three runners on this one machine share **identical** labels:

```
22 gx10-arm64-native   self-hosted,Linux,ARM64,gx10   (ours)
25 gx10-arm64-linux    self-hosted,Linux,ARM64,gx10   (peer)
26 gx10-arm64-linux-2  self-hosted,Linux,ARM64,gx10   (peer)
```

A dispatch asking for `[self-hosted, Linux, ARM64]` lands on whichever is free —
batch 1 went to 25, not 22. Nothing is broken by that (same host, same toolchain),
but it means **label-based targeting cannot select runner 22**, and three
concurrent jobs on a box already running three vLLM containers is how you get
timeouts that look like workflow bugs. Either give each agent a unique label, or
serialize: announce the batch on COMS and take one at a time.

## Operational rules for this runner

1. One listener per agent directory — check `pgrep -af Runner.Listener` first.
2. Never cancel a job on it casually: cancelling kills the listener and leaves a
   sticky session that blocks restart until the run itself is cancelled.
3. arm64 native — amd64-only binaries and action images fail here.
4. The agent runs as `eaguiar2015`; no root.
5. Workspace is `~/actions-runner/_work`; do not delete it mid-job.
