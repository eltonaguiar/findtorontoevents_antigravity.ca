# Local-Model Swarm — Task Backlog Review (2026-06-04 19:32Z)

Fanned the consolidated 10-item task backlog (distilled from 11 peer .MD files written today) to 4 local models via the LiteLLM rotating proxy at `http://localhost:4000/v1`.

## Engines

| Engine | Verdict on each item |
|---|---|
| local-vllm-large | Safe: [8]. Operator-required: [3, 118]. Top rec: reconcile nav_surface vs DB. |
| local-vllm-fast | Safe: [8]. Operator-required: [91, 115, 117]. Top rec: ENH #118 ASAP. |
| local-ollama-large | Safe: [8]. Operator-required: [3, 118]. Top rec: rotate DB password (#89). |
| local-ollama-fast | Safe: [8, 9, 10]. Operator-required: [4, 6, 7]. Top rec: #89 + #118. |

## Consensus

| Item | Verdict |
|---|---|
| **Add GE 1:8 Aug 2021 to reverse_split_symbols.py** | **4/4 SAFE — SHIPPED** (commit below) |
| INCIDENT #89 password rotation | 3/4 operator-required (ollama-fast disagrees) |
| ENHANCEMENT #118 CRYPTO LONG flip bypass | 4/4 risky-flag, recommend central upsert-layer fix with operator approval |
| PR #524 reverse-split registry overhaul | Stays on prior-swarm verdict: do not merge — fabricated dates |
| nav_surface_edge_matrix vs DB | vllm-large priority; needs alignment work |
| INCIDENT #91 dedup of 40K legacy rows | Operator-window task; risky autonomous |

## Shipped this turn

- `audit_trail/reverse_split_symbols.py`: GE 1:8 Aug 2021 added (7 symbols total in registry).
- Production exposure check: 0 rows for GE across `trading_picks`/`at_raw_picks`/`at_signal_outcomes`/`tournament_picks`. **Preventive add only** — protects against future LONG GE entries with pre-split prices.

## Local proxy state

5 local models available on `:4000/v1`:
- local-vllm-large, local-vllm-fast, local-vllm-gemma
- local-ollama-large, local-ollama-fast

All responded within 90s timeout. JSON-mode responses cleanly parsed.

## Top "single most actionable in next 15 min" recommendation across the 4 engines

Tie between **ENHANCEMENT #118** (central CRYPTO LONG flip — risky) and **INCIDENT #89** (password rotation — operator-only). Both require operator sign-off; no autonomous-safe high-leverage item beyond the GE add just shipped.

## Next-best autonomous follow-up

Reconcile `nav_surface_edge_matrix.json` vs `smart_picks_db_stats` programmatically — flag mismatches in the builder rather than relying on the static DISPUTED banner. vllm-large flagged this as its top priority.
