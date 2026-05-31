# Persona-Mix Portfolios — 5 Variants (Shadow Paper)

**Author:** Claude Opus 4.7
**Date:** 2026-05-31
**Surface:** `findtorontoevents.ca/audit/pf.html?key=<portfolio_key>`
**Status:** SHADOW PAPER ONLY — `requires_operator_promotion_to_live: true`
**CLAUDE.md goal:** #1 (phenomenal /audit performance across asset classes)

---

## 1. Methodology

### Data sources
- `https://findtorontoevents.ca/audit/data/ai_tournament_leaderboard.json` (Wilson95 LB pre-computed per fleet)
- `https://findtorontoevents.ca/audit/data/ai_tournament_model_summary.json`
- `https://findtorontoevents.ca/audit/data/ai_tournament_picks_latest.json` (4,419 picks total)

### Reliability gate
A `model_id` (persona fleet) is eligible if:
- `n_resolved >= 20`
- `WR >= 50%`
- `PF >= 1.1`

### Composite reliability score
```
composite = 0.5 * Wilson95_LB(WR) + 0.3 * min(PF_LB, 3.0)/3.0 + 0.2 * (1 - exp(-n/50))
```
Where:
- **Wilson95 LB** is the Brown (2001) lower bound on win-rate at 95% confidence — prevents small-sample WR brag.
- **PF_LB** is a conservative scalar built by scaling the observed PF by the ratio `wr_lb/wr` (no full bootstrap done here; leaderboard ships per-pf CI which is used implicitly).
- **Sample-size factor** asymptotes to 1.0 around n=200.

### Sharpe-proxy
`avg_pnl_pct / stdev_pnl_pct` per fleet (NOT annualized — per-pick risk-adjusted return). Used only for the Sharpe-optimized variant's sleeve weights.

### Retirement cross-check (PR #182)
PR #182 retired three SOURCE_SYSTEMS for resolver-artifact PF inflation: `cta_golden_cross_200`, `prediction_market_consensus`, `luxalgo_confluence`. These are **pick-level strategies**, NOT `model_id` (persona-fleet) labels. No fleet in this portfolio is retired. The block list is honored at the upstream `BLOCKED_SOURCE_SYSTEMS` layer in `audit_trail/quality_gates.py`, which already filters the picks that feed into `ai_tournament_picks_latest.json`.

---

## 2. Top-10 personas by composite reliability

| Rank | Fleet | n | WR | WR_LB | PF | PF_LB | Sharpe~ | Composite |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `deepseek_v4` | 208 | 57.7% | 50.9% | 3.46 | 3.05 | 0.48 | **0.751** |
| 2 | `deepseek_r1` | 133 | 63.2% | 54.7% | 2.99 | 2.59 | 0.39 | **0.719** |
| 3 | `gpt4o` | 137 | 60.6% | 52.2% | 2.93 | 2.53 | 0.44 | **0.701** |
| 4 | `grok3` | 311 | 55.9% | 50.4% | 2.25 | 2.03 | 0.31 | 0.654 |
| 5 | `claude_haiku_4_5` | 77 | 66.2% | 55.1% | 2.59 | 2.16 | 0.39 | 0.649 |
| 6 | `gpt5_mini` | 77 | 62.3% | 51.2% | 2.32 | 1.91 | 0.32 | 0.604 |
| 7 | `ring_261T` | 114 | 58.8% | 49.6% | 1.99 | 1.68 | 0.26 | 0.595 |
| 8 | `cursor_agent` | 105 | 59.0% | 49.5% | 1.95 | 1.64 | 0.28 | 0.587 |
| 9 | `command_a` | 94 | 59.6% | 49.5% | 1.61 | 1.34 | 0.20 | 0.551 |
| 10 | `kimi_direct` | 93 | 57.0% | 46.8% | 1.67 | 1.38 | 0.21 | 0.541 |

**Excluded** (raw WR/PF look great but n<20 → over-fit risk): `fireworks_qwen` (n=9 WR=88.9%), `groq_kimi_k2` (n=7), `gpt4o_mini` (n=10), `hyperbolic_llama` (n=10), `together_deepseek_v3` (n=9), `gemini_25_pro` (n=9), `claude_opus` (n=7). These are watchlist; promote to a portfolio only once n>=30 across at least 30 days.

### Per-asset-class best fleet (used by `diversified_per_class` variant)
| Class | Fleet | n | WR | WR_LB | PF |
|---|---|---:|---:|---:|---:|
| CRYPTO | `gpt4o` | 48 | 60.4% | 46.3% | 2.91 |
| EQUITY | `claude_haiku_4_5` | 15 | 80.0% | 54.8% | 9.07 |
| FOREX | `deepseek_r1` | 14 | 78.6% | 52.4% | 2.40 |
| COMMODITY | `command_a` | 13 | 84.6% | 57.8% | 5.14 |
| ETF | `grok3` | 43 | 83.7% | 70.0% | 15.30 |
| BOND | `claude_haiku_4_5` | 14 | 78.6% | 52.4% | 4.07 |

Per-class n is small for EQUITY/FOREX/COMMODITY/BOND (n=13-15) — flagged as watchlist below.

---

## 3. Portfolio variants

All five share: **starting NAV $100,000**, **equal-weight inside each fleet sleeve**, **all closed positions** for the eligible fleets. Status is `shadow_paper_only` and `requires_operator_promotion_to_live: true`.

### A. `portfolio_mix__conservative_top1` — control
- **Fleet:** `deepseek_v4` (full 100%)
- **n_positions:** 208
- **Metrics:** Total return 4.23% · PF 3.46 · MaxDD 0.36% · Sharpe~ 7.6 (daily-aggregated)
- **Rationale:** Single-fleet control. Highest composite reliability + largest n among eligible. Use as the benchmark every other variant must beat on Sharpe-after-cost.
- **Risk:** Single-fleet concentration risk; if DeepSeek API quality degrades, whole portfolio decays in lockstep. Sample is **money-ready by n** (>=100).

### B. `portfolio_mix__balanced_top3` — flagship
- **Fleets:** `deepseek_v4`, `deepseek_r1`, `gpt4o` (33.3% each)
- **n_positions:** 478
- **Metrics:** Total return 3.25% · PF 3.15 · MaxDD 0.11% · Sharpe~ 6.9
- **Rationale:** Equal-weight top-3 by composite. Two providers (DeepSeek + OpenAI). Halves single-provider risk vs A.
- **Risk:** Still provider-concentrated in DeepSeek (2 of 3 fleets). MaxDD is misleadingly low because position-level pnl is decoupled from a real correlation matrix.

### C. `portfolio_mix__aggressive_top5` — WR-LB weighted
- **Fleets:** top-5 by composite, weighted by `wr_lower_bound`
- **n_positions:** 866 (largest)
- **Metrics:** Total return 2.80% · PF 2.83 · MaxDD 0.10% · Sharpe~ 6.1
- **Rationale:** Maximum diversification across the proven fleets. Lower per-pick return (more "average") but maximum sample size makes Wilson LB convergence fastest.
- **Risk:** Lowest absolute return of the top-3 (A/B/C). Trade-off is robustness > return.

### D. `portfolio_mix__diversified_per_class` — per-class best
- **Composition:** see class table above (6 fleets, one per class, equal-weighted across classes)
- **n_positions:** 147
- **Metrics:** Total return 2.69% · **PF 4.86** · MaxDD 0.07% · Sharpe~ 10.2 (BEST Sharpe)
- **Rationale:** Hand-picks the best fleet per asset class. Class-equal-weighted (16.7% each).
- **Risk:** Per-class n is small (13-48 picks). **WATCHLIST** — do not promote to live until each class reaches n>=30 closed. The high Sharpe is partly an artifact of cherry-picking on small samples.

### E. `portfolio_mix__sharpe_optimized` — Sharpe-weighted top-4
- **Fleets:** `deepseek_v4`, `nvidia_minimax_m2`, `gpt4o`, `claude_haiku_4_5` (weighted by Sharpe-proxy)
- **n_positions:** 422
- **Metrics:** Total return 2.26% · PF 3.09 · MaxDD 0.09% · Sharpe~ 7.1
- **Rationale:** Tilts toward fleets with the best per-pick risk-adjusted return (low pnl variance). NVIDIA's MiniMax M2 (n=25, WR=64%, PF=2.53, Sharpe~0.46) made the cut despite n<30 because Sharpe is its strength.
- **Risk:** `nvidia_minimax_m2` is on the n=25 borderline; if its next 10 picks regress, drop it before promotion. **No regime gate is applied at the data layer** — the SKILL spec recommends a "only emit when class has positive 30d momentum" overlay at the scoring layer downstream.

---

## 4. Caveats + watchlist

| Variant | n_positions | Money-ready by n? | Notes |
|---|---:|---|---|
| A conservative_top1 | 208 | YES | Single-fleet risk only |
| B balanced_top3 | 478 | YES | Strong candidate for first live promotion |
| C aggressive_top5 | 866 | YES | Best diversified across providers |
| D diversified_per_class | 147 | WATCHLIST | Per-class n=13-48 |
| E sharpe_optimized | 422 | YES (minus nvidia_minimax_m2) | Drop minimax if next 10 picks regress |

### Things we did NOT do
- **No bootstrap PF CI** — used a scalar PF_LB = PF * (wr_lb/wr). The leaderboard ships a real bootstrap; production scoring should re-pull `pf_ci_lo` directly.
- **No regime gate** — Sharpe-optimized variant rationale references this but does not implement it; the downstream `calculate_smart_score` is the right place.
- **No cost model** — paper bps/slippage zeroed. Real-money promotion must subtract per-class friction (~3 bps EQUITY, ~10 bps CRYPTO, ~25 bps FOREX).
- **No correlation matrix** — MaxDD is computed from chronological closed-pnl sequence, not a real intraday portfolio NAV walk. Reported MaxDD is therefore optimistic.
- **No DSR / SPA test** — per the M-067 policy, no class is promoted to T2 without DSR/SPA passing. These portfolios are below that bar; they're paper trackers.

---

## 5. File manifest

- `audit_dashboard/data/pf_portfolio_portfolio_mix__conservative_top1.json`
- `audit_dashboard/data/pf_portfolio_portfolio_mix__balanced_top3.json`
- `audit_dashboard/data/pf_portfolio_portfolio_mix__aggressive_top5.json`
- `audit_dashboard/data/pf_portfolio_portfolio_mix__diversified_per_class.json`
- `audit_dashboard/data/pf_portfolio_portfolio_mix__sharpe_optimized.json`
- `reports/peer_claude-persona-mix-portfolios_2026-05-31.md` (this file)

Each JSON conforms to `audit_dashboard/pf.html` schema: `{portfolio, metrics_latest, nav_curve, positions}`. Live view URL pattern:
```
https://findtorontoevents.ca/audit/pf.html?key=portfolio_mix__balanced_top3
```
(requires FTP-deploy of `audit_dashboard/data/pf_portfolio_*.json` and `audit_dashboard/pf.html` to live).

---

## 6. Next steps (recommended)

1. **Operator review.** Pick one of A/B/C as the first candidate for live promotion. B is the recommended balance.
2. **30-day forward shadow.** Track these portfolios via `pf.html` before any real capital. Compare composite reliability of each variant on the new 30-day window.
3. **Regime gate.** Add a feature flag in the scoring layer that pauses sleeves whose 30d momentum is negative (per CLAUDE.md "mutate-before-kill" §`docs/MUTATION_THREE_AXIS_PROTOCOL.md`).
4. **Cost model.** Subtract per-class bps from the paper NAV walk before promotion.
5. **PR #182 sanity.** No fleet here trips PR #182 retire list, but if `BLOCKED_SOURCE_SYSTEMS` expands, re-run the build to drop newly-blocked source_systems from each fleet's pick stream.
