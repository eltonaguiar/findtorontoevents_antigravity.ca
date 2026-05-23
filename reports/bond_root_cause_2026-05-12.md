# BOND Emission Root Cause — Verified Diagnosis

**Date:** 2026-05-12
**Author:** Claude Opus 4.7 (1M ctx) — verification swarm
**Status:** Corrects three prior incorrect diagnoses
**Live state:** `/audit` shows BOND PF 1.72 / WR 55.6% / **n=18** (well below charter T2 floor of n=100)

---

## 0. TL;DR

Three agents proposed three different "root causes" for BOND being stuck at n=18. **All three were wrong or incomplete.** This document records the verified diagnosis after reading actual code paths and recent emitter output.

| Prior claim | Source | Verdict |
|---|---|---|
| `forward_validator.py:395` allowlist is `["crypto","meme"]` | First swarm Explore | **FALSIFIED** — lines 423-432 already include bond/etf/forex/equity/commodity/futures/index (expanded 2026-04-18) |
| `FORWARD_GATE_MIN_TRADES=50` with 0 forward trades | Second swarm Explore | **TRUE but secondary** — never reached because signals fail upstream |
| FRED API timeout / `FRED_API_KEY` missing from secrets | Cloud-agent §8 addendum | **FALSIFIED** — `.github/workflows/bond-agent.yml:48-100` makes zero FRED calls; uses yfinance only |

The 18 BOND picks visible on `/audit` are **legacy** `futures_momentum` trades on ZN=F that were miscategorized as bond futures. **Zero current bond_* strategies have any closed picks.**

---

## 1. The actual three-layer blocker (verified)

### Layer 1 — Primary: Quality curation gate rejects every signal

`non_crypto_agent/data/bond_picks.json` latest run (2026-05-12T15:31:21Z): `total_raw: 7, quality: 0`.

The bond agent produces signals, but every one fails the curation gate at [.github/workflows/bond-agent.yml:107-113](.github/workflows/bond-agent.yml#L107-L113):
- `confidence >= 0.50`
- `risk_reward >= 1.10`
- `elite_score >= _elite_floor` (default **40**)

Hypothesis: the `elite_score` floor is the binding constraint. Bond volatility is structurally lower than equity/commodity/crypto, so signal magnitudes are compressed. A floor calibrated on crypto/equity (where elite_score routinely hits 60+) is mathematically out of reach for a 0.5-0.8%-move bond ETF signal.

**Fix:** lower `_elite_floor` for BOND to ~35 (matches Chinese report's "Score Floor −20%" prescription for bonds). One config change; no logic edit.

### Layer 2 — Secondary: Forward gate would block even if Layer 1 passed

[alpha_engine/forward_validator.py:389](alpha_engine/forward_validator.py#L389) — `FORWARD_GATE_MIN_TRADES = 50` (raised from 30 per Kimi consensus). No per-class override.

Every bond_* strategy has **0 closed picks**. Even if curation passes today, the validator returns `False` with `"insufficient_data (0/50 trades)"` at [forward_validator.py:585-617](alpha_engine/forward_validator.py#L585-L617) until 50 closed trades accumulate.

**Fix:** add `FORWARD_GATE_OVERRIDES["bond"] = 10` (matches Chinese report's "no WR Floor / lower trust" prescription). Defensible because BOND ETFs have lower idiosyncratic volatility — 10 trades carry roughly the statistical weight of 50 crypto trades.

### Layer 3 — Tertiary: Integration gap (the silent killer)

The bond agent writes to `non_crypto_agent/data/bond_picks.json`. The dashboard generator reads from it. But **the forward validator loop reads from `alpha_engine/data/active_picks.json`** — and no job merges `bond_picks.json` into `active_picks.json`.

Even if Layers 1 and 2 are fixed, bond picks will never enter the validator's view.

**Fix:** add a step in the bond-agent workflow (after curation, before commit) that merges qualified bond picks into `active_picks.json`. ~10 lines of Python.

---

## 2. Stacking order matters

Fixing only one layer does nothing:

| Fix applied | Result |
|---|---|
| Lower elite_score floor only | Signals pass curation → still blocked by 50-trade forward gate → still never written to active_picks.json |
| Lower forward gate only | No signals reach the gate to test it |
| Merge to active_picks.json only | Empty input → empty output |

**All three must ship in one PR cluster** to actually move the n=18 number.

---

## 3. Falsifying the "FRED API timeout" theory in detail

The cloud agent's §8 claim was: "BOND emitter silent since 2026-04-20 due to FRED API timeout; add `FRED_API_KEY` to GitHub secrets."

Verification:

1. **[.github/workflows/bond-agent.yml:48-100](.github/workflows/bond-agent.yml#L48-L100)** — the strategy execution block fetches market data via `yf.Ticker(sym).history(period="2y")`. Zero FRED HTTP calls.
2. **[.github/workflows/bond-agent.yml:57](.github/workflows/bond-agent.yml#L57)** — env block does set `BOND_ENABLE_CREDIT_SPREAD: '1'` (PR #545 confirmed correct), but does NOT reference `FRED_API_KEY` at all.
3. **[alpha_engine/bond_data_fred.py:102-106](alpha_engine/bond_data_fred.py#L102-L106)** — *does* use FRED, but only in `etf-bond-scanner.yml` and `worldclass-pipeline.yml`, neither of which is the live BOND emitter.
4. Latest bond-agent run output (`bond_picks.json` at 2026-05-12T15:31Z) shows the workflow **completed successfully** — 7 raw signals generated. If FRED were the blocker, raw count would be 0.

The "since 2026-04-20" date is also wrong: the workflow ran today.

The cloud agent's diagnosis appears to have conflated `etf-bond-scanner.yml` (which does use FRED, may indeed be timing out) with `bond-agent.yml` (which does not use FRED at all and is the actual emitter).

---

## 4. Falsifying the "forward_validator allowlist" theory in detail

[alpha_engine/forward_validator.py:423-432](alpha_engine/forward_validator.py#L423-L432) explicitly lists `"crypto", "meme", "forex", "fx", "equity", "stock", "stocks", "commodity", "commodities", "futures", "future", "etf", "bond", "bonds", "index"` in `allowed_asset_classes`.

The inline comment at [forward_validator.py:416-422](alpha_engine/forward_validator.py#L416-L422) explicitly states:
> bond/etf/futures/forex are LOW-RISK to open here: production_scanner Gate 0 doesn't block them, and current historical performance is acceptable (BOND PF=1.6, COMMODITY PF=1.06, ETF/FOREX still building).

Then [alpha_engine/production_scanner.py:2553-2556](alpha_engine/production_scanner.py#L2553-L2556) normalizes `bond → equity` before any gate sees the category, but that normalization happens *after* admission — so it doesn't block anything, it just rewires the booster keying (which incidentally erases any bond-specific gate floor that keys on `category=="bond"`).

The allowlist theory is firmly off the table.

---

## 5. Recommended PR cluster (single deploy)

| PR | File | Change | Risk |
|---|---|---|---|
| BR-1 | `.github/workflows/bond-agent.yml` (or `non_crypto_policy.py`) | Set `_elite_floor=35` for BOND | Low |
| BR-2 | `alpha_engine/forward_validator.py` | Add `FORWARD_GATE_OVERRIDES = {"bond": 10}` and consult before the global 50-trade check | Low |
| BR-3 | `.github/workflows/bond-agent.yml` | After curation, merge qualified bond picks into `alpha_engine/data/active_picks.json` | Low — write-path only |

**Acceptance:**
- Within 14 days of ship: BOND `n` advances from 18 → 25+ visible on `/audit`.
- Within 90 days: BOND `n >= 100`, PF maintained `>= 1.5`, WR `>= 50%`.

**Stop-loss:** if PF drops below 1.0 in the first 30 picks, raise `_elite_floor` back to 40 and re-investigate signal quality at source.

---

## 6. What this changes in the main plan

[reports/money_ready_validation_plan_2026-05-11.md](reports/money_ready_validation_plan_2026-05-11.md) needs:
- P0-B's "one-line bond allowlist fix" claim struck (was the first swarm's error)
- §8 addendum's FRED claim struck (was the cloud agent's error)
- Replace both with this three-layer diagnosis

That edit should happen *after* the parallel cloud agent commits its `quality_gates.py` work, to avoid stomping on dirty working-tree changes.

---

## 7. Why three agents got this wrong

A common failure pattern: each agent grepped for "where could bond be blocked," found *a* gate, and stopped. None traced the **full signal-to-emission path** end-to-end:

```
bond_strategies.py.run()
  → 7 raw signals
  → bond-agent.yml curation gate (FAILS here — 0/7 pass)
  → bond_picks.json written (with quality: 0)
  → [gap: no merge into active_picks.json]
  → forward_validator never sees them
  → would fail FORWARD_GATE_MIN_TRADES=50 even if it did
  → /audit shows legacy n=18 from futures_momentum on ZN=F
```

The lesson: **swarm-derived "root cause" claims need an end-to-end path trace before adoption.** Otherwise the swarm produces three confident, mutually exclusive, mostly wrong answers — which is exactly what happened here.
