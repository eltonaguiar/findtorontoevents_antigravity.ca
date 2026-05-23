# External AI Peer Review — 2026-04-18

4 external LLMs independently reviewed the 7 consolidated audit findings from `docs/ANALYSIS_TRADING_FORENSIC_2026_04_18.md`. Brief at `C:/Users/zerou/AppData/Local/Temp/peer_review_brief.txt`. Reviews at `C:/Users/zerou/AppData/Local/Temp/review_*.txt`.

## Models used
- **DeepSeek-chat** (direct API, `api.deepseek.com`)
- **DeepSeek-v3.1:671b** (via Ollama cloud)
- **GLM-4.6** (via Ollama cloud)
- **Gemma3:27b** (via Ollama cloud)

Kimi-K2-Thinking + Minimax-m2.5 + Qwen3.5:397b returned errors (model unavailable / server 500). Mercury/Inception key still rejects POST despite GET /models succeeding — unresolved infra issue.

## Unanimous consensus across 4 models

### 🔴 #1 ROI action: Fix MATIC bug + purge contaminated rows BEFORE any strategy change
Every reviewer ranked this as the single highest-ROI action. Three called it "non-negotiable." DeepSeek-v3.1 called the 889 erroneous trades "over 17% of the LONG sample size — their removal is a prerequisite, not a footnote."

### 🔴 My "tilt SHORT" recommendation was premature
All 4 reviewers flagged this.
- **DeepSeek**: "The audit's claim that 'earlier playbook banned SHORTs backwards' is premature."
- **GLM-4.6**: analyzing corrupted data makes strategy attribution speculative.
- **Gemma3**: "n=95 is a small sample size. While 56.8% WR is encouraging, Wilson LB of 46.9% indicates significant uncertainty."
- **DeepSeek-v3.1**: "It is a hypothesis for further testing, not an actionable conclusion."

DeepSeek's quick decontamination math:
- Current LONG: 4,296 trades × avg −0.161% = −691.7% total PnL
- Remove 889 MATIC deterministic losses (all LONG, all −0.15%): leaves 3,407 trades
- Resulting LONG avg is likely closer to breakeven or slightly positive
- SHORT at 56.8% may still be higher but gap closes dramatically; wait for clean data

### 🔴 Biggest analytical flaw: ran strategy attribution on corrupted data
All 4 converge. GLM: "The analysis is building a house on a foundation of sand." DeepSeek-v3.1: same conclusion. Only Gemma3 named a different flaw: "Lack of documented, rigorous backtesting methodology" — but still agreed MATIC must go first.

## Divergent views — which novel strategy to reject?

| Reviewer | Rejects | Reason |
|---|---|---|
| DeepSeek-chat | **#5 Regime-conditional mutator** | "Multiplies complexity without evidence base strategies are profitable. Overfitting risk." |
| DeepSeek-v3.1:671b | **#5 Regime-conditional mutator** | "Solves weak signals by creating more weak signals, not stronger ones. Priority = simplification, not complication." |
| Gemma3:27b | **#1 Copper-Gold regime gate** | "Simplistic, potentially spurious correlation. Naive to rely on a single commodity pairing as universal filter." |
| GLM-4.6 | (response truncated before Q4) | — |

**Consensus on #5 (2 of 3 explicit): don't build the regime-conditional mutator.** Gemma's objection to #1 Copper-Gold is worth heeding but not blocking; the signal has macro-literature support and is a 1-day implementation.

## Divergent on quan_engine exit logic rebuild

- **DeepSeek-chat, GLM-4.6, Gemma3** all said −0.133 correlation is weak (explains <2% variance) and NOT load-bearing enough to rebuild exit logic on.
- **DeepSeek-v3.1** uniquely disagreed: "In high-volume, low-margin prop trading, even a small statistically significant negative correlation between hold time and PnL is a critical failure of exit logic. This is a high-ROI fix."

**Reconciliation**: both are right in different ways. The correlation alone isn't strong enough to rebuild everything, but combined with:
- TIME_EXIT dominance on losers
- The healthy `rapid_fire` counter-example (winners run 3.31h, losers cut 0.92h)
- 97.4% volume concentration in quan_engine

...it's strong enough to **port rapid_fire's exit logic** into quan_engine as a targeted experiment, not a full rewrite. That's the path of smallest-change-highest-signal.

## Critical checks I missed (cross-reviewer)

### Gemma3 — transaction cost analysis
**"Slippage, exchange API limitations, and order book impact are ignored. High-frequency strategies like `quan_engine_scalp` are extremely sensitive to these costs."**

Valid. My audit treated the −0.15% fee constant as fixed; reality includes variable slippage at different volumes, spread widening in low-liquidity symbols, and order-book-impact cost at larger sizes. **Action**: add per-strategy realized-cost decomposition in next audit.

### DeepSeek-v3.1 — price-stability anomaly detection
**"889 trades with identical entry/exit prices and near-zero stdev for a month is a glaring anomaly that should have been caught by automated monitoring long before an audit."**

Valid. No current monitoring flags deterministic-loss patterns. **Action**: add a pre-emission guard that rejects picks where the last N scans on a symbol returned identical price ± ε. Feed_hygiene doesn't currently check this. Low effort, high value.

### DeepSeek-chat — survivorship bias in "proven_" labels
**"Why were `proven_propfirm_cons_prop` (19% WR) and `proven_triple_ema_prop` (17% WR) ever labeled 'proven'? System may have a pattern of promoting strategies without robust walk-forward validation."**

Valid. The "proven_" prefix suggests a historical validation gate that no longer holds. **Action**: audit the promotion pipeline (`strategy_promotion_pipeline.py`?) to confirm it still gates on fresh out-of-sample performance, not stale backtests.

## Consolidated action plan (in order)

| # | Action | Effort | ROI |
|---|---|---|---|
| 1 | **Fix MATIC dead-ticker** — add to `_DEAD_SYMBOLS` in `feed_hygiene.py`, remove from `_SYMBOL_ALIASES` silent remap | 15 min | Stops active bleed; 889 contaminated rows no longer grow |
| 2 | **Tag the 889 historical MATIC rows** as `rebrand_artifact: true` in `closed_picks.json` so aggregates can exclude them | 30 min | Cleans every future WR/PnL calculation |
| 3 | **Add deterministic-loss pre-emission guard** — reject picks where stdev(last 20 prices on symbol) < ε | 1 hour | Catches next rebrand incident automatically |
| 4 | **Re-run V3 playbook analysis on cleaned data** | 1 hour | Accurate direction recommendation |
| 5 | **Port `rapid_fire` exit logic into `quan_engine`** as an A/B test (not full replacement) | 1 day | Addresses 97.4% of volume concentration |
| 6 | **Retire 3 strategies**: `fear_greed_contrarian` (−456% cum), `proven_propfirm_cons_prop` (19% WR), `proven_triple_ema_prop` (17% WR) | 30 min | Removes 7k+ losing picks from emission pipeline |
| 7 | **Audit `strategy_promotion_pipeline.py`** for proper walk-forward validation gates | 2 hours | Prevents future "proven_" mislabeling |
| 8 | **Normalize direction vocabulary** (BUY/SELL → LONG/SHORT) schema migration | 2 hours | Fixes direction-field miscount that caused 103 vs 889 scope error |

## What I got RIGHT (per reviewers)
- Diagnosis of MATIC as a bug (unanimous)
- Identification of quan_engine concentration risk (unanimous)
- Flagging of null-strategy data hygiene (GLM, implicit in DeepSeek)
- Rejecting novel strategy #5 regime-conditional mutator (2/3 explicit)
- Inverse wrapper being wired (factual — all reviewers accepted)

## What I got WRONG (per reviewers)
- "Tilt SHORT" recommendation — premature, n too small, contaminated (4/4)
- Retraction doc's finding #2 ("SHORTS bleed even though they win") — probably an artifact of MATIC contamination, not a real exit-logic issue on SHORTs
- Implied the quan_engine exit-logic rebuild is slam-dunk from −0.133 correlation alone — it's weak evidence that needs other signals to justify
- Didn't flag the monitoring gap (no anomaly detection on deterministic-loss patterns)
- Didn't include transaction cost decomposition beyond fee constant

## Remaining infra issues
- Kimi-K2-Thinking returned Ollama cloud 500 error (reproducible)
- Minimax-m2.5 + Qwen3.5:397b returned empty bodies (possibly model not provisioned on free tier)
- Mercury/Inception POST rejects key despite GET /models accepting it — needs debug

## Raw reviews
- DeepSeek-chat: complete, 2800 chars
- DeepSeek-v3.1:671b: complete, 3187 chars
- Gemma3:27b: complete, 2889 chars
- GLM-4.6: truncated at ~1000 chars (retried with 4000-token limit — check `review_glm.txt`)
