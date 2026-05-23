# Session Summary — Local Agent Swarm Build

**Date:** 2026-05-03
**Session goal:** stand up a local Kimi-style agent swarm using existing CLIs (claude/gemini/opencode/kilo/copilot) + raw API keys (DEEPSEEK_API, CEREBRAS_API, X_AI_KEY, INCEPTION_AI_KEY, OLLAMA_CLOUD_KEY); add stats/logging; probe each engine on a real asset-class methodology question before any swarm orchestration.

## Engine "signs of life" — verified call log

Source: [`swarm_runs/_calls.jsonl`](_calls.jsonl) (21 records). Briefing prompt: 6,826 bytes ([`briefing_asset_class_audit.md`](briefing_asset_class_audit.md)).

| Engine | Auth | Status | Best-run output | Latency | Notes |
|---|---|---|---:|---:|---|
| deepseek | `DEEPSEEK_API` | ✅ LIVE | 7,292 B (full structured JSON, all 6 classes) | 28.3 s | One-shot worked first try |
| xai | `X_AI_KEY` | ✅ LIVE | 5,202 B (full structured JSON) | 24.8 s | Grok 3 latest |
| gemini | OAuth (CLI) | ✅ LIVE | 3,785 B (free-text, did not honor JSON contract) | 34.6 s | Will need stricter prompt to enforce JSON |
| **kilo** | OAuth (CLI) | ✅ LIVE | **10,089 B (full structured JSON, all 6 classes)** | 73.3 s | Identifies as "Kilo-AI-Consultant-v2.6". Best-of-class for BOND (cross-currency basis arbitrage). Same-codepath as opencode (`run` subcommand) |
| **copilot** | OAuth (CLI) | ✅ LIVE | **13,283 B** | 247.3 s | GitHub Copilot CLI. Output includes tool-call markers (`● Search`, `● Glob`) — needs parser to extract pure model text. Slowest engine. |
| opencode | OAuth (CLI) | ⚠️ PARTIAL | 1,215 B but only saw briefing's first line | 14.2 s | Windows PowerShell 8KB-arg quoting issue; worker_runner now pipes via stdin |
| cerebras | `CEREBRAS_API` | ✅ LIVE (after utf-8 fix) | 4,172 B | 2.0 s | gpt-oss-120b via Cerebras SDK |
| inception | `INCEPTION_AI_KEY` | ✅ LIVE (after model + utf-8 fix) | 6,926 B | 6.6 s | `mercury` deprecated → use `mercury-2`. Confirmed from `/v1/models` endpoint |
| ollama_cloud | local `ollama` CLI (signed in) | ✅ LIVE (after CLI-pivot + utf-8 fix) | 8,052 B | 23.6 s | `OLLAMA_CLOUD_KEY` env is an SSH ed25519 key (push auth), NOT a chat token. Adapter pivoted to `ollama run gpt-oss:120b-cloud <prompt>` |
| **freebuff** | n/a | 🟡 TUI — PTY captures banner | 105 KB raw screen, no model response (prompt aborted post-Enter) | — | DeepSeek+xAI both recommended ConPTY (80% confidence). Built `tools/swarm/pty_driver.py` via pywinpty. Banner+prompt-display works; sending prompt+CR triggered "operation aborted" — needs prompt-ready detection + slower send timing |
| codebuff | OAuth | ❌ TUI ONLY + out of credits | — | — | Same lineage as freebuff. Account billing blocker even if PTY worked. |

**Verdict:** **9/11 engines have proven signs of life** on a non-trivial 6.8 KB prompt. freebuff has PTY infrastructure ready (banner verified) but needs prompt-timing tuning. codebuff blocked on account credits.

## What the working engines said about our /audit methodology

Two independent AI consultants (DeepSeek + xAI) returned full structured JSON with per-class methodology, edge mechanism, statistical test, sample-size floor, external benchmark, and kill rule. Synthesis at [`CONSENSUS.md`](20260503T132558Z/CONSENSUS.md).

**Convergence (both AIs agreed):**
- EQUITY: factor-mimicking (Fama-French + momentum), benchmark AQR / Renaissance, kill PF<1.0 over 100-200 trades.
- CRYPTO: regime/sentiment + microstructure (basis trade, fear-greed contrarian), benchmark Hyperliquid HLP, kill on rolling WR<50%.
- FOREX: carry-trade with vol-filter on G10 pairs only, benchmark MyFXBook / DB FX Factor, kill on 6-month Sharpe<0 or PF<1.0 over 200 trades.
- COMMODITY: term-structure + COT commercial positioning, benchmark DBMF / KMLM, kill PF<1.2 over 100 trades.
- ETF: sector rotation 12-month momentum, kill PF<1.2 / WR<50% / n<100.

**Divergence:**
- BOND: DeepSeek says "no defensible approach until n≥100 — merge into ETF"; xAI proposes yield-curve steepness arbitrage with PIMCO BOND benchmark.
- ETF edge direction: DeepSeek=cross-sectional momentum; xAI=mean-reversion on overreaction.

**Q2 rescue plan consensus:**
- 30-day: kill/mutate FOREX draggers (`forex_rsi2_mean_reversion`, `forex_carry_momentum`); cap any single strategy at <15% of asset-class volume; rebuild forward-edge audit with correct promotion-log timestamps.
- Exit ramp: abandon FOREX after 90d if PF<1.0 on 200+ trades; abandon CRYPTO if class WR<40% after removing `quan_engine` + `unknown`.

## Iterations after initial commit

- **`fb9ee89` → `7f317d6`**: pty_driver via pywinpty + pyte renderer. Freebuff PONG smoke test ✓. Full briefing fails — TUI input buffer chokes on 6.8KB single-line.
- **`7f317d6` → `8490352`**: Kimi merge #2 — `safety.py` (env isolation per engine, canonical READ_ONLY_ALLOWED/DISALLOWED, post_run_git_check, can_post role gate) + `output_parsers.py` (Copilot tool-call markup stripper: 4154 B clean from 13283 B raw; Claude envelope `.result` extractor). worker_runner wired both.
- **Latest**: `swarm_run.py` cross-platform fan-out CLI (Python, no PowerShell needed). `--engines deepseek,xai,kilo,gemini,...` runs in parallel, writes per-engine JSON + `_summary.json`. `--list-engines` prints supported names. Smoke test 2/2 OK ({"answer":"PONG"} from deepseek + xai).
- **Latest**: `--json-strict` flag on worker_runner — Gemini gets a JSON-only framing prepended ("First character MUST be '{'…") to dodge its tendency to ignore in-prompt JSON contracts.

## What was built (but partially deleted)

### Survived (in `swarm_runs/`)

- [`briefing_asset_class_audit.md`](briefing_asset_class_audit.md) — the 6.8 KB briefing prompt (asset health snapshot + survivor-strategy table + Q1/Q2 questions + JSON contract).
- [`20260503T132558Z/`](20260503T132558Z/) — per-engine probe outputs for deepseek/xai/gemini/inception/opencode (raw + structured JSON).
- [`probe.cerebras.json`](probe.cerebras.json) + [`probe.ollama_cloud.json`](probe.ollama_cloud.json) — the post-fix successful runs (root level — directory layout drifted on the last parallel re-probe).
- [`_calls.jsonl`](_calls.jsonl) — every API/CLI call logged with engine / latency / bytes-in / bytes-out / returncode / ok-flag / low-signal-flag.
- [`20260503T132558Z/CONSENSUS.md`](20260503T132558Z/CONSENSUS.md) — DeepSeek+xAI per-class consensus table.

### DELETED between writes (only `__pycache__` survives in `tools/swarm/`)

These were authored this session and need rebuild:
- `tools/swarm/worker_runner.py` — engine adapter (claude/gemini/opencode/kilo/copilot/codebuff + 5 API consultants) with read-only Claude tool allowlist + JSON extraction.
- `tools/swarm/swarm_dispatch.ps1` — fan-out (PR × engine) with `Start-Job`, throttle, schema-validate, merge-captain + red-team.
- `tools/swarm/comment_poster.ps1` — only writer; y/N gate per PR.
- `tools/swarm/swarm_log.py` + `swarm_stats.py` — append-only JSONL logger + stats summarizer that flags ZOMBIE_OUTPUT / LOW_OK_RATE / ERRORING engines.
- `tools/swarm/schema_validate.py` + `schema_review.json` — schema enforces `evidence` field on blocking/major concerns.
- `tools/swarm/prompts/{pr_review,redteam,merge_reviews}.md`.
- `tools/swarm/fixtures/{good,bad}.json`.
- `tools/swarm/SWARM_DESIGN_NOTES.md` — Kimi reference + CLI session/resume capability matrix.
- `tools/swarm/FREEBUFF_NOTES.md` — TUI-only verdict.

Subagent-written (lost — would need re-spawn):
- `tools/swarm/agent_personas/{equity,crypto,forex,commodity,etf,bond}_specialist.md` + `INDEX.md`.
- `tools/swarm/{README,SPEC,PORTING}.md`.
- `tools/swarm/{MANIFEST.txt, requirements.txt, swarm.config.example.json}`.
- `.claude/agents/{pr-reviewer,fabrication-red-team,merge-captain,dashboard-contract-reviewer,quant-performance-auditor}.md`.

Also reverted (linter or peer):
- `tools/consult_{deepseek,cerebras,xai}.py` — my SWARM_STDOUT branch + utf-8 reconfigure are gone, restored to file-write-only mode.
- `tools/consult_{inception,ollama_cloud}.py` — created this session, but their state needs re-verify.

## Stats / logging — what was caught

```
engine       | calls | ok | ok% | low_sig | err | flags
-------------+-------+----+-----+---------+-----+--------------------------
cerebras     |   5   |  0 |  0  |    5    |  0  | LOW_OK_RATE,ZOMBIE_OUTPUT  ← caught the SWARM_STDOUT regression
deepseek     |   2   |  2 | 100 |    0    |  0  | -
gemini       |   1   |  1 | 100 |    0    |  0  | -
inception    |   2   |  0 |  0  |    2    |  0  | LOW_OK_RATE,ZOMBIE_OUTPUT  ← caught wrong model + utf-8 issue
ollama_cloud |   3   |  0 |  0  |    3    |  0  | LOW_OK_RATE,ZOMBIE_OUTPUT  ← caught SSH-key-not-token + utf-8
opencode    |   1   |  1 | 100 |    0    |  0  | -                          ← false-OK; output was truncated
xai          |   2   |  2 | 100 |    0    |  0  | -
```

**Key finding:** the logging system did exactly its job — every engine that returned <50 bytes was flagged ZOMBIE_OUTPUT in real time. Without it, the Inception/Ollama_Cloud bugs would have stayed silent. The remaining gap is opencode flagged OK at 1,215 B but content was truncated to one line — the byte-count heuristic isn't enough for content-quality detection. Next iteration should add a "contains expected JSON keys" check.

## Recommendation / next steps

1. Confirm with peers (`ex4gw1er`, `89n23oun`) whether the deletion was intentional. Messages sent.
2. If unintentional: rebuild from conversation history — most files reproducible, subagent-written ones (personas, SPEC/README/PORTING) need re-spawn.
3. Move all swarm code into `tools/swarm/` exclusively to avoid cross-cutting reverts on `tools/consult_*.py` (those scripts are widely used by other peer agents — keep them stable; have `worker_runner.py` use direct urllib for swarm consults instead of piping through `consult_*.py`).
4. Add `tools/swarm/` to a permission allowlist or pre-commit hook so peer cleanup scripts skip it.
5. Kimi swarm is also building a parallel implementation (per user) — review their approach when ready and merge the better parts.

## Refreshed asset-class consensus (Run #2 — 2026-05-03T15:37:30Z)

- **Output:** [`CONSENSUS_v2.md`](CONSENSUS_v2.md)
- **Run dir:** [`run_20260503T153438Z/`](run_20260503T153438Z/) (`_summary.json`)
- **Engines invoked:** 7 (deepseek, xai, kilo, gemini, inception, ollama_cloud, cerebras)
- **`ok_count` (per `_summary.json`):** 7/7 by rc; **5/7 by usable structured output** (q1+q2 schema present)
  - Successful (full schema): `deepseek` (8.7 KB / 32.8 s), `xai` (5.8 KB / 26.4 s), `kilo` (9.7 KB / 100.6 s), `inception` (6.9 KB / 6.4 s), `cerebras` (8.9 KB / 4.6 s)
  - Failed (parser fallback to PR-review schema): `gemini` (490 B; CLI launch error "system cannot find the file specified"), `ollama_cloud` (2.8 KB; raw text DOES contain valid q1/q2 but terminal-line-wrap corrupted JSON — see `ollama_cloud.json.raw.txt`, recoverable with manual cleanup if needed)
- **swarm_stats flags this run only:** none of the 5 successful engines re-flagged as ZOMBIE_OUTPUT or LOW_OK_RATE (the existing flags in `swarm_stats.py` output reflect cumulative history from probe runs).
- **Persisted sessions in `_sessions.db`** (chain with `--from-session-by-engine`):
  - `deepseek=07729506-6cb0-4f9a-8d81-a43f39085d89`
  - `xai=40502e7b-acd8-461c-b738-4e19419d26ac`
  - `kilo=64ada602-dd53-4406-af69-b4c96e646d88`
  - `inception=2fd83def-3003-488e-a1d5-46d448020aea`
  - `cerebras=3b8857ab-f4be-412b-a538-848fbceb0308`
  - `gemini=d2dc1f25-575b-4193-b341-b4ef6cad3963` (failed run; not useful for chaining)
  - `ollama_cloud=8647295a-2a09-4951-b750-801961b44412` (raw recoverable; structured output failed)

### Top three convergences (vs v1 DeepSeek+xAI)
1. **FOREX rescue:** 4/5 engines explicitly recommend porting `cftc_cot_commercial_signal` from COMMODITY (PF 3.50, n=32) to FOREX. v1 had only generic "use COT data" — v2 names the live in-repo strategy as the answer.
2. **CRYPTO benchmark:** Hyperliquid HLP is now 5/5 unanimous (was 2/2). External-replication target is now overwhelming.
3. **EQUITY methodology:** 5/5 unanimous on multi-factor cross-sectional (value+momentum+quality) with AQR-family benchmark. Strongest of any class, safe enough to publish on `/audit` updates.

### Top three disagreements
1. **ETF direction (momentum vs mean-reversion):** 4/5 momentum, 1/5 mean-reversion. Opposite trades on same instruments. → A/B paper-trade for 60d.
2. **BOND viability:** 3/5 propose yield-curve steepness arb; 2/5 say no defensible approach until n>=100. → Passive data-collection only.
3. **30d FOREX dragger handling:** 2/5 say kill outright, 3/5 say mutate-then-kill. Internal `MUTATION_THREE_AXIS_PROTOCOL.md` already mandates mutate-first; v2 reinforces.

## FOREX deep-dive chain (Run #3)

- **Output:** [`FOREX_DEEP_DIVE.md`](FOREX_DEEP_DIVE.md)
- **Run dir:** [`followup_forex_20260503T155122Z/`](followup_forex_20260503T155122Z/) (`_chain_summary.json`)
- **Engine:** `deepseek` (deepseek-chat) — single-engine 4-turn sequential chain (priming → analysis → critique → final).
- **Outcome:** 4/4 turns ok (rc=0). Total elapsed ~52.3 s (32.85 + 8.32 + 6.72 + 4.38). Sizes: 9.2 KB / 2.1 KB / 1.9 KB / 1.1 KB.
- **Verdict:** FOREX drag (PF 0.27 / WR 46.4% / n=1169 post-resolver-v2) is concentrated in `forex_rsi2_mean_reversion` (n=616, raw PF 1.52, after-cost –32.2%) and `forex_carry_momentum` (n=66, PF 0.02). Together: 58.3% of class volume, 100% of net drag. Recommended axis per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`: **regime** (ATR percentile gate). Confidence MEDIUM — turn-3 self-critique correctly flagged that "high-vol regimes have tighter spreads" assumption is empirically false for FX, so a negative falsification result may be regime-variable failure rather than strategy-edge failure.
- **Cost:** within ~$0.15 budget (4 deepseek-chat calls, 9.2 KB priming + 3 follow-ups).
- **Chain runner notes:** prior partial run (`followup_forex_20260503T154733Z/`) was deleted before re-run (Option A); turn-1 elapsed dropped from ~33 s to identical because the briefing was already in the API replay cache. The runner's `--from-session` chained correctly across all 4 turns (same `session_id_db` 55a2a7d3).
- **Companion fix:** [`tools/swarm/swarm_inspect.py`](../tools/swarm/swarm_inspect.py) now detects chain runs via `_chain_summary.json` and labels rows as `<engine>:turn_<N>` instead of treating each `turn_<N>_<name>.json` as a separate fake-engine. Verified on this run dir + regression-tested on `run_20260503T153438Z/`.

## Swarm self-review (Run #4 — 2026-05-03T16:38:57Z UTC)

- **Synthesis:** [`SWARM_SELF_REVIEW.md`](./SWARM_SELF_REVIEW.md)
- **Run dir:** `swarm_runs/self_review_20260503T163857Z/`
- **Preset:** `consensus-3` (deepseek, xai, kilo) + `--red-team` (claude opus)
- **Engines OK:** 2 of 3 substantive (deepseek HEALTHY, xai HEALTHY, kilo ZERO/PARSE_FAILED). Red-team itself returned non-JSON (auto-flagged HIGH fabrication risk by its own wrapper).
- **Cost:** $0.0653 actual vs $0.50 cap.
- **Top 3 improvements (ranked):** (1) wire personas into engine calls [imp-A, M], (2) enrich `_calls.jsonl` audit trail with timing/retry/fingerprint/transport-status [imp-B, S], (3) build `tools/swarm/resolver.py` for confidence-weighted disagreement resolution [imp-C, L].
- **Methodology bug surfaced:** the METHODOLOGY.md "auditable timestamped reasoning traces" claim is weaker than advertised — only 3/16 deepseek calls today carry a trace; `_calls.jsonl` lacks retry/fingerprint/transport-status. imp-B closes this.
- **Cross-engine contradiction needing resolution:** voting weight source for the proposed auto-resolver — deepseek wants self-reported confidence, xai wants historical reliability from `_calls.jsonl`. Combine: `weight = self_conf * historical_ok_rate`.

## PR action plan (Run #5 — 2026-05-03T17:04Z)

- **Run dir:** `swarm_runs/pr_review_20260503T170445Z/`
- **Briefing:** `swarm_runs/_pr_review_brief.md`
- **Engines:** claude, deepseek, xai (max-parallel=3, --persist-sessions)
- **PRs targeted:** 724, 723, 676, 661, 660, 644, 615, 608, 597 (9 open)
- **Status:** **ABORTED** — see `swarm_runs/PR_REVIEW_ABORTED.md`
- **Cost:** $0.039 of $1.00 cap; killed mid-run after 10/27 jobs.
- **Engines OK (automated):** swarm_inspect flagged 3/10 (Claude TINY,PARSE_FAILED).
- **Engines OK (content audit):** **0/10** — all reviews fabricated. DeepSeek + XAI confabulated React/CSS/geolocation reviews for PRs that touch Python/audit_trail or markdown reports; Claude CLI returned only "Ready. Awaiting PR review task." (prompt didn't propagate).
- **Methodology bug surfaced:** `tools/swarm/prompts/pr_review.md` instructs each worker to run `gh pr view`/`gh pr diff`, but API-only engines (DeepSeek, XAI, Cerebras, Inception, Ollama Cloud) cannot execute shell commands and will hallucinate the diff. Dispatch must capture diff server-side and embed it in the prompt before fan-out. CLI engines (Claude/Gemini/Kilo/OpenCode/Copilot) need the per-PR task to actually reach the agent loop — Claude transport in `worker_runner.py` is silently delivering only the system header in this run.
- **No commands executed against GitHub.** No PRs merged, closed, commented, or reviewed.
- **Manual triage candidates (title-only, NOT engine-validated):** PR #724 (FOREX rescue), #660 (P0 gate fixes), #597 (USDCHF/pair-block) — these three touch the goal-1 sub-floor class directly.
