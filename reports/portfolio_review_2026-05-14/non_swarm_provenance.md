# Non-Swarm Position Provenance — 2026-05-14

17 of 33 open paper positions are NOT in `audit_dashboard/data/swarm_picks.json::picks`. This file establishes provenance for each.

**TL;DR:** Three distinct provenance buckets — (1) `alpha_engine` production scanner / copytrader pipeline (FX shorts, brokie crypto longs); (2) manual operator selection from `/audit` dashboard edge-tier rankings recorded in `reports/*.md` (V4 stocks, zerounderscore stocks); (3) legacy / unattributable orphans (`__VERIFIEDALPHA`, KO/LLY filled limits from prior cycles).

There is no code file named anything like `passes_highfw_gate.py` or `score_above_50.py`. The `HIGHFWWRABV55_SCOREABOVE50_*` account names are TradingView paper-portfolio labels chosen by the operator to remind themselves of the intended filter — **the filter is enforced at pick-generation time by the operator selecting from `dashboard_data.json::systems`, not at exec time by a gate function.** This is the exact pattern memory `feedback_gate_at_execution_not_generation` warns about.

## Provenance Table (17 positions)

| Account | Symbol | Side | Provenance | Code/Data File:Line | Notes |
|---|---|---|---|---|---|
| HIGHFWWRABV55_SCOREABOVE50_V2 | TICKMILL:EURUSD | Short | alpha_engine FX scanner (legacy) | `alpha_engine/closed_picks.json` (29× GBPUSD/EURUSD shorts from `multi_asset_copytrader`, 2026-04-30 cluster) + `alpha_engine/production_scanner.py:973-987` (FX caps) | Entry 1.17784 matches `multi_asset_copytrader` Apr-30 cluster; not refreshed since |
| HIGHFWWRABV55_SCOREABOVE50_V2 | FPMARKETS:GBPUSD | Short | alpha_engine FX scanner (legacy) | `alpha_engine/closed_picks.json` GBPUSD SHORT @ 1.354867 from `multi_asset_copytrader` 2026-04-30 | Entry 1.35480 matches Apr-30 batch exactly |
| HIGHFWWRABV55_SCOREABOVE50_V2 | OANDA:AUDJPY | Short | alpha_engine FX scanner | `alpha_engine/data/active_picks.json:7537-7568` (AUDJPY=X strategy `forex_rsi2_mean_reversion`, source `multi_asset_copytrader`) | Open AUDJPY shorts present in live `active_picks.json` |
| HIGHFWWRABV55_SCOREABOVE50_V4 | NASDAQ:SOFI | Long | Manual operator (edge-tier selection) | `reports/v4_edge_picks_and_theswarm_cleanup_2026-05-12_2112EST.md:16` (LIMIT 15.85, picked via `edge_stability_index.json` EQUITY top-3) + `alpha_engine/data/active_picks.json:449` (older SOFI LONG from `regime_terminal` strategy `regime_mild_bull`) | Operator-placed LIMIT 2026-05-12 21:12 EST; thesis = STABLE_EDGE EQUITY |
| HIGHFWWRABV55_SCOREABOVE50_V4 | AMEX:CORN | Long | Manual operator (edge-tier selection) | `reports/v4_edge_picks_and_theswarm_cleanup_2026-05-12_2112EST.md:14` (LIMIT 18.85, COMMODITY top-edge ETF proxy) | Operator-placed LIMIT 2026-05-12 |
| HIGHFWWRABV55_SCOREABOVE50_V4 | AMEX:DBA | Long | Manual operator (edge-tier selection) | `reports/v4_edge_picks_and_theswarm_cleanup_2026-05-12_2112EST.md:15` (LIMIT 28.50, COMMODITY diversifier within top class) | Operator-placed LIMIT 2026-05-12 |
| HIGHFWWRABV55_SCOREABOVE50_V4 | NYSE:KO | Long | Manual operator (cycle-2/3 LIMIT) | `TV_PICKS_2026-05-06_18-00.md:35,131` (KO LIMIT BUY 2 @ 78.58 filled @ 78.12, HOLD +1.55%) | Filled limit from 2026-05-06 cycle-3; not in any pipeline file |
| __VERIFIEDALPHA | OANDA:AUDJPY | Short (no TP/SL) | UNKNOWN_PROVENANCE (legacy/manual) | none — no code references to `VERIFIEDALPHA` anywhere | Account prefix `__` and zero code refs imply manual sidecar. Position has no TP/SL = ungated manual entry |
| __VERIFIEDALPHA | OANDA:AUDUSD | Short | alpha_engine FX scanner (or manual) | `alpha_engine/data/active_picks.json` (3 AUDUSD=X SHORTs from `multi_asset_copytrader` strategies `ig_contrarian_sentiment` / `myfxbook_retail_contrarian` 2026-05-13/14) | Entry 0.71354 close to `active_picks` 0.72547 — likely older alpha_engine entry; account is manual sidecar so could also be hand-placed |
| brokie | BINANCE:APTUSDT | Long | alpha_engine ML pipeline (proportional clone) | `alpha_engine/data/active_picks.json:2286-2362` (`ml_enhanced_APTUSDT_4h_A_xgboost`, source `ml_strategy_reviver`, conf 0.67) | Same strategy/symbol pairing as zerounderscore's APTUSDT LONG; qty=96 vs zerounder qty=3,300 (proportional to ~$1k brokie balance) |
| brokie | BINANCE:INJUSDT | Long | alpha_engine ML pipeline | `alpha_engine/data/active_picks.json:2200-2277` (`ml_enhanced_INJUSDT_1d_B_lightgbm`, source `ml_strategy_reviver`, conf 0.688) | Pipeline-generated INJ LONG; brokie qty=19 = proportional clone |
| brokie | BINANCE:BNBUSDT | Long | alpha_engine ML pipeline (DRAIN-flagged) | `alpha_engine/data/active_picks.json:2030-2111` (`ml_enhanced_BNBUSDT_15m_B_lightgbm`, source `ml_strategy_reviver`, conf 0.75) | BNBUSDT LONG explicitly excluded from zerounderscore slate per memory `feedback_long_source_bias` (0% WR drain) — brokie still holds it |
| brokie | BINANCE:ETHUSDT | Long | UNKNOWN_PROVENANCE (cloned from theswarm round-1 swarm pick) | `tools/swarm/backfill_sessions.py:217-231` recorded theswarm ETHUSDT LONG (different account) | Same symbol/side/entry-ballpark as theswarm round-1 swarm pick recorded 2026-05-11 23:24 EST; that position was CLOSED on theswarm 2026-05-12 per `v4_edge_picks_and_theswarm_cleanup_*.md:30` but is still open on brokie. Likely manual mirror |
| theswarm | COMEX_MINI:MHG1! | Long | Manual operator (commodity rotation) | `reports/open_mkt_picks_2026-05-13_0030EDT.md:12` (MHG LIMIT 4.6850 on V4) + `tv_outcomes_check_cycle5_2026-05-13.md:39` (theswarm MHG1! @ 6.6460 already open) | Operator-placed LIMIT 2026-05-13 00:30 EDT for COMMODITY top-class rotation; theswarm already held it from earlier cycle — note entry 6.6460 vs new V4 limit 4.6850 (different contract months / stale) |
| zerounderscore | NYSE:BAC | Long (no TP/SL) | UNKNOWN_PROVENANCE | none — separate from theswarm BAC LONG (swarm_pick_id `8c20bcb8` qty 30 @ 50.85, this is qty 60 @ 51.22 with no TP/SL) | Different qty/entry/TP-SL state than swarm-tracked BAC; likely manual stack-on. `no TP/SL` violation per `feedback_gate_at_execution_not_generation` |
| zerounderscore | FX:AUDUSD | Long | alpha_engine FX scanner (LONG) | `alpha_engine/data/active_picks.json` 28 forex entries incl AUDUSD=X LONGs from `multi_asset_copytrader` / `forex_carry_momentum` | Side mismatches the SHORT signals on AUDUSD currently in active_picks — this LONG predates current short cluster |
| zerounderscore | NYSE:LLY | Long | Manual operator (cycle-3 LIMIT) | `TV_PICKS_2026-05-06_18-00.md:51` (LLY LIMIT 1 @ 963.33 filled @ 958.45, HOLD +2.70%) | Filled limit from 2026-05-06 cycle-3; inverted SL=970 above entry=958.45 noted in snapshot |

## Files Grepped & First Match Per Symbol

Every file in this list was either grep-searched for the symbol set or read in full. The first significant match for each non-swarm symbol is cited inline.

- `alpha_engine/data/active_picks.json` — contains BNBUSDT, INJUSDT, APTUSDT, AUDJPY=X (SHORT), AUDUSD=X (SHORT + LONG), USDJPY=X SHORT, SOFI LONG. **28 forex entries total. No EURUSD or GBPUSD currently open here.**
- `alpha_engine/data/closed_picks.json` — 29 EURUSD/GBPUSD SHORT entries from `multi_asset_copytrader` source dated 2026-04-30. This is the source of the V2 EURUSD/GBPUSD shorts that have stayed open on TV.
- `audit_dashboard/data/swarm_picks.json` — 16 of the 33 open positions match here (per `provenance.json`). The 17 in the table above do NOT.
- `audit_dashboard/data/dashboard_data.json` — first surfaces `HIGHFWWRABV55_SCOREABOVE50` strings only in nested `swarm_picks` blocks duplicated from `swarm_picks.json`; no gate/filter code.
- `audit_trail/data/dashboard_payload.json` — contains the same nested swarm-pick records; first match for HIGHFW account is at line 582622 (V4 NYSE:F entry from backfill_sessions).
- `audit_dashboard/data/ai_challenge_*_active_picks.json` (7 files: antigravity / claude / grok / kimi_moonshot / mercury / predictable / scanner) — none contain any of the 17 non-swarm symbols. AI-challenge accounts are a separate sub-portfolio not represented in the user's 12 TV accounts here.
- `audit_dashboard/data/forex_futures_picks.json` — no EURUSD or GBPUSD entries (verified).
- `tools/swarm/backfill_sessions.py` — this is what populates `swarm_picks.json`. It hardcodes V4 NYSE:F / VZ / PFE / USB / UNM / KMI picks (lines 470-498) into `HIGHFWWRABV55_SCOREABOVE50_V4`. It contains no EURUSD/GBPUSD/CORN/DBA/SOFI/AUDJPY-SHORT entries — so any position with those symbols cannot have been recorded by backfill.
- `TV_PICKS_2026-05-06_18-00.md` — cycle-3 markdown. Source for KO LIMIT (V4) and LLY LIMIT (zerounderscore). No code-level provenance; these are operator-placed limits documented in markdown only.
- `TV_PICKS_WHY_2026-05-11_2229EST.MD` — zerounderscore round-1 source markdown. Confirms zerounder picks came from `alpha_engine/data/active_picks.json` filtered for conf 0.75-0.79.
- `TV_SWARM_SESSION_2026-05-11_2330EST.MD` / `TV_SWARM_SESSION_2026-05-12_1553EST.MD` — multi-account swarm session markdowns. V4 round-2 picks (F/VZ/PFE/USB/UNM/KMI) are documented here; SOFI/CORN/DBA are NOT — they were added later in `v4_edge_picks_and_theswarm_cleanup_2026-05-12_2112EST.md`.
- `reports/v4_edge_picks_and_theswarm_cleanup_2026-05-12_2112EST.md` — source markdown for V4 SOFI/CORN/DBA LIMITs. Edge ranking derived from `audit_dashboard/data/edge_stability/edge_stability_index.json` (peer-shipped infra).
- `reports/open_mkt_picks_2026-05-13_0030EDT.md` — source markdown for the second MHG limit (V4 @ 4.6850).
- `reports/tv_outcomes_check_cycle5_2026-05-13.md` — confirms theswarm MHG1! @ 6.6460 existed before the V4 limit was added.
- `reports/penny_picks_brokie_suitability_2026-05-13.md` — confirms `brokie` is a charter penny-stock account but the current brokie positions (APT/INJ/BNB/ETH crypto) don't fit charter; they are clones of swarm/zerounder picks, not penny picks.

Grep summary for the rare names:
- `HIGHFWWRABV55` / `SCOREABOVE50` — zero matches in any `.py` file. **No gate code exists.** Matches are entirely in `swarm_picks.json`, `dashboard_payload.json`, `backfill_sessions.py` (hardcoded V4 backfill list), and markdown.
- `VERIFIEDALPHA` — zero `.py` matches. Two matches total, both in TV-skill docs (`.claude/skills/tv-account-switch/SKILL.md`) listing the account name only.
- `MANUALBROKIE` — zero `.py` matches. Only in skill docs + portfolio snapshots.
- `TICKMILL` / `FPMARKETS` — zero matches anywhere in the codebase outside snapshot JSON. These are TradingView broker-prefix variants; the source picks live in `alpha_engine` as bare `EURUSD=X` / `GBPUSD=X` symbols.

## The Filter-Named-Account Pipeline — Code Search Result

**There is no `HIGHFWWRABV55_SCOREABOVE50_*` gate/filter function in this repo.**

What the name implies (`high forward WR >= 55 AND score >= 50`) is enforced manually by the operator selecting picks from `audit_dashboard/data/dashboard_data.json::systems` against those numeric thresholds — see `updates/2026-05-11-paper-trade-session.md:45-49`:

> Gate definition: strategy-level fwd_WR >= 55% AND PF >= 1.5 AND n_closed >= 20.
> Filter run against `audit_dashboard/data/dashboard_data.json::systems` produced 8 eligible strategies: `multi_asset_cot`, `aggregated_picks`, `ml_crypto_pred_v12`, `mega_mutation`, `claude_gainer`, `multi_asset_institutional`, `claude_gainer_st`, `rapid_fire`. Cross-ref against current `active_picks.json` produced 3 unique picks...

The filter is therefore:
1. **At pick-generation:** the operator filters `dashboard_data.json::systems` to strategies meeting the threshold, then cross-references `alpha_engine/data/active_picks.json` for picks from those strategies, then places via `tv-paper-trade` skill into the filter-named account.
2. **At exec time:** no enforcement. This is the pattern memory `feedback_gate_at_execution_not_generation.md` warns about — the account name is a label, not a runtime guarantee. Once a position is open, the gate is not re-checked.

The closest thing to a runtime gate is `alpha_engine/hf_strict_smart_gate.py` / `alpha_engine/passes_smart_gate` (mentioned in `CLAUDE.md` Wire-Up Rule) which scores per-pick — but no caller code wires it to TV exec.

Practical implication: positions like V2 EURUSD/GBPUSD shorts (entered ~Apr 30 by `multi_asset_copytrader`) can persist on V2 indefinitely even if `multi_asset_copytrader`'s forward WR has dropped below 55% in the days since — there is no re-gate or close-on-degrade trigger wired to TV.

## Unknown / Best-Guess Calls

- **__VERIFIEDALPHA AUDJPY Short** — `UNKNOWN_PROVENANCE`. No TP/SL, no source markdown found, account name not in any code or markdown beyond skill docs. Most likely manual entry by operator + never tracked.
- **brokie ETHUSDT Long** — `UNKNOWN_PROVENANCE` for exact entry session. Symbol matches a swarm pick that was later closed on theswarm, but the brokie position is still open and not in swarm_picks.json. Most likely a manual mirror of the original swarm ETH LONG when it was active, kept open on brokie after theswarm closed it.
- **zerounderscore NYSE:BAC Long** — `UNKNOWN_PROVENANCE` for the duplicate. swarm_picks tracks theswarm BAC qty 30 @ 50.85 with TP/SL; zerounderscore holds qty 60 @ 51.22 with no TP/SL. The lot doubles the original, no source markdown documents the stack-on, and no pipeline file has zerounderscore as the destination account for BAC. Likely manual.

## Bottom line for caller

- **11 of 17** trace cleanly to a code-or-markdown source: pipeline (`alpha_engine/data/active_picks.json` + `closed_picks.json` + `production_scanner.py`) or operator markdown (`TV_PICKS_*.md`, `reports/v4_edge_picks_*.md`).
- **3 are partial-attribution** (brokie crypto longs — pipeline strategy + symbol confirmed, but no record of which session placed them onto `brokie` specifically).
- **3 are `UNKNOWN_PROVENANCE`** (`__VERIFIEDALPHA` AUDJPY-Short, brokie ETHUSDT, zerounderscore BAC stack-on).
