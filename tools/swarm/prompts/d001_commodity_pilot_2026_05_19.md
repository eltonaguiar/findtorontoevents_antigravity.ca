# D-001 COMMODITY Pilot Decision: $0 Defer vs $50K Shadow

## Context

COMMODITY asset class current stats (dashboard_data.json as of 2026-05-18):
- PF 1.78, WR 46.9%, n=750 closed picks
- CT=F (Cotton #2 futures) dominates: ~70-80% of COMMODITY picks
- COT_STALE_GATE now enforce-by-default (M-001, flipped 2026-05-19)
- cta_commodity_momentum_term BLOCKED both directions (WR=0% n=11)
- multi_asset_copytrader FUTURES re-blocked (WR=2.5% n=157)
- COMMODITY is T2-candidate by PF (>1.5) but WR 46.9% is below T2 floor (50%)

## The Decision

D-001: Allocate a $50K paper/shadow trading account to COMMODITY picks
- Shadow only (no real capital, just tracking)
- 10% position sizing ($5K per pick)
- Track real forward PnL for 60 days to validate live edge

**Option A: $0 Defer** — Wait until WR reaches 50% and n≥1000 before any shadow capital. Rationale: current 46.9% WR is below T2 floor; allocating shadow capital to a sub-floor class is premature.

**Option B: $50K Shadow Now** — Start shadow capital immediately. Rationale: PF=1.78 is strong T2 evidence; WR might be slightly depressed by legacy bad picks; 60-day forward track will tell us definitively.

**Option C: $25K Partial Shadow** — Split the difference: half-sized shadow account, focus only on CT=F picks with COT_STALE_GATE passing (post-M-001). Rationale: CT=F COT WR=77.5% PF=4.69 n=40 is elite; the weak WR drags come from non-CT=F strategies already blocked.

## Evidence For Option B / C

1. CT=F COT-filtered picks: WR=77.5%, PF=4.69, n=40 — elite tier evidence
2. cta_replicator (non-CT=F) already blocked → WR should rise from 46.9% toward 55%+
3. M-001 COT_STALE_GATE now enforce-by-default → eliminates stale-data risk
4. PF=1.78 means even at 46.9% WR, avg winner covers avg loser with margin
5. COMMODITY_CTF_WEEKLY_CAP (M-002) already default=1 → CT=F concentration managed

## Evidence For Option A

1. WR=46.9% is 3pp below T2 floor (50%) — institutional floor exists for a reason
2. n=750 includes pre-gate picks that would now be rejected → forward sample may be smaller
3. No verified walk-forward out-of-sample evidence yet
4. CT=F n=40 is below charter minimum n≥100 for promotion to "proven"

## Question

Pick A, B, or C. Justify in 2-3 paragraphs. What additional evidence would change your answer? What's the main risk of your choice?

Constraint: We cannot run the COMMODITY generator locally. Shadow capital means we track paper PnL only — no real dollars at risk.
