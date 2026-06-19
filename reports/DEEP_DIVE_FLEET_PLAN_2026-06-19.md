# Deep-Dive Fleet Plan — hunt winners across the money-ready items
**Author:** claude-opus · 2026-06-19 · **Status:** plan for peer-review BEFORE spawning agents

## Goal
Spawn a bounded set of subagents, one per money-ready "item" (asset class + audit surface), to find the path to a **trustworthy, sizeable winner** — net-of-cost PF **CI-LB>1.15 @ n_eff≥80**, time-split-robust, conc<35%, FORWARD window.

## Verification / pre-work (SQL-confirmed 2026-06-19)
- **Honest ledger un-frozen + flowing** (P0 fixed): `at_signal_outcomes` updating; freshness guardian (`db-freshness-guardian.yml`, hourly) is LIVE and fail-hard (>24h intrabar = RED) — so #1 (un-mask) is DONE.
- **Per-class honest baseline (build_intrabar_truth, 11:54Z):** CRYPTO n=1155 PF 0.73 · EQUITY 120 PF 0.47 · COMMODITY 116 PF 1.06 · FOREX 96 PF 1.08 · MEME 77 0.58 · ETF/FUTURES/BOND <20. **0/10 pass.** n's barely moved post-unfreeze (resolution resumed ~03:30Z; accrual is slow).
- **Current-signal edge search is EXHAUSTED** this session (H-118..H-123 + 307-strategy×class sweep + daily-only source audit = 0 promotable). The sole lead `crypto_rsi5070_us` is n-MAXED at 108 (no replay shortcut) — purely forward-gated.
- **Durable rule:** daily-resolved PF inflates ~2-3× vs honest first-touch — honest first-touch is the ONLY promotion input.

## Design principle (avoid circling — the key risk)
Because current-signal search is exhausted, per-class deep-dives must NOT re-run the same scans (that re-derives 0/10). Each subagent has TWO mandates, weighted to the genuinely-new:
1. **(20%) Closest current candidate + ETA** — name the best existing strategy/condition in the class on the honest ledger, its net CI-LB, gap-to-bar, and forward-accrual ETA. (Confirms, doesn't re-search.)
2. **(80%) NEW-data avenue (H3)** — the most promising UNEXPLORED edge source for the class via free APIs (FRED macro, CFTC COT positioning, EDGAR/PEAD earnings, on-chain funding) — propose ONE pre-registered, falsifiable candidate hypothesis (M-107) that could become a NEW winner. This is where new edge actually comes from.

## The fleet (subagents + subtasks)
| # | Subagent | Mandate |
|---|---|---|
| A1 | CRYPTO | rsi5070_us accrual ETA at current rate; + H3: funding-rate / on-chain new candidate (pre-register) |
| A2 | EQUITY | closest (stocks_rsi2 etc.) + H3: **EDGAR PEAD** earnings-drift candidate (the FRED/EDGAR remedy) |
| A3 | FOREX | consensus is DEAD (artifact); + H3: **FRED macro-regime** carry/trend gate candidate |
| A4 | COMMODITY | closest (futures_momentum decayed) + H3: **CFTC COT positioning** candidate |
| A5 | Thin classes (ETF/BOND/FUTURES/MEME) | why n<20; the single highest-value activity to make any one measurable |
| S1 | Audit surfaces (/audit, pick_funnel, ai-tournament, hyrotrader, picks-now) | per surface: is the displayed edge HONEST or a daily-resolution/snapshot artifact? flag any still-misleading cell |

**Each subagent — non-negotiable:** DB via `tools/db_env.py` ONLY (never echo creds); **direct-SQL verify every number** (subagents fabricate DB stats — documented); honest SL-wins-ties first-touch + `tools/pf_ci_lower.py` net CI-LB; **pre-register any backtest (M-107) BEFORE running**; READ-ONLY (no commits/mutations); return structured findings (closest candidate + net CI-LB + gap + ETA; the ONE pre-registered H3 hypothesis + why; any surface honesty flag). Cite `(asset_class | n | timeframe)`.

## Synthesis (after the fleet returns)
Main agent: rank the H3 hypotheses by (economic prior strength × data availability × independence from existing lanes), register the top 2-3 in `hypothesis_registry.json`, wire them as forward-shadow lanes (never sized), and produce a per-class time-to-market table (closest candidate, gap, ETA, the proactive activity to close it).

## Risks & mitigations
- **Circling / re-deriving 0/10** → the 80/20 split forces the new-data focus; subagents are TOLD the current-signal search is exhausted + given H-118..123.
- **Fabrication** → SQL-verify mandate + main re-verifies any promotable claim.
- **Cost** (6 agents) → bounded; one per item; read-only.
- **Premature promotion** → all H3 outputs are pre-registered FORWARD-shadow hypotheses, never sized; promotion only at the bar.

## Open question for the reviewer
Is 6 subagents the right scope, or should the thin-class A5 + surface S1 be deferred (lower expected value) in favor of deeper A1-A4 new-data digs? Is the 80/20 (new-data vs confirm) the right weighting given the exhausted current-signal search?

---

## Peer review (3-model, :4000 proxy) + REVISIONS — 2026-06-19
**Consensus: REVISE** (nvidia-deepseek-v4-pro + deepseek-chat; paid-mode-large errored). Folded in:
1. **100% new-data** (was 80/20) — the "confirm closest candidate" is guaranteed-zero on exhausted signals; collapse it to a 2-line note, not a mandate.
2. **Academic-replication prior filter (the key guardrail)** — each agent may only pre-register a candidate that maps to ≥1 PUBLISHED result (PEAD/COT-positioning/carry/time-series-momentum/funding-basis). No blind API fishing → avoids the 307-sweep redux on new data.
3. **Hard cap + stop-condition** — ≤2 hypotheses/agent; if both fail the honest net CI-LB, STOP (do not fish further).
4. **Anti-overfit beyond SQL-verify** — every hypothesis pre-registered with falsification BEFORE the pull; report IS/OOS time-split + net CI-LB on the HONEST ledger (not a separate backtest); flag if the query was shaped to confirm.
5. **Scope merged to 5** — A1 CRYPTO, A2 EQUITY, A3 FOREX, A4 COMMODITY, A5 = cross-cutting data-source plumbing (FRED/CFTC/EDGAR availability) + audit-surface-honesty. Thin-classes folded into A5.
6. **Expectation set:** new data is NOT immune to honest first-touch; most candidates will still fail. Success = 1-2 replicated, net-of-cost, forward-shadow candidates registered — or an honest "still 0, here's the nearest miss + why."
