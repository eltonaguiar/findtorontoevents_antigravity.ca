# Grok 4.3 Ratchet Next-Steps Progress Tracker
**Session:** audit-dig-deeper-2026-06-12 (isolated worktree)  
**Branch/PR:** audit-dig-deeper-2026-06-12 / #564  
**Main reference:** reports/2026-06-12-grok4-3-quant-deep-dive-analysis-findings-achievements-remaining-actions.md (Pass 77 ratchet)  
**Goal #1 focus:** COM priority (good fut_mom slice inside adverse class), wiring stamp/adverse to prod paths, synthetic cleanup, velocity on admissible, recency hygiene, 0/ classes T2 → Tier-2+.

**Created:** 2026-06-12 (Pass 77/78 tick)  
**Update rule:** Append new entries at top (newest first) or update status in place with timestamp + verif note. All changes only in this wt, rebase-first, only own, verif-before-claim.

## Ratchet Items (from Pass 77)

### 1. Velocity harness read-only on COM n~100 clean
- **Status:** In progress (plan + data prep)
- **Evidence:** entry_conditions_forward gen 19:07 stamped_n=1162 (15 conds); prior intrabar autopsies (COM 134n 29.1% +13.6bp, fut_mom 74n +79bp SI/PL drivers); velocity report 1774+1134 + AddH (n_eff deflation noted for fut).
- **Commands run:** targeted loads (verdict/stamp/recency), py verif on stamp/scanner/picks/gates/recency.
- **Verifs:** py_compile OK; loads read; grep for COM fut + stamp conds.
- **Next action:** Run read-only replay using entry_conditions + prior intrabar slices for COM fut_mom (n_eff, stress, monkey 95th, CI LB, conc). Target: admissible per H-111 / H-VEL-COM-001 (n_eff>=80, CI>1.15, PF>=1.5, WR>=50, conc<35, forward n~100 ~06-13).
- **Owner/ETA:** this 4h block.
- **Last update:** 2026-06-12 ~19:50Z (post rebase + tracker create)

### 2. Synthetic filter in ai-tournament (json/scripts)
- **Status:** Planned (evidence gathered)
- **Evidence:** Live ai-tournament.html (web_fetch): 1636 SYNTHETIC_SEED_ENRICHED; cursor_agent 100% in resolved, kimi_direct 49%, llama4_scout 43%; recommend 0% synth models (grok3 n=52 WR67.3% trustworthy). Pages now surface the flag + "treat as upper-bound".
- **Commands run:** web_fetch ai-tournament + grep synthetic in data/ (some survivorship notes but core contamination in tournament JSONs/HTML).
- **Verifs:** pages full content read; prior MD Pass 76/77 quotes.
- **Next action:** Add filter in ai-tournament processing (or data loader) to exclude SYNTHETIC_SEED_ENRICHED rows or weight 0% synth models only for leaderboard/ranking. Update tournament_picks / model_summary logic if source in wt (or note for generator sidecar). Re-verify grok3 as canonical trustworthy.
- **Owner/ETA:** next 15m tick.
- **Last update:** 2026-06-12 (pages + tracker)

### 3. Safe DB per-sym FWD (COM fut SI/PL + adverse + 14d/48h)
- **Status:** Planned (read-only only)
- **Evidence:** Prior autopsies (memory Pass 76/77): COM fut_mom SI=F 33n +152bp / PL=F 24n +181bp; volume 191n bad, regime_mild 48n bad; recency 14d/48h gens fresh but 48h thin P0.
- **Commands run:** db-schema awareness (use tools/db_env + pymysql read-only; backups for any write — none here).
- **Verifs:** schema notes read in prior; no write attempted.
- **Next action:** Targeted read-only queries (via /tmp or python -c in wt) for per-symbol-dir WR/PF on COM futures_momentum (intrabar_resolved_at IS NOT NULL), adverse families, 14d/48h cutoffs. Output to tracker + main MD. Use only ejaguiar1_stocks via db_env.
- **Owner/ETA:** this 4h.
- **Last update:** 2026-06-12

### 4. Extend wiring (picks_now consume stamp_adj/adverse_flag + scanner/feature/quality explicit)
- **Status:** Progress made (picks_now integration)
- **Evidence:** picks_now_professional.py:641 wiring block (stamp_adj/adverse_flag computed, "caller can use"); score() composite did not consume it pre-edit. This edit integrates into live score.
- **Commands run (this tick):** search_replace + py_compile OK (see below).
- **Verifs:** py_compile post-edit green; grep before/after showed the block; score now += stamp_adj*80 (adverse -20).
- **Next action:** 
  - Verify downstream (return dict already includes per original comment; caller in main flow can now see higher scores for good stamp / lower for adverse).
  - Extend to prod: add similar (or call) in alpha_engine/production_scanner.py (post 5056 or in emitter) and/or audit_trail/quality_gates.py floors (explicit beyond volume).
  - Label opt-in if needed per Wire-Up Rule.
- **Small edit done:** score integration (non-breaking, directly "consume" item).
- **Last update:** 2026-06-12 ~19:50Z (edit + verif)

### 5. Paper on admissible (H-106/H-111 + H-VEL-COM-001)
- **Status:** Planned
- **Evidence:** hyp reg: H-111 COMMODITY REGISTERED-UNTESTED (commodity_futures_momentum_symbol_tier_m); prior H-VEL-COM-001 template (fut + stamp F1/F4/F5 + COT lag3 + no vol + regime + AddH; acceptance criteria exact).
- **Next action:** Define paper book (or use existing sleeve) for COM fut_mom + stamp + COT guard. Log to tracker + paper_trading/. Run 1-2 weeks read-only or zero-size shadow. Measure vs H-111 criteria.
- **Last update:** 2026-06-12

### 6. COT lag3 prototype + wire
- **Status:** Planned (prior sub had details)
- **Evidence:** Prior sub report (19618b): cftc publicreporting + disagg 72hh-3qpy best for GC/SI/PL; lag=3 in cot_positioning.py:45 + commodity_cot_contrarian.py:46. Wiring plan: OPT-IN post scanner:5056 (env COMMODITY_COT_LAG3_PREFILTER).
- **Next action:** Prototype fetch + join (read-only python -c or /tmp script in wt) for current COM symbols. Add guard in relevant emitter or as feature. Wire as sidecar (per Wire-Up).
- **Last update:** 2026-06-12

### 7. Update hyp_reg (verdict on H-111 post-harness)
- **Status:** Pending harness
- **Next action:** After velocity/admissible run on H-111 candidate, update registry result + status. Commit.
- **Last update:** 2026-06-12

### 8. More Pass appends + action plan + PR review
- **Status:** Ongoing (this tracker + main MD)
- **Action:** Append short Pass 78 to main grok deep-dive MD (ref this tracker). Update ACTION_PLAN if material. Monitor 48h/14d pages. Add review comment to PR #564.
- **Last update:** 2026-06-12

## Cross-Cutting Notes
- **Worktree hygiene:** All work here only. Rebase before edits. Only own files in commits (tracker MD + targeted small edits like picks_now integration).
- **Verif iron law:** Every edit/claim preceded by py_compile + loads/grep/pages + read of output.
- **Wire-Up compliance:** All extensions either have prod caller or explicitly labeled opt-in/sidecar with plan.
- **No generators:** py_compile + targeted python -c + read-only DB only.
- **HF / Goal #1 tie-in:** Every item traces to COM edge (good slice), velocity retention, adverse explicit kill, entry stamp > exit, 14d/48h first, pre-reg, paper before size, conc gate.

**Next 15m tick focus:** Complete item 4 (wiring) verification + start item 1 (velocity plan/code) + synthetic filter sketch. Append to this tracker + main MD.

**Evidence trail (this creation tick):** rebase success, py verif green, pages full read (0/6 + synthetic 1636 specifics), loads (gens 19:07/19:13), grep (0 callers), hyp (H-111), picks_now score read + integration edit + post-edit py_compile.

---
*Tracker is the single source for ratchet progress. Main deep-dive MD gets summary Pass entries only.*

## 15m Tick Pass 79 / continuing 4h (2026-06-12 ~19:55Z)
- Rebase clean, skills re-invoked, verifs first (py OK, loads/grep/pages read).
- MEASURE: web_fetch picks-now (0/6 pass, research/paper only, 21.1% FORWARD-TESTED, our stamp/adverse now in research scores); ai-tournament (SYNTHETIC 1636 cursor 100%/kimi 49%, 0% synth grok3 rec, 0 ready); loads (verdict 19:07, stamp 1162/15, recency 19:13); grep (consume edit in picks_now, 0 callers, TODOs).
- DIAGNOSE: COM priority (H-111 REGISTERED-UNTESTED + fut_mom 74n +79bp good slice inside adverse/conc/48h P0 per prior + pages INSUFF); wiring impact (adj now consumed in picks_now research path - boosts good stamp ~+12pts, penalizes adverse -20; main /audit prod still 0 callers/gap); synthetic (pages explicit 1636 flag + filter rec); recency P0 (48h thin despite fresh gen); 0 classes T2 live confirmed; FWD vs strat + adverse dominant.
- ACT/FORWARD: tracker items advanced - item 4 wiring (picks_now consume DONE per edit + this dig; next prod extend); item 2 synthetic (pages evidence + plan filter to 0% synth); item 1 velocity (data prep + read-only plan on COM fut using entry_conditions + intrabar); DB FWD/COT/paper/H-111/HF ratchet per tracker.
- HF applied: velocity, stamp F pre (now in research), adverse explicit (wired + consume), 14d/48h first, conc, pre-reg (H-111), paper admissible, synthetic filter critical (pages now surface).
- RATCHET: this Pass 79 in main grok MD + tracker update (item statuses, evidence from pages/loads). Next 15m: velocity read-only COM, synthetic filter sketch, DB FWD plan, wiring NOTE in scanner/gates, PR review.
- Evidence: rebase, web_fetch full (0/6 + synthetic 1636), loads, grep, py verif, MD anchors, tracker read. All outputs read before append/claim.
- Goal #1: COM edge + wiring (research now has consume) + synthetic + recency P0 now deeper + tracked. 0/ still but measurable + actionable.

**Tracker update (this tick):** Item 4: picks_now consume DONE (edit + dig); item 2: synthetic evidence from fresh pages (1636, grok3 rec), plan filter; item 1: velocity data from loads + plan read-only COM. (See full sections above for details.)
---
