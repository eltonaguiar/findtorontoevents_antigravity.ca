# Audit score improvement — review (Apr 7, 2026)

**NOT FINANCIAL ADVICE** — internal research notes.

## Summary

We reviewed the Cursor plan for **audit picks edge analysis** (snapshot `dashboard_data.json`, active-book analyzer, consolidated MD, Redis bus). The approach is **correct**: JSON-first, no fabricated SQL metrics, honest caveats on unrealized PnL vs predictive IC on closes.

Full write-up: **[docs/AUDIT_SCORE_IMPROVEMENT_PLAN_REVIEW_2026-04-07.md](../docs/AUDIT_SCORE_IMPROVEMENT_PLAN_REVIEW_2026-04-07.md)**

## Headline feedback

- **Crypto:** `smart_score` aligns with closed outcomes better than **elite** — don’t overweight elite in crypto composites until reformulated.
- **Equity:** Scores can **rank** names while the **traded universe** still loses — tighten **strategy allowlists / expectancy gates**, not only weights.
- **Forex / thin classes:** Weak headline score vs PnL and tiny n on some slices — treat as experimental; fix confidence or drop from ranker.
- **Infrastructure:** Fix **dashboard P0s** (total PnL summation, DD caps, payload parity) before exec decisions that cite headline “PnL.”
- **Hedge fund bar:** Add **active-book** reporting (plan’s `analyze_audit_active_book.py`) so the audit page is judged on **the same snapshot** for actives + closes.

Fleet: see **`docs/REDIS_BUS_CHANGELOG.md`** for topic **`audit_picks_score_improvement_review`**.
