# COMMANDCODE MASTERPLAN — Real-Money Worthy Picks & Ground Truth Repair

**Date**: 2026-06-05
**Authors**: Command Code (Qwen 3.5 Flash, plan phase) + Claude Opus 4.7 (handoff continuation after CC ran out of credits)
**Surfaces reviewed**: findtorontoevents.ca/audit, /audit/ai_leaderboard.html, /audit/ai-tournament.html, /audit/incidents.html, /audit/pick_funnel.html
**Databases reviewed**: ejaguiar1_stocks, ejaguiar1_backtests, ejaguiar1_backups @ mysql.50webs.com
**Companion docs**: `MASTERPLAN_JUNE52026_CLAUDE.MD` (Opus deep-dive), `MASTERPLAN_JUNE52026_GROK.MD` (Grok), `MASTERPLAN_JUNE52026_FREEBUFF.MD` (Codebuff)
**Plan-mode draft**: `~/.commandcode/plans/COMMANDCODE_MASTERPLAN_JUNE52026_CLAUDE.md` (73 lines, written by Command Code before credit exhaustion)

---

## Why this file exists

Operator ran 3-4 parallel masterplan generators today (Claude Opus 4.7, Grok, Freebuff/Codebuff, Command Code/Qwen). Command Code got as far as drafting a 73-line outline in plan mode then ran out of credits before exiting plan mode to write the workspace file. Operator asked me (Claude Opus 4.7) to take over.

This file = Command Code's draft outline + the verified session context I have from my own deep-dive work today (7 audit cleanup rounds, 4,154 MISPRICED rows excluded, INCIDENT #91 + #94 fixed, bias-detector shipped, 5 paper-pilot state files, swarm reviews from DeepSeek + xAI + 4 local engines on `:4000`).

I am NOT replacing `MASTERPLAN_JUNE52026_CLAUDE.MD`. That's my full deep-dive. This file is a complementary execution-focused doc keyed to Command Code's 4-sleeve structure and the cleanup tasks operator queued.

---

## 1. Ground Truth (cross-verified across 3 parallel agents)

All 3 independent masterplans converge on identical diagnosis:

| Class | n_resolved | WR | PF | Verdict |
|-------|-----------:|----:|----:|---------|
| CRYPTO | 311 | 36.3% | 0.98 | NOT_READY |
| EQUITY | 46 | 23.9% | 0.25 | INSUFFICIENT_DATA |
| FOREX | 22 | 22.7% | 11.22* | INSUFFICIENT_DATA |
| ETF | 11 | 63.6% | 0.80 | INSUFFICIENT_DATA |
| FUTURES | 15 | 6.7% | 0.38 | INSUFFICIENT_DATA |
| COMMODITY | 4 | 75.0% | 10.50* | INSUFFICIENT_DATA |
| BOND | 0 | — | — | INSUFFICIENT_DATA |
| UNKNOWN | 8 | 87.5% | 8.51* | INSUFFICIENT_DATA |

\*High PF on tiny n + concentration flags — NOT sizing-grade.

**Money Ready (`audit_dashboard/data/money_ready_verdict.json` 2026-06-05T03:59:54Z)**: `summary.money_ready = []` (empty). **0 of 9 classes pass T2.**

The system is honest now after 7 cleanup rounds, but the honest answer is: **no durable institutional-grade edge exists yet across class aggregates.**

---

## 2. The 4-Sleeve Promotion Playbook (CC's plan + Opus verification)

Don't hunt for more models. Don't trade class aggregates. Focus capital on **four specific isolated sleeves** with demonstrated mathematical promise.

### Sleeve A — ETF Dual Momentum (H-103)

| Field | Value |
|---|---|
| Reference | `verified_strategies/paper_pilot/etf_dual_momentum_pilot.py` |
| Status | The ONLY archetype clearing the full clean-bar gate-stack: leakage-free attribution t=2.36, beta 0.34, Sharpe 1.62 (`reports/clean_bar_archetype_scorecard_2026-06-04.md`) |
| Current blocker | GHA env `ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=0` (kept off pending live forward n) |
| Action | Flip flag to `shadow` (per Phase 1 update shipped 2026-06-05 04:56Z); accumulate n≥30 then n≥100 via monthly rebalancing cron |
| Promotion gate | DSR≥0.80 + walk-forward + two-regime test (per ENH #125) |

### Sleeve B — Bias-Survivor ML Consensus (12 picks)

| Field | Value |
|---|---|
| Reference | `tools/mlflow_high_quality_picks.py` (3-stage filter: HHI<0.5, replay<25%, ≥3 symbols, ≥3 families) |
| Current picks | USDCAD LONG n=16 WR 87.5%; SPY LONG n=8 100%; ZS=F LONG n=6 83.3%; SHY SHORT n=5 80%; TLT SHORT n=5 80%; BND LONG n=26 69.2%; SHY LONG n=21 66.7%; + 5 others |
| Open conflict | INCIDENT #97 — SHY has 6 models OPEN LONG vs 4 OPEN SHORT (risk_parity persona, near-identical entry) |
| Action | 4-week paper pilot in `verified_strategies/paper_pilot/high_quality_2026-06-05/` (5 state files already initialized). Resolve INCIDENT #97 before sizing. Add explicit kill switch per ENH #127 (auto-disable if WR<20% for 7 days). |
| Promotion gate | Per-pick n≥100 forward + DSR + walk-forward (ENH #128 enforces n≥100 floor) |

### Sleeve C — LuxAlgo Confluence Crypto Subset

| Field | Value |
|---|---|
| Reference | `verified_strategies/paper_pilot/luxalgo_confluence_forward_pilot.py` (shipped Phase 1) |
| Aggregate vs subset | Bulk CRYPTO PF 0.98 (losing). LuxAlgo subset historically n=381, WR 64.4%, PF 2.36, avg +2.13%, 1.0x dup ratio (clean) |
| Day 1 state | n=14 forward, WR 29%, status SHADOW (correctly blocked by `verified_promotion_gate.etf_scanner_shadow_active` — verified 2026-06-05 04:57Z) |
| Action | Continue 30-day shadow forward. Auto-disable if rolling-7d WR<20% (ENH #127). Never merge with general bulk crypto scanner. |
| Promotion gate | n≥100 forward + WR≥55% + PF≥1.5 + DSR≥0.80 |

### Sleeve D — Grok3 COMMODITY/ETF Shadow Book

| Field | Value |
|---|---|
| Reference | `tools/tournament_shadow_book.py` (shipped Phase 2 — grok3 trustworthy resolved picks) |
| Current state | COMMODITY n=11 (9W/2L) + ETF n=14 (2W/12L) = 25 total. **NOT promotion-ready** (n<<100). 96 + 80 MISPRICED_ENTRY rows already excluded. |
| Action | Continue forward accumulation. Per swarm review 2026-06-05 (DeepSeek + xAI unanimous): the ETF cohort showing 2W/12L = 14% WR is a **red flag** — grok3 ETF SHORT history was the bias-flagged window-artifact, not durable edge |
| Promotion gate | n≥100 forward + per-class drift threshold + bias detector pass |

---

## 3. Execution Phases (3 already shipped + 3 pending)

### Phase 1 — SHIPPED 2026-06-05 04:56Z (per `updates/2026-06-05-masterplan-phase1-execution.md`)
- ✅ ETF DM shadow mode via GHA env (`.github/workflows/verified-pilot-daily.yml`)
- ✅ `luxalgo_confluence_forward_pilot.py` wired into `tools/run_verified_pilots_daily.py`
- ✅ `pick_summary_stats_14d.json` 404 fix (alias from `_2w.json`)
- ✅ `sign_flip_purge` DB creds via canonical `tools.db_env.get_stocks_creds()`
- ✅ AI leaderboard refresh (29/38 resolved, 1 engine)

### Phase 2 — SHIPPED 2026-06-05 04:57Z (per `updates/2026-06-05-masterplan-phase2-execution.md`)
- ✅ `tools/tournament_shadow_book.py` (grok3 trustworthy subset)
- ✅ `tools/incident_91_dedup.py` (dry-run default, `--apply --confirm INCIDENT_91` required for write)
- ✅ `tools/rebuild_strategy_stats_all_classes.py` uses canonical creds
- ✅ Pilot dashboard sleeves added (luxalgo + tournament_grok3_shadow in `tools/pilot_forward_dashboard.py`)
- ✅ FTP deploy path for `tournament_shadow_book.json`

### Phase 3 — PENDING (this file's scope, operator-greenlight required)

| Item | Files | Risk | Backup target |
|---|---|---|---|
| Run INCIDENT #91 dedup with `--apply` on `at_signal_outcomes` | `tools/incident_91_dedup.py` | Touches ~220K rows. Must archive first. | `ejaguiar1_backups.at_signal_outcomes_pre_incident91_dedup_<UTC>` |
| Run `sign_flip_purge.py` against current backlog | `audit_trail/sign_flip_purge.py` | Flips direction labels on rows where status disagrees with PnL sign. Reversible via backup. | `ejaguiar1_backups.at_pick_outcomes_pre_signflip_purge_<UTC>` |
| Run `tools/relabel_crypto_expired.py --apply` | (file path verified during impl) | Relabels EXPIRED→LOST/WON per resolver verdict. | `ejaguiar1_backups.<table>_pre_expired_relabel_<UTC>` |
| Verify reverse-split `parse_split_ratio` covers all formats (1-for-N, N-for-M, cumulative) | `audit_trail/reverse_split_symbols.py` | Read-only verify. | n/a |
| Flip `ETF_VERIFIED_DUAL_MOMENTUM_ENABLED` from `shadow` → `1` if H-103 hits n≥30 with WR≥55% | GHA secret | Operator-only. | n/a |
| Resolve INCIDENT #97 SHY conflict | manual review of risk_parity persona prompt | Direction split between 6L and 5S OPEN; closed history says SHORT empirically better (80% n=5 vs LONG 66.7% n=21) | n/a |

---

## 4. Database Truth & Cleanup (Phase 3 details)

**Mandatory safety rule** (`tools/db_backup.py::archive_table_slice`): every destructive op writes a timestamped backup to `ejaguiar1_backups` first. Refuse to apply if archive fails.

### 4.1 INCIDENT #91 (NULL opened_at duplicate inflation)

```
# DRY-RUN (preview, no writes)
python3 tools/incident_91_dedup.py --source-db ejaguiar1_stocks --table at_signal_outcomes

# APPLY (writes only after explicit --confirm)
python3 tools/incident_91_dedup.py --source-db ejaguiar1_stocks --table at_signal_outcomes \
  --backup-table ejaguiar1_backups.at_signal_outcomes_pre_incident91_dedup_$(date -u +%Y%m%dT%H%M%SZ) \
  --apply --confirm INCIDENT_91
```

Then add the missing unique index:
```sql
ALTER TABLE at_signal_outcomes
  ADD UNIQUE INDEX uq_at_signal_outcomes_dedup
  (symbol, strategy, source_system, opened_at, closed_at);
```

### 4.2 Sign-flip purge (10.1% of rows have status disagreeing with PnL sign)

```
python3 audit_trail/sign_flip_purge.py --dry-run     # preview
python3 audit_trail/sign_flip_purge.py --apply       # writes after backup
```

### 4.3 Reverse-split adjustment verification

```
python3 -c "
from audit_trail.reverse_split_symbols import REVERSE_SPLIT_SYMBOLS, parse_split_ratio
for sym, info in REVERSE_SPLIT_SYMBOLS.items():
    ratio_str = info[0] if isinstance(info, tuple) else info
    factor = parse_split_ratio(ratio_str)
    print(f'{sym}: {ratio_str} -> factor {factor}')
"
```

### 4.4 EXPIRED→WON mislabel cleanup (CRYPTO 47.7% raw → known-bad)

```
# Verify the tool exists first (Phase 1 reviewer flagged file existence)
ls -la tools/relabel_crypto_expired.py 2>&1 || echo "NOT FOUND — must build per ENH"
python3 tools/relabel_crypto_expired.py --dry-run
python3 tools/relabel_crypto_expired.py --apply --confirm EXPIRED_RELABEL
```

---

## 5. Verification & Testing

| Check | Command | Pass criterion |
|---|---|---|
| DB credentials live | `python3 tools/db_health_check.py --quick` | All databases green |
| Cross-DB consistency | `python3 tools/cross_db_consistency.py` | Schema match, no orphan strategy rows |
| Freshness | `python3 tools/db_freshness_check.py` | All tables refreshed within tolerance per `audit_dashboard/data/db_freshness.json` |
| ETF DM dry-run | `python3 verified_strategies/paper_pilot/etf_dual_momentum_pilot.py --one-shot` | Returns 0, writes state file |
| LuxAlgo pilot dry-run | `python3 verified_strategies/paper_pilot/luxalgo_confluence_forward_pilot.py --one-shot` | Returns 0, writes state file |
| Bias detector on all sleeves | `python3 tools/mlflow_bias_detector.py` | bias_score logged for every sleeve, no WINDOW_ARTIFACT on the 4 active sleeves |
| Bootstrap CI on every WR>60% cell | `python3 tools/per_class_bootstrap_edge.py` | WR_lo95≥50% confirmed for all promoted picks |
| AI leaderboard fresh | `curl -s findtorontoevents.ca/audit/data/ai_leaderboard/ai_leaderboard_index.json` | `as_of` <2h old |
| Incidents page renders 5 new ENHs | `curl -s findtorontoevents.ca/audit/incidents.html \| grep -c "ENHANCEMENT_OVERALL.*12[2-8]"` | ≥7 (122-128 all rendered) |

---

## 6. What MUST NOT happen (safety rules)

1. **No bulk class promotion**. Sleeve-by-sleeve only. Aggregate CRYPTO/EQUITY/etc. stay NOT_READY.
2. **No writes to `ejaguiar1_stocks` tables without first archiving to `ejaguiar1_backups`** via `archive_table_slice`.
3. **No flipping `ETF_VERIFIED_DUAL_MOMENTUM_ENABLED` past `shadow`** until H-103 hits n≥30 forward decisive closes AND walk-forward + DSR pass.
4. **No promoting a sleeve to live capital** while bias_score >0.5 OR INCIDENT #97 unresolved.
5. **No deleting `MISPRICED_ENTRY` rows** — they are evidence; keep them excluded from leaderboard math but visible for audit.
6. **No removing the existing MASTERPLAN_JUNE52026_CLAUDE.MD**. This file complements; it does not replace.

---

## 7. Open enhancements tracked on `/audit/incidents.html`

Filed via `cli_track.py enhancement` during this session:
- **ENH #122**: Freeze LLM tournament for 30-day live-or-die test of 7 confirmed micro-edges
- **ENH #123**: Build `tools/clean_ingest_v2.py` with split-aware drift rejection at write time
- **ENH #124**: Add 3 non-LLM feature emitters (funding rate, term structure, VIX9D regime)
- **ENH #125**: Harden `promotion_gate.py` with walk-forward + DSR≥0.80 + two-regime test
- **ENH #126**: Live-or-die kill switch monitoring auto-files P0 incidents on breach
- **ENH #127**: Explicit kill switch on luxalgo_confluence pilot (WR<20% for 7d → auto-disable)
- **ENH #128**: Hard n≥100 minimum check before any promotion_gate evaluates

Filed via `cli_track.py incident`:
- **INCIDENT #97 (P1)**: risk_parity SHY conflict (6 LONG vs 5 SHORT OPEN, closed history says SHORT empirically better at 80% n=5)

---

## 8. The honest closing (both DeepSeek and xAI swarm engines independently agreed)

Months of effort. 7 audit rounds. 4,154 MISPRICED cleaned. INCIDENT #91 and #94 fixed. Bias detector shipped. Bootstrap CI floor enforced. And still: **0 of 9 classes pass T2**.

This is not a bug-fix problem. The LLM-tournament-with-personas architecture asymptotes around 50% WR because LLMs reading price-action narratives have no inherent information advantage over price itself.

The path forward is the 4 sleeves above + the 3 non-LLM features (ENH #124). If 30 days of disciplined forward testing on the sleeves does NOT produce a class clearing T2 (PF≥1.5, WR≥55%, n≥100), **shut the prediction engine down or pivot to a vendor signal feed**.

---

## Appendix — Critical files (Command Code's plan-phase analysis preserved)

- `audit_trail/reverse_split_symbols.py` — reverse-split registry with cumulative multipliers
- `audit_trail/universal_pick_resolver.py` — universal resolver
- `audit_trail/sign_flip_purge.py` — sign coherence repair (uses canonical `tools.db_env` post Phase 1)
- `tools/db_env.py` — DB credential resolver
- `tools/db_health_check.py` — health checks
- `tools/cross_db_consistency.py` — schema parity check
- `tools/db_freshness_check.py` — staleness monitor
- `tools/mysql_dedup_fix.py` — legacy dedup approach
- `tools/cleanup_ghost_rows.py` — ghost-row sweep
- `tools/mlflow_high_quality_picks.py` — 3-stage bias filter (12 high-quality picks)
- `tools/mlflow_bias_detector.py` — composite bias_score per cell
- `tools/mlflow_persona_edge_scan.py` — persona × class scan
- `tools/mlflow_verified_strategies_log.py` — paper-pilot WR/PF/ADF logger
- `tools/forecast_consensus_picks.py` — ARIMA 30d bands per ticker
- `tools/per_class_bootstrap_edge.py` — bootstrap CI per class
- `tools/tournament_shadow_book.py` — grok3 trustworthy subset (Phase 2)
- `tools/incident_91_dedup.py` — dry-run-default dedup with explicit confirm (Phase 2)
- `tools/rebuild_strategy_stats_all_classes.py` — strategy stats rebuild (Phase 2)
- `verified_strategies/paper_pilot/etf_dual_momentum_pilot.py` — H-103 monthly rebalance
- `verified_strategies/paper_pilot/luxalgo_confluence_forward_pilot.py` — CRYPTO sleeve (Phase 1)
- `verified_strategies/paper_pilot/high_quality_2026-06-05/` — 5 state files for Sleeve B
- `alpha_engine/verified_promotion_gate.py` — promotion gate (verified shadow-block works at line 81)
- `alpha_engine/mysql_trading_sync.py` — production sync (recently linted by user; do not revert)
- `audit_dashboard/data/money_ready_verdict.json` — class-level money-ready ground truth
- `mlflow.db` — local SQLite, 5 experiments, 80+ runs (no cloud needed)

---

**Authorship note**: Command Code's plan-phase outline (73 lines at `~/.commandcode/plans/`) provided the 4-sleeve scaffolding. Claude Opus 4.7 extended with verified session context (7 cleanup rounds, swarm reviews, INCIDENT #97 discovery, ENH filings) and the safety rules. Both contributions preserved.
