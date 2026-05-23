---
name: graphify-ask
description: Query the existing Graphify knowledge graph to navigate this codebase fast. Use for "where is X defined", "what calls Y", "how do A and B connect", "explain this module", "what is in graphify". Reads graphify-out/graph.json — no LLM cost. Aliases - graphify-query, ask-graph, code-nav.
---

# graphify-ask — navigate the codebase via the knowledge graph

The repo graph lives at `graphify-out/graph.json` (~90K nodes / ~116K edges,
6,800+ communities). Per-directory graphs also exist at `<dir>/graphify-out/graph.json`.
Querying is free — pure graph traversal, no LLM call.

## Interpreter

```bash
PY="$(cat graphify-out/.graphify_python)"
```

## If no graph exists

If `graphify-out/graph.json` is missing, run `/graphify-map` first.

## Three query verbs

### `explain` — one node + its neighbors

```bash
"$PY" -m graphify explain "evaluate_kill" --graph graphify-out/graph.json
```

Returns the node's source location, type, community, degree, and every inbound
/outbound edge (calls, contains, rationale_for, imports, semantically_similar_to).
Best first move when you want to understand one function/class/concept.

### `query` — BFS traversal from a question

```bash
"$PY" -m graphify query "what computes the kill threshold" --graph graphify-out/graph.json
"$PY" -m graphify query "how are picks scored" --budget 4000 --graph graphify-out/graph.json
```

Flags: `--dfs` (depth-first instead of BFS), `--budget N` (token cap, default
2000), `--context C` (filter by edge type, repeatable, e.g. `--context call`).
Use when you don't know the exact node name — phrase it as a question.

### `path` — shortest path between two nodes

```bash
"$PY" -m graphify path "production_scanner.py" "kill_gate.py" --graph graphify-out/graph.json
```

Shows the chain of edges linking two symbols. "No path found" is a real answer —
it means the two are in disconnected components (genuinely unrelated, or one
isn't wired into the production path — useful for the CLAUDE.md Wire-Up Rule).

## Picking the graph

- Cross-cutting question → `graphify-out/graph.json` (whole repo).
- Question scoped to one subsystem → `<dir>/graphify-out/graph.json` is smaller
  and faster (e.g. `alpha_engine/graphify-out/graph.json`).

## Node-name tips

Node ids look like `audit_trail_kill_gate_evaluate_kill`; labels look like
`evaluate_kill()` or `kill_gate.py`. `explain` matches loosely on the label —
try the bare function name first, then a fuller form if "No node matching" comes
back. If still nothing, the symbol may post-date the graph build → `/graphify-refresh`.

## Reporting

Summarize what the graph showed in plain language and cite real
`file:line` from the node `src`/`loc` fields so the user can jump there. Don't
dump raw NODE/EDGE lines unless asked.

## Companion skills

- `/graphify-map` — build the graph
- `/graphify-refresh` — update it after code changes
