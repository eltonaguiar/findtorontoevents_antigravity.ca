# Session summary — claude-opus (money-ready loop, 2026-06-18→19)

**Headline:** found + (with a peer) fixed a **P0 that green CI had masked for ~6 days** — the honest measurement ledger was frozen; it's now flowing again. Also exhaustively closed the honest-edge search (0 promotable winners; one genuine lead) and overhauled the picks-now surface per the operator's request.

## 1. THE P0 — honest ledger (`at_signal_outcomes`) frozen ~6 days behind GREEN CI  ✅ RESOLVED + VERIFIED
- **Symptom:** `at_signal_outcomes` (the verdict-grade honest ledger the whole program measures against) stopped getting rows on 2026-06-12 (~5-7k/day → 0) while `outcome-resolver.yml` reported green. So all per-class verdicts (0/9) + the `crypto_rsi5070_us` lead (frozen n=108) were on a stale cohort; the Jun-25 gate was unreachable.
- **Diagnosis (pursued through several layers, each verified before acting):** the equity price fetch in `active_picks_sync` was yfinance-only and rate-limited under load → 0 prices → safety-halt → resolver fails → ledger frozen. A peer had added an FMP fallback (06-18) but **`FMP_API_KEY` was never wired into the resolver workflows' env** (the secret existed since 06-06). A *separate* table `at_pick_outcomes` had a missing-DB-creds env gap.
- **My fixes (on main):**
  - `e45c434b7` — wired DB creds onto the `universal_pick_resolver` step (`at_pick_outcomes` writes restored; verified fresh).
  - `7a78863b5` — wired `FMP_API_KEY` into `outcome-resolver.yml`'s active_picks_sync step.
  - `4451526a6` — same on `audit-dashboard.yml`.
  - Did NOT commit a redundant local `active_picks_sync.py` edit — verification showed main already had the FMP fallback (and a 172-line-newer version); a blind PUT would have clobbered it.
- **Peer's complementary fixes:** #608 (active_picks_sync FMP equity + non-fatal per-class + frankfurter FOREX) + the `is_emission_allowed` UnboundLocalError fix in `backfill_local_sources.py` (the mirror step).
- **VERIFIED:** outcome-resolver run 03:27 = SUCCESS; `at_signal_outcomes` latest_created 2026-06-19 03:39, latest_intrabar 03:58 — un-frozen and updating.
- **Docs:** `reports/INCIDENT_honest_ledger_frozen_2026-06-19.md` (full diagnosis trail, incl. my corrected mis-attributions), `reports/IMPLEMENTATION_PLAN_honest_ledger_restore_2026-06-19.md` (+ 3-model peer review via the :4000 proxy, NEEDS_CHANGES folded in).
- **Open recommendation:** un-mask — make the resolver/sync fail-hard (or a freshness monitor) so a frozen ledger turns CI RED, not green-on-halt. (Peer's #610 freshness check partially covers this.)

## 2. Honest-edge search — EXHAUSTIVE, 0 promotable winners
- **FOREX consensus "winner" REFUTED** — it was a **daily-resolution artifact**: honest SL-wins-ties first-touch collapses it to gross PF **1.02** (daily said 2.88 on the same 88 picks). The daily resolver inflates gross PF **~2-3×**. Killed 3 ways: cost (@1bp), vol-rescue (H-117), honest first-touch (H-118). Report: `reports/FOREX_CONSENSUS_HONEST_FIRSTTOUCH_2026-06-13.md`.
- **Durable rule banked:** daily-resolved `trading_picks` PF inflates ~2-3× vs honest first-touch — re-resolve any candidate before believing it. Confirmed 4×: FX consensus 2.8×, COMMODITY 2.09×, forex_rsi2 1.18× (and again at n=28). H1 spot-replay 20/20 = ledger faithful.
- **Sole genuine lead:** `crypto_rsi5070_us` (CRYPTO ∧ RSI(14,1h)∈[50,70] ∧ US session) — honest intrabar net@16bp **PF 1.36**, IS/OOS **1.44/1.30 (holds)**, diversified (RENDER 6%), **cost-robust to 30bp**; sub-bar only on n (CI-LB 0.95 < 1.15 at n=108). Gate n≥150 ~Jun-25. Report: `reports/CRYPTO_RSI5070_US_LEAD_CANDIDATE_2026-06-13.md`.
- **Closed with evidence:** dormant-backtest mining (fantasy PF 35-1000 / losing 0.55); 307-strategy×class honest sweep (0 clear the bar); daily-only source audit (short_dominant_engine/copy_hl_lb_None/myfxbook/pm_momentum all phantoms). Registry: H-117..H-123.

## 3. picks-now overhaul (operator request) — DONE & LIVE
- **MU duplication fixed** (Top Gainers deduped by symbol; was 8× from intraday re-emission) + **pick date/time EST** + `×N` re-emit badge.
- **Honest "unrealised ≠ profit" note** on the Live MTM panel → points to the real net-losing forward result.
- **"Would we profit?" = NO** — honest first-touch on the cohort: net PF 0.82, no edge subset (the +2.51% live MTM was an unrealised rally artifact). Subagent reports: `PICKS_NOW_WHATIF_PROFITABILITY` + `PICKS_NOW_METHODOLOGY_REVIEW`.
- **Over-emission killed structurally:** backed up `picks_now_tracker`, deduped 441→206, added `UNIQUE(symbol,direction,pick_date)` + idempotent `ON DUPLICATE KEY UPDATE` writers (verified 0 dup-groups against live writes).
- **Silent engine outage repaired:** `picks_now_professional.py` ModuleNotFoundError (no PYTHONPATH) → added `sys.path.insert` (4d4f02d74); engine writing fresh picks again.
- Systemic over-emission scan confirmed picks_now was the only affected display table.

## 4. Process notes
- Multi-AI peer review used (LiteLLM :4000 proxy paid-mode, 3 models) on the P0 plan.
- Caught + corrected my own mis-attributions twice (DB_PASS_BACKUPS, "yfinance broadly broken") through direct verification rather than shipping a plausible-but-wrong fix.
- Coordinated with the parallel peer session via dropchat; the P0 was closed by the *combination* of our fixes — flagged overlaps, avoided a clobber.

## Verify / next
- Watch `at_signal_outcomes` rows/day return to ~5k + `crypto_rsi5070_us` n accrue toward the Jun-25 gate.
- Implement the un-mask hardening (fail-hard on frozen ledger).
