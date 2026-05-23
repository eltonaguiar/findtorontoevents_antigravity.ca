# Session Review — 4-engine swarm consensus — 2026-05-13T00:14Z

**Engines:** groq + cerebras + xai + deepseek
**Input:** `reports/session_transcript_20260513T001430Z.md` +
`reports/session_status_20260513T001430Z.md` +
`reports/session_review_prompt_20260513T001430Z.md`

## Per-question consensus

| Q | groq | cerebras | xai | deepseek | Consensus |
|---|---|---|---|---|---|
| Q1 ordering | NS2-NS1 | NS2-NS1 | NS2-NS1 | NS1-NS6 as-is | **REORDER NS2→NS1 (3/4)** |
| Q2 sub-class split | PREMATURE | PREMATURE | PREMATURE | PREMATURE | **UNANIMOUS PREMATURE** |
| Q3 staging | CLASS | CLASS | CLASS | CLASS | **UNANIMOUS CLASS** |
| Q4 systemic debt | pymysql dep | Dockerfile dep | sidecar dep gap | NONE | **3/4 SYSTEMIC** |
| Q5 timeline | OPTIMISTIC | OPTIMISTIC | OPTIMISTIC | OPTIMISTIC | **UNANIMOUS OPTIMISTIC** |
| Q6 inherited claims | 3 named | 3 named | 3 named | 2 named | **all 4 flag asset_class_health + need more verification** |
| Q7 swarm weighting | ADJUST | ADJUST | ADJUST | ADJUST (0.5x cerebras) | **UNANIMOUS ADJUST** |
| Q8 A6 sample size | NEED_N | NEED_N (≥300d) | NEED_N (≥250d) | NEED_N (≥252d) | **UNANIMOUS NEED_N ≥ ~250d** |

## Cerebras fabrication pattern continues

Cerebras Q4 cited commit SHA `a3f9c2d` for Dockerfile dependency claim.
Q6 cited `d4e7f9b` (risk_factor_stability claim) and `9c2a1e0`
(liquidity_buffer claim). **None of these SHAs exist on main.** Matches
the round-1 hallucinated §2.1/§3.4/§4.2 section refs. Q7 unanimous
ADJUST policy is well-founded.

## Applied revisions

### REV-1 — Add pymysql to alpha_engine/requirements.txt
Q4 systemic-debt fix. Already shipped this commit. Resolves the root
cause of the 5-sidecar pymysql-install patches (`62c323578b1`,
`fd04540cda2`).

### REV-2 — Reorder next-step queue
Was: NS1 (A1 verify) → NS2 (--apply) → NS3 (sub-class) → ...
**Now:** NS2 (--apply stage by CLASS, CRYPTO first) → NS1 (A1 verify) →
NS3-NS6 reranked.
Rationale: 99.78% close rate on EQUITY DRY-RUN is suspicious; surfacing
the actual write behavior with a small CRYPTO batch validates the
verdict logic before relying on A1 outputs that depend on closed_picks.json.

### REV-3 — DROP COMMODITY sub-class split
Q2 unanimous PREMATURE. Defer until A1 verifies multi_asset_cot.
Scope churn risk: shipping the taxonomy split now then refactoring after
A1 verdict would be wasted effort.

### REV-4 — Push real-money timeline to 2026-08-15+
Q5 unanimous OPTIMISTIC. Original 2026-07-15 COMMODITY date assumed
A1+A4+A8 clear on schedule. Push to **2026-08-15 minimum** as the
floor; any slip in A1 pushes by ≥1 month.

### REV-5 — Re-verify inherited claims (Q6 list)
Beyond `asset_class_health.n=0` (already corrigendum'd in `1b86b20a483`),
re-verify before any sizing:
1. `multi_asset_cot` PF=19.93 (gated on A1 — already queued)
2. Money-maker P0 list completeness (audit whether any P0s were based
   on similar field-name mismatches)
3. Cross-asset correlation stability claim (Q6 xai concern; partially
   addressed by A6 audit but only 123d sample)

### REV-6 — Swarm-engine weighting policy
Per Q7 unanimous + cerebras fabrication pattern across two rounds:
- **Cerebras consensus weight: 0.5×** (down from 1×)
- **P0 elevation requires ≥ 2 engine corroboration** (not 1)
- **Cite-and-grep verification before acting on any engine-cited SHA / line / file ref**

To be enforced going forward in any `tools/swarm/swarm_run.py` consumer
script that aggregates verdicts.

### REV-7 — Gate A6 finding on n_obs ≥ 252
Q8 unanimous. Current correlation_regime sidecar runs on 123 daily obs.
Either:
- Wait for natural accumulation to 252 (~4 more months)
- Backfill yfinance lookback to 500d (extends sample without waiting)
The latter is the practical fix; one-line config change to
`tools/correlation_regime_sidecar.py` (`--lookback-days 500` default).

## What survives unchanged

- A3 per-strategy concentration extension (Q2-adjacent but Q2 was
  specifically about sub-class TAXONOMY split, not per-strategy
  rollup which IS shipped + valuable)
- A5 UI WARN badge (already shipped + visible in /audit)
- A6 audit (caveats now noted via Q8 — finding stands but with
  n_obs caveat)
- A8 DSR gate enforcement
- 19/23 commit table (only NS3 sub-class deferred; everything else holds)

## Net effect

Most disruptive finding: **A6 "CT=F independent" interpretation is
sample-thin.** 123 days is below the rule-of-thumb 252-trading-day
floor. Sizing decisions cannot lean on the diversifier claim without
either a longer sample or accepting larger error bars in the cap-and-trade
allocation framework.

Most actionable finding: **REV-2 reorder** — flip `active_picks_sync`
class-by-class BEFORE waiting on A1 cron output. Confirms the writer
behavior first; A1 verdict is downstream consumer.

Most preventive finding: **REV-1 pymysql in canonical reqs** — closes
the dependency gap that allowed 5 sidecars to silently no-op for 24h+.
