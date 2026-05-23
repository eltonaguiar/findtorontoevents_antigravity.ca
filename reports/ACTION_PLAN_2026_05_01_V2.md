# Action Plan v2 — 2026-05-01 Post-Mass-Merge Wave (post-5-AI-review)

## Revision summary

5 AI reviewers (DeepSeek, xAI Grok, Cerebras Qwen-235B, Cerebras GLM-4.7,
Moonshot Kimi-k2.6) flagged 9 distinct issues with v1. Consensus deltas
applied below. Original v1 archived at `ACTION_PLAN_2026_05_01_DRAFT.md`.

## Consensus blockers (≥3 of 5 reviewers flagged)

1. **B9 dependency error** (4/5) — v1 said "gated on V1" but V1 is UEPS,
   B9 is TradingAgents. Fixed: B9 now gated on **B23 (resolver
   SYSTEM_SOURCES verify) + tradingagents emitter producing valid picks**.
2. **B25 missing diagnostic step** (3/5) — fix-PR cannot be sequenced
   without a diagnostic first. Fixed: split into **B25-Diag** (log raw
   LLM responses for 7d) → **B25-Fix** (after diagnostic).
3. **14-day shadow rule** (Kimi flagged for B17/B18/B19/FOREX-RESOLVER-2)
   — Kimi cited the codebase's mandatory 14-day shadow before flip-on.
   Fixed: every gate/scoring change item now explicitly says "14-day
   shadow before flip-on; ship default-OFF behind explicit env flag".
4. **B7 Wire-Up Rule** (DeepSeek) — new integration needs production
   caller. Fixed: B7 ships as opt-in scaffold; production caller named
   when first wire-in PR lands (Q3 follow-up; not in this 7-day plan).

## Consensus deltas (≥2 reviewers agreed)

1. **B23 verify earlier** (GLM-4.7 + Cerebras-Qwen) — was at #4, now #2
   (immediately after Wave-1 verifications). One-line check that may
   reveal a critical resolver gap before any code lands.
2. **B2-redux grid panel earlier** (GLM-4.7) — was at #6, now #3. The
   asset-class × timeframe grid IS the diagnostic tool for the EQUITY
   regression (Item 4 below).
3. **V9/V10 explicit verification gates** (xAI-Grok) — was missing, now
   added: V9 (B4 48h soak post-merge stable) + V10 (B12 7d soak). These
   gate B5 + B13 respectively.
4. **HYRO-FRESHNESS earlier** (Cerebras-Qwen) — was at #11, now #7.
   Lower-risk than slippage testing and unblocks telemetry needed for
   downstream diagnostics.

## Reviewer verdicts

| Reviewer | Verdict |
|---|---|
| DeepSeek | accept-with-deltas |
| xAI Grok | needs-rewrite |
| Cerebras Qwen-235B | ready-to-execute (with deltas) |
| Cerebras GLM-4.7 | needs-rewrite |
| Kimi k2.6 | shadow-period concerns (incomplete reply) |

3 of 5 wanted rewrite, primarily on the dependency error + shadow-rule
issues. v2 below addresses every consensus blocker.

## Revised sequence (v2)

| Order | Item | Wave | Risk | Why now (revised) |
|------:|---|---|---|---|
| 1 | Verify V1-V10 (V1-V8 from v1 + new V9/V10 soak gates) | 1 | n/a | Confirms today's mass-merge actually delivered |
| 2 | **B23 verify** — confirm `tradingagents` is in `universal_pick_resolver.py SYSTEM_SOURCES`; ship 1-line fix if missing | 7 | LOW | Closes the TradingAgents resolver loop; unblocks B9 |
| 3 | **B2-redux** Asset-Class × Timeframe grid panel | 2 | LOW | **Diagnostic tool for the EQUITY regression below** |
| 4 | **EQUITY-REGRESS diagnostic** (no PR; report only) — **prereq: Item 3 merged** | 3 | n/a | Use B2-redux grid + B16 daily readout to identify which strategy degraded |
| 5 | **B6** Cursor Phase 5 concept UI chips/filters | 4 | LOW | Surfaces B4's `concept_family` field on /audit |
| 6 | **B19** Pair-level carve-out (`atr_percentile_gate`, `BTCUSDT`, `LONG`) — **default-OFF + 14-day shadow** | 5 | MED | Surfaces a verified single-pair edge; behind shadow flag per Default-OFF rule |
| 7 | **HYRO-FRESHNESS** audit (revive vs retire) | 3 | LOW | Restores hyrotrader telemetry; needed for B5 evidence |
| 8 | **B14-redux** Liquidity / slippage stress test | 2 | LOW | Re-create the closed #586 |
| 9 | **FOREX-RESOLVER-2** (drop non-JPY 5.0 → 1.5) — **default-OFF + 14-day shadow A/B** | 3 | MED | Largest single edge gap (FOREX PF 0.27); shadow-only first |
| 10 | **B7** CFTC COT live-wire — **opt-in scaffold only**; production caller named in follow-up PR | 5 | MED | Highest-leverage missing FOREX/COMMODITY signal; respect Wire-Up Rule |
| 11 | **B25-Diag** Log raw LLM responses per ticker for 7 days; produce report | 6 | n/a | Diagnostic-first; no fix until data is in |
| 12 | **B9** TradingAgents wire-in (14-day shadow) — gated on Item 2 (B23 verify) | 5 | LOW | Activates adversarial-debate sidecar; default-OFF |
| 13 | **B5** Cursor Phase 3 scoring — gated on **V9 (B4 48h soak ✅)** | 4 | HIGH | Default-OFF + **14-day shadow** before flip-on |
| 14 | **B13** Per-class HMM — gated on **V10 (B12 7d soak ✅)** | 4 | HIGH | Default-OFF + **14-day shadow** before flip-on |
| 15 | **B17** HC button after-cost gating — gated on B16 artifact + **14-day shadow** | 5 | MED | Tightens HC; shadow-mode first |
| 16 | **B18** Shadow-mode auto-promotion — gated on B16 artifact + **14-day shadow** | 5 | MED | Shadow-promotes no-history strategies |
| 17 | **B25-Fix** TradingAgents identical-metrics fix — gated on Item 11 (B25-Diag report) | 7 | MED | Only after diagnostic surfaces root cause |

## Out of scope (deferred — same as v1)
- B22 meme producer (operator decision required)
- B26 end-to-end smoke (depends on B25-Fix)
- B10 UEPS KPI panel (needs n≥10 UEPS closes)

## Verification gates (V1-V10)

| ID | What | When | Pass criterion |
|----|---|---|---|
| V1 | UEPS picks reach /audit main table (post-#582) | next dashboard cycle | ≥1 row with `pick_type=long_term_value` in `picks.active` |
| V2 | EQUITY × POSITION lane non-empty | next cycle | ≥2 rows (PEP, LLY confirmed) |
| V3 | TradingAgents emitter dormant when flag off | now | dry-run prints OFF + zero file writes |
| V4 | Penny skyrocket cron wired | now | workflow registered, last run timestamped |
| V5 | PEAD cache persists across runs | next 2 cycles | ≥1 commit touching `data/earnings/` |
| V6 | concept_family stamped on every pick | now | 100% coverage on `picks.active` |
| V7 | BOND credit-spread emitting | when bond-agent fires | ≥1 row OR signal-availability gap logged |
| V8 (NEW) | B16 daily artifact emits | within 24h | `reports/forward_edge_audit_<date>.md` exists |
| V9 (NEW) | B4 48h post-merge soak — concept registry stable | 2026-05-03 21:23 UTC | (a) `concept_family` field present on ≥99% of `picks.active` over 48h sample; (b) zero `concept_*`-tagged errors in `pipeline_health.json`; (c) registry-driven mappings unchanged across ≥10 dashboard rebuilds |
| V10 (NEW) | B12 7d post-merge soak — source-liveness watchdog stable | 2026-05-08 21:21 UTC | (a) zero false-positive alerts (alert with no actual stale source); (b) ≥1 true-positive (alert correctly identified an actual stale source); (c) watchdog runtime <60s per cycle |

## Risk controls (v2 strengthened)

- **14-day shadow rule** explicitly applied to B5, B13, B17, B18, B19,
  FOREX-RESOLVER-2 (was missing on B17/B18/B19/FOREX in v1).
- **Wire-Up Rule** explicitly applied to B7 (now opt-in scaffold; production
  caller named in follow-up PR).
- **Diagnostic-before-fix** for B25 (was sequenced as fix in v1).
- All workflow auto-commits use `safe_push.sh`.
- Every shadow-flag flip-on requires:
  - n ≥ 30 closed picks under shadow
  - Wilson 95% lower bound on WR ≥ class baseline
  - After-cost net positive

## Acceptance criteria

- **Within 7 days:** items 1-10 complete; queue down to 6 gated items.
- **Within 14 days:** items 11 (B25-Diag) + 12 (B9 shadow start) live;
  B25-Diag accruing log data toward its 7-day window.
- **Within 21 days:** B25-Fix (item 17) ships after B25-Diag report;
  items 13-16 begin shadow (B5/B13/B17/B18) after their prereq soaks.
- **Within 28 days:** all shadow flips evaluated; PF measurable via B16
  daily readout.
- **Overall PF target:** 0.98 → ≥1.05 within 21 days for items not
  gated on shadow flip-on; ≥1.10 within 28 days post-shadow-flip.

---

**This is v2.** Sending to 1 final reviewer (DeepSeek — most thorough
on round 1) before implementation.
