---
description: Bootstrap custom personas + test blueprint for a new problem domain.
argument-hint: <problem-file> [design-engine]
---

Parse `$ARGUMENTS`:
- First word: path to a markdown file describing the problem (file paths, line ranges, observed-vs-expected, hypothesis). If missing, fail with usage.
- Second word (optional): design engine. Default `cerebras`. Other options: `inception`, `deepseek`, `xai`, `openrouter`, `nous`, `ollama_cloud`, `claude`.

Run:

```
python tools/swarm/invent_personas.py --problem-file <problem> --persona-design-engine <engine>
```

After the script completes:

1. Show the printed summary table verbatim (file paths + NEW/INVENTED status).
2. Print the recommended next-step invocation from the script's stdout.
3. Remind the user to review the generated persona files in `tools/swarm/agent_personas/` before fanning out a paid swarm — the design engine can hallucinate scope or anti-patterns. Schema validation catches structural errors only.

If the script exits non-zero, surface the last 30 lines of stderr — the most common failure is the design engine returning malformed JSON, which the fallback chain (cerebras -> inception -> claude) usually handles, but all three CAN fail on a vague problem statement.

Reference: `tools/swarm/agent_personas/INVENT_PERSONAS_PROTOCOL.md`.
