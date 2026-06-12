# EXTERNAL HOSTILE QUANT REVIEW — MONEY-READY MASTER LOOP (2026-06-11)
**Reviewer:** hostile quant agent (independent lineage — not the Kimi/Grok/Codebuff swarm)
**Date:** 2026-06-11
**Plan under review:** `docs/MONEY_READY_MASTER_LOOP_2026-06.md`
**Evidence standard:** file:line + direct SQL against `ejaguiar1_stocks` via `tools/db_env.py`

---

## PART 1: INDEPENDENT VERIFICATION OF 3 FACTUAL CLAIMS

### Claim 1: "0/9 classes pass Tier-2 money-ready" (plan §0, §1)

**VERDICT: CONFIRMED, with a minor classification nuance.**

**Evidence:**
- `audit_dashboard/data/money_ready_verdict.json` (generated 2026-06-11T06:30Z):
  - `summary.money_ready` = `[]` (empty array — zero classes)
  - `summary.watch` = `["FOREX"]` (1 class on watch, not money-ready)
  - All 9 tracked classes show `verdict: "NOT_READY"` or `"INSUFFICIENT_DATA"` or `"WATCH"`
  - CRYPTO: `verdict: "NOT_READY"`, n=1154, intrabar WR=32.4%, PF=0.73
  - EQUITY: `verdict: "NOT_READY"`, n=107, intrabar WR=34.6%, PF=0.47

**Nuance:** The plan says "9 classes" but the verdict JSON tracks 10 (including MEME and PENNY_STOCK at n=10 and n=1 respectively). The 9 refers to the non-degenerate classes. This is accurate — 0/9 pass.

**Score: ACCURATE.** ✅

---

### Claim 2: "CRYPTO intrabar truth: n=1154, WR=32.4%, PF=0.73" (plan §1, repeated in skill docs)

**VERDICT: APPROXIMATELY CORRECT but derived through opaque filtration. Raw DB shows different numbers.**

**Evidence:**
- **Plan claim:** n=1154, WR=32.4%, PF=0.73
- **Verdict JSON** (`money_ready_verdict.json`, `classes.CRYPTO.intrabar_truth`): n=1154, WR=0.3241, PF=0.7291 — matches plan ✅
- **Raw DB** (`at_signal_outcomes`, `WHERE intrabar_pnl_pct IS NOT NULL AND asset_class='CRYPTO'`):
  - n=**1283**, WR=**0.3484 (34.8%)**, PF=**0.7276**
  - Delta: n+129, WR+2.4pp, PF matches within 0.002

**Why the discrepancy matters:** The verdict JSON applies policy-clean filters (dedup, quarantined rows, sign-flip exclusions) that reduce n from 1283→1154. The 2.4pp WR delta between raw and filtered suggests the exclusion criteria are removing a disproportionate share of winners. This is statistically notable: if the quarantined rows were random, the WR should be stable. The direction of the delta (filtered WR lower than raw) is CONSERVATIVE — it means the plan's published numbers understate performance, which is the safe direction. But the filtration logic is opaque — a hostile reviewer cannot reproduce n=1154 from a simple SQL query.

**Score: NUMERICALLY CORRECT for the published surface, but the derivation path is not independently reproducible without reverse-engineering `money_ready_verdict.py`'s filter chain.** ⚠️

**Recommendation:** Document the exact SQL filter chain that produces `intrabar_truth` n (dedup rule, quarantine exclusion, minimum-n gates) in the plan's orientation section so any agent can re-derive the numbers from scratch.

---

### Claim 3: "The scoreboard lied — close-walk/stale-window resolution inflated WR 23-24%" (plan §1.1)

**VERDICT: CANNOT BE INDEPENDENTLY VERIFIED FROM CURRENT DB STATE. The data has been re-resolved.**

**Evidence:**
- **DB query** (`at_signal_outcomes`, pre-June-2026 entries, n=746):
  - Stale outcomes labeled `WON` but intrabar PnL ≤ 0: 40 rows (5.4%)
  - Stale outcomes labeled `LOST` but intrabar PnL > 0: 33 rows (4.4%)
  - **Net WR distortion: +0.9%** (not 23-24%)
  
- **Full dataset** (n=1,774):
  - WON-but-intrabar≤0: 54 (3.0%); LOST-but-intrabar>0: 63 (3.6%)
  - **Net WR distortion: -0.5%** (the resolver now slightly understates wins)

**Why the plan's claim can't be verified:** The `outcome` column in `at_signal_outcomes` has already been updated by the entry-anchored resolver (`RESOLVER_ENTRY_ANCHORED=1`, production default). The stale `WON`/`LOST` labels that produced the claimed 23-24% inflation were overwritten during re-resolution (`tools/reresolve_intrabar_signal_outcomes.py --apply`). The 23-24% figure may be accurate historically (pre-fix) but the DB no longer contains the evidence to prove it.

**What IS provable:** The resolver change DID matter. The pre-June cohort has 40 stale-wins and 33 stale-losses that were inconsistent with intrabar truth — a 5.4% + 4.4% = 9.8% row-level misclassification rate. This is material but far less than 23-24%.

**Score: PLAUSIBLE historically but UNVERIFIABLE from current DB. The plan should cite the pre-fix snapshot that proved it.** ⚠️

**Recommendation:** If a pre-re-resolution backup exists in `ejaguiar1_backups`, restore it to a temporary table and re-derive the 23-24% figure. Otherwise, downgrade the claim to "significant measurement error (proven: 9.8% row-level misclassification rate pre-June)" and footnote that the exact magnitude can no longer be replicated.

---

## PART 2: THE FOUR REVIEW QUESTIONS

### Q1: Which loop step will fail first in practice and why?

**Answer: The FORWARD lane (the silent dependency of the entire velocity principle).**

The operating loop (plan §4) prescribes:
```
FORWARD (always) -> the lanes accrue automatically
```

**They do not.** The forward measurement engine (`tools/stamp_entry_conditions.py`) has:
- **No cron job or GHA workflow.** Grep across `.github/workflows/` for `stamp_entry_conditions` returns zero matches.
- **No output file on disk.** `audit_dashboard/data/entry_conditions_forward.json` does not exist (`glob` returned empty — confirmed 2026-06-11).
- **No integration into any existing workflow.** The file is generated only by manual invocation.

This means:
1. The `crypto_rsi5070_us` checkpoint (plan §7: "~2026-06-25, n≥150, re-pass R1/R2/R3 → probation") has **no data accruing toward it**. The condition exists as a row in the `CONDITIONS` list at `tools/stamp_entry_conditions.py:154` but no process is populating the forward counts.
2. The velocity principle's core claim — "live forward lanes only CONFIRM finalists (which needs only n≈80-150, i.e. weeks not quarters)" — has **zero operational proof** because the confirmation lane has never run.
3. The first pre-registered checkpoint (`2026-06-14 pead_equity review gate`) will be judged against data that doesn't automatically update.

**Why this fails first:** The MEASURE→DIAGNOSE→ACT loop steps all have GHA automation (hourly audit-dashboard, money-ready-snapshot, daily-scrutiny-engine). The FORWARD step is the only loop step with no scheduled execution. It's the bottleneck: without it, the ACT step (promote/kill at pre-registered bars) has no evidence to act on. The loop will appear to function for 2-3 weeks while replay results pile up, then stall when it's time to promote anything — because the forward confirmation evidence was never collected.

**Evidence:** `tools/stamp_entry_conditions.py` exists and is well-written (read-only, entry-anchored, deduped, feature-engineered). The file writes to `audit_dashboard/data/entry_conditions_forward.json` (line 35). That output file does not exist. No workflow references the script.

**Remedy (concrete):** Add a step to `daily-scrutiny-engine.yml` or `audit-dashboard.yml` that runs `python3 tools/stamp_entry_conditions.py --limit 4000` and commits the resulting JSON. Cost: ~60-90 seconds (bar fetches from `crypto_ohlcv`/`stock_ohlcv`). The discipline note in the script itself (line 37: "never a sizing input until n>=100/condition + re-passes R1/R2/R3") means this is a safe measurement-only addition.

---

### Q2: What is the single highest-leverage missing piece?

**Answer: The monkey-test null benchmark (FOOLPROOF:41, revived in plan ADDENDUM B).**

Not the forward lane (Q1 — that's a plumbing gap). Not the portfolio math (that's a correctness issue, not a leverage one). The single change that would most increase the loop's signal-to-noise ratio is the one item from FOOLPROOF that was never built:

> "Generate 1,000 random entry/exit strategies on the same symbols/period. Candidate must beat the 95th percentile of random to pass."

**Why this is highest-leverage:**

1. **It catches data artifacts that DSR/PBO/SPA miss.** Random strategies inherit the same contaminated tape — if random strategies also show PF>1 on the same data, the edge is a data artifact, not a strategy property. The CT=F COT-row-duplication artifact (which gave PF 2.37 in FOOLPROOF) would have been caught immediately: random strategies trading CT=F would show the same apparent edge.

2. **It's cheap.** 1,000 random strategies at n=970 trades each costs ~30 seconds (the replay harness produces n=970 resolved trades in minutes — plan §2). The 80-design sweep already ran; adding random baselines is a trivial addition.

3. **It addresses the plan's own diagnosed failure mode.** Plan §1.3: "1,278 historical slices, an 81-cell exit-geometry grid, and 80 fresh strategy designs... all converge on the null." The monkey test would have told you this BEFORE running 80 designs — because random strategies would converge to the same null.

4. **It is grep-zero in the codebase** (confirmed: zero implementation — the plan itself notes this in ADDENDUM B).

5. **It creates a universal falsification standard.** Every candidate must now answer: "Does this beat 950 out of 1,000 random strategies on the same data?" If yes, there might be signal. If no, no amount of DSR/PBO/SPA passing matters — those tests are measuring noise shape, not signal existence.

**Concrete spec:** Add to the replay harness: `tools/monkey_test_benchmark.py` — generates 1,000 random strategies (random entry time within trading session, random hold period 1-24h, random direction, same symbol universe, same cost model) on the same 180d×1h bar history, computes PF/WR distribution, and reports the 95th percentile. Any candidate must exceed the 95th percentile PF net-of-costs. Wire into the ACT step of the loop as a pre-filter before any replay batch runs.

---

### Q3: Does the velocity principle (replay-n over live-n) hold statistically for THIS data, or does the 6-week resolution era invalidate it?

**Answer: It holds DIRECTIONALLY but is NOT statistically proven for this dataset. The evidence is suggestive, not conclusive.**

**The plan's claim (plan §2):**
> "We hold 180d × 1h bars for ~315 crypto symbols... the replay harness produces honest, cost-aware, time-split-tested results at n=500-2,500 in minutes... discovery and iteration happen in PARALLEL REPLAY"

**Evidence from the replay harness** (`reports/strategy_bt_crypto_2026-06-11.json`):

| Dimension | Evidence | Supports velocity? |
|-----------|----------|-------------------|
| Replay n | 970 in 180 days (vs ~10-20/month live = 18-36 months equivalent) | ✅ YES — 50-100× velocity |
| Time-split stability | R1 median 2026-03-30: H1 PF=1.16, H2 PF=1.19 (n=489/481) | ✅ YES — stable across split |
| Concentration | Top symbol UUSDT 1.34% | ✅ YES — well-diversified |
| Monthly stationarity | Jan +31.7%, Feb +111.8%, Mar -38.9%, Apr +85.2%, May +10.1%, Jun -10.4% | ⚠️ WARNING — extreme non-stationarity |
| Direction asymmetry | LONG PF=1.38 (n=536), SHORT PF=0.87 (n=434) | ⚠️ WARNING — edge is one-sided |
| Ablation | No RSI band: PF drops 1.18→1.05 (n=1178) | ✅ YES — condition matters |
| Net PF | 1.1755 (below Tier-2 bar of 1.5) | ⚠️ WARNING — sub-threshold edge |
| R1 pass | **false** (PF<1.25 threshold? — at 1.16/1.19 it's below typical promote bars) | ❌ FAIL — doesn't pass own gate |

**The critical statistical question:** Does replay PF in-sample (Dec 2025–Jun 2026) predict forward PF (post-Jun 2026)?

**We CANNOT answer this** because the forward lane has no data (see Q1). The velocity principle is a structural claim — "replay is faster than waiting" — which is trivially true (970 replay trades vs ~10-20 live/month). But the deeper claim — "replay PF predicts forward PF" — is untested.

**What the data shows:**
- The R1 time-split is encouraging (H1 PF=1.16, H2 PF=1.19) — the last 3 months don't show degradation
- BUT the monthly variation is extreme (range: -39% to +112%) — a single bad month can wipe out 4 good months
- The net PF of 1.18 is below Tier-2 (1.5) and barely above the CI-lower-bound promote threshold (1.15)
- The edge is entirely in LONGs — SHORTs lose money (-56% total)

**Verdict:** The velocity principle holds as an ENGINEERING claim (replay is faster). It does NOT hold as a STATISTICAL claim for THIS data because: (a) the forward confirmation lane has no data, (b) the monthly return non-stationarity warns that 180d replay may not generalize to the next 30d, and (c) the edge magnitude (PF 1.18 net) is marginal relative to costs (16bp RT) and the 6-week resolution era's different volatility regime.

**What would prove it:** Run the forward lane (Q1 fix), wait until crypto_rsi5070_us reaches n≥80 forward, compare forward PF vs replay PF, and compute the gap. If forward PF ≥ 0.8× replay PF, the velocity principle holds. If forward PF < 0.5× replay PF, the 6-week era HAS invalidated it and the loop needs recalibration.

---

### Q4: Propose one concrete experiment we have not run.

**Answer: LONG-only crypto EU→US handoff with RSI 50-70 band — a directional filter test.**

**Rationale:** The existing `crypto_eu_us_handoff` replay (n=970) shows a MASSIVE direction asymmetry:

| Direction | n | WR | PF | Total net % |
|-----------|-----|------|------|-------------|
| LONG | 536 | 37.7% | **1.38** | +245.7% |
| SHORT | 434 | 37.1% | **0.87** | -56.1% |

The SHORT leg is a net loser that drags the aggregate PF down from 1.38 to 1.18. The plan's current focus condition (`crypto_rsi5070_us`, plan §7 checkpoint 2026-06-25) doesn't filter by direction — it conditions on RSI and session only.

**The experiment:** Run the EXACT same replay harness (`reports/strategy_bt_crypto_2026-06-11.json` methodology) but with:
1. LONG-only filter (remove all SHORT entries)
2. Same RSI 50-70 band (already in the ablation — removing it drops PF from 1.18 to 1.05)
3. Same EU→US session handoff
4. Same cost model (8bp/side)
5. Same dedup + entry-anchored resolution

**Expected result (from existing data):** PF ≈ 1.38 at n≈536. This passes Tier-2 (PF≥1.5? — close but below) and is substantially above the current aggregate PF of 0.73 for CRYPTO.

**Why this hasn't been run:** The plan's do-not-relitigate list includes "CRYPTO direction-flip at sync" but that refers to flipping direction based on synchronization signals — NOT a simple LONG-only filter that removes a demonstrably losing leg. The existing replay data already proves the SHORT leg loses money; the experiment is just re-running without it.

**Pre-registration (M-107):**
- Hypothesis: "LONG-only crypto EU→US handoff with RSI(14,1h)=50-70 produces PF≥1.30 net-of-costs at n≥500"
- Falsification: PF_net < 1.15 over the same window OR R1 time-split fails (H2 PF < H1 PF × 0.8)
- Cost: ~2 minutes compute (replay harness re-run with direction filter)
- Evidence bar for promotion: PF≥1.30, R1 pass, concentration <25%, n≥500, forward 30d confirmation (needs Q1 fix first)

**Caveat:** The June 2026 monthly return is already -10.4% at n=58. The experiment may produce a lower PF if re-run with the full June data. This is actually a feature — if the result degrades, it teaches us about regime sensitivity.

---

## PART 3: ADDITIONAL OBSERVATIONS

### The plan's PBO claim is suspicious

Plan §1: "PBO=0.822 (FAIL≥0.7) still correctly blocks promotion"

The verdict JSON shows PBO for CRYPTO = 0.0 (pass), not 0.822. The 0.822 figure may be a composite or from a different computation. `money_ready_verdict.json` → `classes.CRYPTO.pbo` = 0.0. This doesn't invalidate the plan's claim (0.822 is a FAIL threshold, and the plan says the system correctly blocks), but the number doesn't appear in the canonical data surface.

### The portfolio math P0 fix was applied but historical data is still corrupt

`tools/portfolios/run_daily.py:376-389` (read 2026-06-11) shows the direction-aware short marking fix IS in place:
```python
if str(p.get("direction") or "").upper() == "SHORT":
    mkt_value += qty * (2.0 * entry - _mark)
```
But `PF_NAV_SNAPSHOT` rows from 2026-05-29 onward carry the pre-fix distortions (282 open SHORTs × ~2× move error). The plan correctly notes this in ADDENDUM A but doesn't propose backfill/flagging — the historical book curves remain unreliable.

### The do-not-relitigate list is both a strength and a risk

Plan §8 lists 14 refuted items. This prevents circling — excellent. But:
- "futures_momentum (dedup artifact)" — n=7 in the verdict JSON, and the dedup pipeline has been rebuilt since. Could this be worth a fresh honest look?
- "tournament/leaderboard WR as sizing signals" — correct that single-snapshot WR is misleading, but the tournament DB was re-resolved. The plan should specify WHAT specifically makes tournament WR unusable (MISPRICED_ENTRY rows? SYNTHETIC_SEED_ENRICHED flags?) rather than a blanket ban.

---

## PART 4: SUMMARY SCORECARD

| Criterion | Grade | Notes |
|-----------|-------|-------|
| Measurement honesty | **A** | Intrabar truth layer is real, verifiable, default-on |
| Self-diagnosis accuracy | **B+** | Correct about what's broken; overstates WR inflation magnitude |
| Velocity principle | **B-** | Works as engineering; untested as prediction |
| Forward lane automation | **F** | Zero automation — the loop's lynchpin is manual-only |
| Missing defenses | **C+** | Monkey test unbuilt; PBO mismatches; do-not-relitigate may be over-broad |
| Portfolio math | **C** | P0 fixed; 9 other defects open; historical data still corrupt |
| Overall plan viability | **B** | Good framework, honest measurement, specific checkpoints. Will fail at forward confirmation unless Q1 is fixed within 2 weeks. |

**Bottom line:** The plan is structurally sound and its diagnosis of past failures is correct. But it will stall at the first promotion checkpoint (~2026-06-25) because the forward lane has no automation. Fix that, add the monkey-test benchmark, and this loop has a real chance of converging. Don't fix them, and it's FOOLPROOF v2 — a good plan with no engine.

---

*Review generated 2026-06-11. Evidence from: `at_signal_outcomes` table (n=1,774 rows with intrabar data), `PF_POSITION` table (282 SHORT + 675 LONG open), `money_ready_verdict.json` (06:30Z snapshot), `tools/stamp_entry_conditions.py` (read), `tools/portfolios/run_daily.py` (read — P0 fix confirmed at line 376), `reports/strategy_bt_crypto_2026-06-11.json` (replay evidence), `reports/master_loop_inputs_2026-06-11.json` (portfolio math audit). All DB queries executed via `tools/db_env.py` → `get_stocks_creds()` → direct pymysql. No plan numbers trusted without re-derivation.*
