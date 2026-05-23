# Meta-prompt recommendations (strategy harvest 2026-05-19)

Synthesized from cloud debate (Ring, Grok, DeepSeek) + local execute (qwen2.5-coder, qwen3, mistral-nemo).

**Input artifact:** `reports/TOP10_STRATEGIES_PER_ASSET_CLASS_2026-05-19.md`

---

## Five reusable meta-prompts

| meta_id | when_to_use | inject_variables | success_signal |
|---------|-------------|------------------|----------------|
| **META_DEBATE_PER_CLASS** | After regenerating TOP10 MD; cloud only | `{{TOP10_STRATEGIES_MD}}` | Per rank1–3: Judge verdict RESCUE\|KILL\|SHADOW + 30d falsifiable test |
| **STRATEGY_HARVEST_EXECUTE** | After cloud debate; local 14B OK | TOP10 + `{{DEBATE_SYNTHESIS}}` | 3 P0 PRs with real `wire_target` paths |
| **EDGE_STABILITY_RETEST** | Any strategy flagged SHADOW | `hypothesis_id`, `bar_freq`, `symbol` | `tools/edge_stability_harness.py` eff≥0.30, 3/5 windows |
| **EMITTER_WHITELIST_FLIP** | When SHADOW passes harness | `pf_registry` slice + pair list | WR lift ≥8pp on whitelist-only subset vs class net |
| **CROSS_CLASS_DEDUP_AUDIT** | Class PF contradicts strategy PF | dedup_key spec | SQL proof: recompute class net ex-toxic emitters |

---

## Judge verdicts (cloud Ring — ranks 1–3)

| Class | Rank1 strategy | Verdict | 30-day test |
|-------|----------------|---------|-------------|
| CRYPTO | ml_enhanced_DYDXUSDT_15m | **SHADOW** | 15m harness DYDX, PF≥3, n≥30, MDD<8% |
| CRYPTO | ml_enhanced_BNBUSDT_15m | **KILL** | n=19 overfit; quan_engine toxic family |
| EQUITY | multi_asset_copytrader | **KILL** | toxic pair; PF<1 |
| COMMODITY | multi_asset_cot | **RESCUE** | Verify non-CT=F after dedup; ab_analysis |
| COMMODITY | cta_replicator | **KILL** | PF=0.28, hardcoded toxic |
| FOREX | cta_replicator | **SHADOW** | SHORT-only slice; class cap 0% until pass |
| ETF/BOND | (thin n) | **FREEZE** | stop emissions 90d |

---

## How to proceed next (operator)

1. **Regenerate tables after each dashboard deploy:** `python tools/build_top10_strategies_per_class.py`
2. **Run full harvest:** `python tools/strategy_harvest_round.py --phase all`
3. **P0 wiring (this week):**
   - COMMODITY: verify `multi_asset_cot` in `emitter_whitelist` MANUAL_ALLOWLIST; run COT ab_analysis gate
   - CRYPTO: SHADOW only top per-symbol ML stacks — do **not** size class on PF=60 headline (overfit n)
   - FOREX: keep class blocked; paper `cta_replicator` SHORT-only experiment separate from class net
   - EQUITY/ETF/BOND: freeze new emissions; PEAD/trust_score path only for EQUITY
4. **Flip `EMITTER_WHITELIST_ENFORCE=1`** only after SHADOW tests pass for COMMODITY `multi_asset_cot` + any CRYPTO symbol-specific stack admitted by harness
5. **Do not trust** raw `by_asset_class_strategy` PF for symbol-specific `ml_enhanced_*` without walk-forward — aggregate class net (PF 0.66 CRYPTO policy_clean) is the honest headline

---

## Commands

```powershell
python tools/build_top10_strategies_per_class.py
python tools/strategy_harvest_round.py --phase cloud   # meta_debate
python tools/strategy_harvest_round.py --phase local   # strategy_harvest
```
