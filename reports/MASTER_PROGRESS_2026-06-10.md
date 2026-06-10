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

## TICK 05:15-05:40 — live wiring fixed + deliverables shipped
- **Live verdict diagnosis + fix**: live money_ready_verdict.json had generated_at ✓ but intrabar_truth:null — root cause = the money_ready_snapshot step in audit-dashboard.yml was MISSING DB_PASS_STOCKS (5 sibling steps have it) → _intrabar_truth_map() fail-opened in GHA. Env added (1e1efea80f), regen redispatched; verify next tick.
- **pead_equity gem resolved**: ALREADY enabled in alpha-engine-live.yml (note: early vs its own 2026-06-14 review-gate comment). Shadow-only by design (0 DB rows correct). REAL issue found: shadow log pead_shadow_picks.json is overwrite-mode ("w") → no durable history for the 06-14 review. Queued: make it append/dated before the gate.
- **updates/index.html card SHIPPED + FTP-deployed (8431062f7a, HTTP 200)** — the honest-measurement milestone is publicly documented above the AUTO-INJECTED block per convention.
- **Memory protocol done**: personal memory file + MEMORY.md pointer written (project-honest-measurement-live-2026-06-10); agentmemory POST attempted (server quiet); holographic append deferred (agent_shared_memory.json has live peer edits — avoiding clobber).
- REMAINING QUEUE: verify live intrabar_truth post-regen; #553 rebase+gitignore; pick_funnel Money-Ready/Proven-Only doc gaps; pead shadow-log durability; 709 NULL-pnl + 82 asset_class + ohlcv-universe backfills; entry-criteria research swarm return.

## TICK 05:36-06:00 — surface docs live + pead history durable + local-fleet skill
- **pick_funnel.html: 9/9 filters now documented + DEPLOYED** (f9a629bef2) — added the two gaps: Money-Ready policy-clean sizing gate (n>=100/WR>=50/PF>=1.5 + DSR/PBO/SPA/expectancy/HHI/recency + intrabar_truth; "0/6 pass — nothing sized") and Proven-Only manual registry (_TRUST_PROVEN_*).
- **pead shadow history made durable** — pead_shadow_picks.json overwrote every run ("w" mode), so the 2026-06-14 review gate had no history; now appends per-signal pead_shadow_history.jsonl, persisted by the workflow's `git add alpha_engine/data/`. Verified my 11-line edit was the ONLY local delta on the hot file before committing.
- **/consult-local skill created** (.claude/skills/consult-local) — wraps the now-fully-up local fleet (vLLM :8000 Qwen2.5-14B, Ollama :11434 incl. deepseek-r1:32b + llama3.3:70b, LiteLLM :4000) for second opinions/refutation passes with the repo's anti-fabrication rules baked in.
- Live intrabar_truth: still null — the 04:11 hourly run (pre-env-fix) is in flight with the 05:19 run queued; verification rolls to next tick.

## TICK 05:50-06:10 — honest-n grew +591; #553 closed; selection-attack launched
- **591 NULL-pnl rows RECOVERED** (terminal NULL-pnl 709->131; the 107 remaining are sign-incoherent rows the #559 guard correctly skips). Backup first: ejaguiar1_backups.trading_picks_20260610T055138Z (47,927 rows). Honest n grew accordingly.
- **82-row asset_class backfill: verified ALREADY APPLIED** (idempotency check; manifest ids 0 blank) — peer had landed it; no double-apply.
- **#553 CLOSED as superseded** — all deliverables (picks_now_professional.py incl. newer ROOT fix, save_picks_to_db.py, picks-now.html incl. freebuff LIVE-PnL) already live on main; merging June-6 versions would regress them.
- **ENTRY-CONDITIONING EXPERIMENT LAUNCHED** (background): the σ-experiment proved selection (not geometry) is the deficit, so this tests entry-time features (trend-alignment, momentum, RSI band, vol regime, session) per class on the honest cohort, with the same R1/R2/R3 discipline + negative-selection filters. Report -> reports/entry_conditioning_experiment_2026-06-10.json.
- Live intrabar_truth: the 05:19 run predates the env-fix commit; the fix rides the 05:45 queued run — verify ~06:45.

## TICK 06:10-06:25 — FIRST DISCIPLINED ENTRY-EDGE CANDIDATES (the selection attack pays off)
- **Entry-conditioning experiment returned the session's first R1/R2/R3-passing candidates** (935 deduped honest picks, 101 slices, Bonferroni-honest; DIRECT-SQL VERIFIED within tolerance):
  1. **CRYPTO: RSI(14,1h) 50-70 × US-session entries** — n=84, WR 52.4% (+18.8pp vs 33.6% baseline), PF 1.73; passes time-split (both halves), concentration (top sym 7%), p=3e-4 (family-wise ~0.03); survived ex-ensemble + long-only re-tests. **FORWARD-TEST candidate, not a sizing trigger.**
  2. **Strategy-direction cell: luxalgo_confluence SHORT** — verified n=41, 68.3% WR, PF 1.96 (all-CRYPTO-shorts 63.6% is mostly this cell). NOTE: this is SELECTION (which emissions to take), NOT the rejected Copilot direction-FLIP (mutating picks) — distinction matters.
  3. **Negative entry filters the gates don't check:** EQUITY high-vol entries hold 64.3% of class losses (low-vol remainder 62.9%/PF2.48, fragile n); FOREX trend-contrarian entries hold 75.7% of losses (remainder 64.3%/PF4.74 n=14). MEMECOIN = do-not-trade (nothing conditions it).
- Corroborates the σ-experiment: wrong-way LONG selection is the disease; entry conditioning is the cure path.
- NEXT: spec + wire the shadow entry-gate (forward_test_only stamps: entry_condition_met flags on emissions; verdict-excluded) so forward n accrues on conditions 1-2 + the two negative filters; re-test at n>=100/condition.

## TICK 06:20-06:35 — forward-measurement lane spinning up
- **crypto_ohlcv FULL-UNIVERSE 180d backfill RUNNING** (--top-symbols 0; idempotent upserts of regenerable exchange bars — backup rule applies to trade records, not reproducible market data). Will shrink the 1,173 no_data picks; then re-resolve at_signal_outcomes + rebuild intrabar_truth to grow the honest ledger.
- **Shadow entry-gate stamper DELEGATED** (background build): tools/stamp_entry_conditions.py — read-only DB -> audit_dashboard/data/entry_conditions_forward.json sidecar tracking the validated conditions (crypto_rsi5070_us, luxalgo_short, equity_lowvol/highvol-negative, forex_aligned/contrarian-negative) + per-class baselines + rolling 30d forward windows. Measurement-only; never a sizing input until n>=100/condition re-passes R1/R2/R3.
- Live intrabar_truth: 05:19 run STILL in flight (long hourly build); env fix rides the queued 05:45 run.

## TICK 06:35-06:45 — shadow entry-gate lane COMMITTED
- **tools/stamp_entry_conditions.py + entry_conditions_forward.json on main (6d9b0e1895, 0d79e82138)** — read-only (0 write stmts verified), strict no-look-ahead, mirrors the experiment features. The forward lane already teaches:
  - **crypto_rsi5070_us HOLDS in the forward window**: last-30d n=52, 51.9% WR / PF 1.60 vs CRYPTO baseline 28.9% / 0.55. n=52/100 toward the re-test bar.
  - **luxalgo_short: all-recency** (entire n=37 inside last 30d) — needs time-split before belief upgrade.
  - **EQUITY vol-regime SIGNS FLIPPED vs the experiment snapshot** once full bar history was used — the negative-filter claim is fragile; exactly the failure mode this lane exists to catch.
- OHLCV universe backfill ~halfway (H-symbols); re-resolve + truth rebuild on completion (scheduled).

## TICK 06:45-07:05 — honest ledger +221 (universe backfill chain complete)
- **OHLCV full-universe backfill DONE: 827,882 bars upserted** (315 symbols; 132 failed = delisted/garbage).
- **Re-resolve: +221 new intrabar shadow rows** (built-in backup; canonical untouched; rollback documented).
- **Refreshed honest ledger (committed):** CRYPTO n=1154 (32.4%/PF0.73 FAIL), EQUITY n=107 (34.6%/PF0.47 FAIL) — TWO classes now clear the n>=100 bar and BOTH fail honestly; COMMODITY n=90 / FOREX n=88 approaching. Leads unchanged (futures_momentum n47 — concentration caveat stands; forex_rsi2 n20). The honest verdict is STABLE under data growth — measurement layer working as designed.
- Live verdict intrabar_truth: 05:45 env-fixed dashboard run still in flight; verify next tick.

## TICK 07:16-07:35 — forward lane honest-tracking + sign-flip gate restored
- **crypto_rsi5070_us crossed n=100 (108): WR 47.2% / PF 1.54** (last-30d 49.2%/1.50 vs baseline 28.9%/0.55). Still ~+15pp/3xPF over baseline but WR<50 — the honest call: KEEP MEASURING, do not promote. Sidecar refreshed+committed (9869c9e687). luxalgo_short 38 @ 71.1%/2.21 (recency caveat stands).
- **Sign-Coherence Gate failure diagnosed + FIXED**: not my scrub — the gate correctly caught 2 NEW mega_mutation ADAUSDT sign-flips (stored +3.28%/WON, real -3.48%). Purged via audit_trail/sign_flip_purge.py --apply (backup + manifest committed); re-check = 0 flips; gate redispatched.
- Live verdict intrabar_truth: the 05:45 env-fixed dashboard run STILL in flight (long build) — rolls again.
- Other GHA failures: CI Tests (chronic, known), Picks-Now Live PnL hourly (freebuff's new workflow — theirs), masking/leak-guard (old PR-era runs). Nothing else actionable.

## TICK 08:00-08:15 — 🎯 HONEST TRUTH IS LIVE ON /audit (chain complete)
- **ROOT CAUSE of the frozen live verdict found + fixed — it was MY bug**: the verdict's new top-level `generated_at` STRING crashed money_ready_snapshot.py's validate() ("class 'generated_at' record is not an object"); the `|| non-fatal` guard swallowed it, freezing the live JSON at the 04:21 build. (My earlier "live" probes were also reading the wrong JSON level — the snapshot nests under `classes`.) Fix: meta-strip non-dict keys (23bbf508db). Honest accounting: the GHA env fix was necessary but NOT the blocker.
- **LIVE + VERIFIED on findtorontoevents.ca**: `classes.CRYPTO.intrabar_truth {n:1154, wr:32.4%, pf:0.73}`, `classes.EQUITY.intrabar_truth {n:107, 34.6%, 0.47}` — the full honest chain (entry-anchored resolver -> at_signal_outcomes ledger -> verdict -> live site) is END-TO-END COMPLETE. FTP'd + curl-verified (f7758d157f).
- Sign-Coherence Gate re-run: **GREEN** (post-purge). Money-Ready Snapshot workflow redispatched with the fix.
- Forward lane: crypto_rsi5070_us n=108 47.2%/1.54 (keep measuring, no promote); luxalgo_short 38 @ 71.1%/2.21 (recency).

═══════════════════════════════════════════════════════════════════
## SESSION CLOSE — 12-hour Top-Notch-Picks run (2026-06-10, ~02:00-09:00 UTC core)
═══════════════════════════════════════════════════════════════════

### What this run PROVED (the scoreboard no longer lies)
1. **PR1+PR2: entry-anchored intrabar resolution is the production DEFAULT** — debate-gated (11 must-fixes), shadow-diff-gated (pre-registered T1-T3, PASSED), harness 15/15, instant rollback env. The 23-24% WR-inflation class of bugs is closed.
2. **Definitive edge audit (1,278 slices, Bonferroni)**: NO hidden repeatable edge in the historical data; narrowing lifts PF mechanically but NOTHING survives the time-split. Why-not-profitable proof: 60-98% TIME_EXIT drag + zero payoff asymmetry + corruption (now quarantined).
3. **σ-geometry NULL with the key insight**: losses are DIRECTION/SELECTION losses, not exit-geometry — vol-scaled exits trade TIME_EXIT for WR one-for-one. Effort correctly redirected to ENTRY criteria.
4. **Entry-conditioning: the first disciplined candidates** — CRYPTO RSI(14,1h) 50-70 × US-session (R1/R2/R3-pass; now n=108 @ 47.2%/PF1.54 vs baseline 32.1%/0.72 — tracking honestly BELOW the 50% promote bar); luxalgo_confluence SHORT (n=38 71.1%/2.21, all-recency caveat); negative filters (FOREX contrarian = ~76% of losses; EQUITY vol-claim flipped on fuller data = fragility caught by the forward lane, as designed).
5. **The full honest chain is LIVE**: resolver → at_signal_outcomes ledger (now n=1154 CRYPTO / 107 EQUITY, both FAIL honestly) → money_ready_verdict classes.*.intrabar_truth → findtorontoevents.ca/audit (curl-verified).

### Data hygiene totals (all backed up to ejaguiar1_backups first)
+591 NULL-pnl recovered · 93 wrong-symbol sign-flip rows + 7 scale-monsters quarantined (CRYPTO raw PF 13.6→1.02) · 2 fresh sign-flips purged (gate back to 0-baseline GREEN) · 827,882 OHLCV bars backfilled (full universe) · +221 honest intrabar rows · 82 asset_class rows verified applied · PBO unfrozen 1.0→0.822 · status standardization GREEN.

### Surfaces + plumbing shipped
Live updates card (honest-measurement milestone) · pick_funnel 9/9 filter docs · profitable-but-filtered observational lane (P0) · picks-now ROOT 1-char fix · pead shadow history durable · stamp_entry_conditions forward lane (read-only, no-look-ahead-verified) · consult-local skill · credential scrub COMPLETE repo-wide · #553/#556/#557 all resolved · snapshot meta-strip fix (own-bug, honestly attributed).

### HANDOFF — next session priorities
1. **OPERATOR (only you can): ROTATE the 50webs DB passwords** (history exposure; live code is clean).
2. **rsi5070 re-test at n≥150 across ≥3 regime-weeks** — promote to probation ONLY if WR≥50 & PF≥1.5 & R1/R2/R3 re-pass; it's at 47.2% — let it prove itself or die honestly.
3. **luxalgo_short time-split** once it spans >30d (all-recency today).
4. **COMMODITY (n=90) + FOREX (n=88) cross n=100 soon** — first honest verdicts due within days; do NOT pre-promote on the sub-100 leads (futures_momentum concentration caveat stands).
5. **PR2 historical rows**: decision recorded = leave + dispute banners; optional one-time re-resolve via the documented backup-table path if the operator wants history cleaned.
6. **Option-A leftovers**: thread asset_class/forward_test_only through ml_crypto_predictor/claude_gainer/crypto_signal_engine callers + implement the signal-week dedup (protects DSR/PBO IID).
7. **CI Tests chronic timeout** (33/40 fails — split the suite); Binance HTTP-451 runner flake (region-block) intermittently times out the hourly resolver step — consider a job-level timeout + skip-grace.
8. **MEMECOIN = do-not-trade** (nothing conditions it); EQUITY/CRYPTO honest baselines FAIL — the path remains: honest n + entry-criteria forward lanes, not resurrection of refuted sleeves (the full do-not-relitigate list is in the 72h-sweep section).
