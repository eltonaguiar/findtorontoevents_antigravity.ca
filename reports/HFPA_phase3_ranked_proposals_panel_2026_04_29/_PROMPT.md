You are a senior quant on a hedge-fund-grade PR-prioritization panel. The orchestrator is running THEASK Phase 3 RETROACTIVELY — they shipped 28 PRs in Phase 4 directly from Phase 2 per-class panel verdicts, skipping the cross-class ranking step. Your job is to RE-RANK these PRs by EXPECTED IMPACT TO HEDGE-FUND-GRADE PERFORMANCE and tell the operator what shipped in suboptimal order, what was missed, and what to prioritize next session. Return ONLY a JSON object matching the schema at the end. No prose, no markdown fences.

# Context — system baseline (do not project beyond it)
- System WR 31.1% / PF 0.72 / cumulative -$1,134 across 3,500 trades (Apr-21 forensic)
- 48h bounce: +$111 @ 39.3% WR
- EQUITY 30d hits Tier 2 candidate (PF 1.385, MDD-bound)
- CRYPTO MDD ~140-177% (the binding constraint per 5-stream consensus)
- FOREX clean WR 49.6% (margin-WR-only); resolver fix (1bp -> 5bp) not yet shipped
- COMMODITY: Metals net +$30; Oil/Agro net negative
- ETF: sector edge real; broad-market (IWM/GLD) drag confirmed unanimous

# Per-class Phase 2 verdicts (one-line each)
- CRYPTO (Phase 2-A 8/8 unanimous): kill `rapid_fire x rsi_bounce`; SHORT regime-gate opt-in; vol-target/Kelly is THE binding fix for MDD
- EQUITY (Phase 2-B 9/9 unanimous): kill goldmine_stocks + copy_trader_highscore; blacklist JNJ/ABBV/MRK/GS LONG-momentum; unblock kimi_riseoftheclaw
- FOREX (Phase 2-C 6/7): kill JPY-cross BUY direction; resolver A/B test (5bp threshold) NOT shipped this session
- COMMODITY (Phase 2-D 7/7): keep Metals only, kill Oil + Agro sub-classes; CFTC COT scaffold (live wire NOT shipped)
- ETF (Phase 2-E 6/6 unanimous): kill broad-market IWM + GLD; sector-only edge
- BOND (Phase 2-F): bond_credit_spread emitter wire-up only; no major changes
- FUTURES (Phase 2-F 9/9): whitelist ZN/ES/NQ; CFTC COT scaffold (live wire NOT shipped)

# The 28+ session PRs (compressed) — Cat / Class / Default / LOC / Risk / Expected impact

## SURGICAL KILLS (8) — default-ON
- #514 kill goldmine_stocks (EQUITY, 363 LOC, LOW, +53% sum_pnl drag removed, n=13 WR 0%)
- #509 kill rapid_fire x macd_rsi_confluence (EQUITY, 335 LOC, LOW, BANNED leak source #1)
- #487 kill copy_trader_highscore + goldmine_stocks v0 (EQUITY, 783 LOC, LOW, -78%/-70% drag)
- #516 kill rapid_fire x rsi_bounce (CRYPTO, 348 LOC, LOW, Phase 2-A 8/8 bleeder)
- #517 kill JPY-cross BUY (FOREX, 215 LOC, LOW, -36.83% sum drag CADJPY/EURJPY/NZDJPY)
- #520 kill agro/oil sub-classes (COMMODITY, 321 LOC, LOW, +$30 Metals only)
- #521 blacklist JNJ+ABBV+MRK+GS LONG-momentum (EQUITY, 311 LOC, LOW, +9% sum drag avoid)
- #524 kill IWM + GLD broad-market (ETF, 245 LOC, LOW, sector-only edge)

## GATE / SIZING (5)
- #515 trust-tier disable non-CRYPTO (NON-CRYPTO, 288 LOC, MED, default-ON, Gate 1 Q4 unanimous)
- #525 CRYPTO SHORT regime-gate (CRYPTO, 415 LOC, LOW, default-OFF, 7/8)
- #527 CRYPTO vol-target / Kelly-resize (CRYPTO, 299 LOC, LOW, default-OFF, 5-stream consensus on MDD)
- #505 null wf_verdict treat-as-FAILING (ALL, 292 LOC, LOW, default-OFF)
- #506 quan_engine MAX_CONCURRENT_PER_SYMBOL (CRYPTO, 344 LOC, LOW, default-OFF)
- #508 EQUITY trust-tier exemption (EQUITY, 233 LOC, LOW, default-OFF; superseded by #515)

## EDGE-DELIVERY UNBLOCKS (5)
- #519 kill_list scrub + rsi2 + mutation_name fallback (EQUITY+CRYPTO, 397 LOC, MED, unblocks 6 dormant S-tier)
- #522 kimi_riseoftheclaw promotion-step (EQUITY, 288 LOC, MED, 9/9 unanimous)
- #523 luxalgo_confluence un-paper-only (CRYPTO, 209 LOC, LOW, PROVEN tier)
- #486 bond_credit_spread emitter wire (BOND, 73 LOC, LOW, agent reaches scheduler)
- #484 mutation engine wire-up (ALL, 503 LOC, LOW, default-OFF, scan-loop wire)

## UNIVERSE / SCAFFOLDS (3)
- #492 asset-class precedence (ZN=F→FUTURES) (FUTURES+BOND, 242 LOC, LOW, label correctness)
- #494 UEPS price failover (EQUITY, 1837 LOC, MED, equity 0/0 emit unblocked)
- #526 FUTURES whitelist + COT scaffold (FUTURES, 729 LOC, LOW, default-OFF, ZN/ES/NQ + COT dormant)
- #518 UEPS sync into active_picks 4h cron (EQUITY, 295 LOC, MED, picks reach scoring path) [open]

## MISC FIXES / DASHBOARD / INFRA (12)
- #495 HF_QUALITY_GATE_ENABLED default-ON (ALL, 714 LOC, HIGH, telemetry guardrails)
- #489 disable CRYPTO RSI-4h killzone + expand BANNED (CRYPTO, 165 LOC, MED, writer-artifact false-reject removed)
- #497 R2 phantom HALT + R3 circuit-breaker stale-state (ALL, 523 LOC, MED, regression fixes)
- #500 signal_validation Tier-2 hero card (AUDIT, 862 LOC, LOW, dashboard XSS-safe)
- #499 PEAD bootstrap (EQUITY, 563 LOC, LOW, signal cache)
- #496 PEAD nested type guards (EQUITY, 71 LOC, LOW, test-pin)
- #501 meme env-flag asset-class hint (CRYPTO, 159 LOC, LOW)
- #502 _cache_path harden (EQUITY, 76 LOC, LOW, defense-in-depth)
- #503 dashboard import error log (AUDIT, 9 LOC, LOW)
- #504 events past-dated filter (EVENTS, 90 LOC, LOW, Goal #3)
- #510 claude_gainer_st visibility (AUDIT, 28 LOC, LOW)
- #491 Hyro silent-fail logging (AUDIT, 84 LOC, LOW, WARNING-level)
- #493 remove fatal git fetch --unshallow (CI, -4 LOC, MED, OOM fix)
- #498 docs (n/a, 62 LOC)
- #511 livetrader2026 secret-rotation plan (INFRA, 139 LOC, security) [open]
- #512 phantom-HALT mixed-unit XFAIL (TESTING, 101 LOC) [open]
- #513 UEPS emit verification chore (EQUITY, 91 LOC) [open]

# Chronological shipping order (what we DID)
#484 → #486 → #487 → #489 → #491 → #492 → #493 → #494 → #495 → #496 → #497 → #498 → #499 → #500 → #501 → #502 → #503 → #504 → #505 → #506 → #508 → #509 → #510 → #514 → #515 → #516 → #517 → #519 → #520 → #521 → #522 → #523 → #524 → #525 → #526 → #527

# Operator pre-flagged missing actions (deferred-note)
1. FOREX resolver A/B test (5bp threshold) — Phase 2-C 6/7 verdict; biggest expected-impact item NOT shipped
2. CFTC COT live-wire (only scaffolded in #526; no scoring-path binding)
3. HMM regime detection live wire-up (9/9 panel methodology consensus; no PR)
4. Net-of-cost dashboard panel (Gate 1 Q5=B verdict)
5. CPCV gate flip default-on (#507 scaffold open; awaits CPCV-validated PF > 1.5 lower-bound)

# Anti-hallucination contract (HARD)
- Cite PR numbers before any recommendation
- Do NOT invent expected-impact numbers — use what's in the table or say "no panel-projected magnitude"
- Be honest: if you think operator shipped a wrong-order PR (e.g., #495 default-ON HIGH-risk before surgical kills), say so by PR#
- Re-ranking should consider: surgical kills with quantified PnL drag removed are highest-leverage; broad gate changes (#495, #515) carry HIGH risk and should follow not lead; the FOREX resolver fix is the operator's #1 missing action
- Session grade should reflect ordering quality + missed-action severity, not absolute PR count

# Required JSON schema (return ONLY this object)
{
  "model_id": "<provider/model>",
  "reranked_priority": [
    {"pr": <number>, "rank": <integer 1-N>, "rationale": "<one sentence>"}
  ],
  "ordering_critiques": [
    {"shipped_pr": <number>, "should_have_shipped_first": <number_or_null>, "reason": "<why the order was wrong or right>"}
  ],
  "missing_actions_we_didnt_ship": [
    {"action": "<short name>", "expected_impact": "<numeric or qualitative>", "priority": "P0|P1|P2"}
  ],
  "overall_session_grade": "A|B|C|D|F",
  "ONE_BIG_LESSON_FOR_NEXT_SESSION": "<one sentence>"
}

reranked_priority: top 15 PRs by expected impact, in order. ordering_critiques: at least 3 entries. missing_actions: at least 3 entries.
