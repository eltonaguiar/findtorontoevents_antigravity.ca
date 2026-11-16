# Audit-Page Action Plan — kilo/auditpage

- **Author:** kilo (worktree `.kilo/worktrees/auditpage`)
- **Date:** 2026-11-16T06:25Z
- **Scope:** https://findtorontoevents.ca/audit/ — text/claims, DB health, data quality, PnL sanity, per-asset-class profitability, WIRED_IN integration, prediction-market data, GH Actions.
- **Status:** findings only. No code was changed in this pass (read-only audit).
- **Peers consolidated:** none available in this pass. The two spawned subagents returned (a) a generic tool-inventory reply instead of findings and (b) an API error. All findings below are my own, verified against repo files at `2d4672cb0c0` (origin/main).

---

## 0. TL;DR

| Area | Verdict |
|---|---|
| Money-ready classes | **0 / 9** — nothing passes n≥100, WR≥50%, PF≥1.5 |
| Honest (intrabar first-touch) WR/PF | CRYPTO 35.8%/0.92 · FOREX 32.2%/0.66 · EQUITY 59.2%/0.94 · COMMODITY 40.2%/1.03 · ETF 2.2%/0.02 · BOND 7.7%/0.39 · MEME 29.4%/0.66 |
| Best real lead | `crypto_rsi5070_us` shadow, net PF 1.11, CI-LB 0.92 (bar 1.15) — below promotion bar |
| Ghost rows | **Real: 22,947** (db_health.json). Dashboard truth-layer text claiming "0" is **stale/wrong** |
| WIRED_IN | Only `childlike-airport` is actually wired; safe (paper_only, sizing 0) |
| Prediction markets | Plumbing broken: 3 registered data files don't exist; dual-write path mismatch; 4 redundant workflows |

---

## 1. CRITICAL — data integrity

### 1.1 Ghost rows still 22,947 but page claims 0  (HIGH)
- Producer: `tools/db_health_check.py:172-240` → writes `audit_dashboard/data/db_health.json::checks.ghost_rows.data.total_ghost_rows`.
- Current value: **22,947** across **10 cohorts**, all `MEMECOIN` / `meta_strategy` (DOGEUSDT ×3, WIFUSDT ×2, PEPEUSDT, FLOKIUSDT, BONKUSDT, SHIBUSDT, ORDIUSDT), `distinct_entries` 1–4, `n` 1,692–3,569.
- Renderer: `audit_dashboard/dashboard_enhancements.js:750-755` shows the real 22,947.
- Contradiction: the TRUTH LAYER prose block on the page hard-codes "Ghost rows: 0 (was 22,947)". Grep for that literal in the template (`audit_dashboard/template.html` / `dashboard_generator.py` truth-layer strings) and **make it data-driven or delete it**.
- Why it matters: MEMECOIN PF 0.66 / WR 29.4% is partly an artifact of duplicate boilerplate rows. Cleaning or excluding these is the single cheapest credibility win.
- Suggested fix: run `tools/cleanup_ghost_rows.py --min-size 10 --execute` on `bt_backtest_trades` for the MEMECOIN cohorts (dry-run first), then re-run `db_health_check.py`, then re-generate the dashboard. Also fix the truth-layer literal.

### 1.2 Zero-PnL / FLAT rows — intentional, but make it visible (MED)
- `audit_trail/universal_pick_resolver.py:301-313` deliberately sets `pnl_pct = 0.0` when a fallback price is unavailable; `:1148-1159` maps TIME_EXIT/FLAT/EXPIRED accordingly. This is correct behaviour, not a bug.
- Risk: those rows land in closed_picks as FLAT and silently dilute WR. The dashboard shows 11 FLAT in W/L/F — small, acceptable — but there is no per-class count.
- Suggested fix: emit `resolution_method` breakdown per class into `dashboard_data.json::data_quality.zero_pnl_breakdown` so the page can show "n FLAT by reason" and reviewers stop chasing phantom PnL=0%.

### 1.3 Suspicious round-number closed PnL (MED)
- Seen on page: CRYPTO closed BTCUSDT/ETHUSDT/SOLUSDT/NEARUSDT all exactly **-2.00%**, JUPUSDT **+3.50%**, AVAX-USD **±2.00%/+3.00%**. These are SL/TP template values, not realized moves — fine if the exit reason is SL_HIT/TP_HIT, dangerous if reported as realized pnl.
- Suggested fix: add a hygiene check in `tools/db_health_check.py` counting closed rows whose `pnl_pct` exactly equals a round number AND `closed_at - created_at < 1h` AND `exit_reason` is null. That is the signature of a synthetic/prefill row.
- Also: `signal_validation` shows MDD **123.4%** and 90d cum **-118.4%** (grep `signal_validation` in the strategy registry) — that is a degenerate strategy still displayed in a "TIER-2 PROVEN" card. Kill it from that panel.

### 1.4 Walk-forward Sharpe mis-scaled (MED)
- Page shows `BOND` walk-forward Sharpe **-65.632** and `FOREX` **+10.7** on n=3. A Sharpe of -65 is a unit/scale bug, not a finding.
- Likely `std` near zero on a handful of rows. In `walk_forward_by_class()` (grep in `audit_trail/dashboard_generator.py`) clamp/skip Sharpe when `n < 30` or `std < 1e-6`, and render "n/a".
- FOREX n=3 in the walk-forward table vs n=612 in the headline is itself a filter bug — the WF table is not using the same cohort as the headline. Same for BOND (n=31 WF vs n=1 headline). Document which ledger each panel reads.

### 1.5 `strategy_ic_analysis.json` missing (LOW)
- Page shows "Failed to load IC analysis data". File absent from `audit_dashboard/data/`. Either generate it in the hourly cron or remove the panel — a dead panel reads as sloppiness.

---

## 2. Per-asset-class profitability — what is actually true

Source of truth used: `audit_dashboard/data/intrabar_truth_by_class.json`, `money_ready_verdict.json`, `audit_surface_truth.json`.

| Class | Honest n | WR | PF | Avg PnL/trade | Status |
|---|---|---|---|---|---|
| CRYPTO | 3,716 | 35.8% | 0.916 | -0.107% | FAIL |
| FOREX | 612 | 32.2% | 0.660 | -0.105% | FAIL |
| EQUITY | 250 | 59.2% | 0.939 | -0.074% | FAIL (PF<1 despite high WR) |
| COMMODITY | 229 | 40.2% | 1.026 | +0.027% | FAIL (thin) |
| FUTURES | 52 | 42.3% | 1.094 | +0.079% | INSUFF-N |
| ETF | 45 | 2.2% | 0.022 | -2.33% | BROKEN |
| MEME | 102 | 29.4% | 0.661 | -0.343% | FAIL, 74.5% single-day concentration |
| BOND | 26 | 7.7% | 0.391 | -0.334% | INSUFF-N |
| PENNY | 4 | 50% | 0.178 | — | INSUFF-N |

Observations:
1. **EQUITY's 59.2% WR with PF 0.94** is the clearest illustration that WR is not edge — average loss > average win. Any sizing decision made on WR is wrong.
2. **ETF PF 0.022 / avg -2.33%/trade** is not a strategy, it is a broken emitter. Kill or quarantine ETF emitters before showing the class at all.
3. **COMMODITY is the only class with positive average PnL (+0.027%)**, and futures_momentum (n57, 63%, PF 2.6) is the best sub-sleeve — but n<100 and not policy-clean (policy_clean_n=14, PF 0.17). This is a forward-track candidate, not a sizing candidate. The policy-clean vs raw gap (85.5% filtered vs 60.2% raw, per the page note) is a filter-survival artifact that must be surfaced, not hidden.
4. **FOREX win/loss asymmetry** (wins ~0.62%, losses ~1.00%, WR 57.8%, PF 0.85) — tight-TP/wide-SL geometry. Any FOREX emitter using symmetric ATR stops needs its TP floor raised or it will stay net-negative at 60% WR forever.
5. **Time buckets are all negative** (24h -5.69%, 7d -462%, 30d -957%, all-time -1,335% Σ). There is no recent positive cohort at n≥30. Aggregate compound -94.29% vs Σ per-trade +310.94% means position sizing on the compounding path is destroying a positive-expectancy trade stream — that is a *portfolio-construction* bug (likely equal-weight compounding on many small trades), worth a separate investigation.

**Conclusion: nothing is profitable. The system is a research ledger, not a money book.** The page should say that at the top, once, in plain language, and remove anything that reads like a win (the "TIER-2 PROVEN" card showing a -118% strategy; "Verified Realized WR 51.5%" without n/CI; "Smart Snapshot 75.4%").

---

## 3. WIRED_IN

- `WIRED_IN/` contains 26 timestamped folders; only **one** ships an artifact: `2026-11-15T0150Z_childlike-airport` → `audit_dashboard/data/wired_in_childlike_active_picks.json`, 3 picks (XLV/LLY/SHY), `paper_only: true`, `sizing_allowed: false`, `trust_tier: UNPROVEN`.
- Registration is correct: `audit_trail/dashboard_generator.py:4289-4291` (`JSON_PICK_SOURCES`), `audit_trail/universal_pick_resolver.py:265` (`SYSTEM_SOURCES`), excluded from forward-tested wins at `dashboard_generator.py:4307`.
- Gap: the file is a frozen 2026-11-15T01:50Z snapshot. No cron regenerates it. Either (a) add a job that re-scans the 3 symbols, or (b) label it "static snapshot — do not treat as live".
- All other WIRED_IN folders are specs/prompts — no action needed beyond a README table (which exists).
- Orphans: `WIRED_IN/final_v001/.../paper_scan.py`, `WIRED_IN/2026-11-15_0708/.../run.py` are not referenced by any workflow. Archive or wire.

## 4. Prediction markets (Polymarket / Kalshi)

The `pm_kalshi_signals` row showing **SOLUSDT / ETHUSDT / BTCUSDT** is **by design** — `alpha_engine/kalshi_signals.py:41-59` maps Kalshi crypto series (KXBTCD→BTCUSDT etc.) onto spot symbols and `dashboard_generator.py:5467` synthesizes spot entry/TP/SL. This is intentional and should be commented at `kalshi_signals.py:37` so it stops being reported as a bug.

Real gaps:
1. **Missing files.** `dashboard_generator.py:4090-4094` and `universal_pick_resolver.py:216-218, 322-325` register `prediction_market_agents/data/{kalshi,momentum,whale}_signals.json`. These files do not exist in the repo. Either a producer must write and commit them in CI, or the registration must be dropped. Today `pm_*` buckets are permanently empty.
2. **Path split.** `alpha_engine/kalshi_signals.py:31` writes `alpha_engine/data/kalshi_signals.json` while the resolver reads `prediction_market_agents/data/kalshi_signals.json`. Reconcile to one path.
3. **Redundant workflows.** `alpha-engine-live.yml` (cron `3 */2`), `prediction-market-agents.yml` (`15 */2`), `polymarket-signals.yml` (`13,43 * * * *`) and `audit-dashboard.yml` (hourly) all run overlapping PM scripts. Every invocation ends `|| echo ... non-fatal`, so failures are silent. Consolidate to one PM workflow; remove `|| echo` from steps that matter.
4. **Kill-list contradiction.** `alpha_engine/config.py:294` puts `prediction_market_consensus` on the kill list, yet it is still invoked by 3 workflows and tagged as a verified-alpha PM source in `dashboard_generator.py:5531`. Decide: remove, or shadow with a visible badge.
5. **No hard shadow pin.** Memory says "prediction markets stay shadow (PBO 0.603)" but there is no code constant enforcing it; PM families ride the normal 10-step gate (`admissibility_pipeline.py:105` `SIZING_SCHEDULE["shadow"]=0.0` applies only to whatever tier they land in). Add `PREDICTION_MARKETS_SHADOW_ONLY = True` at the sizing decision in `admissibility_pipeline.py:~720` and a test.

## 5. GitHub Actions

- 373 workflow files. Several `*.yml.disabled` remain (e.g. `alpha-engine-bond.yml.disabled`, `alpha-suite-daily-refresh.yml.disabled`) — delete or move to `archive/` so the directory count stops misleading audits.
- PM duplication (section 4.3) is the biggest redundancy.
- `|| echo ... non-fatal` masking appears in `alpha-engine-live.yml:159-170` and peers. Replacing with `|| (echo FAILED; exit 1)` (or a step-level `continue-on-error: false`) would make PM breakage visible.
- (See `GHACTIONS_2026-11-16/` deliverables from the earlier session for the queue/cancel-cascade audit — no new queue findings in this pass.)

---

## 6. Recommended order of work

**P0 — truth and credibility (do first, small diffs)**
1. Fix the stale "Ghost rows: 0" prose (make it read `db_health.json`).
2. Kill the `signal_validation` card from "TIER-2 PROVEN" (MDD 123%, n=102, -118%).
3. Clamp walk-forward Sharpe rendering when n<30 or std<1e-6; document which ledger each panel reads.
4. Add a plain-language banner: "0/9 asset classes money-ready; this is a research ledger, not a money book."

**P1 — data integrity**
5. Clean the 10 MEMECOIN ghost cohorts; re-run db_health; re-generate dashboard.
6. Emit `zero_pnl_breakdown` and `round_number_pnl` counts into the dashboard payload.

**P2 — pipeline correctness**
7. Reconcile the Kalshi/PM data paths; either generate the 3 missing PM files in CI or drop their registration.
8. Consolidate the 4 PM workflows into one; remove `|| echo` masking.
9. Resolve `prediction_market_consensus` kill-list vs verified-alpha contradiction.
10. Add the `PREDICTION_MARKETS_SHADOW_ONLY` sizing pin + test.

**P3 — profitability investigation**
11. Investigate the compound-vs-sum divergence (-94.29% compound vs +310.94% Σ per-trade): is sizing per-trade destroying a positive-expectancy stream? This is the only path to a real edge in current data.
12. Formalise forward-tracking for the two plausible leads: COMMODITY `futures_momentum` (n57, 63%, PF 2.6) and FOREX `forex_rsi2` (n19, 63%, PF 2.4). Track only; no sizing until n≥100 and policy-clean PF≥1.5.
13. Continue `crypto_rsi5070_us` shadow tracking to the n≥150 gate (~2026-12).

**P4 — hygiene**
14. Archive `.disabled` workflows; tidy orphaned WIRED_IN scripts; generate `strategy_ic_analysis.json` or remove the panel.

---

## 7. Evidence index

- `audit_dashboard/data/db_health.json` — ghost_rows 22,947; pnl_integrity 130/24,158; won_pnl_contradiction false
- `audit_dashboard/data/intrabar_truth_by_class.json` — per-class honest n/WR/PF
- `audit_dashboard/data/money_ready_verdict.json` — FOREX full gate dump (expectancy -0.00345, mdd 0.8212, bootstrap CI [-0.0077, +0.0029])
- `audit_dashboard/data/audit_surface_truth.json` — policy_clean vs n_resolved per class
- `tools/db_health_check.py:120-169` (pnl_integrity), `:172-240` (ghost_rows)
- `audit_trail/universal_pick_resolver.py:301-313, 1148-1159` (zero-PnL / FLAT)
- `audit_trail/dashboard_generator.py:4090-4094, 4289-4291, 4307, 5467, 5527-5532`
- `audit_dashboard/dashboard_enhancements.js:750-755`
- `alpha_engine/kalshi_signals.py:31, 37, 41-59`
- `alpha_engine/config.py:294` (prediction_market_consensus kill list)
- `audit_dashboard/data/wired_in_childlike_active_picks.json`
