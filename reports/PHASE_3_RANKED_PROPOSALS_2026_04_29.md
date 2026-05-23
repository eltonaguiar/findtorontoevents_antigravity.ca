# Phase 3 — Ranked PR Proposals (retroactive)

**Status:** Retroactive Phase 3 artifact for THEASK 5-phase plan.
**Date:** 2026-04-29
**Scope:** All 28 session PRs (24 merged + 4 open as of dispatch).
**Operator:** zerounderscore@gmail.com.

Per THEASK.md L36, Phase 3 was supposed to consolidate Phase 2 research into a single ranked-proposal MD with AI panel input on ordering, BEFORE shipping action PRs. The orchestrator skipped this and shipped action PRs directly from Phase 2 panel verdicts. This artifact closes the gap.

The deferred-note (`reports/DEFERRED_PHASE_3_RANKED_PROPOSAL_NOTE.md`) and Phase 5 testing-protocol panel (`reports/HFPA_phase5_testing_protocol_panel_2026_04_29/`) are inputs.

---

## All 28 session PRs (sorted by panel-suggested priority, current shipping order in `merged_at`)

Legend:
- **Effort:** XS (<200 LOC), S (<400), M (<800), L (>800)
- **Risk:** LOW (default-off / surgical / docs), MED (default-on but easy revert), HIGH (default-on broad behavior change)
- **Default:** ON = active in production immediately, OFF = opt-in env-flag only
- **Panel verdict:** "X/Y" = panelists in agreement / total panelists; "cross-stream" = appeared in 5-stream consensus

| # | PR | Category | Class | Default | LOC | Effort | Risk | Expected impact | Panel verdict | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | #514 kill goldmine_stocks | surgical kill | EQUITY | ON | 363 | S | LOW | +53.36% sum_pnl removed (n=13 WR 0%) | Cross-stream + Copilot meta | merged |
| 2 | #509 kill rapid_fire x macd_rsi_confluence | surgical kill | EQUITY | ON | 335 | S | LOW | BANNED leak source #1 plug | Phase 2-B 8/8 | merged |
| 3 | #487 kill copy_trader_highscore + goldmine_stocks v0 | surgical kill | EQUITY | ON | 783 | M | LOW | -78% / -70% drag removed | Mutation protocol pre-panel | merged |
| 4 | #516 kill rapid_fire x rsi_bounce | surgical kill | CRYPTO | ON | 348 | S | LOW | Phase 2-A unanimous bleeder | Phase 2-A 8/8 | merged |
| 5 | #517 kill JPY-cross BUY-direction | surgical kill | FOREX | ON | 215 | XS | LOW | -36.83% sum drag (CADJPY/EURJPY/NZDJPY) | Phase 2-C 6/7 | merged |
| 6 | #520 kill agro/oil + silver/gold sub-classes | surgical kill | COMMODITY | ON | 321 | S | LOW | Keep Metals only (+$30 net) | Phase 2-D 7/7 | open |
| 7 | #521 blacklist JNJ+ABBV+MRK+GS LONG-momentum | surgical kill | EQUITY | ON | 311 | S | LOW | +9% sum drag avoid | Phase 2-B 9/9 | merged |
| 8 | #524 kill IWM + GLD broad-market ETF | surgical kill | ETF | ON | 245 | S | LOW | Sector-only edge, broad-market drag | Phase 2-E 6/6 | merged |
| 9 | #515 disable trust-tier for non-CRYPTO | gate change | NON-CRYPTO | ON | 288 | S | MED | Gate 1 Q4 unanimous; CRYPTO untouched | Cross-stream + 9/9 | merged |
| 10 | #525 CRYPTO SHORT regime-gate | gate change | CRYPTO | OFF | 415 | M | LOW | Phase 2-A 7/8 (vs 8/8 SHORT-bias regime) | Phase 2-A 7/8 | merged |
| 11 | #527 CRYPTO vol-target / Kelly-resize sidecar | sizing | CRYPTO | OFF | 299 | S | LOW | MDD reduction 140-177% to <50% target | 5-stream consensus | merged |
| 12 | #519 kill_list scrub + rsi2 filter + mutation_name fallback | unblock | EQUITY+CRYPTO | ON | 397 | S | MED | Unblocks 6 dormant S-tier strategies | Edge-delivery investigation | merged |
| 13 | #522 kimi_riseoftheclaw promotion-step | unblock | EQUITY | ON | 288 | S | MED | Phase 2-B 9/9 unanimous | Phase 2-B 9/9 | merged |
| 14 | #523 luxalgo_confluence un-paper-only | unblock | CRYPTO | ON | 209 | XS | LOW | PROVEN tier, stale-config blocker | Edge-delivery investigation | merged |
| 15 | #492 asset-class precedence (ZN=F→FUTURES) | universe | FUTURES+BOND | ON | 242 | XS | LOW | Cross-class label correctness | CHARTER §5 footnote | merged |
| 16 | #494 UEPS price failover | universe | EQUITY | ON | 1837 | L | MED | Equity 0/0 emit unblocked | Failover audit | merged |
| 17 | #526 FUTURES whitelist + COT scaffold | universe | FUTURES | OFF | 729 | M | LOW | ZN/ES/NQ + CFTC COT (dormant) | Phase 2-F 9/9 | merged |
| 18 | #518 UEPS sync into active_picks (4h cron) | universe | EQUITY | ON | 295 | S | MED | UEPS picks reach scoring path | Wire-up rule | open |
| 19 | #495 HF_QUALITY_GATE_ENABLED default-on | gate change | ALL | ON | 714 | M | HIGH | Telemetry guardrails default-on | Pre-Phase 1 cleanup | merged |
| 20 | #489 disable CRYPTO RSI-4h killzone + expand BANNED | gate change | CRYPTO | ON | 165 | XS | MED | Writer-artifact false-reject removed | Pre-Phase 1 cleanup | merged |
| 21 | #484 mutation engine wire-up (opt-in) | unblock | ALL | OFF | 503 | M | LOW | apply_mutations_to_scanner() in scan loop | Wire-up rule | merged |
| 22 | #486 bond_credit_spread emitter wire-up | unblock | BOND | ON | 73 | XS | LOW | Bond agent reaches scheduled emitter | Wire-up rule | merged |
| 23 | #497 R2 phantom HALT + R3 circuit-breaker stale-state | misc fix | ALL | ON | 523 | M | MED | Regression fixes for ghost halts | Forensic | merged |
| 24 | #500 signal_validation Tier-2 hero card | dashboard | AUDIT | ON | 862 | L | LOW | XSS-safe Tier-2 hero card | Phase 4 dashboard | merged |
| 25 | #499 PEAD bootstrap (data/earnings/) | misc fix | EQUITY | ON | 563 | M | LOW | PEAD signal cache bootstrap | Phase 2-B sidekick | merged |
| 26 | #496 PEAD nested type guards | misc fix | EQUITY | ON | 71 | XS | LOW | Test-pin for #499 | Phase 2-B sidekick | merged |
| 27 | #505 null wf_verdict treat-as-FAILING (opt-in) | gate change | ALL | OFF | 292 | S | LOW | Surgical fail-closed flag | Phase 2-A | merged |
| 28 | #506 quan_engine MAX_CONCURRENT_PER_SYMBOL cap | gate change | CRYPTO | OFF | 344 | S | LOW | Anti-flood gate (default-off) | quan_engine MATIC artifact | merged |
| 29 | #508 EQUITY trust-tier exemption (opt-in) | gate change | EQUITY | OFF | 233 | XS | LOW | Pre-#515 stepping stone | Phase 2-B | merged |
| 30 | #501 meme env-flag asset-class hint | misc fix | CRYPTO | ON | 159 | XS | LOW | Asset-class hint precedence | Phase 4 dashboard | merged |
| 31 | #502 _cache_path harden ticker injection | misc fix | EQUITY | ON | 76 | XS | LOW | Defense-in-depth for #494 | Security review | merged |
| 32 | #503 dashboard import error log | misc fix | AUDIT | ON | 9 | XS | LOW | Diagnose missing asset_class import | Phase 4 dashboard | merged |
| 33 | #504 events past-dated UPCOMING filter | misc fix | EVENTS | ON | 90 | XS | LOW | Goal #3 (events grid) | Goal #3 | merged |
| 34 | #510 claude_gainer_st recent_closed | dashboard | AUDIT | ON | 28 | XS | LOW | Dashboard visibility | Visibility audit | merged |
| 35 | #511 livetrader2026 secret rotation plan | docs/security | INFRA | n/a | 139 | XS | LOW | Stage-1 PR; needs operator FTP | Security review | open |
| 36 | #512 phantom-HALT mixed-unit XFAIL test | misc fix | TESTING | ON | 101 | XS | LOW | Regression pin (XFAIL pending P0-DATA) | Phase 5 sidekick | open |
| 37 | #513 UEPS emit verification chore | docs | EQUITY | n/a | 91 | XS | LOW | EMITTING n_long=30 verified | Verification chore | open |
| 38 | #491 Hyro silent-fail logging upgrade | misc fix | AUDIT | ON | 84 | XS | LOW | WARNING-level for previously-silent failures | Phase 4 audit | merged |
| 39 | #493 remove fatal git fetch --unshallow | infra | CI | ON | -4 | XS | MED | 37GB .git OOM ubuntu-latest fix | CI cleanup | merged |
| 40 | #498 docs CI cleanup summary | docs | n/a | n/a | 62 | XS | LOW | Session note | Documentation | merged |

(Where the "PR count" exceeds 28: this list captures **all session PRs including pre-Phase-2 misc fixes** that the operator's brief lumps into "the 28". The Phase 2 panel-driven action set is rows 1-18; rows 19-40 are pre-existing or sidekick/infra fixes.)

---

## Sequencing observations (pre-AI-panel)

**What we shipped first (chronologically):** #484 → #486 → #487 → #489 → #491 → #492 → #493 → #494 → #495 → #496 → #497 → #498 → #499 → #500 → #501 → #502 → #503 → #504 → #505 → #506 → #508 → #509 → #510 → #514 → #515 → #516 → #517 → #519 → #520 → #521 → #522 → #523 → #524 → #525 → #526 → #527.

**What the panel-priority ordering would have been (top of this table):**
The seven surgical-kill PRs (#514 #509 #487 #516 #517 #520 #521 #524) are the LOWEST-risk highest-EV-leverage actions (kills with quantified PnL drag removed). The two CRYPTO sizing/regime opt-ins (#525 #527) are MEDIUM-EV but require shadow-run before flipping default-on.

**Suspicious sequencing:**
- #495 (HF_QUALITY_GATE_ENABLED default-on, HIGH risk, 714 LOC) shipped **before** any of the surgical kills — broader change with less consensus shipped before narrower clearly-positive changes.
- #494 (UEPS price failover, 1837 LOC, MED risk) shipped before all #514/#516/#517/#520/#521/#524 surgical kills despite being the largest single PR of the session.
- #515 (trust-tier disable for non-CRYPTO, default-ON, MED risk) shipped between surgical kills #509+#514 and #516. Cross-stream consensus exists, but the broader change went out before the smaller ones cleared production.

**What's missing (operator-flagged in `DEFERRED_PHASE_3_RANKED_PROPOSAL_NOTE.md`):**
1. FOREX resolver A/B test (5bp threshold) — Phase 2-C 6/7 verdict, queued. Largest expected-impact item NOT shipped this session.
2. CFTC COT live-wire (#526 only scaffolds the fetcher; no live binding to scoring path).
3. HMM regime detection live wire-up (9/9 panel methodology consensus, no PR shipped).
4. Net-of-cost dashboard panel (Gate 1 Q5=B verdict).
5. CPCV gate flip default-on (#507 scaffold open; awaits CPCV-validated PF lower-5%-bound > 1.5).

---

## AI Panel Re-Ranking (Phase 3, retroactive)

**Dispatched:** 2026-04-29 via `reports/HFPA_phase3_ranked_proposals_panel_2026_04_29/_dispatch.py`. 7/7 panelists responded with valid JSON.

### Panel
- Cerebras: `qwen-3-235b-a22b-instruct-2507`, `gpt-oss-120b`, `zai-glm-4.7`
- Ollama Cloud: `deepseek-v3.1:671b-cloud`, `gpt-oss:120b-cloud`, `glm-4.6:cloud`, `kimi-k2.5:cloud`

### Re-ranked top 9 PRs (7/7 unanimous appearance)

Sorted by panel-count then median rank:

| Panel rank | PR | Median rank | Range | Theme |
|---|---|---|---|---|
| 1 | #514 (kill goldmine_stocks, EQUITY) | 1 | 1-4 | Largest quantified drag (+53%) — unanimous #1 |
| 2 | #516 (kill rapid_fire×rsi_bounce, CRYPTO) | 3 | 2-7 | Phase 2-A 8/8 bleeder |
| 3 | #487 (kill copy_trader_highscore + goldmine_stocks v0) | 2 | 1-7 | -78%/-70% drag (6/7 panel) |
| 4 | #517 (kill JPY-cross BUY, FOREX) | 4 | 3-5 | -36.83% sum drag (6/7 panel) |
| 5 | #521 (blacklist JNJ/ABBV/MRK/GS LONG) | 5 | 4-14 | EQUITY 9/9 unanimous |
| 6 | #520 (kill agro/oil COMMODITY) | 6 | 3-13 | Metals-only retain |
| 7 | #524 (kill IWM/GLD broad-market ETF) | 7 | 5-10 | ETF 6/6 unanimous |
| 8 | #527 (CRYPTO vol-target / Kelly) | 9 | 1-9 | Binding-MDD-constraint fix; 1 panelist (kimi) ranked #1 |
| 9 | #525 (CRYPTO SHORT regime-gate) | 10 | 9-12 | Phase 2-A 7/8 |
| 10 | #522 (kimi_riseoftheclaw promotion-step) | 10 | 7-12 | EQUITY 9/9 |
| 11 | #519 (kill_list scrub + rsi2 + mutation_name) | 10 | 6-13 | Unblocks 6 dormant S-tier |
| 12 | #523 (luxalgo_confluence un-paper-only) | 13 | 8-13 | PROVEN tier (6/7) |

Notable lower placements: #515 (median 14, only 4/7 mention), #495 (median 15, only 2/7 mention) — i.e. the gate-changes ranked lowest by all panelists.

### Top ordering critiques (≥2 panelists agree)

1. **`#495 should have shipped AFTER #514` — 7/7 unanimous.**
   `qwen-3-235b`: "HIGH-risk HF_QUALITY_GATE_ENABLED shipped before surgical kills with quantified PnL drag, inverted risk priority"
   `gpt-oss-120b`: "High-risk HF_QUALITY_GATE was enabled before the highest-leverage surgical kills, risking regression before core drag removal"
   This is the single biggest ordering error of the session — every panelist independently flagged it.

2. **`#527 should have shipped AFTER #484` — 2/7 panelists (zai-glm-4.7 + kimi-k2.5).**
   `zai-glm-4.7`: "#527 (binding MDD fix for CRYPTO) shipped last (#35), while #484 (mutation engine wire-up) shipped first; the binding constraint fix must precede generic engine work."
   `kimi-k2.5`: "Binding MDD constraint fix (#527) shipped last at position 36 despite 5-stream consensus identifying vol-target/Kelly as THE fix for 140-177% MDD; catastrophic prioritization error."
   1 panelist (qwen) ranked #527 as #1; the spread (1-9) reflects disagreement on whether default-OFF opt-in changes the priority calculation.

3. **`Surgical kills should have led, infrastructure/logging followed.`**
   `zai-glm-4.7`: "#517 (-36.83% FOREX drag removal) shipped at #26, while #491 (Hyro silent-fail logging) shipped at #5; logging is lower priority than stopping quantified capital bleed."
   `zai-glm-4.7`: "#516 (CRYPTO bleeder kill) shipped at #24, while #493 (git fetch fix) shipped at #7; CI fixes are lower priority than removing a unanimous class bleeder."
   `gpt-oss-120b`: "EQUITY trust-tier exemption [#508] was applied before the broader non-crypto trust-tier disable [#515], creating redundant gating."

### Missing actions panel surfaced (we DIDN'T ship)

| Action | Panel votes | Modal priority | Notes |
|---|---|---|---|
| FOREX resolver A/B test (5bp threshold) | 7/7 | P0 | Largest expected-impact item NOT shipped — Phase 2-C 6/7 verdict was queued in deferred-note |
| CFTC COT live-wire (scoring-path binding) | 7/7 | P0/P1 | #526 only scaffolded the fetcher; no scoring-path binding |
| HMM regime detection live wire-up | 7/7 | P0/P1 | 9/9 panel methodology consensus; no PR shipped |
| Net-of-cost dashboard panel | 3/7 | P2 | Gate 1 Q5=B verdict |
| CPCV gate flip default-on | 3/7 | P2 | #507 scaffold open; awaits PF lower-bound > 1.5 |

The top-3 missing actions overlap exactly with the deferred-note's flagged items (1, 2, 3). The panel did NOT independently surface a new missing action with 4+ votes, but did re-confirm the operator's self-flagged priorities at unanimous-7/7.

### Session grade (panel)

| Panelist | Grade |
|---|---|
| qwen-3-235b-a22b-instruct-2507 | C |
| gpt-oss-120b | C |
| zai-glm-4.7 | C |
| deepseek-v3.1:671b-cloud | C |
| gpt-oss:120b-cloud | C |
| glm-4.6:cloud | C |
| kimi-k2.5:cloud | D |

**Aggregate GPA: 1.86 → Grade C** (6/7 C, 1/7 D).

The "C" verdict reflects: surgical kills did all eventually ship (positive), but in suboptimal order (negative), with the binding-MDD constraint fix shipped last (negative) and the operator-flagged P0 missing actions (FOREX resolver, CFTC COT live-wire, HMM regime) NOT addressed (negative). No "F" because the work that did ship has consensus support and is reversible.

### ONE BIG LESSON for next session — verbatim per panelist

- **qwen-3-235b**: "Surgical kills with quantified PnL drag must ship before high-risk global flags or large-LOC non-core changes."
- **gpt-oss-120b**: "Ship the highest-leverage surgical kills first, then defer high-risk gating and scaffold work to preserve performance gains."
- **zai-glm-4.7**: "Prioritize quantified PnL drag removal and binding constraint fixes before telemetry, logging, or infrastructure changes."
- **deepseek-v3.1**: "Prioritize surgical kills with quantified PnL impact before HIGH-risk system gates, and ship the FOREX resolver fix immediately to capture the biggest expected-impact improvement."
- **gpt-oss-cloud**: "Prioritize shipping the high-impact risk-mitigation fixes (FOREX resolver test, COT live-wire, HMM regime) before low-risk infra and dashboard changes."
- **glm-4.6**: "Ship all quantified surgical kills before any gate, scaffold, or infrastructure changes to maximize immediate PnL recovery."
- **kimi-k2.5**: "Ship binding constraint fixes (MDD/resolver) and unanimous surgical kills before guardrails and dashboards; never ship HIGH-risk infrastructure before alpha recovery."

**Convergent theme (7/7 panelists):** Order matters as much as content. Quantified-drag surgical kills come first; HIGH-risk default-on gates and scaffolds come last; the FOREX resolver A/B is the operator's #1 missed action.

### Operator decision (for next session)

**Recommended actions based on panel:**

1. **Reorder remaining queue** — bump these to the top of next session's queue:
   - FOREX resolver A/B test at 5bp threshold (Phase 2-C 6/7 verdict; 7/7 panel P0)
   - CFTC COT live-wire (binding to scoring path; 7/7 panel P0/P1)
   - HMM regime detection live wire-up (9/9 prior panel + 7/7 this panel)

2. **Validate already-shipped default-OFF opt-ins via shadow-runs** — #525, #527, #505, #506, #508, #526. Per Phase 5 testing-protocol panel, shadow-run BEFORE flipping default-on.

3. **Operator policy note for next session:** Adopt the convergent panel rule — *quantified-drag surgical kills ship before any default-on gate change or HIGH-risk infrastructure PR*. Build a pre-flight ordering check (lint-style) into the orchestrator that blocks default-on HIGH-risk PRs from merging until all queued surgical kills are merged.

4. **Don't repeat #495-vs-#514 ordering error** — make HIGH-risk default-on PRs queue last, not first, when surgical kills are pending. This was the single most-flagged error this session (7/7 unanimous).

5. **Decision required:** Ship #518 (UEPS sync into active_picks 4h cron) and #520 (currently open) immediately — they are within the panel-top-12 ranked actions but still in PR-open state.

### Provenance

- Panel artifacts: `reports/HFPA_phase3_ranked_proposals_panel_2026_04_29/{cerebras,ollama}_*.md`
- Synthesis trace: `reports/HFPA_phase3_ranked_proposals_panel_2026_04_29/_synthesis_output.txt`
- Dispatch summary: `reports/HFPA_phase3_ranked_proposals_panel_2026_04_29/_dispatch_summary.json` (7/7 valid JSON)
- Inputs: `reports/DEFERRED_PHASE_3_RANKED_PROPOSAL_NOTE.md`, all merged + open PRs cataloged via `gh pr list`

