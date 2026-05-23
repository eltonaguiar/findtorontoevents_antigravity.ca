# Verify Two Findings — Second Opinion Requested

You are 1 of 5 diverse engines giving a SECOND OPINION on two specific findings from the prior verification rounds. The pattern this session has been "0/11 prior numeric claims fully verified at face value" — so I want independent double-checks before acting.

## Finding 1 — FETUSDT elite RETRACTION

CLAIM: `ml_enhanced_FETUSDT_1d_B_lightgbm` is NOT a buried elite. Raw stats (n=44, WR 56.8%, PF 9.43, +$15,181) collapse after deduplication-by-exit-date to **n=20, WR 35%, PF 1.79, +$908**.

EVIDENCE:
- 44 picks but only 20 distinct `exit_date` values
- 10 of 44 picks (23%) collapse to a single market exit on 2026-03-25, all with identical `pnl_pct = +0.5813`
- Strategy fires daily; when one TP hits, all open positions in same direction close at same return → 10 bookkeeping wins, 1 market event
- Cross-check on other "elites":
  - INJUSDT_1d_B_lightgbm: raw PF 41.52 → dedup PF 25.88 (still strong, n=18 distinct events)
  - DYDXUSDT_15m_D_ensemble_stack: raw PF 60.54 → dedup PF 40.20 (still strong, n=20 distinct events)

Question: is dedup-by-exit-date the correct sample correction for daily-firing strategies, or am I over-correcting?

## Finding 2 — Pre-existing `+18 score bonus for confidence [0.75, 0.80)` is harmful

CLAIM: `audit_dashboard/template.html:9239` has been awarding +18 score to picks with confidence in [0.75, 0.80) under the comment "Verified edge: conf [0.75,0.80) = ~86% WR (Perplexity Comet verified)". But the live data does NOT support that claim.

EVIDENCE (verified earlier in `reports/comet_claims_verification_2026_05_04.md`):

| Band | n | WR | PF | Avg PnL |
|---|---|---|---|---|
| **[0.75, 0.80)** | **93** | **38.7%** | **0.69** | **-0.04%** |
| [0.80, 0.85) | 120 | 62.5% | 5.83 | +0.082% |
| [0.85, 0.90) | thin sample | — | — | — |
| [0.90, 1.0) | 1 (degenerate) | — | — | — |

The +18 bonus is firing on a LOSING band. Meanwhile a parallel `+12 score bonus for [0.80, 0.85)` was added on `template.html:9241` (this one is correct). So picks with conf [0.75, 0.80) currently get LARGER bonuses (+18) than picks with conf [0.80, 0.85) (+12), inverted from the actual edge.

Source: `alpha_engine/data/closed_picks.json` post-Patch-2 backfill (n=7,472).

Question: does removing the +18 bonus on [0.75, 0.80) introduce regression risk on any other code path (e.g., strategy gates, scaling logic), or is it isolated to score computation?

## Required output JSON

```json
{
  "engine": "<your name>",
  "finding_1_verdict": "agree|disagree|caveats",
  "finding_1_concerns": ["..."],
  "finding_1_recommended_action": "retract_promotion|hold|investigate_further|other",
  "finding_2_verdict": "agree|disagree|caveats",
  "finding_2_concerns": ["..."],
  "finding_2_recommended_action": "remove_+18_bonus|reduce_to_neutral|leave_alone|other",
  "regression_risks": ["..."],
  "confidence": 0.0-1.0,
  "notes": "<any extra context worth flagging>"
}
```

## Hard rules

- Cite the exact file/line/data path.
- If you disagree with my dedup methodology, propose the alternative (e.g., dedup by entry_date instead, or by symbol+exit-date pair, or no dedup with concentration-weighting).
- For finding 2, if you recommend removal, name the exact lines to edit (template.html:9239 and any related score-tracking variables `breakdown.conf_sweet_spot`).
- Default to skepticism: 0/11 prior claims face-value verified. The bar for accepting my new findings should be HIGH.

Output ONLY the JSON envelope.
