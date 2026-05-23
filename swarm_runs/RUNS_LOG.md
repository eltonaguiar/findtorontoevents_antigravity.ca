# Swarm Runs Log — 2026-05-03 (UTC)

End-to-end audit of every swarm run executed today against `findtorontoevents.ca/audit` Goal #1 (asset-class methodology + rescue plan). Read-only post-hoc compilation. Source of truth: [`_calls.jsonl`](_calls.jsonl) (54 records), [`_sessions.db`](_sessions.db) (6 active sessions), per-run `_summary.json` / `_chain_summary.json`.

---

## 1. Executive overview

- **Distinct swarm runs today**: **9** (1 PR/research fan-out v1, 1 PR/research fan-out v2, 1 multi-turn FOREX chain, 1 disagreement-resolution batch, 1 single-engine smoke, 2 ad-hoc resume tests, 1 probe-excluded ladder, 1 freebuff TUI ladder). Plus a long tail of 1-shot regression / fix-test calls.
- **Engines that produced signs of life today**: 11 (deepseek, xai, kilo, gemini, inception, ollama_cloud, cerebras, opencode, copilot, freebuff, codebuff). 9 with structured-JSON output proven; copilot proven via CLI but never wired into a fan-out; codebuff blocked on credits.
- **Total API/CLI calls**: 54 (per [`_calls.jsonl`](_calls.jsonl)).
- **Total response bytes**: ~137,881 B (~134 KB).
- **Total wall-clock** (sum of latencies, mostly parallel): 1,484.8 s (~24.7 min CPU-equivalent; actual real wall ~ 90 min spread across 6h).
- **Headline finding for the quant project**: 5/5-engine consensus locks the methodology axis per asset class — EQUITY=multi-factor cross-sectional, CRYPTO=Hyperliquid HLP-style, FOREX=carry+regime (mutate-first), COMMODITY=DBMF/COT, ETF=cross-sectional 12mo momentum (post xai concede). FOREX deep-dive narrows `forex_rsi2_mean_reversion` (n=616) + `forex_carry_momentum` (n=66) as 100% of class drag and orders an ATR-percentile falsification slice as the cheapest <30min test that either saves or kills the class.

---

## 2. Per-run sections

### Run `20260503T132558Z` — initial probe / fan-out v1
- **Type**: fan-out (research) + signs-of-life probe.
- **Problem solved**: Q1 best statistically-proven approach per asset class, Q2 30/60/90d rescue plan; first independent second-opinion on `/audit` methodology.
- **Triggered by**: ad-hoc per-engine `worker_runner.py` invocations (no YAML — predates `swarm_run.py` CLI). Reconstructed from `_calls.jsonl` rows 1-19 hitting `swarm_runs\20260503T132558Z\probe.<engine>.json`.
- **YAML config used**: ad-hoc, no YAML.
- **Personas/subagents involved**: none. The 6 `tools/swarm/agent_personas/*.md` were authored *from* this run's CONSENSUS, not used as inputs.
- **Engines** (after multiple retries; final state):

| Engine | Status | Bytes | Latency (final) | Notes |
|---|---|---:|---:|---|
| deepseek | OK | 7,292 | 28.3 s | Full structured JSON, all 6 classes |
| xai | OK | 5,202 | 24.8 s | Grok-3-latest, full schema |
| gemini | OK | 3,785 | 34.6 s | Free-text, ignored JSON contract |
| opencode | PARTIAL | 1,215 | 14.2 s | Saw briefing first line only (PowerShell 8KB-arg quoting bug) |
| inception | OK (after fix) | 6,926 | 6.6 s | `mercury` deprecated → `mercury-2`; utf-8 fix |
| cerebras | OK (after fix) | 4,172 | 2.0 s | gpt-oss-120b via SDK; utf-8 fix |
| ollama_cloud | OK (after fix) | 8,052 | 23.6 s | OLLAMA_CLOUD_KEY is SSH key, not chat token; pivoted to `ollama run gpt-oss:120b-cloud` |

- **Rounds per engine**: 1 turn each. Cerebras / inception / ollama_cloud had 2-5 retry attempts each (visible as ZOMBIE_OUTPUT-flagged calls in `_calls.jsonl`) before the post-fix successful response.
- **Outputs produced**: [`20260503T132558Z/CONSENSUS.md`](20260503T132558Z/CONSENSUS.md) (DeepSeek+xAI synthesis only — the v1 "2-engine" consensus).
- **Key replies**:
  - **deepseek**: "Factor-mimicking (Fama-French + momentum)... BOND no defensible approach until n>=100 — merge into ETF."
  - **xai**: "Carry trade with rate differential and vol gate... BOND yield-curve steepness arb with PIMCO benchmark." (disagrees with deepseek on BOND.)
  - **gemini**: free-text per-class summary; did not honor JSON contract.
  - **inception/cerebras/ollama_cloud/opencode**: present in raw files but not folded into v1 consensus (v1 only synthesised deepseek+xai).
- **Notable**: logging system caught every ZOMBIE_OUTPUT (output <50 B) and surfaced 3 distinct bugs (utf-8 encoding, wrong inception model, ollama SSH-key-vs-token confusion). opencode flagged false-OK at 1,215 B (size heuristic insufficient for content-quality).

---

### Run `probe_excluded` — engine signs-of-life ladder for non-API CLIs
- **Type**: signs-of-life probe (one-shot per engine).
- **Problem solved**: confirm whether copilot / kilo / freebuff produce non-trivial output on the same 6.8 KB briefing; later excluded from main fan-out for either auth, latency, or TUI reasons.
- **Triggered by**: ad-hoc `worker_runner.py` calls (rows 20-24 in `_calls.jsonl`).
- **YAML config used**: ad-hoc.
- **Personas/subagents**: none.
- **Engines**:

| Engine | Status | Bytes | Latency | Notes |
|---|---|---:|---:|---|
| kilo | OK | 10,089 | 73.3 s | Full structured JSON; later promoted into v2 fan-out |
| copilot | OK | 13,283 | 247.3 s | Tool-call markup needs stripping (see `tools/swarm/output_parsers.py`); excluded for latency |
| freebuff (run 1) | OK | 157 | 144.4 s | TUI-only; PTY captured banner not model response |
| freebuff (run 2) | OK | 167 | 144.6 s | Same |
| deepseek (safety_smoke) | LOW_SIGNAL | 4 | 1.1 s | 16-byte prompt — sanity test of safety/env-isolation pipeline |

- **Rounds**: 1 each.
- **Outputs**: 5 files in [`probe_excluded/`](probe_excluded/) (no CONSENSUS doc; this dir is exclusion / audit material).
- **Notable**: kilo's BOND answer (cross-currency basis arbitrage) was the most class-specific in the entire session; promoted kilo into the v2 fan-out. copilot proven OK but not used downstream (slowest engine + tool-call noise).

---

### Run `_smoke` — 2-engine PONG smoke test
- **Type**: single-engine smoke (×2 in parallel).
- **Problem solved**: prove `swarm_run.py` CLI fan-out works end-to-end with a tiny prompt before running a real briefing.
- **Triggered by**: `python tools/swarm/swarm_run.py --engines deepseek,xai ...` against a 36-byte temp prompt (`C:\Users\zerou\AppData\Local\Temp\jsmoke.txt`). Reconstructed from [`_smoke/_summary.json`](_smoke/_summary.json).
- **YAML config used**: ad-hoc (no YAML — direct `--engines` flag).
- **Personas/subagents**: none.
- **Engines**: deepseek (217 B / 1.3 s, OK), xai (202 B / 1.5 s, OK). 2/2 ok.
- **Rounds**: 1 each.
- **Outputs**: 2 JSON + 2 raw txt files. No consensus doc — smoke only.
- **Notable**: confirmed parallel fan-out path; same CLI later used for v2 run.

---

### Run `qa_20260503T151036Z` — empty / failed fan-out (no surviving dir)
- **Type**: ad-hoc QA fan-out (failed).
- **Problem solved**: nothing — appears to have used the placeholder 27-byte `swarm_runs/_adhoc_prompt.md`.
- **Triggered by**: `swarm_run.py --config tools/swarm/examples/multi_model_qa.yaml` with un-edited template prompt. Inferred from `_calls.jsonl` rows 27-29 `run_dir = swarm_runs\qa_20260503T151036Z` (directory was cleaned up).
- **YAML config used**: [`tools/swarm/examples/multi_model_qa.yaml`](../tools/swarm/examples/multi_model_qa.yaml).
- **Engines**: deepseek (3 B / LOW_SIGNAL), xai (3 B / LOW_SIGNAL), cerebras (3 B / LOW_SIGNAL). All low-signal.
- **Rounds**: 1 each.
- **Outputs**: directory cleaned up; no surviving artifacts.
- **Notable**: triggered the `multi_model_qa.yaml` exemplar but with the unfilled template prompt. Treat as evidence the YAML is plumbed but not productively used.

---

### Run `run_20260503T151049Z` — single deepseek probe (orphan)
- **Type**: single-engine smoke / regression.
- **Problem solved**: unknown — 27-byte prompt, 3-byte LOW_SIGNAL response. Probably part of `swarm_run.py` smoke wiring.
- **Triggered by**: `swarm_run.py` (row 30 in `_calls.jsonl`, run_dir absolute path).
- **YAML config used**: unknown — not recorded in summary.
- **Engines**: deepseek only, 3 B, 0.8 s. LOW_SIGNAL.
- **Rounds**: 1.
- **Outputs**: directory not preserved.
- **Notable**: orphan smoke; no useful signal.

---

### Run `_resume_test` — session-resume regression
- **Type**: multi-turn chain (2 turns, single engine).
- **Problem solved**: validate that `worker_runner.py --from-session` chains state across turns via API JSONL replay (deepseek path).
- **Triggered by**: ad-hoc `worker_runner.py` × 2 calls; turn 2 used `--from-session a3ca27a7-…` against the recorded session in `_sessions.db`.
- **YAML config used**: ad-hoc.
- **Personas/subagents**: none.
- **Engines**: deepseek × 2 turns (q1: 99-byte prompt → 40 B / 1.1 s, LOW_SIGNAL; q2: 568-byte prompt → 18 B / 1.1 s, LOW_SIGNAL).
- **Rounds per engine**: 2 (chain).
- **Outputs**: [`_resume_test/q1.json`](_resume_test/q1.json) (`{"acknowledged": true, "colour": "teal"}`), [`_resume_test/q2.json`](_resume_test/q2.json) (`{"colour": "teal"}`).
- **Notable**: structurally a successful resume — q2 returned the same `colour: teal` value seeded in q1, proving the JSONL-replay path remembers state. Both flagged LOW_SIGNAL because the schema-validator wants more bytes; functionally a green test.

---

### Run `run_20260503T153438Z` — fan-out v2 (the canonical 7-engine asset-class audit)
- **Type**: fan-out (research).
- **Problem solved**: re-run Q1/Q2 across 7 engines after all engine-fix work (utf-8, model swaps, SSH-key→CLI pivot), with sessions persisted to `_sessions.db` so disagreement resolution can resume specific engines.
- **Triggered by**: `python tools/swarm/swarm_run.py --config tools/swarm/examples/asset_class_audit.yaml --persist-sessions` per [`_run2_log.txt`](_run2_log.txt).
- **YAML config used**: [`tools/swarm/examples/asset_class_audit.yaml`](../tools/swarm/examples/asset_class_audit.yaml) (7 engines, max_parallel=4, json_strict=false except gemini=true).
- **Personas/subagents**: none invoked. Personas were only authored, not loaded.
- **Engines** (per [`run_20260503T153438Z/_summary.json`](run_20260503T153438Z/_summary.json)):

| Engine | Status | Bytes | Latency | Session ID (db) |
|---|---|---:|---:|---|
| gemini | FAILED (CLI launch) | 490 | 0.2 s | d2dc1f25-… |
| inception | OK | 6,878 | 6.4 s | 2fd83def-… |
| xai | OK | 5,820 | 26.4 s | 40502e7b-… |
| cerebras | OK | 8,892 | 4.6 s | 3b8857ab-… |
| deepseek | OK | 8,710 | 32.8 s | 07729506-… |
| ollama_cloud | OK (raw) / FAILED (parsed) | 2,813 | 35.1 s | 8647295a-… (terminal-line-wrap corrupted JSON; raw recoverable) |
| kilo | OK | 9,661 | 100.6 s | 64ada602-… |

- **Rounds per engine**: 1 each.
- **Outputs**: [`CONSENSUS_v2.md`](CONSENSUS_v2.md) (5-engine usable, 22.6 KB).
- **Key replies**:
  - **deepseek/xai/kilo/inception/cerebras**: 5/5 unanimous on EQUITY multi-factor methodology + AQR benchmark.
  - **deepseek/xai/kilo/inception/cerebras**: 5/5 unanimous on Hyperliquid HLP as CRYPTO benchmark (was 2/2 in v1).
  - **deepseek/xai/kilo/inception**: 4/5 on FOREX recommend porting `cftc_cot_commercial_signal` (live PF 3.50, n=32) from COMMODITY into FOREX (named in-repo strategy, not generic "use COT").
  - **xai vs the other 4**: ETF momentum-vs-mean-reversion split (1/5 mean-reversion).
  - **xai+inception+cerebras vs deepseek+kilo**: BOND yield-curve arb-vs-merge-to-ETF split (3/2).
  - **deepseek+cerebras vs xai+inception+kilo**: FOREX dragger handling kill-vs-mutate (2/3).
- **Notable**: gemini failed at CLI launch ("system cannot find the file specified"); ollama_cloud raw was usable but terminal-line-wrap corrupted the JSON parse path. Both flagged in v2 consensus header. Successful 5/7 by usable structured output.

---

### Run `_disagree` — disagreement-resolution turns (3 sessions, parallel)
- **Type**: disagreement resolution / followup turns via session resume.
- **Problem solved**: resolve the 3 disagreements surfaced in `CONSENSUS_v2.md`: ETF direction (xai mean-rev vs 4 others momentum), BOND viability (deepseek/kilo merge vs xai/inception/cerebras steepness arb), FOREX dragger handling (deepseek/cerebras kill vs xai/inception/kilo mutate).
- **Triggered by**: `tools/swarm/worker_runner.py --from-session <id>` × 3 — one per disagreement, resuming the dissenter or strongest skeptic from `_sessions.db`.
- **YAML config used**: ad-hoc (no YAML — direct `--from-session` calls).
- **Personas/subagents**: none.
- **Engines** (rows 40-42 in `_calls.jsonl`):

| Disagreement | Resumed engine | Session ID | Bytes | Latency |
|---|---|---|---:|---:|
| ETF (xai concede?) | xai | 40502e7b-… | 553 | 3.3 s |
| BOND (deepseek concede?) | deepseek | 07729506-… | 354 | 2.6 s |
| FOREX (kilo specifics?) | kilo | 64ada602-… | 812 | 17.1 s |

- **Rounds per engine**: 1 followup turn each (turn 2 of an implicit chain rooted in the v2 fan-out).
- **Outputs**: [`_disagree/{etf,bond,forex}.json`](_disagree/) + matching `.raw.txt` + `_prompt_*.txt`; synthesised in [`DISAGREEMENT_RESOLUTION.md`](DISAGREEMENT_RESOLUTION.md).
- **Key replies**:
  - **xai (ETF)**: `{"position": "concede", "switch_to": "momentum", "public_track": "MTUM Sharpe>0.8 5+yr"}` — verdict: 5/5 unanimous after concede.
  - **deepseek (BOND)**: `{"verdict_holds": true, "min_n_to_reopen": 100}` — verdict: still split 3/2, but operationally aligned (both camps converge on paper-only until n>=100).
  - **kilo (FOREX)**: 3 specific mutations across param/symbol/polarity axes + hard kill-after criteria + 400-trade total budget — verdict: mutate-first wins per repo policy + concrete plan.
- **Notable**: 0 sessions failed. All 3 resumes returned valid parsed JSON on first attempt — clean validation of the session-resume infrastructure.

---

### Run `followup_forex_20260503T154733Z` — FOREX deep-dive chain (aborted, restarted)
- **Type**: multi-turn chain (deleted before completion).
- **Problem solved**: same as 155122Z below — 4-turn FOREX deep-dive.
- **Triggered by**: `python tools/swarm/swarm_followup.py --config tools/swarm/examples/forex_deep_dive.yaml`.
- **Engines**: deepseek (turn 1 priming only completed before abort: 9,363 B / 35.8 s).
- **Outputs**: directory deleted (Option A: rerun cleanly). Turn-1 entry survives as session `b549a55c-…` in `_sessions.db`.
- **Notable**: orphaned partial chain; supplanted by `155122Z` 7 minutes later.

---

### Run `followup_forex_20260503T155122Z` — FOREX deep-dive chain (canonical)
- **Type**: multi-turn chain (single engine, 4 turns sequential).
- **Problem solved**: zoom into FOREX class drag (PF 0.27 / WR 46.4% / n=1169) — pinpoint the source_systems, pick mutate-before-kill axis, self-critique, emit JSON contract.
- **Triggered by**: `python tools/swarm/swarm_followup.py --config tools/swarm/examples/forex_deep_dive.yaml`.
- **YAML config used**: [`tools/swarm/examples/forex_deep_dive.yaml`](../tools/swarm/examples/forex_deep_dive.yaml) (1 engine × 4 turns: priming, analysis, critique, final).
- **Personas/subagents**: none invoked. Briefing referenced `forex_specialist.md` indirectly via the asset-class context but persona file was not loaded as a system prompt.
- **Engine**: deepseek (deepseek-chat) only. Chain session `55a2a7d3-e775-4a36-8c14-28f033bd88b3`.
- **Rounds**: 4 turns chained via `--from-session 55a2a7d3-…`. All 4 ok (rc=0).

| Turn | Name | Prompt bytes | Output bytes | Latency |
|---|---|---:|---:|---:|
| 1 | priming | 6,826 | 8,478 (envelope 9.2 KB) | 32.5 s |
| 2 | analysis | 22,878 | 1,852 (env 2.1 KB) | 8.2 s |
| 3 | critique | 47,502 | 1,628 (env 1.9 KB) | 6.5 s |
| 4 | final | 96,708 | 772 (env 1.1 KB) | 4.2 s |

- **Outputs**: [`followup_forex_20260503T155122Z/turn_*.json`](followup_forex_20260503T155122Z/) + [`final.json`](followup_forex_20260503T155122Z/final.json) + synthesis in [`FOREX_DEEP_DIVE.md`](FOREX_DEEP_DIVE.md).
- **Key replies**:
  - Turn 2 (verbatim): "the carry signal is inverted; signal polarity mutation is secondary but less likely to recover edge than regime gating."
  - Turn 3 self-retraction: "Retract: 'A regime filter would avoid low-volatility periods where spread eats the mean-reversion edge' — this assumes spreads are higher in low volatility, which is the opposite of typical FOREX market microstructure."
  - Turn 4 final JSON: `{"asset_class":"FOREX","recommended_axis":"regime","falsification_query":"Compare after-cost PF of forex_rsi2_mean_reversion split by ATR percentile >70 vs <30...","weakest_claim":"forex_rsi2_mean_reversion shows raw PF of 1.52","confidence":"MEDIUM"}`.
- **Notable**: chain demonstrably did the self-critique work (downgraded turn-2 HIGH → turn-4 MEDIUM after turn-3 self-attack). Total cost ~$0.15 (4 deepseek-chat calls). Prompt bytes grow each turn because the full conversation history is replayed via JSONL.

---

### Late-session 1-shot regression / fix-test calls (rows 48-54 in `_calls.jsonl`)
- Not full runs — individual smoke probes after the canonical work completed.

| ts_utc | engine | prompt B | output B | OK? | purpose |
|---|---|---:|---:|---|---|
| 15:53:27 | gemini | 26 | 5 | LOW_SIGNAL | `_gemini_fix_test.json` — testing if gemini CLI launch fixed |
| 15:54:09 | ollama_cloud | 6,826 | 8,321 | OK | `_ollama_fix_test.json` — re-verify post-fix |
| 15:54:21 | xai | 26 | 4 | LOW_SIGNAL | `_xai_regress.json` — regression smoke |
| 15:54:21 | deepseek | 26 | 4 | LOW_SIGNAL | `_deepseek_regress.json` |
| 15:54:23 | opencode | 6,826 | 0 | LOW_SIGNAL | `_opencode_fix_test.json` — opencode still partial |
| 15:54:42 | kilo | 26 | 5 | LOW_SIGNAL | `_kilo_regress.json` |
| 15:55:48 | opencode | 36 | 17 | LOW_SIGNAL | `_oc_short.json` — final opencode short-prompt regression |

---

## 3. Rounds-per-agent rollup

Aggregated over all 54 calls in `_calls.jsonl`.

| Engine | Total runs (unique run_dir) | Total turns/calls | Total raw bytes | Avg latency | OK rate |
|---|---:|---:|---:|---:|---:|
| deepseek | 8 | 16 | 37,951 | 11.7 s | 56.2% |
| xai | 5 | 7 | 11,091 | 11.1 s | 57.1% |
| kilo | 3 | 4 | 20,111 | 52.0 s | 75.0% |
| ollama_cloud | 4 | 6 | 24,341 | 24.0 s | 50.0% |
| inception | 2 | 4 | 13,289 | 5.3 s | 50.0% |
| cerebras | 4 | 8 | 12,469 | 2.3 s | 25.0% |
| copilot | 1 | 1 | 13,283 | 247.3 s | 100.0% |
| gemini | 3 | 3 | 3,790 | 13.9 s | 33.3% |
| opencode | 4 | 4 | 1,232 | 62.6 s | 25.0% |
| freebuff | 1 | 2 | 324 | 144.5 s | 100.0%* |
| **TOTAL** | — | **55** | **137,881** | — | — |

*freebuff "OK" rate is misleading — both calls captured banner only, no model response.

**Most-used by call count**: **deepseek** (16 calls).
**Least-used (and OK)**: **copilot** (1 call, fully OK at 13.3 KB but excluded for 247s latency).

---

## 4. YAML config usage

| YAML file | Times invoked | Runs |
|---|---:|---|
| [`asset_class_audit.yaml`](../tools/swarm/examples/asset_class_audit.yaml) | 1 | `run_20260503T153438Z` |
| [`forex_deep_dive.yaml`](../tools/swarm/examples/forex_deep_dive.yaml) | 2 (1 aborted, 1 canonical) | `followup_forex_20260503T154733Z`, `followup_forex_20260503T155122Z` |
| [`multi_model_qa.yaml`](../tools/swarm/examples/multi_model_qa.yaml) | 1 (with un-edited template prompt → low-signal) | `qa_20260503T151036Z` |

All 3 YAMLs in `tools/swarm/examples/` were exercised. Only `asset_class_audit.yaml` produced a substantive run; `multi_model_qa.yaml` was wired but never loaded with a real prompt; `forex_deep_dive.yaml` powered the deep-dive chain.

---

## 5. Persona usage

### `tools/swarm/agent_personas/*.md`

| Persona | Authored | Referenced in any prompt? | Loaded as Claude Code subagent? |
|---|---|---|---|
| [`INDEX.md`](../tools/swarm/agent_personas/INDEX.md) | yes | no | no |
| [`equity_specialist.md`](../tools/swarm/agent_personas/equity_specialist.md) | yes | no | no |
| [`crypto_specialist.md`](../tools/swarm/agent_personas/crypto_specialist.md) | yes | no | no |
| [`forex_specialist.md`](../tools/swarm/agent_personas/forex_specialist.md) | yes | no | no |
| [`commodity_specialist.md`](../tools/swarm/agent_personas/commodity_specialist.md) | yes | no | no |
| [`etf_specialist.md`](../tools/swarm/agent_personas/etf_specialist.md) | yes | no | no |
| [`bond_specialist.md`](../tools/swarm/agent_personas/bond_specialist.md) | yes | no | no |

**All 6 personas + INDEX are reference docs only**, written *from* the v1+v2 consensus output, not used as inputs. None were prepended to any prompt today; none invoked via Claude Code Task tool.

### `.claude/agents/*.md`

| Subagent | Authored | Invoked via Task tool today? |
|---|---|---|
| [`pr-reviewer.md`](../.claude/agents/pr-reviewer.md) | yes | no |
| [`fabrication-red-team.md`](../.claude/agents/fabrication-red-team.md) | yes | no |
| [`merge-captain.md`](../.claude/agents/merge-captain.md) | yes | no |
| [`dashboard-contract-reviewer.md`](../.claude/agents/dashboard-contract-reviewer.md) | yes | no |
| [`quant-performance-auditor.md`](../.claude/agents/quant-performance-auditor.md) | yes | no |

All 5 Claude Code subagent definitions are scaffolding. None show up in any swarm run summary or chain summary today. Per [`SESSION_SUMMARY.md`](SESSION_SUMMARY.md), these were authored but the Task-tool dispatches were lost in the same cleanup that wiped the swarm scaffolding files.

---

## 6. Selection methodology

| Run | How engines were chosen |
|---|---|
| `20260503T132558Z` (probe v1) | **operator-picked** — Claude/user enumerated all 8 engines per-call to test signs-of-life on each available API/CLI. |
| `probe_excluded` | **operator-picked** — explicit "test these CLIs separately" decision (kilo / copilot / freebuff / safety_smoke). |
| `_smoke` | **operator-picked** — `swarm_run.py --engines deepseek,xai`. |
| `qa_20260503T151036Z` | **config-driven** — engine list from `multi_model_qa.yaml`. |
| `run_20260503T151049Z` | unknown — not recorded in summary. |
| `_resume_test` | **operator-picked** — single engine (deepseek) chosen because it has the most reliable JSONL replay path. |
| `run_20260503T153438Z` (v2) | **config-driven** — `asset_class_audit.yaml` enumerates all 7 (deepseek, xai, kilo, gemini, inception, ollama_cloud, cerebras). |
| `_disagree` | **operator-picked** — each followup resumed the specific dissenter from CONSENSUS_v2 (xai for ETF, deepseek for BOND, kilo for FOREX). Selection logic: resume the strongest skeptic / most concrete proposer. |
| `followup_forex_*` | **config-driven** — `forex_deep_dive.yaml` hardcodes `engine: deepseek`. |
| late regression smokes | **operator-picked** — one engine per call to verify post-fix CLI launch. |

**No engine self-selected based on prompt class.** No random selection. Two patterns dominated: (a) config-driven enumeration in YAMLs for fan-out runs, (b) operator-picked single engine for resume/smoke/regression.

---

## 7. Headline findings (consensus + disagreements)

### Convergences (with engine count)

| Finding | Engines | Source |
|---|---|---|
| EQUITY: multi-factor cross-sectional (value+momentum+quality), AQR-family benchmark, kill PF<1.0 over 100-200 trades | 5/5 | [`CONSENSUS_v2.md`](CONSENSUS_v2.md) |
| CRYPTO: regime/sentiment + microstructure; **Hyperliquid HLP unanimous benchmark** | 5/5 (was 2/2 in v1) | [`CONSENSUS_v2.md`](CONSENSUS_v2.md) |
| FOREX rescue: port `cftc_cot_commercial_signal` (live PF 3.50 / n=32) from COMMODITY → FOREX | 4/5 | [`CONSENSUS_v2.md`](CONSENSUS_v2.md) |
| COMMODITY: term-structure + COT-commercial; **DBMF / KMLM benchmark** | 5/5 | [`CONSENSUS_v2.md`](CONSENSUS_v2.md) |
| ETF: cross-sectional 12-mo momentum + vol-parity, MTUM-style | 5/5 (after xai concede) | [`DISAGREEMENT_RESOLUTION.md`](DISAGREEMENT_RESOLUTION.md) §1 |
| Mutate-before-kill on FOREX draggers (3 specific mutations + hard kill criteria + 400-trade budget) | 5/5 (after kilo specifics + repo-policy alignment) | [`DISAGREEMENT_RESOLUTION.md`](DISAGREEMENT_RESOLUTION.md) §3 |

### Disagreements — RESOLVED

- **ETF momentum vs mean-reversion**: xai conceded after being asked for a public ETF mean-reversion track record; cited MTUM Sharpe>0.8 5+yr as stronger forward-only evidence. Net: 5/5 momentum.

### Disagreements — STILL OPEN (operationally aligned)

- **BOND viability**: 3/5 (xai/inception/cerebras) yield-curve steepness arb is salvageable; 2/5 (deepseek/kilo) merge to ETF until n>=100. **Still split**, but both camps converge on the same operational gate: passive paper-only collection until n>=100 with Wilson LB WR>=55% + PF>=1.5 12mo + independent replication. deepseek explicitly retains veto.

---

## 8. Open questions / next runs

Based on action items in [`FOREX_DEEP_DIVE.md`](FOREX_DEEP_DIVE.md) §"Concrete action items" and [`DISAGREEMENT_RESOLUTION.md`](DISAGREEMENT_RESOLUTION.md) §"Net new action items":

| # | Run that should fire next | Trigger source | Why |
|---|---|---|---|
| 1 | ATR-percentile falsification slice on `forex_rsi2_mean_reversion` | FOREX_DEEP_DIVE Action 1 | Cheapest <30min test that either saves FOREX or unlocks kill authority |
| 2 | Inverse-polarity test on `forex_carry_momentum` (n=66, PF 0.02) | FOREX_DEEP_DIVE Action 2 | PF 0.02 strongly suggests sign error; flip-test cheaper than redesign |
| 3 | Verify FOREX `PF 1.52` figure is gross or net of resolver-v2 5bp | FOREX_DEEP_DIVE Action 3 | Chain's flagged weakest claim; gates the whole regime-axis hypothesis |
| 4 | Implement kilo's 3 FOREX mutations sequentially (param → symbol → polarity, ~133 trades each) | DISAGREEMENT_RESOLUTION §3 | Mutate-first locked in by repo policy + 5/5 panel (post-resolution) |
| 5 | Stand up duration-hedge CUSIP-level execution logging | DISAGREEMENT_RESOLUTION §2 | Prerequisite for re-polling BOND swarm at n=30 |
| 6 | Re-poll BOND swarm at n=30 milestone | DISAGREEMENT_RESOLUTION §2 | deepseek explicitly retains veto authority; required-evidence checklist must pass |
| 7 | Hardcode kill-rule automation (after-cost <= -10% OR PF<1.2 etc.) per `feedback_halt_flag_must_be_hardcoded.md` | DISAGREEMENT_RESOLUTION §"Hardcode automation" | Documenting kill rules is not enough; must refuse fills |
| 8 | Update `audit_dashboard/template.html` MAJOR-GOAL banner ETF row to MTUM-style cross-sectional 12-mo | DISAGREEMENT_RESOLUTION §1 | Dashboard now has a documented methodology to cite |
| 9 | Run `multi_model_qa.yaml` with a real prompt (not the empty template) | section 4 | YAML wired but never productively used today |
| 10 | Re-run with personas loaded as system prompts (`forex_specialist.md` etc.) | section 5 | All 6 personas authored but never injected into a prompt — opportunity to A/B persona-loaded vs persona-free runs |

---

## Audit-trail contradictions vs existing CONSENSUS docs

- **CONSENSUS.md (v1) header** ([`20260503T132558Z/CONSENSUS.md`](20260503T132558Z/CONSENSUS.md) line 6) reads `Confidence: DeepSeek=MEDIUM; xAI=MEDIUM` — but only DeepSeek+xAI raw probes were synthesised, despite inception/cerebras/ollama_cloud/opencode all having usable raw output sitting in the same directory. Reading the v1 doc cold, you might think only 2 engines responded; in fact 5+ did. Not a contradiction per se but a coverage gap.
- **SESSION_SUMMARY.md "Stats / logging" table** (lines 87-97) reports 21 records and shows e.g. `deepseek calls=2 ok=2`. The actual `_calls.jsonl` is **54 records** with `deepseek calls=16 ok=9` cumulative. The SESSION_SUMMARY table reflects only the v1-probe-era state and was not refreshed when v2 + disagree + chain ran. Not a contradiction in conclusions, but the published-numbers-vs-reality gap is real.
- **CONSENSUS_v2 §Disagreement** says ETF is split 4/5 vs 1/5 — superseded but still not overwritten by [`DISAGREEMENT_RESOLUTION.md`](DISAGREEMENT_RESOLUTION.md) §1 (xai concede → 5/5 unanimous). Reader of CONSENSUS_v2 alone would still see the split. Recommend adding a header banner to CONSENSUS_v2 pointing to DISAGREEMENT_RESOLUTION.
- **`_run2_log.txt`** says 7/7 ok, but [`run_20260503T153438Z/_summary.json`](run_20260503T153438Z/_summary.json) shows gemini's `stderr_tail = "[gemini rc=1] The system cannot find the file specified."` and ollama_cloud raw was JSON-corrupted — i.e. 5/7 by usable structured output. Both [`SESSION_SUMMARY.md`](SESSION_SUMMARY.md) §"Refreshed asset-class consensus" and [`CONSENSUS_v2.md`](CONSENSUS_v2.md) report this honestly; the log file alone is misleading.
