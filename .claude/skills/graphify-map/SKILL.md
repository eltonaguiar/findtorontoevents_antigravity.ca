---
name: graphify-map
description: Build or rebuild the Graphify knowledge-graph map of this gigantic repo SAFELY. Use when asked to "map the codebase", "graphify the repo", "regenerate the code graph", or "index docs/code into graphify". Encodes the workarounds for this repo's 20K-file scale. Aliases - graphify-build, map-codebase, index-repo.
---

# graphify-map — safe codebase mapping for a 20K-file repo

Builds `graphify-out/graph.json` + `GRAPH_REPORT.md`. This repo is ~20,000
tracked files plus ~150 MB of vendored junk — the naive `graphify` skill flow
hangs or explodes here. This skill encodes the workarounds.

## Interpreter

Graphify is installed under a specific Python. Always use it:

```bash
PY="$(cat graphify-out/.graphify_python)"   # set by `graphify install`
```

If `graphify-out/.graphify_python` is missing, run `graphify install` once first.

## HARD RULES (learned the hard way)

1. **NEVER run `detect()` or `graphify update` on the repo root.** `detect()`
   does NOT honor `.graphifyignore` — it walks `node_modules/` (92 MB),
   `openclaude/` (50 MB), `swarm_runs/`, `.worktrees/` and runs for 30+ min at
   800 MB RAM before dying. Always scope to explicit source directories.
2. **`graphify merge-graphs` CLI is broken** on graphify 0.8.3 (networkx
   `compose_all` "All graphs must be graphs or multigraphs"). Merge graph JSON
   manually instead (see Step 3).
3. **Always cluster with `--no-viz`.** The merged graph is 90K+ nodes; the HTML
   viz step chokes above ~5,000 nodes.
4. **Code (AST) extraction is free + deterministic.** Docs need an LLM backend
   and cost tokens — keep them separate.

## Step 1 — AST-extract code (free, fast, per-dir)

`graphify update <dir> --no-cluster` writes `<dir>/graphify-out/graph.json`.
Run it per source directory — never the repo root. The production source dirs:

```
alpha_engine audit_trail tools genome scripts baby_strategies copy_trader_intel
paper_trading cross_pc_protocol audit_dashboard predictions incubator
cross_aggregation crypto_ml_edge coinglass_strategies ml_crypto_predictor
regime_terminal prediction_market_agents crypto_signal_engine signal_recorder
claude_gainer_ml ab_testing_agent breakout_arena rl_agent skyrocket_detector
strategy_registry STOCKS strategy_health tournament_agents ml_gatekeeper
local_gpu_trainer scanners forward_testing parallel_agent data_pipeline
data_providers stabilization engine utils portfolio_tracker strategies
TORONTOEVENTS_ANTIGRAVITY live-monitor signal_aggregator quan_engine
multi_asset meta_strategy risk_management trading database shared findstocks
findforex2 quant_lab mercury2
```

```bash
for d in alpha_engine audit_trail tools ...; do
  [ -d "$d" ] && "$PY" -m graphify update "$d" --no-cluster 2>&1 | grep -E 'Rebuilt|updated in'
done
```

Repo-root `*.py` (scrapers, deploy + dashboard scripts) have no clean
`update` path — extract them directly:

```python
from graphify.extract import collect_files, extract
from pathlib import Path
paths = sorted(p for p in Path('.').glob('*.py') if p.is_file())
result = extract(paths, cache_root=Path('.'))
Path('graphify-out/.graphify_sitecode.json').write_text(json.dumps(result))
```

**SKIP** (vendored / generated / scratch): `node_modules`, `openclaude*`,
`swarm_runs`, `.worktrees`, `.claude/worktrees`, `.git`, `tmp/`, `tests/`,
`HedgeFundData`, `AutoHedge`, `KIMI_*`, `battleground`, `ml_battleground`,
`sandbox`, `favcreators/node_modules`, `audit_dashboard/data/`, `next/_next/`,
`*.min.js`, `*.joblib`, `*.pkl`, `*.db`, large `data/*.json` dumps.

## Step 2 — Semantic-extract docs (optional, costs tokens)

For `*.md` / research / Pine — needs an LLM backend. There is **no
`GEMINI_API_KEY`** on this machine. Working backends + their env keys:

| Backend | Model | Key env var | Notes |
|---|---|---|---|
| kimi | `kimi-k2.5` | `KIMI_MOONSHOT_APIKEY` (set as `MOONSHOT_API_KEY`) | reliable JSON |
| cerebras | `gpt-oss-120b` | `CEREBRAS_API` | fastest, queue-throttles under load |
| inception | `mercury-2` | `INCEPTION_AI_KEY` | reliable |

Dropped: **xai/grok** (both `X_AI_KEY` + `GROK_SUPER` revoked), **deepseek**
(frequent malformed JSON), **ollama-cloud** (`OLLAMA_CLOUD_KEY` is an SSH
push-key, not a chat token).

Register the non-built-in backends at runtime and shard across them for ~3×
throughput:

```python
import graphify.llm as gllm
gllm.BACKENDS["cerebras"] = {"base_url":"https://api.cerebras.ai/v1",
  "default_model":"gpt-oss-120b","env_key":"CEREBRAS_API","pricing":{"input":0.3,"output":0.5},
  "temperature":0,"max_tokens":16384}
gllm.BACKENDS["inception"] = {"base_url":"https://api.inceptionlabs.ai/v1",
  "default_model":"mercury-2","env_key":"INCEPTION_AI_KEY","pricing":{"input":0.3,"output":0.5},
  "temperature":0,"max_tokens":16384}
```

**Truncation fix (mandatory):** graphify's default `max_tokens=16384` truncates
the JSON response mid-string (~60K chars) → parse failure. Before importing
graphify set `os.environ["GRAPHIFY_MAX_OUTPUT_TOKENS"]="32768"` AND pass
`token_budget=20000` to `extract_corpus_parallel(...)`. Smaller input chunks
keep output under the cap.

`tools/_graphify_docs_multibackend.py` is the reference implementation — shards
the `.md` corpus across kimi+cerebras+inception with the fix applied.

## Step 3 — Merge fragments (manual — CLI is broken)

```python
import json
nodes = {}; links = []; hyper = []
for f in [list of every */graphify-out/graph.json + .graphify_*.json fragment]:
    d = json.load(open(f, encoding="utf-8"))
    for n in d.get("nodes", []): nodes[n["id"]] = n
    links.extend(d.get("links", d.get("edges", [])))
    hyper.extend(d.get("hyperedges", []))
out = {"nodes": list(nodes.values()), "links": links, "hyperedges": hyper,
       "input_tokens": 0, "output_tokens": 0}
json.dump(out, open("graphify-out/graph.json", "w", encoding="utf-8"))
```

Dedup nodes by `id`. graph.json uses `links` (some fragments use `edges` — handle both).

## Step 4 — Cluster + report

```bash
"$PY" -m graphify cluster-only . --no-viz --graph graphify-out/graph.json
```

Produces `graphify-out/GRAPH_REPORT.md` + community structure. Always `--no-viz`.

## Step 5 — Report to user

Node/edge/community counts, token cost (0 for AST-only), and the
`graphify-out/graph.json` + `GRAPH_REPORT.md` paths. Do NOT commit
`graphify-out/` — graph.json is 60-90 MB; add it to `.gitignore`.

## Companion skills

- `/graphify-ask` — query the built graph
- `/graphify-refresh` — incremental update after code changes
