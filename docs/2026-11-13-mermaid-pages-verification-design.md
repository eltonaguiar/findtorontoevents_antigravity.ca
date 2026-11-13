# Design specification — proving mermaid fixes render on GitHub Pages, and attributing model results

**Status:** proposal, not implemented. Nothing in Components A or B has been built or deployed.
**Date:** 2026-11-13. **Author:** Buffy (Freebuff CLI, GX10/GB10 host).
**Companion records:** `updates/2026-11-13-freebuff-mermaid-bench-handoff.md` (what was measured and
why), `docs/2026-11-13-mermaid-followups-implementation-pack.md` (the runnable artifacts: attribution
script, fixture page and runner, guard CI patch, cleanup runbook, completeness matrix),
`/tmp/freebuff.txt` on the host (coordination log; `SYNC 14` indexes all three).
**Repo rules obeyed:** no secret values, `dbpasses.txt` untouched, no force-push, own files only.

---

## 0. What this document is, and what it is not

It is the end-to-end design for the three follow-ups left after the benchmark, plus the cleanup work
around the Inception/Mercury sunset, each with its own post-validation gate, the items that cannot
be actioned without more information, and a **decision log of what I deliberately skipped or held**.

It is not a claim that any of it works. Where something was measured, the number is cited with its
source. Where it is design, it is labelled as design.

Two standing facts that shape everything below:

1. **The site pins mermaid 10.9.1; the local tooling is 12.x.** `mmdc` is 12.2.0, the repo's
   `detect_dead_mermaid.py` uses 12.3.0. A 12.x green light is not evidence about the site. Any
   validator in this design must run 10.9.1 or it is measuring the wrong thing.
2. **`ULTRA_PAID_MODE` is not a model.** See 1.1 — this is the correction that makes Component A
   necessary rather than cosmetic.

---

## 1. Problem statement

Two questions remain open after the 2026-11-13 benchmark:

- **Q1 (attribution):** the benchmark scored *router aliases*. We do not know which concrete model
  answered, or whether the "paid" 5/5 came from a paid deployment at all.
- **Q2 (site fidelity):** local validation reproduces mermaid's grammar verdict, but two classes only
  fail on a real GitHub Pages deploy — the Jekyll/Liquid layer, and the site's own shim rule that
  skips a block whose first line is not a diagram keyword.

### 1.1 Why the alias is not a model — config evidence

From `litellm_config.yaml` (read, not inferred):

```yaml
- {model_name: ULTRA_PAID_MODE, litellm_params:
    {model: openai/mimo-v2.5-pro, api_key: os.environ/XIAOMI_MIMO_TOKEN_PLAN,
     api_base: https://token-plan-sgp.xiaomimimo.com/v1}}
...
- ULTRA_PAID_MODE: ["ULTRA_PAID_MODE_LARGE", "ULTRA_FREE_CLOUD_LARGE", "ULTRA_FREE_CLOUD"]
```

So a request to `ULTRA_PAID_MODE` can be served by **mimo-v2.5-pro, or by a free pool through the
fallback chain**, and `/tmp/litellm_cooldown_state.json` shows the router cooling deployments
between calls. The response body's `model` field echoes the alias, which is why the benchmark table
says "paid pool" and not "paid model".

**Consequence, stated plainly:** the 5/5 paid result may have been produced by free deployments. The
benchmark's paid-vs-free contrast is therefore **not yet established** — only the alias-level result
is. That is the honest reading, and it is why Component A comes first.

---

## 2. Ground truth ladder (shared by both components)

Each level is strictly stronger and strictly more expensive. A result is only as trustworthy as the
highest level it passed.

| L | Check | Cost | Catches |
|---|---|---|---|
| L0 | `mermaid.parse()` at 10.9.1 (jsdom) | ~0.4 s | grammar, exact parser error |
| L1 | node/edge preservation vs the original | free | "fixed" answers that silently delete structure |
| L2 | render at 10.9.1 via kroki | ~1 s, network | parse-ok-but-render-fail |
| L3 | headless render in a real DOM at 10.9.1 | ~3 s | layout/DOM errors the parser misses |
| L4 | the answer rendered on a live GitHub Pages fixture | minutes (build queue) | shim skip, CDN/version drift, base-path |
| L5 | Liquid/Jekyll build behaviour (`{{ }}`, raw tags) | minutes | the only class no parser can see |

The benchmark used L0 + L1. Nothing in it used L2–L5.

---

## 3. Component A — per-model attribution

**Goal:** replace "the paid pool scored 5/5" with "model X scored p/n, served by deployment Y", for
every call, with the fallback rate visible.

### 3.1 Option comparison

| # | Method | Touches the shared proxy? | Sees fallbacks? | Effort |
|---|---|---|---|---|
| A1 | **Direct provider calls** (bypass the router; pin one model per provider) | no | n/a — you *are* the routing | low |
| A2 | `litellm_settings.success_callback: ["jsonl"]` + a JSONL path | **yes** (config edit + restart) | yes | medium |
| A3 | `--detailed_debug` / verbose stdout, then grep | yes (restart) | yes | medium, noisy, logs payloads |
| A4 | `/spend/logs` admin endpoint | no | yes | blocked unless a master key + DB are configured — unverified here |

**Recommendation: A1 first, A2 only if the router path itself must be characterised.**

Rationale: A1 answers the scientific question ("which models fix mermaid 10.9.1?") without touching a
proxy that Roo, Kilo, Copilot and every other agent on this host depend on. A restart has a
60–180 s discovery window on this box and is exactly the operation that has produced random-port
ghosts before. The bench harness already separates transport from scoring, so swapping the call layer
for direct provider calls is a small change.

### 3.2 A1 — implementation

1. Reuse the provider table from `tools/…/consult-multi` conventions: keys read from `~/dbpasses.txt`
   by name only; **never** echo a value; never write a key into a repo file.
2. Targets: at minimum `nvidia` deepseek-v4-pro, `groq` llama-3.3-70b, `cerebras` qwen, `gemini`
   flash, `openrouter` (the id the site's own OpenRouter key would reach), and Xiaomi `mimo-v2.5-pro`
   via its token-plan endpoint (the deployment behind `ULTRA_PAID_MODE`).
3. Keep the same 5 cases, same prompt, same temperature 0, same grader (L0 + L1).
4. Raise N to 10 per case per model — 5 gives a 1/5 granularity and cannot separate 3/5 from 4/5.
5. Record `provider`, `model_id`, `attempt`, `latency`, `answer`, `verdict`, `parser_error`.

### 3.3 A2 — implementation, if the router must be measured

```yaml
litellm_settings:
  drop_params: true
  set_verbose: false
  success_callback: ["jsonl"]          # temporary, attribution run only
  turn_off_message_logging: true       # keep prompts out of the log
```
plus `JSONL_LOGS_PATH=/tmp/litellm_attrib` in the unit environment.

Restart discipline (from the `litellm-port-4000-debug` skill, do not improvise):
`systemctl --user restart litellm-4000.service`, then **wait 60–180 s** before concluding anything;
never wrap the launcher in `timeout` — that kills the proxy it just started; never start a second
proxy while 4000 is bound.

Then parse the JSONL for one record per call and read the deployment field, not the alias.

### 3.4 Post-validation for Component A

| Gate | Assertion | How |
|---|---|---|
| A-G1 | every benchmark call has a concrete deployment name | 100% of JSONL records carry a model/deployment field; zero nulls |
| A-G2 | fallback rate is known, not guessed | count records where the served deployment ≠ the primary for that alias |
| A-G3 | the matrix is recomputed and the old one is superseded, not silently edited | new `results_attrib.json` + a diff table in the record |
| A-G4 | a known-good control still passes | rerun case B (smart quotes) on one model; must pass |
| A-G5 | the proxy still serves after any config edit | `curl :4000/v1/models` → 200, count unchanged, and one chat completion returns |

If A-G1 cannot reach 100%, the alias-level table stands and the attribution claim is withdrawn — not
downgraded in wording but removed.

### 3.5 Risks

- Config edit on a shared proxy affects every agent on the host → A1 avoids it entirely.
- JSONL grows without bound; prompts may contain user text → `turn_off_message_logging` + a dated path
  under `/tmp`, deleted after the run.
- Provider free tiers rate-limit; a 429 must be recorded as excluded, not scored as a model failure
  (the benchmark already learned this the hard way: timeouts read as model failure until retried).

---

## 4. Component B — the GitHub Pages fixture harness

**Goal:** make L4/L5 real: prove an answer renders **on GitHub Pages through the site's own shim**,
not just through a parser.

### 4.1 Why one page, not one deploy per model

Local 10.9.1 validation already reproduces the site's grammar verdict — measured: broken block → rc=1
with `got 'PS'`; fixed block → rc=0 and a 14 KB kroki render. Deploying a page per model re-tests that
same grammar through the same parser. The deploy adds exactly two things the parser cannot see (L4/L5
above), and both are properties of the **page**, not of the model. So: one page, many candidate answer
sets.

### 4.2 Layout

```
mermaid-fixture/
  index.html                 # pinned mermaid 10.9.1 + an explicit copy of the site shim rule
  cases/                     # A..F source blocks, the ground-truth corpus
  answers/<run>/<case>.mmd   # one candidate answer per case, written by the runner
  results/<run>.json         # what the page reported, as fetched by the runner
  runner.py                  # commit an answer set, wait for the build, read the DOM verdict
  README.md
```

Pages source: the repo root or `/docs` on the default branch of the fixture repo — a **separate,
throwaway repo** (`eltonaguiar/mermaid-fixture`) is preferred over a subfolder of a live site, so a
broken candidate can never reach a page anyone reads.

### 4.3 What the page must replicate (this is the point)

`index.html` must be *the site's* rendering path, not a generic mermaid demo:

1. load `https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js` — the pinned version;
2. implement the shim rule explicitly: **if the block's first non-blank line is not a diagram
   keyword (`flowchart`, `graph`, `sequenceDiagram`, `classDiagram`, `stateDiagram-v2`, `erDiagram`,
   `gantt`, `pie`, `journey`, `mindmap`, `timeline`), the block is skipped and left as raw text** —
   because that is what the site does, and case D exists to prove the skip happens;
3. wrap blocks in `{% raw %}`-equivalent protection for the Liquid class so a `{{ }}` answer is
   tested at build time, which is the only place it fails;
4. expose the verdict machine-readably:
   ```js
   window.__FIXTURE__ = [{case:"A", shim:"ran"|"skipped", rendered:true|false, error:"…"}]
   ```
5. never cache-bust by query string on the `.mmd` fetch — Pages serves the built HTML, so a rebuild is
   what updates the answer.

### 4.4 Runner loop

```
for each answer-set:
  write answers/<run>/<case>.mmd
  commit (ONE commit for the whole set) and push
  poll GET /repos/{o}/{r}/pages/builds/latest until status == "built" and the commit matches
  page = playwright.chromium.launch().new_page(); goto fixture URL with cache disabled
  verdict = page.evaluate("window.__FIXTURE__")
  score  = per case: shim == "ran" AND rendered == true
  append to results/<run>.json ; print a row
```

Deploy math: one commit per **answer set** (all 5 cases at once), so a 5-model run is 5 commits and
**1 initial deploy**, not 25. GitHub Pages has a soft limit of ~10 builds/hour for a repo — that is the
real constraint, and it is why the runner batches by set and why the fixture is a dedicated repo.

### 4.5 Post-validation for Component B

| Gate | Assertion | How |
|---|---|---|
| B-G1 | negative control fails | the deliberately broken A-block must report `rendered:false` with a mermaid error — if it renders, the harness is not actually parsing and every green is meaningless |
| B-G2 | positive control passes | the quoted-label fixed block must report `rendered:true` |
| B-G3 | shim rule is live, not assumed | case D must report `shim:"skipped"` and `rendered:false` even though L0 says the block parses — this is the one check that proves the fixture is testing the site shim |
| B-G4 | Liquid class is exercised | case F must fail without raw tags and pass with them, at build level |
| B-G5 | parity | for A/B/C/E the L0 verdict and the L4 verdict agree; any disagreement is investigated before the harness is trusted |
| B-G6 | version pin is real | fetch the page and assert the loaded mermaid version string is `10.9.1` — a CDN change must not silently move the target |

### 4.6 Failure modes to design around

- **Build queue latency** (seconds to minutes) → poll the builds API, never `sleep 30` and hope.
- **Pages caching** → disable cache in the Playwright context; assert the commit sha the page reports.
- **Private repo + Pages** → needs a paid plan; use a public throwaway repo or skip the class.
- **Jekyll excludes** → `_`-prefixed paths are not published; keep `answers/` published deliberately.
- **A green page with an empty `__FIXTURE__`** → treat as harness failure, never as a pass; B-G1 exists
  to catch exactly this.

---

## 5. Component C — Inception Labs / Mercury key cleanup

Vendor sunset **2026-12-28**. A revoked key is not a code change, so this is sequenced separately from
the scrub.

### 5.1 State verified 2026-11-13

| Fact | Value | How |
|---|---|---|
| Retired-provider guard | rc=0, clean | `python3 tools/check_retired_providers.py --quiet` |
| `~/dbpasses.txt` | 478 lines, **1** line mentions Inception, **0** mention Mercury | counts only, values never printed |
| Scrub branch | `scrub/inception-mercury-2026-11-12` @ `2c08a4bb1433`, 37 files | earlier session record |
| Guard branch | `feat/retired-provider-guard-2026-11-12` @ `58baed09b6aa`, merge requested in `SYNC 11` | `/tmp/freebuff.txt` |
| Known plaintext copy | `eltonaguiar/hermesbackup` (private) — revocation must precede its scrub | earlier session record |

### 5.2 Why the local file is not the target

The owner's instruction was explicit: **do not delete `dbpasses.txt`, the Inception key stays.** So
cleanup means **revoke, rotate, and stop depending** — not file surgery. The risk that follows: other
tooling on this host may enumerate that file and will start returning 401s once the vendor turns the
key off. That is a **consumer audit**, and it is action I can do without the owner.

### 5.3 Plan

| Step | Owner | Action | Post-validation |
|---|---|---|---|
| C1 | me | consumer audit: every code path that would attempt the Inception key | list is explicit; each entry either has a guard or is documented as expected-to-fail |
| C2 | owner | revoke the key in the vendor dashboard | vendor returns 401 for a known request |
| C3 | owner | rotate the OpenRouter key (it shared blast radius) | proxy still serves; old key rejected |
| C4 | me, after C2 | remove the plaintext copy from `hermesbackup` (private repo) | `grep` returns 0 in the repo and in history-reachable files; documented |
| C5 | peer/owner | merge the scrub branch | guard rc=0 on `main`; 0 live references |
| C6 | peer | wire the guard into CI (4-line step; workflow files are the peer's) | a synthetic violation fails the job; a clean tree passes |

Ordering is not negotiable: **C2 before C4**, because scrubbing a private repo does not revoke access
that already exists.

### 5.4 What I can do without asking

C1 (audit), a draft patch for C6 for the peer to apply, and the C4 check. C2/C3/C5 are outside my
authority; C5 in particular is a merge decision, not a technical one.

---

## 6. Items that need more information before I action them

Each row names the question, why it blocks, and what I can do in the meantime.

| # | Question | Why it blocks | Meanwhile |
|---|---|---|---|
| 1 | Fixture repo name + visibility (`eltonaguiar/mermaid-fixture`, public?) | a Pages deploy is an external publish; private Pages needs a paid plan | the page template and runner can be written and tested against `file://` / local server |
| 2 | May I enable a JSONL callback on the shared proxy, or is direct-provider only acceptable? | A2 restarts a proxy every agent on this host uses | A1 needs no permission — start there |
| 3 | What counts as "paid" for this comparison — the Xiaomi token-plan deployment, or any metered provider? | the alias mixes a metered primary with free fallbacks (1.1) | report per-model, let the owner draw the tier line |
| 4 | May prompts be logged during the attribution run? | attribution via A2/A3 can persist prompt text | A1 logs only answers; `turn_off_message_logging` otherwise |
| 5 | Which agent owns the workflow files for the guard step (C6)? | `AGENTS.md`/`SYNC` convention says the peer owns them | deliver a ready-to-paste 4-line step |
| 6 | Merge order: scrub now, or after revocation (C2)? | earlier note says revocation must precede the plaintext scrub | nothing merged from my side either way |
| 7 | Is a `/spend/logs` admin key + DB configured for this proxy? | decides whether A4 is available | unverified; A1/A2 do not depend on it |
| 8 | Appetite for ~10 Pages builds/hour on a fixture repo | sets the batch size per run | batch per answer-set, 5 commits per run |

---

## 7. Decision log — what I skipped or held, and why

Recorded so a successor does not re-litigate settled calls.

| Decision | Choice | Reason | Reversible? |
|---|---|---|---|
| Per-model Pages URLs (the owner's original phrasing) | **skipped** — one fixture page instead | grammar verdict is already reproduced locally; a deploy adds only shim/Liquid; N deploys cost N× build queue for no extra signal | yes, but no reason found |
| `mmdc` as the validator | **skipped** | it is 12.2.0 here, the site pins 10.9.1 — it green-lights syntax the site rejects | yes, if a 10.9.1-installed mmdc is wanted |
| Grading with the repo's `detect_dead_mermaid.py` (12.3.0) | **skipped for scoring**, kept for diagnosis | same version skew | yes |
| Wiring the retired-provider guard into CI | **held** | workflow files belong to the peer; guard shipped as a standalone tool + documented 4-line step | yes — peer applies the patch |
| Dropping the 4-line `.ruflo/orchestrator.py` hunk from the scrub branch | **held** | needs explicit authorisation; would be a new commit, never a rewrite | yes |
| Deleting/editing `dbpasses.txt` | **skipped** | owner instruction: the Inception key stays | n/a |
| Force-updating my own docs branch to add a second file | **skipped** | an append commit is non-destructive; force-push is banned without asking | n/a |
| Merging any of the five branches to `main` | **held** | merge is an owner/peer call, not a technical one | yes |
| Probing Hermes `ask` further | **skipped** | `192.168.2.32:8642` refuses in 0 ms; no `API_SERVER_KEY` — nothing to probe without the owner | yes |
| Upgrading the NVIDIA driver to raise throughput | **rejected** | permanent veto in `docs/HARDWARE_DRIVER_UPGRADE_VETO.md`; downside is an unbootable GB10 | no |
| Running `check_active_picks.py` / `smart_picks_engine.py` | **skipped** | `AGENTS.md` veto — too noisy, side effects | owner may ask |
| Re-running the benchmark at N=10 now | **held** | it should happen together with attribution (Component A), otherwise we produce a second un-attributed table | yes |
| Treating free-tier 401/429s as model failures | **corrected, not repeated** | the first run scored timeouts as failures; the retry pass changed 3 results | n/a |

---

## 8. Sequencing

```
A1 (attribution, direct providers)  ──►  N=10 rerun  ──►  supersede the alias table
B-local (page + runner on file://)  ──►  needs repo yes ──►  B deploy + gates B-G1..G6
C1 (consumer audit) ──┐
                      ├─► C2 revoke ──► C4 hermesbackup cleanup ──► C5 merge scrub ──► C6 CI guard
C6 draft patch ───────┘
```
Nothing in A or B blocks C; C2 is a date-driven deadline (2026-12-28) and should not be queued behind
a benchmark.

**Ready to execute:** `docs/2026-11-13-mermaid-followups-implementation-pack.md` carries the code for
Part A1 (`attribute_models.py` + `targets.json`), the fixture `index.html` and `runner.py` with its
local preflight, the 4-line guard CI insert with its three false-positive tests, and the C1…C6
runbook. This spec is the *why*; that pack is the *how*, and nothing in it has been run.

---

## 9. Appendix — commands

```bash
# L0/L1 grader (pinned 10.9.1)
cd /tmp/mm_bench && node validate.mjs vb.mmd     # expect ok:false, "got 'PS'"
node validate.mjs vf.mmd                         # expect ok:true

# the existing benchmark
python3 bench.py ; python3 bench.py --retry

# proxy health before/after any config change
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:4000/v1/models
systemctl --user is-active litellm-4000.service

# retired-provider guard
python3 tools/check_retired_providers.py --quiet ; echo rc=$?

# Pages build state
gh api repos/eltonaguiar/<fixture>/pages/builds/latest --jq '.status,.commit'
```
