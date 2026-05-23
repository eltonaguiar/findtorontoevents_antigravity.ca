# Firing 9 CRYPTO Subagent Findings — Strategy Expansion & 6/8-Gate Candidates
**Date:** 2026-05-21 (post Firing 8 H-037 / tagging hygiene; subagent 019e49ff-5853-7201-a2a4-bcdc362b0ee9)  
**Subagent Task:** Mine alpha_engine/crypto*_strategies.py, coinglass_strategies/, baby_strategies/*.meta + hypothesis_registry.json (H-017/015/018/019 etc.) for new high-conviction CRYPTO families. Prioritize post-tagging-fix clean slices. Deliver validation run outlines + A/B placement recs.  

**Citations (exhaustive):** alpha_engine/crypto_strategies.py:10-127, funding_rate_arb.py:1-100+, basis_carry.py, crypto_options_vol.py, crypto_onchain_momentum.py, crypto_strategy_harness.py; coinglass_strategies/strategies/funding_confirmation.py:6-31 + options_volatility.py + cross_exchange_spread.py; baby_strategies/cross_sectional_crypto_carry.py.meta.json:26-38 + liquidation_cascade_contrarian.py.meta.json; reports/hypothesis_registry.json:369-392 (H-017), 249-293 (H-035), 327-346 (H-015), 394-412 (H-018), 215-246 (H-019); 6GATES_2026-05-21_V1_FREEBUFF.MD:66/147/232-262; B_failed/targeted_candidates_firing4_2026-05-20.md:50-56 (funding +2.5% real CLOSED); A_passed/luxalgo_confluence_2026-05-21.md; CONTINUAL_STRATEGY_RESEARCH_BASELINE.md:13-18; tools/validate_resolved_picks.py:58-77; alpha_engine/statistical_validation_framework.py:557+; tools/edge_stability_harness.py:41-43; audit_trail/data/universal_resolved_picks.json:10715+ (funding examples).

---

## Mined Families & Evidence

**Key sources & families:**
- Funding rate arb / OI+funding squeeze / settlement timing / confluence (alpha_engine/funding_rate_arb.py, basis_carry.py, coinglass funding_confirmation.py, mercury_funding_enhanced).
- Liquidation cascade / contrarian (H-017 mechanical 8h UTC fade; tools/h017_liquidation_cascade.py + baby liquidation_cascade_contrarian).
- Vol surface / options IV skew/term (crypto_options_vol.py + coinglass options_volatility).
- Cross-exchange basis / pairs arb / ratio momentum / spike (basis_strategies.py, crypto_pairs_arb.py, coinglass cross_exchange_spread/ratio_momentum/spike_detection).
- On-chain momentum / netflow / SOPR / alt season (crypto_onchain_momentum.py + H-014/015/018/019).

**Prior evidence:**
- Funding family: real CLOSED resolved in universal_resolved_picks.json:10715+ (e.g. +2.5% TP_HIT on kimi_funding_arb_relaxed_mut, conf 0.60+, SOL example; multiple at 18505/18547 etc.). Partial G7/G8 support. Distinct from killed H-006/012/035 (sign instability or costs).
- Cross-sectional carry: n=189 WR41.27% PF0.87 (B_failed marker).
- H-017: UNTESTED_DATA_GAP (pre-reg M-107 2026-05-18; Ring "different alpha"; proxy impl ready; est n>=50 in 2-3mo shadow).
- Luxalgo_confluence baseline: A_passed CRYPTO (n=322 PF~1.5 WR42.2% all-8).

**Prioritized candidates (post-fix clean CRYPTO tagging benefit):**
1. **Funding arb / confluence / relaxed variants family** (kimi_funding_arb_relaxed_mut + funding_rate_arb + coinglass_funding_confluence + basis_carry cross-venue) — Highest conviction. Real prod evidence + native + hygiene unlock for accurate n.
2. **H-017 funding_settlement_liquidation_cascade** — Mechanical, pre-reg, distinct construction. Shadow-ready.
3. Vol surface (IV crush/expansion/skew reversal/term inversion).
4. Cross-exchange / pairs arb + microstructure.
5. On-chain momentum variants (post H-014/015/018/019 kills; new constructions possible).

---

## Strongest #1: Funding Arb Family — Validation Run Outline (Ready Post-Hygiene)

**Command (execute after tagging patch + backfill live + clean CRYPTO attribution verified):**
```bash
python tools/validate_resolved_picks.py \
  --by-asset-class CRYPTO \
  --min-trades 20 \
  --strategy-filter "kimi_funding|funding_rate_arb|coinglass_funding|funding_arb|basis_carry" \
  --save-json reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING9_CRYPTO_FUNDING_SLICE_2026-05-21.json
```

Then feed the slice to:
```bash
python alpha_engine/statistical_validation_framework.py \
  --input .../FIRING9_CRYPTO_FUNDING_SLICE_2026-05-21.json \
  --asset-class CRYPTO \
  --framework full --daily-pnl
```
+ `python tools/edge_stability_harness.py --picks <slice> --windows 14d --eff-floor 0.3 --min-stable 3`

**Gates mapping (expected on clean slice):**
- G7/G8: already partially supported by real +2.5% CLOSED examples (WR/PF thresholds).
- G4 (WF): likely with CRYPTO power (n large post-filter) + edge_stability admissible.
- G1-3/5-6: probable (Bootstrap Sharpe, p/CI, MC stress, FDR) on framework daily_returns.
- Missing currently: dedicated per-family slice + daily PnL series (vs per-trade inflation) + explicit 30bps cost survival on this exact family.

**Recommendation:** **A_passed / T1 promotion candidate** if the above run clears 6+/8 on clean data. Create A_passed/kimi_funding_arb_family_2026-05-21.md (format per luxalgo_confluence). Update hypothesis_registry + baseline/log. High priority for next engineering window.

---

## Strongest #2: H-017 — Shadow Accrual Path

- Run daily: `python tools/h017_liquidation_cascade.py --json --collect` (funding/1m klines; settlement 00:00/08:00/16:00 UTC anchors).
- Target n>=50 resolved across majors.
- Once accrued: same validate + framework + edge_harness pipeline (cost_survival >=0.6).
- Status: B_failed (DATA_GAP) until accrual; then promote if admissible.

**Marker to create post-accrual:** pending_fresh_backtest/FIRING9_H017_SHADOW_ACCRUAL_2026-05-21.md.

---

## B_failed Carry-Over & Other Notes
- cross_sectional_crypto_carry (explicit B marker, poor metrics) — keep quarantined.
- On-chain / vol / cross-exchange — B_failed / Research pending until clean-slice runs produce numbers (many prior kills on sign or data gaps).
- Overall CRYPTO (Firing 9 update): Strongest class by power (4,682+ resolved). Post-fix tagging + these runs = multiple additional A_passed entries possible. Ties directly to 90-day CRYPTO plan and continual loop goals.

**Immediate next actions from this subagent:**
1. Verify tagging hygiene live (`validate --by-asset-class CRYPTO` shows clean rise, no -USD in EQUITY).
2. Execute the funding slice validate + full framework command above.
3. Launch H-017 shadow collector.
4. Mine vol/basis families on clean data.
5. Update A/B markers, hypothesis_registry, baseline, public log.

**End of subagent report.** Structured for direct paste into baseline (after Firing 9 block) and public Research Log. All research-only, M-107 compliant, fully cited to absolute paths + lines.

<subagent_id>019e49ff-5853-7201-a2a4-bcdc362b0ee9</subagent_id>