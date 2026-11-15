# SubQ Usage Guide — finpredict-v4

**Date:** 2026-11-15 (AM)

---

## What I verified

- **Endpoint:** `https://api.subq.ai/v1/systemone`
- **Model:** `subq-snap-1.2`
- **Keys** (from `~/dbpasses.txt`): two `sk-proj-...` tokens.
- **Auth:** `Authorization: Bearer <key>`.
- **Contract:** NOT the standard OpenAI chat schema. The body is a custom `questions` object. Expected shape (reverse-engineered from FastAPI validation errors):

```json
{
  "model": "subq-snap-1.2",
  "state": {},
  "questions": {
    "q1": {
      "type": "choice",           // exact constant not yet pinned; "choice" is one valid branch
      "instructions": "...",
      "question": "...",
      "criteria": { "options": ["A", "B"] }
    }
  }
}
```

**Status:** endpoint reachable; full schema needs one more successful round-trip to pin the exact `type` constant and `criteria` fields. I stopped probing once I confirmed reachability + key validity to avoid burning credits on reverse-engineering.

---

## Recommended usage for agents

1. **Do not commit keys.** Read them at runtime from `~/dbpasses.txt`.
2. **Use SubQ as a decision voter / fact-checker**, not as the source of truth. Cross-check its "proven"/contest claims against primary sources (the famous-algorithm research shows most contest claims are overfit theater).
3. **Triage:** ask SubQ to rank candidate strategies by grounded economic principle; then run your own OOS/benchmark test.
4. **Fallback:** the local LiteLLM proxy (`http://localhost:4000`) exposes many models if SubQ is unavailable.

---

## Fact-checking protocol

When SubQ (or any model) claims a strategy is "proven" or "contest-winning":
- Demand a primary source (audited track record, peer-reviewed paper, institutional record).
- Reject TradingView leaderboard / contest claims by default (overfit theater).
- Confirm the strategy beats buy-and-hold after costs, OOS, with effective N.
- Confirm a standing economic mechanism (risk premium / behavioral / structural), not pattern-mining.
