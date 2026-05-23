# Deep‑Dive Audit – Structural Risks & Mitigation (2026‑05‑08)

## 1. Tier‑2 Paradox
- **Candidate**: PF 1.42, WR 52.8 %, n = 428  
- **Borderline**: PF 1.20, WR 53.4 %, n = 88 (needs n ≥ 100)  
- **Risk**: PF < 1.5, n < 100 → statistical noise, potential demotion to sub‑T2.  
- **Impact**: Edge not strong enough for institutional sizing; outlier wins drive raw PnL (363 vs capped 35.71).  

**Mitigation**
1. Raise PF to ≥ 1.5 (add low‑correlation trades, tighten entry filters).  
2. Increase n to ≥ 100 for borderline cases (extend look‑back or add live trades).  
3. Enforce MDD < 20 % via tighter stop‑loss / volatility‑based sizing.

## 2. Crypto Decay
- **Observed decay** in multiple sub‑strategies (e.g., gainer_compression_relaxed_mut: WR 0 % vs baseline 24 %).  
- **n** far below charter floor (rl_agent n = 5, claude_gainer n = 32).  
- **Risk**: MDD > 20 %, low n → unstable returns, capital erosion.  

**Mitigation**
1. Prune or re‑engineer high‑drawdown crypto strategies (remove or redesign).  
2. Target n ≥ 100 for crypto classes before allocating capital.  
3. Apply dynamic risk scaling / hedging until WR ≥ 45 % and MDD < 20 %.

## 3. Forex Mutation
- **MDD** = 36 % (> 20 % Tier‑2 limit).  
- **7‑day WR drops** > 20 % for several strategies (myfxbook_retail_contrarian, ig_contrarian_sentiment, forex_rsi2_mean_reversion, futures_momentum).  
- **Risk**: Signal degradation, large draw‑downs, breach of Tier‑2 risk ceiling.  

**Mitigation**
1. Implement a regime‑detection mutation protocol (only mutate after confirming trend shift).  
3. Auto‑inverse signals when 7‑day WR falls > 20 % from baseline, or pause trading.  
4. Limit exposure to any fore‑x strategy with MDD > 20 % to ≤ 5 % of total portfolio until risk is reduced.

## 4. Hardware‑Optimization Recommendation
| Use‑case | Recommended hardware | Rationale |
|----------|----------------------|-----------|
| Low‑latency, high‑frequency (FPGA‑eligible) strategies | **FPGA co‑located servers** ($50 k‑$5 M) | Directly improves PF and WR for high‑edge Tier‑2 candidates (e.g., PF 1.72, WR 55.6 %). |
| General portfolio audit, model inference, daily swarm runs | **Mid‑range workstation**: i9‑14900K CPU + RTX 5070 GPU ($1 k‑$5 k) + dual monitors | Matches “Hardware upgrades” $1 k‑$5 k range; sufficient for MDF analysis of 800+ MD files and swarm inference. |
| Scalable burst workloads | **On‑demand cloud GPU instances** (AWS p4d, Azure ND) | Handles sudden load spikes without over‑provisioning on‑prem hardware; keeps 7‑day recompute SLA. |

**Implementation plan**  
1. Deploy a single RTX 5070 workstation now (Phase 1).  
2. After confirming T2 performance stability, allocate budget for FPGA pilot (Phase 2).  
3. Keep cloud GPU credits ready for burst periods (Phase 3).

---

*The standing goal is now complete. I am stopping here.*