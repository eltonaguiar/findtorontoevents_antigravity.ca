Thinking...
We need to answer concisely.

We have 3 strategies just below threshold.

Need to decide priority.

A: Crypto strategy; has just over n=205 (above floor but below proven), n=205 closed picks. WR 52.2% PF 1.66 < threshold 1.5?? Wait threshold: Tier-2 PF>=1.5 WR>=50 MDD<20. 1.66 passes PF, 52.2 passes WR, MDD not listed? Not given but likely >20? maybe threshold 20 for Tier-2. They blocked due to kill_list etc. Also symmetric. Danger: blocked due to kill_list. Also had "appears in every toxic consensus combo" but not standalone? That indicates we might explore.

B: Equity/ETF strategy; n=23, PF 7.49, WR 78.3% > threshold. But small n, rare setup.

C: BTC strategy; n=22, WR 95.5% PF 13.51. Score <50, block gate. Reaches kill_list removal but score gate blocks.

Prioritization: Which needs intervention to get promotion?

A: Already meets thresholds, blocked by kill_list. So intervention: unblock strategy. Highest leverage fix: remove from kill_list, update block list removal in blocklist. Or get trust tier move from RELIABLE? trust tier is RELIABLE, wf_verdict VIABLE score 45. Actually score 45 borderline.

But it's blocked in _PAPER_ONLY_STRATEGIES due to 'appears in toxic consensus combo', meaning we might need to whitelist or add patterns.

B: It is not blocked but just rare, low closed picks and no active. Might require upstream issue. We can schedule, but not urgent.

C: Score gate blocks emission; even with kill_list removed. We need to adjust score or add to proven strategies.

Thus, priority A > C > B.

Now 1-line fixes:

A: Remove from _PAPER_ONLY_STRATEGIES and kill_list; update blocklist entries.

C: Increase score threshold reasoning; add to proven_list after manual review or raise trust tier. Or temporarily lower 50 score floor.

B: Ensure upstream logic handles rare setup; verify spark/emit triggers; add missed triggers.

Fragility concerns: A: 205 trades moderate but firmly 2 months? Have symmetric, but still possible noise. risk of changing consensus patterns. B: small n 23, high DR; not robust. C: avg score <50; many picks have low conf <0.5; vulnerable to regime shift. Also concentrated symbol BTC only.

Relax floor? For proven-WR strategies, maybe loosen 0.55/50 conf but keep rigorous to avoid noise. So keep rigid for now, but consider temporary relaxation for high WR.

Symmetric LONG/SHORT and equal TP/SL: means strategy is systematic; not noise. That is a positive factor.

We answer.

Let's craft concise answer.
...done thinking.

**1. Priority order (promotion‑step work in this week)**  
- **A. luxalgo_confluence (GR)** – meets/wraps Tier‑2 metrics, but is blocked by kill‑list & paper‑only filter.  
- **C. atr_percentile_gate (BTC‑only)** – high WR/PF but trapped by the 50‑score/0.55‑conf gate.  
- **B. rs‑breakout‑scout (EQUITY/ETF)** – exceeds WR/PF but suffers from an upstream “rare‑setup” message and has no live runs; less urgent.

**2. Highest‑leverage 1‑line fix for each**  
- **A**: `unmark_in_kill_list_and_paper_only('luxalgo_confluence')` (edit strategy_blocklist.py & core_whitelist.json).  
- **C**: `bounce_score_gate_by_explicit_agreement()` – temporarily bump the strategy to “PROVEN” after manual review and lock its score threshold into the config.  
- **B**: `force_manual_trigger_via_smart_picks_engine()` – add a hard‑coded daily check so the engine fires even on rare setups.

**3. Fragility concerns**  
- **A**: 205 trades → moderate sample, but heavy reliance on consensus patterns can over‑fit to recent crypto volatility.  
- **C**: Avg score 44.7 / 27 % confidence <0.5 → highly fragile to regime change; only BTC exposure compounds risk.  
- **B**: 23 picks → tiny‑n, performance inflated by luck; over‑reliance on a few ticker checks (SOXX, XLK, etc.) makes it vulnerable to sector moves.

**4. 0.55 confidence / 50‑score floor**  
- Keep rigid for *all* Tier‑2 and Tier‑1 promoted strategies to guard against noise.  
- For a *high‑WR*, *high‑PF* strategy that has a mature sample and is proven in other archetypes, a temporary, *operator‑approved* relaxation can be considered, but not a hard rule change.

**5. Symmetric LONG/SHORT + equal TP/SL hit counts in A**  
- **FOR** – indicates a disciplined, model‑based system rather than luck; the balance reduces directional bias and makes the edge more credible.  
- No evidence that the symmetry is a noise artifact; it should be treated as a validating signal for promotion.

