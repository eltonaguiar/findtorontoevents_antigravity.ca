---
description: Quick 3-engine consensus check. Get a second (and third) opinion on any question, code change, or decision.
argument-hint: <question or topic>
---

User wants a second opinion. Invoke with:

```
/swarm second-opinion $ARGUMENTS
```

If `$ARGUMENTS` is empty, ask what they want a second opinion on.

## How it works

1. **Pick 3 engines** from the `consensus-3` preset (deepseek, xai, kilo).
2. **Fan the question** to all 3 simultaneously via `python tools/swarm/swarm_run.py`:
   ```bash
   python tools/swarm/swarm_run.py \
       --prompt-file /dev/stdin \
       --engines deepseek,xai,kilo \
       --max-parallel 3 \
       --out-dir swarm_runs/second-opinion-$(date -u +%Y%m%dT%H%M%SZ)
   ```
3. **Collect responses** and analyze:
   - Where do ALL 3 agree? → **High confidence** (consensus)
   - Where do 2/3 agree? → **Likely correct** (majority)
   - Where do all 3 disagree? → **Needs human judgment** (flag it)
4. **Present the consensus report** in this format:

```
SWARM CONSENSUS REPORT
======================
Question: [user's question]

CONSENSUS (3/3 agree):
- [point 1]
- [point 2]

MAJORITY (2/3 agree):
- [point 3] (dissented: [engine])

DISAGREEMENTS (needs your call):
- [point 4] — deepseek says X, xai says Y, kilo says Z

RECOMMENDATION: [synthesize the consensus into a clear recommendation]
```

## Prompt template

Write the user's question into a prompt file with this structure:

```markdown
You are reviewing a question for a trading/audit platform.
Give a clear, direct answer with your reasoning.

Question: [USER'S QUESTION]

Context (if relevant):
[any file content, PR diff, or code snippet the user is asking about]

Respond in JSON:
{
  "answer": "your direct answer",
  "confidence": "high|medium|low",
  "reasoning": "why you think this",
  "risks": ["potential issues"],
  "recommendation": "what to do"
}
```

## Speed notes

- This uses the **fast-cheap** path: 3 API engines in parallel
- Typical completion: 20-45 seconds
- Cost: ~$0.001 total (DeepSeek is nearly free, xAI is cheap)
- If an engine fails, proceed with 2/3 — still useful consensus

## Memory note

This is a one-shot check. The results are NOT stored in swarm session memory.
For persistent analysis that builds on prior findings, use `/swarm audit` or `/swarm github` instead.
