---
name: noshortcutsprompt
description: Generates a no-shortcuts system prompt for querying any AI model, requiring production-grade reasoning, cited sources, no hallucinated data, and complete output. Use when the user says "/noshortcutsprompt", "no shortcuts", or "production grade prompt".
---

# /noshortcutsprompt — Production-Grade AI Prompt Generator

Outputs the standard "no shortcuts" system prompt used in the AI Prediction Tournament
(see `docs/AI_PREDICTION_TOURNAMENT_METHODOLOGY.md`).

## When to use

User says:
- `/noshortcutsprompt`
- "use the no shortcuts prompt"
- "add the production grade requirement"
- "make sure the AI doesn't take shortcuts"
- When sending any prompt to an external AI where you want rigorous, non-hallucinated output

## The prompt

When invoked, output the following prompt block ready to copy or prepend to a task:

---

```
Act as a senior quant researcher at a top hedge fund.
We need production-grade, mathematically rigorous, and thoroughly verified code/strategies for this task.

Requirements:
- Think step by step and show your reasoning BEFORE writing any code or picks.
- Double-check every formula and assumption against standard references (cite the exact source if possible).
- Use full type hints, complete docstrings, and include safety checks (e.g. minimum sample size, no lookahead bias).
- Output ONLY ready-to-apply results: strategies with symbol, direction, entry_price, take_profit, stop_loss, confidence (0-1), asset_class, and a full rationale.
- If anything is approximate or simplified, explicitly call it out and provide the full rigorous version instead.
- Explicitly state your data sources and date ranges. DO NOT fabricate historical data.
- If you cannot access real data for a claim, say so rather than inventing numbers.
- Partial code or "I'll leave this as an exercise" is not acceptable. Complete implementations only.

Current live dashboard: https://findtorontoevents.ca/audit/
Task: [YOUR ACTUAL REQUEST HERE]
```

---

## Usage in AI Tournament context

When collecting picks from a model for `audit/ai-tournament`, append the following after the base prompt:

```
Your task:
1. Choose your preferred symbol universe for [ASSET_CLASS] trading.
   Justify each inclusion (liquidity, data availability, your prior conviction, economic rationale).
2. Design ONE primary strategy for [ASSET_CLASS]. Name it. Describe the exact entry/exit logic.
3. Generate [N] specific forward-test picks valid from today [DATE].
   For each pick: symbol | direction | entry_price | take_profit | stop_loss | confidence | rationale
4. State which historical period your strategy performed best in and cite the source.
5. What is the primary failure mode — when does this strategy NOT work?
6. What would falsify your strategy? State the kill condition.
```

## Anti-patterns to catch in responses

If the model's response contains any of these, re-prompt with a correction:

- "I don't have access to real-time data" used as a blanket excuse to give no picks → push back: "Use any reasonable current estimate and flag it explicitly"
- WR/PF numbers given without n (sample size) → push back: "Always include n"
- Strategy described in prose but no actual entry/exit signals → push back: "Give me the exact if/then logic"
- "Historical returns may not predict future results" as the only disclaimer, with no actual risk analysis → push back: "Give me the actual failure modes"
- Claims of 80%+ WR on >500 trades in a liquid market without any alpha decay note → flag as likely hallucination, run §5.1 verification

## Notes

- This skill is a prompt generator, not an executor. After outputting the prompt, the user applies it.
- For automated swarm use, the prompt is written to a `.md` file and passed to `tools/swarm/swarm_run.py --prompt-file`.
- Full methodology: `docs/AI_PREDICTION_TOURNAMENT_METHODOLOGY.md`
