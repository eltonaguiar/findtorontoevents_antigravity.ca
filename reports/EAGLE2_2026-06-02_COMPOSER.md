# EAGLE2 Enhancement Plan — Research-to-Production Translation

**Author:** Composer (Cursor Agent)  
**Date:** 2026-06-02  
**Status:** APPROVED FOR EXECUTION (quant memo → engineering backlog)  
**Builds on:** `EAGLE_JUNE2_COMPOSER.md`, `docs/BACKTEST_ADMISSIBILITY_STANDARD.md` (M-108)  
**Live baseline:** policy-clean 0/9 money-ready; 81 PF portfolios (66 open); tournament deepseek_v4 n=208 pf_ci_lo≈2.5  
**NFA — enhancement plan, not a sizing recommendation.**

---

## 0. Problem statement (what we are fixing)

The institution does **not** primarily have a patience problem. It has a **translation problem**:

| Layer | State today | Trust for capital? |
|-------|-------------|-------------------|
| Main `/audit` production book | CRYPTO PF 0.89, EQUITY 0.33, FOREX 0.48 (policy-clean) | **No** |
| AI tournament + `pf.html` | deepseek_v4 / gpt4o / grok3 credible paper edge | **Paper only** |
| `pick_funnel.html` cells | Interesting CRYPTO RR bands; surfaces flagged DISPUTED | **Discovery only** |
| Verified lab sleeves | ETF DM Tier-2; crypto VWAP/Bollinger WF PASS | **Wait forward n≥100** |

**Core failure mode:** research edge ≠ deployed edge. Lab winners are opt-in sidecars; the scanner still emits from a noisy universe with inconsistent validation, concentration artifacts, and resolver/label pollution.

**Portfolio note:** `deepseek_v4__aggressive` is **not empty** (11 open on live JSON). Empty `pf.html` UI → corrupted `?key=` Unicode or stale cache — fixed in `pf.html` 2026-06-02.

---

## 1. North-star outcomes (90-day)

| Metric | Today | Target (D+90) |
|--------|-------|---------------|
| Money-ready asset classes (policy-clean) | 0/9 | **≥1** (ETF first) |
| Production emitters with M-108 artifact | ~5% | **100% of active emitters** |
| Silent / unvalidated strategies in funnel | ~78/88 | **≤15** (rest killed or shadow) |
| CRYPTO policy-clean PF | 0.89 | **≥1.0** (stop bleed) → **≥1.2** (candidate) |
| ETF forward virtual n_closed | 0 | **≥100** with PF≥1.5 |
| Nav surface “edge” without holdout+concentration pass | many | **0 promoted to sizing** |
| EXPIRED→WON / TIME_EXIT zombie rate (FOREX/FUTURES) | elevated | **<2% decisive rows** |
| Tournament→production conflation incidents | ongoing | **0** (hard universe split) |

---

## 2. Enhancement architecture — one pipeline, three universes

```
┌─────────────────────────────────────────────────────────────────┐
│  UNIVERSE A — DISCOVERY (no capital)                            │
│  pick_funnel cells, nav matrix, multi-AI tournament brainstorm  │
│  Output: hypothesis_registry.json entries only                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ M-107 pre-register
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  UNIVERSE B — LAB + FORWARD (promotion candidates)              │
│  rigorous_backtest_harness + walkforward_suite + virtual book   │
│  Output: WALKFORWARD_REPORT.json + forward stats JSON         │
└────────────────────────────┬────────────────────────────────────┘
                             │ promotion_ready + shadow 30d
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  UNIVERSE C — PRODUCTION (capital)                              │
│  production_scanner merge ONLY from verified_promotion_gate     │
│  Sized ONLY from money_ready_verdict policy-clean               │
└─────────────────────────────────────────────────────────────────┘

Parallel track (never auto-merge):
  UNIVERSE T — TOURNAMENT PAPER (ai-tournament + pf.html daily engine)
```

**Rule:** Nothing crosses B→C without `verified_promotion_gate.*_merge_allowed() == True` AND forward gate pass. Nothing in C gets size without `money_ready_verdict` READY.

---

## 3. Phase plan

### Phase 0 — Stop the bleeding (Week 1, P0)

**Goal:** Halt false confidence and capital-adjacent signals from weak/contaminated books.

| # | Action | Owner file / command | Acceptance |
|---|--------|---------------------|------------|
| 0.1 | **Hard zero default sizing** on CRYPTO/EQUITY/FOREX until money_ready flips | `alpha_engine/money_ready_verdict.py`, dashboard copy | No UI implies “ready” when verdict NOT_READY |
| 0.2 | **Depromote top loss sources** — cap or shadow `regime_terminal`, `incubator_gainer`, unverified mercury2 paths | `audit_trail/quality_gates.py`, `production_scanner.py` | CRYPTO/EQUITY top_source_share <40% on new closes |
| 0.3 | **Concentration gate before Smart Picks merge** — reject cells with single_source_share >60% | `alpha_engine/smart_picks_engine.py`, `tools/build_nav_surface_matrix.py` | Smart Picks CRYPTO row cannot pass without deduped multi-source proof |
| 0.4 | **Dashboard honesty strip** — show policy-clean PF alongside any headline WR | `audit_dashboard/template.html`, `strategy_admissibility.json` consumer | Every asset-class card shows raw vs policy-clean |
| 0.5 | **Daily admissibility refresh in CI** | `tools/strategy_admissibility_report.py`, `verified-pilot-daily.yml` | JSON <24h stale on live `/audit/data/` |
| 0.6 | **pf.html key sanitization** (done) | `audit_dashboard/pf.html` | Unicode-corrupted keys resolve correctly |

**Do not wait for Phase 0 to finish before starting Phase 1 pilots.**

---

### Phase 1 — Data integrity & resolver trust (Weeks 1–3, P0)

**Goal:** Fix FOREX/FUTURES “high WR / terrible PF” and disputed cohort pollution so class-level stats become trustworthy.

| # | Action | Owner file / command | Acceptance |
|---|--------|---------------------|------------|
| 1.1 | **EXPIRED→WON audit + fix** | `audit_trail/universal_pick_resolver.py`, `outcome_resolver.py` | FOREX EXPIRED_pos_pnl_share <10% on 14d panel |
| 1.2 | **TIME_EXIT zombie purge** — `futures_connors_rsi2` and similar @ pnl=0 | resolver + `quality_gates.py` BLOCK | FUTURES TIME_EXIT decisive share <5% |
| 1.3 | **Duplicate signal-ts dedup** at insert (not just dashboard) | `alpha_engine/smart_picks_engine.py`, DB constraint doc | dup_groups trend down 50% on 90d CRYPTO |
| 1.4 | **Flicker-dedup policy-clean as canonical** everywhere | `tools/build_pf_registry.py`, all dashboard generators | No doc/code path cites raw `by_asset_class` for sizing |
| 1.5 | **regime_terminal entry_price=0 block** | `pipeline_health.json` flagged — fix emitter | Zero entry_price picks blocked pre-insert |
| 1.6 | **pick_funnel DISPUTED banner auto-refresh** from live DB weekly | `pick_funnel.html`, `pick_summary_stats_2w.json` GHA | Banner numbers match live DB ±1pp |

---

### Phase 2 — Unified validation engine (Weeks 2–6, P1)

**Goal:** One admissibility standard for every strategy — no more `real_data_backtest.py` promotion path.

| # | Action | Owner file / command | Acceptance |
|---|--------|---------------------|------------|
| 2.1 | **`academic_backtest_bridge.py`** — route all RD adapters through harness | new `alpha_engine/academic_backtest_bridge.py` | 31/31 academic strategies callable via harness CLI |
| 2.2 | **Purged WF + embargo** on main WF backtester | `walk_forward_backtester.py` ← harness patterns | Methodology audit Flaw #1 closed |
| 2.3 | **Block bootstrap** replace i.i.d. MC | `verified_strategies/strategy_verification_engine.py`, harness | MC p-values not used alone for promotion |
| 2.4 | **Per-class cost model everywhere** | propagate `DEFAULT_COSTS` from harness | All engine outputs include costed PF |
| 2.5 | **Strategy census + kill list** | `tools/strategy_census.py` (new), `dead_strategies.json` | ≤15 active emitters per class without artifact |
| 2.6 | **CI gate:** PR touching scanner wiring must attach `strategy_admissibility.json` delta | new `.github/workflows/strategy-admissibility-gate.yml` | PR blocked if new emitter lacks WF artifact path |

**Promotion artifact schema (required on disk):**

```json
{
  "strategy_id": "etf_dual_momentum",
  "asset_class": "ETF",
  "stages_passed": [0, 1, 2, 3, 4, 5],
  "oos_pf_net": 1.21,
  "oos_n": 32,
  "forward_n": 100,
  "forward_pf": 1.55,
  "dsr": 0.92,
  "pbo": 0.08,
  "promotion_ready": true
}
```

---

### Phase 3 — Promote proven sleeves (Weeks 3–12, P1)

**Goal:** Move lab edge into production **only** through forward proof — starting with ETF, then crypto filters.

#### 3A — ETF dual momentum (primary candidate)

| Week | Action | Gate |
|------|--------|------|
| 3–8 | Daily `run_verified_pilots_daily.py` + virtual book | forward n→100 |
| 8 | If promotion_ready: `ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=1` shadow | 30d shadow log |
| 10 | If shadow PF≥1.3: `verified_scanner_merge.py` live merge | policy-clean ETF n≥30 |
| 12 | Re-run money_ready_verdict | ETF verdict WATCH or READY |

#### 3B — Crypto VWAP + Bollinger (secondary)

| Week | Action | Gate |
|------|--------|------|
| 3–10 | Hyro WF pilot + `crypto_wf_forward_stats.py` | forward n→100 per sleeve |
| 10 | Enable `CRYPTO_VERIFIED_VWAP_ENABLED=1` only if forward PF≥1.5 | block Bollinger if PF<1.3 forward |
| 12 | **Do not** size aggregate CRYPTO — size **sleeve-only** cohort in registry | CRYPTO aggregate PF still tracked separately |

#### 3C — Faber TAA / carry / equity momentum (mutation track)

| Sleeve | Mutation axis | Kill if |
|--------|---------------|---------|
| Faber TAA | QQQ vs SPY; +10bps costs | forward PF <1.0 @ n=50 |
| FOREX carry | multi-pair + FRED cache mandatory | OOS n still <30 @ D+90 |
| equity 12-1 mom | MDD cap + sector neutral | WF still FAIL after tune |

**Explicitly do NOT promote:** Connors crypto (PF 0.90), Donchian combined WF FAIL, COT post-leakage strategies.

---

### Phase 4 — Tournament bridge (Weeks 6–12, P2)

**Goal:** Harvest tournament edge without contaminating production Smart Picks.

| # | Action | Acceptance |
|---|--------|------------|
| 4.1 | Label all tournament picks `universe=tournament_paper` in DB | zero tournament rows in policy-clean production rollup |
| 4.2 | **Promotion path:** tournament model → extract rule set → M-108 lab sleeve → forward book | deepseek_v4 rules extracted as hypothesis, not raw pick copy |
| 4.3 | `pf.html` roster health widget — open count, last daily run | 15 empty portfolios explained in UI |
| 4.4 | Pick_funnel **PROVEN cell → hypothesis** auto-ticket | CRYPTO RR1.0-1.5 LONG cell gets registry entry + harness run |

**Never:** copy tournament picks directly into Smart Picks / money-ready surfaces.

---

## 4. Per-class enhancement playbook

| Class | Primary action | Mutation? | Invert? | Timeline |
|-------|----------------|-----------|---------|----------|
| **CRYPTO** | Route production through VWAP/Bollinger sleeve; depromote incubator/battleground bulk | Filter cell RR band as scanner gate | No class invert | Stop bleed W1; sleeve proof W12 |
| **EQUITY** | Kill/cap `regime_terminal`; Faber shadow | Faber QQQ + costs | No | Honest fail until W8+ |
| **ETF** | **Promote dual momentum** after forward n≥100 | Sector basket widen | No | **First money-ready candidate W10–12** |
| **FOREX** | Fix EXPIRED mislabels first; then carry pilot | Multi-pair carry | Per-pair invert only after OOS proof | Data fix W3; edge W12+ |
| **COMMODITY** | Vol-scaled cross-mom; no COT | Drop ZC=F (done v4) | No | Insuff sample — W12+ |
| **FUTURES** | TIME_EXIT resolver fix; block connors zombie | N/A | No | Artifact cleanup W3 |
| **BOND** | HYG/LQD momentum forward pilot | Credit Faber tune | No | W12+ |

---

## 5. Concentration & “fake edge” defenses (cross-cutting)

Implement in **`smart_picks_engine.py`** + **`build_nav_surface_matrix.py`**:

1. **Single-source cap:** no surface row passes if top `source_system` share >60% (already flagged — **enforce block**).
2. **Symbol cap:** no class sizing if top symbol share >25% without explicit override doc.
3. **Holdout mandatory:** nav matrix `is_edge=true` requires holdout PF≥1.2 **and** Bonferroni — already computed; **wire to promotion**.
4. **14d recency panel veto:** if 14d PF<1.0, auto-demote 90d PROVEN cell to WATCH.
5. **Train/holdout gap flag:** train_pf − holdout_pf >2.0 → overfit badge, block merge.

---

## 6. Mutation & inversion policy (selective, not blanket)

Reference: `docs/MUTATION_THREE_AXIS_PROTOCOL.md`

| Candidate | Axis 1 (signal) | Axis 2 (risk) | Axis 3 (universe) | Invert? |
|-----------|-----------------|---------------|-------------------|---------|
| Faber TAA | QQQ/TLT mix | 10bps slip | Drop weak months | No |
| Commodity TSMOM | Vol-scale | Drop ZC=F | 63d mom / 5d reb | No |
| CRYPTO RR cell | Gate scanner to RR1.0-1.5 LONG only | TP/SL from virtual book | Exclude incubator_gainer | Test invert on **one** symbol only |
| Connors crypto | — | — | — | **Kill — loss skew** |
| FOREX carry | Add AUD/JPY/EUR pairs | Widen stop | FRED cache required | No |

**Inversion allowed only when:** OOS inverted PF≥1.3, original PF<0.7, symmetric costs, n≥50 — logged in `hypothesis_registry.json` as separate hypothesis ID.

---

## 7. Metrics dashboard (weekly quant standup)

Pull from:

```bash
python3 tools/strategy_admissibility_report.py --write --fetch-live-portfolios
python3 alpha_engine/money_ready_verdict.py --json
python3 tools/pilot_forward_dashboard.py
```

| KPI | Source | Red threshold |
|-----|--------|---------------|
| policy-clean PF by class | `money_ready_verdict.json` | PF <1.0 on n≥50 |
| forward n / PF per sleeve | `pilot_forward_dashboard.json` | n<20 @ W6 |
| concentration flags | `pick_summary_stats_2w.json` caveats | single_source >60% |
| portfolio open rate | `strategy_admissibility.json` | <60/81 without explanation |
| silent strategies | strategy census (Phase 2.5) | >20 silent |
| resolver backlog | `tools/db_freshness_check.py` | overdue >500 |

---

## 8. Workstream owners & dependencies

```
Phase 0 (stop bleed) ──┬──> Phase 1 (resolver) ──> Phase 2 (harness)
                       │                              │
                       └──> Phase 3A ETF pilot ────────┘
                       └──> Phase 3B crypto pilot ────┘
Phase 4 (tournament) ────── parallel after Week 6
```

| Workstream | Primary files | Depends on |
|------------|---------------|------------|
| Admissibility CI | `strategy_admissibility_report.py`, GHA | Phase 0.5 |
| Resolver integrity | `universal_pick_resolver.py`, `outcome_resolver.py` | — |
| Harness unification | `academic_backtest_bridge.py`, `rigorous_backtest_harness.py` | Phase 1.4 |
| ETF promotion | `etf_verified_dual_momentum.py`, `verified_promotion_gate.py` | forward n≥100 |
| Crypto sleeve | `crypto_verified_wf.py`, `walkforward_suite.py` | harness + forward |
| Dashboard honesty | `template.html`, `pick_funnel.html` | admissibility JSON |
| Tournament isolation | `tools/portfolios/run_daily.py`, DB schema tag | Phase 4.1 |

---

## 9. Immediate next 7 days (action checklist)

- [ ] **P0** Merge concentration block into Smart Picks gate (0.3)
- [ ] **P0** Shadow/cap `regime_terminal` + `incubator_gainer` on new emissions (0.2)
- [ ] **P0** EXPIRED→WON forensic on FOREX 14d cohort (1.1)
- [ ] **P1** Scaffold `academic_backtest_bridge.py` with 3 pilot adapters (equity/etf/crypto) (2.1)
- [ ] **P1** Daily pilot cron green + forward dashboard on live FTP (0.5)
- [ ] **P1** Register CRYPTO RR1.0-1.5 LONG cell as hypothesis H-ETF-CRYPTO-RR (4.4)
- [ ] **P2** `pf.html` empty-state copy: distinguish 404 vs zero-position vs Unicode fix (4.3)

---

## 10. Success definition (quant sign-off)

We declare **Phase 3 complete** when **all** are true:

1. **≥1 asset class** `money_ready_verdict` = READY or WATCH with policy-clean PF≥1.5, n≥100.
2. **Zero** production sizing from raw registry, nav matrix, or tournament PF alone.
3. **Every** active `production_scanner` emitter has M-108 artifact on disk.
4. **FOREX/FUTURES** mislabel rates below red thresholds (§7).
5. **Forward book** for promoted sleeve matches lab OOS within 15% PF drift.

Until then: **tournament and pick_funnel remain research; `/audit` policy-clean remains the only capital surface.**

---

## 11. References

| Doc | Path |
|-----|------|
| EAGLE1 quant review | `reports/EAGLE_JUNE2_COMPOSER.md` |
| Root-cause long form | `reports/quant_strategy_root_cause_review_2026-06-02.md` |
| M-108 standard | `docs/BACKTEST_ADMISSIBILITY_STANDARD.md` |
| Methodology flaws | `reports/backtesting_methodology_audit_2026-06-02.md` |
| Live machine report | `audit_dashboard/data/strategy_admissibility.json` |
| Mutation protocol | `docs/MUTATION_THREE_AXIS_PROTOCOL.md` |

**Final line:** Fix translation, not clock-watching. Promote ETF dual momentum first; bleed-stop CRYPTO/EQUITY/FOREX; never confuse tournament paper edge with production money-ready edge.
