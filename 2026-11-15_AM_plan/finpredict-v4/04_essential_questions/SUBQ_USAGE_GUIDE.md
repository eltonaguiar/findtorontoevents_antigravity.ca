# SubQ Usage Guide — finpredict-v4 (UPDATED with verified working schema)

**Date:** 2026-11-15 (AM)
**Status:** Round-trip COMPLETE — verified working call.

---

## Verified API contract (from official docs + confirmed working call)

- **Endpoint:** `POST https://api.subq.ai/v1/systemone`
- **Model:** `subq-snap-1.2` (do NOT use `subq-savant-1.4` — rejected with 422)
- **Auth:** `Authorization: Bearer <key>` (keys in `~/dbpasses.txt`; never commit)
- **Context:** passed under `"state"` (string/object/array) — NOT `input` or `messages`
- **Questions:** top-level `questions` object, keyed by custom question name (≤100 chars), each with:
  - `"type"` — one of **`"noul"`**, **`"choice"`**, **`"score"`**
  - `"instructions"` — **required** (string)
  - `"question"` — the prompt text
  - `"criteria"` — per type:
    - **`noul`** (Yes/No gate): object with `"true"` and `"false"` string descriptions. Returns `answers.<name>.noul` = 0..1 probability.
    - **`choice`** (single-select): **2–255 keys** inside `criteria`, each mapping to a description string or null. Returns `answers.<name>.choice` (winning key) + per-option `probabilities` + `confidence`.
    - **`score`** (ordered rating): `criteria` is an **ordered array of 2–10 level strings** (lowest first). Returns `answers.<name>.score` (probability-weighted float) + `legend` + `probabilities` + `confidence`.

### Schema gotchas (verified)
- **NO `options` key.** Passing `options` or omitting `criteria` on choice/score → 422 `validation_error` ("must have required property 'criteria'").
- `instructions` is required on every question (the official docs omit it; the live API requires it — confirmed).
- Model must be `subq-snap-1.2` (or your key's active model from `GET /v1/models`).

---

## Verified working payload (copy-paste template)

```json
{
  "model": "subq-snap-1.2",
  "state": { "context": "..." },
  "questions": {
    "q1": {
      "type": "choice",
      "instructions": "Select the single best option.",
      "question": "...",
      "criteria": {
        "opt_a": "Description A",
        "opt_b": "Description B"
      }
    }
  }
}
```

**Sample verified results (3-question test):**
| Question | Type | Answer | Interpretation |
|----------|------|--------|----------------|
| is_index_bet_core | noul | **0.979** | Confirms index ETF buy-and-hold ≈ highest-probability lower-risk path |
| best_style | choice | **long_term_trend (0.875)** | Long-term trend most grounded; day-trading 0.027, scalping 0.041 |
| confidence_score | score | **1.95 / 4** | Evidence for trend-vs-scalp is grounded but modest |

---

## Fact-checking the SubQ response (grounding logic)

The SubQ outputs agree with primary evidence:
1. **Index beta core (0.979)** — grounded in the equity risk premium + low costs (Vanguard/Fidelity index funds). This matches every audit round's conclusion (beta ≠ alpha).
2. **Long-term trend > scalping (0.875)** — matches the famous-algorithm reality checks: Faber 200-day, AQR/Clenow momentum, CTA trend are grounded (risk premium/behavioral); intraday scalping is cost-fragile and overfit-prone.
3. **Low-moderate confidence (1.95)** — appropriately humble; the evidence is real but not overwhelming (momentum crashes, trend's flat 2010s). SubQ is NOT overclaiming — a good sign it's reasoning from grounded principles rather than pattern-mining.

**Conclusion:** SubQ's outputs are logically consistent and grounded. Use it as a decision voter/fact-checker, cross-referenced with primary sources and your own OOS/benchmark tests.

---

## Recommended usage for agents

1. Read keys at runtime from `~/dbpasses.txt`; never commit.
2. Use the exact schema above (type noul/choice/score, criteria, state, subq-snap-1.2).
3. Treat SubQ as a **decision voter / fact-checker**, not the source of truth.
4. Triage: rank candidates by grounded principle; then run your own OOS/benchmark test.
5. Reject any "proven"/contest claim that SubQ (or any model) cannot back with a primary source.
