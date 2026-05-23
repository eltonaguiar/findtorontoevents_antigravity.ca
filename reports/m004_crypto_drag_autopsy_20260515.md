# M-004 CRYPTO Drag Autopsy — 2026-05-15

**Source:** `audit_dashboard/data/dashboard_data.json` generated_at 2026-05-15T20:20Z
**CRYPTO aggregate:** PF=1.30, WR=46.1%, n=8122 (resolved_n = wins+losses post `_is_valid_resolved_pick` filter)

> ## ⚠️ CORRECTION 2026-05-17 — DO NOT ACT ON THE "HIGH-PF STARS" SECTION
>
> A reproduction-grade audit (`reports/crypto_edge_artifact_audit_2026_05_17.md`)
> found this report's "High-PF stars" table is **wrong**:
> - The `closed` counts are `closed_picks`, NOT valid resolved trades.
>   `kimi_signal_tracking` real verified sample is **n=21** (1182 of 1203 are
>   `excluded_closed`), not 1198 — a 57× overstatement.
> - `aggregated_picks` is a **loser**, not a star: `system_clean_metrics`
>   shows PF 0.54 / avg -0.70 / total PnL -82.55 — contradicting the
>   `systems[]` PF 5.60 cited here.
> - The high WR/PF is largely a **fixed-TP artifact**: aggregated_picks 70%
>   of wins land at exactly +3.5%, signal_validation 81% at exactly +3.0% --
>   wins credited at nominal TP, not verified exit fills.
>
> **The recommendation to "scale kimi_signal_tracking / aggregated_picks into
> active picks" is withdrawn -- it rests on inflated sample sizes.** Use
> `resolved_picks` (not `closed_picks`) as n, and require n>=100 valid resolved
> before promoting any system. See the 2026-05-17 audit for full evidence.

## quan_engine post-5% cap (PRIMARY QUESTION)

`quan_engine` current: closed=555, WR=33.2%, PF=1.25

**Verdict: Cap is working.** PF=1.25 (>1.0) means the volume-capped picks are slightly profitable.
Prior description of "PF 0.70 drag" reflected the pre-cap / full-volume state. At 5% cap, quan_engine
contributes minimal drag and no emergency action needed.

Volume sync: `alpha_engine/per_source_volume_cap.py` and `alpha_engine/quarantine_manifest.json`
both confirm 5% CRYPTO cap — SYNCED (no desync).

## Real CRYPTO drags (systems with PF < 1.0, n > 20)

| System | closed | PF | WR% | Status |
|---|---|---|---|---|
| rapid_fire | 609 | 0.83 | 37.4% | Noise filter active (score<10 rejected); historical picks inflate closed count |
| copy_trader_highscore | 343 | 0.89 | 36.2% | Blacklisted (`BLACKLISTED_STRATEGIES` line 1540) — historical picks remain |
| alpha_engine_fast | 299 | 0.62 | 43.2% | BLOCKED for CRYPTO (`BLOCKED_ASSET_STRATEGY_PAIRS` line 1649) — historical picks remain |
| super_signals | 159 | 0.81 | 36.0% | Partially handled (line 2492) |
| paper_trading | 103 | 0.92 | 34.8% | Simulation system — should be excluded from verdict metrics |
| dna_rapid_fire_mutations | 52 | 0.78 | 33.3% | No specific block — small n |
| mercury2_fast | 32 | 0.07 | 42.9% | Tiny n, very low PF — investigate or block |
| mutation_lab | 22 | 0.36 | 18.2% | Tiny n — incubator system, acceptable |

## High-PF stars (CRYPTO systems to scale)

| System | closed | PF | WR% |
|---|---|---|---|
| kimi_signal_tracking | 1198 | 5.80 | 76.2% |
| aggregated_picks | 424 | 5.60 | 76.6% |
| signal_validation | 562 | 4.70 | 61.0% |
| ml_crypto_pred_v12 | 123 | 2.53 | 55.6% |
| claude_gainer | 963 | 2.23 | 56.2% |

## Largest-volume diluters (PF < T2 but > 1.0)

| System | closed | PF | WR% | Note |
|---|---|---|---|---|
| baby_strats_forward | 6289 | 1.38 | 45.8% | Largest CRYPTO volume; 9 overfit strategies blocked 2026-05-15 |
| luxalgo_filters | 1862 | 1.12 | 44.3% | Capped 10% via quarantine_manifest (2026-05-15); still dilutive |
| stocks_competition | 1902 | 1.32 | 49.3% | Below T2 WR floor |

## Path to CRYPTO T2 (PF≥1.5, WR≥50%, n≥100)

1. **Blocked systems age out**: alpha_engine_fast, copy_trader_highscore are blocked — their historical
   picks remain in resolved_n but new picks won't be added. PF should improve as the pool ages.
2. **baby_strats overfit block**: 9 strategies blocked 2026-05-15 should improve PF over next 30-60d.
3. **Scale stars**: kimi_signal_tracking (PF=5.80) and aggregated_picks (PF=5.60) are producing elite
   CRYPTO results — wiring these into active picks path would lift aggregate PF.
4. **mercury2_fast (PF=0.07)**: P2 investigation needed — this is catastrophically bad. Very small n=32
   but PF near zero suggests systematic error (wrong price reference, slippage bug, etc.).

## Actions taken this session

- M-004 verified: quan_engine PF=1.25 post-5%-cap — no emergency action needed
- 9 baby_strats overfit blocks applied to quality_gates.py (commit e5f4d4a52a)
- Volume cap synced: per_source_volume_cap.py = quarantine_manifest.json = 5% CRYPTO

## P2 recommendations

- Block `dna_rapid_fire_mutations` CRYPTO (PF=0.78, n=52) after mutation protocol
- Investigate `mercury2_fast` PF=0.07 (n=32) — likely a price reference bug
- Exclude `paper_trading` from verdict-grade resolved_n (it's simulation, not live)
