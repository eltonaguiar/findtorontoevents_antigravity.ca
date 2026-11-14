# Final synthesis (scratch-hippodraco) — peers reviewed + path to “true profitability, statistically valid”

## 1) What I reviewed (sources)
- This worktree’s prior consolidated audit: `scratch-hippodraco.MD` (in repo root of this worktree/history context) and the quick-wins bundle under `2026-11-14/scratch-hippodraco-quick-wins/` (pushed on branch `docs/scratch-hippodraco-audit-2026-11-14` in prior session).
- Main repo snapshot (observed): `audits/2026-11-14/finpredict-v4_2026-11-14-1555/*`, `2026-11-14/finpredict-v2_20261114-1602/*`, recent `git log`/`status` captured under `01-main-repo-recent-and-local-changes/`.
- Worktrees inventoried: `finpredict`, `finpredict-v2`, `finpredict-v3`, `finpredict-v4`, `flaxen-hair`, `hilarious-seer`, `childlike-airport` (notes in `04-worktree-notes/`).
- Live/stat artifacts already present in repo: `audit_dashboard/data/money_ready_verdict.json`, `audit_dashboard/data/benchmark_ledger_proof.json` (as read in prior conversation turns) — summarized again below.

## 2) Peer work consensus (high level)
- **finpredict-v4 (2026-11-14 15:55, committed under `audits/.../finpredict-v4_2026-11-14-1555`)**: strong structured outputs (INDEX, dashboard/evidence JSONs, deep dives, market crossref, actions health). Useful as a **data-pack snapshot**; treat any recycled May-era numbers inside older narrative files as stale unless cross-checked against `evidence_*` + live regen. Proposed destructive SQL / unblock suggestions in that tree were **red-lined** in prior scratch review — do not apply.
- **finpredict-v2 (2026-11-14 16:02 bundle in `2026-11-14/finpredict-v2_20261114-1602`)**: emphasized reconciliation (three stores), policy-clean framing, and multiple-testing context (e.g. family counts) — aligns with “ledger truth before profit claims.”
- **finpredict-v3**: prior notes highlighted a gatekeeper leak-default change directionally right but **not merge-safe** without retrain/bundle parity and A/B/test fixes; also hygiene tooling mentions (`pi_data_hygiene.py`) worth adopting as **warn** gates if validated.
- **finpredict (v1)**: prior notes credited P0 truth fixes in a branch context (FX direction bucketing, summary WR>100% class, prediction-market None coercion) — adopt patterns carefully (OTHER-bucket / avoid silent LONG defaults / fix fallback paths) per `scratch-hippodraco.MD` A.5.
- **flaxen-hair / hilarious-seer / childlike-airport**: mixed value; childlike contributed SQLite stale/sign-flip corroboration (reconciled in scratch appendices). hilarious flagged weak/stub in prior review. Treat as supplementary unless re-verified.

## 3) Statistical validity + “true profitability” (current state, from prior verified reads)
- `money_ready_verdict.json` (2026-11-14): **no class MONEY_READY**; many `NOT_READY`/`INSUFFICIENT_DATA` with failures in expectancy, WR/PF gates, MDD/CVaR, bootstrap CI (examples summarized in prior turn). Recency sometimes OK — **validity is the blocker**, not “did we run the job.”
- `benchmark_ledger_proof.json` (2026-10-20 snapshot noted earlier): **no ledgers pass the 95% paired benchmark gate** in that run (`n_pass_95 0`). This is the wrong kind of “profitability story” to sell externally.
- Repo already encodes the right methods: DSR (with real `nb_trials`), SPA, PBO/CSCV gating patterns, anti-overfit registry concepts, `benchmark_closed_ledger`, `PRODUCTION_READINESS_FRAMEWORK.md` seven gates. The gap is **data integrity + pipeline plumbing + regenerated evidence**, not missing theory.

## 4) What “true profitability, statistically valid” requires (checklist)
1. **Canonical truth layer**: one deduped, policy-clean closed ledger per class; consistent PnL units (percent, not mixed fractions); resolver drain of OPEN backlog; explicit handling of EXPIRED/zombies (never in “active” performance claims).
2. **Costs real**: slippage/funding/roll/dividends/commissions per class wired into evals (not just displayed PnL).
3. **OOS discipline**: walk-forward/refit rules, embargo/purge where needed, report OOS windows — no in-sample-only promotion.
4. **Multiple testing**: DSR with correct `nb_trials` (all strategies/families tested that season), SPA family-wise control, PBO only when powered (≥5 strategies context). Expect false discoveries at 300+ variants without correction.
5. **Economic + risk gates**: net expectancy > 0 after costs, PF/WR vs Charter floors, MDD/CVaR limits, concentration caps.
6. **Benchmark proof**: paired tests vs appropriate benchmarks per class/direction (regenerate with current truth data).
7. **Recency + stability**: 14d/48h panels corroborate 90d; no silent data freeze.

## 5) Recommended execution order (concrete)
**Phase A — stop lying (1–3 days of focused plumbing)**
- Fix PnL unit contract at resolver + backfill + remove generator heuristics that guess units (per `scratch-hippodraco.MD` P0). Add CI guards (unit sanity, active-count reconciliation).
- Drain/reconcile OPEN/EXPIRED zombie flows; publish one active count and one closed ledger definition on the dashboard/JSON.
- Surface freshness/red/yellow from guardian into public payloads (no “stale warning false” when resolver lanes stale).

**Phase B — regenerate truth surfaces**
- Rebuild `closed_picks`/registry pipeline outputs, then regenerate `money_ready_verdict.json`, `pf_registry`-derived stats, `benchmark_ledger_proof.json`.
- Re-run `tools/ci_gate_money_ready_vs_registry` (and related gates) in CI.

**Phase C — score per class**
- For each class with sufficient candidates, compute DSR/SPA/PBO where applicable, net expectancy, MDD/CVaR, concentration. Fill a table matching `PRODUCTION_READINESS_FRAMEWORK.md` style.

**Phase D — promote only on evidence**
- Only classes passing rolling 90d **and** frozen walk-forward OOS with Charter checklist (`PRODUCTION_READINESS_FRAMEWORK.md` §4) may be considered for size-up; else paper/research.

## 6) What to do with peer branches/worktrees
- Do **not** merge `hilarious-seer` quick-win claims without re-verification.
- Treat finpredict-v4 `proposed_fixes/*` as ideas only; many flagged destructive/inappropriate.
- For finpredict-v3 gatekeeper changes: require retrain + bundle + parity tests before any prod merge.
- Prefer **small PRs**: (a) data hygiene/warn gates, (b) unit/backfill, (c) freshness surfacing, (d) validator alignment — each with tests.

## 7) Files in this bundle to read first
- `03-peer-audit-artifacts-2026-11-14-mainrepo/finpredict-v4_2026-11-14-1555/INDEX.md`
- `03-peer-audit-artifacts-2026-11-14-mainrepo/finpredict-v2_20261114-1602/INDEX.md` and `MASTER_AUDIT.md`
- Your pushed bundle: on branch `docs/scratch-hippodraco-audit-2026-11-14` includes `scratch-hippodraco.MD` and `2026-11-14/scratch-hippodraco-quick-wins/` (use GitHub/remote diff to review before merge).
