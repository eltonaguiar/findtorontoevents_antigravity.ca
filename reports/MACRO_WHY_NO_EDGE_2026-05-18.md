# Macro Synthesis — Why This System Has No Money-Ready Edge — 2026-05-18

**Scope:** synthesis of every report/update from 2026-05-04 → 2026-05-18 plus the
2026-05-18 edge-hunt corpus (EDGE_VERDICT, EDGE_HUNT_EXHAUSTED, EDGE_HUNT_CONCLUSION,
COHORT_HARNESS_VERDICT, DEEP_DIVE_MONEYREADY, PER_CLASS_CANDIDATE_TRADES,
MAGIC_FILTER_HUNT, EDGE_HARVEST, BURIED_WINNER_HUNT, HARNESS_GATES_AND_REGIME,
ROADMAP_TO_EDGE, EQUITY_VERDICT_FINAL, CORRECTED_GAMEPLAN, hypothesis_registry.json).

**Question answered:** at the macro level, *why* does this system have no
money-ready, profitable picks per asset class — not "11 hypotheses failed" (that
is the symptom), but the root cause.

---

## 1. The macro root cause(s)

"11 hypotheses failed" is the box score. The macro causes underneath, ranked by
how load-bearing they are:

### Root cause #1 — The system measures the wrong signal space at the wrong resolution.

Every tested signal — pipeline scores, COT, funding rate, roll-yield, 2s10s,
PEAD, on-chain z-scores, options skew, exchange net-flow — is a
**price/volume-derived or slow-published technical, resolved on daily/settlement
bars, applied to a small correlated basket.** Every one of the 11 kills dies one
of two identical ways (often both):

1. **eff sign-instability across walk-forward windows** — in-sample the signal
   separates winners from losers; out-of-sample the sign flips regime to regime.
   This is the harness's exact test for "real edge vs regime noise," and 11/11
   fail it.
2. **gross edge thinner than cost** — where a signal does produce gross edge it
   is 1–9 bps, below the ~30 bps crypto round-trip. Net edge is negative.

This is **structural, not bad luck**. The recurring `next_step` thread in the
hypothesis registry is the same sentence repeated: *"daily residual is
post-arbitrage noise — needs intraday resolution."* The free-data, daily-bar,
retail-accessible signal space is **empirically empty in this universe**. By
the time a daily bar prints, the information has been arbitraged out. The system
is sampling a space that genuinely does not contain durable edge at retail
latency/cost.

### Root cause #2 — The system measures rather than predicts; it harvests noise, not signal.

The 8,400-pick ledger is an *accumulation of emitter output*, not a designed
experiment. The dominant emitters (`quan_engine_scalp` n≈1,793 PF 0.0,
`ml_enhanced` 149 variants, `cot_positioning`, `claude_gainer_st` n=790 WR 26.5%)
were never causal hypotheses — they are pattern-mined or LLM-narrated picks.
Re-running an edge hunt on this ledger is data-dredging over noise: as
EDGE_VERDICT puts it, "re-testing more features on a ledger that is itself noise
is low-EV." The system was built to *log and score* picks, not to *predict and
falsify* — so the artifact it produces (the ledger) cannot be mined into edge.

### Root cause #3 — Pervasive data-quality corruption manufactures fake positives, which is *worse* than having no edge.

The session is littered with retracted "edges" that were data artifacts:

- **Duplicate re-emissions** — 4,830 of 14,700 raw rows are the same
  symbol/direction firing repeatedly within seconds. Inflates trade count,
  craters PF, and every swarm engine independently named this the #1 corrupt
  cohort. 83% of raw rows are dropped to reach a clean ledger (4,830 dup +
  ~4,763 policy-excluded).
- **Corrupted `confidence` field** — 146 CRYPTO rows hold values 15–78 in a
  field whose domain is 0–1 (percent-as-integer leak). *Any* confidence-based
  filter manufactures a fake positive — this poisoned the Hermes "RR≥1.5 +
  conf≥0.65 → 48.9% WR" filter.
- **Placeholder-stat artifacts** — `ml_enhanced_*` family shows PF 41–999 from
  near-zero `avg_loss` inflating the mean; SPA/DSR cannot detect it.
- **COT look-ahead leakage** — `cot_positioning` PF 4.64 / DSR 1.0 / SPA-pass is
  85% CT=F (cotton); ex-CT=F it is n=20, WR 30%, PF 0.51. CFTC data used before
  it was publicly available.
- **Single-symbol / single-pair concentration** — FOREX "PF 52" is one USDJPY
  pair; `cta_replicator` is 86% USDJPY.

This matters at the macro level: the corruption doesn't just hide edge, it
**produces convincing false edge** that passes PF/DSR/SPA/White's tests. Six of
the seven (and now 11) candidates were fake-positives caught in analysis. The
real value the system has produced is the *kill-loop that catches them* — not a
strategy.

### Root cause #4 — Non-crypto pick volume is too thin to ever form a verdict.

CRYPTO is the only class with enough clean, deduped, resolved picks (~1,900–6,300
depending on view) to even run the 5-window walk-forward harness. Every other
class is sample-starved: EQUITY n=31–33, COMMODITY n=47–173 (and ~85% is the
CT=F leakage cohort), FUTURES n=12, BOND n=1, ETF n≈105. You cannot filter a
profitable set out of a near-empty bucket. The upstream cause is partly
**non-crypto forward resolution** (picks emitted but slow to resolve to
WON/LOST) and partly a **traded universe of only ~12 actively-traded symbols**.
Note an unresolved sub-debate here (see §5): EQUITY_VERDICT_FINAL says the
resolver is *not* broken and n=33 is correct; PER_CLASS_CANDIDATE_TRADES says
resolution is broken. Either way, the classes are too thin to verdict.

### Root cause #5 — No causal hypothesis discipline until very late; the harness kills regime-dependent edge.

Until M-107, signals were tested without a pre-registered economic mechanism —
data-dredging. The corrected discipline (causal hypothesis BEFORE data) only
arrived in the last week. Separately, the harness's sign-stability rule
(≥3/5 windows same sign) **kills any regime-dependent edge** — and most real
edge is regime-dependent. The regime-conditional harness that would fairly judge
such signals is not yet shipped and the regime backfill is too thin (3 of 8,421
picks carry resolve-date regime; the snapshot backfill tags old picks with
today's regime).

**Bottom line:** the edge does not exist *and* does not get found because the
system samples an arbitraged-away signal space at too-coarse a resolution, on a
corruption-ridden ledger that manufactures fake positives, with non-crypto
volume too thin to verdict — and only recently adopted the causal discipline
that would prevent re-dredging.

---

## 2. Tried-and-killed vs never-genuinely-tried

### Definitively tried and KILLED (the 11-entry kill log)

| # | asset | family | failure mode |
|---|-------|--------|--------------|
| 1 | COMMODITY | COT positioning | look-ahead leakage; CT=F-concentrated |
| 2 | CRYPTO | funding-rate z-score directional | sign-unstable 4+/4− on deep archive |
| 3 | COMMODITY | front/second roll-yield | sign-split 4+/2− |
| 4 | BOND | 2s10s yield-curve momentum | sign-split 144+/182− (57k records) |
| 5 | EQUITY | PEAD 30-day drift | sign-split 3+/2− |
| 6 | CRYPTO | funding-arb delta-neutral carry | cost-survival 5.7% (≪60%) |
| 7 | EQUITY/ETF | options-flow put/call + skew + VIX | sign-split all 3 sub-signals + cost |
| 8 | CRYPTO | on-chain address/tx/stablecoin z | sign-split all 3 + cost |
| 9 | CRYPTO | funding-settlement liquidation cascade | sign-split + 1.3 bps ≪ 30 bps cost |
| 10 | CRYPTO | exchange net-flow full-book | sign-split 11+/1− + 3.4 bps ≪ cost |
| 11 | CRYPTO | cross-exchange Coinbase premium | sign-split 23+/22− + 9.3 bps ≪ cost |

Plus: all 7 pipeline scores (`elite_score` eff 0.06, `method_a_score` inverts,
`forward_wr` random walk), `ml_enhanced` 149 variants (placeholder artifact),
3 qlib factors (`pv_corr30`, `vol_ratio`, `realized_vol30` — clean-universe
backtest), and the `risk_reward` R:R band (confound, n=17 after leakage strip).
The data excuses were eliminated, not worked around — H-006 got 6 years of
funding history, H-008 got 496 windows, H-010 got 242 names. Even PEAD, the
most OOS-robust anomaly in academic literature, failed identically.

### NEVER genuinely tried (the honest gaps)

1. **Genuine intraday / tick-level resolution.** *Every* kill's `next_step`
   points here ("daily residual is post-arbitrage noise"). All 11 were resolved
   on daily/settlement bars. This is the only axis with an *untested rationale* —
   and it requires paid L2 tick data (~$300–500 one-time, Tardis.dev) for
   C-1 order-book imbalance reversion.
2. **C-2 exchange net-flow cross-sectional *spread*** (market-neutral, long
   biggest-outflow / short biggest-inflow). H-019/H-020 tested net-flow
   *directionally* and absolute; the cross-sectional spread that cancels crypto
   beta — the structural fix for the beta-domination defect behind 9 kills — has
   not been built.
3. **Regime-conditional admissibility.** The harness mode that would judge a
   regime-dependent signal *within* a regime is designed but not shipped; the
   regime backfill is too thin to run it.
4. **Ensemble / portfolio construction.** Every test was a single hero-signal
   hunt. Hundreds of weak, partially-correlated signals with Bayesian shrinkage
   + portfolio optimization (how real funds operate) has never been attempted.
5. **Execution / structure alpha** (market-making, basis capture, funding-arb
   where you are *paid* to provide liquidity/carry) — a different system, never
   built.
6. **A clean, designed pick ledger.** Every analysis has been retrospective on a
   noise ledger. A forward, pre-registered, deduped, properly-resolved emission
   stream of one causal strategy has not been run to a verdict.

---

## 3. Top-5 highest-leverage fixes (ranked)

Ranked by how much each would change the *odds of finding edge* — not by effort.

1. **Fix the data layer at the writer — duplicate re-emission dedup + 60-day
   clean backfill + REST reconciliation.** 83% of raw rows are dropped to reach
   clean; the dedup is papered over downstream, not fixed upstream. Every swarm
   engine independently named this the #1 move. Until the ledger is *certified*,
   every harness verdict and every "edge" is suspect — and the system keeps
   manufacturing fake positives. Highest leverage because it is a precondition
   for everything else being trustworthy. Also: clamp/reject `confidence` >1.0
   at ingestion (146 corrupt rows) and widen `edge_stability_harness.py:35` to
   read all 32 pf_registry source files, not 1.

2. **Acquire a genuinely new input class at a materially finer resolution —
   paid L2 tick data — and test C-1 order-book imbalance reversion + C-2
   net-flow cross-sectional spread.** This is the *only* axis with an untested
   rationale. New inputs into the *same* daily-bar single-signal hunt = an 8th
   overfitting trap (both AI reviewers said so). New inputs at *tick resolution*,
   pre-registered, is the one move that adds information the system has never
   seen. The C-2 spread also structurally repairs the beta-domination defect.

3. **Ship regime-conditional admissibility + a per-resolve-date regime
   backfill.** The current harness kills regime-dependent edge by construction,
   and most real edge is regime-dependent. This widens what the harness *can*
   admit without lowering the bar — but it is only meaningful once the regime
   backfill is per-date (today it is a single snapshot; 3/8,421 picks carry true
   resolve-date regime).

4. **Make the dashboard tell the truth — default to `pf_registry.json`
   canonical view.** The /audit "Money Ready / High Conviction / Smart Picks"
   tabs imply an edge that does not exist, because `asset_class_health` /
   `hf_stats` / `by_asset_class` recompute on the un-deduped ledger
   (`AUDIT_HEALTH_SOURCE` defaults to legacy). This is why EQUITY shows WR 53%
   vs canonical 33%. Flipping the source flag (issue #1221) does not find edge,
   but it stops the system from *lying about having it* — which is what burns
   agent-hours re-litigating fake positives.

5. **Run ONE causal-hypothesis strategy forward to a clean verdict — and accept
   the 9th/10th kill as a decision point.** Stop retrospective mining of the
   noise ledger. Pre-register C-2, emit it forward, accrue ≥30 deduped resolved
   picks, harness it. If it passes, it is the first real edge; if it kills, that
   is the honest trigger to declare paper-only. This is leverage because it
   *resolves the strategic fork* instead of perpetuating it.

---

## 4. Honest probability & timeline

**Can this system reach money-ready (PF>1.5, harness-admissible) per asset
class? Realistically: no — not "per asset class."**

- **Per asset class:** ~2–4%. FOREX, FUTURES, BOND are near-unanimously called
  retail-hopeless (spreads + HFT, co-location latency, dealer-dominated coarse
  data). EQUITY and COMMODITY are sample-starved and COMMODITY's only "edge" is
  a leakage artifact. The phrase "money-ready per asset class" should be retired
  as a goal — it is not achievable on shared hosting + free/cheap APIs.

- **One class (CRYPTO) reaching money-ready:** ~5–8%. This is the two
  independent AI reviewers' estimate and it is the honest number. CRYPTO is the
  only class with the volume to ever pass the harness. The path is real but
  narrow: fix the data layer → buy tick data → build C-2 → harness → forward-test.

- **Timeline if pursued:** 3 months minimum to a *verdict* on the first causal
  CRYPTO strategy (Wk 1–2 data fix, Wk 3–4 regime harness, Wk 5–8 build, Wk 9–12
  forward-test). That verdict is more likely a kill than a pass. Money-ready
  (≥10 forward trades, WR≥50, PF≥1.3 net-of-cost, capacity-aware) would be 6+
  months out *if* the Wk 9–12 forward test passes — and the base rate after
  11 straight kills says it probably won't.

**The honest default posture, stated plainly:** this is a research sandbox, not
a money-maker. Real capital stays at $0 until the harness passes something. That
is not failure — **11 kills before real money is the system working as
designed.** The realistic outcome is paper-only; the 5–8% CRYPTO path is worth
*one* honest 3-month attempt, after which a 9th/10th kill is the decision point
to stop.

---

## 5. Contradictions / unresolved debates across the 2 weeks of docs

The reports do **not** all agree. The disagreements are material:

1. **Is `risk_reward` admissible?** `HARNESS_GATES_AND_REGIME` (codebuff,
   05-18): "`risk_reward` ✅ ADMISSIBLE — the only score that should gate
   picks." `EDGE_VERDICT` / `EDGE_HUNT_CONCLUSION` (05-18): `risk_reward` is
   kill #2 — "confound; n=17 after leakage strip; sign-flips every window." The
   regime-conditional table in the *same* HARNESS_GATES doc then shows
   `risk_reward` REJECTED (mixed sign). **Unresolved** — the global-harness pass
   and the leakage-controlled kill cannot both be right. The leakage-controlled
   verdict is almost certainly the correct one; the global pass did not strip
   the COT/CT=F confound.

2. **Are COT COMMODITY strategies real edge or a leakage artifact?**
   `HARNESS_GATES_AND_REGIME`: "COT signals (COMMODITY) are the only defensible
   profits — PF>4, n>130, multi-symbol, economic rationale … these are real …
   should be unblocked as Tier-1." `EDGE_VERDICT` / `DEEP_DIVE_MONEYREADY` /
   `MAGIC_FILTER_HUNT`: COT is kill #1 — 85% CT=F, look-ahead leakage, M-095
   block; strip CT=F → PF 0.23. **Directly contradictory.** The leakage finding
   (CFTC data used before publication + single-symbol concentration) is the
   better-evidenced one; HARNESS_GATES's "unblock COT" recommendation is
   dangerous and should be treated as superseded.

3. **Is the non-crypto forward resolver broken?** `PER_CLASS_CANDIDATE_TRADES` /
   `DEEP_DIVE_MONEYREADY` / `HARNESS_GATES`: "non-crypto forward resolution is
   broken (FOREX/EQUITY ~0% resolved) — UNCLAIMED P0." `EQUITY_VERDICT_FINAL`
   (explicitly closing the investigation): the resolver is **NOT broken** —
   fixed in outcome_resolver.py v2/v2.1/v2.2; the low non-crypto WR is the
   resolver *correctly* classifying weak picks. **Unresolved** — EQUITY_VERDICT
   is the later, more specific doc and claims to supersede, but other 05-18
   docs still cite "broken resolver" as a live P0.

4. **CRYPTO PF — which number?** 1.18 (MAGIC_FILTER, n=1662) vs 1.25
   (DEEP_DIVE/EDGE_VERDICT, n=1949) vs 1.28 (CORRECTED_GAMEPLAN, n=1942) vs 0.88
   (ROADMAP/EQUITY_VERDICT `by_asset_class`, n=6353). All claim to read
   `pf_registry.json`. The spread comes from different views (`by_asset_class`
   vs `policy_clean_net` vs strategy-rollup) and different generation timestamps
   the same day. **Not contradictory in verdict** (all sub-1.5, all "no edge"),
   but it shows the canonical source is not yet truly canonical — pick counts
   swing 1,662→6,353 for "the same" class.

5. **Money-ready threshold drift.** CORRECTED_GAMEPLAN uses PF≥1.6; ROADMAP uses
   PF≥1.3 net (Phase 4 gate); DEEP_DIVE uses PF≥1.3; the prompt here uses PF>1.5.
   The bar itself is not pinned across docs.

6. **"mega_mutation is a marginal YES" vs "0 admissible."** `MAGIC_FILTER_HUNT`
   surfaces `mega_mutation` (n=72, PF 2.19, well-distributed) as the *one* slice
   surviving all artifact/concentration screens — a "marginal YES, size small
   and monitor." `COHORT_HARNESS_VERDICT` / `EDGE_VERDICT`: 0 admissible,
   nothing passes. These are reconcilable (n=72 ≈ 1 walk-forward window, so it
   is in-sample-profitable but harness-*untestable*, not harness-*passing*) —
   but the docs use "YES" and "0 admissible" without flagging that they are
   answering different questions, which invites mis-citation.

**Pattern across all six:** the contradictions are not random — they trace to
one root issue. Docs that read the **un-deduped / global / single-file** view
(`HARNESS_GATES`, the inflated EQUITY 53%, the Hermes filter) find "edge"; docs
that read the **deduped, leakage-controlled, policy-clean** view find none. This
is itself evidence for root cause #3: the data corruption is so pervasive that
two honest agents reading "the same" ledger reach opposite verdicts. Until the
data layer is certified (fix #1), this contradiction will keep regenerating.

---

*Synthesis only — no production files edited. Sources: all reports/ and updates/
docs 2026-05-04→18, principally the 2026-05-18 edge-hunt corpus listed in scope.*
