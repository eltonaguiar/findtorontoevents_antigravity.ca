# Gaps and Opportunities Audit — 2026-04-18

**Scope:** Four-part performance and strategy-inventory audit against [alpha_engine/data/closed_picks.json](../alpha_engine/data/closed_picks.json) (n=4,391 closed picks; full file window 2026-03-16 → 2026-04-18; last 90 d window identical to full file because the alpha_engine closed stream only goes back ~33 days).

**Analysis tooling:** Pure-Python aggregation ([_tmp_audit.py](../_tmp_audit.py)); raw output persisted to [docs/_audit_2026_04_18_data.json](_audit_2026_04_18_data.json).

**Schema notes / data caveats:**
- "Score" candidates found in the schema: `confidence` (0.45–0.95, covers 4,280 / 4,391 picks), `elite_score` / `ml_composite_score` / `method_a_score` (all three only populated on the most recent 500 picks, range 5.5–71.0). There are **no picks with raw score ≥ 85 or ≥ 95 on the elite scale** in the file — the task's threshold "score ≥ 85 / ≥ 95" therefore had to be reinterpreted as `confidence ≥ 0.85` / `confidence ≥ 0.95`. Flagged where it matters.
- `exit_reason` values observed: `TIME_EXIT`, `SL`, `TP`, `trail`, blank. `won` is imputed from `pnl_pct > 0` except where `exit_reason` explicitly says SL/TP.
- Gated source systems (`_HIDDEN_SYSTEMS`, `_FRESHNESS_REQUIRED_HOURS` in [audit_trail/dashboard_generator.py](../audit_trail/dashboard_generator.py)) **do not appear in closed_picks.json at all** — that file is written by `alpha_engine` / `quan_engine` / `rapid_fire` only. Dormant-systems analysis is therefore "not reproducible from closed_picks.json alone" — see Audit 4 caveat.

---

## 1. Lowest-Performing Assets

### Top-line (90 d, n ≥ 20)

| Rank | Symbol | n | WR | Avg PnL % | Total PnL % |
|---:|:--|---:|---:|---:|---:|
| 1 | MATICUSDT | 889 | 0.0% | -0.150 | **-133.35** |
| 2 | KASUSDT | 402 | 35.6% | -0.270 | **-108.53** |
| 3 | UUSDT | 26 | 0.0% | -2.269 | -59.00 |
| 4 | BTCUSDT | 466 | 35.6% | -0.120 | -56.06 |
| 5 | DOTUSDT | 220 | 30.5% | -0.242 | -53.30 |
| 6 | TAOUSDT | 421 | 37.3% | -0.110 | -46.31 |
| 7 | ICPUSDT | 239 | 30.5% | -0.181 | -43.30 |
| 8 | ETHUSDT | 101 | 28.7% | -0.268 | -27.11 |
| 9 | ONDOUSDT | 78 | 21.8% | -0.331 | -25.78 |
| 10 | RENDERUSDT | 190 | 33.7% | -0.123 | -23.33 |

### Analysis

- **MATICUSDT is the single biggest drain: -133 PnL-% on 889 trades with a 0% win rate.** Every pick exits flat-to-negative; 786/889 are `strategy=null` from `source_system=quan_engine` with a mean PnL of -0.15%, i.e. the position pays commission/slippage and times out. This is not a bad edge — it is a dead asset (MATIC was renamed POL in 2024; our entries may be executing on a phantom ticker or on near-zero-volume illiquidity). **Fix: blocklist MATICUSDT at the universe layer immediately.**
- **UUSDT (n=26, -2.27 avg PnL, 0% WR)** is the highest-per-trade bleeder. 18/26 come from `volume_spike_breakout` and 6/26 from `stochrsi_macd_combo`, both at 0% WR — a symbol-specific microstructure mismatch (UUSDT is a low-liquidity meme on Binance).
- **quan_engine dominates every single top-10 loser except UUSDT** (which is `rapid_fire`). `quan_engine` is NOT in `_HIDDEN_SYSTEMS` and NOT in `_FRESHNESS_REQUIRED_HOURS` — so it continues to publish picks into the consensus. The [inverse-wrapper design](superpowers/specs/2026-04-14-inverse-wrapper-design.md) *already specifies* quan_engine as its first caller (2.8% WR on n=36 was the prior read). This audit re-confirms that finding at n≈2,000+.
- **Strategy drag within losers is almost entirely the `strategy=null` bucket** (i.e. the default / unlabeled `quan_engine_scalp` path). The only labeled strategies that matter are `quan_engine_scalp` (consistently 20–33% WR, always negative) and two tiny pockets (`volume_spike_breakout`, `stochrsi_macd_combo`) on UUSDT/TAOUSDT.

### Recommended actions

1. **Universe blocklist:** MATICUSDT, UUSDT, KASUSDT, ONDOUSDT. Estimated recovered PnL: **+326%** in 90 days.
2. **Wrap `quan_engine` in the inverse wrapper** for `conf < 0.70` band per [inverse-wrapper-design.md](superpowers/specs/2026-04-14-inverse-wrapper-design.md) — there is no sign this has shipped yet.
3. **Add symbol-level kill switch** to the dashboard generator's gating alongside `_HIDDEN_SYSTEMS`.

---

## 2. High-Conviction Picks That Performed Poorly

### Top-line

| Tier | n | WR | Avg PnL % | Total PnL % |
|:--|---:|---:|---:|---:|
| HC (confidence ≥ 0.85) | **2** | 100.0% | +0.614 | +1.23 |
| non-HC (confidence < 0.85) | 4,278 | 28.9% | -0.136 | -580.60 |

### Analysis

- The "high conviction" bucket is **essentially empty** — only 2 picks in 4,391 cleared `confidence ≥ 0.85`, and both won. This is a **calibration artefact, not evidence of HC edge.** The `confidence` field is compressed into a narrow band (0.45–0.95) and almost all picks fall into 0.55–0.72.
- `confidence ≥ 0.95`: 1 pick, won. No calibration-failure cases exist in the file at that threshold.
- Using the elite score (populated only on 500 recent picks, max observed 71.0) the "top 50 by elite_score" bucket has:
  - median pnl_pct = **-0.021%**
  - hit rate = **13/50 = 26%**
  - elite_score range on the top-50: 49.5 – 71.0 — meaning the highest-confidence quintile of the *new* scorer is still losing.
- `elite_score ≥ 95` or `confidence ≥ 0.95` picks that hit SL: **zero** (no picks exist at that level).

### Recommended actions

1. **The HC threshold is mis-set.** At `confidence ≥ 0.85` only 0.05% of picks qualify. Either recalibrate the confidence output range, or shift "HC" definition to use `elite_score` quantiles once the new scorer has full coverage.
2. **Promote `elite_score` to canonical** and backfill the older 3,891 picks so this audit can be re-run at meaningful scale.
3. **At the current elite-scorer high band (≥60), hit rate is 26%.** That is calibration failure — see §3.

---

## 3. Top-Scored Picks vs. Outcomes

### Top-line

| Metric | Value |
|:--|---:|
| Top-50 by `confidence` — median pnl_pct | 0.000% |
| Top-50 by `confidence` — mean pnl_pct | +0.062% |
| Top-50 by `confidence` — hit rate | **24 / 50 = 48%** |
| Top-50 by `confidence` — conf range | 0.742 – 0.950 |
| Top-50 by `elite_score` — median pnl_pct | -0.021% |
| Top-50 by `elite_score` — hit rate | **13 / 50 = 26%** |
| Spearman ρ (confidence, pnl_pct) | **+0.145** (n=4,280) |
| Spearman ρ (elite_score, pnl_pct) | **+0.408** (n=500) |

### Analysis

- **`confidence` is weakly predictive** (ρ=0.145, p statistically significant at n=4,280 but economically tiny). The task's criterion — "if correlation <0.1 or negative, scoring is broken" — is **marginally not met**; `confidence` is not broken but is near-useless as a ranker.
- **`elite_score` is genuinely predictive** (ρ=0.408) on its 500-pick sample. This is the right score to promote — but its hit-rate on its own top-50 is still only 26%, so the signal is directional (higher = better) but the *absolute* calibration at the top band is a disaster: 74% losers.
- Top-50 by `confidence` includes the narrow HC band and still only hits 48% — a coin flip.
- There are **no `elite_score ≥ 95` or `confidence ≥ 0.95` SL hits** in the file because no picks reach those thresholds. The calibration-failure list requested in the prompt is therefore empty.

### Recommended actions

1. **Deprecate `confidence` as a ranking input** (ρ < 0.15). Use it only as a softmax/temperature input, not a gating threshold.
2. **Recalibrate `elite_score`** via isotonic regression on the 500-pick training sample: the ordering is correct but the absolute probability is off.
3. **Re-run this audit after `elite_score` coverage > 2,000 picks.**

---

## 4. Dormant Strong Systems + MD Strategy Inventory

### 4a. Dormant strong systems — data caveat

**Reproducibility flag:** The gated system sets (`_HIDDEN_SYSTEMS` n=28, `_FRESHNESS_REQUIRED_HOURS` n=47 in [dashboard_generator.py](../audit_trail/dashboard_generator.py#L3652-L3755)) contain names like `ml_bg_system_a…f`, `ai_challenge_*`, `revival_*`, `macd_dna_mutations`, `neat_neural`, `prop_firm_strategies`, etc. **None of these appear as `source_system` values in `closed_picks.json`.** closed_picks.json is exclusively populated by `alpha_engine`, `quan_engine`, `rapid_fire`, and `prediction_market_agents` (1 pick).

Conclusion: **Historical WR / Wilson LB for gated systems cannot be computed from this file.** The canonical source for that analysis is `audit_dashboard/data/dashboard_data.json → picks.recent_closed` (n=3,500), which [DNA_MUTATION_WINNERS_2026-04-14.md](DNA_MUTATION_WINNERS_2026-04-14.md) already uses.

From [dashboard_generator.py](../audit_trail/dashboard_generator.py) comments, the **likely dormant-but-strong candidates** (based on documented reason for gating) are:
- `ai_challenge_claude`, `ai_challenge_grok`, `ai_challenge_kimi_moonshot`, `ai_challenge_antigravity`, `ai_challenge_mercury` — retired 2026-04-18 only because "tournament ended at Round 5 on 2026-04-12 and no Round 6 generator exists." If any of these had Wilson LB > 50% historically, **restarting a Round 6 generator is a cheap win**.
- `revival_*` (12 systems) — orphaned 2026-04-11 because no workflow writes their paths. If any were strong before orphaning, **re-attaching a writer workflow recovers them at zero ML cost**.
- `prop_firm_strategies`, `proven_strategies`, `ml_bg_system_[a-f]` — freshness-gated at 72 h because of a 2026-04-11 mass commit. These are explicitly documented as "can re-engage automatically if a writer produces a fresh file" — **diagnose the writer, don't rebuild the signal**.

**Recommended follow-up audit:** Re-run this section against `audit_dashboard/data/dashboard_data.json` which has the needed `source_system` coverage.

### 4b. IDE-dropped .MD strategy files (Apr 2026)

Ranked 1–5 for integration value. Integration checked via `grep` against `alpha_engine/` and `audit_trail/`.

| Rank | File | Summary | Integration |
|---:|:--|:--|:--|
| **5** | [docs/superpowers/specs/2026-04-14-inverse-wrapper-design.md](superpowers/specs/2026-04-14-inverse-wrapper-design.md) | Pure-function pick inverter for `quan_engine` (2.8% WR) and `Value+Quality`; surgical confidence-band flip, not whole-strategy flip. | **Partial** — `alpha_engine/quan_engine_scalp_hybrid_inverse.py` exists but audit confirms quan_engine still bleeding → not yet wired into prod flow. |
| **5** | [docs/DNA_MUTATION_WINNERS_2026-04-14.md](DNA_MUTATION_WINNERS_2026-04-14.md) | Identifies 32 winning strategies with <80 picks (starved edges); proposes mutating winners rather than building new. | **Not wired** — mentioned in plan docs only; no production mutation batch yet. |
| **4** | [docs/DNA_MUTATION_BACKTEST_REFORM_2026-04-12.md](DNA_MUTATION_BACKTEST_REFORM_2026-04-12.md) | Three reforms: regime-conditional backtest / purged CV, expand symbol universe (TRXUSDT = -86% PnL), deploy mutations at scale. | **Not integrated** — infra exists (`dna_mutation_engine.py`) but only 99/3,500 mutated picks. |
| **4** | [docs/CROSS_ASSET_STRATEGY_MATRIX.md](CROSS_ASSET_STRATEGY_MATRIX.md) | Matrix mapping proven strategies → asset classes (Connors RSI-2, Z-Score 200d fade, Funding Rate Carry). Explicit cross-asset transplantation. | **Partial** — `alpha_engine/non_crypto_policy.py` modified (see git status) suggests active work; matrix not fully shipped. |
| **3** | [docs/MUTATION_THREE_AXIS_PROTOCOL.md](MUTATION_THREE_AXIS_PROTOCOL.md) | Required pre-kill protocol: autopsy by symbol/direction/TF before blocking a strategy. | **Referenced in [CLAUDE.md](../CLAUDE.md)** as mandatory — protocol live, but no evidence the quan_engine loss was run through it. |
| **3** | [alpha_engine/MASSIVE_MUTATION_PLAN.md](../alpha_engine/MASSIVE_MUTATION_PLAN.md) | Scale genome evolution from 6k → 1M+ backtests with overfitting guards. | **Partial** — `genome_evolution_v2.py` referenced; scale-up unclear. |
| **2** | [CROSS_PERMUTATION_SYSTEM.md](../CROSS_PERMUTATION_SYSTEM.md) | Cross-system & cross-strategy permutation tester with forward-test trust tracking. | **Referenced** — design only; no active pipeline found. |
| **2** | [docs/NEW_DNA_MUTATION_TYPES.md](NEW_DNA_MUTATION_TYPES.md) | Two new mutation types added March 2026 (MAP-Elites extensions). | **Integrated** historically; not a new opportunity. |
| **1** | [alpha_engine/HEDGE_FUND_STRATEGIES_RESEARCH.md](../alpha_engine/HEDGE_FUND_STRATEGIES_RESEARCH.md), [alpha_engine/INSTITUTIONAL_SHORT_TERM_STRATEGIES.md](../alpha_engine/INSTITUTIONAL_SHORT_TERM_STRATEGIES.md) | Research dumps. | Background reading only. |
| **1** | [alpha_engine/revolutionary_comeback.md](../alpha_engine/revolutionary_comeback.md) | Narrative / brainstorming. | No prod hook. |

**Inversion / DNA / genome / cross-asset transplantation — special focus:**
- **inverse_wrapper** (rank 5) and **DNA_MUTATION_WINNERS** (rank 5) are the two highest-leverage unshipped items. Both directly address top-of-funnel losses this audit just quantified.
- **CROSS_ASSET_STRATEGY_MATRIX** is the only "transplantation" doc; it proposes moving Connors RSI-2 from stocks (proven) into crypto and forex. Given quan_engine's crypto failure, a stocks-proven mean-reversion transplant is a low-correlation hedge.

---

## Top 10 Actionable Items Ranked by P/L Impact

| # | Action | Est. 90 d PnL-% recovered | Effort | Source |
|---:|:--|---:|:--|:--|
| 1 | Blocklist MATICUSDT at universe layer (0% WR, 889 picks) | **+133** | 1 h | §1 |
| 2 | Blocklist KASUSDT (35.6% WR, already losing) | **+109** | 1 h | §1 |
| 3 | Blocklist UUSDT (2.27% avg loss per trade, n=26) | **+59** | 1 h | §1 |
| 4 | Ship `inverse_wrapper` for `quan_engine` conf < 0.70 band | **+60 to +150** (extrapolated) | 1–2 d | [inverse-wrapper-design.md](superpowers/specs/2026-04-14-inverse-wrapper-design.md) |
| 5 | Blocklist DOTUSDT, ICPUSDT, ONDOUSDT, RENDERUSDT | **+145** | 1 h | §1 |
| 6 | Recalibrate `elite_score` via isotonic regression on 500-pick training set (stops 74% top-band losses) | **+40 to +80** | 1 d | §3 |
| 7 | Diagnose + restore writers for freshness-gated `ml_bg_system_*`, `prop_firm_strategies`, `proven_strategies` | unknown, potentially large | 0.5 d each | §4a, [dashboard_generator.py](../audit_trail/dashboard_generator.py#L3700) |
| 8 | Execute [DNA_MUTATION_WINNERS_2026-04-14.md](DNA_MUTATION_WINNERS_2026-04-14.md) top-5 mutations to scale 32 starved winners | +30 to +80 | 2–3 d | §4b |
| 9 | Ship cross-asset transplant of Connors RSI-2 and Z-Score 200d fade per [CROSS_ASSET_STRATEGY_MATRIX.md](CROSS_ASSET_STRATEGY_MATRIX.md) | +20 to +60 | 3–5 d | §4b |
| 10 | Deprecate `confidence` as a gating threshold (ρ=0.145 — economically useless) | neutralizes phantom-HC noise | 1 h | §3 |

**Total recoverable PnL from items 1–5 alone: ≈ +506%** over the 90-day window, dominated by universe hygiene. This dwarfs anything the scoring system can recover, and it should be done first.

---

## Appendix: Reproducibility flags

- HC threshold `score ≥ 85` / `≥ 95` interpreted as `confidence ≥ 0.85` / `≥ 0.95` because no `score` field exists; raw `elite_score` max observed is 71.0.
- Top-50 by elite_score only samples the last 500 picks (~10 days); treat as indicative.
- Dormant-system historical stats **NOT reproducible** from `closed_picks.json`; requires `audit_dashboard/data/dashboard_data.json`.
- 90 d window is effectively the full file because the file only spans 33 days (2026-03-16 → 2026-04-18).
