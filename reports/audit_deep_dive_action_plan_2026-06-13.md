# Audit Deep Dive Action Plan & Todos — 2026-06-13 (Pass 132 continuation)

**Goal #1 Priority:** Phenomenal /audit performance across ALL asset classes. Tier-2 min (PF>1.5/WR>50/MDD<20/conc<35/CI LB>1.15/forward n_eff>=80 clean). Current: 0/10 classes pass (policy-clean-net/intrabar). Focus: COMMODITY (weak n=12 policy net wr=33.3 pf=0.82, intrabar n=115 wr~34.8 pf~1.05) + CRYPTO (n large but sub-T2, velocity on good 15 CONDITIONS like crypto_rsi5070_us n=108 wr=47.2 pf=1.535 l30 48.3/1.454 retention lift). Velocity principle (replay for discovery, forward for confirm). Master loop: MEASURE-DIAGNOSE-ACT-FORWARD-RATCHET. Scheduler 019ebf514e5b for constant 15m digs. One-sided pathology (FINDING#12: 33 strats 100% one-sided from bad external: reddit/copy/gnews/currents/stocktwits/youtube hype/spam — H4/H5). Hygiene extensions done in quality_gates (BLOCKED/passes_adverse_hard Pass 129/131), scanner (Pass 130), picks_now banned (Pass 132). NFA.

## Current State Snapshot (from fresh MEASURE 2026-06-13 ~04:52-04:56Z)
- **stamp_entry_conditions.py --stdout** (gen 04:52Z/04:56Z, cohort 1205/stamped 1162): 15 CONDITIONS. Good velocity/retention: crypto_rsi5070_us (CRYPTO) 108n 47.2/1.535 (l30 58n 48.3/1.454, n>=100 re-run R1/R2/R3); luxalgo_short 38n 71.1/2.211 stable; forex_trend_aligned 16n 68.8/5.333; equity_lowvol 22n 36.4/1.328; highvol_NEGATIVE 36n 55.6/0.824 (avoid good). Baselines weak: COMMODITY 43n 20.9/0.515; CRYPTO 924n 32.0/0.712 (l30 decay 29.2/0.55); EQUITY 58n 48.3/0.989; FOREX 43n 41.9/1.48. JSON: skips for scale/bars; discipline_note: forward-test only, n>=100 + re-runs before sizing.
- **money_ready_verdict.json / pf_registry policy_clean_net** (gen ~04:00-04:01Z): 0/10 pass T2. COMMODITY n=12 wr=33.33 pf=0.823 INSUFF (policy_frozen); CRYPTO n=1697 wr=51.44 pf=0.657 NOT_READY (mdd bad); EQUITY n=386 wr=47.41 pf=0.72; FOREX n=70-71 wr~41 pf~0.85 INSUFF; others tiny/INSUFF. intrabar: COM n=115 wr~34.8 pf~1.05 FAIL; CRYPTO 1155 ~32.4/0.73 FAIL.
- **pick_summary 14d/48h**: Old gens (~20:06 prior); recent 48h CRYPTO degraded (wr 28 pf 0.49, 100% single-source Alpha conc + dups).
- **check_one_sided_resolution.py**: FAIL FINDING#12 — 33 strats >=20 resolved 100% one-sided (LOST-only heavy: drawdown/atr/reddit/gnews/copy/stocktwits/currents; WON-only: ml_enhanced crypto/reddit/youtube/coinbureau/cta). H4/H5 pathology (bad external polluting 21.1% FWD/picks-now research-only; biased emission no variance).
- **Gaps (from greps in quality_gates/picks_now/scanner)**: One-sided kills extended but leaks possible in research paths; COM DB per-sym probes thin (n~12-115, granular fut good 50.8/1.586 but class drag; SI/PL noted); velocity on 15 CONDITIONS good slices (crypto_rsi retention +18pp vs decay) but full harness (n_eff/stress/monkey95/CI/AddH) not run at scale; no paper on admissible yet; pre-reg H-15x partial; tier tracker/pf_registry need update; recency 14d/48h panels old (P0 note); adverse/stamp hygiene in gates/scanner/picks_now but more extension needed for bad sources regardless of stamp.

**References**: deep-dive MD (Passes 119-132 + 06-13 summary/ACTION_PLAN); master loop doc (H1-H5 table §3, velocity §2, checkpoints §7, free data §6, ratchet §4); entry_conditions_forward.json (15 conds); stamp/intrabar/one-sided outputs; prior H-15x; thingstocheck_June2026; HF playbook; verif history; scheduler for constant digs.

## Action Items / Todos (Prioritized by Goal #1 + COM rescue + hygiene + velocity)
1. **Source Hygiene Extension (H4/H5 one-sided pathology — P0, quick win)**: Extend kills for all 33 FINDING#12 one-sided strats/sources (reddit u's, copy_pm_*, gnews, currents, stocktwits, youtube/coinbureau, ml_enhanced crypto, etc.) to remaining paths. Tie to stamp: kill bad sources *regardless* of stamp_good (protect only clean sources' good conds like crypto_rsi/forex_aligned). 
   - Fix: picks_now_professional.py (banned in load_db_edge_forward + forward query — done in Pass 132, verify both sites).
   - Fix: quality_gates.py (BLOCKED_SOURCE_SYSTEMS + passes_adverse_hard — done 129/131, extend if more).
   - Fix: production_scanner.py (hygiene near copy_pm_/COM blocks + _BLOCKED_CATEGORY_STRATEGIES — done 130, extend for full list).
   - New: Add to BANNED_SOURCES or source filters in other emitters if grep shows gaps. Update banned tuple in DB queries.
   - Verif: py_compile, grep for all 33, re-run one-sided check post-fix, loads.
   - Impact: Cleans 21.1% FWD pollution, aggregate WR, COM probes.

2. **Velocity Harness on 15 CONDITIONS + COM slices (H2/H3 — high priority for COM rescue)**: Run full velocity harness (1774 intrabar + 1134 stamp cohort + Addendum H: n_eff/stress/monkey95/CI/recency/conc<35%) on the 15 conds (focus crypto_rsi n=108 retention lift, forex_aligned 5.333 stable, luxalgo 2.211, equity_lowvol). Target admissible 48-55%WR/1.7+PF at n_eff>=80 + forward. Include COM fut_momentum (granular n~61 50.8/1.586 +0.83bp SI/PL, good vs GC/HG 0% conc).
   - Fix/Plan: Create or extend tool (e.g., velocity_harness_stub.py or use existing in reports/strategy_bt_*.json pattern). Pre-reg via hypothesis-registry (new H or fork H-106/H-15x for COM fut + specific CONDITIONS).
   - ACT: Run on locked cohort (entry-anchored first-touch SL-wins, net costs 2-16bp, dedup sym/day, time-split). Condition on stamp F + not adverse.
   - Paper prep: On top 3 (crypto_rsi, forex_aligned, luxalgo) + COM fut (with new hygiene).
   - Verif: harness output, CI LB>1.15, AddH checks.
   - Timeline: In next 4h ticks (harness sim now, full run post pre-reg).

3. **COM DB per-sym Probes + Widen Data (H3 data scarcity — COM priority)**: Safe DB probe (tools/db_env.py + pymysql) for at_pick_outcomes / tracker per-sym COM fut (HG=F/PL=F priority per BLACKLIST; SI/PL noted good slices). Tie to stamp tag from load_forward. Use for FWD/adverse flags.
   - Fix: Add stub or call in deep-dive analysis or new tool (e.g., com_per_sym_probe.py). Backup first (db_backup_to_backups.py).
   - Widen: Wire CFTC COT / EIA / FRED (plan §6) for COM (free APIs). Update COMMODITY_BLACKLIST enforcement if needed.
   - Verif: DB counts (n per sym), stamp join, conc<35%.
   - Impact: n accrual for COM ~06-13-16 n=100 checkpoint (plan §7).

4. **Pre-reg + Harness for New H (M-107 discipline)**: Pre-register hypotheses for velocity on top CONDITIONS + COM fut with hygiene (via hypothesis-registry skill). Include one-sided guard + stamp tie.
   - Fix: Update reports/hypothesis_registry.json (new H-112 or fork). Commit before any backtest/replay.
   - ACT: Run admissibility (edge_stability_harness) on conditioned slices.
   - Verif: Registry audit, pre-reg timestamp.

5. **Tier Tracker / pf_registry / Recency Update (RATCHET)**: Update tier tracker (python3 tools/strategy_tier_tracker.py), pf_registry (build_pf_registry.py), recency (build_recency_summary.py --force-db). Publish 14d/48h panels + verdict before sizing.
   - Fix: Run + commit updates. Extend for one-sided hygiene impact.
   - Verif: JSON gens, 14d/48h first (per CLAUDE.md recency rule).

6. **Paper + Forward Lanes (FORWARD)**: Prep paper trades on admissible slices (top CONDITIONS + COM fut). Accrue forward (stamp read-only, 14d/48h + verdict before promote). Monitor checkpoints (COM n=100 ~06-13-16, crypto_rsi n>=150 ~06-25, etc.).
   - Fix: Update ratchet tracker MDs. Add to deep-dive.
   - Verif: Forward n accrual, CI LB.

7. **Scheduler / Constant Progress (RATCHET + loop)**: Leverage existing scheduler 019ebf514e5b (15m recurring dig prompt). Extend to auto-run harness sims/paper prep/DB probes at ticks. Update prompt if needed for new hygiene.
   - Fix: If gaps, edit scheduler or add cron-like in wt (but per rules, no broad).
   - Verif: Next fire, output.

8. **Incidents / FINDING#12 Closeout**: File/resolve one-sided (H4/H5). Extend to all paths (picks_now/scanner/quality_gates already partial; verify no leaks in research vs prod).
   - Fix: Use tools/audit_pick_funnel/cli_track.py. Update banned in more places if grep shows.
   - Verif: Re-run one-sided post, grep for remaining 33.

9. **Peer Review + Plan (as requested)**: This .MD is the plan. Fan out to 5-20 models via /PeerReviewSwarmOptions (e.g., /consult-cloudflare-models 37+, /consult-multi fanout 11 providers, /swarm-second-opinion 3-engine, /swarmv2-pr-review for depth, /consult-nvidia-models, etc.). Review for: hygiene completeness, COM rescue plan, velocity harness viability, one-sided H4/H5 triage.
   - Fix: Create this MD, then run swarms (e.g., python tools/swarm/swarm_run.py --prompt-file this.md --engines deepseek,xai,kilo,gemini,ofox,nvidia_deepseek --out-dir swarm_runs/plan-review-2026-06-13). Integrate feedback.
   - Verif: Swarm outputs, updates to plan.

10. **Surface / Deploy (RATCHET)**: Update deep-dive MD (this Pass), weekly scorecard, progress summary. Surface via updates/index.html card (before AUTO-INJECTED marker) + tools/deploy_audit_files.py --only updates + curl verify. PR#564 comment. No generators locally.

**Risks / Verifs**: All claims with direct evidence (tool outputs, JSON gens, grep hits, plan § refs, prior Passes). py_compile every edit. git only own (MD + 1-2 py max), rebase-first, --force-with-lease. Backup DB before probes. 14d/48h panels + verdict first (per CLAUDE.md). Mutate-before-kill. Wire-up rule (callers in prod path or opt-in + plan). Scheduler for constant. NFA.

**Timeline / 4h 15m Ticks (per scheduler + prior plans)**: 1) This plan + peer review swarm. 2) Harness sim on 15 conds (n=108 rsi retention). 3) Paper on top 3 + COM fut. 4) DB per-sym COM + hygiene verify. 5) Pre-reg H + tier update. 6) Ratchet (MD/PR/scorecard). 7) Next scheduler tick. Enforce gates before size.

**Evidence/Refs**: Subagent MEASURE/grep/MD (fresh tables, suggestions); deep-dive MD (Passes 119-132 + 06-13 summary); master loop (H1-H5 §3, velocity §2, checkpoints §7); stamp/intrabar/one-sided outputs; entry_conditions_forward.json; prior H-15x; thingstocheck_June2026; HF playbook; verif history; scheduler prompt; CLAUDE.md/AGENTS.md rules.

This plan is the .MD for peer review (fan out now via swarms). Execute fixes below (hygiene already in 129-132; more if gaps from review).

**End of Plan.** NFA.
