# Cotton (CT=F) Kill-vs-Revive Autopsy — 2026-05-15

## Purpose

PR #1060 surfaced that CT=F (cotton) is in `COMMODITY_BLACKLIST` — contradicting a 5-AI consensus that called cotton the real-money pilot. This document provides the supporting data + methodology behind the blacklist claim, and resolves the n=12-vs-n=41 paradox. It then defines a reproducible revive/keep decision procedure and submits the logic for multi-engine review.

## Claim under examination

> "CT=F (cotton) is deliberately blacklisted and is NOT a real-money candidate."

**Verified TRUE on the blacklist side.** `audit_trail/quality_gates.py:1270` — `COMMODITY_BLACKLIST` frozenset contains `"CT=F"`. Introduced by commit `162d1d8286d` (PR #535, "fix(commodity): kill agro/oil/silver/gold sub-classes (Phase 2-D 7/7 panel)"), authored 2026-04-29 23:43:23 EDT by eltonaguiar. `passes_active_gate()` hard-rejects any pick whose symbol is in `COMMODITY_BLACKLIST` unless env `COMMODITY_SUBCLASS_KILL_DISABLED=1` is set.

The kill justification comment (quality_gates.py:1262):
```
CT=F (cotton) n=12 WR 8.3% sum -8.41% KILL
```

## Methodology

**Source of truth:** `audit_dashboard/data/dashboard_data.json::picks.recent_closed` filtered to `symbol == "CT=F"`. This is the resolver-v2 ledger (trustworthy post the 2026-04-28 `outcome_resolver.py` PNL_WIN_THRESHOLD fix). NOT the 50webs MySQL `at_signal_outcomes` table (0.08% resolution — ghost-infested, untrustworthy).

**Steps:**
1. Extract all CT=F closed picks. Capture: `direction`, `source_system`, `strategy`, `entry_price`, `exit_price`, `pnl_pct`, `status`, `exit_reason`, `timestamp` (entry), `closed_at`.
2. Verify internal consistency: for SHORT picks, a WIN must have `exit_price < entry_price`. Reject the dataset if prices contradict pnl sign.
3. Split picks by entry `timestamp` around the kill commit time (2026-04-29 23:43:23 EDT). PRE-kill = picks the Phase 2-D panel could have seen. POST-kill = picks emitted after the blacklist landed.
4. Compute n / WR / PF / sumPnL for: ALL, PRE-kill, POST-kill, and per source×strategy.
5. Compare PRE-kill computed stats against the blacklist comment's cited stats.
6. Weekly WR/sumPnL timeline to detect regime survivorship.
7. Verdict per the decision rule (below).

## Raw data

**Universe:** 41 CT=F closed picks. 100% SHORT direction. Entry timestamps 2026-04-23 06:50 → 2026-05-14 16:19 UTC (3-week window).

**Internal-consistency check: PASS.** Sampled picks — SHORT win `entry 87.35 → exit 81.08` (pnl +7.18, TP_HIT); SHORT loss `entry 83.33 → exit 86.68` (pnl -4.02, SL_HIT). Exit prices agree with pnl sign + exit_reason. Data is real resolved trades, not placeholders.

### Aggregate stats

| Window | n | W | L | WR | PF | sum PnL |
|---|---|---|---|---|---|---|
| ALL | 41 | 34 | 7 | 82.9% | 7.24 | +147.68% |
| **PRE-kill** (entry < 2026-04-29 23:43) | **12** | 8 | 4 | **66.7%** | **3.50** | **+32.30%** |
| POST-kill (entry ≥ 2026-04-29 23:43) | 29 | 26 | 3 | 89.7% | 11.73 | +115.38% |

### Per source × strategy

| source / strategy | n | W | WR | sum PnL |
|---|---|---|---|---|
| multi_asset_copytrader / cftc_cot_commercial_signal | 22 | 17 | 77.3% | +69.08% |
| multi_asset_cot / cot_positioning | 17 | 15 | 88.2% | +61.70% |
| multi_asset_copytrader / futures_bb_mean_reversion | 2 | 2 | 100.0% | +16.89% |

### Weekly timeline

| Week | n | WR | sum PnL |
|---|---|---|---|
| 2026-04 w4 | 9 | 56% | +17.5% |
| 2026-04 w5 | 5 | 80% | +15.8% |
| 2026-05 w1 | 18 | 100% | +82.3% |
| 2026-05 w2 | 9 | 78% | +32.1% |

## The paradox resolved

The blacklist comment cites **n=12, WR 8.3%, sum -8.41%**. The actual 12 PRE-kill picks (the only 12 picks that existed when the Phase 2-D panel ran on 2026-04-29) resolved to **WR 66.7%, PF 3.50, sum +32.30%**.

The `n=12` matches exactly. **Every performance number is wrong.** WR 8.3% vs 66.7%. Sum -8.41% vs +32.30%.

**Conclusion: the Phase 2-D cotton kill was based on bad data.** The most likely cause: at panel time (2026-04-29 23:43), those 12 picks were freshly opened and still UNRESOLVED. The panel read open positions / pending rows — either marking unresolved picks as losses, or reading the ghost-infested MySQL `at_signal_outcomes` table (0.08% real resolution). The picks subsequently resolved to a 66.7% WIN rate. The kill verdict never saw the real outcomes.

A secondary anomaly: 29 CT=F picks were emitted AFTER the blacklist landed. No `COMMODITY_SUBCLASS_KILL_DISABLED=1` env flag exists in any workflow. This means either (a) the `multi_asset_copytrader` / `multi_asset_cot` emission path bypasses `passes_active_gate()`'s blacklist check, or (b) the blacklist gate has a wiring defect. Separate bug — flagged for follow-up.

## Caveats — why this is NOT an automatic revive

1. **100% directional.** All 41 picks are SHORT cotton. The 3-week window (2026-04-23 → 2026-05-14) was a cotton downtrend (entries clustered 83–90, TP exits clustered ~80). The 82.9% WR may be regime survivorship — if cotton reverses to an uptrend, a SHORT-only strategy bleeds. No LONG cotton picks exist to prove the strategy is direction-agnostic.
2. **n=41 < charter floor (n≥100).** Per CLAUDE.md / PERFORMANCE_CHARTER, no asset class scales up below 100 clean trades. Cotton is 41% of the way there.
3. **Low elite_score.** The 41 picks score `elite_score` 15–51 (the scoring model rated them mediocre, yet they won). Either the scorer is mis-calibrated for COMMODITY, or the wins are luck the model correctly distrusted.
4. **3-week sample.** Insufficient to span a full COT-positioning cycle. COT extremes mean-revert over months.
5. **Source concentration.** `cftc_cot_commercial_signal` + `cot_positioning` are both COT-derived — not independent signals. 39 of 41 picks share the same underlying COT data. Effective independent n is far below 41.

## Decision rule

```
cotton_verdict:
  # Step 1 — was the kill data valid?
  if blacklist_cited_WR within ±10pp of recomputed_PRE_kill_WR:
      kill_data_valid = True
  else:
      kill_data_valid = False   # <-- THIS CASE (8.3% cited vs 66.7% actual)

  # Step 2 — if kill data was invalid, the kill is void but revival is gated
  # n_eff = effective INDEPENDENT sample, NOT raw trade count. Picks sharing a
  # weekly signal source collapse to ~1 independent obs per signal-release.
  if not kill_data_valid:
      if n_eff >= 100 and PF > 1.5 net-of-cost and not single-direction-only:
          verdict = REVIVE_LIVE
      elif n_eff >= 20 and PF > 1.5 and regime_decomposition_passed:
          verdict = REVIVE_SHADOW   # emit, tag, do NOT size; accrue to n_eff>=100
      else:
          verdict = HOLD_KILLED_PENDING_DATA
  else:
      verdict = KILL_STANDS
```

**Applying the rule (revised post swarm review — see Swarm Verdict section):**
kill_data_valid = False (8.3% cited, 66.7% actual — 58pp gap).
raw n = 41 BUT **n_eff ≈ 3-4**: 39/41 picks derive from COT data (`cot_positioning` + `cftc_cot_commercial_signal`); CFTC publishes COT once weekly; the 3-week window yields only ~3-4 independent signal-releases. PF 7.24 on n_eff≈4 is statistically meaningless.
regime_decomposition_passed = unknown (not run — all 41 picks SHORT in one downtrend window).
→ **verdict = HOLD_KILLED_PENDING_DATA.**

The original draft of this autopsy concluded REVIVE_SHADOW using raw n=41. A 3-engine swarm review (DeepSeek high-confidence + Cerebras medium-confidence; xAI failed to return parseable output) flagged the `n>=20` threshold as using the WRONG sample-size metric — raw trade count instead of effective independent observations. Corrected above.

## Recommendation

1. **Do NOT flip `COMMODITY_SUBCLASS_KILL_DISABLED=1` globally** — that revives all 14 blacklisted COMMODITY symbols at once. The Phase 2-D panel killed 7/7 sub-classes with the same flawed methodology; each needs its own autopsy.
2. **Re-run the Phase 2-D panel for CT=F specifically** against the resolver-v2 ledger (not MySQL). If it confirms this autopsy, remove `CT=F` from `COMMODITY_BLACKLIST` and re-add it in **SHADOW mode** — emit picks, tag them, but block sizing until n≥100 clean.
3. **Audit the other 6 Phase 2-D kills** (CL=F, KC=F, SI=F, GC=F, ZC=F, etc.) — `KC=F` (coffee) cites the identical "n=12 WR 8.3%" — suspiciously identical to cotton, suggesting a copy-paste or a systematic resolver bug at panel time.
4. **Fix the gate-bypass bug** — 29 CT=F picks emitted post-blacklist. Determine why `passes_active_gate()`'s `COMMODITY_BLACKLIST` check didn't stop the `multi_asset_*` emission path.
5. **Add a kill-floor rule** to the Phase 2-D protocol: no kill on n<50 clean resolved trades. The cotton kill fired on n=12.
6. **Verify the SHORT-only concern** — pull cotton (CT=F) price history for the window; if it was a clean downtrend, discount the WR for regime survivorship before any sizing.

## Verdict (post swarm review)

**HOLD_KILLED_PENDING_DATA.** The Phase 2-D cotton kill *was* data-flawed (8.3% cited vs 66.7% actual on the same n=12) — that finding stands. But the kill being flawed does NOT make cotton revivable. The raw 41-pick record collapses to **n_eff ≈ 3-4 independent observations** once you account for the shared weekly COT signal source. PF 7.24 on n_eff≈4, all in one 3-week SHORT-only downtrend, is not evidence of edge — it is a small-sample regime artifact.

**Two separate things are both true:**
1. The kill verdict used bad numbers (likely unresolved picks / ghost MySQL). The kill *reasoning* is invalid.
2. Cotton still should NOT trade real money, or even shadow-mode, until: (a) effective-n ≥ 20 by signal-cluster count, (b) regime decomposition shows the SHORT edge survives a non-downtrend window, (c) transaction-cost haircut applied, (d) survivorship check on never-entered SHORT setups.

**Required before ANY revival** (swarm-mandated additions):
- Cluster the 41 picks by COT-release week; recompute WR/PF per independent cluster.
- Pull CT=F spot/continuous price path for 2026-04-23..05-14 — confirm or rule out "pure downtrend = pure luck".
- Friction-adjusted DSR on the clustered series (use PR #1058's `cot_lag_corrector` machinery, FRICTION_RATE=0.0008).
- Out-of-sample test on a different 3-week window if any cotton history predates the sample.

The 5-AI "cotton = real-money pilot" consensus was wrong, and the original draft of this autopsy (REVIVE_SHADOW) was *also* wrong — both over-weighted raw trade count. The kill, the consensus, and the first-draft revival all share one root error: **nobody computed the effective independent sample size.** That is the meta-lesson.

## Swarm Verdict (methodology review, 3-engine)

The decision rule above was submitted to a 3-engine swarm (DeepSeek / xAI / Cerebras) for adversarial review.

| Engine | Verdict | Key point |
|---|---|---|
| DeepSeek | HOLD_KILLED_PENDING_DATA (high confidence) | `n>=20` threshold uses raw count; 39/41 share weekly COT signal → true independent n ≈ 3-4 weeks. PF 7.24 on that sample "highly suspect, likely overfits the 3-week downtrend." |
| Cerebras | HOLD_KILLED (medium confidence) | "Strong short-term win outweighed by lack of independent data, regime risk, and missing cost/risk analyses." |
| xAI | (no parseable output — transport failure) | — |

**2/3 engines independently rejected REVIVE_SHADOW.** Both flagged the same flaw: the decision rule conflated raw n with effective independent n. The methodology was corrected accordingly (Step 2 of the decision rule now uses `n_eff` + a `regime_decomposition_passed` gate). This is the methodology working as intended — the swarm caught a real logical error before it could drive a bad revival.

## Reproducer

```bash
python3 -c "
import json
d = json.load(open('audit_dashboard/data/dashboard_data.json'))
ct = [p for p in d['picks']['recent_closed'] if p.get('symbol')=='CT=F']
KILL='2026-04-29T23:43:23'
pre=[p for p in ct if p.get('timestamp','')<KILL]
def s(ps,l):
    w=[float(p['pnl_pct']) for p in ps if float(p.get('pnl_pct',0) or 0)>0]
    l2=[float(p['pnl_pct']) for p in ps if float(p.get('pnl_pct',0) or 0)<=0]
    print(f'{l}: n={len(ps)} WR={100*len(w)/len(ps):.1f}% PF={sum(w)/abs(sum(l2)):.2f}')
s(ct,'ALL'); s(pre,'PRE-kill 12')
"
```

## Provenance

- Blacklist source: `audit_trail/quality_gates.py:1262-1273`, commit `162d1d8286d` (PR #535)
- Data: `audit_dashboard/data/dashboard_data.json::picks.recent_closed` (resolver-v2)
- Triggered by: PR #1060 (`ideas/cotton-kill-reversal-2026-05-15`, MERGED)
- Memory: `project_cotton_blacklisted_2026_05_15`
- Methodology swarm review: `swarm_runs/cotton-vet-*/` (DeepSeek + Cerebras + xAI), 2026-05-15
