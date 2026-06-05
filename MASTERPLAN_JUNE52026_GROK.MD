# MASTERPLAN — June 5, 2026 (Grok)

**Author:** Grok (Cursor) — independent deep dive, cross-checked against MySQL + local dashboard JSON  
**Surfaces:** [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit/), [ai_leaderboard.html](https://findtorontoevents.ca/audit/ai_leaderboard.html), [ai-tournament.html](https://findtorontoevents.ca/audit/ai-tournament.html), [pick_funnel.html](https://findtorontoevents.ca/audit/pick_funnel.html)  
**Databases:** `ejaguiar1_stocks` (live picks), `ejaguiar1_backtests` (research archive), `ejaguiar1_backups` (destructive-op snapshots) @ `mysql.50webs.com`  
**Companion doc:** `MASTERPLAN_JUNE52026_CLAUDE.MD` (Opus + swarm) — same diagnosis, different prioritization below  

**Reproduce ground truth:**
```bash
python3 -c "import json;d=json.load(open('audit_dashboard/data/money_ready_verdict.json'));print(d['generated_at']);[print(k,v) for k,v in d['classes'].items()]"
python3 tools/audit_truth_scan.py --live   # staleness + RSPLIT + high-WR flags
# DB (read-only): tools/db_health_check.py, subagent SQL in session notes
```

---

## Executive summary (one paragraph)

The multi-AI prediction stack is **operationally rich but statistically not money-ready**: **0 of 9 asset classes** pass policy-clean Money Ready on data generated **2026-06-05T03:59:54Z**. The gap is not mainly “one more model” — it is **contaminated ledgers, disputed UI surfaces, resolver/backlog drift, and breadth-without-promotion-gates**. Roughly **59% of tournament rows are `MISPRICED_ENTRY`** (4,154 / 7,099). Production `trading_picks` shows **6,966 closes in 90d** with dominant sleeves near coin-flip or negative expectancy. The AI leaderboard book is **frozen** (38 picks, last pick **2026-05-12**). The path to real money is: **freeze noisy emitters → clean write-path → promote only verified sleeves with forward n≥100 → non-LLM feature sleeves in parallel** — not more tournament volume.

---

## 1. Ground truth snapshot (verified 2026-06-05)

### 1.1 Policy-clean Money Ready (`money_ready_verdict.json`)

| Class | n_resolved | WR | PF | Verdict |
|-------|------------|-----|------|---------|
| CRYPTO | 311 | 36.3% | 0.98 | **NOT_READY** |
| EQUITY | 46 | 23.9% | 0.25 | INSUFFICIENT_DATA |
| FOREX | 22 | 22.7% | 11.22* | INSUFFICIENT_DATA |
| ETF | 11 | 63.6% | 0.80 | INSUFFICIENT_DATA |
| FUTURES | 15 | 6.7% | 0.38 | INSUFFICIENT_DATA |
| COMMODITY | 4 | 75.0% | 10.50* | INSUFFICIENT_DATA |
| BOND | 0 | — | — | INSUFFICIENT_DATA |
| UNKNOWN | 8 | 87.5% | 8.51* | INSUFFICIENT_DATA |

\*High PF on **tiny n** + concentration flags — **not sizing-grade**.

- `summary.money_ready`: **[]** (empty)  
- Drift vs 2026-06-04: CRYPTO **n −27**, **WR −2.7pp**; gates **`pbo_ok` / `spa_ok` flipped false**  

### 1.2 PF registry policy-clean net (`pf_registry.json`, same generation)

| Class | n | WR% | PF | Net PnL% |
|-------|---|-----|-----|----------|
| CRYPTO | 311 | 36.33 | 0.977 | −0.58 |
| EQUITY | 46 | 23.91 | 0.250 | −1.18 |
| FOREX | 22 | 22.73 | 11.22 | +0.58 |
| ETF | 11 | 63.64 | 0.801 | −0.31 |
| FUTURES | 15 | 6.67 | 0.384 | −0.14 |

**Tier-2 charter (Goal #1):** PF>1.5, WR>50%, MDD<20%, **n≥100** — **0/6–9 classes pass.**

### 1.3 Recency panels

| File | generated_at (local refresh 2026-06-05) | Note |
|------|----------------------------------------|------|
| `pick_summary_stats_2w.json` | **2026-06-05** | CRYPTO 14d WR ~40%, PF inflated by leakage caveats in JSON |
| `pick_summary_stats_48h.json` | **2026-06-05** | CRYPTO **0 closed / 137 active** — resolver backlog, not sizing-grade |

**Do not size from 48h CRYPTO until closes appear; trust `money_ready_verdict` for class-level decisions.**

### 1.4 AI leaderboard (`ai_leaderboard_index.json`, as_of 2026-06-05T04:55Z)

| Metric | Value |
|--------|-------|
| Picks in book | 38 |
| Resolved | 29 |
| Engines | **1** (`claude-opus-4-7`) |
| Overall WR / PF | 41.4% / 1.79 (n=29) |
| Rank floor | `MIN_N_RANKED=20` — most per-class cells **“building”** |
| Research candidates (specs) | 503 |

Pipeline: `swarm_picks.json` → `tools/ai_attribution/build_ai_leaderboard.py` → `data/ai_leaderboard/`. **Ingestion dead since May 12** — leaderboard cannot inform Goal #1 until revived or tab deprecated.

### 1.5 AI tournament (`tournament_picks`, MySQL)

| status | count |
|--------|------:|
| MISPRICED_ENTRY | **4,154** |
| OPEN | 1,197 |
| LOSS | 890 |
| WIN | 858 |

**Closed pool (WIN+LOSS):** n=**1,748**, aggregate WR **49.1%**, PF **~1.03** (breakeven).

**Per-class closed WR (WIN/LOSS only):**

| Class | n | WR% |
|-------|---|-----|
| ETF | 216 | 57.4 |
| FOREX | 189 | 54.5 |
| COMMODITY | 243 | 53.5 |
| FUTURES | 20 | 50.0 |
| BOND | 314 | 48.4 |
| CRYPTO | 454 | 45.4 |
| PENNY | 45 | 42.2 |
| EQUITY | 266 | 38.3 |

None meet **n≥100 + WR≥55 + PF≥1.5** simultaneously. `tournament_model_stats` last updated **2026-05-22** (~2 weeks stale vs picks).

**Top models (n≥30, by WR):** `kimi_direct` 68.5%, `llm7_qwen` 67.5%, `grok3` 61.5% — still **sub-charter** at pool level; high-WR cells need bias-scrutiny (stale commodity quotes per `reports/deep_audit_high_wr_2026-06-04.md`).

### 1.6 Production `trading_picks` (90d closed, n=6,966)

| Strategy (top by volume) | n | WR% | avg pnl% |
|--------------------------|---|-----|----------|
| luxalgo_confluence | 2,073 | 43.7 | +0.08 |
| futures_momentum | 690 | 34.5 | −0.22 |
| forex_rsi2_mean_reversion | 661 | 45.7 | −0.15 |
| *(blank strategy)* | 457 | 65.4 | +2.73 |
| prediction_market_consensus | 89 | 89.9 | +2.83 |

**90d by category:** crypto **4,858** closes, avg pnl **−0.11%**; forex **1,685**; commodity **834**.

**Dup inflation (30d, same symbol+direction+entry):** e.g. `smart_money_accumulation` AMZN **24×**, AVGO **19×** — distinct from `at_raw_picks` dedup_hash (1.0× there). Production analytics must **dedup by position key** before WR/PF.

### 1.7 `at_raw_picks` ledger warning

90d resolved rows show **absurd sum_pnl** (e.g. FUTURES **+1,001,530%**, CRYPTO **+303,235%**) — unit/scale/resolver contamination in the raw ledger. **Verdict-grade numbers live in `money_ready_verdict` + `pf_registry` policy-clean paths**, not raw `at_raw_picks` sums.

### 1.8 Reverse splits

`at_signal_outcomes.reverse_split_affected=1`: **2 rows** (WKHS, EQUITY). Registry shipped (`audit_trail/reverse_split_symbols.py`). **Not** the main failure mode anymore; **stale quotes + dup rows + MISPRICED tournament** dominate.

### 1.9 Verified / paper-forward sleeves (`verified_edge_status.json`, `pilot_forward_dashboard.json`)

| Track | Forward closes | PF / WR | Status |
|-------|----------------|---------|--------|
| inverse_ml ADA 15m | 36 | 1.73 / 55.6% | Closest crypto forward candidate; **n<100** |
| etf_dual_momentum | 25 | 1.47 / 52% | T2-shaped watch |
| B_flip XRP | 39 | 1.08 / 53.9% | Not enable-ready |
| etf_verified_dual_momentum | **0** forward | Lab WF **PASS** | Shadow only; open XLK |
| crypto_verified_donchian | — | Lab **FAIL** | Blocked |

`any_promotion_ready: false` across pilot dashboard.

### 1.10 Open incidents (feed `2026-06-04 22:23 EDT`, 15 P0 OPEN)

1. **#89** — DB password hardcoded repo-wide (rotate + scrub)  
2. **#49** — money_ready=[] — no class passes gate  
3. **CRYPTO P0** — LONG **33% WR** vs SHORT **67%** (directional bug)  
4. **FOREX P0** — `kimi_signal_tracking` sign-flip **38.7%**  
5. **COMMODITY P0** — COT look-ahead PF **4.6 → 0.51** post-dedup  
6. **STOCKS P0** — EQUITY emission unlocked but **PROBATION**, WR **42%**, PF **0.39**  

---

## 2. Root-cause diagnosis (why months without real-money picks)

| # | Cause | Evidence | Fix class |
|---|--------|----------|-----------|
| A | **Breadth > depth** | 23+ LLM models × personas; pool PF ~1.03 | Freeze tournament ingest 30d |
| B | **Data contamination** | 4,154 MISPRICED; blank strategy n=457; AMZN 24× dup | `clean_ingest_v2` + dedup view |
| C | **Disputed surfaces** | Pick funnel 78.9% CRYPTO banner vs policy-clean 36% | UI truth labels + single trust hierarchy |
| D | **Resolver / backlog** | CRYPTO 48h **0 closes**; EXPIRED mislabels (historical) | Intrabar OHLC + 14d panel regen |
| E | **No promotion gate** | Lab PASS sleeves stay shadow at forward_n=0–39 | Wire `promotion_gate.py` + n≥100 |
| F | **Wrong edge hypothesis** | LLMs price-pattern match without slow features | Funding rate, term structure, VIX regime emitters |
| G | **Class policy** | FOREX hard-disabled 2026-06-04; EQUITY sub-25% WR | Keep frozen until carry-factor criteria met |

**Grok assessment:** This is **70% methodology / data-contract**, **30% engineering**. More models without clean ingest and promotion gates will not produce money-ready picks.

---

## 3. Trust hierarchy (mandatory for humans + agents)

Use **only** this order for capital decisions:

1. **`audit_dashboard/data/money_ready_verdict.json`** + **`pf_registry.json` → `by_asset_class_policy_clean_net`**  
2. **`verified_edge_status.json`** + **`pilot_forward_dashboard.json`** (forward paper, n→100)  
3. **`verified_strategies/paper_pilot/*`** logs (post-harness sleeves)  
4. **AI tournament** — research / paper only, **not** production sizing  
5. **AI leaderboard** — attribution book; **frozen**; illustrative only  
6. **Pick funnel / Smart Picks / HC / ELITE** — funnel diagnostics; **DISPUTED** where banner says so  

**Never** let an external LLM “fetch /audit” and cite WR/PF — feed JSON verbatim (`CLAUDE.md` rule).

---

## 4. 90-day MASTERPLAN (three phases)

### Phase 1 — STOP THE BLEEDING (Days 0–7)

| Day | Action | Owner skill/tool | Done when |
|-----|--------|------------------|-----------|
| 0 | Confirm **FOREX_HARD_DISABLE=1**; no new FOREX emissions | config + GHA | `passes_active_gate` false for FOREX |
| 0 | **Pause** `ai-tournament-pipeline` cron (operator) | `gh workflow disable` | No new `tournament_picks` OPEN rows |
| 0 | File ENHANCEMENT cards for phases 2–3 on `/audit/incidents.html` | `cli_track.py` | 5 cards visible |
| 1–2 | Ship **`tools/clean_ingest_v2.py`**: reject entry drift, RSPLIT pre-date, TP_HIT_REPLAY-only inflates | new tool | Unit test on last 100 `trading_picks` |
| 1–2 | Backup → `ejaguiar1_backups`; create **`trading_picks_v2`** clean view | MySQL migration | Reversible parity report |
| 2–3 | Regenerate **`pick_summary_stats_48h`** + **`pick_summary_stats_2w`** in audit-dashboard workflow | `dashboard_generator.py` | `generated_at` within 2h of deploy |
| 3–5 | **CRYPTO directional gate**: production LONG block or 2× score floor until SHORT/LONG WR parity proven | `quality_gates.py` | 14d panel LONG WR ≥45% |
| 5–7 | Revive or **deprecate** AI leaderboard tab; if revive, daily `swarm_picks` ingest cron | `build_ai_leaderboard.py` | >100 resolved picks / 30d OR tab marked deprecated |

### Phase 2 — BUILD REAL EDGE (Days 8–45)

| Workstream | Deliverable | Success metric |
|------------|-------------|----------------|
| **2A Non-LLM features** | `tools/feature_signals/{funding,term_structure,vix_regime}.py` → `feature_signals` table | 30d head-to-head WR vs tournament; PF≥1.2, n≥50 |
| **2B Promotion gate** | `audit_trail/promotion_gate.py` + `promotion_gate_rejections` table | 0 production writes without 6 checks (§4.1) |
| **2C Paper pilots** | Top 3 forward tracks only: **inverse_ml ADA 15m**, **etf_dual_momentum**, **etf_verified** shadow | Forward n→100; PF≥1.5, WR≥50% |
| **2D Dedup analytics** | `trading_picks_deduped` view for dashboard PF | luxalgo WR within 5pp of deduped truth |
| **2E Bias scrutiny** | Nightly `mlflow_bias_detector` on WR>60% cells | Auto-incident WINDOW_ARTIFACT |

**Promotion gate checks (Action 4 — adopt):**
1. n ≥ 100 closed (real-time, not backfill)  
2. WR ≥ 55% on last 100  
3. PF ≥ 1.4 on last 100  
4. Walk-forward OOS PF ≥ 0.85 × IS PF  
5. DSR ≥ 0.80 (statsmodels → mlflow)  
6. Two-regime: WR drop ≤15pp between VIX high/low  

### Phase 3 — PROVE OR KILL (Days 46–90)

| Track | Capital | Kill switch |
|-------|---------|-------------|
| **Live-or-die basket** | 7 micro-edges from bias-scrutiny PASS (QQQ/SPY/USDCAD/NEAR/BTC-SHORT/SHY/TLT) @ **0.25%** risk | DD>15%, 3 losing weeks, or forward WR<55% (n≥30) |
| **Best feature sleeve** | Winner of 2A @ **0.5%** if Phase 2 PF≥1.5, n≥100 | Same kill |
| **Best paper pilot** | First sleeve with `promotion_ready=true` | Revert to shadow on any P0 |

**Day-90 decision tree:**
- **≥1 sleeve** passes Tier-2 on policy-clean → enable **quarter-Kelly** production scanner flag  
- **0 sleeves** → shut LLM tournament permanently; external vendor signal or feature-only stack  
- Partial → extend paper 30d, no live capital  

---

## 5. Parallel swarm execution map

Use **`/ParallelSwarm`** or **`/consult-multi`** to divide:

| Agent / provider | Task | Output |
|------------------|------|--------|
| **DB agent** | `clean_ingest_v2` parity + dup view SQL | `reports/clean_ingest_parity_*.md` |
| **Gate agent** | `promotion_gate.py` + tests | PR + pytest |
| **Feature agent** | funding + term structure emitters | `tools/feature_signals/*` |
| **UI agent** | template.html stale CRYPTO text; funnel DISPUTED banner | `audit_dashboard/template.html` only |
| **Consult ring / NVIDIA** | Review promotion gate math | `swarm_runs/goal_june5_*.md` |
| **Reviewer** | `code-reviewer` on PR before merge | block if no wire-up |

**LiteLLM proxy** (`http://localhost:4000/v1`, `free-mode` / `free-mode-fast`): cheap triangulation; **paid** (DeepSeek/xAI) for gate math disputes only.

---

## 6. Kill / keep / freeze list

### Freeze (30 days)
- LLM tournament ingestion  
- EQUITY production sizing (PROBATION trust tier)  
- FOREX (already hard-disabled)  
- Any dashboard cell with **n<20** labeled “building” / not rank-eligible  

### Kill or demote
- **PENNY_STOCK** class for production (42% tournament WR, split noise)  
- Historical claims on `tournament_picks` before **2026-06-04** bias-scrutiny pass  
- **`stocks_rsi2_pullback`** as “edge” (INCIDENT #96: ~34% WR deduped)  
- **`prediction_market_consensus`** 89% WR sleeve until n≥100 deduped audit  
- Compounded headline metrics (use `total_pnl_pct_compounded_rolling_100` only)  

### Keep
- `money_ready_verdict` + policy-clean PF path  
- Resolver intrabar OHLC (ported 2026-06-04) + per-class drift in `price_tracker.py`  
- `reverse_split_symbols.py` + RSPLIT badges  
- mlflow + statsmodels local experiments  
- Paper pilots with explicit `promotion_ready` booleans  
- mutate-before-kill (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`)  

### Defensible sleeve (monitor, do not size up yet)
- **`luxalgo_confluence` CRYPTO** — deduped n≈381, WR≈64%, PF≈2.36 per `reports/deep_audit_high_wr_2026-06-04.md`; dashboard still marks OVERFIT_LIKELY at low n — **needs forward paper 100 closes post-clean_ingest_v2**  

---

## 7. UI / dashboard debt (Goal #1 surfaces)

| Page | Issue | Fix |
|------|-------|-----|
| `/audit/` | Static CRYPTO copy (~39% WR) vs live JSON 36.3% | Regenerate from `dashboard_generator` |
| `/audit/pick_funnel.html` | DISPUTED 78.9% CRYPTO | Point to policy-clean table + “as_of” |
| `/audit/ai_leaderboard.html` | 1 engine, stale book | Stale banner (shipped) + ingest or deprecate |
| `/audit/ai-tournament.html` | 59% MISPRICED rows | Banner: “not money-ready universe” |
| Recency panels | 7d stale | CI path registry: add pick_summary to hourly job |

---

## 8. MySQL hygiene checklist

- [ ] Rotate credentials per **INCIDENT #89**; scrub git history  
- [ ] Sync `tournament_model_stats` after each tournament resolve batch  
- [ ] Fill blank `strategy` on 457 `trading_picks` rows  
- [ ] Materialized view: `trading_picks_deduped` (position key + 1h window)  
- [ ] Confirm `ejaguiar1_backtests` creds via `get_backtests_creds()` (not stocks user)  
- [ ] Nightly `tools/cross_db_consistency.py` green  

---

## 9. Success criteria (goal done)

This masterplan is **achieved** when all are true:

1. **`MASTERPLAN_JUNE52026_GROK.MD`** committed and linked from `updates/index.html` card (before INCIDENTS marker)  
2. **Phase 1** complete: tournament paused, clean ingest pilot, recency JSON <24h stale  
3. **≥1 sleeve** reaches forward **n=100** with PF≥1.5, WR≥50% on policy-clean path  
4. **money_ready** contains ≥1 class OR documented kill pivot to feature-only stack  
5. AI leaderboard either **>100 resolves/30d** or tab marked **deprecated**  

---

## 10. Differences vs Claude masterplan (same day)

| Topic | Claude Opus plan | Grok plan |
|-------|------------------|-----------|
| Tone | “No durable edge” — kill prediction engine risk | Same diagnosis; **explicit keep** luxalgo + ADA forward track |
| Priority #1 | Freeze tournament + 7 micro-edges | Freeze + **clean ingest before** micro-edge live-or-die |
| Leaderboard | Not emphasized | **Revive or deprecate** — frozen book is a trust bug |
| DB finding | MISPRICED + incidents | Adds **at_raw_picks sum_pnl unusable**, **trading_picks dup clusters**, **tournament_model_stats stale** |
| FOREX | Kill class | **Already disabled** — hold until carry-factor criteria |

**Recommendation:** Execute **both** plans’ Phase 1 overlap (freeze tournament, clean ingest, promotion gates); use Grok §5 swarm map for parallel staffing.

---

## Appendix A — Key file paths

| Purpose | Path |
|---------|------|
| Verdict | `audit_dashboard/data/money_ready_verdict.json` |
| PF registry | `audit_dashboard/data/pf_registry.json` |
| AI leaderboard index | `audit_dashboard/data/ai_leaderboard/ai_leaderboard_index.json` |
| Swarm picks source | `audit_dashboard/data/swarm_picks.json` |
| Verified edge | `audit_dashboard/data/verified_edge_status.json` |
| Paper forward | `audit_dashboard/data/pilot_forward_dashboard.json` |
| Gate code | `audit_trail/quality_gates.py`, `tools/dashboard_hc_rules.py` |
| Resolver | `alpha_engine/outcome_resolver.py`, `audit_trail/universal_pick_resolver.py` |
| Truth scan | `tools/audit_truth_scan.py` |
| DB creds | `tools/db_env.py` (never commit `dbpasses.txt`) |

---

---

## Progress log (Grok session)

| When (UTC) | Item | Status |
|------------|------|--------|
| 2026-06-05 | Phase 1–2: clean_ingest_v2, promotion_gate tier2, CRYPTO LONG block, feature_signals | Shipped (`b9ffae732c` area) |
| 2026-06-05 | Recency JSON refresh (`build_recency_summary.py`) | Local + deploy pick_funnel |
| 2026-06-05 | luxalgo forward truth: n=827 deduped, WR 42%, PF 0.97 → **SHADOW** | Pilot state `promotion_status=SHADOW` |
| 2026-06-05 | `inverse_ml_ada_forward_pilot.py` + tier2 on DB/virtual | Virtual n=0; bootstrap n=36 in pilot JSON |
| 2026-06-05 | `tools/forward_n100_tracker.py` | `reports/forward_n100_tracker_latest.{json,md}` |
| 2026-06-05 | `PROMOTED_STRATEGIES` | **Empty** (intentional) |

---

*Generated 2026-06-05 by Grok deep-dive session. Re-derive all numbers before sizing decisions — do not trust this table if `generated_at` on verdict JSON is >24h old.*