# Swarm Master Synthesis — 3-Round Multi-Model Review — 2026-05-14

Engines: deepseek (deepseek-chat) + xai (grok-3) + cerebras (gpt-oss-120b)
Rounds: A (Crypto GitHub), B (Gap Analysis), C (Proactive Monitoring)
Est. cost: ~$0.20 total | Est. time: <3 min per round

---

## Cross-Round Consensus (all 3 engines, all 3 rounds)

### C0 — Capital Protection Emergency (before ANY optimization)

> **Concept drift KS_D = 6.6× critical with no automated pause = sizing blindly into regime collapse.**
> Every engine in every round independently flagged this first. This is not a P1. It is P0.

Action: Wire `passes_active_gate` drift auto-pause when `KS_D > 3× critical`.
Files: `audit_trail/quality_gates.py`, `audit_dashboard/data/dashboard_data.json::hf_stats.concept_drift`
ETA: same-day code change.

### C1 — Source Quality is the CRYPTO Bottleneck

> **quan_engine (18% vol, PF 0.70) + unknown source (7%, PF 0.35) drag elite sub-strategies from PF 2-58 down to system PF 1.26.**
> All 3 rounds flag this. The problem is not the ML models — it's uncontrolled bad-source emission.

Action: Hard 5% volume ceiling on quan_engine in `production_scanner.py`.
Target: CRYPTO system PF 1.26 → ~1.6 within 30 days post-ceiling.

### C2 — Triple-Barrier Labeling (Round A unanimous)

> **Fixed-horizon labels are likely the root cause of confidence-band inversion and WR suppression.**
> Switch to triple-barrier (mlfinlab) + fractional differencing for features.

Repo: https://github.com/hudson-and-thames/mlfinlab (BSD license)
Priority: P1 (after P0 infrastructure fixes)

### C3 — BOND Fix = FRED + Yield Curve Strategies (Round B consensus)

> **n=18 is the entire BOND problem. Not model quality. Not gates. Just no signal generation.**
> Ken French bond factor data + FRED yield curve = add 4-6 strategy types immediately.

Free source: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
Free source: https://fred.stlouisfed.org (FRED_API_KEY already referenced in codebase)

### C4 — Four-Tier Circuit Breaker (Round C consensus)

> **All 7 documented failure modes would have been contained within 24h by proposed checks.**
> Current monitoring is fully reactive. Need proactive circuit breakers.

---

## Consolidated Priority Queue (post-swarm)

| Priority | Action | Source | Expected Impact | Effort |
|----------|--------|--------|-----------------|--------|
| **P0** | Concept drift auto-pause (KS_D > 3× critical) | All 3 rounds | Capital protection | 2h |
| **P0** | quan_engine hard 5% volume ceiling | Round A+B | CRYPTO PF +0.30-0.50 | 1h |
| **P0** | Fix regime tagging bug (stamp at emission) | Round B+C | Unblocks monitoring | 1h |
| **P0** | goldmine_stocks score +12→-30 correction | Round B | Score integrity | 30m |
| **P1** | VIX regime gate: set env var (no code) | Round B | EQUITY PF 2.82→4.55 | 5m |
| **P1** | Hourly open-bloat check (>90% → pause emissions) | Round C | WR integrity | 3h |
| **P1** | Daily KS_D + PSI drift check with auto-alert | Round C | Drift early warning | 4h |
| **P1** | COT expansion to 20+ CFTC symbols | Round B | COMMODITY WR +5-10pp | 1d |
| **P2** | Triple-barrier labeling (mlfinlab) | Round A | CRYPTO WR +5-10pp | 2d |
| **P2** | BOND yield-curve strategies (FRED + Ken French) | Round B | BOND n 18→100+ | 3d |
| **P2** | CRYPTO symbol expansion (13→30+ pairs) | Round A | CRYPTO n diversity | 1d |
| **P2** | CoinGlass funding rate integration | Round A | CRYPTO signal quality | 1d |
| **P3** | Change-point regime detection (ruptures lib) | Round A | Regime-adaptive sizing | 2d |
| **P3** | Position sizing (volatility-scaled Kelly) | Round B | MDD -30-50% | 3d |
| **P3** | Portfolio-level MDD circuit breaker | Round C | T1 MDD criterion | 2d |
| **P4** | Canary strategy infrastructure per class | Round C | Early warning system | 3d |
| **P4** | Confidence calibration (isotonic regression) | Round A | Re-enable high-conf | 2d |

---

## Per-Asset-Class Roadmap (swarm-validated)

### CRYPTO — Current PF 1.26 → Target 2.0+
1. P0: quan_engine ceiling (5%) — eliminates biggest drag
2. P0: Drift pause gate — stops sizing into KS_D=6.6× regime
3. P1: CoinGlass funding rates + open interest features
4. P2: Triple-barrier labeling + CPCV validation
5. P2: Expand to 30+ symbols (SOL, ARB, OP, SUI, NEAR, AVAX)
Timeline: 30d to PF ~1.6 (P0+P1), 90d to PF ~2.0 (P2 full)

### COMMODITY — Current PF 2.08 → Target 2.5+
1. P0: Fix COT timing lag guard (PR #941 — verify live)
2. P1: COT expansion 5→20+ CFTC commodity classes
3. P1: Add roll-yield strategy (momentum × carry double-sort)
4. P2: Weather → soft commodities (NOAA GFS + WASDE, IDEA-H)
Timeline: 30d to consistent Tier 1 on WR (currently WR 46.9%, need 55%)

### EQUITY — Current PF 1.42 → Target 2.0+
1. P1: VIX gate env var flip (immediate, zero code)
2. P1: Factor diversification (Fama-French SMB/HML + 12-1m momentum)
3. P1: Expand kimi scanner to 500+ S&P tickers
4. P2: Earnings momentum (EPS surprise + SUE factor, EDGAR 8-K)
Timeline: PF 1.42 → 2.82+ within days (VIX gate), → 4.55 with full filter

### ETF — Current PF 1.20, WR 55.2%, n=87 → Target n≥200
1. P1: Expand to 100+ ETF universe (sector, thematic, international)
2. P1: Dual momentum strategy (12-1m relative + trend)
3. P2: Factor tilts (value/momentum/quality ETFs: VBR, MTUM, QUAL)
Timeline: 60d to n≥100; 90d to n≥200

### BOND — Current PF 1.72, n=18 → Target n≥200
1. P1: FRED yield curve slope strategy (2s10s inversion signals)
2. P1: Treasury futures ZN/ZB/UB addition to bond_scanner.py
3. P2: Ken French bond factor carry strategy
Timeline: 90d to n≥100 (viable), 6m to n≥200

### FOREX — Current PF 0.27 → DEAD / Mutation Protocol
- 3-axis mutation per docs/MUTATION_THREE_AXIS_PROTOCOL.md
- Do NOT re-enable sizing until mutation finds profitable sub-niche

---

## Free GitHub Repos to Integrate (Round A top picks)

| Repo | URL | Use Case | Effort |
|------|-----|----------|--------|
| mlfinlab | github.com/hudson-and-thames/mlfinlab | Triple-barrier, fractional diff, CPCV | Medium |
| ruptures | github.com/deepcharles/ruptures | Change-point regime detection | Low |
| alibi-detect | github.com/SeldonIO/alibi-detect | PSI + drift auto-retrain triggers | Low |
| cryptofeed | github.com/bmoscon/cryptofeed | Real-time funding rates, OI, trades | Medium |
| pandas-ta | github.com/twopirllc/pandas-ta | 130+ indicators (replace manual) | Very Low |
| QuantStats | github.com/ranaroussi/quantstats | Pro audit reports, benchmarking | Very Low |
| vectorbt | github.com/polakowo/vectorbt | 50-100× faster crypto backtests | Medium |

---

## Implementation Order (starting now)

**Today (P0 code changes):**
1. Concept drift auto-pause in quality_gates.py
2. quan_engine 5% volume ceiling in production_scanner.py
3. Fix regime tagging at emission in production_scanner.py
4. goldmine_stocks source score correction

**Tomorrow (P1 env/config changes):**
5. VIX regime gate env var in GitHub Actions secrets
6. Daily KS_D monitoring cron job

**This week (P1 expansions):**
7. COT expansion to 20+ CFTC symbols
8. ETF universe expansion to 100+

---

*Generated by 3-engine swarm (deepseek + xai + cerebras) | 2026-05-14*
*Source reports: swarm_crypto_github_tips_20260514.md, swarm_gap_analysis_vs_hedgefund_20260514.md, swarm_proactive_monitoring_20260514.md*
