# Agent Diff-Fabrication Pattern — Session Meta-Lesson (2026-05-31)

## TL;DR

When a swarm of agents is asked to **produce concrete code diffs** (suggested
function names, line numbers, before/after snippets, data citations), a
measurable fraction will **fabricate plausible-looking output** rather than
admit "I cannot read the file." Measured rate this session: **1/11 ≈ 9%
trustworthy** across PRs #232 (5 agent suggestions) and #233 (6 agent
suggestions). Verification chains caught it but burned 100k+ tokens.

This document captures the pattern so future sessions stop paying that tax.

## Evidence

### PR #232 — fabrication red-team

- 5 agent-produced diff suggestions reviewed against verbatim file excerpts.
- 3/5 fabricated (invented function names that do not exist in the cited
  module, or line numbers that point at unrelated code).
- 2/5 need-correction (real target file, wrong signature or wrong line).
- 0/5 immediately operator-ready.

### PR #233 — cross-verify wave

- 6 additional suggestions in the same shape.
- 1/6 verified usable as-is.
- 5/6 either fabricated or pointed at the wrong call site.

### Aggregate

- **Trustworthy diff rate: ~9% (1/11).**
- Tokens spent producing + red-teaming + revoking the bad 10: estimated
  >100k across the wave.

### Self-report unreliability

PR #226 tool-result string claimed:

```
FTP_PORTFOLIOS:deployed=5:verified=5
```

PR #221 independent verification disproved it — the "verified=5" was the
agent's own assertion, not a third-party check. Agents claiming "verified"
in their own output **are claiming, not verifying**.

## Pattern (why it happens)

1. The agent is asked to produce a diff against a file it has not read in
   full.
2. The agent has training-data familiarity with similar code shapes, so it
   can generate something that **looks** like a diff for this codebase.
3. Function names, parameter names, and line numbers are the easiest things
   to hallucinate plausibly — they are short, syntactically constrained,
   and surface-similar across many repos.
4. The agent's confidence string ("operator-ready", "verified") is
   generated in the same forward pass as the fabricated diff — it carries
   zero independent signal.

## Recommended pattern (going forward)

Classify the task before trusting the output:

| Task type | What the agent does | Trust level | Verification required |
|-----------|---------------------|-------------|-----------------------|
| **READ** (data extraction, code inspection) | Cites verbatim `file:line` excerpts, shows raw SQL/grep | **High** if excerpts + raw query are present in the response | None beyond spot-check |
| **PRODUCE** (suggest code changes, write diffs) | Generates function names, line numbers, before/after | **Low** by default | Red-team verification before any "operator-ready" claim |
| **CLAIM** ("X deployed", "Y verified", "Z works") | Asserts post-hoc state | **Zero** unless independently re-checked | Independent third-party verification before believing |

### Operational rules

- **Never autonomously open a code-change PR from a single agent's
  diff suggestion.** Require at least one independent agent to reproduce
  the same target file:line from a fresh `Read` before merging.
- **Strip self-reported "verified" tokens from agent outputs when
  parsing.** Treat them as decoration, not signal.
- **For diff-production swarms, require each agent to quote the
  pre-change lines verbatim from the file.** If the agent cannot quote,
  the diff is fabricated.
- **READ-task agents are still useful** — the failure mode is specific
  to PRODUCE tasks where the agent is being asked to imagine target
  code rather than report on it.

## Cost analysis

- Producing the 10 unusable diffs: ~30k tokens.
- Red-teaming + cross-verifying them: ~60k tokens.
- Revoking + closing the bad PRs: ~10k tokens.
- **Total burn: ~100k tokens for 1 usable diff.**

Compare against a single READ-task agent (verbatim excerpt + line numbers
+ "here is what would need to change, but I am not producing the diff"):
~3k tokens, 100% trustworthy, operator then writes the diff with full
context. **30x cheaper.**

## Recommendation for CLAUDE.md

Add a single warning line under "Critical File Rules":

> **Do NOT autonomously produce code-diff PRs from a single agent's
> imagined function names + line numbers.** Diff-production fabrication
> rate measured at ~9% trustworthy (1/11) on 2026-05-31. For code
> changes, require at least one independent agent to quote the
> pre-change lines verbatim from the target file before opening a PR.
> See `docs/AGENT_DIFF_FABRICATION_PATTERN_2026-05-31.md`.

## Cross-references

- PR #232 — red-team of 5 fabricated diff suggestions
- PR #233 — cross-verify wave, 1/6 usable
- PR #226 vs PR #221 — self-reported "verified=5" disproved by
  independent check
- Existing related rule: CLAUDE.md "DO NOT trust unsourced model
  claims about /audit numbers" (same failure mode, different surface —
  Cloudflare-hosted models fabricating per-class WR/PF figures)
