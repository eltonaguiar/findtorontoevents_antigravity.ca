You are reviewing a quant trading system session. Answer the 4 questions below. Respond ONLY with the JSON block — no prose, no markdown fences.

Context:
- C1 (gap-aware TP/SL fill): PR #1130/#1132 open, awaiting human review
- C2 (net PF with slippage): PR #1127 open, awaiting human review
- C3 (exclude blocked sources from aggregate): PR #1127 open, awaiting human review
- C4 (correct m004 autopsy n=21 not 1198): DONE
- C5 (preserve signal_time/entry_time/closed_at in _SCORING_FIELDS): DONE this session
- C6 (dedupe same-bar opposite-direction baby-strat collisions in incubator/validation/update_forward_matches.py:247-307): P3, NOT done

Questions:
1. Given the above status, what is the VERDICT for session completeness (DONE = nothing left we can do without human review; MOSTLY_DONE = <=1 minor thing; NEEDS_WORK = multiple actionable items remain)?
2. List any remaining code-actionable items that do NOT require human PR review (be specific: file + function if known).
3. C6 impact is ~0.2pp WR improvement, classified P3. Should we DO_NOW, DEFER, or SKIP?
4. mercury2_fast system: PF=0.07, n=32. Three-axis mutation protocol threshold is n>=20. Should we INVESTIGATE_NOW (open mutation investigation doc now), WAIT (gather more data first), or SKIP?

Respond in exactly this JSON format:
{
  "verdict": "DONE | MOSTLY_DONE | NEEDS_WORK",
  "remaining_code_actionable": ["item1", "item2"],
  "c6_recommendation": "DO_NOW | DEFER | SKIP",
  "mercury2_fast_recommendation": "INVESTIGATE_NOW | WAIT | SKIP",
  "summary": "one paragraph"
}
