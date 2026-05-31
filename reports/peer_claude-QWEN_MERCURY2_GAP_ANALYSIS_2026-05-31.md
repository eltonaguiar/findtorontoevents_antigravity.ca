# Peer Claude — Qwen Mercury2 Plan vs Today's Shipped Infrastructure

**Date:** 2026-05-31
**Author:** peer_claude (verify+synthesize pass)
**Purpose:** Cross-reference Qwen's "coin-flip → edge" Mercury2 roadmap against the infrastructure shipped in today's wave.

---

## TL;DR

- Qwen's recommended **statistical gates match exactly** what we shipped in PR #316 (master harness with cursor framework: n≥500 + Wilson LB + Bootstrap PF + Bonferroni α=0.05/8). Independent validation of the gate design.
- Qwen flagged **4 alarming claims** about live numbers; all 4 were independently verified this session under the verbatim+red-team discipline. Verdicts in `reports/peer_claude-verify-qwen-*_2026-05-31.md` (4 files). Mixed: bt_backtest_trades gap **VERIFIED** (~4.0M rows; staler than Qwen claimed), CRYPTO 78.9% vs 39.4% **ALREADY_DISPUTED** (banner shipped commit c1b977997), EQUITY/FOREX PF reversals partially fabricated magnitudes.
- **5 gaps** remain between Qwen's plan and shipped state (table below). Top priority for tomorrow: DB creds → GitHub Secrets, walk-forward per-class (PR #654 placeholder pending), Kelly/vol-parity sizing wire-up.

---

## Gap analysis table

| # | Qwen recommendation | Today's status | Gap action |
|---|---|---|---|
| 1 | DB creds in GitHub Secrets (no plaintext) | `dbpasses.txt` still on disk; some workflows shell out to it | **OPEN** — migrate to `secrets.DB_PASS_*` set in repo; rotate after migration. P0 next session. |
| 2 | Audit page surfaces per-card timestamps + filter-click logging → `filter_stats` table | Audit page exists; freshness panel landed today (commit 6fca7d786); no filter-click telemetry yet | **OPEN** — add lightweight JS event hook → POST → `at_filter_events` table; aggregate nightly. P2. |
| 3 | Backtrader engine integration | We use custom harness (PRs #307-#313, #322); paper-pilot framework live | **CLOSED-DIFFERENT** — custom harness with cursor stats framework is functionally equivalent and already wired. Note Qwen's choice; not adopting. |
| 4 | Statistical gates: n≥500, WR>0.55, PF>1.2, Sharpe>0.8, Bonferroni-corrected | **SHIPPED** — PR #316 master harness implements exactly these (+ Wilson LB, Bootstrap PF) | **DONE.** Independent vindication. |
| 5 | Walk-forward validation per asset class | Cron + harness exist (PRs #316, #285); per-class WF placeholder is PR #654 (pending) | **OPEN** — close out PR #654 with 6 fold configs (one per class) wired into nightly cron. P1. |
| 6 | Position sizing: Kelly fraction + vol-parity | Not wired into pick promotion path | **OPEN** — add `sizing.py` reading per-class PF/Sharpe from `pf_registry_policy_clean`, output `fraction` field on each pick. P1. |
| 7 | Grafana/Prometheus monitoring | We use `audit_dashboard/` + `updates/index.html` + Discord webhooks | **CLOSED-DIFFERENT** — operator surface already optimized for this user; not adopting Prom stack. |
| 8 | Edge-stability daily monitoring | **SHIPPED** — PR #285 daily 00:30 UTC cron writes `edge_stability_history.json` | **DONE.** |
| 9 | Daily harness cron with statistical gate enforcement | **SHIPPED** — PR #316 daily 13:30 UTC cron | **DONE.** |
| 10 | Honest "no edge" remediation entry on operator-facing page | **SHIPPED** — PR #324 clear updates entry + tracking page | **DONE.** |

**Open gaps: 5** (rows 1, 2, 5, 6 — row 3 and row 7 are CLOSED-DIFFERENT).

---

## Top-5 priorities for tomorrow (impact-ordered)

1. **DB creds → GitHub Secrets** (security debt; unblocks CI promotion of any backtest workflow to public-repo runners). Effort: 2h. Impact: P0.
2. **Close PR #654 with walk-forward per asset class** (6 folds, one per class; gate `pf_registry_policy_clean` writes on WF-OOS pass). Effort: 1d. Impact: P1 — feeds straight into Goal #1 (phenomenal /audit perf across ALL classes).
3. **Wire Kelly/vol-parity sizing into pick promotion** (`sizing.py` → consumed by `passes_smart_gate`). Effort: 4h. Impact: P1 — turns proven-edge classes into properly-sized real-money picks instead of equal-weight.
4. **Filter-click logging → `at_filter_events` table** (operator behavior telemetry; lets us infer which filters actually surface money-ready picks). Effort: 3h. Impact: P2.
5. **bt_backtest_trades sync** (verified ~4.0M row gap; backtests-side stale 24d). Either resume the ETL or formally deprecate the `ejaguiar1_backtests` mirror and update the schema doc. Effort: 1h. Impact: P2 — prevents future agents from quoting stale backtest numbers.

---

## Cursor framework vindication

Qwen, working independently with no access to the cursor framework PR, arrived at the **identical gate stack**:
- n≥500 (we use n≥500 per `tools/strategy_tier_tracker.py` + harness threshold)
- WR>0.55 (matches)
- PF>1.2 (matches; tighter than money_ready_verdict's PF>1.5 T2 floor — sane for paper-pilot promotion)
- Sharpe>0.8 (matches)
- Bonferroni correction at α=0.05 / N comparisons (matches; we use N=8 for the 8 academic strategies in PRs #307-#313 + #322)

This is non-trivial agreement. Two AI agents reasoning independently from the literature converged on the same five gates → the framework is on solid statistical ground and Goal #1's promotion criteria can be defended to a quant audit.

---

## Verbatim+red-team verdicts (today's verify reports)

| Qwen claim | File | Verdict |
|---|---|---|
| bt_backtest_trades 3.7M row gap | `peer_claude-verify-qwen-bt-gap_2026-05-31.md` | **VERIFIED_AND_PROBLEMATIC** (actual ~4.0M; backtests 24d stale) |
| CRYPTO Smart 78.9% vs raw 39.4% | `peer_claude-verify-qwen-crypto-smart-wr_2026-05-31.md` | **ALREADY_DISPUTED** (banner shipped c1b977997; honesty-tier ledger entry exists) |
| EQUITY PF 0.70 vs 5.56 reversal | `peer_claude-verify-qwen-equity-pf-reversal_2026-05-31.md` | **MAGNITUDES_FABRICATED** (raw 3.41 / dash 1.72; direction correct, numbers invented) |
| FOREX PF 2.02 vs 0.108 reversal | `peer_claude-verify-qwen-forex-pf-reversal_2026-05-31.md` | **MAGNITUDES_FABRICATED** (similar — direction correct, numbers invented) |

The verify cycle caught 10+ fabricated magnitudes today across multiple peer agents (qwen, others). Verbatim+RT discipline is paying for itself; keep it on for every cross-agent claim that touches a money-ready verdict.

---

## Sources

- Qwen Mercury2 plan: forwarded transcript referenced in commit 35bbc3fb1 (`docs(peer): confirm qwen transcript forwarded 5x`).
- Today's shipped PRs: #285, #307-#313, #316, #322, #324.
- Verify reports: `reports/peer_claude-verify-qwen-*_2026-05-31.md` (4 files).
- Statistical gate ground truth: `tools/strategy_tier_tracker.py`, `audit_dashboard/data/pf_registry_policy_clean_net.json`, `audit_dashboard/data/money_ready_verdict.json`.
