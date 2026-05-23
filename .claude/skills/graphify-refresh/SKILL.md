---
name: graphify-refresh
description: Incrementally update the Graphify graph after code changes — re-extract only the touched directories and re-merge, instead of a full rebuild. Use after a commit, after editing modules, or when graphify-out is stale. Aliases - graphify-update, refresh-graph, regraph.
---

# graphify-refresh — incremental graph update

A full `/graphify-map` rebuild of this 20K-file repo is slow. After code
changes, re-extract only the affected directories and re-merge.

## Interpreter

```bash
PY="$(cat graphify-out/.graphify_python)"
```

## Check staleness

`GRAPH_REPORT.md` records the build commit ("Built from commit: `<sha>`").
Compare to `git rev-parse HEAD`. If equal and no uncommitted edits, the graph
is current — stop.

## Step 1 — find changed source directories

```bash
git diff --name-only HEAD~1 HEAD -- '*.py' | sed 's|/[^/]*$||' | sort -u
```

For uncommitted work use `git diff --name-only` (no range). Keep only
directories that were part of the original map (see `/graphify-map` source-dir
list) — ignore `node_modules`, `tests`, `.worktrees`, vendored dirs.

## Step 2 — re-extract each changed dir (AST, free)

```bash
for d in <changed dirs>; do
  "$PY" -m graphify update "$d" --no-cluster 2>&1 | grep -E 'Rebuilt|updated in'
done
```

`graphify update` is content-hash cached — unchanged files are skipped, so this
is fast even on a big directory. It rewrites `<dir>/graphify-out/graph.json`.

`graphify watch <path>` is the auto-mode (rebuilds on file save) — mention it to
the user if they want continuous refresh, but for a one-shot update use `update`.

## Step 3 — re-merge + re-cluster

The repo-level `graphify-out/graph.json` is a manual merge of every per-dir
fragment (the `merge-graphs` CLI is broken on 0.8.3). Re-run the manual merge
from `/graphify-map` Step 3 over ALL `*/graphify-out/graph.json` fragments, then:

```bash
"$PY" -m graphify cluster-only . --no-viz --graph graphify-out/graph.json
```

If `cluster-only` warns "new graph has N nodes but existing has M, refusing to
overwrite", the rebuild legitimately shrank (deleted code) — re-run with
`GRAPHIFY_FORCE=1` or `--force`.

## Doc changes

`graphify update` handles **code only**. Changed `.md`/docs need semantic
re-extraction — re-run `tools/_graphify_docs_multibackend.py` (it is per-file
cached, so only changed docs cost tokens).

## Report

State which directories were re-extracted, the new node/edge counts, and the
commit the graph now reflects.

## Companion skills

- `/graphify-map` — full rebuild from scratch
- `/graphify-ask` — query the graph
