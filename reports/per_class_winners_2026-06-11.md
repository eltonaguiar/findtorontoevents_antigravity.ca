# Per-Class Proven-Winner Hunt — 2026-06-11

**Cohort:** deduped intrabar (`at_signal_outcomes`, TP_HIT/SL_HIT, symbol+direction+day MIN id)  
**Tools:** `tools/per_class_winner_hunt.py`, `tools/strategy_pass_hunter.py`, `tools/stamp_entry_conditions.py`  
**Tier definitions:**

| Tier | Criteria |
|------|----------|
| **PROVEN** | n≥100 + WR≥50% + PF≥1.5 + R1/R2/R3 pass |
| **PROBATION** | n≥30 + full discipline pass (hold sizing until n→100) |
| **WATCH** | Best honest cell; forward stamp accruing n |
| **NEG_FILTER** | Avoid-rule removing ≥50% class losses |
| **PROXY** | OHLC backtest T2 candidate; **not** intrabar-confirmed |

---

## Executive summary

| Class | Verdict | Best unit | n | WR | PF | Full pass? |
|-------|---------|-----------|---|-----|-----|------------|
| **CRYPTO** | **PROBATION** | `luxalgo_confluence` SHORT | 38 | 71.1% | 2.21 | **YES** |
| FOREX | WATCH | F1 trend=ALIGNED filter | 14 | 64.3% | 4.74 | No (n<30) |
| EQUITY | WATCH | F2 mom24=WITH | 24 | 54.2% | 2.17 | No (n<30, R1/R2 fail) |
| COMMODITY | NONE | futures_momentum SHORT | 10 | 60.0% | 2.27 | No (n<30) |
| ETF | NONE | — | 11 | 0.0% | 0.00 | No |
| BOND | NONE | — | 6 | 33.3% | 2.24 | No (n<6) |
| FUTURES | NONE | — | 7 | 28.6% | 0.22 | No |
| MEMECOIN | NONE | ensemble LONG | 50 | 30.0% | 0.78 | No |

**PROVEN winners (n≥100): 0 / 8 classes**  
**PROBATION (disciplined, n≥30): 1** — CRYPTO luxalgo SHORT only  
**Closest non-CRYPTO:** FOREX trend-aligned (PF 4.74 but n=14), EQUITY mom-with (PF 2.17, n=24)

---

## CRYPTO — one real edge

### PROBATION: `luxalgo_confluence × SHORT`

- Wilson 95%: [55.2%, 83.0%]
- R1 split: 79%/2.49 | 63%/2.02 ✓
- R2: NEARUSDT 18.4% ✓
- R3: p ≈ 3.4×10⁻⁷ ✓
- MC vs coin flip: 99.8th percentile
- **Emission:** `luxalgo_confluence_v2_short` via `priority_picks_emitter` (forward observation)

### WATCH (do not size — forward stamp only)

| Slice | n | WR | PF | Blocker |
|-------|---|-----|-----|---------|
| F5=US & Monday | 40 | 55.0% | 1.92 | R1 fail (H1 45%/1.38); ex-luxalgo n=24 PF 1.47 |
| rsi5070+US (all) | 108 | 47.2% | 1.53 | WR<50% (LONG leg drags) |
| rsi5070+US SHORT | 16 | 81.2% | 6.25 | n<30 |
| lux SHORT + rsi5070+US | 13 | 92.3% | 11.06 | n<30 |

**Lesson:** Session/day filters lift WR but **luxalgo SHORT is the only cell that survives full discipline at n≥30**. The Jun-10 experiment survivor (rsi5070+US n=84 WR 52.4%) **degraded** as new cohort rows entered.

---

## FOREX — filter story, not a winner yet

| Unit | n | WR | PF | Notes |
|------|---|-----|-----|-------|
| Class baseline | 49 | 40.8% | 1.24 | Below T2 WR |
| **F1=ALIGNED** | 14 | 64.3% | 4.74 | Best positive filter; stamp `forex_trend_aligned` |
| F1=CONTRARIAN (NEG) | 24 | 29.2% | 0.53 | **Avoid** — captures ~76% of losses |
| forex_rsi2_mr strategy | 11 | 63.6% | 2.67 | n too small |
| F4=LOW | 24 | 41.7% | 1.79 | PF ok, WR not |

**Path:** Emit `forex_trend_aligned_v2` (block CONTRARIAN) + accrue n to 30→100. No PROVEN/PROBATION unit today.

---

## EQUITY — fragile lift

| Unit | n | WR | PF | Notes |
|------|---|-----|-----|-------|
| Class baseline | 59 | 47.5% | 1.14 | Near break-even |
| **F2=mom24 WITH** | 24 | 54.2% | 2.17 | Best slice; R2 fail (concentration) |
| F4=LOW (Jun-10 exp) | 22 | 36.4% | 1.33 | WR collapsed vs experiment (62.9%) |
| F4=HIGH (NEG) | 30 | 53.3% | 0.81 | **Avoid high-vol entries** — WR looks ok but PF<1 |

**Path:** Stamp `equity_mom_with`; need n≥30 + R1/R2 pass before PROBATION.

---

## COMMODITY / ETF / BOND / FUTURES / MEMECOIN — no honest winner

- **COMMODITY:** `futures_momentum` SHORT n=10 PF 2.27 — prior n=47 was duplicate inflation; **NONE**
- **ETF:** n=11, 0% WR — do not trade
- **BOND:** n=6 PF 2.24 — noise
- **FUTURES:** n=7 PF 0.22 — fail
- **MEMECOIN:** n=65 WR 28% — do-not-trade class

### PROXY only (intrabar not confirmed)

From `reports/june2026_strategy_research_2026-06-12.json` OHLC harness:

| Class | Strategy | n | WR | PF | MC pctile | Next step |
|-------|----------|---|-----|-----|-----------|-----------|
| COMMODITY | gold_overnight_gap_fade | 108 | 63.9% | 1.92 | 99.8% | Wire to intrabar replay harness |
| EQUITY | first_hour_range_break | 25 | 76.0% | 1.87 | 99.8% | n<30; forward emit |
| PENNY | volume_spike_fade | 177 | 58.2% | 1.54 | 98.7% | Closest proxy; needs honest resolver rows |

---

## Forward stamp lanes added (measurement only)

New conditions in `stamp_entry_conditions.py`:

- `crypto_us_monday` — US session + Monday entries
- `crypto_rsi5070_us_short` — rsi band + US + SHORT only
- `equity_mom_with` — 24h momentum aligned with direction

Re-run weekly:

```bash
python3 tools/stamp_entry_conditions.py --limit 5000
python3 tools/per_class_winner_hunt.py --json reports/per_class_winners_$(date +%F).json
python3 tools/strategy_pass_hunter.py
```

---

## Honest answer to “proven winners per asset class”

| Class | Proven? | Action |
|-------|---------|--------|
| CRYPTO | **PROBATION** (not PROVEN until n≥100) | Keep luxalgo SHORT emitting; ship P0-A reresolve |
| FOREX | No | Trend-aligned filter forward stamp |
| EQUITY | No | Mom-with stamp; avoid high-vol |
| COMMODITY | No | Replay gold gap-fade on intrabar; kill futures_momentum hype |
| ETF/BOND/FUTURES/MEMECOIN | No | Do not size |

**Net:** 0 proven, 1 probation, 3 watch lanes with forward measurement wired.
