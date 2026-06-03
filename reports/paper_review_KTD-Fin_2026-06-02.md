# Paper Review — KTD-Fin: Memory-Controlled Benchmark for LLM Trading Agents

**Reviewed by:** Claude Opus 4.8 · **Date:** 2026-06-02 · **Source:** kurate.org rank #1542 (ts_score 1405)
**Paper:** *From Knowing to Doing: A Memory-Controlled Benchmark for LLM Trading Agents on Stock Markets*
Zhu, Zhao, Sun, Luan, Lu, Wang, Li, Jiang — arXiv **2605.28359v1** (2026-05-27, cs.AI / q-fin.TR)

## What it says
End-to-end LLM-trading-agent backtests have **two evaluation failures**:
1. **Knowledge leakage** — long backtests overlap the LLM's knowledge cutoff, so memorized tickers /
   dates / prices / market narratives substitute for genuine investment reasoning.
2. **Raw returns ≠ alpha** — positive PnL may be market **beta**, **style** exposure, or a favorable
   **regime**, not stock-selection skill.

**KTD-Fin** fixes both: (a) a **data-side masking protocol** anonymizing tickers + calendar
identifiers consistently across prompts *and* tools (separates market memory from decision-making);
(b) a **Barra-style attribution** decomposing returns into market / style / stock-selection-alpha.

**Result** (10 frontier LLMs, CSI300, 2024–2026): masking pushes agent rationales toward anonymized
factor reasoning; under leakage-control, cumulative returns are *"largely explained by passive market
and style exposure, with limited evidence of persistent stock-selection alpha."*

## Why this matters to US (direct hit on our headline claim)
Our "best edge" is the **ai-tournament `deepseek_v4` sleeve: n=208, WR 57.7%, PF 3.46** — evaluated on
a **recent (2024-2026-ish) window that sits inside frontier-model knowledge cutoffs**, on named tickers.
Per this paper, that number is **doubly suspect**:
- It may be partly **memorization** (leakage), not reasoning — the exact failure mode #1.
- Even the real part may be **beta/style**, not alpha — failure mode #2. This is the academic form of
  our own "two-scoreboard split" (PR #476): tournament PF ≫ production PF.

So the tournament leaderboard, which the project treats as "where the edge lives," is **not validated
as skill** by current methodology. This *strengthens* the EAGLE2 thesis (research edge ≠ deployable edge).

## Concrete actions (proposed)
1. **Return-attribution gate** (new, HIGH): before any LLM-agent sleeve is called "edge," decompose its
   returns into market + style + residual alpha; require the alpha component (not raw PF) to clear the
   bar. Wire into `promotion_path.reconcile_scoreboards` as a third leg. → ENHANCEMENT_OVERALL.
2. **Leakage-controlled re-score of `deepseek_v4`**: re-run the tournament sleeve on an
   **out-of-knowledge-cutoff** forward window only (post-model-release dates) and on **masked tickers**;
   compare PF to the headline 3.46. If it collapses, the edge was memorization. (Forward-paper data the
   shadow-size ladder #67 already collects is naturally leakage-free — use it.)
3. **Adopt masking for the tournament harness**: anonymize ticker+date in the prompt/tooling for a probe
   run; if rationales/PF change materially, the original run was memory-driven.

## Verdict
Strong, directly-applicable paper. Single most useful import: **attribution (alpha vs beta/style) +
leakage-control as a promotion prerequisite for any LLM-generated sleeve.** It says, rigorously, what
our money_ready=[] data already hints: the tournament edge is probably not transferable skill yet.
Adds nothing that contradicts the shipped gate-stack; it adds a missing dimension (attribution) on top.
