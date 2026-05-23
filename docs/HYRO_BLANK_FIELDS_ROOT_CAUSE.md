# Hyrotrader Audit Page — Blank Fields Root Cause Analysis

**Date:** 2026-04-14  
**URL:** https://findtorontoevents.ca/audit/hyrotrader/

---

## Summary

Three sections on the Hyrotrader audit page render with blank/empty table rows:

1. **QuanEngine Regime Analysis** — 4 rows show only Symbol/Regime/Hurst; all other columns are "—"
2. **Live Playbook Signals (1h)** — QuanEngine column shows regime but no ensemble/mode/risk data
3. **Pick List** — all entry_price / stop_loss / take_profit show "—" (by design — not a bug)

---

## Root Cause #1: `ensemble: null` in hyro_quan_bridge.json (MAIN ISSUE)

**File:** `audit_dashboard/data/hyro_quan_bridge.json`

All 4 symbols (BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT) have:

```json
"ensemble": null,
"trade_setup": null,
"risk_gate": null
```

**Why:** The bridge generator (`tools/hyro_quan_bridge.py`, line ~170) initializes `ensemble`, `trade_setup`, and `risk_gate` as `null` and only populates them when `ensemble.vote(votes)` returns a non-null signal. The signal is null when the ensemble layer can't reach consensus — i.e. fewer than 45% of strategies agree on a direction (`CONSENSUS_THRESHOLD = 0.45` in `quan_engine/config.py`).

**Current state:** Only 3–5 out of 18 strategies cast active (non-ABSTAIN) votes per symbol. That's 17–28% consensus — well below the 45% threshold. The ensemble returns `None`, so `run_symbol()` bails early at line ~176 (`if signal is None: return out`) with all three fields still null.

**Effect on UI:**  
- **QuanEngine Regime Analysis table** (line 1220): renders regime + hurst but shows `No consensus (3/18)` and fills Signal/Consensus/Confidence/Mode/Entry/TP/SL/R:R/Strategies with "—"
- **Live Playbook Signals → QuanEngine column** (`quanCellHtml`, line 497): shows regime + hurst but ensemble direction line shows "—", no mode badge, no RiskGate badge

### Fix options

| Option | Change | Tradeoff |
|--------|--------|----------|
| **A. Lower consensus threshold** | `config.py` → `CONSENSUS_THRESHOLD = 0.20` | More signals, but noisier — may approve weak setups |
| **B. Show partial data** | Template shows active votes + direction breakdown even when no consensus | Informational only — doesn't create trade_setup/risk_gate |
| **C. Add more strategies to pools** | Increase pool sizes so 45% is reachable with fewer agreements | More dev work; strategies need validation |
| **D. Show "no consensus" explicitly** | Replace blank cells with vote breakdown (e.g. "3 BUY / 0 SELL / 15 ABSTAIN") | Pure UI fix — most honest about what's happening |

**Recommended:** Option D (UI clarity) + Option A (lower to ~0.30) so the system actually fires when 6+ of 18 strategies agree.

---

## Root Cause #2: Pick List prices intentionally blank

**File:** `audit_dashboard/data/hyrotrader_picks.json`

All 7 picks have:
```json
"entry_price": null,
"stop_loss": null,
"take_profit": null
```

**This is by design.** The TP/SL warning card on the page explicitly says:

> Numeric prices stay empty until you paste real levels from your chart — we do not invent prices.

The template (`formatLevelsCell`, line 292) handles this correctly, showing "No numeric prices in JSON yet" instead of blank cells. **Not a bug.**

---

## Root Cause #3: Live Playbook "No setup" rows

The Live Playbook Signals table fetches real-time 1h klines from Binance and evaluates each strategy against the last closed bar. When a strategy's rules aren't met on the current bar, it shows "No setup" — this is normal behavior, not a blank field bug. The "Hide No setup" checkbox (checked by default) collapses these rows.

However, the **QuanEngine column within this table** is also blank/minimal because it reads the same `hyro_quan_bridge.json` with null ensemble data (Root Cause #1).

---

## Data Flow Diagram

```
tools/hyro_quan_bridge.py
  └─ quan_engine/ensemble_layer.py  →  vote() returns None (< 45% consensus)
     └─ run_symbol() bails early   →  ensemble/trade_setup/risk_gate = null
        └─ Writes to audit_dashboard/data/hyro_quan_bridge.json
           └─ Browser fetches JSON
              ├─ QuanEngine Regime Analysis table  → "—" in 9 of 12 columns
              └─ Live Playbook → QuanEngine column → "—" for ensemble/mode/risk
```

---

## Files Involved

| File | Role |
|------|------|
| `tools/hyro_quan_bridge.py` | Generator — runs QuanEngine per symbol, writes JSON |
| `quan_engine/config.py` | `CONSENSUS_THRESHOLD = 0.45`, `MIN_AVG_CONFIDENCE = 0.45` |
| `quan_engine/ensemble_layer.py` | `vote()` — returns None when threshold not met |
| `quan_engine/strategy_pool.py` | Pools: TRENDING, MEAN_REVERSION, PROP (18 total strategies) |
| `audit_dashboard/data/hyro_quan_bridge.json` | Output JSON with null fields |
| `audit_dashboard/data/hyrotrader_picks.json` | Pick list (prices intentionally null) |
| `audit_dashboard/hyrotrader/index.html` | Renderer — lines 1183–1260 (QuanEngine table), 402–475 (bridge panel), 483–515 (QuanEngine cell) |
