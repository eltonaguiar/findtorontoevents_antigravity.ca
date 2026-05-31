# Phase 9 — DAILY_IDEAS Review Result (2026-05-31)

**Companion to:** `reports/peer_claude-phase9-daily-ideas-review_plan_2026-05-31.md`
**Reviewer:** Claude Opus 4.7 (server-side subagent, no execution)
**Anchor synthesis:** `reports/daily_ideas_edge_sweep_2026_05_17.md` (15 ideas, multi-agent ranked) + `DAILY_IDEAS.MD` IDEAs A–L (user brainstorm + 2-engine verdicts).

## Per-file bucket summary

| File | Total ideas | NOW | LATER | PARKED | OUTDATED | OP-PENDING |
|---|---|---|---|---|---|---|
| `DAILY_IDEAS.MD` (3677 lines, ~50 sections) | ~50 | 4 | 6 | 3 (IDEA-E, BOND, ETF) | ~30 (incidents shipped) | 2 (DB secret, MySQL pwd rotate) |
| `daily_ideas.MD` | 1 (today's parallelswarm prompt) | 0 | 0 | 0 | 1 (this session executed it) | 0 |
| `edge_sweep_2026_05_17.md` (top-15) | 15 | 3 | 2 | 0 | 7 (SHIPPED) | 3 (DB_PASS_BACKTESTS, pwd, CT=F prob) |
| `DIGEST_FOR_RESCUE_2026-05-19.md` | 6 per-class rescue threads + 6 question seeds | 1 | 2 | 1 | 2 | 0 |
| `daily_ideas_synthesis_2026-05-16.md` | ~12 | 1 | 1 | 0 | ~10 | 0 |
| `daily_ideas_synthesis_2026-05-15.md` | ~15 | 1 | 2 | 0 | ~12 | 0 |
| `daily_ideas_edge_per_class_20260513T010800Z.md` | 6 class-level rescue plans | 2 | 1 | 0 | 3 | 0 |
| `DAILY_IDEAS_PROMPTS.MD` (1174 lines) | 5 master prompts + 6 sub-areas | 1 | 1 | 0 | 3 | 0 |
| `daily_ideas_KimiCode.MD` (579 lines) | ~22 (5 areas) | 1 | 2 | 0 | ~15 (schema items shipped) | 4 (Windows env + DB secret) |
| `DAILY_IDEAS_GROK_2026_05_16.MD` | ~9 | 0 | 1 | 0 | ~6 | 0 |
| `DAILY_IDEAS_KIMICLI_2026_05_16.MD` | ~8 | 0 | 1 | 0 | ~7 | 0 |
| `DAILY_IDEAS_OLLAMA.MD` | ~7 | 0 | 1 | 0 | ~6 | 0 |
| `daily_ideas_ghcopilot_auto.MD` | ~14 | 1 | 1 | 0 | ~10 | 0 |
| `DAILY_IDEAS_OPENMONOAGENT.MD` | ~8 | 0 | 1 | 0 | ~7 | 0 |
| `DAILY_IDEAS_LLMARENA_May162026.MD` | ~12 | 0 | 1 | 0 | ~9 | 0 |
| `DAILY_IDEAS_XIAOMIMIMO_May172026.MD` | ~5 | 0 | 0 | 0 | ~5 | 0 |
| `DAILY_IDEAS_CURSORCLI_2026_05_16.MD` | ~7 | 0 | 1 | 0 | ~6 | 0 |
| `daily_ideas_nvidia.MD` | ~5 | 0 | 0 | 0 | ~5 | 0 |
| `DAILY_IDEAS_HUGGINGFACE.MD` | ~5 | 0 | 1 | 0 | ~4 | 0 |
| `daily_ideas_Kilocode_laguna.MD` | ~15 | 0 | 1 | 0 | ~13 | 0 |
| **Totals** | **~220** | **~14 unique** | **~25** | **3 explicit** | **~150 shipped** | **~9** |

(After de-dup against `edge_sweep_2026_05_17.md` consensus table the ~14 NOW-candidates collapse to ~7 unique items.)

## Cross-reference against today's session (PRs #150–#188)

Items already shipped today — **dropped from NOW**:

- IDEA-A FOREX isolation (split `cta_cross_asset_tsmom` vs `multi_asset_copytrader`) — landed via `5676eace2` (FOREX consolidation) + `1688956c7` (P0 batch).
- "RETIRE resolver-artifact strategies" — `cta_golden_cross_200` + `prediction_market_consensus` retired (#180, #182).
- MySQL silent-fail removal (`edge_sweep` #2, kimi 2.1) — landed in #152.
- NULL `pnl_pct` repair (KimiCode 4.1 + DIGEST per-class CRYPTO drag) — landed in #187 (162 LOST→WON reconciled) + Phase 7 forensic (#186).
- Profitable-but-filtered observability lane (LLM-Arena #4 + IDEA-A CRYPTO audit) — landed in #136.
- Audit CLI severity preserve (KimiCode 5.x) — landed in #76.
- Portfolios meta-effectiveness P6 (Cursor/Grok ensembling idea) — landed in #83.
- Peer red-flag sweep across open PRs (DIGEST creative question #1 meta) — landed in #188.

## NEXT-SWEEP-CANDIDATES (ranked)

| rank | idea (1-line) | source file | rationale (why now) | estimated PR scope |
|---|---|---|---|---|
| 1 | **Schema drift watchdog** — nightly `information_schema` snapshot vs version-controlled baseline in `schemas/`; CI fails on unexplained drift | `edge_sweep_2026_05_17.md` #9, `KimiCode` 1.3 | Today's Phase-5 found `at_strategy_stats.strategy` column holds tier labels instead of strategy names (PR #183). A drift watchdog would have caught this at write-time. Small blast radius, infra-only, 3h. | 2-file (1 workflow + 1 baseline JSON) |
| 2 | **Confidence calibration tracking table** — `at_confidence_calibration` MySQL table, per-bucket actual WR vs expected WR, auto-quarantine when gap < −50pp | `edge_sweep_2026_05_17.md` #11, `KimiCode` 1.3 | CLAUDE.md says "confidence is anti-edge on CRYPTO/ETF" yet there's no live calibration feedback loop. Phase-7 NULL-pnl forensics proved we measure outcome only after-the-fact; this closes the loop. **BLOCKED until DB_PASS_BACKTESTS in GH secrets** — operator action required first. | docs+schema (1-file) until secret lands; multi-file once unblocked |
| 3 | **FOREX carry-factor scaffold** — `tools/research/forex_carry.py`, long G10 high-yielders / short low-yielders, monthly rebalance, paper-only | `edge_sweep_2026_05_17.md` #14, `DAILY_IDEAS.MD` IDEA-A FOREX line 164, `edge_per_class` 2026-05-13 | FOREX is still FAIL (PF 0.55, USDJPY 55% concentration per CLAUDE.md). `cta_cross_asset_tsmom` consolidation today removes the bleed but doesn't add upside. Carry-factor is the only documented 30-yr edge per AQR; FRED_API_KEY already in secrets. Multi-file but research-only (no prod gate change). | multi-file (research module + paper-track entry) |
| 4 | **ETF sector rotation overlay** — relative-strength across 11 SPDRs (XLF/XLE/XLK/...) + risk-parity weights | `edge_sweep_2026_05_17.md` #15, `Kilocode` ETF section, IDEA-G | ETF is INSUFF-N (n=2 in CLAUDE.md) — class is starved of picks, not failing. Rotation adds an orthogonal emission stream that lifts n toward the n≥30 charter floor. | multi-file (strategy module + registry wiring) |
| 5 | **Polymarket Fed-rate macro overlay MVP (Phase-1 only)** — `~150 LOC`, query Polymarket Gamma + Kalshi for FOMC markets; emit signal when both agree ≥70% on rate-cut direction | `DAILY_IDEAS.MD` IDEA-H May-24 swarm verdict (7.5/10 composite) | Highest-scoring user-brainstorm idea per 2-engine swarm. ~40% infra reuse (8,700 LOC PM engine already exists). No new deps, no new API keys, paper-track only. Accept/Reject at 60-day mark. | 1-file MVP (Phase-1 scope only) |
| 6 | **200-day MA trend strategy + variants** — SMA-200 / EMA-200 / HMA-200 entries per asset class, tracked on `/audit/ai_leaderboard.html`; 1-2% risk floor stop | `DAILY_IDEAS.MD` 2026-05-29 user prompt | User explicitly requested 2026-05-29 — sat in queue 2 days. Simple, falsifiable, per-class baseline. Pairs naturally with the "golden persona finder" UI ask. | multi-file (strategy + leaderboard column) |
| 7 | **"Golden persona finder" UI on `/audit/ai_leaderboard.html`** — sortable highlighted view exposing high-PF Model-Persona cells | `DAILY_IDEAS.MD` 2026-05-29 user prompt | UI-only, single-file (`audit_dashboard/template.html`). User explicit ask. Low risk, immediate operator value. | 1-file |
| 8 | EQUITY value-momentum composite (P/E, P/B, EV/EBITDA + 6mo momentum) + insider-buy clusters | `DAILY_IDEAS.MD` IDEA-A EQUITY line 162 | EQUITY is FAIL+INSUFF-N (PF 0.90, n=33). 20-round research already approved in scope-modified IDEA-A. Free data only (yfinance + EDGAR). | multi-file (250 LOC) |
| 9 | COMMODITY seasonality overlay (grain harvest, energy winter draw, metals) on top of existing COT | `DAILY_IDEAS.MD` IDEA-A COMMODITY line 163, `edge_per_class` | Existing COT works (PF 1.42 pre-fix) — additive signal targeting WR 54.5%→58%. CT=F probation already running. | multi-file (150 LOC) |
| 10 | Cross-DB strategy-key consistency expand (ejaguiar1_backtests ↔ ejaguiar1_stocks symbol-class label mismatches) | `edge_sweep_2026_05_17.md` #10 marked SHIPPED but extension warranted | Phase-5 schema-mismatch finding (#183) suggests the cross-DB audit needs a column-semantics check too, not just key presence. | 1-file extension |

**Top-3 if forced to ship next session (smallest-blast/highest-certainty):** #1 (schema drift watchdog), #7 (golden persona finder UI), #5 (Polymarket Fed-rate MVP). All single- or 2-file scope, no operator unblock needed, advance Goal #1 directly.

## Red flags (ideas that contradict today's findings)

| # | idea | source | contradicts |
|---|---|---|---|
| R1 | "Promote `cta_golden_cross_200` to live sizing" (implicit in any "200-day MA win-rate looks great" framing of the May-29 prompt) | `DAILY_IDEAS.MD` 2026-05-29 line 3651 | **Phase-4 diagnosis (#180, #182) just retired this strategy as a resolver artifact.** The 200-day MA *concept* is fine to track; the *existing-DB stats* on `cta_golden_cross_200` must NOT be cited as edge evidence. Any new 200-MA work must use a fresh strategy name + paper-only registry entry. |
| R2 | "Promote `prediction_market_consensus` weight in HC scoring" (LLM-Arena #6 references PM consensus favorably) | `DAILY_IDEAS_LLMARENA_May162026.MD` | Retired today (#182) as resolver artifact alongside cta_golden_cross_200. The IDEA-H Polymarket MVP (rank #5 above) is a **new build with paper-only acceptance criteria**, not a revival of the retired strategy key. |
| R3 | "Size up CRYPTO based on 78.9% Smart-Picks WR" (echoed in multiple May-15/16 syntheses) | `daily_ideas_synthesis_2026-05-15.md`, `_2026-05-16.md` | CLAUDE.md explicitly disputes this number — raw DB shows 39% WR / PF 0.37 with 4 leakage signals. Any candidate that cites the 78.9% figure as forward-edge evidence must be down-graded. |
| R4 | "Tighten CRYPTO SL to lift PF" (suggested in `daily_ideas_KimiCode.MD` § Quick Wins) | `daily_ideas_KimiCode.MD` line ~314 | MEMORY note (2026-05-31): proven that tightening SL collapsed PF via whipsaw — opposite of winsorized estimate. SL-optimization requires intrabar OHLC replay, not winsorization. Any tighten-SL candidate is RED until price-path replay is in place. |
| R5 | "Trust headline `multi_asset_cot` PF 21.33 as Tier-1 candidate" | `DAILY_IDEAS_GROK_2026_05_16.MD`, May-15 synthesis | Already de-flagged in `edge_sweep_2026_05_17.md` #3 (DSR≥0.85 gate pending `ab_analysis`). Restate here so future re-reads of the Grok file don't re-promote it. |
| R6 | "Open new BOND/ETF live sizing now" | `daily_ideas_Kilocode_laguna.MD` | CLAUDE.md + IDEA-A both DEFER until n≥30. BOND n=8, ETF n=2 per current cohort. Any sizing-up candidate is RED. |

## NOW-count summary

- **ACTIONABLE-NOW unique items:** 7 (ranks #1–#7 above; ranks #8–#10 fall into ACTIONABLE-LATER due to multi-file scope or dependency).
- **RED FLAGS:** 6 (R1–R6).

## Recommendation for the operator

Settle the incidents-batch dust (today's PRs #180–#188 + this branch's PR), confirm `/audit` panels reflect the retire + consolidation, then run `/money-maker-readyv2` as previously sequenced. After that, the natural next-session candidate set is ranks #1, #7, #5 — small blast radius, no operator unblock required, three independent surfaces (infra + UI + new edge research).

Do **not** open work on ranks #2 (calibration table) or #8 (EQUITY value-momentum) until `DB_PASS_BACKTESTS` lands in GH secrets and `at_pick_outcomes` is provisioned — they will stall otherwise.
