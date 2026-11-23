# 13 PREDICTION_MARKET

Central question: is this a measured asset class or a label on crypto spot trades, and can any of
its bets actually be settled?

## 1 Identity
[SRC: alpha_engine/money_ready_verdict.py:239] Not one of the canonical classes. `CANONICAL_ASSET_CLASSES` is the eight names CRYPTO, EQUITY, COMMODITY, ETF, FOREX, BOND, FUTURES, MUTUAL_FUND.
[SRC: _raw/audit_data_money_ready_verdict.json] Absent from `/audit`'s classes (11 keys) and from its readiness table (11 keys).
[SRC: _raw/audit3_audit3_ledger.json:16885] No class bucket in the ledger either: the PM trades are filed under CRYPTO as strategy `prediction_market_consensus`.
[SRC: audit_trail/pm_contract_resolver.py:156] The name exists in code only as a contract marker (`asset_class in {"PREDICTION_MARKET", "PREDICTION_MARKETS", "EVENT_CONTRACT"}`).
[SRC: tools/pm_macro_expansion.py:172] And as an emitter tag from the macro-expansion tool.
So it is an adjacent signal source, not a first-class class: it has no verdict surface of its own, and every number it produces is counted under CRYPTO or under a source family.

## 2 What the class is
A binary contract ("Will X happen?") on Polymarket or Kalshi. It has no spot price and no meaningful TP/SL; it settles at 1.0 if the side bought is correct and 0.0 otherwise [SRC: audit_trail/pm_contract_resolver.py:22]. Instruments in this repo are crypto up/down series and macro contracts (Fed decision, CPI, GDP, index levels) [SRC: tools/pm_macro_expansion.py], plus sports series in the Kalshi snapshots [SRC: data/kalshi_snapshots/20261123T064511Z.json:127]. Settlement is by market outcome at an expiry date, not by a price series.

## 3 Measured state
Headline: UNMEASURED for the class. No file on main carries a settled prediction-market contract.
[SRC: alpha_engine/data/pm_macro_expansion_picks.json:8] The only picks that carry `asset_class` PREDICTION_MARKET: 4 rows, all `status` OPEN, all `contract_side` YES, entry prices 0.9925 / 0.97 / 0.94 / 0.9 as probabilities, `pnl_pct` null on all four. Zero settled.
[SRC: data/pm_market_outcomes.json] Absent from the tree. The settle feed that `pm_contract_resolver` reads [SRC: audit_trail/pm_contract_resolver.py:59] and `pm_outcome_ingest` writes [SRC: audit_trail/pm_outcome_ingest.py:36] is not committed (and not gitignored: `git check-ignore` finds no rule for it), so the contract branch has no outcome to read.
[SRC: data/kalshi_snapshots/20261123T064511Z.json:127] Market inventory: 532 markets in the latest snapshot, 9054 rows across the 16 snapshots. Every row is `status` active, and yes_bid, volume, last_price and open_interest are null in all 9054. No settlement and no price.
[SRC: prediction_market_agents/data/pm_odds_history.jsonl] 27573 odds rows over 202 market ids (keys date, ts, platform, market_id, title, action, prob, volume), with no outcome field.
[SRC: reports/pm_calibration.json:15] Calibration coverage: 12 markets tried, 0 with price history.
[SRC: _raw/audit3_audit3_ledger.json:32599] The ledger's prediction_market family is the only PM number on any audit surface: n 2, WR 1.0 CI [0.3424, 1.0], PF n/a (n=2, net 10.0bp), net expectancy 2.3512 pct, single_source true, verdict INSUFFICIENT_N ("n=2 < 20: no statistical claim").
Under the label, spot-derived crypto trades (asset_class CRYPTO, not contracts):
[SRC: verified_strategies/paper_pilot/prediction_market_consensus_paper_log.jsonl] 110 rows, TP_HIT 87 / SL_HIT 16 / MANUAL 7, and entry_price, tp, sl are null on all 110, so the P&L cannot be reconstructed from the file. Computed from it: WR 84.47 pct (87/103) Wilson [76.25, 90.21], PF 13.198. One XRP row of +80.37 pct [:79] is 29 pct of gross wins; without it PF is 9.407.
[SRC: verified_strategies/paper_pilot/prediction_market_consensus_pilot.json:10] Pilot stats: 1016 picks, 837 resolved, 542 wins, 251 losses, 44 flats, wr 64.76, pf 2.0242, max_drawdown 69.17. Recomputed: WON/(WON+LOST) 68.35 pct Wilson [65.03, 71.49]; the published 64.76 divides by 837, so it counts the 44 flats as non-wins.
[SRC: reports/forward_paper_pilot_prediction_market_consensus_20260609T044529Z.json:10] Forward replay verdict REFUTED: true WR 38.2 pct, true PF 1.362 over 2627 replayed picks; the two sibling files give 44.8 pct on 830 and 38.0 pct on 3143.
None of these is a prediction-market win rate: each scores the underlying crypto perp.

## 4 Contradictions
[SRC: verified_strategies/paper_pilot/prediction_market_consensus_pilot.json:4] The pilot file says `promotion_ready` true, with `min_forward_n` 50 [:6].
[SRC: verified_strategies/paper_pilot/prediction_market_consensus_state.json:9] The state file says `promotion_ready` false, status ACTIVE_PAPER_PILOT, with `min_forward_n` 150 [:25].
[SRC: verified_strategies/paper_pilot/prediction_market_consensus_dashboard.json:12] The dashboard agrees with the state: `promotion_ready` false on n 110, wr 79.09, pf 13.198.
One strategy, two promotion verdicts and two minimum-n rules. The pilot's own max_drawdown 69.17 [:19] also exceeds the state's max_drawdown_pct 15.0 criterion.
[SRC: audit_trail/quality_gates.py:2045] A third view: the strategy is RETIRED because 23 DOGEUSDT SL_HIT rows carried POSITIVE pnl and one XRPUSDT row worth +80.37 pct was tagged SL_HIT (REPAIRED_PNL_CONTRADIC).
[SRC: verified_strategies/paper_pilot/prediction_market_consensus_paper_log.jsonl:79] The committed log's +80.37 pct XRP row is tagged TP_HIT, not SL_HIT. Same magnitude, opposite exit label; from main I cannot tell whether these are the same row.
[SRC: alpha_engine/config.py:369] The strategy is also on the unified kill list ("WR 26%, -29% intrabar").

## 5 Data integrity
[SRC: audit_trail/universal_pick_resolver.py:263] Six PM systems are registered in SYSTEM_SOURCES (:263-:268, plus pm_macro_expansion at :272), so the resolver does track them.
[SRC: audit_trail/universal_pick_resolver.py:1011] `_is_prediction_market_pick` then classifies them.
[SRC: audit_trail/universal_pick_resolver.py:1027] For a non-contract PM pick it synthesises the entry from the spot price and TP/SL at 2.5 / 1.5 pct. That is how PM picks get resolved: as spot trades on the underlying.
[SRC: audit_trail/universal_pick_resolver.py:1487] Contract picks are routed to `pm_contract_resolver` instead, which settles only from a known market outcome and otherwise expires with `pnl_pct` None [SRC: audit_trail/pm_contract_resolver.py:17].
So the spot-derived picks resolve, and their win rate is a crypto win rate. The contracts do not resolve, because no outcome feed is on main; an unresolvable class cannot have a win rate.
[SRC: .github/workflows/audit-dashboard.yml:139] The ingest step runs in CI with a non-fatal fallback, and its output is not committed, so the feed exists only inside a run.
[SRC: reports/forward_observations.jsonl] 449 forward rows exist, and none names a prediction-market system.

## 6 Cost reality
[SRC: audit_trail/pm_contract_resolver.py:22] Contract cost is the entry probability with payout 1.0/0.0, so a win at 0.97 pays (1-0.97)/0.97 = 3.09 pct gross and a loss is -100 pct [SRC: audit_trail/pm_contract_resolver.py:166]. No venue fee is subtracted.
[SRC: alpha_engine/cursor_statistical_framework.py:57] The only PREDICTION_MARKET cost constant is a framework default, spread 20.0, commission 100.0, impact 1.0, i.e. 110 bp one-way; it is a placeholder, not a measurement.
[SRC: alpha_engine/money_ready_verdict.py:270] SLIPPAGE_BPS has no PREDICTION_MARKET key, so it would fall back to the 10 bp default [:280], a spot-equity number.
[SRC: _raw/audit3_audit3_ledger.json] The ledger's `slippage_pct_by_class` has no PM key either; the n 2 family is costed at 0.1 pct, with no PM-specific constant (the CRYPTO class constant is 0.0996).
Kalshi/Polymarket fee schedules, bid-ask spread and settlement fees are UNMEASURED: none of the four generators models them. Because the gross win on a 0.97 contract is 3.09 pct, a fee of that size flips the sign, so the missing cost is decisive rather than cosmetic.

## 7 What would change the verdict
One experiment: run `pm_outcome_ingest`, commit `data/pm_market_outcomes.json`, and settle the macro-expansion contracts against it. Gate: at least 100 settled contracts with payout-honest P&L and a net PF CI-LB above 1.0 (the ledger's proven_min_n is 100). Falsifier: if fewer than 100 contracts settle, or the settled net PF CI includes 1.0, the class stays UNMEASURED.

## 8 Blunt answer
UNKNOWN, not investable and not yet disprovable: as a binary-contract class it has zero settled contracts on main, so there is no prediction-market win rate to report. The only edge-like numbers under the label come from spot crypto trades, and those were REFUTED forward (38.2 pct true WR) and retired.

Least survivable number: the ledger's PM family WR 1.0 at n 2 [SRC: _raw/audit3_audit3_ledger.json:32599]. Two wins is not a win rate, and it is the number a dashboard would quote.

## 9 Cross-check against /audit and the database
[SRC: _raw/audit_data_dashboard_data.json] `/audit` lists pm_kalshi_re_signals, pm_kalshi_signals, pm_macro_expansion, pm_momentum_signals, pm_polymarket_re_signals, pm_whale_signals, polymarket_signals and prediction_market_consensus; every one has resolved null, wins 0, losses 0, win_rate 0.0, and pm_whale_signals is `empty`. Its only two closed PM rows are XRP +2.4512 and DOGE +2.4513 pct, both TP_HIT, both asset_class CRYPTO, source_system alpha_engine.
[SRC: _raw/audit3_audit3_ledger.json:1541] The denylist logged 112 hits for prediction_market_consensus out of 269 total between 2026-11-19 and 2026-11-22, the largest single strategy.
[SRC: reports/forward_paper_pilot_prediction_market_consensus_20260609T044417Z.json:11] The three replay files disagree with each other (true PF 0.069, 1.329, 1.362), so even the proxy has no stable number.

## Provenance
- model: none (curator-written from origin/main at db3f0d02 and its committed files)
- prompt: none
- snapshot: the /audit3 and /audit payload numbers are quoted from `_raw/` as frozen on 2026-11-22, not re-fetched
- not measured: settled binary contracts (none on main), venue fees and spreads, any PREDICTION_MARKET class metric
