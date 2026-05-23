# Portfolio Review — 2026-05-14 23:14Z

Multi-account TradingView paper book review. 12 portfolios captured, 33 open positions, weekly perf cross-referenced against `audit_dashboard/data/dashboard_data.json`.

## Actions executed this session

| # | Account | Symbol | Action | Status |
|---|---|---|---|---|
| 1 | `__VERIFIEDALPHA` | OANDA:AUDJPY Short | **CLOSED** (no SL + losing + cold FOREX week + unknown provenance) | ✅ realized −$1001 |
| 2 | `zerounderscore` | NYSE:BAC Long | **PROTECTED** — added TP 55.50 / SL 47.50 (was unprotected) | ✅ verified in table |
| 3 | `zerounderscore` | BINANCE:ADAUSDT Short | **SL tightened** 0.2894 → 0.2786 (BE+1pip, locks +2.55%) | ✅ verified |
| 4 | `theswarm` | BINANCE:POLUSDT Short | SL-tighten attempt 0.1036 → 0.0985 | ⚠️ order-ticket path didn't persist (existing-position SL needs different code path; see "Open Issues") |

US equity / ETF positions deferred — markets closed (NY 18:14 ET at session start). No CLOSE actions on those; they reopen Fri 13:30Z.

## Per-account snapshot (open positions, 23:08Z)

| Account | n_pos | Σ UPnL | Notes |
|---|--:|--:|---|
| HIGHFWWRABV55_SCOREABOVE50 | 0 | — | idle |
| HIGHFWWRABV55_SCOREABOVE50_V2 | 3 | +$394.69 | EUR/GBP shorts winning, AUDJPY short losing |
| HIGHFWWRABV55_SCOREABOVE50_V3 | 0 | — | idle |
| HIGHFWWRABV55_SCOREABOVE50_V4 | 7 | +$5.45 | barely positive value-tilt book |
| _MANUALBROKIE_CONV_TRUST6p4 | 0 | — | flat |
| __MANUALBROKIE_STRONG_CONV | 0 | — | flat |
| __VERIFIEDALPHA | 1 (post-close) | −$30 | AUDJPY closed; AUDUSD short remains protected |
| TRUSTOURSCORE | 0 | — | idle |
| HYROTRADER | 0 | — | idle |
| brokie | 4 | +$6.51 | all crypto LONGs in green |
| theswarm | 13 | +$21.29 | most diverse + most swarm-tagged |
| zerounderscore | 4 | +$57 (post-protect) | LLY swing winner |

## Provenance summary

**16 / 33 open positions** match `audit_dashboard/data/dashboard_data.json::swarm_picks_data.picks` (account + symbol + direction). The other **17** came from one of:

- **Alpha-engine pipeline (8 positions)** — `multi_asset_copytrader` FOREX shorts (EURUSD, GBPUSD, AUDJPY, AUDUSD) + brokie's `ml_strategy_reviver` crypto LONGs. Lives in `alpha_engine/data/active_picks.json` + `closed_picks.json`.
- **Manual operator from edge-tier dashboard (6 positions)** — V4 SOFI/CORN/DBA/KO, zerounderscore LLY. Traced to `reports/v4_edge_picks_and_theswarm_cleanup_2026-05-12_*.md`. Operator pulls from `audit_dashboard/data/edge_stability/edge_stability_index.json`.
- **UNKNOWN_PROVENANCE (3 positions)** — `__VERIFIEDALPHA` AUDJPY (now closed), brokie ETHUSDT, zerounderscore BAC 60-share stack.

Full file: `reports/portfolio_review_2026-05-14/non_swarm_provenance.md`.

### Filter-named accounts (`HIGHFWWRABV55_SCOREABOVE50_*`)

**No gate code exists in the repo.** The filter is operator-applied at pick-time (filter dashboard `systems` for fwd_WR ≥ 55%, PF ≥ 1.5, n ≥ 20, then cross-ref `active_picks.json`). There is no runtime re-check after the position opens. Aligns with `feedback_gate_at_execution_not_generation` memory: a position can persist on the account even if its source-system's forward WR has since degraded. **Recommend wiring a daily reconciliation job** that closes any V*/HIGHFWWR position whose source-system has dropped below the filter floor.

## Weekly per-asset-class performance (last 7 days from `recent_closed`)

| Class | n_week | WR | PF | Σ PnL% | Top winner src | Worst src |
|---|--:|--|--|--|---|---|
| CRYPTO | 842 | 41.8% | 1.21 | +151.75% | `quan_engine` +55%, `kimi_riseoftheclaw` +51% PF 2.84 | `luxalgo_filters` −19.75%, `alpha_engine` −14.50%, `battleground` −12.96% |
| FOREX | 45 | 17.8% | 1.87 | +5.74% | `kimi_riseoftheclaw` 50% WR (n=10) | `signal_validation` ships zero-PnL rows (resolver bug) |
| EQUITY | 35 | 22.9% | 1.03 | +1.83% | `kimi_riseoftheclaw` +15.06% (n=17) | `multi_asset_copytrader` PF 0.33 |
| ETF | 15 | 53.3% | 1.60 | +6.07% | — | — |
| COMMODITY | 14 | 100.0% | inf | +70.22% | All wins on CT=F across 3 sources (likely double-counted signals) | — |
| TOTAL | 951 | 41.0% | 1.29 | +235.61% | — | — |

### Divergences vs CLAUDE.md all-time anchors (>10pp WR shift)

- **FOREX week 17.8% vs anchor 46.4% → COLD −28.6pp.** Validates the AUDJPY-close decision.
- **EQUITY week 22.9% vs anchor 52.7% → COLD −29.8pp.** Justifies waiting on equity closes (let intraday volatility reset).
- **COMMODITY week 100% vs anchor 46.9% → +53pp HOT — but 14 trades is noise.** Don't chase.

Full file: `reports/portfolio_review_2026-05-14/weekly_asset_class_perf.md`.

## Per-model deepdive — surprise finding

The "swarm" is **NOT** a multi-model ensemble. Every `models_consulted[*].underlying_model` across all 38 picks in `swarm_picks_data.picks` is `claude-opus-4-7`. Differentiation is by *persona* (system-prompt role), not by underlying model.

Per-persona rationale-grounding (does the model cite specific numeric inputs vs hand-wave?):

| Persona | data-grounded % | volume |
|---|--:|--:|
| `V4_VALUE_SCREENER_SWARM` | 100% (cites P/E, div %, FCF $) | low |
| `FOREX_RESEARCH_SWARM` | 50% (rate diff, EMA, swap pips) | low |
| `ONCHAIN_QUANT` | 33% (name promises on-chain — content doesn't deliver) | medium |
| `FUND_VALUE` | 30% | medium |
| `NEWS_FLOW` | 12.5% | high |
| `MOMENTUM_TECH` | 13.3% | highest |

**Resolved picks (n=5):** 2W/3L. Both winners were LONG 1W non-crypto (USO ETF +4.33%, MCL1! WTI +2.85%). The biggest loser (`a0ceea8c` ONDOUSDT −4.27%) came from `trio_bot` whose rationale was self-referential meta ("trio_bot elite=100") with zero market data — cleanest rationale-quality-vs-outcome correlation in the sample.

Missing field: `data_sources_used`. Recommend adding to every pick so the next audit has real provenance for "did the model actually check the data" instead of regex-on-rationale heuristics.

Full file: `reports/portfolio_review_2026-05-14/swarm_model_deepdive.md`.

## Open issues / follow-ups

1. **POLUSDT SL-tighten didn't persist.** Order-ticket-based modify (`order-ticket-take-profit-input` + `place-and-modify-button`) works for adding TP/SL when none exists (BAC) but doesn't overwrite existing-position SL via the bracket-input path. Need to either (a) drag the SL chart line via JS, or (b) right-click the position row and use a different modify dialog. Add to `tv-debug` skill as a known gap.
2. **`signal_validation` source ships zero-PnL FOREX and `stocksunify2` zero-PnL EQUITY** — unresolved-pnl pollution per `feedback_noncrypto_resolver_live_close_bug`. Existing known issue; flagging that it inflates WR/PF this week (PF 1.87 FOREX looks robust but 27/45 trades are bogus zeros).
3. **`performance.asset_class_health.wr_pct / pf / pnl_pct` are NULL in payload** — only `resolved_n` populated. `audit_trail/dashboard_generator.py` should emit the computed metrics so the dashboard banner isn't blank. Filed against payload-contract drift.
4. **Active-picks `account` field is uniformly None** — provenance precision is limited to `(symbol, direction)` matching. Need pipeline to stamp the target paper account onto each active pick.
5. **The "swarm" is single-model with personas.** Either rename to "persona ensemble" or route different personas to genuinely different underlying models (Sonnet, Haiku, Grok, DeepSeek) for real diversity. Current setup is correlated noise dressed as ensemble.
6. **Per `feedback_gate_at_execution_not_generation` memory**: build a daily reconciliation job for filter-named accounts that closes positions when source-system filter no longer passes.

## New TV skills committed

To delegate future TV ops to other agents / Hermes:

- `.claude/skills/tv-cdp-launch/SKILL.md` — launch with port-bridge fallback (no admin needed)
- `.claude/skills/tv-account-switch/SKILL.md` — DOM-index click, dropdown auto-close gotcha, post-switch verify
- `.claude/skills/tv-positions-read/SKILL.md` — symbol-regex filter, Positions-tab pin, Unicode-minus normalize
- `.claude/skills/tv-close-positions/SKILL.md` — row-Close button, market-state gating
- `.claude/skills/tv-debug/SKILL.md` — full symptom→fix matrix
- `tools/tv_cdp_proxy.py` — userland 9222→9223 forwarder

Combined with the existing `.claude/skills/tv-paper-trade/SKILL.md`, the TV operations stack is now delegable.

## Files in `reports/portfolio_review_2026-05-14/`

| File | Purpose |
|---|---|
| `snapshot_*.json` | Per-account position snapshots (12 files) |
| `aggregate.json` | Cross-account position roll-up |
| `provenance.json` | Open positions × swarm_picks_data join |
| `portfolio_desc.txt` | Compact description used as swarm input |
| `swarm_model_deepdive.md` | Persona-level rationale audit |
| `weekly_asset_class_perf.md` | 7-day per-class WR/PF |
| `weekly_perf_raw.json` | Source aggregates for re-derivation |
| `non_swarm_provenance.md` | Where the 17 non-swarm picks came from |
| `FINAL_SYNTHESIS.md` | This document |
