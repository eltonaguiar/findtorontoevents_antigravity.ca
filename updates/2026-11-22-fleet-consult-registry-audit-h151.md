# Fleet consult, registry numeric audit, and H-151 pre-registration

**Date:** 2026-11-22 · **Branch:** `fix/dsr-baselines-h146-key-scrub-2026-11-21`

## Why

Four follow-ups from the H-150 work: (1) check the rest of the registry for the same class of
unfalsifiable metric that H-150 shipped, (2) stop hand-trusting model reviews by making their
claims mechanically checkable, (3) pick the next hypothesis now that gross profitability is
refuted, and (4) use the whole local fleet — not one LM Studio endpoint — and then the cloud
tags, to generate candidates.

## 1. Registry numeric audit — `tools/registry_metric_audit.py`

Mechanical, no model in the loop. Each hypothesis is compared against its own recorded numbers
and its own declared thresholds.

| rule | what it flags |
|---|---|
| R1 | a decisive metric (alpha, IR, PF, WR, Sharpe, eff, t, DSR) stuck at exactly 0 / 1 / -1 / null |
| R3 | an affirmative verdict while a declared numeric criterion is violated |
| R3-nonaff | same, on a non-affirmative hypothesis (context only, expected) |
| R5 | affirmative status with prose only, no numbers |
| I1 | a declared threshold with no corresponding number (informational — many registries keep numbers in prose) |

**Validation that matters:** run against the registry as of `536cb04e081` (before the H-150 fix),
R1 fires on H-150 with `decisive metric degenerate (-0.0)` — the tool catches the real defect it
was written for. Against the current registry R1 finds nothing.

Current findings: 111 hypotheses, 6 R5 (`H-120`, `H-126`–`H-129`, `H-133` — affirmative status,
prose-only evidence), 5 R3-nonaff (violated criteria on hypotheses already marked non-affirmative,
expected and left alone), 61 I1 (thresholds whose numbers live in prose rather than in fields).
**No live R1 and no live R3.** The R5 cluster is the actionable backlog: six hypotheses claim an
affirmative state with no number attached to it.

## 2. Claim-checked fleet consult — `tools/fleet_consult.py`

Engines are discovered, not configured: LM Studio `/v1/models`, Ollama `/api/tags`, across every
`--target`. Requests route to the engine that owns the model; replies are written to disk as they
land so one hung model cannot cost the others.

`--check-claims` asks models for findings in a strict one-line format requiring a `file:line`
citation **and a verbatim quote of the code they object to**, then opens the file and verifies the
quote is there. Verdicts: `VERIFIED`, `VERIFIED_ELSEWHERE` (multi-line quote, cite drifted), or one
of `UNVERIFIED` / `NO_SUCH_FILE` / `LINE_OUT_OF_RANGE` / `PATH_OUTSIDE_REPO`.

`--self-check` proves the checker rejects a fabricated line number, a quote that is not in the file,
a missing file, and a path traversal — and accepts a real multi-line citation.

Live run against the H-150 excerpt: `usb-mistral-small-24b` correctly flagged the IR defect I had
already fixed and quoted the comment verbatim (`VERIFIED` after the multi-line fix);
`llama3.1:8b` produced no parseable findings; `gpt-oss-20b` and `minimax-m3:cloud` returned empty.

## 3. Fleet as found, and what it cost to learn

| host | engine | models | state |
|---|---|---|---|
| 192.168.2.32 | LM Studio :1234 | 11 | `gpt-oss-20b` loaded |
| 192.168.2.32 (Windows) | Ollama :11434 | ~70 | all cold |
| 127.0.0.1 (Linux) | Ollama :11434 | 27 | all cold |
| — | vLLM :8000 | 0 | not running |

Retired server-side (HTTP 410 → `glm-5.3-flash:cloud`): `deepseek-v3.1:671b-cloud`,
`kimi-k2.5:cloud`, `kimi-k2-thinking:cloud`, `cogito-2.1:671b-cloud`, `minimax-m2:cloud`,
`glm-4.6:cloud`, `qwen3-coder-next:cloud`. Live cloud tags: `glm-5.3-flash:cloud`,
`gpt-oss:120b-cloud`, `gemma4:31b-cloud`, `minimax-m3:cloud`.

Two failure modes cost several calls: reasoning models return `content: ""` with
`finish_reason: length` below ~2,500 tokens, and a cold 20–32 GB model exceeds a 420 s timeout
while answering in 2 s once warm (`GET /api/ps` shows what is loaded).

## 4. Ideation sweep and the pick

`reports/2026-11-22-fleet-ideation-sweep.md` — 64 ideas from 5 models, each judged against the 87
existing families. `gemma4:31b-cloud` was the best source (18 ideas in 8 s); `gpt-oss:120b-cloud`
was second but truncated mid-JSON; the two 8B local models produced restatements and templates.

**H-151 — Net Share Issuance (EQUITY)** pre-registered, frozen spec. 12-month change in shares
outstanding from EDGAR `dei:EntityCommonStockSharesOutstanding`, point-in-time (filed + 1 trading
day), split-guarded, quintile long-short, 1-month hold, 10bps/side. Accepted only on the same
terms H-150 was held to: harness eff ≥ 0.30 over ≥ 3 same-sign 14-day windows, FF4 alpha t ≥ 2 on
non-overlapping months, appraisal ratio ≥ 0.5 with sign matching the raw spread, cost survival
≥ 60%.

Chosen because the data is already cached from the H-150 run, the prior is old and economic
(Pontiff & Woodgate 2008), and issuance is a **financing** signal — orthogonal to the investment
signal that just failed. Prior art recorded: proposal ET-1 uses ETF shares outstanding as an
Authorized-Participant flow proxy, which is a different mechanism and is explicitly out of scope.

## Verification

- `tools/registry_metric_audit.py --self-check` → passes (4 synthetic cases incl. underpowered pass)
- `tools/fleet_consult.py --self-check` → passes (5 verification cases + fabricated-claim rejection)
- audit run against pre-fix registry → R1 fires on H-150; against current registry → no R1
- `pytest tests/test_registry_duplicate_keys.py tests/test_hypothesis_status.py` → 12 passed
- registry parses; 111 hypotheses; `H-151` present with empty `result` (pre-registration only)
- both new tools compile

## Not done

H-151 has not been backtested. Pre-registration is deliberately committed before the first run so
the spec cannot be tuned after seeing results. That run is the next step.
