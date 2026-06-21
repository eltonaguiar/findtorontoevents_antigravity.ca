# ACTION PLAN: Audit Edge Hunt & Performance Turnaround (Grok 4.3 Quant Deep Dive - 2026-06-12)

**Context**: This plan synthesizes the 4h+ deep dive (recurring 15m ticks, Pass 1-70+ in deep-dive MD, thingstocheck_June2026 investigation, velocity harness on 1774 intrabar + 1134 stamp cohort, HF FAST playbook, per-class autopsy, picks-now 21.1% WR root cause, synthetic data issues, stale pages, FWD vs strategy tracking loss, adverse selection ~74% volume drag, entry selection deficit, concentration, recency stale 06-05, small-n, permissive gates, no velocity in prod, discovery not production-gated).

**Goal #1 (North Star per CLAUDE.md)**: Phenomenal performance (Tier-2 min: PF>1.5 / WR>50 / MDD<20 + conc<35% + CI LB>1.15 + forward) across ALL asset classes on findtorontoevents.ca/audit. Current honest state: 0/6 classes pass (COM closest with policy-clean PF 2.04 n=31 but INSUFF; CRYPTO FAIL PF~0.65-0.73 despite T1 sleeves; others worse or INSUFF). Prioritize where edge best worth risk (COM first).

**Key Findings (Evidence-Backed, Asset_Class | n | Timeframe)**:
- Adverse selection dominant drag (granular DB: volume_spike n~117 WR37.6 PF0.92 avg-0.13bp; regime_mild n37 WR18.9 PF0.21; alpha ~1298 ~27% WR; ~74% vol in bad families; z CRYPTO -13.6 / volume -12.4).
- Entry selection deficit (velocity/stamp retention proof: CRYPTO rsi5070_us n=108 WR47.2 PF1.535 last30 48.3/1.454 stable vs baseline decay 0.54; F1-5 pre-entry from stamp.py:98-165 not wired to prod/valuation/picks-now; exit geometry null experiments).
- Concentration (GC=F 20%+ in COM per deepdive CT=F 57-88% artifact; single-source 85%+ CRYPTO/BOND per pf_registry; false-T1 from unenforced gates pre-DSR/SPA).
- Recency ignored/stale (panels gen 2026-06-05; CRYPTO 0 closed 48h; verdict recency_gate false; 14d/48h not primary).
- Small n non-crypto (COM/ETF/BOND/FUT <=31 or <100; research runs n=4-17 fail Tier-2).
- Data quality/legacy/synthetic (pre-v2 resolver 23-24% EXPIRED->WON inflation/mispriced 4k+; ai-tournament synthetic cursor 100%/kimi 49%/llama 43%; reverse splits wrong prices; active limits incorrect counts; ghost/mismatches fixed but legacy).
- Permissive gates/leaks (regime_filter.py:474 "Unknown... allowing by default"; production_scanner fallbacks; no early conc/adverse in all paths; score calibration inverted).
- Discovery not production (Grok 9+49/15/13 keltner heavy CRYPTO no full stamp/adverse/conc/vel/monkey; ai-tournament/research mostly NO_EDGE; picks-now valuation 21.1% WR because research/paper only + no stamp/vel/adverse + risk-off + 4 gates 0/6 pass).
- No velocity in prod (1774+1134 replay 50-100x fast vs live 10-20/mo; not used for iteration).
- Portfolios losing (ai-tournament/model risk-managed many down; no TWR/attr validation).
- FWD WR% vs strat/symbol-dir mismatch (resolver pre-fix, conc, one-sided; tracking lost in active/star tab).
- Hidden edge? None reliable (funnel/research NO_EDGE/MIXED; high cells disputed/small/post-hoc/conc e.g. CRYPTO Smart 78.9% vs raw ~39% 91.7% claude_gainer_st + EXPIRED mislabels; some sleeves positive e.g. futures_mom 61/50.8/1.586, stamp CONDITIONS lifts, carry 26/73/2.01, lux short 38/71/2.211 but fail n/recency/conc/full gates/paper/T2; no combo of filters/buttons/tabs yields T2 per class; picks-now valuation + growth screener potential but 21.1% horrible).

**Sources**: thingstocheck_June2026 skill (full prompt + workflow), PLAN_INSIGHTS_GROK_June122026_1030pm.MD, main deep-dive MD (Passes 1-70+), sprint-refine:78+ (12-step 4h checklist + granular + COM priority + HF playbook + 15m timeline), velocity MD (1774 intrabar +1134 stamp + Add H n_eff/stress/monkey95/CI/conc/recency/rubric/emitter), stamp.py:98-165 (F1 ALIGNED 114-116/F3 50-70 120-122/F4 LOW 123-129/F5 US 130-132 + CONDITIONS 18 + discipline), june2026_research_candidates.py:22- (ENHANCED_V2/NEW + parents), entry_conditions_forward.json (gen 04:15Z stamped 1134), money_ready_verdict.json (04:47Z 0 T2), pf_registry.json (policy COM 31/58.06/2.04), tier trackers, Grok loads (ai 9 + sleeves 49/15/13), hyp_reg (104+ H-105-109 UNTESTED), granular DB (futures_mom 61/50.8/1.586 +0.83bp; volume~117 37.6/0.92; regime 37 18.9/0.21), recency 14d/48h gen 06-05 stale, COT ~17, pages fetches (disputed/21.1%/stale/NO_EDGE/synthetic), db-schema (at_* tables + db_env + backup rule), manifest 47 buttons/17 tabs/31 filters, quality_gates lines, master loop §§2/4/5/7/8/10, CLAUDE Goal#1/AGENTS (coord/Wire-Up/no gens/deploy/only own/text>brain), all verif blocks (outputs read).

**Suggested Action Plan (HF FAST + Velocity + thingstocheck Synthesis - Prioritized for Goal #1, 4h War Room Sprints)**:

1. **Data Hygiene First (P0, 0-30m per sprint checklist)**: 
   - Clean synthetic filter in tournament/leaderboard/ai-tournament (cursor 100%, kimi 49% - backfill or nuke old/start fresh).
   - Legacy re-resolve kimi/gpt + direct live DB per-symbol-dir FWD WR/PF/n vs strat (use tools/db_env.py + backup to ejaguiar1_backups first; targeted queries on at_signal_outcomes/at_raw_picks for conc/NULL/mispriced/ghost/recency/one-sided; reverse splits adjuster; active limits fix).
   - Fix recency generator (tools/audit_pick_funnel/build_recency_summary.py - force DB, sidecars stale 06-05, 0 decisive for COM/mom; cron :10 / push removed 05-19).
   - Backup DB before any mutate (tools/db_backup_to_backups.py; names <=64).

2. **Wire Velocity/Stamp/Adverse to Prod/Valuation/picks-now (P0, sprint steps 2/3/8)**:
   - Wire stamp F pre-entry boost (stamp.py:98-165 F1-5) + adverse explicit kill (volume/regime first from granular + MUTATION_THREE_AXIS before BLOCK; config BLACKLIST; quality_gates/production_scanner/emergency_mutations).
   - Velocity 1774+1134 replay fast iter on cohorts (COM futures + stamp rsi n=108 + NEW; R1/R2/R3 sim + full Add H n_eff/stress/monkey95/CI/conc/recency; falsif forward/replay PF>=0.8).
   - Stamped HC wire (JUNE2026_FORWARD_OBSERVATION=1: if good CONDITION e.g. rsi/futures set hf_conviction_tier="A" + priority).
   - To picks-now (tools/picks_now_professional.py - integrate stamp/vel/adverse + growth-stock-screener FCF/magic/acquirer for equity; paper top admissible; track per-symbol-dir FWD; update disclaimer to honest).
   - Per Wire-Up: grep production callers in alpha_engine/audit_trail/tools for calculate_smart_score/passes_*/priority_picks_emitter/quality_gates.

3. **Enforce Recency/Conc Early (sprint steps 6/7/12 + HF 14-step)**:
   - 14d/48h panels primary in verdict/UI (stale 06-05 P1 fix; degrade -> shadow/throttle; CRYPTO 0/48h flag).
   - Conc one-per-ticker/source<15%/sym<25% before DSR/SPA (per CLAUDE P0; update manifest for honest FWD vs strat/symbol-dir).
   - Kill adverse fast (granular list volume_spike 117/regime_mild 37/alpha/mercury first; MUTATION before BLOCKED expand).

4. **Pre-reg M-107 + Velocity Harness + Full Add H (sprint steps 4/10 + master §4/7 + velocity MD)**:
   - New hyps for valuation + growth screener + COT lag3 + prediction markets per-source (H- new; acceptance n>=80-100/WR50/PF1.5/CI1.15/conc35/MDD20/forward/3 windows + monkey/stress + paper; data lock stamp + intrabar + COT; banned distinct killed).
   - Velocity harness on 1774+1134 + Add H (n_eff cluster trade-date; stress cost x0.5-4 + slips + vol cap PF CI-LB>1.15 >=3 adverse; monkey 95th 1000 randoms match count/univ/costs/rubric hash-lock; emitter back-pressure throttle sub-baseline; CI LB>1.15 n>=80; conc<35; recency 48h/14d; 3-null rotate).
   - Checkpoints: COM ~06-13-16 n=100 clean (first honest class verdict); crypto_rsi ~06-25 n>=150 + re-pass R1/R2/R3; FOREX ~06-16-20 n=100.
   - COM first admissible batch priority (futures_momentum_dedup_v2 H-106 + stamp F1/F4/F5 + COT lag3 + adverse fade + dedup + vel + AddH + ATR + first-touch + full gates + paper; target ~1.6-2.5 conditioned; june NEW gold_overnight_gap_fade etc).

5. **Paper on Admissible Only + Portfolio Math (sprint steps 5/6 + master §5 + HF 14-step)**:
   - Paper via tv-paper-trade/paper_trading/ (top from vel/valuation/COM futures + stamp + rsi retention; mandatory TP/SL; monitor TWR/attr from DB aggs; no size till n>=100 clean + R1-3 + full gates + recency + monkey).
   - Portfolio TWR/attr validated (daily geom equity-curve from fills/aggs NOT sum-pct bug; attribution Brinson-lite per class/strat from DB aggs; risk-adj Sharpe/Calmar/MDD from curve; daily P&L recon fills matches curve; fix losing model portfolios by gates + de-gross).

6. **Fix Stale Pages + UI (thingstocheck + sprint step 11)**:
   - ai_leaderboard: multi-model refresh + synthetic filter.
   - portfolio_history: update with current or deprecate with reason + TWR/attr engine.
   - research_index: highlight actionable + increase n via velocity (mostly NO_EDGE small n).
   - ai-tournament: clean synthetic, honest per class FWD.
   - Update manifest/UI for honest FWD tracking, no post-hoc segments (INC#1 warned).

7. **Integrate Concepts + 4h War Room Sprints + Ratchet (sprint full 12-step + HF 14-step + master loop + thingstocheck)**:
   - Growth-stock-screener (FCF/magic/acquirer) for equity picks-now long-term valuation.
   - Copytrader/Polymarket/Kalshi (per-source scorecard H4 kill/keep + velocity).
   - Meme/cheap/penny/IPO (data build + gates).
   - 4h sprints (0-30m: pulls+verifs+kill draft+hyp seed; 30-90m: vel batch1 COM + stamp + Add H + COT; 90-150m: stamped HC + adverse kills + shadow T1 + TWR/attr; 150-210m: batch2 + falsif + paper; 210-240m: 14d/48h + verdict + tier + RATCHET + update MD + verif).
   - Ratchet weekly H1-H5 scorecard (reports/weekly + hyp_reg result post-pass + memory + surface; swarm/peerreviewswarmoptions for PLAN/findings review).
   - Hostile re-deriv + independent verif before wire (anti-fab; require pre-change lines quote).

8. **External Data + Focus 2-3 + Do-Not-Relitigate (master §§6/8 + HF)**:
   - COT lag3/FRED ( ~17 cot_*.json z noncomm/comm for COM; FRED macro; EDGAR for EQUITY; per-class deep_dive + 30/60/90 rescue if PF<1/WR<30/MDD>2x).
   - Focus COM + CRYPTO (EQUITY background; rotate 3-null).
   - Do-not-relitigate (refuted: stocks_rsi2_pullback promote, CRYPTO direction-flip, futures_momentum dedup artifact, etc.).

**Verification & Next (Iron Law + AGENTS/CLAUDE)**:
- All claims (asset_class | n | timeframe) + file:line/JSON gen + repro (e.g. python3 tools/strategy_tier_tracker.py --class COMMODITY; DB via db_env; stamp --stdout).
- Verif before claims: py_compile (stamp/quality_gates/june/config/production_scanner OK); JSON loads (verdict 04:47Z 0 T2, entry 1134, pf COM 31/58/2.04 etc); grep (stamp 0 prod, mispriced); worktree 13+; git status; /tmp pass* + shared; Pass count +1; all outputs READ.
- No generators/destructive/push (py_compile only; backup first; pull --rebase first).
- Coord peers (worktree/list_peers/check_messages first + every few).
- Updates rule (if HTML: read full + insert-before-AUTO + deploy_audit_files.py --only updates + curl verify).
- Wire-Up (no new without callers in prod path).
- M-107 pre-reg before bt/harness.
- Memory/2026-06-12.md + this .MD updated.
- Deploy after MD touch (python3 tools/deploy_audit_files.py --only updates if needed).
- Ready for operator: execute plan with backups + verifs + 4h sprints; continue recurring dig or terminate per user.

**References**: Full list in deep-dive MD Passes + PLAN_INSIGHTS + thingstocheck skill + sprint-refine + velocity MD + stamp.py + june.py + entry/verdict/pf/tier/Grok/hyp/granular/recency/COT/pages/db-schema/manifest/quality_gates/master/CLAUDE/AGENTS + verif blocks.

**End of Plan**. (NFA; no sizing without full gates + paper + explicit greenlight. Operator: run in worktree, PR changes.)

**Pass 93 update (2026-06-12, in .worktrees/audit-dig-deeper-2026-06-12):** 
- Wiring FULL complete in picks_now_professional.py (search_replace + prior: stamp F1/F4/F5 0.15 boost + adverse_flag kill proxy + synth downweight in _score_momentum + load context; signals; "FULL complete Pass 93" note). Research path addresses 21.1% + 0/6. Prod plan explicit (scanner TODO post-harness, quality_gates opt-in sidecar).
- Grok deep-dive MD: Pass 93 appended (fresh loads: verdict 20:00 COM ~0.35/1.05, stamped 1162, cond lifts; wiring confirmed picks_now:697+/scanner:2942+; velocity H-111 full plan COM fut+stamp+adverse+COT+AddH+paper; synth active; verif iron law block; HF/Goal#1 ratchet).
- ACTION_PLAN + tracker ratcheted (items 2/3/4 advanced: synth, DB FWD, wiring full).
- Verifs all run+read (py_compile OK py files; loads verbatim; grep wiring/synth "FULL"; tails; wt git only own staged for commit; no junk in this delta).
- Next per plan: harness sim, COT proto, growth wire, paper, hyp verdict, PR#564.
Only own changes. Rebase-first. Goal #1. (See grok MD Pass 93 for full evidence.)

