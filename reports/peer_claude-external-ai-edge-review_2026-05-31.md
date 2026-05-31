# External Peer-AI Edge Review — 2026-05-31

**Question:** "Do we even have an edge?" (operator framing, given months of work and the
TRUTH LAYER showing 11.13% WR / PF 0.46 raw, 25.28% WR / PF 0.61 on smart-picks).

**Methodology:** Composed a single neutral data packet (RAW vs smart-picks PF/WR,
0/9 classes passing T1/T2 per money_ready_verdict, edge_stability flags including the
small-n STABLE_EDGE on COMMODITY n=178 / EQUITY n=286, decaying CRYPTO+FOREX, the
unverified +313% rolling-100 claim, and today's 4 scoring-path PRs #263/#275/#277/#278).
Sent verbatim to 3 independent external models via their native APIs. **No model was
allowed to claim it "fetched" /audit** — data was injected directly per CLAUDE.md rule.

Each model was asked to (1) state if real edge exists, (2) evaluate the +313% claim,
(3) name one filter most likely to surface true edge, and to terminate with one of
`VERDICT: NO_EDGE | POTENTIAL_EDGE | INCONCLUSIVE`.

---

## Model 1 — xAI Grok (`grok-4-fast-reasoning`)

**Verbatim:**

> **1. No real edge exists.** All core metrics (11% WR / PF 0.46 overall; 25% WR / PF 0.61
> on smart-picks) sit far below breakeven. Zero of nine asset classes clear even Tier-2
> thresholds; the few "STABLE_EDGE" flags rest on n<300 with heavy concentration and
> documented decay in crypto/forex. This is classic noise with negative expectancy, not
> a tradable signal.
>
> **2. The +313% claim is almost certainly spurious.** A rolling-100 window cannot produce
> triple-digit returns when the unconditional PF is 0.46 and the best filtered subset is
> still 0.61. Any such headline requires extreme cherry-picking of start dates, asset
> subsets, or unclosed marks — none of which survive the raw closed-trade ledger.
>
> **3. Most useful single filter:** add a minimum 200-trade look-back per signal source
> with a hard requirement that its own trailing PF > 1.2 and WR > 48%. Everything else
> (score thresholds, recency, etc.) has already failed to move the needle.
>
> VERDICT: NO_EDGE

**Classification:** `CONFIRMS_NO_EDGE`

---

## Model 2 — Alibaba Qwen-Plus (DashScope intl)

**Verbatim:**

> No. The raw 11.13% win rate and PF 0.46 are statistically indistinguishable from noise —
> especially with tens of thousands of picks. A PF < 1 means systematic loss; WR < 35%
> with negative expectancy implies no robust edge. Smart-picks (25.28% WR, PF 0.61)
> improve only marginally — still deeply unprofitable. Zero asset classes meet even
> Tier 2 thresholds; CRYPTO's PF 1.14/WR 43% is borderline but decaying rapidly
> (78.9% → 38% in 14 days), and its 0 closed trades in 48h vs 322 active signals severe
> latency or execution failure — not edge. ETF's PF 11.99 is meaningless on n=2.
> COMMODITY's 11% WR and 57% CT=F concentration confirm overfitting. STABLE_EDGE flags
> on tiny samples (n=178, n=286) lack statistical power — no p-value, no out-of-sample
> validation, no walk-forward testing reported. The "+313% rolling 100" claim is almost
> certainly cherry-picked: it contradicts the full-sample reality and lacks time-stamp
> provenance, window justification, or risk-adjusted metrics (Sharpe, max DD). With no
> position sizing, slippage, or commission modeling shown, it's a vanity metric. The four
> merged PRs won't fix structural flaws — they're code-correct but likely operating on
> flawed signal logic or unvalidated features. To surface real edge, add *mandatory
> minimum hold-time filtering* (e.g., ≥24h for crypto, ≥3d for equities) to kill
> latency-driven false positives and expose whether signals persist beyond microstructure
> noise. Without that, you're optimizing for quote-tick hallucinations — not market
> structure.
>
> VERDICT: NO_EDGE

**Classification:** `CONFIRMS_NO_EDGE`

---

## Model 3 — Xiaomi MiMo v2.5-Pro

**Verbatim:**

> # Independent Quant Review — Blunt Assessment
>
> ## 1. Do You Have an Edge?
>
> **No.** The data screams no-edge across the board.
>
> PF 0.46 means for every $1 risked, you return $0.46. That's not a strategy — it's a
> donation to the market. The "smart-picks" filter improving PF to 0.61 is still
> catastrophic; you need PF >1.0 *after* costs just to break even. Zero asset classes
> pass any reasonable tier. CRYPTO (PF 1.14, n=728) is the *best* candidate, but:
> - PF 1.14 is within noise bands for that sample size
> - It's actively **decaying** (78.9% → 38% WR)
> - After slippage/commissions, it's almost certainly net negative
>
> ## 2. The +313% Claim
>
> **Almost certainly a window artifact.** With tens of thousands of picks at PF 0.46,
> the variance distribution has fat tails. A rolling 100-pick window *will* produce
> outlier positive clusters — that's basic probability, not edge. Ask for: (a) the
> *median* rolling 100-pick return, (b) how many windows are negative, (c) the full
> distribution. If the operator can't produce these immediately, the claim is decorative,
> not analytical.
>
> ## 3. Best Single Filter Addition
>
> **Regime/volatility gate.** The most common scenario in datasets like this: signals work
> in trending/volatile regimes and bleed in mean-reverting chop. Add a simple ADX>25 or
> realized-volatility percentile filter and re-run the backtest. This frequently converts
> a PF 0.5 system to PF 1.2+ — or confirms nothing survives.
>
> ## Bottom Line
>
> Months of work on a system returning 46 cents per dollar risked. The four new PRs won't
> rescue this without a fundamental rethink. Kill the headline claim, stop production
> trading, and do proper regime-conditioned analysis before deploying capital.
>
> **VERDICT: NO_EDGE**

**Classification:** `CONFIRMS_NO_EDGE`

---

## Aggregate Consensus

| Model | Verdict |
|---|---|
| xAI Grok (grok-4-fast-reasoning) | NO_EDGE |
| Alibaba Qwen-Plus | NO_EDGE |
| Xiaomi MiMo v2.5-Pro | NO_EDGE |

- `no_edge_votes` = **3 / 3**
- `potential_edge_votes` = **0 / 3**
- `inconclusive_votes` = **0 / 3**

**Unanimous consensus: NO EDGE.** All three independent models, given the same neutral
data packet, converge on the same conclusion: the project does not currently exhibit a
real, exploitable statistical edge. The +313% rolling-100 claim is unanimously flagged
as a probable window artifact / cherry-pick that is mathematically inconsistent with
the unconditional PF 0.46.

Notable convergent recommendations (different mechanisms, same destination — "you must
prove out-of-sample, regime-conditioned, sample-sufficient persistence before sizing
up"):

- Grok: per-source trailing PF>1.2 / WR>48% gate with n≥200.
- Qwen: minimum hold-time gate to kill microstructure / latency hallucinations.
- MiMo: regime/volatility gate (ADX>25 or realized-vol percentile).

---

## My Independent Verdict (Claude Opus 4.7, this session)

Based on what I can verify from this repo *without* deferring to the external panel:

1. **TRUTH LAYER raw 11.13% WR / PF 0.46 is unambiguously losing.** That is not a noisy
   "almost break-even" — it is a system bleeding ~54¢ per dollar risked at the
   unconditional level. Months of filter engineering have moved this to 25.28% WR /
   PF 0.61 on smart-picks — still net negative, still below break-even by a wide margin.

2. **Zero asset classes at T1 or T2 per `money_ready_verdict.json`** (already cited in
   CLAUDE.md MAJOR GOALS section). The two STABLE_EDGE flags are on n=178 (COMMODITY)
   and n=286 (EQUITY) — neither is enough sample to claim a hedge-fund-grade edge
   surviving Deflated Sharpe / SPA correction. The CLAUDE.md doc itself acknowledges
   concentration gate is not enforced before DSR/SPA → false-PASSes have already happened.

3. **CRYPTO 78.9%→38% WR over 14d with 0 closed in 48h vs 322 active** is the strongest
   single piece of evidence that the apparent historical "edge" was either (a) resolver
   mislabel artifact, (b) regime-dependent and the regime is over, or (c) selection
   survivorship that vanishes once positions actually close. None of those are edge.

4. **The +313% rolling-100 claim contradicts the unconditional PF 0.46.** It is
   mathematically possible (fat tails) but the burden of proof is on the operator to
   show the *distribution* of rolling-100 windows, not the best one. Until then it is
   not evidence of edge — it is consistent with noise.

5. **Today's 4 scoring-path PRs** (#263/#275/#277/#278) are code-correct but address
   plumbing/scoring mechanics, not the absence-of-edge problem. They cannot create edge
   where none exists in the underlying signals; they can only stop further bleeding from
   bad routing/labeling.

**My verdict: `NO_EDGE`** at the project level today. There are localized signals worth
investigating (CRYPTO trust_score=7 at 85.9% WR / n=99 per MEMORY.md, COMMODITY/EQUITY
small-n STABLE_EDGE flags), but none of them rise to "the project has an edge" — they
rise to "there are 2–3 narrow hypotheses worth pre-registering and replicating
out-of-sample before sizing capital." That is the *opposite* of a green light.

The honest answer to the operator's question is: **no, not yet — and the +313% headline
is almost certainly a window artifact that should be retracted until provenance is
proven.**

---

## Return Token

`PEER_AI:models_consulted=3:no_edge_votes=3:potential_edge_votes=0:inconclusive=0:my_verdict=NO_EDGE`
