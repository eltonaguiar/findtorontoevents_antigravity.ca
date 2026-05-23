# Swarm Pick Tracking — Design Document

**Owner:** Claude Opus 4.7 (1M ctx) | **Date:** 2026-05-12 | **Status:** DRAFT — design only, no production HTML modified.

This design proposes a persistence + scoring + dashboard layer that captures every multi-model swarm-generated paper pick, scores its outcome against consensus tier and per-model vote, and surfaces per-tier/per-model edge on `findtorontoevents.ca/audit`. It is the durable home for the data that `TV_SWARM_SESSION_2026-05-11_2330EST.MD` and `TV_PICKS_WHY_2026-05-11_2229EST.MD` currently capture only in committed markdown — and the persistence layer the multi-model bake-off proposed in `DAILY_IDEAS.MD` (2026-05-11 entry, lines 330-376) needs in order to "prove over time which model is the best at each asset class."

It complements (does **not** replace) the existing **AI Challenge** curator panel (round-based curator-as-strategy tournament at `audit_dashboard/data/ai_challenge_*_active_picks.json`) — that panel scores curators-as-strategies; this panel scores **consensus tier × per-model vote across a fanned-out swarm**, which is a different dimension and a different cadence.

---

## Section A — Current state

### What exists today

1. **Swarm dispatch infrastructure** — `tools/swarm/swarm_dispatch.ps1`, `tools/swarm/output_parsers.py`, `tools/swarm/schema_validate.py`, 60+ personas under `tools/swarm/agent_personas/`. Built for PR-review / audit-question fanout, not pick-tracking. Outputs live in `swarm_runs/<run_id>/<engine>.json` with a `MASSFEEDBACK.MD`-style flat schema.

2. **TV paper trade execution layer** — `.claude/skills/tv-paper-trade/SKILL.md` plus the TradingView Desktop MCP (78 tools). Already places picks across `zerounderscore`, `The Leap Crypto`, `theswarm`, `HIGHFWWRABV55_SCOREABOVE50_V4` accounts with full TP/SL audit + side-sanity gate. Per-trade transcript markdown is the only durable record.

3. **AI Challenge panel (curator tournament)** — `audit_dashboard/data/ai_challenge_*_active_picks.json` (7 curators × per-round arrays). Schema covers `symbol, direction, signal_type, entry_price, take_profit, stop_loss, confidence, strategy, status, outcome, pnl_pct, round, rank, curator, methodology, rationale, statistical_basis, risk_reward, generated_at, ml_score`. Loaded by `audit_trail/dashboard_generator.py:3796-3829`. Rendered behind the audit dashboard via standard pick-grid template logic.

4. **The most recent 10-persona swarm** placed 14 picks on `theswarm` paper account across 5 asset classes on 2026-05-11. Per `TV_SWARM_SESSION_2026-05-11_2330EST.MD`, consensus tiers were **manually** classified as **unanimous (5/5 LONG)**, **strong (4/5 SHORT)**, **moderate (3/3 LONG)**, **control (0-net or +1 only)**. No machine-readable persistence — the asset-class-consensus-heatmap exists only in the .MD table.

5. **DAILY_IDEAS.MD bake-off proposal** (2026-05-11 entry, §330-376) specifies four planned artifacts that do not yet exist:
   - `tools/swarm/model_bakeoff.py`
   - `tools/swarm/data_point_diff.py`
   - `tools/swarm/debate_orchestrator.py`
   - `tools/swarm/criteria_backtester.py`
   - target output dir `tools/swarm/bakeoff_runs/<round_id>/<model>/<class>.json` — `tools/swarm/bakeoff_runs/` confirmed **does not exist** as of this commit (`Glob "tools/swarm/bakeoff_runs/**/*"` returns no files).

### What's missing (gaps)

| Gap | Concrete file / call site | Symptom |
|-----|---------------------------|---------|
| **No durable swarm-pick store** | no `audit_dashboard/data/swarm_picks.json` | per-pick consensus tier + per-model vote lives only in transcript .MDs; cannot be queried, joined to outcomes, or scored over time |
| **No per-pick per-model vote log** | nowhere — the 10 personas' LONG/SHORT/SKIP votes for the 30-symbol universe were aggregated then discarded | cannot compute per-model live WR, cannot answer "which model is best at FOREX" |
| **No outcome resolver wired to swarm picks** | `alpha_engine/outcome_resolver.py` operates on `*_active_picks.json` schemas with `outcome=PENDING/WIN/LOSS`. Swarm picks never enter this pipeline | TP/SL fills never linked back to consensus tier |
| **No weekly review cadence** | no `tools/swarm/weekly_review.py`, no `reports/swarm_review/` dir | tier-vs-WR question ("did unanimous beat control?") cannot be answered without manual grep |
| **No dashboard panel** | `audit_dashboard/template.html` mentions `theswarm` zero times; `AI Challenge` panel covers curators but not consensus-tier × model votes | users cannot see swarm-pick performance on `/audit` |
| **No leaderboard feed-back loop** | no `swarm_leaderboard.json`; bake-off proposal references one but no producer or consumer exists | future fanouts cannot weight votes by historical model accuracy |
| **No pattern miner** | `reports/` has per-session swarm-output dirs but no cross-session aggregator | "do unanimous picks beat strong?" / "do BULLISH-regime picks win more?" answerable only by hand |

---

## Section B — Schema proposal

### Primary store: `audit_dashboard/data/swarm_picks.json`

Single JSON file. **Array of pick records.** Atomic write via `<file>.tmp` then `os.replace()`. Optionally split per month if it exceeds 5 MB.

```json
[
  {
    "pick_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2026-05-11T23:18:00-05:00",
    "session_id": "tv_swarm_2026-05-11_2230est",
    "account": "theswarm",
    "symbol": "BINANCE:LINKUSDT",
    "direction": "LONG",
    "entry": 10.52,
    "tp": 11.56,
    "sl": 9.98,
    "qty": 475,
    "qty_unit": "asset_units",
    "timeframe": "4H",
    "asset_class": "CRYPTO",
    "consensus_tier": "unanimous",
    "models_consulted": [
      {"name": "MOMENTUM_TECH",  "role": "persona",  "vote": "LONG", "confidence_0_100": 78, "timeframe": "4H", "justification_summary": "LINK breaking 200d EMA on rising volume; macro alt-rotation thesis."},
      {"name": "MACRO_BEAR",     "role": "persona",  "vote": "LONG", "confidence_0_100": 55, "timeframe": "1D", "justification_summary": "Even bears agree LINK base is intact; risk/reward fav up."},
      {"name": "MEAN_REVERSION", "role": "persona",  "vote": "LONG", "confidence_0_100": 70, "timeframe": "4H", "justification_summary": "Bounce off lower BB band on 4H; mean revert toward mid."},
      {"name": "FUND_VALUE",     "role": "persona",  "vote": "LONG", "confidence_0_100": 65, "timeframe": "1D", "justification_summary": "Oracle sector TVL recovering; relative value vs peers."},
      {"name": "ONCHAIN_QUANT",  "role": "persona",  "vote": "LONG", "confidence_0_100": 72, "timeframe": "4H", "justification_summary": "Stake-flow net positive; smart-money accumulation tag."}
    ],
    "models_agreed": 5,
    "models_voted": 5,
    "consensus_score": 1.0,
    "regime_at_entry": {
      "btc_regime": "RANGE",
      "vol_regime": "MID",
      "source": "audit_dashboard/data/live_market_regime.json"
    },
    "outcome": null,
    "pattern_tags": []
  }
]
```

### Field definitions (canonical)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `pick_id` | UUIDv4 string | yes | generator-assigned; never re-used |
| `created_at` | ISO-8601 w/ TZ | yes | exec time, not vote-aggregation time |
| `session_id` | string | yes | groups picks placed in one swarm run; matches `swarm_runs/<id>/` if available |
| `account` | enum: `theswarm` \| `V4` \| `Leap` \| `zerounderscore` \| `BROKIE` \| `SCALPER` \| `TESTER` \| `TRUSTOURSCORE` | yes | matches `.claude/skills/tv-paper-trade/SKILL.md` account list |
| `symbol` | TV-style string | yes | exchange-prefixed (e.g., `BINANCE:LINKUSDT`, `NASDAQ:TLT`, `FX:USDJPY`) |
| `direction` | `LONG` \| `SHORT` | yes | filled trades only — `SKIP` is recorded in `skipped_candidates` (see below) |
| `entry`, `tp`, `sl` | float | yes | as placed; must satisfy LONG: `tp>entry>sl`, SHORT: `sl>entry>tp` (asserted on write) |
| `qty` | float | yes | as placed |
| `qty_unit` | `asset_units` \| `pct_balance` | yes | TV paper field is %-balance for crypto perps per memory `reference_tv_paper_qty_field`; record canonical so analyzer doesn't double-convert |
| `timeframe` | `15m` \| `1H` \| `4H` \| `1D` \| `1W` | yes | the model-consensus timeframe (median vote) |
| `asset_class` | `CRYPTO` \| `EQUITY` \| `ETF` \| `FOREX` \| `BOND` \| `COMMODITY` \| `FUTURES` \| `SPORTS` | yes | use class taxonomy from `dashboard_data.json::performance.asset_class_health` |
| `consensus_tier` | `unanimous` \| `strong` \| `moderate` \| `single` \| `control` | yes | derived: `score>=0.95` unanimous, `>=0.66` strong, `>=0.50` moderate, `>0` single-model, `==0` control |
| `models_consulted[].vote` | `LONG` \| `SHORT` \| `SKIP` | yes | every model that responded; missing models go in `models_skipped[]` |
| `models_agreed` | int | yes | count of votes matching `direction` |
| `models_voted` | int | yes | count of non-SKIP non-missing votes |
| `consensus_score` | float 0..1 | yes | `models_agreed / models_voted` |
| `regime_at_entry` | object | yes | snapshot of `live_market_regime.json` at trade time |
| `outcome` | object \| null | yes | null until exit; filled by `outcome_resolver_swarm.py` |
| `pattern_tags` | string[] | yes | populated by weekly review; e.g., `["high_consensus_unanimous","BULLISH_regime","short_alpha"]` |

### Outcome sub-schema (populated post-exit)

```json
"outcome": {
  "filled_price": 10.515,
  "fill_time": "2026-05-11T23:18:42-05:00",
  "exit_price": 11.56,
  "exit_time": "2026-05-14T09:04:18-05:00",
  "exit_reason": "TP_HIT",
  "pnl_usd": 496.31,
  "pnl_pct": 9.98,
  "pnl_R": 1.93,
  "bars_held": 142,
  "max_favorable_excursion_pct": 11.2,
  "max_adverse_excursion_pct": -2.1,
  "resolver_version": "swarm_v1"
}
```

`exit_reason` ∈ `{TP_HIT, SL_HIT, TIME_CAP, MANUAL, ROLL}`. `pnl_R` = `pnl_pct / risk_pct` where `risk_pct = |entry-sl|/entry`. `resolver_version` lets us replay if the resolver bug class re-occurs (memory `feedback_noncrypto_resolver_live_close_bug`).

### Sibling stores

- `audit_dashboard/data/swarm_picks_skipped.json` — same envelope minus exit fields; records SKIP-consensus candidates (e.g., the 16 symbols the 30-symbol 2026-05-11 universe rejected). Lets us answer "did the swarm correctly skip losers?"
- `audit_dashboard/data/swarm_leaderboard.json` — per-model live WR/PF rollup. Produced by `weekly_review.py`. Schema:

```json
{
  "computed_at": "2026-05-19T00:00:00Z",
  "window_days": 30,
  "models": [
    {
      "name": "MOMENTUM_TECH",
      "asset_class_breakdown": {
        "CRYPTO": {"n": 38, "wr": 0.55, "pf": 1.62, "avg_R": 0.34},
        "EQUITY": {"n": 12, "wr": 0.42, "pf": 1.05, "avg_R": 0.04}
      },
      "overall": {"n": 71, "wr": 0.52, "pf": 1.41, "avg_R": 0.22},
      "consensus_contribution": {
        "in_unanimous": 28,
        "in_strong": 19,
        "in_winning_picks_pct": 0.58
      },
      "recommended_weight": 1.15
    }
  ]
}
```

### JSON Schema (formal) — write to `audit_dashboard/schemas/swarm_pick.schema.json`

Use JSON Schema Draft 2020-12. `swarm_picks.json` validates as `{ "type":"array", "items": { "$ref": "swarm_pick.schema.json" } }`. Validation runs in `tools/swarm/schema_validate.py` (already exists for review-swarm output; add swarm-pick variant).

---

## Section C — Weekly review process

### Script: `tools/swarm/weekly_review.py`

**Cadence:** Mondays 06:00 UTC via GitHub Actions cron (or local Windows scheduled task; align with `audit-dashboard.yml`).

**Inputs:** `audit_dashboard/data/swarm_picks.json` (filtered to last 7 days where `outcome != null`).

**Algorithm:**

1. **Load + filter.** Load all picks with `outcome.exit_time >= now-7d`. Reject picks still `PENDING` (carry to next week).
2. **Per-consensus-tier stats** — group by `consensus_tier`, compute `n, wins, losses, WR, PF, sum_R, sharpe_est`. Sharpe estimate = `mean(pnl_R) / std(pnl_R) * sqrt(N_per_year)` where `N_per_year` is the implied annualization from `bars_held` distribution. Flag tier results where `n < 10` as `underpowered`.
3. **Per-model stand-alone WR.** For each model in `models_consulted`, compute the WR if it had traded only its own votes (LONG when it voted LONG, SHORT when it voted SHORT) — independent of swarm consensus. Use the realized pick outcome for direction agreement, invert for direction disagreement.
4. **Winning-pick presence.** For each model, `% of winning picks where this model voted with the final direction`. High value = "always on the winning side"; low value = "noise" or "contrarian."
5. **Pattern correlations.**
   - Tier-vs-WR delta: `WR(unanimous) - WR(control)`. If <= 0 over 30 days with `n_unanimous >= 30`, **consensus-tier hypothesis fails** — flag in report header.
   - Regime-vs-WR delta: `WR(BULLISH-regime picks) - WR(BEARISH-regime picks)`.
   - Side-vs-WR delta: `WR(SHORT) - WR(LONG)`. Memory `feedback_long_source_bias` predicts SHORTs outperform in current regime; weekly review verifies.
6. **Output report.** Write `reports/swarm_review/YYYY_WW.md` (ISO year-week, e.g., `2026_19.md`). Sections:
   - Header: window dates, total picks closed, headline tier-delta verdict
   - Per-tier table
   - Per-model leaderboard (top 10 + bottom 5)
   - Pattern findings (regime, side, asset class)
   - Hot/cold cells flagged for next week's prompts (the Section E winning/losing cell tables)
7. **Update `swarm_leaderboard.json`.** Atomic-replace; downstream consumers (future bake-off, swarm-vote-weighting) read this file.
8. **Update `pattern_tags`** on each pick in `swarm_picks.json`: e.g., the analyzer tags every pick that fell in a winning-cell (Section E) with `winning_cell_<class>_<tier>_<regime>`.

**Exit criteria:** script runs in < 30 s on 1k picks; writes report + leaderboard; CI green on schema validation of updated `swarm_picks.json`.

### Skill mapping

- Use `money-maker-ready` (skill) as the rubric for translating WR/PF into go/no-go verdicts per asset class (T1/T2 tier thresholds from `docs/PERFORMANCE_CHARTER.md`).
- Use `swarm-invent` (skill) when a new persona is added — it produces the YAML registry entry that the bake-off / weekly-review code reads to discover models.

---

## Section D — Dashboard integration

### New panel: "Swarm Pick Tracking"

**Location in `audit_dashboard/template.html`:** insert directly under the AI Challenge curator panel (search anchor: the comment block at `template.html:3511` `// 4 AI Challenge Curators`). Keep curator panel intact — swarm-pick panel is a sibling, not a replacement.

**Data feed:**
- Hot data: `/audit_dashboard/data/swarm_picks.json`
- Aggregates: `/audit_dashboard/data/swarm_leaderboard.json`
- Regime context (already loaded): `/audit_dashboard/data/live_market_regime.json`

**Columns (table view):**

| symbol | direction | account | consensus tier | models agreed | avg model conf | current PnL | expected R | realized R | exit reason |
|--------|-----------|---------|-----------------|---------------|----------------|-------------|------------|------------|-------------|
| LINKUSDT | LONG | theswarm | unanimous | 5 / 5 | 68 | +9.8% | 2.0R | 1.93R | TP_HIT |

**Filters:**
- account multi-select
- consensus tier multi-select
- asset class multi-select
- date range (default last 30d)
- direction (LONG/SHORT/both)
- regime at entry (BULLISH/BEARISH/RANGE)

**Inline visualizations:**
- **Sparkline panel:** WR-by-consensus-tier over rolling 30 days. 4 lines: unanimous, strong, moderate, control. Verifies the consensus-tier hypothesis at a glance.
- **Model-vote heatmap:** rows = models, cols = asset classes, cell color = per-model-per-class WR. Click cell → drill to pick list.
- **Hot/cold cell tables** (Section E output): two compact tables labeled "Pattern cells: winning" and "Pattern cells: losing." Refresh weekly.

**Click-through:** clicking a row opens a per-pick detail page (`audit_dashboard/swarm_pick_detail.html?id=<pick_id>`) showing all model justifications side-by-side, the entry/exit chart-snapshot if available, and the consensus-vote bar.

### Generator integration (in `audit_trail/dashboard_generator.py`)

Add a tuple to the existing PICK_SOURCES table at `audit_trail/dashboard_generator.py:~3796` style:

```python
("swarm_picks", "audit_dashboard/data/swarm_picks.json", None),
```

And register the file under a new section in `_PAPER_ONLY_SYSTEMS` so it appears for display **but does not pollute** system-wide PF/WR aggregates (these are persona-vote ensemble picks, not a single-strategy system — should not be averaged into `dashboard_data.json::performance` until tier-specific stats are surfaced separately).

### Contract review

Before any `template.html` edit, run the **`dashboard_contract_reviewer` skill** to lock the JSON payload key contract between generator + template. Specifically pin:
- the `consensus_tier` enum values
- the `outcome.exit_reason` enum
- the `pattern_tags` shape (array of strings)

This prevents the silent key-rename failure mode documented in memory `feedback_diag_commits_can_break_prod` (2026-04-20 crypto-tile blank).

### CLAUDE.md compliance

- Edit `audit_dashboard/template.html` only — never `index.html`. (CLAUDE.md, "Critical File Rules.")
- Verify with `python -m py_compile audit_trail/dashboard_generator.py` only — never run the generator locally. (CLAUDE.md, "Never run dashboard generators locally.")

---

## Section E — Pattern-detection MVP

### Script: `tools/swarm/pattern_miner.py` (invoked at the end of `weekly_review.py`)

**Goal:** identify `(consensus_tier × asset_class × regime)` cells where the swarm has a real edge or real anti-edge, with sample size large enough to bias next week's prompts.

**Algorithm:**

1. Group closed picks by the 3-tuple. Compute `n, wins, losses, WR, PF, avg_R`.
2. **Winning cells** = `WR > 0.60 AND n >= 10 AND PF > 1.5`.
3. **Losing cells** = `WR < 0.40 AND n >= 10 AND PF < 0.8`.
4. Sort each list by `(n × |WR − 0.5|)` to surface high-confidence cells first.
5. Emit two tables to `reports/swarm_review/YYYY_WW.md` (and to a sidecar `swarm_pattern_cells_latest.json` for dashboard consumption):

**Winning-cells table example:**

| tier | class | regime | n | WR | PF | avg R |
|------|-------|--------|---|-----|-----|--------|
| unanimous | ETF | BULLISH | 28 | 0.71 | 2.10 | 0.52 |
| strong | CRYPTO | BEARISH (SHORT) | 41 | 0.66 | 1.94 | 0.41 |

**Losing-cells table example:**

| tier | class | regime | n | WR | PF | avg R |
|------|-------|--------|---|-----|-----|--------|
| control | FOREX | RANGE | 14 | 0.21 | 0.31 | -0.58 |
| moderate | FUTURES | BULLISH | 11 | 0.27 | 0.46 | -0.39 |

6. **Feedback into prompts:** the next week's swarm-prompt template auto-prefixes the winning-cell tags as "bias toward" and the losing-cell tags as "bias away from." Example: `BIAS HINT: prior 30d shows unanimous ETF BULLISH wins 71% (n=28); control FOREX RANGE loses 79% (n=14). Weight your vote accordingly.`

7. **Pattern tag persistence:** every pick whose 3-tuple is in a winning cell gets `pattern_tags += ["winning_cell:<tier>_<class>_<regime>"]`. Same for losing cells. This lets the dashboard color-code rows.

**Statistical guard:** require `n >= 10` AND Wilson-score 95%-LB(WR) > 0.50 for winning-cell promotion (prevents 7/10 = 70% from getting featured). For losing cells, require Wilson UB(WR) < 0.50.

---

## Section F — Concrete tasks ranked

Each task is 1-2 hours, atomic, with clear exit criteria. Ordered by leverage (highest WR-impact first).

1. **Define + write the schema files.**
   File: `audit_dashboard/schemas/swarm_pick.schema.json` + `swarm_leaderboard.schema.json`. Add validator hook in `tools/swarm/schema_validate.py`. Exit: `python tools/swarm/schema_validate.py --schema swarm_pick --input <sample>` returns 0 on a hand-written sample with 3 picks. (No production impact yet.)

2. **Backfill `swarm_picks.json` from 2026-05-11 session transcripts.**
   Parse `TV_SWARM_SESSION_2026-05-11_2330EST.MD` + `TV_PICKS_WHY_2026-05-11_2229EST.MD`. Produce the initial `swarm_picks.json` with ~22 picks (14 theswarm + 4 zerounderscore + 3 Leap + 1 MCL). Each pick gets a UUID, the swarm's classified tier, and the per-pick justification mapped to a synthetic single-model vote where individual model votes weren't recorded. Exit: schema-validation passes, dashboard generator picks it up (`grep "swarm_picks" audit_trail/dashboard_generator.py` returns ≥1 hit), CI green.

3. **Build `tools/swarm/outcome_resolver_swarm.py`.**
   Polls TV positions via the TradingView MCP `data_get_trades` tool + reads filled/closed prices, writes back `outcome.{filled_price,fill_time,exit_price,exit_time,exit_reason,pnl_*,bars_held,MFE,MAE}`. Idempotent — never overwrites a previously-resolved `outcome`. Honour `feedback_noncrypto_resolver_live_close_bug` — close at real exit fill from TV, not yfinance spot. Exit: resolver run on backfilled file flips ≥1 pick from `outcome=null` to a resolved object; no schema errors.

4. **Write `tools/swarm/weekly_review.py` + first run.**
   Per Section C. Run once on the backfilled data (will be underpowered — that's expected and the report should say so). Commit the first report to `reports/swarm_review/2026_19.md`. Exit: report written; `swarm_leaderboard.json` written and schema-valid; per-tier and per-model tables non-empty.

5. **Wire the swarm-pick generator into the live swarm flow.**
   Edit `tools/swarm/swarm_dispatch.ps1` (or a new wrapper `tools/swarm/picks_recorder.py`) so that any persona-divergent pick swarm writes a `swarm_picks.json` record at the moment picks are placed (not after the fact in a .MD). The recorder takes the raw votes JSON from the swarm + the TV order receipt + writes the canonical record. Exit: next swarm session creates new rows in `swarm_picks.json` automatically; no .MD-only records going forward.

6. **Add the dashboard panel (template + generator) — design-locked first.**
   Run `dashboard_contract_reviewer` skill against the schema. Then edit `audit_dashboard/template.html` (anchor near AI Challenge panel comment at `:3511`) to add the table + filter row + sparkline. Edit `audit_trail/dashboard_generator.py` to push `swarm_picks.json` payload to the template context. Verify with `python -m py_compile`. Exit: `py_compile` clean; PR description includes a screenshot from a hand-built mock JSON; no production HTML edited locally (dashboard auto-rebuilds via the audit-dashboard.yml cron commit).

7. **Build `tools/swarm/pattern_miner.py` + hot/cold cell sidecar.**
   Per Section E. Stitch it into the tail of `weekly_review.py`. Output: `audit_dashboard/data/swarm_pattern_cells_latest.json`. Exit: sidecar JSON is schema-valid, dashboard panel renders the two tables.

8. **Add prompt-injection hook for next-week swarm fanouts.**
   When the bake-off / persona swarm is invoked, read `swarm_pattern_cells_latest.json` and prefix the prompt with `BIAS HINT: ...`. Exit: prompt-template diff shows the auto-prefix; one round of swarm picks runs cleanly with the hint injected.

9. **Per-pick detail page.**
   `audit_dashboard/swarm_pick_detail.html` — a thin template that loads `?id=<pick_id>` from `swarm_picks.json` and renders the per-model justification grid + entry/exit chart-snapshot from TV. Exit: click-through from the main panel works; mobile-readable.

10. **Cron the resolver + reviewer.**
    Add two workflows: `swarm-resolver.yml` (hourly, runs `outcome_resolver_swarm.py`) and `swarm-weekly-review.yml` (Mondays 06:00 UTC, runs `weekly_review.py`). Both follow the `audit-dashboard.yml` `[skip ci]` commit pattern. Exit: two `.github/workflows/swarm-*.yml` files committed, both green on first scheduled run.

**Tasks 1-4 are pre-production** — they create artifacts and reports but don't change `/audit`. Task 5 wires the live recorder. Task 6 surfaces it on the dashboard. Tasks 7-10 close the feedback loop.

---

## Section G — Open questions (need user input before implementation)

1. **Storage cap & rotation.** At ~14 picks/swarm × ~2 swarms/week ≈ 1.5k picks/year. Comfortably fits in a single JSON file (~3 MB). Confirm we keep a single file vs. monthly-shard (`swarm_picks_2026_05.json`). Sharding helps git-diff readability and dashboard load time at the cost of multi-file aggregation. **My recommendation: single file until it exceeds 5 MB.**

2. **SKIP-candidate recording.** The 30-symbol universe → 14-pick session means 16 candidates were SKIPped by the swarm. Should we persist those in `swarm_picks_skipped.json` so we can measure "did the swarm correctly skip losers"? **My recommendation: yes**, but only the aggregate vote (no per-model justifications) to keep file size in check.

3. **Persona vs. underlying-model identity.** On 2026-05-11 the "10 personas" were lenses applied to one or two underlying models (MOMENTUM_TECH and MACRO_BEAR were both Opus-4.7 with different system prompts). The leaderboard treats them as separate "models." Should we add `models_consulted[].underlying_model` (e.g., `"opus-4.7"`, `"qwen3-coder-480b"`, `"deepseek-v3.2"`) so the dashboard can roll up by **underlying model** as well as by **persona**? **My recommendation: yes** — adds one field, unlocks the bake-off's central question.

4. **Outcome resolver source-of-truth.** TV paper-trade fills are the only realistic feed (Binance/yfinance can disagree with TV's fill price on a stop). Confirm the resolver reads exclusively from TV MCP `data_get_trades` (with a fallback to manual transcript .MD only). **My recommendation: TV-only**, fail loudly if MCP unavailable rather than silently resolve with yfinance.

5. **Real-money gate.** Does any pick in `swarm_picks.json` ever cross into real-money via `papertrade → live` promotion, or is this strictly a paper-edge-discovery layer? If the former, the `account` enum needs a real-money flag and the resolver needs to support `MANUAL` exit-reasons for human overrides. **My recommendation: paper-only for v1**; real-money requires the 10-step Lopez de Prado readiness gate per `docs/PERFORMANCE_CHARTER.md` and is out of scope.

---

## Appendix — File touch-list (for v1 implementation)

**New files:**
- `audit_dashboard/data/swarm_picks.json`
- `audit_dashboard/data/swarm_picks_skipped.json`
- `audit_dashboard/data/swarm_leaderboard.json`
- `audit_dashboard/data/swarm_pattern_cells_latest.json`
- `audit_dashboard/schemas/swarm_pick.schema.json`
- `audit_dashboard/schemas/swarm_leaderboard.schema.json`
- `audit_dashboard/swarm_pick_detail.html`
- `tools/swarm/outcome_resolver_swarm.py`
- `tools/swarm/weekly_review.py`
- `tools/swarm/pattern_miner.py`
- `tools/swarm/picks_recorder.py`
- `.github/workflows/swarm-resolver.yml`
- `.github/workflows/swarm-weekly-review.yml`
- `reports/swarm_review/2026_19.md` (and forward)

**Edited files (production-impact; require contract-review first):**
- `audit_dashboard/template.html` (NEW panel under AI Challenge section)
- `audit_trail/dashboard_generator.py` (register `swarm_picks.json` source + paper-only flag)
- `tools/swarm/schema_validate.py` (new schema variant)
- `tools/swarm/swarm_dispatch.ps1` (call into recorder when picks are placed)

**Do not touch:**
- `index.html` (auto-generated; CLAUDE.md rule)
- `audit_dashboard/data/ai_challenge_*_active_picks.json` (curator panel is a separate dimension)
- `alpha_engine/outcome_resolver.py` (swarm resolver is a separate file — do not pollute the production resolver per the bug class in `feedback_noncrypto_resolver_live_close_bug`)

---

## Free-data-source budget (per constraint)

All resolution / regime / context data must come from free sources only:
- **Crypto price + fills:** TradingView MCP (primary), Binance public API + 3+ fallback chain (CoinGecko / KuCoin / CryptoCompare) per CLAUDE.md "API Failover Rule"
- **Equity / ETF / Bond fills:** TradingView MCP (primary), Yahoo Finance (`yfinance`) fallback for close prices only
- **FX:** TradingView MCP + Yahoo Finance FX pairs
- **Macro/regime:** FRED (free tier), `live_market_regime.json` (already in repo)
- **Sports (if added later):** the-odds-api free tier, ESPN public scoreboard

No Bloomberg, Refinitiv, Polygon paid tier, Tradier paid, or other paid sources at any layer.

---

End of design.
