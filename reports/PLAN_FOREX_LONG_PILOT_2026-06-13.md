# PLAN — FOREX `non_crypto_consensus` LONG forward-paper pilot

**Status: DRAFT for peer review (5–20 AI models). Author: claude-fable, 2026-06-13.**
**Decision sought: how (and whether) to wire a forward-paper pilot for the validated FOREX-LONG edge without disrupting production or the operator's other agents.**

## 1. The validated edge (recap, all DB-verified, reproducible)

`source_system = non_crypto_consensus`, category FOREX, direction LONG, on `ejaguiar1_stocks.trading_picks` (2026+, resolved, deduped per symbol-day, 5bp percent win-threshold):

- **n = 129, PF 3.13, IS-half 4.82 / OOS-half 2.05, decisive WR 73%.**
- Parent FOREX (both directions): n=304, PF 1.96, IS 1.91 / OOS 2.03, decisive WR 62%, outlier-robust (PF 1.97 minus largest winner; 1.96 winsorized ±2%), 0/200 direction-sign mismatches, 46 active trading days.
- Edge is broad-based: USDCAD PF 5.60, EURUSD 2.40, GBPUSD 2.26, AUDUSD 2.09, CADJPY 1.77; the most-traded pair EURJPY is break-even (0.94) — not single-symbol-carried.
- Mechanism: `non_crypto_consensus` only emits when ≥2 independent systems agree on symbol+direction (consensus filter).
- Reproducer: `tools/validate_forex_consensus_edge.py` (PR #587).

**Caveats:** daily first-touch resolver (NOT intrabar — non-crypto rows lack intrabar bars); 2026 cohort (~50 days); single source, single class.

## 2. Pilot specification (proposed)

| Param | Proposed value | Rationale |
|---|---|---|
| Sleeve | `non_crypto_consensus` FOREX **LONG only** | LONG is the powerhouse (PF 3.13 vs SHORT 1.54) |
| Symbol set | **ALL FOREX LONG pairs — no exclusion** (REVISED per peer review) | excluding the 3 break-even pairs post-hoc was flagged as selection bias by ~6/8 reviewers; LONG-all-pairs is already PF 3.13 / n=129, so no exclusion is needed |
| Book | **paper / shadow only** — 0% real capital | Stage-3 WATCH per the bridge; no real money until forward n≥100 |
| Notional (shadow accounting) | 0.5% notional-equivalent per pick | matches `docs/MONEY_READY_MASTER_LOOP` shadow size |
| Position cap | ≤ 5 concurrent open pilot picks | concentration control |
| Circuit breaker | halt new pilot emission if rolling pilot drawdown > **5%** OR cumulative pilot loss > **2% of book** (REVISED — tighter per peer review) | 10% was too loose for a 0.5% sleeve; a last-10-WR breaker was dropped because this strategy is intentionally low-decisive-frequency (177/304 are near-flat TIME_EXITs) so a WR breaker would fire on noise |
| Acceptance (promote to Stage 4) | forward n≥100 AND PF≥1.5 AND decisive WR≥50% post-slippage AND IS/OOS still hold | Tier-2 sized-up gate |
| Kill | forward PF<1.0 after 30 days OR forward n<10 after 30 days | fail-fast |
| Resolver | daily first-touch (current) for the pilot; **intrabar replay required before any real sizing (Stage 4)** | non-crypto intrabar bars are the gap |

## 3. Wiring options (the crux — needs review)

**Option A — pure sidecar tracker (no emission-path change).** A standalone `tools/forex_long_pilot_tracker.py` + daily cron reads `non_crypto_consensus` FOREX LONG picks already emitted into `trading_picks`, tags them into a separate `forex_long_pilot` paper book, marks-to-market, and accrues forward stats. **Touches no production gate/emitter.** Lowest collision risk. Downside: it only observes picks the existing pipeline already emits — doesn't change sizing/priority.

**Option B — gate/score boost in production.** Add a small score or priority boost (or a `high_conviction`-style tag) for `non_crypto_consensus` FOREX LONG in `audit_trail/quality_gates.py` / scoring so these picks surface on the audit dashboard as a tracked pilot sleeve. Touches the production scoring path — **collides with the peer's active CRYPTO-LONG-block / gate work** (config.py / quality_gates.py).

**Option C — emitter sleeve.** Add a dedicated emission sleeve. Highest effort + highest collision risk. Rejected for a pilot.

**Recommendation: Option A** — a pure sidecar tracker. It begins accruing forward, leakage-free, verifiable stats immediately, changes zero production behavior, and avoids the shared-tree emission collisions that have burned this repo repeatedly. Option B only after the operator/peer coordinate on the gate file.

## 4. Open questions for reviewers

1. Is daily first-touch resolution acceptable for a **paper** pilot, or must the intrabar replay land first even for paper? (Non-crypto intrabar bars don't exist yet — building them is a separate, larger task.)
2. Is excluding the 3 break-even pairs **selection bias** that will inflate forward expectations, or legitimate spec-tightening? (They were excluded on full-sample PF, not on a held-out split.)
3. Is n=129 LONG / ~50 days enough to start a paper pilot, or should it wait for more breadth?
4. Single-source/single-class concentration: pilot LONG-only now, or pair it with a second uncorrelated sleeve (e.g. `myfxbook_retail_contrarian` PF 1.74) to diversify the paper book?
5. Slippage/cost model for FX paper marks: what bps round-trip is realistic for these pairs, and does PF survive it? (Headline PF is gross.)
6. Is the consensus mechanism itself at risk of regime decay (it worked in the 2026 cohort — what breaks it)?
7. Should the circuit-breaker thresholds (DD>10%, last-10 WR<35%) be tighter given low-WR/high-PF strategies have lumpy equity curves?

## 5. Non-goals / hard rules

- **No real capital** at any point in this pilot.
- **No edit to the production emission path** without explicit operator + peer coordination (Option A respects this).
- **No promotion to `PROMOTED_STRATEGIES`** until all 5 bridge stages complete.
- Do **not** present the gross PF as net or as forward-proven — it is backtest/historical until the pilot accrues forward n.

## 6. Reviewer instruction

Critique the spec and the wiring recommendation. Specifically: (a) is Option A the right call, (b) are the acceptance/circuit-breaker thresholds sound, (c) what's the single biggest way this pilot could mislead us into a false "winner," and (d) is the break-even-pair exclusion legitimate or selection bias? Be adversarial — assume the edge is a measurement artifact until proven otherwise.

## 7. Peer review — 8-model adversarial panel (2026-06-13) + applied revisions

Fanned this draft to a 13-model panel (LiteLLM proxy + Ollama local); **8 responded** (deepseek-chat-direct, free-mode, paid-mode-large, hybrid-model-large, free-mode-large, free-mode-fast, qwen2.5-7b, + minimax empty). Convergent verdict:

| Question | Panel verdict |
|---|---|
| Option A (sidecar)? | **GO** — 5 GO, 2 "revise spec", 0 NO-GO. Proceed with the no-production-change sidecar. |
| Break-even-pair exclusion? | **SELECTION BIAS** — ~6/8. "Textbook cherry-picking / removes the most challenging cases / masks decay." Only 1 called it legit. |
| Circuit-breaker thresholds? | **Too loose** — 10% DD too loose for a 0.5% sleeve (tighten to 5% / absolute cap); a WR breaker fires prematurely on a lumpy low-WR/high-PF curve. |
| Biggest false-winner risk? | **Regime fragility** (edge is a 2026-only artifact) + the pair-exclusion masking. |
| Insisted improvements | Pre-register full symbol set + acceptance criteria *before* the first pick; **mandate intrabar replay before any real sizing**; consider a regime-robustness check. |

**Revisions applied (this version):**
1. **Dropped the break-even-pair exclusion** → pilot ALL FOREX LONG pairs (§2). LONG-all-pairs is already PF 3.13 / n=129, so nothing is lost and the selection-bias objection is removed.
2. **Tightened the circuit breaker** → 5% rolling DD or 2%-of-book cumulative loss; removed the last-10-WR breaker (would fire on the strategy's many near-flat TIME_EXITs, which are noise, not losses) (§2).
3. **Pre-registration is now mandatory** (below) before the first pilot pick — addresses the bias + regime-fishing concerns.
4. **Intrabar replay reaffirmed as a hard Stage-4 gate** before any real capital (already in §2; reviewers doubled down).

### Pre-registration (M-107 style — required before pilot start)
Register in `reports/hypothesis_registry.json` BEFORE the first pilot pick:
- Hypothesis: `non_crypto_consensus` FOREX LONG (all pairs) sustains PF≥1.5 / decisive WR≥50% forward.
- Frozen symbol set: all FX pairs the source emits LONG (no exclusions).
- Frozen acceptance/kill criteria (§2) and start date.
- This prevents post-hoc symbol-pruning or threshold-shopping from manufacturing a false pass.

**Net decision: GO on Option A (pure sidecar tracker), with the revised spec above.** The sidecar can start accruing pre-registered, leakage-free forward stats with zero production-emission change — which is also the lowest-collision path given the operator's other agents are active in the gate/emitter files.
