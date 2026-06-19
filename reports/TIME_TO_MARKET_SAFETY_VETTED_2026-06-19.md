# Time-to-Market — Safety-Vetted Companion (2026-06-19)

**Companion to** `reports/TIME_TO_MARKET_ACCELERATION_2026-06-19.md` (a peer's independently-derived plan — we
**converge** on the thesis: the binding cost is calendar time on FORWARD honest-n accrual, and the #1 move is to
never lose accrual days to a silent freeze). This doc adds the **two layers my 7-agent quant-team workflow uniquely
produced**: (1) an **adversarial safety-critic's DROP list** — accelerations that secretly trade trust for speed; and
(2) the **SQL-verified root cause** of the current accrual stall (it is deeper than "freshness").

**Method:** 5 diverse lenses → synthesis → an adversarial safety-critic told to kill any trust-for-speed trade.
The critic **rejected the synthesis's own #1 and #4 ranked items.** Every number below was re-verified by the lead.

---

## 0. Verified root cause — it is resolver INSTABILITY, not just a freeze
- Emission is healthy (`trading_picks` ~285–775/day). The throttle is **resolution**: of ~2,260 picks from the last
  6 days, **2,172 (96%) are still OPEN** → never resolve → never enter the honest ledger (`at_signal_outcomes` only
  ingests *resolved* picks).
- **`outcome-resolver` is still unstable: 6 of the last 8 hourly runs FAILED** (only 03:04 + 03:27Z succeeded). PRs
  #608/#614 fixed two crash causes (a trickle now flows: 12 mirrored / 3 resolved Jun-19 vs ~5k / ~90 on Jun-10/12),
  but **full volume has not returned.**
- ⇒ The single biggest time-to-market lever is **make the resolver run reliably (fail-LOUD)** so the OPEN backlog
  drains and accrual resumes ~90/day — landing the rsi5070 (n≥150, ~Jun-25) and handoff (OOS, ~Jul-9) gates in **days,
  not months.** This is a *sharper* statement of the peer's "freshness fail-hard": the freeze monitor catches the
  *symptom*; the resolver-stability fix removes the *cause*.

## 1. SAFE accelerators that survived the adversarial critic (ranked)
1. **Stabilize the resolver, fail-LOUD** — fix the 6/8 failing runs (diagnose the real per-class failure; do NOT mask). *The #1 lever.*
2. **Fail-loud freshness heartbeat** — make #610's alarm BLOCK/incident when the ledger is >36h stale (insertion ≈ `dashboard_generator.py:832-843`). Detection 6d → 1h. *(= peer's #1, finished.)*
3. **Stop dead/killed sources accruing n** — tighten `is_emission_allowed` in `backfill_local_sources.py` to DROP do-not-relitigate/BLOCKED rows. Trust-positive.
4. **Wire the monkey-test as a REPLAY-only selection filter** — `tools/monkey_test_benchmark.py` **exists** (#609, 213 lines) but is **unwired** (0 refs in `loop_preflight`). Build/wire to Addendum-H spec (decision stat pre-specified = PF CI-LB/t-stat; randoms match trade-count+universe+costs; labeled "selection, not promotion"; fail-closed). Saves a full 8–12wk forward window per dud.
5. **Shadow-forward the VIX term-structure rotator** — highest-Sharpe candidate (`reports/equity_vix_regime_rotator_2026-06-04`: Sharpe ~3.0, PF 1.70, free data). File+callers exist but likely route to research, not the forward lane. Route to shadow-forward (M-107, forward-n only, unchanged gate). Higher Sharpe ⇒ **13–50× fewer trades** to clear CI-LB. *(The validate-fast-alpha principle: per-trade Sharpe sets n-to-significance — structural premia prove in 14–250 trades vs 700–1800 for thin directional.)*
6. **Effective-n hardening (with guard)** — entry-day (`DATE(opened_at)`) cluster key everywhere; explicit `INSUFFICIENT_CLUSTERS` (floor ≥10–12); **AND validate the `.632`-replication bootstrap in `pf_ci_lower.py` does not narrow CI width** before it gates anything.

**Also endorsed (from the peer's doc, no conflict):** retroactive honest OOS replay of the lead to learn *this week*
whether rsi5070 will clear at n≥150 (de-risk the wait); widen the lead's qualifying universe (more honest picks/day,
condition unchanged); prove maker (~5bp) vs taker (16bp) fills to clear the bar at the same n.

## 2. DROPPED by the safety-critic — trust-for-speed traps (do NOT do)
- ❌ **Un-gate Active Picks Sync via `continue-on-error`** (synthesis ranked #1). Re-introduces the **masked-by-green-CI**
  pattern; silences a *snapshot* WON/LOST writer that isn't the promotion-grade source; root cause already addressed by
  #608. "15–45×" is illusory. **The correct fix is #1 above (fix it fail-loud), not silence it.**
- ❌ **Anytime-valid promotion gate** (`anytime_pf_gate`, synthesis #4). **Zero** alpha-spending machinery exists;
  mirroring a bootstrap percentile across the **hourly** recompute is **uncontrolled multiple testing**; "30–50% fewer
  days" reveals it's being used to promote *sooner*. **Promotion stays at the pre-registered fixed-n checkpoints.** A real
  e-process is *more* conservative and is a multi-week correctness project — out of scope.
- ⚠️ **Auto-loop new promotable conditions** — allowed only as an accrual mechanism; each NEW condition needs its own
  M-107 pre-registration; **do not re-tune rsi5070/handoff before their gates** (do-not-re-tune).

## 3. Sequenced plan
- **This week:** #1 resolver-stability (fail-loud) → #2 freshness heartbeat → #3 kill dead-source n → peer's retroactive replay of the lead.
- **Weeks 2–3:** #4 monkey-test (replay-only) ‖ #5 VIX rotator (shadow-forward, M-107) ‖ #6 effective-n + bootstrap validation.
- **At the gates (Jun-25, Jul-9):** judge on the *unchanged* fixed-n net-PF CI-LB > 1.15 / n_eff≥80 / time-split / conc<35% bar.

**Bottom line:** time-to-market compresses by **fixing the boring pipeline so picks resolve and accrue**, **adding
faster-to-prove structural archetypes (VIX carry)**, and **detecting staleness in 1h not 6 days** — *never* by silencing
failures, sequential peeking, padding n, promoting on replay-n, or re-tuning a pre-registered candidate. The trust anchors
do not move. The adversarial safety-critic just prevented us from "accelerating" by quietly lowering the bar twice.
