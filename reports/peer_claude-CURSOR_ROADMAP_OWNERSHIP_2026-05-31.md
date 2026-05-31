# Cursor Roadmap Ownership — Consolidated Synthesis

Date: 2026-05-31
Owner: claude (opus-4-7) session
Inputs: 8 section audits (`reports/peer_claude-roadmap-section{1,2,3,4,6,7,8,9-10}_*_2026-05-31.md`)
Note: Section 5 (strategy library) was not produced as a standalone audit; coverage folded into Section 3 (backtest) and Section 4 (stats) where relevant.

---

## 1. Consolidated HAVE / GAP Table (10 cursor sections)

| Section | Cursor recommendation | Our state | Gap | Effort | Priority |
|---|---|---|---|---|---|
| 1. Secure foundations | dbpasses.txt -> Secrets, no hardcoded pw, backup-before-destructive | GH Secrets HAVE (50+), backup helper HAVE (`safe_db_archive.py`), 14 files still hardcode `*1234560`, 6 files still read `dbpasses.txt` | Eradicate hardcoded pw + pre-commit gate + rotate leaked creds | M (1-2d) | P1 |
| 2. Cron pipeline | Add scheduled refresh + EST timestamp + filter logging | 287/331 workflows scheduled (massive); `_fmtEST` wired in template.html; **filter logger ABSENT** | Single fact-pack workflow; `_fmtEST` in dashboard_enhancements.js; greenfield filter-click logger | M | P1 |
| 3. Backtest framework | Backtrader/vectorbt + parallel + look-ahead/survivorship + versioned table | Custom engines (no Backtrader, 19k files); walkforward_validator HAVE; `bt_backtest_runs/_trades` versioned tables HAVE; PRs #156/#170/#284 today | survivorship_guard, lookahead_invariant, multiprocessing fan-out, wire walkforward into live scoring path | L (2-3w) | P0 |
| 4. Stat validation | Binomial+t-test+bootstrap CI Sharpe+MC random+BH FDR+n>=500 | MC (316 files), bootstrap CI, Wilson, PSR/DSR/SPA, FDR (`tools/fdr_control.py`) all HAVE | n=500 floor not enforced (ours=100); CI-excludes-0.5 gate not in verdict; PBO not visible | M | P0 |
| 5. Strategy library | (not audited as standalone) | Heterogeneous; rsi2/dxy_trend_filter/gold_safe_haven wired; skyrocket SHADOW | Catalog + tiering doc; consolidate via `strategy_tier_tracker.py` | M | P1 |
| 6. Portfolio/risk | Kelly<=2%, vol-parity, slippage 5bp, multi-class diversification | Kelly tiers 3/5/8% (EXCEEDS 2%), slippage 5-8bp/class, charter sizer HAVE, 1028 risk-cap refs; **vol-parity MISSING**, 60/64 portfolios single-class | vol_parity_sizer.py; clamp Kelly to 2%; gross-150% gate; per-pick asset_class on portfolios | M | P1 |
| 7. Deploy (k8s/grafana) | Docker+k8s+Prometheus+Grafana+audit_log | audit_log tables STRONG (10+ tables); prometheus skeleton; **no root Dockerfile, no k8s, no Grafana**; live=50webs FTP (no shell) | **DROP k8s/grafana — aspirational, not urgent.** Replace: Slack webhook + audit-log retention cron | S | P3 |
| 8. Governance/docs | Model spec + risk policy + backtest archive + leaderboard methodology + rotation log | 495 .md docs; Charter+Mutation+Investigation strong; methodology family present | `MODEL_SPEC.md`, `RISK_POLICY.md`, `BACKTEST_INDEX.md`, `API_KEY_ROTATION_POLICY.md`, `GOVERNANCE_INDEX.md` | M | P2 |
| 9. Continuous-improvement loop | A/B router + 5% shadow capital + retrain trigger | A/B router HAVE (`ml_gatekeeper/ab_router.py` + 4 test files + CI); **5% capital slice MISSING**; retrain loop unwired | shadow_pilot capital router; weekly A/B->retrain cron | M | P1 |
| 10. Quick-start checklist | 8-item checklist | 0/8 fully done; 4 PARTIAL; 4 MISSING | Treat as scoreboard, drive via P0/P1 items above | — | scorecard |

**Totals:** HAVE=~30%, PARTIAL=~40%, MISSING=~30% across the 10 sections.

---

## 2. Per-Asset-Class Concrete Next Steps

| Class | Today's state | Concrete next step | Acceptance |
|---|---|---|---|
| CRYPTO | PF 1.14 / WR 43% / n=728 (T2 sub); 78.9% Smart-Picks DISPUTED; 14d collapsed 78.9->38%, 48h=0 closed | (a) intrabar resolver fix (T2 blocker); (b) leakage audit on `claude_gainer_st` (3 closed rows); (c) restore daily emission cadence | n>=100 clean post-fix; PF>=1.5 14d window |
| FOREX | PF 0.55 / WR 40% / n=53; USDJPY 55% concentration; `dxy_trend_filter` shipped (PR #275) | Forward-emit data for dxy_trend_filter; require n>=100 observation window before tier reassessment | n>=100 with filter ON; PF>1.2 |
| EQUITY | PF 0.90 / WR 33% / n=33 (FAIL+INSUFF-N); `stocks_rsi2_pullback` un-killed (PR #277); 14d improving 37%->67% WR | Forward emission data for rsi2_pullback; verify EST trading-hours scheduler; archive killed rows | n>=100; PF>=1.5; sustained 14d>=55% WR |
| COMMODITY | PF 0.31 / WR 11% / n=28; CT=F 57% concentration; `gold_safe_haven` wired (PR #278) | Non-COT signal rebuild scope (CFTC release cadence-aware); diversify away from CT=F; commodity-specific resolver verify | n>=100; HHI<0.30; PF>=1.5 |
| BOND | PF 0 / WR 0% / n=8; `bond_connors_rsi2` shadow pilot | 30-day minimum shadow observation; verify TLT/IEF coverage; bond_yield_curve sidecar | n>=30 shadow; sign-of-life PF>=1.0 |
| ETF | PF 11.99 / WR 50% / n=2 (INSUFF-N); `etf_faber_tactical` shadow pilot | Faber 12-month MA test on monthly bars; n>=30 baseline | n>=30; PF>=1.5 stable |
| FUTURES | RESEARCH-ONLY policy stable | No production change. Keep portfolios pinned. Document research-only invariant in `RISK_POLICY.md`. | policy unchanged |
| PENNY/IPO/CHEAP | `skyrocket_detector` SHADOW (PR #256/#228); Gate 0 reject bug | Fix Gate 0 logic; smaller universe; cap notional 0.5% | Gate 0 passes >=10 candidates/wk; n>=30 |

**Cross-class:** all 8 paths depend on the **intrabar resolver fix** (the upstream T2 blocker per project-memory 2026-05-31).

---

## 3. Calibrating Cursor's Stat Gates to Our Scale

**Honest gap:** cursor's plan asks for n>=500 with WR-CI excluding 0.5 and p<0.05. Ours is n>=100 (CLAUDE.md T1/T2 floor + `MIN_N_WIRE`). 5x stricter.

**Two-tier proposal (recommend adoption):**

| Tier | n floor | Eligibility | Capital |
|---|---|---|---|
| Paper-Track | n>=100 | shadow-tracker enrolment; eligible for `/audit` "directionally suggestive" badge | 0% live |
| Live-Capital | **n>=500** + WR p<0.05 + PF>1.2 + Sharpe>0.8 + WR-CI excludes 0.5 + DSR pass | size-up decision; eligible for Tier-1/Tier-2 classification | up to charter cap |

Wording for dashboard: a strategy at n=100 is **directionally suggestive but not statistically robust**. For a $100k paper portfolio, n=100 is enough to start shadow-pilot tracking but NOT enough to size up to real capital. Cursor's n>=500 floor is the **right gate for the live-capital decision**, not for elimination from the candidate pool.

**Action:** keep `tools/baby_dsr_scanner.py:46 MIN_N_WIRE = 100`, and add `MIN_N_LIVE_CAPITAL = 500` separately. Surface both badges on `/audit`.

---

## 4. Top-5 Recommended Actions (ranked by edge-finding leverage)

1. **Per-class shadow-pilot tracker with cursor's full stat-gate stack.** Enforce: WR p<0.05 + PF>1.2 + Sharpe>0.8 + n>=500 + CI-excludes-0.5. Builds on existing `tools/wr_posterior.py`, `tools/sharpe_lower_bound.py`, `tools/block_bootstrap_ci.py`, `tools/fdr_control.py`. New: `tools/shadow_pilot_tracker.py` + `audit_dashboard/data/shadow_pilot_status.json` + dashboard panel. **Leverage:** turns every active strategy into a measurable candidate; aligns with money-ready bottleneck (plumbing) per project-memory.
2. **Filter-click logger** to populate `pick_funnel.html` with empirical filter performance. `data-filter-id` on chips + delegated handler + JSONL append + cron aggregator. **Leverage:** today the funnel page shows configured filters, not effective filters; this exposes which filters survive contact with reality.
3. **Backtest-results archival table + automated archival** from existing walk-forward runs into `bt_backtest_runs` with new `code_git_sha` + `engine_version` columns. Auto-index report at `reports/BACKTEST_INDEX.md` via cron. **Leverage:** 1268 reports without manifest = institutional memory leak; archive makes every prior result queryable.
4. **EST timestamp script applied to ALL /audit pages** (extend PR #285's pattern). 1-line fix in `dashboard_enhancements.js` to call `window._fmtEST` (lines 655/669/735). **Leverage:** cheap, kills "stale dashboard?" peer questions, unblocks remote-AI grounding.
5. **Per-class regime-conditioned analysis** (bull/bear sub-sampling) on top-10 strategies per class. New: `tools/regime_conditioned_backtest.py` consuming existing walkforward outputs. **Leverage:** today's verdicts pool across regimes; CRYPTO 78.9->38% collapse strongly suggests regime-flipped edge. Conditioning will surface true sub-edges or kill false ones.

---

## 5. Honest Framing for the Operator

Today's 10-agent verdict + 3-AI external review converge on **NO_EDGE** across the audit surfaces:
- 0/6 asset classes pass T2.
- 3 of 6 degraded in last 72h.
- The headline 78.9% CRYPTO Smart-Picks number is DISPUTED (4 leakage signals; real 90d = 39% WR / PF 0.37).
- EQUITY/COMMODITY/ETF/BOND all INSUFF-N (n<100).

**Cursor's framework gives a path to RIGOROUS edge detection, but we should be careful not to confuse "framework adopted" with "edge found."**

The framework adoption is multi-week work:
- Section 1 (secure) and Section 7 (k8s/grafana) are governance/operability — they do not produce edge.
- Section 2 (cron + timestamps + filter logging) is observability — it makes existing edge visible, does not create it.
- Section 3 (backtest) and Section 4 (stats) are the only sections that can actually surface edge — and per project-memory, the **money-ready bottleneck is plumbing (resolvers + wire dormant edges)**, not new strategy R&D.

**Recommended sequencing (operator decision):**
- Week 1: actions #4 (timestamps) + #2 (filter logger) — cheap, visible.
- Week 2-3: action #1 (shadow-pilot tracker) — required for any future edge claim.
- Week 4: action #3 (backtest archive index) + action #5 (regime conditioning).
- **Parallel and HIGHEST PRIORITY: intrabar resolver fix** (upstream T2 blocker — outside cursor's framework, internal to our pipeline).
- Defer: Section 7 (k8s/grafana — aspirational), full n=500 enforcement until shadow-pilot tracker has 30+ days of data.

**Bottom line:** cursor's roadmap is a sound external check; it does NOT replace the resolver-fix + plumbing work that's already on the critical path. Adopt the framework but do not let it crowd out the work that actually moves picks toward Tier 2.

---

## Return summary

- sections_audited = 8 (1,2,3,4,6,7,8,9-10; section 5 folded into 3+4)
- gap_items = 30+ concrete items across the 10 sections
- per_class_actions = 8 (CRYPTO, FOREX, EQUITY, COMMODITY, BOND, ETF, FUTURES, PENNY/IPO/CHEAP)
- top5_actions = shadow-pilot tracker, filter-click logger, backtest archive, EST timestamps everywhere, regime conditioning
