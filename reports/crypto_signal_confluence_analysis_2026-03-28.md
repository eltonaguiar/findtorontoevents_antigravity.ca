# Crypto signal confluence analysis

**Data source:** `audit_trail/data/dashboard_payload.json`  
**Latest analysis payload (UTC):** `2026-03-28T22:35:12.174731+00:00`

> **Live numbers:** `python tools/analyze_crypto_signal_window.py --compare` prints a multi-window table from whatever payload you have locally. Older narrative tables in this file used an earlier payload cut; the **compare table** below matches the latest run documented here.

---

## Latest run: multi-window summary

Cohort: **CRYPTO** `recent_closed` rows with `closed_at` in `[generated_at - hours, generated_at]`.

| Hours | Trades | Overall WR | WR in `agreement_count` 5+ | 3–4 | 0 | Score gap* |
|------:|-------:|-----------:|---------------------------:|----:|--:|-----------:|
| 3 | 57 | 54.4% | 69.2% | 30.0% | 85.7% | **-2.19** |
| 24 | 798 | 59.3% | 67.1% | 48.9% | 61.5% | +1.47 |
| 72 | 1496 | 47.0% | 52.0% | 43.5% | 42.0% | +5.24 |
| 168 | 1822 | 48.3% | 52.7% | 44.9% | 42.2% | +4.57 |

\* **Score gap** = mean(`score` | win) − mean(`score` | loss). A **negative** gap means winners had *lower* average score in that window (unstable short-horizon signal).

### Interpretation

1. **Agreement:** Over **24–168h**, **`5+` is the strongest bucket** (67% → 53% WR as the sample ages). **`3–4` is consistently the weakest** (49% → 45%). The **very high WR for `0` in the 3h window (85.7%) does not hold** at 24h (61.5%) or 72h (42%) — treat **short-window polar agreement patterns as noise** unless they repeat across runs.

2. **Overall win rate:** **59% at 24h** vs **~47–48% at 72–168h** suggests the **most recent day was a better regime** for this pipeline than the prior multi-day aggregate (or a composition effect in what closed).

3. **Score:** **Never trust mean score vs outcome on a 3h slice alone.** In the latest 3h run, score was **inverted** (winners lower). At **72h+**, gap is **+4.5 to +5.2** points in favor of winners — aligned with using score as a **slow** filter.

4. **RSI at entry:** Still **~98% missing** in the 3h window. The tool now buckets **`technical_rsi_4h` as a fallback** when entry RSI is absent; **effective RSI missing** drops to **~5%** in that window, so **4h technical RSI** is usable for coarse regime bucketing until entry RSI is backfilled.

5. **Trust tier (3h snapshot):** In the latest 3h output, **`WATCH` had 75% WR** (18W/6L) vs **`PROVEN` 44.4%** (12W/15L) — **counter-intuitive** and likely **selection / cohort mix** (not a recommendation to prefer WATCH). Use trust tier only with **longer windows and larger *n*** (see golden criteria report).

6. **Volume ratio (72h, when populated):** Buckets with data show **`volume_ratio < 1` ~11.6% WR** vs missing baseline ~50% — when the field exists, **low relative volume** lines up with **worse** outcomes. **Backfilling `volume_ratio`** remains high priority.

7. **Strategy/symbol sanity:** **`ml_crypto_predictor::FETUSDT`** shows **many wins, zero losses** over 24–72h in `recent_closed`. That can be **legitimate streak** or **duplicate / resolution artifact** — worth a **data audit** (one symbol/strategy flooding closes).

---

## Historical snapshot (earlier payload, 3h only)

The following table used payload **`2026-03-28T22:23:38Z`** (52 trades). It is **superseded** by the multi-window view above for methodology, but kept as an example of **how fast** small-window stats can shift.

| Metric | Value |
|--------|------:|
| Trades in window | 52 |
| Wins / Losses | 28 / 24 |
| Win rate | 53.8% |

That cut showed a **polar** agreement pattern (0 and 5+ high, 3–4 low). The **24h** row in the main table shows **3–4 still weakest** but **0 no longer dominates** — reinforcing **multi-window review**.

---

## Cross-check: golden criteria (last 3 days)

From `reports/crypto_golden_criteria_report.md`:

- **Trust tier `PROVEN`:** 58.8% WR (345 trades).
- **Track WR bucket 60+:** 70.7% WR (273 trades).
- **Score bucket 55–69:** 58.8% WR (194 trades).

Use these as **orthogonal** filters when `trust_tier` and track fields are populated at scale.

---

## Recommendations (updated)

1. **Operational:** Run **`--compare` daily**; do not act on **3h score gap** or **3h trust tier** in isolation.
2. **Data:** Persist **`rsi_at_entry`** and **`volume_ratio`** on every resolution; until then, use **`technical_rsi_4h`** only as a **secondary** signal (already in the tool).
3. **Risk:** Keep **extra scrutiny on `agreement_count` 3–4** — it is the **weakest bucket** from 24h through 168h in the latest payload.
4. **Research:** Audit **`ml_crypto_predictor` + FETUSDT** (and similar **0-loss** pairs) for duplicate closes or resolver bias.
5. **Monitoring:** Track **24h vs 72h overall WR**; a sharp drop may flag regime change.

---

## Tool reference (`tools/analyze_crypto_signal_window.py`)

| Feature | Description |
|---------|-------------|
| `--hours N` | Single window report (default 3). |
| `--compare` | Prints **3 / 24 / 72 / 168h** summary table (overall WR, agreement sub-WRs, score gap). |
| `--json` | Full report JSON (includes `trust_tier_buckets`, `rsi_buckets_entry_only`, `rsi_buckets_effective`, `data_quality`, `top_strategies_min5`, `score_note`). |
| **RSI effective** | `rsi_at_entry` or fallback **`technical_rsi_4h`**. |
| **Data quality** | Percent of decided trades missing RSI@entry, missing `volume_ratio`, missing effective RSI. |
| **`closed_at`** | Parses ISO `Z`, offsets, and trailing **`EST` / `EDT`**. |

```bash
python tools/analyze_crypto_signal_window.py --compare
python tools/analyze_crypto_signal_window.py --hours 24 --json
```

---

## Raw JSON summary (illustrative)

```json
{
  "summary": {
    "payload_generated_at": "2026-03-28T22:35:12.174731+00:00",
    "windows_compared_hours": [3, 24, 72, 168],
    "finding": "Use multi-window compare; 3h score gap can invert; agreement 5+ strongest at 24-168h; 3-4 weakest"
  },
  "confluencemetricinsights": {
    "signal_agreement": "5+ best at 24h+; 3-4 weakest; 0-agreement spike is 3h-only",
    "rsi": "Entry RSI sparse; technical_rsi_4h fallback fills most gaps",
    "volume": "When volume_ratio present, low <1 aligns with weak WR over 72h",
    "score": "Positive gap at 72h/168h; negative possible at 3h"
  }
}
```
