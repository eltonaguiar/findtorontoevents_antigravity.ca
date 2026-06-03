# Affected Portfolios — Resolver Artifact Impact (2026-06-03)

**Source**: `reports/ai_tournament_winrate_audit_2026-06-03.md` + live DB verification + transcript cross-review (claude-opus-4-7-c9b9 session).

**Summary**: The AI tournament resolver (`tools/ai_tournament/price_tracker.py:resolve_pick`) is a once-daily spot-price snapshot with no intrabar high/low path. This inflates win rates for the 6 models ≥70% WR (fireworks_qwen 90.3%, gpt4o_mini 90.9%, gemini_25_pro 87.5%, together_deepseek_v3 87.5%, hyperbolic_llama 78.1%, nvidia_minimax_m2 73.5%). LONG picks show 87% WR vs SHORT 33% — regime drift, not edge. n_resolved per model is 31–49 (<100 "proven" bar). Data is only 4–14 days old.

This artifact affects any portfolio/leaderboard that consumes `tournament_picks` or the leaderboard JSONs derived from it.

---

## Portfolio Families — Impact Classification

| Family | Source | Resolution Method | Affected? | Evidence | Recommended Note Location |
|---|---|---|---|---|---|
| **AI Tournament family** (`pf_portfolio_deepseek_v4__aggressive`, `pf_portfolio_gpt4o_mini__*`, etc.) | `tools/portfolios/run_daily.py` + `export_json.py` reading `tournament_picks` + `ai_tournament_leaderboard.json` | `price_tracker.resolve_pick` (daily snapshot, no intrabar) | **YES — FULLY AFFECTED** | 977 OPEN rows across 50 models; 0 closed in 7d window before recent resolver fixes; inflated WR/PF directly visible on `/audit/ai-tournament.html` and per-model drill pages | `reports/ai_tournament_winrate_audit_2026-06-03.md` (already written) + banner on `ai-tournament.html` + `model.html` |
| **portfolio_mix__* family** (`pf_portfolio_portfolio_mix__aggressive_top5`, `balanced_top3`, etc.) | Same `run_daily.py` / `export_json.py` pipeline but seeded from `PF_POSITION` table (not tournament_picks) | `prices.get_close` + `engine.mark_position` (live yfinance fetch) | **NOT AFFECTED** | Uses real-time prices; PR #488 + #494 fixed the MtM columns; live JSON now shows `current_price`, `unrealized_pnl_pct`, `weight_pct` | None required (already clean) |
| **Verified pilots** (`macd_rsi_m048`, `etf_verified_dual_momentum`) | `verified_strategies/paper_pilot/*_pilot.py` + `*_state.json` | Direct DB `trading_picks` status (WON/LOST) or intrabar resolver in `outcome_resolver_swarm.py` | **NOT AFFECTED** | Separate resolution path; shadow trackers only; promotion gate (`audit_trail/promotion_gate.py`) is deny-by-default in SHADOW mode | `verified_strategies/paper_pilot/macd_rsi_m048_pilot.py` docstring + `EAGLE_JUNE2_2026-06-02_CLAUDE_OPUS_4_7.MD` |
| **Hyrotrader / swarm_picks** | `audit_dashboard/data/swarm_picks.json` + `outcome_resolver_swarm.py` | Intrabar OHLC (yfinance high/low or Binance klines) | **NOT AFFECTED** | Uses `fetch_high_low` + `_check_tp_sl_intrabar`; different resolver entirely | None required |
| **Copy-trader / non-crypto consensus** | `copy_trader_intel/data/*_copytrader_picks.json` + `copy_trader_intel/outcome_resolver.py` | Binance spot + yfinance | **NOT AFFECTED** | Separate resolver; not wired through tournament price tracker | None required |
| **Forward-test / paper pilots** (`alpha_engine/forward_test_portfolios.py`, `crypto_test_portfolios.py`, etc.) | `alpha_engine/data/active_picks.json` + `forward_test_portfolios.py` | `fetch_price` (multi-source) + `mark_position` | **NOT AFFECTED** | Independent price fetch; not tournament-derived | None required |

---

## Per-Module Notes (for future agents)

**`tools/ai_tournament/price_tracker.py:217`** — The root cause. `resolve_pick` fetches ONE current spot price per day, checks `current_price >= tp` BEFORE `current_price <= sl`, has NO intrabar high/low path, and books P&L at the barrier price. This is the single source of the 73–91% WR inflation.

**`tools/ai_tournament/resolve_db_picks.py:41`** — Re-uses the exact same `resolve_pick` function for the production DB path. Any fix here must also be applied to `price_tracker.py`.

**`audit_dashboard/ai-tournament.html:182-189`** — DISPUTED banner already present (added 2026-06-03). Do not remove without intrabar OHLC resolution + n≥100 per model.

**`audit_dashboard/model.html:180-184`** — Reads `?id=` param and filters `ai_tournament_picks_latest.json`. The banner on the parent page (`ai-tournament.html`) is sufficient; no duplicate banner needed here.

**`alpha_engine/production_scanner.py:5629-5640`** — Promotion gate (`is_admissible_for_production`) is already wired and runs in shadow mode (`PROMOTION_GATE_ENFORCE` env-flag). Tournament models are currently excluded because they are not in `PROMOTED_STRATEGIES`. This is the correct behavior.

**`tools/portfolios/export_json.py:119-144`** — The portfolio JSON generator. After PR #494 the MtM columns are populated for the `portfolio_mix__*` family. The `pf_portfolio_deepseek_v4__aggressive` family (tournament-derived) still shows the resolver artifact in its WR/PF columns — this is expected and documented.

**`verified_strategies/paper_pilot/macd_rsi_m048_pilot.py`** — The only honest promotion candidate currently in shadow. Day-30 review is ~2026-07-02. Do not promote any tournament model until the resolver is fixed and n≥100 path-verified resolutions exist.

---

## Recommended Operator Actions (from transcript + this review)

1. **Do not size any of the 6 Tier-1 tournament models on real money** until (a) intrabar OHLC resolution is live and (b) n≥100 path-verified resolutions per model.
2. **Continue the two live shadow pilots** (`macd_rsi_m048` + `etf_verified_dual_momentum`) — they use independent resolution paths and are the only credible near-term promotion candidates.
3. **Wire the dead-letter field** `correlation_adjusted_size_usd` (written by `production_scanner.py:5831`) into `position_multiplier` if you want the Phase 4 cluster-exposure card to show real data (currently all zeros because the field is never read).
4. **Replace the 5 hardcoded clusters** in `risk_controls.py` with a live correlation matrix (the institutional pattern) — the current coverage leaves ~95% of the universe in UNCATEGORIZED.

---

**Filed**: `reports/affected_portfolios_resolver_artifact_2026-06-03.md`
**Companion audit**: `reports/ai_tournament_winrate_audit_2026-06-03.md`
**Live banner**: `audit_dashboard/ai-tournament.html:182-189`

No further action required on this note unless the resolver is fixed or a new portfolio family is added that consumes `tournament_picks`.