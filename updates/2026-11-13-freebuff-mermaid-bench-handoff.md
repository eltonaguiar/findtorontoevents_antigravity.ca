# FREEBUFF handoff — mermaid fix benchmark + Mercury carry-over (2026-11-13)

**Why this file exists:** a peer agent (or a future session) should be able to pick this work up
from this document alone, without access to the original chat and without reading a `/tmp` log that
may be cleared. It is the repo copy of the session export.

**Provenance**
- Session: 2026-11-12 late → 2026-11-13, Freebuff CLI on the GX10/GB10 host.
- Repo branch at time of writing: `job-search-2026-11-03-ledger`.
- Session-local source: `/tmp/freebuff-mermaid-bench-2026-11-13.md` (identical body).
- Coordination log with the peer: `/tmp/freebuff.txt`, block `SYNC 12` points here.
- Peer's own log (`/tmp/claude_ollama.txt`) is owned by ollama-claude — never overwrite it.
- No secret values in this document. A scan for the usual provider key prefixes (OpenAI-style
  `sk-`, NVIDIA `nvapi-`, Google `AIza`) plus any assignment to the Inception key variable
  returns zero matches; the wording here avoids spelling a pattern that would trip that scan.

**Verified before publishing:** every number below comes from `results.json` written by the harness
in this document's section 4; the validator was proven on both a known-broken and a known-good
input before any model was called. Nothing here is estimated.

---

## Contents
1. Where the session started (Mercury carry-over)
2. The mermaid question the owner asked
3. Two of my own errors, corrected
4. The benchmark: method, results, artifacts, repro
5. Why one fixture page beats N deployed URLs
6. Pending, by owner
7. Repo rules kept

---

## 1. Where the session started (Mercury carry-over)

The objective was **not** mermaid. It was: retire the Inception Labs **Mercury** API (vendor sunset
2026-12-28) from every `github.com/eltonaguiar` surface, keep LiteLLM on `:4000` serving, and
coordinate with ollama-claude through `/tmp` files.

State of that work at handoff:

| Item | Branch / commit | Status |
|---|---|---|
| Mercury retirement, 37 files | `scrub/inception-mercury-2026-11-12` @ `2c08a4bb1433` | published, 3 ahead / 236 behind (behind = bot cron), **awaiting owner/peer merge decision** |
| hermes-web menu entry | `feat/hermes-web-menu-entry-2026-11-12` @ `5606c6c86702` | published, additions only |
| safe-patch helper | `feat/safe-patch-helper-2026-11-12` @ `6f51bc9eaa02` | published, additions only |
| AST reviewer codemod | `feat/ast-reviewer-codemod-2026-11-12` @ `ffd0bfdf5dcd` | published, additions only |
| retired-provider guard | `feat/retired-provider-guard-2026-11-12` @ `58baed09b6aa` | published, 2 added files, **merge requested from peer in SYNC 11 — no reply yet** |
| two peer patches | `/tmp/patch_swarm_picker_help.diff`, `/tmp/patch_ruflo_template_yaml.diff` | both `git apply --check` rc=0, ownership stays with the peer |

Owner-only blockers, unchanged: vendor key revocation, OpenRouter key rotation, FREELLM PR #1
merge, Windows bind/firewall for TCP 8642. Hermes `ask` is untestable from this host
(`192.168.2.32:8642` refuses in 0 ms, no `API_SERVER_KEY`).

Deliberate constraint honoured throughout: **`dbpasses.txt` was not modified or deleted** (owner
instruction); `INCEPTION_AI_KEY` is still in it.

Publishing mechanism, because `git push` hangs on this repo: the **Git Data API**, authenticated
with `gh auth token`. `git config --get github.token` is empty and produces "Bad credentials",
which makes every branch look missing — do not read an auth failure as "branch absent".

## 2. The mermaid question the owner asked

> "consider whether 'paid' models, or model composition has a correlation to fitting github pages,
> couldnt you deploy a few different URLs with broken mermaid diagrams and deploy individual models
> to attempt to solve them, or at least if its a single-call then to give you the solution and you
> and/or another model checks it"

So: does model tier predict success at fixing mermaid that must render on GitHub Pages, and is a
deploy-per-model harness worth building? I measured the model half locally and recommended one
fixture page rather than N deploys (section 5).

## 3. Two of my own errors, corrected (do not repeat them)

1. **`mmdc` was never broken.** An earlier conclusion of mine was that mmdc failed with
   `UnknownDiagramError: No diagram type detected` on *both* valid and invalid input. The cause was
   mine: I fed it fenced markdown, so it received a literal ` ```mermaid ` line. Re-run on a clean
   `.mmd`: broken → rc=1, `Parse error on line 2 … got 'PS'`; fixed → rc=0 and an 11,496 b PNG.
   Lesson: strip fences before handing a diagram to any CLI.
2. **Version skew was hiding the real question.** `mmdc` here is **12.2.0**, the repo's
   `detect_dead_mermaid.py` uses **mermaid 12.3.0**, and the ServiceNow Pages site pins **10.9.1**.
   A 12.x linter green-lights syntax 10.9.1 rejects. Every verdict below is graded at **10.9.1**,
   installed locally for the purpose.

## 4. The benchmark: method, results, artifacts, repro

### Method — ground truth is deterministic, not my opinion
- 5 broken diagrams, one per error class; each has a known minimal fix.
- 5 targets × 5 cases = **25 single calls**, temperature 0, one retry on timeout, 0 remaining call
  failures.
- An answer passes a case only if **mermaid 10.9.1 parses it** (jsdom) **and** every node id in the
  original still appears in the answer — so "delete the diagram" cannot score.
- Prompt asked for one fenced `mermaid` block only, no prose, keep every node and edge.

### Error classes
A unquoted parentheses in a label (the real 2026-11-12 ServiceNow break) · B smart quotes / em dash
from a paste · C unclosed `subgraph` · D diagram type not on line 1 · E pipe character inside a
plain label · plus F, Jekyll/Liquid `{{ }}`, which no mermaid parser can catch because it fails at
build time.

### Result matrix

| case | qwen2.5-coder:7b | qwen3:30b-a3b | FREE_CLOUD | FREE_NVIDIA | **PAID_MODE** |
|---|---|---|---|---|---|
| A unquoted parens | fail | **PASS** | fail | fail | **PASS** |
| B smart quotes | PASS | PASS | PASS | PASS | PASS |
| C unclosed subgraph | PASS | PASS | PASS | PASS | PASS |
| D type not line 1 | PASS | PASS | PASS | PASS | PASS |
| E pipe in label | fail | PASS | fail | PASS | PASS |
| **total** | 3/5 | **5/5** | 3/5 | 4/5 | **5/5** |
| wall clock, 5 cases | 18.0 s | **142.2 s** | 39.8 s | 36.2 s | **17.2 s** |

### The finding, in one line
Paid correlated with success **and** speed (5/5 in 17 s vs 3/5 in 40 s for the free cloud pool), but
the mechanism is **error localisation, not price**: on case A the free tiers and the 7B model all
rewrote lines that were never broken —

- `D{OK?}` → `D[OK?]` (free cloud)
- `D -->|No|` → `D -- No -->` (qwen2.5-coder:7b)
- `<br/>` → `<br>` (qwen3:30b, first attempt)

— while leaving `E[Synchronous REST<br/>RESTMessageV2.execute()]` with its unquoted parentheses
intact. The paid pool quoted the label: `E["Synchronous REST<br/>RESTMessageV2.execute()"]`.
Case A is the actual ServiceNow Pages break, so it is the case that matters.

### Caveats, stated honestly
- n=5 per target. Directional, not a leaderboard.
- The proxy reports its **alias** (`ULTRA_PAID_MODE`), not the backend that served the call, so
  results attribute to a *pool*, not a named model. Splitting that needs LiteLLM per-request logs.
- Grading at 10.9.1 is correct **for this site**; a fix valid at 10.9.1 may or may not satisfy 12.x.

### Artifacts (host-local, regenerable from this document)
```
/tmp/mm_bench/bench.py        harness; `--retry` reruns only non-passing cells
/tmp/mm_bench/validate.mjs    mermaid 10.9.1 parse via jsdom (10.x is ESM-only,
                              which is why a plain require() of it fails)
/tmp/mm_bench/corpus.md       the 5 broken/fixed pairs, per class, plus Jekyll class F
/tmp/mm_bench/results.json    every answer, served pool, latency, parse error
/tmp/mm_bench/vb.mmd vf.mmd   the two smoke inputs used to prove the validator
/tmp/mm_bench/node/           mermaid@10.9.1 + jsdom@24
```

### Repro
```bash
cd /tmp/mm_bench
node validate.mjs vb.mmd      # expect ok:false, "got 'PS'"
node validate.mjs vf.mmd      # expect ok:true
python3 bench.py              # full 25-call run
python3 bench.py --retry      # fill only the failures
```

## 5. Why one fixture page beats N deployed URLs

Local validation already reproduces the site verdict for grammar classes A–E, because it runs the
**same library at the same pinned version** (broken → `got 'PS'`; fixed → parse OK, kroki renders to
a 14 KB PNG). Deploying a page per model would test the same grammar through the same parser and add
no signal.

A Pages deploy adds exactly one class the parser cannot see: **the Jekyll shim and Liquid**.
- `{{ }}` in a label (case F) parses fine as mermaid and dies at **build** time.
- A block whose first line is not a diagram keyword (case D) parses fine, but the **site shim skips
  it** and renders raw code.

So the useful shape is **one fixture page, not one repo per model**: deploy the 5-block corpus once,
then per candidate answer push it into the fixture and re-check the rendered DOM for
`Syntax error in text`. 1 deploy + N commits instead of N deploys, and it isolates shim/Liquid
behaviour from grammar while leaving the model scoring above intact.

Not built yet, and deliberately not deployed: publishing to a Pages repo is an external action and
no fixture repo exists. It needs an explicit yes on creating `eltonaguiar/mermaid-fixture` or a
subfolder of an existing Pages site.

## 6. Pending, by owner

| # | Item | Owner | Note |
|---|---|---|---|
| 1 | Merge `feat/retired-provider-guard-2026-11-12` | peer (ollama-claude) | requested in SYNC 11; peer silent since 20:21:44Z on 2026-11-12 |
| 2 | Drop the 4-line `.ruflo/orchestrator.py` hunk from the scrub branch | me, **only if authorised** | new commit, never a rewrite; guard is not wired into any workflow — workflow files belong to the peer |
| 3 | Fixture Pages page + per-answer runner | owner decision | see section 5 |
| 4 | Optional: attribute paid-pool results to concrete models | me, no blocker | read LiteLLM per-request logs for the 5 paid calls |
| 5 | Mercury key revocation, OpenRouter rotation, FREELLM PR #1, Windows 8642 bind | owner | carried from section 1 |

## 7. Repo rules kept

No secret values printed. `dbpasses.txt` untouched. Only my own files published. No force-push, no
`reset --hard`, `trash` over `rm`. Fix records live in `updates/*.md`
(`updates/2026-11-12-retired-provider-guard.md` is the most recent before this one).
