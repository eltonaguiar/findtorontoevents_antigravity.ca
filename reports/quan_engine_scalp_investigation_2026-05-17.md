# quan_engine_scalp — Strategy Investigation Before Kill

**Date:** 2026-05-17
**Protocol:** `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
**Data source:** `alpha_engine/data/closed_picks.json` (8,421 closed rows, file mtime 2026-05-15)
**Verdict:** **ALREADY-BLOCKED** — confirmed correct. No salvageable subset on any axis. Keep blocked.

---

## 1. Headline numbers (verified)

| Metric | Value |
|---|---|
| Closed rows (`strategy == quan_engine_scalp`) | **5,293** |
| Share of entire `closed_picks.json` | **62.9%** (5,293 / 8,421) |
| Win rate | **29.9%** |
| Profit factor | **0.379** |
| Cumulative PnL | **−960.3%** |
| `source_system` for all rows | `quan_engine` (uniform) |

This matches the verified context (WR 29.94% / n≈5,294 / PF 0.38) and `strategy_performance.json`. It is the **single largest drag in the system** — the largest closed-volume strategy and the most negative cumulative PnL.

---

## 2. AXIS 1 — SYMBOL

Top symbols by volume (full table for n≥30):

| Symbol | n | share | WR | PF | cumPnL |
|---|---|---|---|---|---|
| MATICUSDT | 1,057 | 20.0% | **0.0%** | 0.000 | −158.5% |
| BTCUSDT | 628 | 11.9% | 35.2% | 0.523 | −97.7% |
| KASUSDT | 565 | 10.7% | 36.5% | 0.498 | −104.5% |
| HYPEUSDT | 504 | 9.5% | 43.1% | 0.351 | −112.0% |
| TAOUSDT | 464 | 8.8% | 38.8% | 0.227 | −89.9% |
| DOTUSDT | 290 | 5.5% | 36.6% | 0.332 | −69.3% |
| ICPUSDT | 246 | 4.6% | 30.9% | 0.306 | −64.7% |
| TRXUSDT | 244 | 4.6% | 49.6% | 0.917 | −4.2% |
| ETCUSDT | 202 | 3.8% | 43.1% | 0.797 | −12.7% |
| RENDERUSDT | 198 | 3.7% | 32.8% | 0.133 | −49.4% |
| XLMUSDT | 195 | 3.7% | 32.3% | 0.308 | −57.6% |
| ETHUSDT | 121 | 2.3% | 34.7% | 0.337 | −27.7% |
| AVAXUSDT | 110 | 2.1% | 30.0% | 0.381 | −25.7% |
| DOGEUSDT | 106 | 2.0% | 43.4% | 0.619 | −11.9% |
| SOLUSDT | 96 | 1.8% | 26.0% | 0.387 | −20.3% |
| ONDOUSDT | 78 | 1.5% | 21.8% | 0.080 | −30.5% |
| BNBUSDT | 61 | 1.2% | 50.8% | 0.964 | −0.5% |
| ADAUSDT | 54 | 1.0% | 29.6% | 0.249 | −18.7% |
| XRPUSDT | 41 | 0.8% | 48.8% | 0.927 | −0.7% |
| LTCUSDT | 33 | 0.6% | 39.4% | 0.595 | −3.8% |

**Step-5 mutation-quality guard** (winning subset must be WR>50% **AND** n≥100 **AND** ≥10% of total = ≥530 rows):

- **No symbol clears the guard.** The only symbol with WR>50% is BNBUSDT (50.8%) but n=61 (below 100) and PF=0.964 (still <1.0 — not profitable, just least-bad).
- Every symbol with n≥100 has **PF < 1.0**. The "least-bad" large-n symbols — TRXUSDT (WR 49.6%, PF 0.917) and ETCUSDT (WR 43.1%, PF 0.797) — still lose money and still fail WR>50%.
- **No symbol-allowlist mutation is viable.** Symbol axis: **DEAD.**

---

## 3. AXIS 2 — DIRECTION

| Direction | n | share | WR | PF | cumPnL |
|---|---|---|---|---|---|
| BUY (LONG) | 4,709 | 89.0% | 28.2% | 0.361 | −863.2% |
| SELL (SHORT) | 584 | 11.0% | **44.3%** | 0.506 | −97.0% |

- The strategy is 89% LONG-only. SHORTs are *relatively* less bad (WR 44.3% vs 28.2%) but **PF 0.506 — still a money-loser**, and WR fails the >50% bar.
- A SHORT-only mutation would clear the n≥100 and ≥10%-share bars (n=584, 11.0% share) but **fails the WR>50% / PF>1.0 requirement**. There is no profitable direction.
- **Direction axis: DEAD.** SHORT is not salvageable — it is just a smaller loss.

---

## 4. AXIS 3 — TIMEFRAME

All 5,293 rows carry no `source_strategy_type` / `timeframe` field — the strategy is single-timeframe (SCALP, by name). No timeframe split exists in the data. **Timeframe axis: N/A — no subset to mutate.**

---

## 5. AXIS 4 (added) — SYMBOL × DIRECTION

Best symbol×direction combos with n≥100, sorted by WR:

| Symbol | Dir | n | share | WR | PF | cumPnL |
|---|---|---|---|---|---|---|
| TRXUSDT | BUY | 235 | 4.4% | 48.5% | 0.893 | −5.3% |
| ETCUSDT | BUY | 184 | 3.5% | 42.9% | 0.785 | −12.0% |
| HYPEUSDT | BUY | 413 | 7.8% | 41.6% | 0.342 | −94.8% |
| TAOUSDT | BUY | 371 | 7.0% | 38.3% | 0.251 | −65.7% |
| KASUSDT | BUY | 456 | 8.6% | 37.7% | 0.536 | −73.2% |
| BTCUSDT | BUY | 557 | 10.5% | 34.8% | 0.517 | −88.2% |
| MATICUSDT | BUY | 1,057 | 20.0% | 0.0% | 0.000 | −158.5% |

**No symbol×direction combo clears the Step-5 guard** (best is TRXUSDT BUY at WR 48.5% / PF 0.893 — fails both WR>50% and PF>1.0, and at 4.4% share fails the ≥10% bar). Cross-axis combination does **not** rescue the strategy.

---

## 6. MATIC 100%-WR / fixed-TP artifact check — CONFIRMED

Repo memory (`project_quan_engine_matic_positive_artifact`) flagged a synthetic MATICUSDT artifact. The closed data confirms a **synthetic-clone artifact** (here it is a 0%-WR loss artifact, not a win artifact):

All **1,057 MATICUSDT** `quan_engine_scalp` rows are byte-identical clones:

| Field | Value (all 1,057 rows) |
|---|---|
| `pnl_pct` | **−0.15** (1 distinct value, stdev = 0.0) |
| `take_profit` | **0.38505714** (1 distinct value) |
| `entry_price` | **0.3794** (1 distinct value) |
| `direction` | BUY (100%) |
| `exit_reason` | TIME_EXIT (100%) |

This is a **non-real data artifact**: 1,057 identical fixed-TP MATIC LONG rows, all closed by TIME_EXIT at the exact same loss. It inflates the strategy's row count (20% of all `quan_engine_scalp` volume) and contributes −158.5% of the −960.3% cumulative PnL. Even excluding the MATIC artifact, the remaining 4,236 rows still produce WR ≈ 37% and PF < 1.0 system-wide — **the strategy is a genuine loser independent of the artifact**, the artifact merely amplifies the visible damage.

`quality_gates.py:2061` already hard-blocks `("quan_engine_scalp", "MATICUSDT")`. The data-pipeline cause of these clones should be referred separately to the resolver/ingestion owner — it is out of scope for the kill decision.

---

## 7. Current block status — ALREADY FULLY BLOCKED

`quan_engine_scalp` is blocked in **multiple** layers of `audit_trail/quality_gates.py`:

| Line | Structure | Entry |
|---|---|---|
| 1301 | `BLOCKED_STRATEGIES` | `"quan_engine_scalp"` — "25% WR, 1793 trades, −352.88% PnL — worst strategy by total loss" |
| 1302 | `BLOCKED_STRATEGIES` | `"quan_engine"` (base variant) — proactively blocked |
| 1303 | `BLOCKED_STRATEGIES` | `"quan_engine_position"` — sister, 0% WR |
| 2061–2064 | `BLOCKED_STRATEGY_SYMBOL_PAIRS` | scalp×MATICUSDT / ADAUSDT / ICPUSDT / SOLUSDT |
| 2169 | `BLOCKED_ASSET_STRATEGY_PAIRS` | `("CRYPTO", "quan_engine_scalp")` — CRYPTO-wide block |
| 2462 | `BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES` | `("CRYPTO", "quan_engine", "MATICUSDT")` (base variant) |
| 2033 | `inverse_quan_engine_scalp` | inverse pipeline registered (0 closed rows — never produced) |
| 2065, 5118, 5262, 5304–5307 | score penalties | `-28`, `-15`, `-12`, plus per-symbol penalties |
| 3608 | volume cap | `quan_engine` CRYPTO picks capped, `-5` penalty |

The strategy is **hard-blocked at the source-strategy level, the asset-class level, and the symbol-pair level**, with defense-in-depth score penalties. It cannot reach production picks. No further block is *required* — the existing blocks are correct and comprehensive.

---

## 8. VERDICT — ALREADY-BLOCKED (confirm; no action needed)

- **Symbol axis:** DEAD — no symbol clears WR>50% / n≥100 / ≥10%-share; every n≥100 symbol has PF<1.0.
- **Direction axis:** DEAD — SHORT (WR 44.3%, PF 0.506) is less-bad but still a loser; fails WR>50% / PF>1.0.
- **Timeframe axis:** N/A — single-timeframe, no subset.
- **Symbol×Direction:** DEAD — best combo TRXUSDT BUY (WR 48.5%, PF 0.893) fails all three Step-5 bars.
- **MATIC artifact:** CONFIRMED — 1,057 identical fixed-TP clones; loss artifact, not a win artifact; already symbol-blocked.
- **Salvageable subset:** **NONE.** Mutate-before-kill protocol has been satisfied — all four axes evaluated, no subset clears the Step-5 mutation-quality guard.
- **Block status:** ALREADY-BLOCKED in 9+ structures across `quality_gates.py`. Correct and comprehensive.

**Recommendation:** Keep `quan_engine_scalp` blocked. No `quality_gates.py` edit is needed — the strategy is already in `BLOCKED_STRATEGIES` (line 1301), `BLOCKED_ASSET_STRATEGY_PAIRS` (line 2169), and `BLOCKED_STRATEGY_SYMBOL_PAIRS` (lines 2061-2064). The mutate-before-kill investigation is hereby documented as complete and the block is upheld.

### Optional hardening (recommend only — do NOT apply automatically)

The existing block is sufficient. If a reviewer wants belt-and-suspenders defense-in-depth (in case `BLOCKED_STRATEGIES` is ever conditionally rolled back), the source-system block can be made explicit, since all 5,293 rows carry `source_system == "quan_engine"`:

```python
# audit_trail/quality_gates.py — BLOCKED_SOURCE_SYSTEMS (~line 1707)
# quan_engine_scalp investigation 2026-05-17: n=5,293 WR 29.9% PF 0.38
# cumPnL -960.3% (62.9% of all closed rows). 4-axis autopsy found NO
# salvageable subset (best: TRXUSDT BUY WR 48.5%/PF 0.893 — fails Step-5).
# source_system field is uniformly "quan_engine" for the scalp variant.
BLOCKED_SOURCE_SYSTEMS = {
    ...
    "quan_engine",   # ADD — source-system-level defense-in-depth
    ...
}
```

This is **not required** — `quan_engine` the base strategy is already in `BLOCKED_STRATEGIES` (line 1302) and `BLOCKED_ASSET_STRATEGY_PAIRS`/`...TRIPLES`. Adding it to `BLOCKED_SOURCE_SYSTEMS` would hide all historical attribution for the source; weigh that against the marginal safety gain. Decision left to a human reviewer.

---

*Reproducer:* filter `alpha_engine/data/closed_picks.json` to `strategy == "quan_engine_scalp"`; group by `symbol`, `direction`; WR = pnl_pct>0 share, PF = gross-profit / gross-loss. `python tools/mutation_analysis.py --json` for the system-wide direction/symbol-variance cross-check.
