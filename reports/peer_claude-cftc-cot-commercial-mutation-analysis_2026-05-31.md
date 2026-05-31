# cftc_cot_commercial_signal — Mutation Analysis & Disposition
**Slug:** cftc-cot-commercial-mutation-analysis
**Date:** 2026-05-31
**Author:** Claude Opus 4.7 (with Qwen-max consult)
**Incident:** INCIDENT_COMMODITIES #1 (P2) — "BLOCKED 19% WR on n=16"
**Status:** Recommendation = **REHAB via shadow-mode mutation, DO NOT permanently kill yet**

---

## 1. Live state verification (DB: ejaguiar1_stocks.trading_picks)

Query: `SELECT status, direction, COUNT(*), AVG(pnl_pct) FROM trading_picks WHERE strategy LIKE '%cftc_cot_commercial_signal%' AND category='commodity' GROUP BY status, direction`

| status | direction | count | avg pnl % |
|---|---|---|---|
| LOST | SHORT | 2 | -5.08 |
| OPEN | SHORT | 2 | (active) |
| TIME_EXIT | SHORT | 26 | 0.00 |
| TIME_EXIT | LONG | 4 | 0.00 |
| TP_HIT | SHORT | 2 | +4.76 |
| TP_HIT | LONG | 1 | +0.70 |

**Lifetime totals:** 37 picks · 3 wins · 2 losses · 30 TIME_EXIT washes · 2 OPEN
- **Decisive WR (TP_HIT vs LOST):** 3/5 = 60% (n too small)
- **All-closed WR (TIME_EXIT counted ≠ win):** 3/35 = 8.6%
- **Incident snapshot (7d window 2026-05-20):** n=20, WR=5.0%, PF=0.113, sum-PnL -65.79% (per HOURLY_AUDIT_2026-05-20_07Z.md / weekly_filter_2026-05-17.md "51.6% concentration in this strategy"). The "19% / n=16" figure originates from this same 7d-class panel.

**By symbol:** CT=F (2W/1L/4 wash), KC=F (1W/0L/2 wash), ZW=F (0W/1L/7 wash), ZS=F (0W/0L/7 wash), CL=F (0W/0L/6 wash), NG=F (0W/0L/2 wash), ZC=F (0W/0L/2 wash), GC=F (2 OPEN).

**Key anomaly:** 30/37 = **81% of picks expire at TIME_EXIT with pnl ≈ 0.** Neither TP nor SL fires inside the holding window. This is a strong signal that the **exit-rule axis is mistuned**, not necessarily that the COT signal lacks edge. Per `reference-sl-optimization-needs-pricepath.md` MEMORY entry, never trust winsorized estimates for TP/SL tuning — but the time-out pattern here is a different failure (window-too-short, not stop-too-tight).

---

## 2. Existing safeguards already in code
- `audit_trail/quality_gates.py:2105-2114` — included in `COT_DEDUP_SYSTEMS` with a 72h dedup window (one CFTC report cycle).
- Line 9979-9981 — included in the negative-score branch when `source_system == "multi_asset_copytrader"` (-10 score penalty).
- Line 5680 — minimum-pick floor 20 for confidence tier.
- M-046 (line 9823): optional COMMODITY single-source concentration cap (default OFF, gated by `COMMODITY_SOURCE_CAP=1`).
- M-096 (line 9863): CT=F symbol cap at 40% of OPEN COMMODITY (ON).
- **NOT** in `PERMANENTLY_KILLED_STRATEGIES` (line 1370). **NOT** in `BLOCKED_STRATEGIES` (line 2122).

---

## 3. Qwen-max three-axis mutation analysis

Full Qwen response (prompt + completion) saved verbatim to:
`reports/peer_claude-cftc-cot-commercial-mutation-analysis_qwen_consult_2026-05-31.md` (qwen-max, 1030 prompt + 722 completion tokens, id chatcmpl-44aec6d3).

### Axis 1 — Entry Rule
1. **Add momentum confirmation** (technical momentum filter — e.g. price/MA cross or RSI direction confirming COT signal direction). Reduces premature fundamental-only entries.
2. **Require higher COT z-score extremity** (multi-year extreme percentile only). Stricter signal admission → fewer but higher-conviction entries.

### Axis 2 — Exit Rule (HIGHEST PRIORITY given 81% TIME_EXIT washes)
1. **Extend holding period to next COT release.** Currently positions time out before the next weekly COT report can move the position. Aligning the exit cadence with the data source's release cadence is the most likely single fix.
2. **Widen TP/SL** so price movement isn't truncated by tight bands inside the COT-cycle window.

### Axis 3 — Symbol Universe
1. **Restrict to CT=F + KC=F** (the only symbols that ever hit TP). All other grains/oils/gas are pure wash universe.
2. **Drop CL=F** explicitly (6 washes, 0 wins, 0 losses) — pure noise contribution.

### Qwen Verdict
> Test the three mutations **in shadow mode for N picks (≈50)** before re-admitting to live trading. **If WR does not improve to ≥ 30% after shadow testing, formally retire and add to PERMANENTLY_KILLED_STRATEGIES.**
>
> The decisive-only 60% WR (n=5) is statistically meaningless either way. Mass TIME_EXIT pattern suggests exit-rule fix could rescue the strategy.

---

## 4. My recommendation (Claude Opus 4.7)

**Concur with Qwen: REHAB-VIA-SHADOW, do NOT add to PERMANENTLY_KILLED_STRATEGIES yet.**

Reasoning:
- Decisive sample (n=5) is too small to assert "edge is gone". The 81% TIME_EXIT pattern is diagnostic, not damning — it points to a fixable exit-rule axis.
- COT data is institutional fundamental positioning — losing this source family permanently is a costly information loss if the issue is plumbing (holding window) rather than signal quality.
- The strategy already has 4 layered safeguards (dedup, score penalty, source-cap, symbol-cap). The blast radius is already contained.

### Proposed shadow-mode rehab plan (NOT shipped in this PR — defers to human review / next session)
1. **Symbol restriction first** (lowest-risk mutation, no behavioral change for non-CT/KC entries): in `audit_trail/quality_gates.py`, add an early-reject when `strategy == "cftc_cot_commercial_signal"` AND `symbol NOT IN {"CT=F","KC=F"}`. Gated by `COT_COMM_SYMBOL_RESTRICT=1`.
2. **Exit-window extension** (in `alpha_engine/outcome_resolver.py`): special-case strategies in `COT_DEDUP_SYSTEMS` to use a 14-day holding window (≈2 COT cycles) instead of the default 7-day. Shadow-only via `COT_EXTENDED_WINDOW=shadow` (records would-be-different outcomes without changing live behavior).
3. After 50 shadow picks have closed under (1)+(2), recompute WR. If ≥ 30% → promote out of shadow; if < 30% → add to `PERMANENTLY_KILLED_STRATEGIES`.

### What I am NOT doing now
- **Not adding to `PERMANENTLY_KILLED_STRATEGIES`.** Premature on n=5 decisive + diagnostic exit-rule pattern. Per SESSION RULES "risky/complex items — docs-only PR".
- **Not shipping mutation code.** Touches `quality_gates.py` admission logic + `outcome_resolver.py` — needs human review and a shadow harness, not a same-session drive-by.

---

## 5. Disposition for the incident ledger

| Field | Value |
|---|---|
| Incident | INCIDENT_COMMODITIES #1 — `cftc_cot_commercial_signal` |
| Original claim | 19% WR / n=16 (BLOCKED) |
| Verified lifetime | 3W/2L/30 TIME_EXIT/2 OPEN — decisive WR 60% (n=5), all-closed WR 8.6% (n=35) |
| Diagnosis | Exit-rule axis (81% TIME_EXIT washes), not entry-signal collapse |
| Existing controls | 72h dedup, -10 score penalty, optional source-cap, CT=F symbol cap |
| Disposition | **DEFERRED — shadow-mode mutation plan documented; do not kill yet** |
| Next-session action | Implement (1) symbol restriction + (2) extended exit-window shadow harness; review at 50 shadow picks |

---

## 6. References
- Live verification query: this file §1
- Qwen-max consult: `reports/peer_claude-cftc-cot-commercial-mutation-analysis_qwen_consult_2026-05-31.md`
- Mutation protocol: `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- Kill protocol: `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
- SL-tuning caveat: MEMORY `reference-sl-optimization-needs-pricepath.md`
- Historical context: `reports/HOURLY_AUDIT_2026-05-20_07Z.md` (FINDING-22), `reports/weekly_filter_2026-05-17.md` (51.6% concentration), `reports/cotton_cot_real_money_sizing_2026-05-12.md`
