# /money-maker-readyv2 — Freebuff Notes Integration — 2026-05-19T0030Z

Companion to `reports/MONEY_MAKER_READYV2_NORTH_STAR_2026-05-19T2350Z.md` +
`reports/MONEY_MAKER_READYV2_ADDENDUM_TODOS_2026-05-19T0010Z.md`. Folds in
peer-WIP notes from `FREEBUFF_*.MD` + `NOTESFORFREEBUFF_*.MD` +
`HERMESTOFREEBUFF.MD` + 4 `updates/2026-05-0[3-7]-freebuff-*.md`.

## Freshness audit

| File | Date | Status | Action |
|---|---|---|---|
| `FREEBUFF_2026-05-17_1901EST.MD` | 2d old | FRESH | INTEGRATE (P0 blocks + outlier cap) |
| `NOTESFORFREEBUFF_COPILOT.MD` | 14d | INFRA | SKIP — already wired (Ollama keyless tier) |
| `HERMESTOFREEBUFF.MD` | 14d | INFRA | SKIP — Hermes binary resolution |
| `updates/2026-05-03_FREEBUFF_BUFFY_CHAT_LOG_*` | 16d | SUPERSEDED | SKIP — May-17 covers |
| `updates/2026-05-03_FREEBUFF_BUFFY_PR_REVIEW_*` | 16d | SUPERSEDED | SKIP — May-17 covers |
| `updates/2026-05-04-freebuff-wasm-swarm-hardening.md` | 15d | INFRA | SKIP — PTY tree-sitter fallback |
| `updates/2026-05-07-freebuff-dispatch-protocol-log.md` | 12d | INFRA | SKIP — protocol telemetry |
| `DB_DASHBOARD_ENHANCEMENT_PLAN.md` | 11d | FRESH | INTEGRATE (DB integrity Tier-1) |
| `SWARM_ENHANCEMENT_PROPOSAL.md` | 11d | FRESH | INTEGRATE (Tier-1 swarm coverage) |

---

## INTEGRATE — three new P0 items advancing Goal #1

### F-1 PnL outlier cap ±100% at resolver layer

**Source:** `FREEBUFF_2026-05-17_1901EST.MD` — `ig_contrarian_sentiment` FOREX
showed CADJPY +8,559% PnL outlier inflating class PF to 26.57 (artifact, not
edge).

**Wire target:** `alpha_engine/outcome_resolver.py` + `audit_trail/quality_gates.py`

**Rule:** Cap per-pick `pnl_pct` to ±100% (or per-class median × 10) at the
canonical writer layer. Original value preserved in `pnl_pct_raw`. Aggregations
in `pf_registry.json` use the capped column.

**Acceptance:** Zero pf_registry rows with `|pnl_pct| > 100` AND class PF
deltas ≤ 0.05 between raw + capped views (sanity).

**Why this advances Goal #1:** Stops a single outlier from creating phantom
T2-candidates. FOREX PF 1.49 today is canonical-net; an uncapped outlier
elsewhere could mask the actual class state.

### F-2 DB integrity Tier-1 (db_health_check.py + dashboard panel)

**Source:** `DB_DASHBOARD_ENHANCEMENT_PLAN.md` (May 8).

**Findings to surface:**
- **PnL Integrity Badge:** 58% mismatch between `at_raw_picks` and resolver
  outcomes — actively distorts every canonical view.
- **Ghost Row Counter:** ~639k synthetic rows pollute aggregates.
- **OPEN Bloat Warning:** 26.96M OPEN-status rows = 90.4% of the picks table;
  triggers writer slowdowns + skews dedup.

**Wire target:** new `tools/db_health_check.py` + new `/audit` dashboard panel
"DB Health" rendered from a fresh JSON in `audit_dashboard/data/db_health.json`.

**Acceptance:**
1. `db_health_check.py` runs in <60s against `ejaguiar1_stocks` +
   `ejaguiar1_backtests`,
2. Emits `db_health.json` with 4 metrics (PnL-mismatch %, ghost-row count, OPEN
   bloat %, phantom EXPIRED count),
3. Dashboard panel renders top-right of `/audit`, red if any metric crosses
   alert threshold (mismatch >10%, ghosts >1k, OPEN >50%, phantoms >100).

**Why this advances Goal #1:** Canonical `pf_registry.json` is THE
verdict-grade ledger. If 58% of pnl values are mismatched, every per-class PF
+ Tier-2 verdict is suspect. This is necessary plumbing before any harness
clearance.

### F-3 Swarm coverage Tier-1 (strategy kill/keep triage automation)

**Source:** `SWARM_ENHANCEMENT_PROPOSAL.md` (May 8) — 17 personas authored,
only 3-4 dispatched; ML quality-gate personas (DSR, PSR, MinTRL) never run.

**Wire target:** new daemon / scheduled GHA `strategy-triage-daemon.yml`
firing `tools/swarm/swarm_run.py` against `docs/swarm_prompts/STRATEGY_KILL_TRIAGE_v1.md`
(NEW prompt).

**Rule:** Auto-flag for kill any (class, strategy) pair where `n≥30 AND
(WR<40% OR PF<0.8)`. Cross-checked against canonical PF before commit. Posts
suggested `STRATEGY_INVESTIGATION_*.md` template to `docs/` for human review.

**Acceptance:** Daily run identifies the top-3 drag emitters from canonical
view; ≥80% match against operator's prior manual kill decisions on a backtest.

**Why this advances Goal #1:** ensemble CRYPTO −56pp drag was discovered
manually this session. Automating the discovery accelerates per-class
hygiene — every drag killed lifts the class closer to T2 mechanical floor.

---

## SKIP rationale (transparent)

Infra notes (Ollama keyless tier, Hermes binary, WASM PTY, dispatch
telemetry): already operational; no edge / no per-class signal; nothing to
integrate.

May 3 PR reviews: 16-day-old snapshot of `quan_engine` 15% concentration cap,
FOREX 0% WR on `non_crypto_consensus`. Same findings present in May-17 note
(fresher). Avoid double-integration.

---

## What this does NOT do

- Does NOT reverse the no-edge verdict (`EDGE_VERDICT_2026-05-18.md`). 18
  pre-registered, 0 admissible-under-canonical stands.
- Does NOT introduce new hypotheses (none in freebuff notes worth M-107
  pre-registration; everything is hygiene/drag-removal).
- Does NOT claim any class is money-ready post-integration. F-1, F-2, F-3 are
  measurement upgrades that **make the next harness verdict trustworthy**;
  they do not themselves create edge.

---

## Updated TODO list (priority refresh after freebuff integration)

| # | Item | Priority | Source |
|---|---|---|---|
| 1 | Wire HARNESS_FDR_GATE (BH q=0.10) | P0 | Original swarm A |
| 2 | Wire DSR/PBO/WFE (López de Prado) | P0 | Renaissance prompt |
| 3 | Widen `is_admissible()` ledger scope 1/32 → ≥80% | P0 | T1-05 merged |
| 4 | **NEW: F-1 PnL outlier cap ±100% at resolver** | **P0** | **freebuff May-17** |
| 5 | **NEW: F-2 DB integrity Tier-1 (db_health_check.py + panel)** | **P0** | **DB_DASHBOARD May-8** |
| 6 | Ship `docs/swarm_prompts/RENAISSANCE_LDP_GATE_v1.md` | P0 | Renaissance |
| 7 | Fix `=F` → COMMODITY classification (FUTURES n=0 emit) | P0 | FOOLPROOF |
| 8 | Fix `timeframe=None` stamping (26 EQUITY picks) | P0 | ACTION_PLAN_V2 |
| 9 | **NEW: F-3 Swarm coverage Tier-1 (strategy kill/keep triage)** | **P1** | **SWARM_ENHANCEMENT** |
| 10 | STRATEGY_INVESTIGATION `quan_engine` CRYPTO | P1 | MASTER 2026-05-18 |
| 11 | Classify UNKNOWN class (n=38 PF 1.72) | P1 | this session |
| 12 | Confidence cap >0.90 at emission | P1 | EXPERT_FEEDBACK |
| 13 | Wire V-gate suite (V1..V10) into nightly CI | P1 | ACTION_PLAN_V2 |
| 14 | Codify P-1..P-7 as new `docs/swarm_prompts/` templates | P1 | mining session |
| 15 | Pre-register H-039 CRYPTO intraday volume-imbalance (M-107) | P2 | merged plan |
| 16 | Binance aggTrade fetcher | P2 | merged plan |
| 17 | Auto-broadcast hypothesis_registry status nightly | P2 | session goal |
| 18-21 | Operator-gated (whitelist enforce, FOREX harness, stash pop, FRED key) | Operator | various |

---

## Companion docs

- North-star master: `reports/MONEY_MAKER_READYV2_NORTH_STAR_2026-05-19T2350Z.md` (eb1053a)
- 18-item TODO addendum: `reports/MONEY_MAKER_READYV2_ADDENDUM_TODOS_2026-05-19T0010Z.md` (7998b6d)
- Merged plan: `reports/MERGED_ACTION_PLAN_2026-05-19.md`
- Edge verdict: `reports/EDGE_VERDICT_2026-05-18.md`
- Executive summary: `reports/EXECUTIVE_SUMMARY_2026-05-19T2240Z.md` (ab266e9)
- DB enhancement plan source: `DB_DASHBOARD_ENHANCEMENT_PLAN.md` (peer-WIP, repo root)
- Swarm enhancement source: `SWARM_ENHANCEMENT_PROPOSAL.md` (peer-WIP, repo root)
- Freebuff source: `FREEBUFF_2026-05-17_1901EST.MD` (repo root)

---

*Generated 2026-05-19T2358Z. Inspection via subagent against 9 freebuff/DB/swarm
peer-WIP MDs. Integration verdict: 3 new P0/P1 items, all hygiene (not new
edge). Aligned with no-edge frame. No fabrication.*
