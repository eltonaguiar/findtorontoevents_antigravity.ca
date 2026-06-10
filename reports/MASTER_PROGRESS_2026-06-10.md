# MASTER PROGRESS — Top-Notch Picks Per Asset Class (12h run, 2026-06-10)

Live log for the autonomous run. Plan: `~/.claude/plans/greedy-mixing-puppy.md`. Endorsed by Mercury, Mercury2, Grok ("execute as written") + DeepSeek (convergent root-cause). Cadence: progress every 5-15 min.

## ROOT CAUSE (why months of sub-coin-flip picks)
The project optimized for months against a **corrupted measurement layer** (inaccurate resolver → 23-24% inflated WR; backfill/label contamination; scale-corrupt PFs; over-emission + single-source concentration; promotion on raw not intrabar-true; no per-class entry criteria). Fix order: honest measurement → clean data → correct gates → grow honest n → THEN per-class edge.

## DONE (this session, committed to main)
- **PR1** entry-anchored intrabar resolver in `universal_pick_resolver.py` behind `RESOLVER_ENTRY_ANCHORED` (default OFF=byte-identical) + harness 15/15 green. (36cdfbfc04)
- **#559 MERGED** — geometry guard in the HOURLY `outcome_resolver.py` (the `outcome-resolver.yml` cron resolver) — complementary to PR1; closes the +5548%-fake-pnl class there. (reviewed correct; backfill-half redundant-but-harmless)
- **#557 CLOSED** — its backfill chk-guard was INVERTED (regression) + pillar-cols already identical on main.
- **#556** was merged by a peer; verified main is **clean of the money_ready_picks_generator password leak** (my scrub 104753d8ab survived). `.agents/skills/` (56 docs) came in — not a security issue.
- **Security scrub**: money_ready_picks_generator.py + sign_flip_purge.py cleaned (env/db_env). Scale-corrupt rows quarantined (CRYPTO raw PF 13.6→1.02). Concentration P0 fail-closed. Status GREEN.
- **Debate** (meta→adversarial rounds) on the PR2 plan → REVISE with 11 must-fixes (folded into v2 plan).

## KEY FINDING (picks-now "closest edge candidates")
- `stocks_rsi2_pullback` EQUITY: page shows 5/6 gates pass, RECENCY FAIL. **RECENCY FAIL is a STALE-DATA bug** — live DB has 351 equity picks in 8d (last TODAY); `picks_now.json` is stale (2026-06-09). BUT its 58.8% WR/PF2.68 is the **inflated pre-intrabar number**; honest (INCIDENT #96 dedup) = n140 WR 33.9% LOSING. → NOT a real money-ready; the apparent near-readiness is stale+inflated scoreboard. Confirms PR2 is the unlock.
- `GBPUSD=X` FOREX forex_rsi2 (n114/58.8%/recency✓, PF/DSR unknown, single-source) + `RENDERUSDT inverse_ml` CRYPTO (n15/80%/PF7.7, small-n, emitting) = the other two closest; both need honest PF + n.

## REMAINING SECURITY
- 2 root-level scratch leaks still on main: `investigate_tp_sl_bug.py`, `investigate_tp_sl_bug_v2.py`. → scrub/delete.
- **OPERATOR ACTION (only they can): ROTATE 50webs DB passwords** — already in git history (#556 branch + docs).
- The DB-password-leak-guard CI should be a REQUIRED check (it failed on #556 yet #556 merged).

## NEXT (prioritized)
1. WS-D: refresh stale data — `dashboard_data.json` (5d), `pick_funnel_today/90d.json` (12.8d), `picks_now.json` (1d+ + stale recency) → trigger regen workflows; add missing `generated_at` stamps. (Makes the picks-now recency gate accurate.)
2. WS-B: PR2 entry-anchored shadow-diff (clean snapshot, per-class before/after incl. high/low-conf split per Mercury) → if sane, default ON. Wire money_ready_verdict to the intrabar ledger.
3. WS-B: grow honest n (crypto_ohlcv 180d backfill, 709 NULL-pnl recovery, 82 blank asset_class) — each in a txn w/ row-count sanity + backup.
4. WS-A: scrub investigate_tp_sl_bug*.py; #553 rebase+gitignore picks_now.json+keep clean scripts; GHA fixes (CI Tests timeout, edge-stability push race).
5. WS-C: re-baseline per-class on the post-PR2 cohort; forward-track leads (shadow-only).
6. WS-E: updates/index.html card + FTP deploy; loop.

## RISKS (per peer reviews — mitigations adopted)
Bulk DB mutations → txn + row-count sanity + rollback + backup (Mercury #1). Keep per-class leads shadow-only until 30-60 forward-resolved post-cleanup. n≥100 + DSR + WFE before any T2 claim. Don't flip a class to money-ready on stale/inflated numbers (the stocks_rsi2_pullback trap).

## TICK 04:00-04:25 — PR2 SHIPPED (the headline)
- **PR2 LIVE (0bac396a88): entry-anchored intrabar resolution is now the production DEFAULT.** Shadow-diff PASSED all pre-registered gates (T1 flip-rate 29.4%<=30, T2 close-approx flips 78%<=90, T3 no class WR inflation; 400 open picks, prod-style fetch; conf-band split: flips concentrate in low-conf). Report 8e7c12bac8, harness 21f7088631. Rollback: RESOLVER_ENTRY_ANCHORED=0. Historical rows: left + dispute banners (recorded).
- **Credential scrub COMPLETE** — repo-wide .py zero leaks (b7d88a97ab, 0caef8edd9). OPERATOR: rotate 50webs pw.
- **Regens:** pick_funnel 12.8d->today ✓, dashboard_data 5d->today ✓, picks-now still running.
- **Copilot/DeepSeek 482-line plan TRIAGED through the validation layer:**
  - REJECTED: stocks_rsi2_pullback promote ("58.8% n=894") — direct SQL: RAW 40%/PF0.83 losing; TP/SL-only = 100% TP / 0 SL ever = close-walk labeling artifact; intrabar-true n=5. Honest perf UNKNOWN; let PR2-honest n build.
  - REJECTED: CRYPTO SHORT-direction flip at sync layer — global-inversion premise previously refuted (w0fkolehf + live audit); destructive risk.
  - ADOPTED: TSMOM/academic sleeves as forward_test_only shadow; FDR re-run (stale Apr 6); crypto_ohlcv 180d; blueprint_generator verify-before-fix.
- NEXT TICK: verify picks-now regen done; wire money_ready_verdict to intrabar ledger; TSMOM shadow wiring; FDR re-run; #553 cleanup.

## TICK 04:10-04:20 — verdict wired to honest ledger
- **money_ready_verdict wired to intrabar truth (110722812e):** per-class `intrabar_truth` block (at_signal_outcomes.intrabar_*) + the missing top-level `generated_at` (fixes index.html/freshness '?'). Scratch-verified before commit; verdict gates unchanged this pass (re-baseline flips inputs later).
- **HONEST-DATA UPDATE: EQUITY crossed n>=100 and FAILS** — intrabar n=104, WR 34.6%, PF 0.48 (the earlier 60%/PF2.13 n=55 "closest lead" dissolved as honest n grew; matches main commit d4ce42658b "EQUITY lead dissolves"). First class to reach honest n>=100 confirms: no edge yet anywhere; supply+time thesis holds. COMMODITY intrabar n=81 PF 1.77 is now the most PF-promising sub-100 class.
- **PR2 confirmed ON origin/main** (Cursor's "branch-only" delta was their stale fetch). Cursor FIXIT review otherwise converges; adopted its queue.
- **Peer coordination:** freebuff active on the shared tree/branch (picks-now LIVE-PnL + tools/live_pnl_tracker.py) — I stay on Contents-API commits, hands off their files.
- NEXT: trigger verdict regen workflow (live JSON gets intrabar_truth), TSMOM shadow wiring, FDR re-run, #553 cleanup, updates card.

## TICK 04:25-04:50 — hidden-gem sweep + DEFINITIVE edge proof + new P0 fixed
- **72h MD sweep (subagent, 35,885->~106 unique reviewed):** Top-10 genuinely-open gems extracted; full list in the sweep output. Highest-value: PBO=1.0 global promotion blocker computed on PRE-fix June-2 data (blocks ALL classes; regen = cheapest cross-class unlock); profitable_filtered_observer orphan; bollinger_squeeze MUTATE candidate (WR 52.9%/PF 0.10 = geometry-kill); EQUITY cohort wrong-class rows retag; picks-now ROOT bug; pead_equity shadow flag OFF; Option-A remaining callers; crypto_ohlcv full-universe (1,173 no_data). Also: 14 looks-like-gems explicitly marked DONE/REFUTED so nobody re-litigates.
- **DEFINITIVE EDGE AUDIT (subagent, 1,278 slices, Bonferroni-disciplined): NO hidden repeatable edge survives.** Sole triple-pass (alpha_engine×CRYPTO 80.6% WR) = synthetic-pnl artifact (quantized constants, conf=0.77 everywhere, midnight closes, 7 symbols re-emitted). Best honest candidate: kimi_signal_tracking n=156 59.6%/PF1.89 p=0.0099 = CANDIDATE-WATCH (needs ~250 more n or intrabar). trust_score=7 "85.9%" prior claim REFUTED (43.3%/PF0.64 deduped). NARROWING TEST: excluding bottom-3 bleeders lifts PF to 1.16-1.80 in most classes BUT every narrowed slice FAILS the time-split — mechanically profitable, repeatable NOWHERE.
- **WHY-NOT-PROFITABLE proof (per class):** (a) resolution drag — 60-98% TIME_EXIT so TP/SL geometry never expresses; (b) zero payoff asymmetry (avg win ≈ avg loss at sub-50% WR); (c) corruption flipping class signs. 79% duplication in raw terminal rows (43,392 -> 9,199 groups).
- **NEW P0 FIXED: 93 wrong-symbol exit-price contamination rows QUARANTINED** (backed up -> ejaguiar1_backups.trading_picks_xsymbol_contam_quarantine_20260610T042907Z). Pattern: BTCUSDT "TP_HIT +79-98%" rows whose exits actually crashed 80-98% — sign-flipped fake wins flipping CRYPTO/EQUITY/BOND class signs.
- **picks-now ROOT->REPO 1-char fix committed (42c5db0c73)** — honesty fields will reach live picks_now.json next refresh.
- **IN FLIGHT (background agents):** σ-scaled TP/SL geometry experiment (the operator's empirical-rule question — tests whether vol-scaled exits cure the proven TIME_EXIT+symmetry diseases; report -> reports/sigma_geometry_experiment_2026-06-10.json); profitable_filtered_observer wire-up (verbatim-anchored, I review+commit).
- **Triage notes:** MiniMax review = convergent, but its "verified edge" table cites already-REFUTED sleeves (futures_momentum 63%, forex_rsi2) — do not act on those rows. AI fleet: LiteLLM:4000 + Ollama:11434 + vLLM now all UP for second opinions.

## TICK 04:50-05:15 — σ-geometry verdict + observer lane live + PBO regen
- **σ-GEOMETRY EXPERIMENT (the operator's empirical-rule question): honest NULL.** Vol-scaled exits (k·σ grid, 783 picks, entry-anchored replay) cut TIME_EXIT (COMMODITY 17.7->7.3%, FOREX 23.5->2.0%) and manufacture aW/aL asymmetry, but **WR drops in exact compensation — net expectancy unimproved or worse in every large class; 0/81 cells clears p<0.005.** ROOT INSIGHT: the losses are DIRECTION/SELECTION losses (wrong-way entries), NOT geometry losses. Exit statistics cannot fix entry selection. → effort redirects to per-class ENTRY criteria (research swarm) + honest n growth. Only weak follow-up: COMMODITY 2.0×0.75 (PF 1.83, R1-fail, 91.7% censored) — re-test after censoring clears, never size. Report: reports/sigma_geometry_experiment_2026-06-10.json.
- **profitable_filtered_observer WIRED (f73fcec34b)** — the P0 "profitable-but-filtered picks not surfaced" incident now records a daily JSONL false-negative lane (observational-only, fully guarded; verbatim-anchored subagent implementation, reviewed + committed).
- **PBO regen (gem #1):** global PBO 1.0 (stale June-2, degenerate) -> 0.8222 on the post-PR2+quarantine cohort (pool honestly 56->17 strategies). Still FAIL>=0.7 — CORRECTLY blocking promotion, consistent with the edge audit's null. The gate is no longer frozen on pre-fix data.
- picks-now ROOT fix (42c5db0c73) + 93-row contamination quarantine logged previous tick.
