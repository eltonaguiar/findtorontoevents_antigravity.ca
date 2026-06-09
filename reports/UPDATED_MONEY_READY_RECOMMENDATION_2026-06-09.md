# Updated Money-Ready Recommendation — 2026-06-09

**Synthesis of:** 4 grounded sub-agents (EQUITY dig, picks-now audit, research_index+FOREX diagnosis, recent-.md scan) + policy-clean trust data (`money_ready_verdict.json` 2026-06-08) + 3 peer-AI artifacts (Mercury `low_hanging_fruit_report.md`, `revised_super_plan.md`, `peer_a_review.md`).

**Bottom line:** The lowest-hanging fruit is **not** a strategy — it's **fixing the resolver/measurement layer**. Every per-class number is currently distorted by backfill contamination + missing intrabar replay + 5×-oversized TP/SL. Promoting any sleeve on today's numbers risks exactly the "loser after loser" outcome we're trying to avoid.

---

## 1. ⚠️ The peer-AI plan chain is built on contaminated data — DO NOT EXECUTE AS-IS

`low_hanging_fruit_report.md` → `revised_super_plan.md` → "Grok approved" → `peer_a_review.md` "green light" is a **cascade of mutual agreement that never checked the policy-clean trust source.** Three of its core recommendations are actively harmful:

| Peer recommendation | Why it's wrong | Evidence |
|---|---|---|
| "stocks_rsi2_pullback: 894 / 58.8% / PF 2.68, only recency blocks it — **lower RSI oversold 35→30 to re-emit**" | The 894 is dup-inflated + period-biased (May 7-20 correction). 14d WR collapsed to **29.9%**. Lowering the RSI threshold **re-opens the falling-knife floodgate** the breadth-throttle (>5) + RSI(14)≥30 floor just closed. | `pick_summary_stats_14d.json`; commit 745b947c1a |
| "FOREX GBPUSD n=114/58.8%, EURUSD n=114/56.1% — already n≥100 & WR≥50%, just **forward-test for PF/DSR**" | Those counts are 10×-dup / batch-artifact inflated. Policy-clean FOREX = **n=25, WR 24%, PF 0.077**. 48h slice is 1W/7L. FOREX is a verified catastrophic FAIL. | `money_ready_verdict.json`; commit cc1f7a89c7 ("10x write-duplication") |
| "RENDERUSDT inverse_ml 80%/PF 7.7 — **synthetic backtest on rolling windows to raise n to 100**" | `inverse_ml_enhanced_RENDERUSDT` is **0% WR on 3 clean live trades** → already moved to PERMANENTLY_KILLED. Rolling-window synthetic n = correlated/overlapping samples = the exact contamination DSR/PBO is built to reject. | auto_tuner.py PERMANENTLY_KILLED (2026-06-06) |

Also: the report calls "V" Vanguard (it's **Visa**), and `peer_a_review.md` suggests "force a new pick if none in 48h" — gaming the recency gate produces junk picks. **None of these go to production.**

The peer methodology (parallel agents, composite ranking) is fine; the **data anchoring and the "manufacture n" instinct** are the failures.

---

## 2. Tier-2 gate failures by asset class (VERIFIED vs `money_ready_verdict.json` 2026-06-08)

The Inception "Tier-2 Gate Failures" table is **substantively correct** but has one error: it omits **`n_ok=False` for EQUITY** (n=71 < 100 *does* fail n_ok), and its takeaway "every class except EQUITY has n<100" is wrong — **EQUITY also has n<100.** Corrected:

| Class | n | WR | PF | Passing gates | Failing gates | Verdict |
|---|---|---|---|---|---|---|
| **EQUITY** | 71 | 53.5% | 1.84 | wr_ok, pf_ok, dsr_ok(1.0), spa_ok, expectancy_ok, cvar_ok, recency_ok, wf_oos_ok | **n_ok(71<100), mdd_ok(33%), bootstrap_ci_ok(CI crosses 0), single_source_ok, pbo_ok(=None/uncomputable), fdr_ok(=None)** | Closest, but ≥5 independent blockers — n-growth alone does NOT fix it |
| **CRYPTO** | 175 | 48.6% | 0.92 | n_ok | wr, pf, dsr(0), expectancy(−0.013), mdd(1.0), cvar, fdr, single_source | Has n, no edge |
| **FOREX** | 25 | 24% | 0.077 | — | all | **KILL/MUTATE** |
| **FUTURES** | 20 | 30% | 1.05 | — | n, wr, pf, dsr, expectancy, bootstrap | Insufficient + no edge |
| **ETF** | 20 | 25% | 0.37 | — | all | Insufficient + no edge |
| **COMMODITY** | 18 | 27.8% | 0.28 | — | all | Insufficient + no edge |
| **CHEAP_STOCKS** | 4 | 50% | 1.03 | — | n + most | Insufficient |
| **BOND** | 1 | 100% | null | — | all | Insufficient |
| **PENNY_STOCK** | 1 | 0% | 0 | — | all | Insufficient |

**Key correction to all prior analyses:** EQUITY's n=71 is itself **misleading** — only ~45 are live forward closes; the rest is backfill (`reports/2026-06-05-LIVE-FORWARD-TRIAGE.md`). So EQUITY needs **~55 more clean LIVE closes**, not 29.

---

## 3. The #1 leverage point: FIX THE RESOLVER (upstream of every class)

Three independent recent audits converge: **the measurement layer is broken, not the alpha supply.**
- Intrabar OHLC replay missing for ALL classes → **56–94% of picks resolve as TIME_EXPIRED** (never touch TP/SL in the snapshot loop).
- **77.8% of `pf_registry` outcomes are backfill-contaminated** (`resolved_at IS NULL` or `backfill_*` labels).
- **Resolver-version selection bias:** same CRYPTO June data → PF 0.51 vs 2.15 depending on resolver version → verdict inversion.
- **TP/SL 5× oversized:** FOREX emits 8%/4% when real moves are <1.5%; caps exist at `picks_now_professional.py:637-639` but aren't propagated to `production_scanner` emitters.

**Fix these and the per-class numbers become trustworthy for the first time.** Tooling already exists (`tools/reresolve_intrabar.py`). This is the true low-hanging fruit because it unblocks EVERY class at once.

---

## 4. Ranked action plan (low-hanging fruit first)

### DONE this session
- ✅ **Banned `multi_asset_scanner`** (dominant FOREX bleeder ~9% WR/PF 0.21; completes the multi_asset_* ban family). Commit on main.
- ✅ Prior: RENDERUSDT inverse_ml killed; breadth-throttle >5 + RSI(14) floor + sector blocklist; smart_money dedup; DXY gate; genome→at_raw_picks bridge; PM-macro overlay; battleground_ml_relaxed_mut promoted.

### P0 — Resolver/measurement (unblocks all classes)
1. **Run intrabar OHLC replay across all 6 classes** (`tools/reresolve_intrabar.py`): resolve TP-vs-SL by first touch, set `resolved_at` + `forward_test_only=1`. Re-measure every class. *(DB/operator-gated — DB unreachable from agent IPs.)*
2. **Propagate per-class TP/SL caps** from `picks_now_professional.py:637-639` into `production_scanner` emitters (FOREX ≤1.5%/1.0%, COMMODITY ~1.5-2%, ETF/BOND right-sized).
3. **Quarantine backfill rows** in `build_pf_registry.py` (`resolver_version LIKE 'backfill%'` + `resolved_at IS NULL`) from all WR/PF/DSR/stability math.

### P1 — EQUITY (the closest class)
4. **Quarantine EQUITY dead weight** via mutation-before-kill: `regime_terminal` (n=17, WR 17.6% — already globally banned) + `cta_replicator` (n=6, WR 0%). Removing both lifts the clean EQUITY cohort to **n≈48, WR 72.9%, PF 5.55** (verified by EQUITY agent).
5. **Give EQUITY a 2nd independent, trusted strategy** so PBO becomes computable and single_source_ok can pass: move `smart_money_accumulation` onto the v2.1 intrabar resolver + fix its `entry_date=None` rows. (Currently EQUITY edge is 57% concentrated in one source — HHI 0.38.)
6. **Refresh stale gate inputs** (`dashboard_data.json` 06-03, `deflated_sharpe_results.json` 06-06) so post-fix EQUITY wins get scored — currently the harness fails the lead strategy on dead late-May crash data. *(operator/DB-gated.)*

### P1 — Wire dormant academic sleeves (AFTER resolver fix)
7. **TSMOM (all classes)** — `tsmom_strategy.py` + `cta_bridge.py` exist, dormant. Exits on trailing-stop/sign-flip → structurally solves the TIME_EXPIRED problem.
8. **Residual momentum (EQUITY)** — `residual_momentum.py`, `equity_qmom_residual.py` in academic sidecar.
9. **Carry + roll-down (FOREX/COMMODITY/BOND)** — `bond_strategy_harness.py` built but unwired.

### P1 — FOREX cleanup (finish the kill)
10. **Wire `apply_emitter_discipline`** into intake OR migrate its FOREX kill-list into `BANNED_SOURCES` — it's coded but orphaned (zero importers) so its FOREX kills never run. Mutate only on the direction/regime axis of a single forward-paper pair; never expand coverage.

### P0 — Security (DB password leak, INCIDENT #89)
11. **26 files hardcode `stocks1234560`.** Create `alpha_engine/db_credentials.py` helper (env → aliases → `~/dbpasses.txt` → FATAL), refactor the 26 sites, add `.github/workflows/db-secret-scan.yml`, operator rotates password last. Ready-to-execute ~2h plan (`HANDOFF_CLAUDE_CLI_2026-06-03.md` §6).

### Display quality (peer-owned file — FLAG ONLY)
12. **picks-now dividend-yield double-multiply** (`picks_now_professional.py` ~line 491, `if div_yield: div_yield *= 100`): yfinance already returns yield as percent → GOOGL 24%, SBUX 260%, PLD 296% shown live, and it wrongly gave 14/20 picks a +5 score bonus. A peer agent is mid-edit on this file and fixed only the FMP fallback path — **the primary yfinance path still needs the fix.** Also: STRONG_BUY labels on negative-upside picks (MU −22%), incoherent "safest" bucket (ARB-USD, no data). *Not edited — peer owns the file.*

---

## 5. How to increase data for low-n classes (the RIGHT way)

Low-effective-n: ETF, COMMODITY, FUTURES, FOREX, CHEAP_STOCKS, BOND, PENNY_STOCK (all n<25 clean).

- ✅ **Forward paper-trade** the one or two T2-shaped sleeves per class with the trusted intrabar resolver, tracking a daily `n_to_t2 = 100 − n_clean_closed` counter. Realistic: ~6-12 weeks per sleeve at honest emission cadence.
- ✅ **Add a 2nd OHLC source** (Alpha Vantage for EQUITY/FOREX, Stooq for COMMODITY, FRED for BOND) so non-CRYPTO picks actually resolve instead of expiring (`tools/ai_tournament/price_tracker.py:438`).
- ❌ **Do NOT** synthesize n via rolling-window/synthetic backtests (correlated samples; fails DSR/PBO; this is what the peer plan proposed). ❌ Do NOT count EXPIRED as resolved. ❌ Do NOT count backfill rows.

---

## 6. Honest verdict

**No asset class is money-ready today.** EQUITY is closest but has ≥5 independent gate failures (not just n). The fastest path to a *trustworthy* money-ready class is: **fix the resolver → quarantine dead weight → grow LIVE n on 1-2 vetted sleeves per class → wire the dormant academic strategies that exit on signal rather than waiting for oversized TP/SL.** The strategy supply already exists and is coded; the measurement layer is the bottleneck.

*Sources: money_ready_verdict.json (2026-06-08), audit_surface_truth.json (2026-06-06), reports/equity_money_ready_path_2026-06-09.md, reports/picks_now_quality_audit_2026-06-09.md, reports/research_index_and_forex_diagnosis_2026-06-09.md, reports/2026-06-05-LIVE-FORWARD-TRIAGE.md, reports/2026-06-06-per-asset-class-edge-reality-and-academic-roadmap.md, HANDOFF_CLAUDE_CLI_2026-06-03.md.*
