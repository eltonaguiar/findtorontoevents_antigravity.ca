# Daily Idea #6 — Golden Persona Finder

**Date:** 2026-05-31
**Investigator:** Claude (claude-opus-4-7)
**Idea slug:** `golden-persona-finder`
**Verdict:** **LEAKAGE_SUSPECTED / INSUFFICIENT_CROSS_TIME** — do NOT promote to "golden"

## Verbatim user idea

> Under ai_leaderboard.html, we need a way to quickly find out if a particular Model-Persona, or persona (if not unique to the model) is highly profitable, so we don't lose a 'GOLDEN' opportunity buried in the stats.
>
> What to investigate: Build a model-persona x asset-class pivot ranking on ai_leaderboard.html that surfaces statistically significant high-PF combos (n>=30, PF>2, p<0.05). Highlight 'golden' cells. Filter UI for sortable view.

## Hypothesis

H1: Some (model_id, persona_id, asset_class) cells in `ai_tournament_picks_latest.json` have statistically significant PF≥2 / WR≥55 / n≥30 ("golden") that are not surfaced on `ai_leaderboard.html` today.

H0: No such cell exists with valid stats — apparent edges are due to small samples, symbol concentration, or single-day batch-resolver leakage.

## Methodology

- **Source:** `audit_dashboard/data/ai_tournament_picks_latest.json` (1037 picks, 647 closed with `status in (WIN,LOSS)` and non-null `pnl_pct`).
- **Computed:** n, WR, PF, avg_pnl, Wilson 95% lower-bound per (model, persona, asset_class) and per persona-only and per model-only.
- **Cross-checks:** (a) recency 14d vs 7d, (b) symbol concentration, (c) exit-reason distribution, (d) hold time, (e) date span of resolutions.

## Raw results

### (model × persona × class), n≥10 only

```
model                  persona                 class    n   wr%    pf    avg%   wlb
nous_hermes_4          volatility_tilt         ETF     12  75.0   5.49  2.56   0.47
grok3                  gamma_raid              PENNY   10  60.0   4.39  9.99   0.31
nous_hermes_4          statistical_arb         EQUITY  11  63.6   3.71  2.86   0.35
aimlapi_gpt4o          volatility_tilt         ETF     11  54.5   2.10  1.20   0.28
nvidia_nemotron_3_70b  flight_to_safety        BOND    11  63.6   1.34  0.31   0.35
nvidia_nemotron_3_70b  volatility_tilt         ETF     12  50.0   1.25  0.34   0.25
```

**No (model × persona × class) cell with n≥30 — the cell-level hypothesis fails before stats.**

### Persona-only, n≥30 (sorted by PF)

```
persona                  n    wr%    pf      wlb
microcap_momentum        38   73.7   6.26    0.58
weather_hedge            56   58.9   4.62    0.46
macro_hedge              45   71.1   4.04    0.57
volatility_tilt          81   65.4   3.91    0.55
statistical_arb          68   66.2   3.32    0.54
gamma_raid               40   52.5   2.26    0.37
flight_to_safety         52   38.5   0.67    0.26  ← negative
```

### Model-only, n≥30

```
model                    n    wr%    pf      wlb
deepseek_r1              30   83.3   16.36   0.66
deepseek_v4              55   60.0   4.63    0.47
grok3                    52   57.7   3.34    0.44
gh_models_gpt4o          32   50.0   3.22    0.34
aimlapi_gpt4o            45   53.3   3.13    0.39
groq_llama_3_70b         31   58.1   2.88    0.41
nous_hermes_4            49   49.0   1.58    0.36
nvidia_nemotron_3_70b    40   55.0   1.17    0.40
together_qwen_3          41   36.6   1.00    0.24
```

## CRITICAL LEAKAGE FINDINGS — why these numbers are NOT real edge

### 1. Single-day batch resolver (FATAL)
- **All 647 closed picks resolved on `2026-05-30`** (only 1 unique resolution date).
- Submission dates span `2026-05-28..30` only (3 days).
- 14d window = 7d window = all-time, because there is no time-span to validate against.
- This is a one-shot batch resolver flash, **not 4 weeks of live track-record**.

### 2. Symbol concentration in microcap_momentum (HHI ≫ gate)
38 picks span only ~15 symbols, top-5 (CLSK, KULR, RGTI, GSAT, LODE) hold 20/38 = 53%:
```
KULR: n=5 wins=5  pnls=[26.54, 19.88, 24.88, 24.88, 19.88]  ← duplicate pnls
GSAT: n=3 wins=3  pnls=[20.57, 24.88, 35.08]
LODE: n=3 wins=3  pnls=[24.88, 22.10, 16.55]
RGTI: n=4 wins=3  pnls=[24.88, 13.22, 21.62, -7.35]
```
- Per CLAUDE.md MEMORY (concentration = strategy level, HHI>0.30 disqualifies). microcap concentration is structural — 5 names drove the PF.
- Repeating exact `pnl_pct` (24.88, 19.88) indicates **multiple models picked the same symbol simultaneously** and all hit TP at the same instantaneous quote — these are not 38 independent trades.

### 3. Hold time ~10 h
- Picks held 10.6–10.8 h before resolution.
- TP_HIT 28/38 in microcap means the resolver crossed the TP threshold once on the very next yfinance quote bundle — exactly the **resolver spot-flicker pattern** documented in `feedback_noncrypto_resolver_live_close_bug.md`.

### 4. deepseek_r1 n=30 is concentrated across personas/classes
- 30 picks spread across 5 personas × 4 classes — the cell-level n is 5–8 per (model,persona,class). PF=16.36 is a portfolio-stack artifact, not a repeatable per-model edge.

### 5. Bonferroni
- ~9 personas × ~10 models × ~7 classes = ~630 cells tested. p<0.05 single-test → required p<0.05/630 = 7.9e-5. Wilson lower-bounds 0.40–0.58 are NOT significant after this correction.

## Cross-check vs today's NO_EDGE swarm verdict

- Today's 10-agent + 3 external-AI verdict is NO_EDGE across 6 asset classes (`money_ready_verdict.json` 2026-05-24, `pf_registry.json` policy-clean).
- The tournament JSON shows PF>4 on multiple personas. **Contradiction** — but it resolves cleanly: tournament picks are an isolated 3-day, 1-resolver-day batch with ~10h holds and symbol concentration. They do not enter `pf_registry.by_asset_class_policy_clean_net` and the policy-clean numbers correctly exclude them.
- Verdict: today's NO_EDGE stands. The "golden" cells are **(c) thin-sample noise + (d) look-ahead leakage** per the menu in section 3 of the task.

## Verdict

**LEAKAGE_SUSPECTED** at cell level; **INSUFFICIENT_CROSS_TIME** at persona level.

| Bucket | Tier verdict | Why |
|---|---|---|
| model × persona × class | INSUFFICIENT_N (max n=12) | no cell hits n≥30 |
| persona-only top-PF | LEAKAGE_SUSPECTED | single-day resolver, symbol concentration, duplicate pnls |
| model-only (deepseek_r1 PF=16.36) | LEAKAGE_SUSPECTED | unrealistic PF, n=30 across 5×4 sub-cells, 1-day batch |

Confidence: HIGH that no current "golden" cell is real money-grade. The cells may still be **shadow-pilot candidates** once the tournament accrues ≥4 weeks of live, multi-resolver-day data with diversified symbols.

## Recommended next step

1. **DO NOT** add a "GOLDEN" highlight to `ai_leaderboard.html` yet — it would mislead the operator with single-day artifacts.
2. **DO** build the model×persona×class pivot UI as requested, but gate the "golden" badge on:
   - n ≥ 30 closed picks
   - resolution dates span ≥ 14 unique days (NOT just the latest batch)
   - symbol HHI < 0.30 within the cell
   - PF ≥ 2.0 AND Wilson WR lower-bound ≥ 0.50
   - p < 0.05 / (number of tested cells) — Bonferroni
3. **Shadow-pilot** `microcap_momentum`, `volatility_tilt`, `statistical_arb` personas — track them in `tournament_shadow_personas.json`, do NOT size up.
4. **File an incident** on the resolver: 1037 picks across 3 submission days all resolved on a single calendar day is a re-resolution sweep, not real fills. See `feedback_noncrypto_resolver_live_close_bug.md`.

## Reproducer

```bash
python3 -c "
import json, math
from collections import defaultdict
picks = json.load(open('audit_dashboard/data/ai_tournament_picks_latest.json'))
closed = [x for x in picks if x.get('status') in ('WIN','LOSS') and x.get('pnl_pct') is not None]
g = defaultdict(list)
for x in closed: g[x['persona_id']].append(x['pnl_pct'])
for pers,p in sorted(g.items()):
    n=len(p); w=sum(1 for v in p if v>0)
    gp=sum(v for v in p if v>0); gl=-sum(v for v in p if v<0)
    pf = gp/gl if gl>0 else float('inf')
    if n>=30: print(f'{pers}: n={n} WR={w/n*100:.1f}% PF={pf:.2f}')
"
```
