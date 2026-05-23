# Coverage Validation: 5000 rounds vs production strategies

## Verdict: ❌ NOT VALIDATED — 2.4% coverage, content still boilerplate

5000 rounds exist locally (post pull at 2026-05-09 12:00 UTC) but they cover only 24 distinct strategy names cycled 200-220 times each.

## Numbers

| metric | value |
|---|---|
| Total round dirs | 5000 |
| Distinct strategy names in rounds | **24** |
| Production strategies (leaderboard rows, distinct) | **1008** |
| Production strategies with fwd_trades > 0 (actually live) | 663 |
| Production strategies with fwd_trades >= 20 (meaningful sample) | 190 |
| Coverage of all production: 24/1008 | **2.4%** |
| Coverage of meaningful (n>=20): 24/190 | **12.6%** |
| Coverage of fully live: 24/663 | 3.6% |

## 24 strategy names currently cycled

| name | rounds | in production? |
|---|---|---|
| hurst_exponent_pairs | 220 | ✅ alpha_engine/untapped_strategies.py:195 |
| adaptive_bollinger_momentum | 220 | ⚠️ training-data ref only |
| liquidity_imbalance_reversal | 220 | ✅ alpha_engine/cerebrus_strategies.py:542 |
| turn_of_month_enhanced | 220 | ✅ alpha_engine/untapped_strategies.py:992 |
| vix_term_structure_signal | 220 | ✅ alpha_engine/untapped_strategies.py:1121 |
| put_call_ratio_contrarian | 220 | ✅ alpha_engine/untapped_strategies.py:517 |
| chatgpt_combined | 220 | ⚠️ source-system ref only |
| statistical_arbitrage_pairs | 220 | ❌ 0 hits |
| regime_aware_momentum | 220 | ❌ 0 hits |
| factor_exposure_balanced | 220 | ❌ 0 hits |
| confluence_strategy | 200 | ❌ generic |
| anti_overfit_gate | 200 | ❌ generic |
| long_term_equity_value | 200 | ❌ generic |
| forex_carry_trade | 200 | ⚠️ similar to carry_trade in forex_strategies.py:124 |
| crypto_vol_target | 200 | ❌ generic |
| equity_momentum | 200 | ❌ generic |
| options_max_pain | 200 | ❌ generic |
| macro_regime_filter | 200 | ❌ generic |
| sentiment_contrarian | 200 | ❌ generic — but real `st_fear_greed_contrarian` exists w/ PF 4.22 |
| alpha_engine_quant | 200 | ⚠️ similar to source_system "alpha_engine" |
| mercury2_ensemble | 200 | ⚠️ similar to source_system "mercury2" |
| kimi_rise_of_the_claw | 200 | ⚠️ similar to source_system "kimi_riseoftheclaw" |
| ml_battleground_v1 | 200 | ⚠️ similar to source_system "battleground" / ml_bg_* |
| dna_mutator_v2 | 200 | ⚠️ similar to dna_winner_picks family |

7 real defs, 9 ghost-similar, 8 generic/missing.

## Major gaps — REAL high-value production strategies NOT in rounds

Top live strategies by forward sample / edge that the 5000 rounds DO NOT document:

| strategy | n | wr_pct | pf | source |
|---|---|---|---|---|
| st_fear_greed_contrarian | 96 | 75.0% | 4.22 | forward_edge_audit_2026-05-02.json |
| cftc_cot_commercial_signal | 32 | 68.8% | 3.50 | forward_edge_audit_2026-05-02.json |
| atr_percentile_gate | 22 | 95.5% | 13.51 | forward_edge_audit_2026-05-02.json |
| rs-breakout-scout | 18 | 77.8% | 6.70 | forward_edge_audit_2026-05-02.json |
| mega_mutation_macd_rsi_m048 | 17 | 88.2% | 11.53 | forward_edge_audit_2026-05-02.json |
| crypto_keltner_compression_expansion_v1 | walk-forward proven | — | — | walk_forward_results.json |
| multi_period_rsi_confluence_eth/xrp | walk-forward robust | — | — | walk_forward_results.json |
| cta_commodity_momentum | live (just got 2x weight via top-7 #3) | — | — | alpha_engine/cta_bridge.py:274 |
| funding_rate_carry / funding_carry | 8.19 Sharpe | — | — | STRATEGY_WEIGHT_OVERRIDES |
| etf_dual_momentum / etf_sector_momentum / etf_faber_tactical | 3.0x weighted | — | — | STRATEGY_WEIGHT_OVERRIDES |
| signal_validation | Tier-2 PROVEN | n=139 | 57.6% | quality_gates.py:1217 |
| skyrocket_detector | live cron | — | — | JSON_PICK_SOURCES |
| ueps (16 active picks today) | live | — | concept_family=long_term_value | JSON_PICK_SOURCES |
| stocksunify2 | live (just wired in top-7 #1) | — | — | tools/sync_stocksunify2.py |
| tradingagents | live | — | — | JSON_PICK_SOURCES |

Plus 980+ more leaderboard rows un-documented.

## Content quality (unchanged from 200-round REVIEW_2026-05-09.md)

Sampled rounds 0001 (missing — generator uses 1-not-zero-padded), 2500, 5000:
- `strategy.md`: same template `"Base strategy definition for round N"` + Applicable Symbols block (only addition since hermes batch)
- No real entry/exit/risk parameters
- `performance-report.json`: still has the static fake stats
- `research-optimizations.md`: still identical template

## Recommendation

5000 rounds × 24 names is a worse problem than 200 rounds × 10 names — same content quality but 25× the disk + commit cost. **Ship Option A from the 200-round review:** delete `docs/strategy-audit-rounds/` and replace with a single auto-generated `docs/STRATEGY_REGISTRY.md` rendered from `dashboard_data.json::leaderboard` covering all 1008 production strategies (or top 190 by sample).

If hermes is set on per-strategy dirs, ship Option B: rewrite `scripts/generate_strategy_audit_rounds.py` to iterate the 190 meaningful strategies (one round per strategy, not per modulo cycle), pull `inspect.getsource()` + actual leaderboard row, write a real strategy.md + real performance-report.json. Then `docs/strategy-audit-rounds/<strategy_slug>/` instead of numbered dirs.

## Coordination needed

Hermes is the author of the round generator + the 5000 batch. Cross-pc message recommended:
- Stop current generation (no more batches)
- Decide A vs B
- If B, agree on slug-based naming so cycles can't repeat the same strategy

## Repro

```bash
python -c "
import os; from collections import Counter
base='docs/strategy-audit-rounds'
names=[]
for d in sorted(os.listdir(base)):
    p=os.path.join(base,d,'strategy.md')
    if not os.path.isfile(p): continue
    with open(p) as f: line=f.readline().strip()
    if 'Strategy:' in line: names.append(line.split('Strategy:',1)[1].strip())
c=Counter(names); print(len(names), 'rounds /', len(c), 'distinct')
for n,cnt in c.most_common(): print(f'  {n}: {cnt}')
"

python -c "
import json
d=json.load(open('audit_dashboard/data/dashboard_data.json'))
lb=d.get('leaderboard',[])
print('production distinct strategies:', len(set(r.get('strategy','') for r in lb if r.get('strategy'))))
print('with fwd_trades>=20:', len(set(r.get('strategy','') for r in lb if r.get('fwd_trades',0)>=20)))
"
```
