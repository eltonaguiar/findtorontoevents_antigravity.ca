# Master Paper-Pilot Harness

**Owner:** alpha-engine peer fleet  
**Source:** `/tmp/strategy_builds_2026-05-31/master_paper_pilot_harness.py`  
**Cron:** `.github/workflows/paper-pilot-daily.yml` — `30 13 * * *` UTC  
**Status JSON:** `reports/peer_claude-master_paper_pilot_status_<YYYY-MM-DD>.json`

## What it is

A single orchestrator that runs the 7 cursor-statistical-framework paper
pilots built on 2026-05-31. Each strategy keeps its own sidecar JSON of
picks and trades — **no writes to `trading_picks` or any `ejaguiar1_*`
DB** (M-107 / cursor framework rules). The master harness:

1. Imports each strategy's `paper_pilot_harness.py`.
2. Gates by cadence (daily vs. monthly month-end-weekday).
3. Invokes the strategy's `run_once()` / `tick()` / `main()` entrypoint.
4. Re-aggregates picks → applies the cursor statistical gates uniformly.
5. Writes an aggregate status JSON to `reports/`.
6. Commits and uploads the status JSON.

## Strategies integrated (7)

| Strategy           | Asset class    | Cadence  | Sidecar                                                  |
|--------------------|----------------|----------|----------------------------------------------------------|
| `connors_rsi2`     | CRYPTO + EQUITY| daily    | `connors_rsi2/paper_state.json`                          |
| `faber_tactical`   | MULTI          | monthly  | `faber_tactical/faber_paper_ledger.json`                 |
| `fx_carry`         | FOREX          | monthly  | `fx_carry/paper_picks/fx_carry_paper_picks.json`         |
| `magic_formula`    | EQUITY         | monthly  | `magic_formula/paper_state.json`                         |
| `piotroski`        | EQUITY         | monthly  | `piotroski/paper_state.json`                             |
| `post_ipo_drift`   | EQUITY         | daily    | `post_ipo_drift/state/`                                  |
| `tsmom`            | MULTI          | monthly  | `tsmom/tsmom_trades.json`                                |

Monthly strategies are gated to the last weekday of the calendar month
(`is_month_end()`), so the daily cron does not over-trade them.

## Cursor statistical framework (enforced uniformly)

| Knob                       | Value                                                  |
|----------------------------|--------------------------------------------------------|
| Wilson CI                  | lower-bound at 95% (z = 1.96)                          |
| Bootstrap PF CI            | 1000 resamples, 95% interval, seed 17                  |
| Family-wise alpha          | 0.05                                                   |
| Bonferroni per-test alpha  | `0.05 / 7 = 0.007142857`                              |
| Graduation n-floor         | `n_closed >= 500`                                      |
| Significance test          | one-sided exact binomial vs break-even WR              |

### Promotion gates (all four must pass to graduate)

1. `n_closed >= 500`
2. `wilson_lb_wr > break_even_wr` (break-even derived from observed
   avg-win / avg-loss)
3. `pf_ci_lo > 1.0` (bootstrap PF 95% lower-bound clears 1.0)
4. `p_value < 0.007142857` (Bonferroni-adjusted significance)

Until all four pass, `status = "paper_pilot"`. When all four pass,
`status = "graduated"` — and only then is the strategy eligible for
live-money sizing review.

## Operations

### Manual run

```bash
# Run everything that's due today.
python /tmp/strategy_builds_2026-05-31/master_paper_pilot_harness.py

# Re-aggregate stats only (no strategy invocation).
python master_paper_pilot_harness.py --status

# Force-run all 7 ignoring cadence (useful for backfill).
python master_paper_pilot_harness.py --force

# One strategy only.
python master_paper_pilot_harness.py --strategy connors_rsi2
```

### CI

The `paper-pilot-daily` workflow runs at 13:30 UTC. On `workflow_dispatch`
you can override:

- `force` — `true` to bypass cadence gate
- `strategy` — name of a single strategy to run

The workflow:

1. Stages the strategy build artifacts from `tools/strategy_builds_2026-05-31/`
   (if present in the repo) to `/tmp/strategy_builds_2026-05-31/`. If the
   tools-mirror is absent, the run continues with whatever sidecar state
   already exists at the `/tmp/` path on the runner.
2. Runs the master harness.
3. Commits the per-day status JSON to `main`.
4. Uploads the status JSON as a 30-day artifact.

### Output schema (status JSON)

```json
{
  "as_of": "2026-05-31",
  "framework": {
    "wilson_z": 1.96,
    "bootstrap_resamples": 1000,
    "bonferroni_family_alpha": 0.05,
    "bonferroni_per_test_alpha": 0.00714285,
    "n_strategies": 7,
    "graduation_n_floor": 500
  },
  "strategies": {
    "connors_rsi2": {
      "n_closed": 0,
      "wins": 0,
      "win_rate": null,
      "wilson_lb_95": null,
      "pf": 0.0,
      "pf_ci_95": [0.0, 0.0],
      "p_value": 1.0,
      "gates": {
        "n_floor_500": false,
        "wilson_lb_wr_gt_be": false,
        "pf_ci_lo_gt_1": false,
        "p_bonferroni": false
      },
      "status": "paper_pilot"
    }
  },
  "summary": {
    "n_strategies": 7,
    "n_graduated": 0,
    "total_picks_tracked": 0
  }
}
```

## Design rules (do NOT relax without authorization)

1. **No DB writes.** Picks live in JSON sidecars. The cursor framework
   exists specifically because `trading_picks` is a known contamination
   surface (M-067 / M-107 policy-clean cohort doc).
2. **Cadence respect.** Monthly strategies do not run on non-month-end
   days. Daily-cron mis-runs of monthly strategies inflate the
   trade count and violate the n-floor's epistemic meaning.
3. **Bonferroni stays at 7.** If you add an 8th strategy, the alpha
   drops to `0.05 / 8`. Don't lower the family alpha to compensate —
   accept the stricter per-test bar.
4. **Graduation is multi-gate.** Never promote on a single metric
   crossing. All four gates required, simultaneously, for >=1 status
   snapshot before any live-money discussion.
5. **Failures are non-fatal.** One broken strategy module never blocks
   the others. The master traps exceptions and reports them in
   `run_log` rather than aborting the cycle.

## Related docs

- `docs/AGENT_QUICKSTART_AUDIT_AND_STRATEGIES.md` — repo tour
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — mutate-before-kill rule
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — kill-list governance
- `reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md` — origin of the
  Wire-Up Rule (every module needs a caller)
- `reports/peer_claude-TOPIC_DEEP_DIVE_SYNTHESIS_2026-05-31.md` — full
  synthesis of the 6 topic deep-dives that produced sections H-M below

## 24-strategy expansion — methodology addendum (2026-05-31)

The original cursor framework (n>=500 / Wilson LB / Bootstrap PF / Bonferroni) covers per-strategy graduation but does not cover **portfolio-level**, **regime**, **cost**, **sizing**, or **payoff-shape** decisions. Sections H-M below close those gaps for the 24-strategy expansion (mine 8 + kilo 8 + zoo 8) launching 2026-06-01 13:30 UTC.

Authoritative synthesis: `reports/peer_claude-TOPIC_DEEP_DIVE_SYNTHESIS_2026-05-31.md`. Source per-topic deep-dives in `reports/peer_claude-topic_*_2026-05-31.md` (deepseek/grok/qwen-pro/mimo/gemini-FAIL/kimi).

**Bonferroni α update for the 24-cohort:** family size = 24 → per-test α = `0.05 / 24 = 0.00208333` (overrides the 0.05/7 value in the table above once the 24-strategy cohort lands).

### Section H — Execution costs per class

All gates operate on **net PnL** = `raw_pnl_bps − one_way_cost_bps`, where one-way cost = `spread/2 + commission_bps + impact_bps(notional)` and `impact_bps = coeff * sqrt(notional_usd / 1e6)` (active only above $10k notional).

| Class | Spread bps | Commission bps | Impact coeff |
|---|---:|---:|---:|
| CRYPTO_MAJOR | 4 | 10 | 0.10 |
| CRYPTO_ALTCOIN | 15 | 10 | 0.50 |
| EQUITY_SP500 | 1.5 | 0.5 | 0.01 |
| EQUITY_SMALLCAP | 7 | 0.5 | 0.10 |
| FOREX_MAJOR | 0.8 | 0.2 | 0.005 |
| FOREX_CROSS | 3 | 0.2 | 0.02 |
| COMMODITY_FUTURES | 3 | 1 | 0.05 |
| ETF_SPY | 1.5 | 0.5 | 0.01 |
| BOND | 10 | 2 | 0.20 |
| FUTURES_ES | 0.8 | 0.3 | 0.005 |
| FUTURES_NQ | 1 | 0.5 | 0.008 |
| PREDICTION_MARKET | 20 | 100 | 1.0 |

Recalibrate per class if realized cost vs IBKR/exchange fills deviates >20% over first 100 trades. Refs: Almgren-Chriss (2001), Kissell (2013), Cont & Wagalath (2016), BIS Triennial.

### Section I — Regime-change kill switches

Five macro signals computed daily at T-1 close:
1. VIX level > 35 OR ΔVIX_1d > +8
2. 20d pairwise corr < 0.15 (breakdown) OR > 0.75 (flight-to-quality)
3. 20d RV / 60d RV > 1.8 (expansion) OR < 0.6 (crush)
4. Median bid-ask spread z-score > +3.5
5. Strategy-specific 5d cum return < -3.5σ of 252d history

Decision tree: 0 → OK; 1 (persists <2d) → PAUSE 3 days; ≥2 OR persists >3d → KILL; strategy DD < -4σ → immediate KILL. Re-entry needs 5 consecutive clean days.

Per-class kill map: EQUITY/ETF kill trend/momentum on corr collapse or vol switch; FUTURES/COMMODITY kill CTAs on RV ratio > 1.8; FOREX kill carry on liq z > 3 or corr > 0.75; CRYPTO kill all except basis arb on VIX > 40 or RV switch; BOND/PRED_MKT kill directional on DD only.

Lookbacks: fast 5-20d, regime 60d vs 252d, correlation 20d Diebold-Yilmaz. Refs: Ang & Bekaert (2002), Diebold & Yilmaz (2012), Hamilton (1989), Cont (2001).

### Section J — Capacity + Kelly sizing

Capacity haircut: `h = min(1, threshold_$M / AUM_$M)` per (asset_class × edge_type), with thresholds:

| Edge | CRYPTO | EQUITY | FOREX | COMMOD | ETF | BOND | FUTURES | PRED_MKT |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Mean-rev | 50 | 200 | 100 | 100 | 150 | 300 | 100 | 50 |
| Momentum | 100 | 500 | 200 | 200 | 300 | 600 | 200 | 100 |
| Stat-arb | 20 | 100 | 50 | 50 | 100 | 200 | 50 | 20 |
| Cross-asset arb | 50 | 300 | 100 | 100 | 200 | 400 | 100 | 50 |

Kelly: default **fractional Kelly = 0.25 × f_raw** for the 24-strategy pilot. Full Kelly only when Wilson LB WR ≥ 0.60 AND bootstrap PF LB ≥ 1.5 AND n ≥ 500 AND 4 weeks paper-trade clean. f_raw = `(μ − r_f) / σ²` (Thorp 2006 continuous form). Per-strategy NAV cap: 5% if any sub-gate fails or n<500; 15% otherwise.

Admission gate for strategy N+1: reject if marginal Sharpe ≤ 0 OR if |corr| > 0.5 to any existing strategy. Refs: Thorp (2006), MacLean/Thorp/Ziemba (2010).

### Section K — Cross-strategy correlation gate

Compute on **risk-adjusted returns** (`ret / vol_rolling_63d`), **Spearman** rank, 252d rolling.

| Gate | Warn | Kill |
|---|---|---|
| Pairwise ρ | > 0.70 | > 0.85 |
| Tail ρ (portfolio in 5%-tail, ≥3 strats same AC) | — | > 0.75 |
| Fraction strats in >5% DD | > 0.50 | > 0.60 sustained 10d |
| N_eff / N_actual (Bouchaud) | < 0.50 | < 0.30 |
| Max HRP cluster weight | — | > 0.40 |
| Max single-strategy weight | — | > 0.10 |

`N_eff = (Σ λ_k)² / Σ λ_k²` (corr-matrix eigenvalues). Allocation uses Lopez de Prado 2016 HRP — quasi-diagonalization (Ward linkage on `√(0.5(1−ρ))`) + recursive bisection. Reject MVO/IVP (corr matrix near-singular at N=24/T=252). Tail-cluster detection: stress-mask `portfolio_ret < q05` → conditional Spearman → cluster → kill if cluster tail ρ > 0.75 with ≥3 strats same asset class. Refs: Lopez de Prado (2016), Bouchaud & Potters (2009), Adrian & Brunnermeier (2016), Laloux et al. (1999), Embrechts et al. (2002), Patton (2006), Evans & Archer (1968), Elton & Gruber (1977).

### Section L — Live-vs-paper divergence tracking

**Status:** PLACEHOLDER (Gemini consult failed — quota exhausted on all 3 free-tier keys); re-route to `/consult-codex` or `/consult-cloudflare run gpt-oss-120b` before live trading begins. Bailey & Lopez de Prado (2014) DSR/PSR-anchored scaffold:

- **30d rolling:** alert if `|PF_live − PF_paper| / PF_paper > 0.30`
- **60d rolling:** alert if `Sharpe_live / Sharpe_paper < 0.70 OR > 1.30`
- **90d rolling:** PSR_live < 0.95 → DOWN-WEIGHT; < 0.90 → PAUSE; < 0.80 → KILL

Pause triggers (any): Sharpe drop > 30% over 30d; PF drop > 50% over 30d; 5 consecutive losers.

Regime vs alpha-decay test:
1. Section I macro signals firing → regime change → PAUSE.
2. Macro clean but DSR < 0.95 → alpha decay → KILL candidate.
3. Confirm via 90d walk-forward refit: if refit Sharpe ≈ live → parameter drift; if refit ≈ paper → regime overwhelm.

Primary ref: Bailey & Lopez de Prado (2014) *The Deflated Sharpe Ratio*. JPM 40(5).

### Section M — R:R floor + tail risk gates

Per-class R:R floor + 3-tier tail stack (Sortino + CVaR-95 + Modified Sharpe) **overrides** the existing Sharpe-only gate:

| Class | R:R | PF | Sharpe | Sortino | CVaR-95 | Max-Loss / Trade | Convex Max-Loss |
|---|---|---|---|---|---|---|---|
| CRYPTO | 1.5:1 | 1.3 | 1.0 | 1.5 | ≤ -2.5 × σ_tgt_daily | 1.00% NAV | 1.50% |
| EQUITY | 1.2:1 | 1.3 | 1.0 | 1.3 | ≤ -2.5 × σ_tgt_daily | 0.50% NAV | 0.75% |
| FOREX | 1.0:1 | 1.2 | 0.8 | 1.2 | ≤ -2.5 × σ_tgt_daily | 0.50% NAV | 0.75% |
| COMMODITY | 1.5:1 | 1.3 | 0.9 | 1.4 | ≤ -2.5 × σ_tgt_daily | 0.75% NAV | 1.00% |
| ETF | 1.0:1 | 1.2 | 0.8 | 1.2 | ≤ -2.5 × σ_tgt_daily | 0.50% NAV | 0.75% |
| BOND | 1.0:1 | 1.2 | 0.7 | 1.0 | ≤ -2.5 × σ_tgt_daily | 0.50% NAV | 0.75% |
| FUTURES | 1.2:1 | 1.3 | 0.9 | 1.3 | ≤ -2.5 × σ_tgt_daily | 0.50% NAV | 0.75% |
| PREDICTION_MARKETS | 1.0:1 | 1.2 | 0.8 | 1.2 | ≤ -2.5 × σ_event | 0.50% NAV | 0.75% |

**Gate order (short-circuit on first fail):** sample/intrabar → Bonferroni (α=0.00208) → PF & R:R floor → Wilson LB → concentration (HHI) → tail risk (Sortino + CVaR-95) → Modified Sharpe (Cornish-Fisher if kurt>3, Lo 2002) → bootstrap PF (block bootstrap, Patton-Politis-White 2009) → Kelly sizing + NAV cap.

**Convexity Protocol** (asymmetric 20%-WR / 10:1-R:R strategies): n≥1000 OR ≥30 wins>3× avg-loss; skew>1.5; HHI<0.50; single-trade<25% gross profit; Sortino≥1.0; bootstrap 95% CI on mean trade PnL > 0; sizing **1/16 Kelly**; aggregate CT capital ≤ 15% NAV; max 3 simultaneous CT strats; auto-flatten on single trade > 25% trailing-90d gross profit OR CVaR-95 breaches -3.0 × σ_tgt_daily; recertify every 21 trading days (skew<1.0 or Wilson LB<0.10 → revoke, collapse to 1/32 Kelly); ruin hardstop 30% DD from HWM → permanent kill.

Refs: Harvey & Liu (2015), Lo (2002), MacLean/Thorp/Ziemba (2011), Patton/Politis/White (2009), Rockafellar & Uryasev (2000), Sortino & van der Meer (1991), Taleb (2020).

### Production wiring map (sections H-M)

| Section | Production module | Status |
|---|---|---|
| H exec costs | `alpha_engine/cursor_statistical_framework.py::apply_execution_costs` | shipped (this PR) |
| I regime kill | `alpha_engine/cursor_statistical_framework.py::regime_kill` | shipped (this PR) |
| J capacity+Kelly | `alpha_engine/cursor_statistical_framework.py::size_strategy` | shipped (this PR) |
| K corr gate | `alpha_engine/cursor_statistical_framework.py::correlation_cluster_gate` | stub (full HRP allocator in `alpha_engine/paper_pilot/correlation_gate.py` — follow-up PR) |
| L divergence | `alpha_engine/cursor_statistical_framework.py::live_paper_divergence_gate` | placeholder (re-route Gemini prompt → Codex/Cloudflare) |
| M R:R + tail | `alpha_engine/cursor_statistical_framework.py::rr_floor_gate` | shipped (this PR; full `gates.py` per Kimi spec lands in `alpha_engine/paper_pilot/gates.py` — follow-up PR) |
