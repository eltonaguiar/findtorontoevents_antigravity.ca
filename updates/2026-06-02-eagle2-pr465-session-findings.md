# EAGLE2 / PR #465 Session — Findings, Achievements & Next Steps

**Date:** 2026-06-02  
**Agent:** cursor-composer (gx10)  
**Goal #1 surface:** [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit)  
**Related:** [PR #465](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/465) (merged `4e2887f9e`), [post-steps](https://findtorontoevents.ca/updates/2026-06-02-pr465-merged-post-steps.md)

---

## Executive summary

We landed **mutation PF hardening** and a **shadow promotion gate** on the production scanner, ran a full **resolver + hygiene** pass, and documented why `/audit` health still shows **YELLOW** without implying time-expired picks are piling up. **Capital policy is unchanged:** `PROMOTED_STRATEGIES` is empty, money-ready is **0/9**, and **no production sizing** should occur on aggregate Smart Picks.

---

## Achievements (verified)

### Code & merge

| Item | Evidence |
|------|----------|
| **PR #465 merged** | `4e2887f9e` — `_MAX_REPORT_PF=99`, zero gross-loss → `0.0`, INVERT ADOPT needs ≥3 losing trades |
| **Promotion gate shadow** | `production_scanner.py` §6f2.8 stamps `_promotion_gate_*`; `audit_trail/promotion_gate.py` allowlist **empty by design** |
| **Honest mutation scan** | `tools/run_mutation_scan_honest.py` → `reports/mutation_scan_honest_latest.json` |
| **Tests** | `tests/test_mutation_framework_pf.py` — 4 passed |
| **CI fix** | `test_portfolio_engine.py` aligned to conservative `-6.5%` SL in `config/portfolio_risk_profiles.json` |
| **Deploy manifest** | `tools/deploy_audit_files.py` includes post-steps + this findings `.md` |

### Incidents / DB (prior in session)

- **5 incidents + 5 enhancements** seeded to `ejaguiar1_stocks` (`INCIDENT_OVERALL#78` mutation PF P0 → **RESOLVED**)
- Live incidents feed: [/audit/incidents.html](https://findtorontoevents.ca/audit/incidents.html)

### Operations (2026-06-02)

| Job | Result |
|-----|--------|
| `universal_pick_resolver.py` (run 1) | **+123** resolved (TP 75 / SL 37 / EXP 11); 565 file-source actives checked |
| `universal_pick_resolver.py` (run 2) | Additional file-source resolutions (e.g. mutation_lab +4, signal_validation +3); ~11 min |
| `resolve_stale_open_picks.py --execute` | **+24** MySQL stale closes (BOND/COMMODITY/INDEX/STOCKS); then **0** time-stale in follow-up batches |
| `outcome_resolver.py --mysql` | **+3–7** non-crypto bar-replay closes (FOREX/COMMODITY); requires `PYTHONPATH=<repo>` |
| `run_verified_pilots_daily.py` | ok=True — ETF XLK OPEN, `n_closed=0` |
| `run_eagle_suite.py` | ok=True — money_ready **0/9**, THRESHOLD_FREEZE until **2026-08-18** |
| `backfill_source_system_from_strategy.py` | **0** rows (provenance already clean) |
| Updates deployed | PR #465 card on [/updates/](https://findtorontoevents.ca/updates/index.html); post-steps MD live |

### Documentation & coordination

- `memory/2026-06-02.md` — session log  
- Cross-PC broadcasts on `192.168.2.32:8788`  
- Git: `d8d4d8c0f`, `533e2c99a`, `e98a20344`, `533e2c99a` (wave-2 docs), etc.

---

## Key findings

### 1. Honest mutation PF (P0 closed)

- **Before:** win-count/loss-count ratio + **999 sentinel** → fake INVERT PF 600+  
- **After PR #465:** dollar PF, cap 99, zero-loss → 0, min 3 losses for ADOPT/CONSIDER  
- **MySQL scan:** 2298 closed / 35 strategies → **5** INVERT adopt/consider (not 14)  
- **Do not ship** INVERT to production — `baby_strategies/inverted_strategies.py` remains **RESEARCH ONLY**

Top honest INVERT (still cap-inflated when gross_loss tiny — treat as **research flags only**):

| Strategy | Orig PF | Inv PF | Verdict |
|----------|---------|--------|---------|
| alpha_engine_fast | 0.00 | 99.00 (cap) | ADOPT |
| cta_replicator | 0.23 | 65.84 | CONSIDER |
| multi_asset_copytrader | 0.04 | 35.29 | ADOPT |
| non_crypto_consensus | 0.02 | 6.54 | CONSIDER |
| mercury2 | 0.02 | 2.49 | CONSIDER |

### 2. Promotion gate is wired but not enforcing

- Empty `PROMOTED_STRATEGIES` → shadow metadata only  
- **`PROMOTION_GATE_ENFORCE=1` with empty allowlist blocks ALL emission** — keep off until first admission  
- First candidate: `etf_verified_dual_momentum` after forward **`n_closed ≥ 30`** (currently **0**, XLK BUY OPEN)

### 3. Resolver health YELLOW is misleading

`tools/check_resolver_health.py` → `stale_by_category` sets **`estimated_stale = total_open`** for every OPEN row. That is **not** “past max hold hours.”

- **OPEN:** 2465 (commodity 771, equity 765, crypto 432, …)  
- **Time-stale tool:** `resolve_stale_open_picks.py` only queries `status='OPEN'` → **0** stale after hygiene batch  
- **Real issue:** volume of unresolved **OPEN** + parallel **`ACTIVE`** cohort (below)

### 4. ACTIVE vs OPEN — dual live cohort (mitigated 2026-06-02)

**P0 resolver** closed **3663** past-hold `OPEN`+`ACTIVE` rows to `TIME_EXIT`. Post-hygiene (~23:57Z): **2690** live picks, **0** past hold window in a 10-batch stale pass.

| Status | Pre-P0 | Post-P0 (approx.) |
|--------|--------:|------------------:|
| **OPEN** | 2465 | ~2432 |
| **ACTIVE** | 3726 | ~258 |
| TIME_EXIT | 29206 | ~32813 |

**Writer fix (wave 3):** `mysql_trading_sync.pick_to_row` defaults missing status to **`OPEN`**; live `ACTIVE` without terminal `exit_reason` maps to **`OPEN`** on upsert so the dual cohort does not regrow.

### 5. Money-ready / capital (unchanged)

- **0/9** asset classes money-ready (`run_eagle_suite` / `money_ready_verdict.json`)  
- **THRESHOLD_FREEZE** active until 2026-08-18  
- Production Smart Picks: **do not size**  
- **Watch only:** tournament paper + `etf_verified_dual_momentum` shadow pilot

### 6. `outcome_resolver` invocation footgun

Running `python3 alpha_engine/outcome_resolver.py` without repo on `PYTHONPATH` fails at MySQL dedup (`No module named 'alpha_engine'`).

**Correct:**

```bash
cd /path/to/findtorontoevents_antigravity.ca
export PYTHONPATH=. DB_PASS_STOCKS=...
python3 alpha_engine/outcome_resolver.py --mysql
```

---

## Reproducer commands

```bash
# Honest mutation scan
DB_PASS_STOCKS=... python3 tools/run_mutation_scan_honest.py

# Verified pilots + forward stats
python3 tools/run_verified_pilots_daily.py
python3 tools/etf_forward_stats.py --write

# File-source resolver
python3 audit_trail/universal_pick_resolver.py

# MySQL stale OPEN (hold-window)
AUDIT_DB_PASS=... python3 tools/resolve_stale_open_picks.py --execute --max-batches 10 --batch-size 500

# Outcome resolver (repo root + PYTHONPATH)
PYTHONPATH=. DB_PASS_STOCKS=... python3 alpha_engine/outcome_resolver.py --mysql

# Daily operator bundle
python3 tools/run_eagle_suite.py --skip-swarm

# Health
python3 tools/check_resolver_health.py
```

---

## Next steps (prioritized)

### P0 — Data hygiene (blocks trustworthy /audit)

| # | Action | Status |
|---|--------|--------|
| 1 | **ACTIVE aged-pick resolver** — `resolve_stale_open_picks.py` now scans `OPEN`+`ACTIVE` | **DONE** — 3663 TIME_EXIT on 2026-06-02 ([doc](https://findtorontoevents.ca/updates/2026-06-02-active-stale-resolver-p0.md)) |
| 2 | **Fix health label** — `total_past_hold_window` vs `total_live_picks` | **DONE** — `tools/check_resolver_health.py` |
| 3 | **Normalize writer default** — `mysql_trading_sync.pick_to_row` OPEN default + live ACTIVE→OPEN | **DONE** — [wave 3 doc](https://findtorontoevents.ca/updates/2026-06-02-resolver-hygiene-wave3.md) |

### P1 — Verified edge path (shadow only)

| # | Action | Gate |
|---|--------|------|
| 4 | Daily `run_verified_pilots_daily.py` + `etf_forward_stats.py` | Cron |
| 5 | ETF XLK → first `n_closed` on monthly rebalance | `n_closed ≥ 30` shadow |
| 6 | After shadow PASS → add `etf_verified_dual_momentum` to `PROMOTED_STRATEGIES` | Then optional `PROMOTION_GATE_ENFORCE=1` soak |

### P2 — Research / mutation (no production)

| # | Action |
|---|--------|
| 7 | Weekly `run_mutation_scan_honest.py`; never wire INVERT without promotion gate + forward proof |
| 8 | Investigate `alpha_engine_fast` INVERT cap-99 cohort (209 trades) — mutation analysis export |

### P3 — CI / ops hardening

| # | Action |
|---|--------|
| 9 | CI: `PYTHONPATH` + stale OPEN+ACTIVE + `--mysql` in `outcome-resolver.yml` | **DONE** — [CI hygiene doc](https://findtorontoevents.ca/updates/2026-06-02-resolver-ci-hygiene.md) |
| 10 | Daily cron via `tools/run_daily_resolver_hygiene.sh` | **DONE** — wire on host with `AUDIT_DB_PASS` |

---

## Capital policy reminder

1. **NO-GO** production sizing on policy-clean book (0/9 money-ready).  
2. **Do not** set `PROMOTION_GATE_ENFORCE=1` until allowlist has ≥1 admitted strategy.  
3. **Do not** promote Mimo INVERT mutations to `production_scanner`.  
4. Re-check **14d/48h** recency panels on `/audit` before any class-specific trust.

---

## Links

- Updates card: https://findtorontoevents.ca/updates/index.html (search “PR #465”)  
- Operator steps: https://findtorontoevents.ca/updates/2026-06-02-pr465-merged-post-steps.md  
- Audit dashboard: https://findtorontoevents.ca/audit/  
- Git PR: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/465  
