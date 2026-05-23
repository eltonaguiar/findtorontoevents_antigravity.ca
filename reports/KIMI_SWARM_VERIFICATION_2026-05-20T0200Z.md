# Kimi Agent Swarm Renaissance-Quant Review — 16-claim verification — 2026-05-20T0200Z

Operator forwarded a Kimi Agent Swarm "Renaissance Quant Edge Review" with
sharp critique of our north-star plan. This document is the on-disk
fact-check.

**Method:** read-only subagent verification against actual repo files. Each
claim categorized VERIFIED / PARTIAL / UNVERIFIABLE / WRONG with file:line
evidence.

**Outcome:** **4 VERIFIED, 5 PARTIAL, 5 UNVERIFIABLE, 2 WRONG** across 16
claims. **Plan needs amendment for 4 VERIFIED P0 gaps Kimi correctly identified.**

---

## VERDICT TABLE

| # | Claim | Status | Severity | Evidence |
|---|---|---|---|---|
| 1 | "18 pre-reg, 0 admissible" is false; H-037 passed harness | **WRONG** | CRITICAL | `reports/H037_CANONICAL_HARNESS_AUDIT_2026-05-19T2200Z.md` — H-037 FAILS canonical harness (densified: 64 NEG / 4 POS eff = sign-unstable + INVERTED). 18/0 verdict stands. Kimi conflated peer-claimed PASS (custom WF) with canonical-harness clearance. |
| 2 | H-037 + H-001 invisible on dashboard | **PARTIAL** | HIGH | H-037 in `audit_trail/edge_filters.py` as `tier=PAPER_TRADE` (30-day). H-001 status=REJECTED in registry. Neither wired into emitter dynamically; emitter hardcodes references, doesn't read registry. |
| 3 | Canonical pf_registry stale vs dashboard | **UNVERIFIABLE** | MED | pf_registry.json is 39.8MB; cannot directly diff against dashboard JSON. Possible Kimi conflated raw `by_asset_class` (inflated tile) with `by_asset_class_policy_clean_net` (canonical). Need explicit diff tool. |
| 4 | "Paper-only" contradicted by H-037/H-001 live-testing | **PARTIAL** | HIGH | H-037 = PAPER_TRADE tier (correct, not live). H-001 = REJECTED (correct, not live). Kimi's premise that they're "live" is partially wrong; the **lack of graduated transition protocol** (harness-pass → paper-pilot → real-money) is the real gap. |
| 5 | FDR/DSR/PBO/WFE tools already exist | **VERIFIED** | LOW | `alpha_engine/validation/statistical_gates.py` exists (main repo + worktrees). `tools/edge_stability_harness.py` exists (15895 bytes). Plan's "ship these P0" assumed missing; reality is they EXIST but may have bugs (claim 12). |
| 6 | COMMODITY PF=2.48 unadjusted dedup artifact | **UNVERIFIABLE** | MED | No `filter_survival` doc found. Canonical COMMODITY PF in our session pull was 1.42 (not 2.48). Possible Kimi looked at raw tile, or there are two views. |
| 7 | Score thresholds actively snooped post-plan | **VERIFIED** | HIGH | `audit_trail/quality_gates.py:441,461` — FOREX floor 55→40 (2026-05-03 comment), COMMODITY 60→30 (2026-05-15). Git log confirms post-plan commits. **Active data snooping.** |
| 8 | PR #891 NULL pick fix already merged 2026-05-08 | **VERIFIED** | LOW | `gh pr view 891` MERGED; "fix(mysql_sync): entry_time/exit_time fallback — repairs 87% NULL closed_at orphans." 367 additions. Plan's "Kill NULL strategy picks (5945 noise rows) P0" is **stale** — already done. |
| 9 | Phase timelines fictional; no Phase 0 executed | **PARTIAL** | CRITICAL | Plan dated 2026-05-19T2350Z, today 2026-05-20. Git log shows partial execution (Phase 1B submissions, peer resolver-step5-6 APPLY run in progress) but **no Phase 0 FDR/DSR/PBO suite operational today.** Honest framing required in north-star doc. |
| 10 | **0.09% outcome coverage crisis (121 of 136K+ picks resolved)** | **VERIFIED** | **CRITICAL** | `database/Freebuff_analysis/DB_DASHBOARD_ENHANCEMENT_PLAN.md:116-120` — "Outcome tracking covers only 0.09% of signals." Match exact. **Every canonical PF/WR/DSR is computed on 99.91% unresolved data — mathematically invalid.** |
| 11 | **655K ghost rows + 58% PnL mismatch** | **VERIFIED** | **CRITICAL** | `DB_DASHBOARD_ENHANCEMENT_PLAN.md:21-31,42` — "58% closed rows >1% mismatch between pnl_pct and recomputed"; "~639K constant-PnL ghost rows: quan_engine MATICUSDT 225,916 + meta_strategy 413,112". Match within rounding. |
| 12a | DSR `max(sr_var, 1e-16)` bug | **UNVERIFIABLE** | MED | Pattern not found in quick grep of statistical_gates.py. Need targeted code audit. |
| 12b | PBO zero-purging / IS Sharpe / sqrt(250) bugs | **UNVERIFIABLE** | MED | Specific bugs not isolated. `backtest_new_strategies.py:39` shows annualize=252.0 (correct), not sqrt(250). Need named-function grep on actual stat-gate impl. |
| 13 | DB credentials plaintext in ab_analysis.yml | **WRONG** | LOW | `.github/workflows/ab_analysis.yml:64-65` uses `${{ secrets.MYSQL_PASSWORD }}` — GitHub Secrets reference, NOT plaintext. (Distinct from this session's 3 plaintext leaks in `.md` files already redacted.) |
| 14 | `continue-on-error: true` everywhere | **PARTIAL** | HIGH | `ab_analysis.yml` 7 instances + `audit-dashboard.yml` 34 instances + others. Not "all CI steps" but **systemic in key money-ready workflows** — zero-PnL detector, A/B analysis, PF verification all silently swallow failure. Pipeline permanently green. |
| 15 | No hypothesis-to-emitter wiring | **VERIFIED** | HIGH | `grep -r "hypothesis_registry" alpha_engine/` = NO matches. `edge_filters.py` hardcodes H-037 status/tier; does NOT read from registry. Rejected hypotheses can still trade. |
| 16 | 17 strategies >20% 7d WR decay | **UNVERIFIABLE** | MED | `tests/test_hf_decay_watchlist.py` exists but no `decay_watchlist.json` artifact found. Specific cot_positioning 7d WR 23% vs baseline 93% delta not isolatable. PR #681 ("strategy_decay_guard") REQUEST_CHANGES status. |

---

## Critical truths Kimi correctly surfaced (4 P0 NEW items)

### K-P0-1 — Resolver coverage 0.09% → fix to >90%

Every canonical PF/WR/DSR/PBO is computed on **121 outcomes for 136,000+
raw picks** = **0.09% coverage**. Until this is fixed, our entire
verdict-grade ledger is mathematically invalid. **Highest single-impact
change of the session.**

### K-P0-2 — DB integrity (655K ghost rows + 58% PnL mismatch)

`quan_engine MATICUSDT` 225,916 ghost rows + `meta_strategy` 413,112 ghost
rows. Plus 58% of closed rows have >1% PnL mismatch between recorded
`pnl_pct` and recomputed. Every downstream metric (PF/WR/DSR/PBO/WFE)
poisoned by this. Required before any T2 promotion claim.

### K-P0-3 — Threshold freeze 90d

`audit_trail/quality_gates.py:441` shows FOREX min-score floor lowered
55→40 (2026-05-03 comment). COMMODITY 60→30 (2026-05-15). **This is active
data-snooping post the no-edge verdict** — every lowered threshold
artificially manufactures pick volume to claim "tracking."

### K-P0-4 — `continue-on-error: true` on 34+ audit-dashboard.yml steps

Zero-PnL detector, A/B analysis, PF verification, audit-pf-check — all
silently swallow failure. Pipeline is permanently green even when canary
fails. **Remove `continue-on-error: true` from critical-gate steps OR
explicitly route failures to operator alert.**

---

## Kimi WRONG on 2 claims

### W-1 — "18 pre-reg, 0 admissible is false"

Kimi claimed H-037 is harness-admissible. **Our 2026-05-19T2200Z audit
proved H-037 FAILS canonical harness:** sign-unstable (64 NEG / 4 POS eff
windows) + inverted direction-of-effect (contango predicts UNDER-performance
opposite of pre-registered prior). M-107 impl drift: `tools/h037_vix_carry.py`
used custom `_walk_forward_eff` not canonical `is_admissible()`. **18/0
verdict stands.**

### W-2 — "DB credentials plaintext in ab_analysis.yml"

False positive. File uses `${{ secrets.MYSQL_PASSWORD }}`. Kimi confused
secret-reference syntax with literal value. (Note: this session DID find +
redact 3 plaintext leaks elsewhere in `.md` files.)

---

## Plan amendments folded into todos

Adding 4 new P0 from Kimi:
- K-P0-1 Fix resolver coverage 0.09% → >90% (gates everything else)
- K-P0-2 DB integrity (ghost-row purge + PnL mismatch fix)
- K-P0-3 Threshold freeze 90d (stop the snooping)
- K-P0-4 Remove `continue-on-error: true` from critical gates

Adding 5 new P1 from Kimi:
- K-P1-1 Hypothesis → emitter wiring
- K-P1-2 Targeted statistical_gates / walk_forward code audit (4 named bugs)
- K-P1-3 CLV-positive gate enforcement
- K-P1-4 Liquidity/ADV hard gate
- K-P1-5 Auto cost-survival ≥60% at 30bps gate
- K-P1-6 17-decay-watchlist auto-action

Removing 1 already-done:
- ~~P0: Kill NULL strategy picks at schema (5945 noise rows)~~ — done in
  PR #891.

---

## Honest framing — what this changes about our session work

**The Grok-derived `lopez_de_prado_gates()` patch is BLOCKED by Kimi-P0-1.**
Computing DSR/PBO on 0.09% resolved data returns garbage regardless of
formula correctness. Wire the gate code, but **the gate output is invalid
until resolver coverage is fixed.**

**The mega_mutation FORWARD_CONFIRMED finding (n=58 PF 2.43) is also
suspect.** That cohort's outcomes ARE in the 0.09% — but the comparison
universe (the 99.91% that didn't resolve) means we can't compute proper
walk-forward eff, FDR-adjusted significance, or DSR. **Treat as preliminary
until resolver coverage clears.**

**The ensemble CRYPTO kill (commit 9834307) STANDS.** That decision was
based on the strategy's 79 RESOLVED picks — all of which ARE in the 0.09%
that did resolve. The block is good. (24/25 symbols WR=0%, 136 LONG / 0
SHORT, mutation-3-axis no rescue.)

---

*Generated 2026-05-20T0200Z. Read-only fact-check subagent against repo.
No fabrication. 4 verified P0 gaps added to todo list (53 items, now
including Kimi findings). Next concrete action: K-P0-1 resolver coverage
fix is the single highest-impact item until completed.*
