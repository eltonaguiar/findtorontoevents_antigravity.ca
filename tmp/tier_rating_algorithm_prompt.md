# Question: per-asset-class symbol tier-rating algorithm (1–10 scale)

You are participating in an AI tournament for the findtorontoevents.ca/audit dashboard. The system currently scores picks with a class-agnostic composite, but per-asset-class formulas would likely lift WR/PF — especially on FOREX (currently sub-floor: PF 0.27 / WR 46.4%).

## Your task

If you were challenged to give a pick rating system to create a tier list of symbols on a scale of **1–10 per asset class**, what algorithm would you use for each asset class?

Output **one weighted-formula recipe per class** for **all eight classes**: EQUITY, ETF, CRYPTO, FOREX, COMMODITY, BOND, FUTURES, PENNY.

For each class, give:

1. **3–7 features** with **exact integer weights summing to 100%**
2. **Data feed required** per feature (be specific: yfinance, FRED, CFTC COT, Binance funding API, EIA inventories, etc.)
3. **One-line rationale** per feature (why it's predictive for this class)
4. **The score floor** below which you would refuse to enter the trade (1–10)
5. **One signature insight** per class — what's the single biggest mistake you see most rating systems make for this class?

## Output format (STRICT — must be valid JSON)

```json
{
  "model_id": "<your name>",
  "answered_at": "<UTC ISO timestamp>",
  "asset_classes": {
    "EQUITY": {
      "features": [
        {"name": "...", "weight": 25, "data_feed": "...", "why": "..."}
      ],
      "floor": 4,
      "signature_insight": "..."
    },
    "ETF": { ... },
    "CRYPTO": { ... },
    "FOREX": { ... },
    "COMMODITY": { ... },
    "BOND": { ... },
    "FUTURES": { ... },
    "PENNY": { ... }
  }
}
```

## Anti-shortcut rules

- Do **not** copy generic textbook factor lists. Tie each feature to a real data source you'd actually wire up.
- Weights must be your considered opinion, not equal-split.
- If you'd refuse to score a class because you don't have a strong opinion, return `"floor": null` and one paragraph explaining why — but try to answer all 8.
- Do not hedge with "it depends on market regime" unless you also specify the regime switch and a regime-dependent feature.

## Why we're asking

Your answer will be cross-compared with other models. Per-feature majority-weight will seed a new `alpha_engine/score_v3.py` candidate. The highest-conviction features that ≥3 models agree on get promoted into the production scoring pipeline.

Be rigorous. The output is consumed by code, not humans.
