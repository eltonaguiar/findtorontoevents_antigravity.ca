# Pipeline Map — every gate, in order

Verified against the repo 2026-05-18. All paths under `e:\findtorontoevents_antigravity.ca\`.

## Stage 1 — EMIT (where picks originate)

No single scanner. Dozens of emitters write per-source JSON; `collect_all_picks()`
(`audit_trail/dashboard_generator.py:8163`) merges them.

| Module | Asset class | Output |
|--------|-------------|--------|
| `alpha_engine/production_scanner.py` | CRYPTO, stamps FOREX/EQUITY | `alpha_engine/data/premium_signals.json`, `active_picks.json`, `closed_picks.json` |
| `alpha_engine/scanner.py` | multi-class | scan reports |
| `alpha_engine/antigravity_strategies.py` | CRYPTO/multi | `audit_dashboard/antigravity_picks_data.json` |
| `alpha_engine/tradingagents_emitter.py` | multi | per-source JSON |
| `alpha_engine/{etf,bond,commodity,forex,equity}_*.py` | ETF/BOND/COMMODITY/FOREX/EQUITY | `audit_dashboard/data/forex_futures_picks.json` + backtest JSONs |
| `copy_trader_intel/*_scraper.py` | CRYPTO (CEX whale copy) | `copy_trader_intel/data/*` |
| `coinglass_strategies/scanner.py` | CRYPTO (derivatives) | `coinglass_strategies/data/*` |

## Stage 2 — INGEST

`collect_all_picks()` merges every per-source JSON → returns `(active, closed,
all_closed_including_expired)`. Picks also land in MySQL `at_raw_picks` (the core ledger).

## Stage 3 — ACTIVE GATE  `quality_gates.passes_active_gate()`  (`quality_gates.py:5774`)

Dashboard-visibility / execution admission. Order (every gate is env-kill-switchable, fail-open):

| Order | Gate | Line | Rejects |
|-------|------|------|---------|
| 1 | A1 meta-labeler | 5784 | shadow; enforces only if `META_LABEL_GATE_ENFORCE=1` |
| 2 | M-049 safety STOP | 5806 | ALL picks when `safety_status=STOP` |
| 3 | M-108 magnitude-sanity | 5819 | move % outside `MAX_MOVE_PCT_BY_CLASS` |
| 4 | FOREX directional | 5835 | FOREX LONG without elite≥75 & conf≥0.75 |
| 5 | FOREX symbol | 5859 | NZDUSD/EURJPY/USDCHF |
| 7 | penny/meme class | 5893 | |
| 8 | BLOCKED_SOURCE_SYMBOL_PAIRS | 5902 | cta_replicator CL=F/NG=F/ZC=F |
| 10 | kill gate | 5946 | `kill_gate.evaluate_kill` |
| 11 | CRYPTO dynamic quarantine | 5974 | reads `crypto_quarantine.json` |
| 13 | CRYPTO confidence guards | 6023-6107 | conf>0.90, inversion sources, `CRYPTO_MAX_CONFIDENCE` |
| 14 | M-036/037 | 6140/6166 | CRYPTO BUY-direction; ml_score < `MIN_ML_SCORE_CRYPTO` (0.65) |
| 15 | KS concept-drift auto-pause | 6269 | pauses CRYPTO+FOREX when KS_D > ratio |
| 16 | M-013 concentration cap | 6305 | per-symbol % share over class cap |
| 19 | BLOCKED_ACTIVE_TRUST_TIERS | 6410 | BANNED/AVOID — **bypassed for all non-CRYPTO** |
| 20 | FOREX SHORT-only | 6501 | blocks ALL FOREX LONG |
| 21 | EQUITY elite_score ≥55 | 6552 | low-elite equity |
| 21 | ETF_BLACKLIST / COMMODITY_BLACKLIST | 6603/6620 | IWM, GLD, CT=F, etc. |
| 22 | wf_verdict=FAILING | 6635 | walk-forward failing |
| 23 | elite_grade F hard block | 6751 | grade-F (BOND/ETF + commodity_cot/cta_replicator exempt) |

Rejections are logged to MySQL `at_filter_log` (REJECT rows only — no PASS rows).

## Stage 4 — SMART GATE + SCORE

`passes_smart_gate()` (`quality_gates.py:7545`) **first calls `passes_active_gate`**
(so Smart ⊆ Active), then adds: per-class score/WR floors (`ASSET_CLASS_SMART_THRESHOLDS`
@7726), `forward_validated=true` required @7749 (COMMODITY/ETF/EQUITY source exemptions),
CRYPTO Smart = LONG-only @7757, FOREX FwdWR≥50 @7789.

`calculate_smart_score()` (`quality_gates.py:8399`) — 0-100 ranking (NOT a gate):
base 30 + R:R quality 15 + strategy forward-WR 15 + PSR/trust 12 + confidence sweet-spot 10,
minus penalties. The dashboard keeps the **top 50** by smart_score (`dashboard_generator.py:16988`).

## Stage 5 — HIGH CONVICTION  `passes_high_conviction_pick()`  (`tools/dashboard_hc_rules.py:368`)

Gates 1-9 + a stamped-tier supplemental path. JS twin: `audit_dashboard/hc_filter.js`
(`evaluateHcGates1to9` @329, `passesHighConvictionPick` @499). Config:
`config/hc_gate_params.json` (scoreAbsoluteFloor 40, scoreCompoundFloor 50,
per-class FWD-WR floors crypto 40 / equity 50 / forex 55, confidenceMax 0.90,
trust-tier blacklist SANDBOX/UNPROVEN/PROBATION/DEMOTED). Tiers S/A/B from
`config/hf_conviction_tiers.json`. `filterHcStrict` also rejects COMMODITY/BOND/ETF/FUTURES
via `filterValidatedEdgePerClass` (`hc_filter.js:12902`).

## Stage 6 — CONSENSUS

Multi-source agreement collapses raw picks into `at_consensus_picks`
(columns `agreement_count`, `consensus_tier`, `classification`). Past-week survival
is low: ~35 CRYPTO open, ~2 EQUITY open.

## Stage 7 — OUTCOME

- `alpha_engine/outcome_resolver.py` — resolves closed picks, `PNL_WIN_THRESHOLD_BY_CLASS`
  (CRYPTO 0.1bp, others 5bp), writes `closed_picks.json` + `at_raw_picks.status/pnl_pct`.
- `alpha_engine/forward_validator.py` — CRYPTO forward-validation, stamps `forward_validated`.
- `walkforward_validator.py` — produces `wf_verdict`.

A pick is **active** when `status ∈ {OPEN,ACTIVE,PENDING,LIVE,""}`. Closed picks render
as `picks.recent_closed` in the payload.

## Money Ready (per-CLASS verdict, not a pick filter)

`alpha_engine/money_ready_verdict.py::money_ready_verdict()` — per asset class:
n≥50, WR≥0.55 (EQUITY 0.52 / CRYPTO 0.50), PF≥1.5, DSR≥0.95, PBO≤0.55 (≥5 strategies),
SPA α=0.10, symbol concentration ≤0.60. Verdict ∈ MONEY_READY / WATCH / NOT_READY /
INSUFFICIENT_DATA. Snapshot: `audit_dashboard/data/money_ready_verdict.json`.

**UX bug (2026-05-18):** the `/audit` "💰 MONEY READY" *button* (`#btn-money-ready`,
`template.html:1309`) is orphaned — `applyMoneyReady()` in `money_ready_filter.js:174`
calls undefined `window.renderActive` and no render path consults `_moneyReadyActive`
or calls `filterMoneyReady()`. The Money Ready *tab* (`#tab-moneyready`) works.

## Dashboard generation

`audit_trail/dashboard_generator.py::generate()` (@13684) → `collect_all_picks` → enrich
→ smart picks (@16967) → money_ready_verdicts (@16147) → `build_html()` writes
`audit_dashboard/data/dashboard_data.json` (17.4 MB — exceeds the 8 MB embed threshold,
so the live page fetches it externally) + `audit_dashboard/index.html`.
**Never run generators locally** — they overwrite live HTML. `py_compile` only.
