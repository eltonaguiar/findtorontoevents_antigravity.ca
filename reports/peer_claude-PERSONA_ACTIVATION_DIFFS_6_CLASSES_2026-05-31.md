# Persona Activation Diff Packets — 6 Classes × 33 Steps — 2026-05-31

**Source PR:** #219 (`feat(tournament): per-class strategy-grounded personas (shadow-only)`)
**Source doc:** `reports/peer_claude-per-class-strategy-personas_2026-05-31.md`
**Author:** Claude (operator-item #5, wave wnkqcqck5)

This file is the copy-paste packet for the operator to activate the 6 personas landed in PR #219. All 33 documented activation steps are grouped by asset class, with pre-flight checks, exact diff targets, apply commands, verification, rollback, and explicit activation gates.

**Steps covered: 33 of 33** (EQUITY 7 + FOREX 6 + CRYPTO 5 + ETF 5 + BOND 5 + COMMODITY 5).

---

## Shared infrastructure (applies to every class)

Two shared files take entries for every persona:

- `tools/populate_picks.py:405` — `PERSONA_STRATEGIES: dict[str, str]` (one-line description)
- `tools/populate_picks.py:456` — `PERSONA_THESIS_MAP: dict[str, list[str]]` (2-4 thesis sentences)
- `config/model_persona_mapping.json` — per-model × asset_class assignment

Pre-flight (run once):
```bash
grep -n "PERSONA_STRATEGIES\b\|PERSONA_THESIS_MAP\b" tools/populate_picks.py
# Expect lines 393, 394, 405, 456, 557, 651, 657, 821
python3 -c "import json; json.load(open('config/model_persona_mapping.json'))" && echo ok
ls config/personas/strategy_persona__*.json | wc -l   # expect 6
```

Kill-list pre-flight (run once for all classes):
```bash
python3 - <<'PY'
import re, pathlib
src = pathlib.Path('alpha_engine/auto_tuner.py').read_text()
for tag in ['PERMANENTLY_KILLED','LOW_CONFIDENCE_STRATEGIES','HARD_DISABLED_PATTERNS']:
    m = re.search(rf'{tag}\s*=\s*[\{{\[].*?[\}}\]]', src, re.S)
    print(tag, '->', (m.group(0)[:300] if m else 'NOT FOUND'))
PY
```

---

## 1. EQUITY — `strategy_persona__equity_rsi2_pullback` (7 steps)

**Wraps:** `stocks_rsi2_pullback` · **Live:** n=34, WR 52.9%, PF 1.52 · **MC P(T2@n=100):** 0.52

### Pre-flight
```bash
mysql -h ftps2.50webs.com -u ejaguiar1_stocks -p"$(grep -A1 ejaguiar1_stocks /home/eaguiar2015/dbpasses.txt | tail -1)" ejaguiar1_stocks -e "
  SELECT COUNT(*) live_rows, ROUND(AVG(pnl_pct),3) avg_pnl
  FROM trading_picks WHERE strategy='stocks_rsi2_pullback' AND closed_at IS NOT NULL;"
# Expect >=34 rows (Phase-3 MC envelope)
grep -n "stocks_rsi2_pullback" alpha_engine/auto_tuner.py
# Expect NO match in PERMANENTLY_KILLED / LOW_CONFIDENCE_STRATEGIES
```

### Activation gate
> **DO NOT activate until** auto_tuner kill-list pre-flight passes clean. If incident #202 applied an n=10 kill on 2026-05-28, the kill must be reverted first.

### Diff targets
1. `alpha_engine/auto_tuner.py` — if `stocks_rsi2_pullback` appears in kill block, remove that one line.
2. `tools/populate_picks.py:405` (`PERSONA_STRATEGIES`) — append entry.
3. `tools/populate_picks.py:456` (`PERSONA_THESIS_MAP`) — append entry.
4. `config/model_persona_mapping.json` — append persona_id to `cursor_agent.EQUITY` AND `claude_opus.EQUITY` arrays.

### Apply commands
```python
# tools/populate_picks.py:405 — add inside PERSONA_STRATEGIES dict
"strategy_persona__equity_rsi2_pullback": "RSI(2) pullback in established uptrend (S&P 500, ADV20>$50M)",
```
```python
# tools/populate_picks.py:456 — add inside PERSONA_THESIS_MAP dict
"strategy_persona__equity_rsi2_pullback": [
    "Larry-Connors RSI(2) < 10 in a stock above its 200SMA with adequate liquidity.",
    "Exit on RSI(2) > 70 or 5-day hard time-stop; stop below entry-day low.",
    "Highest conviction when SPY itself is above its 200SMA and VIX < 20.",
],
```
```bash
# config/model_persona_mapping.json — append persona_id to each model's EQUITY list
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('config/model_persona_mapping.json')
d = json.loads(p.read_text())
for m in ('cursor_agent','claude_opus'):
    bucket = d.setdefault(m, {}).setdefault('EQUITY', [])
    pid = 'strategy_persona__equity_rsi2_pullback'
    if pid not in bucket: bucket.append(pid)
p.write_text(json.dumps(d, indent=2) + "\n")
PY
```

### Verification (24h after activation)
```sql
SELECT COUNT(*) FROM tournament_picks
WHERE model_id LIKE 'strategy_persona__equity_rsi2_pullback%'
  AND created_at >= NOW() - INTERVAL 24 HOUR;
```

### Rollback
```bash
git checkout HEAD -- tools/populate_picks.py config/model_persona_mapping.json
# Operationally: remove persona_id from the two EQUITY arrays; restart populate_picks worker.
```

### Re-promote gate (live sizing)
n ≥ 100 closed AND PF ≥ 1.5 AND DSR-concentration gate passes.

---

## 2. FOREX — `strategy_persona__forex_carry_trade_momentum` (6 steps)

**Wraps:** `fx_smart_carry_trade_momentum` · **Live:** n=21, WR 52.4%, PF 1.62 · **MC P(T2@n=100):** 0.64 (best candidate)

### Pre-flight
```bash
grep -n "fx_smart_carry_trade_momentum" alpha_engine/auto_tuner.py   # expect no kill-list match
mysql ... -e "SELECT symbol, COUNT(*) n FROM trading_picks
  WHERE strategy='fx_smart_carry_trade_momentum' AND closed_at IS NOT NULL
  GROUP BY symbol ORDER BY n DESC;"
# Watch USDJPY share — historical 55% concentration is the live risk
```

### Activation gate
> **DO NOT activate until** a per-symbol concentration cap of 40% is wired into the persona emit path (step 5). USDJPY-only carry is the legacy 55% concentration trap (PF 0.55).

### Diff targets
1. `tools/populate_picks.py:405` — PERSONA_STRATEGIES.
2. `tools/populate_picks.py:456` — PERSONA_THESIS_MAP.
3. `config/model_persona_mapping.json` — `claude_opus.FOREX` AND `gemini_25_pro.FOREX`.
4. Per-symbol cap: at emit time (worker that reads this persona), enforce `open_exposure[symbol] / total_open_exposure <= 0.40`.

### Apply commands
```python
# tools/populate_picks.py:405
"strategy_persona__forex_carry_trade_momentum": "Carry+momentum FX with IR-diff filter and trend confirmation",
```
```python
# tools/populate_picks.py:456
"strategy_persona__forex_carry_trade_momentum": [
    "Long higher-yielder / short lower-yielder when 12m trend confirms direction.",
    "Filter out pairs with central-bank surprise risk in next 48h (FOMC/BoJ calendar).",
    "Per-symbol cap 40% of persona exposure — no single pair (esp. USDJPY) dominates.",
],
```
```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('config/model_persona_mapping.json'); d = json.loads(p.read_text())
for m in ('claude_opus','gemini_25_pro'):
    b = d.setdefault(m, {}).setdefault('FOREX', [])
    pid = 'strategy_persona__forex_carry_trade_momentum'
    if pid not in b: b.append(pid)
p.write_text(json.dumps(d, indent=2) + "\n")
PY
```

### Verification
```sql
SELECT symbol, COUNT(*) n FROM tournament_picks
WHERE model_id LIKE 'strategy_persona__forex_carry_trade_momentum%'
  AND created_at >= NOW() - INTERVAL 24 HOUR GROUP BY symbol;
-- Pass: no single symbol > 40% of total
```

### Rollback
`git checkout HEAD -- tools/populate_picks.py config/model_persona_mapping.json` + restart worker.

### Re-promote gate
n ≥ 100 closed AND PF ≥ 1.5 AND USDJPY concentration < 40%.

---

## 3. CRYPTO — `strategy_persona__crypto_trust7_promoter` (5 steps) [**BLOCKED**]

**Wraps:** meta-gate `trust_score >= 7` over surviving crypto emitters · **Live (trust=7 cohort):** n=99 / WR 85.9%

### **HARD BLOCK — DO NOT activate**

This persona is gated on **two** upstream fixes. Activating before they land will accrue bad outcomes from mislabeled TP_HITs and 369 banned-strategy picks/7d.

| Blocker | Source | Status |
|---|---|---|
| (a) Plan #198 blocklist wired in `production_scanner` | `reports/phase10b_crypto_money_maker_readyv2_2026-05-31.md` | **PENDING** — 369 banned picks/7d still emitting |
| (b) Resolver TIME_EXIT vs TP_HIT label fix (Phase 11 wave) | session memory `project-money-ready-2026-05-31` | **PENDING** — 162 CRYPTO mislabels |

> **CRYPTO WARNING:** The resolver currently mislabels TIME_EXIT outcomes as TP_HIT for 162 closed CRYPTO picks. If this persona is activated before the Phase 11 resolver fix, every `trust_score >= 7` pick that hits a time-stop will be booked as a winner, inflating PF and forcing premature live promotion. **Activation is conditional on Phase 11 resolver TIME_EXIT rewrite landing first.**

### Dependency on operator-item #X (PR #232 follow-on)
This persona depends on the Phase 11 wave landing the resolver intrabar rewrite (session memory: "resolver intrabar is THE upstream T2 blocker"). Track that PR's number; do not pull this packet until that PR is merged AND a re-derived `pf_registry.by_asset_class_policy_clean_net` CRYPTO row shows PF > 0.8 (current 0.37).

### Diff targets (deferred — for reference only)
1. `alpha_engine/smart_picks_engine.py::passes_active_gate` — add `if asset_class == 'CRYPTO' and trust_score < 7: return False`.
2. `tools/populate_picks.py:405` — PERSONA_STRATEGIES entry.
3. `tools/populate_picks.py:456` — PERSONA_THESIS_MAP entry.

### Apply commands (DO NOT RUN until both blockers cleared)
```python
# tools/populate_picks.py:405
"strategy_persona__crypto_trust7_promoter": "Trust-score >= 7 meta-filter over surviving CRYPTO emitters",
```
```python
# tools/populate_picks.py:456
"strategy_persona__crypto_trust7_promoter": [
    "Trust score >= 7 has 85.9% WR over n=99 in pre-fix data — re-derive in clean data first.",
    "Apply only to CRYPTO; meta-filter sits on top of the blocklist-respecting emitter set.",
    "Concentration check: ensure trust=7 cohort is not 90%+ in any single emitter.",
],
```

### Verification (post-block-clear)
```sql
-- Step 1: re-derive cohort PF in clean data
SELECT COUNT(*), AVG(pnl_pct>0)*100 wr, ROUND(SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END)
       / NULLIF(ABS(SUM(CASE WHEN pnl_pct<0 THEN pnl_pct ELSE 0 END)),0),2) pf
FROM trading_picks WHERE category='crypto' AND trust_score>=7 AND closed_at IS NOT NULL
  AND closed_at >= (SELECT MIN(closed_at) FROM trading_picks WHERE resolver_version='intrabar_v2');
-- PASS gate: PF >= 1.5 in post-fix data with n >= 50
```

### Rollback
Remove the `passes_active_gate` patch. Remove persona from any model_persona_mapping.json bucket. Restart smart_picks worker.

### Re-promote gate
Both blockers cleared AND re-derived PF ≥ 1.5 in clean post-fix data with n ≥ 100.

---

## 4. ETF — `strategy_persona__etf_regime_bull` (5 steps)

**Wraps:** `regime_mild_bull` (ETF branch only) · **Live ETF:** n=2 (INSUFF-N artifact)

### Pre-flight
```bash
grep -n "regime_mild_bull" alpha_engine/auto_tuner.py   # expect no kill-list match
mysql ... -e "SELECT category, COUNT(*) n FROM trading_picks
  WHERE strategy='regime_mild_bull' AND closed_at IS NOT NULL GROUP BY category;"
# Confirms category-mess: ETF=2, EQUITY=2, stocks=4, crypto=1
```

### Activation gate
> **DO NOT activate until** the persona emit path filters strictly on resolved `asset_class == 'ETF'`. Filtering on raw `category` will pull in stocks/crypto leakage rows (-4.5% crypto pick was a category leak).

### Diff targets
1. `tools/populate_picks.py:405` — PERSONA_STRATEGIES.
2. `tools/populate_picks.py:456` — PERSONA_THESIS_MAP.
3. `config/model_persona_mapping.json` — `claude_opus.ETF` AND `ring_261T.ETF`.
4. Persona emit path: hardcode `asset_class_whitelist=['ETF']` (NOT category).

### Apply commands
```python
# tools/populate_picks.py:405
"strategy_persona__etf_regime_bull": "Mild-bull regime ETF rotation (SPY/QQQ/IWM/sector ETFs)",
```
```python
# tools/populate_picks.py:456
"strategy_persona__etf_regime_bull": [
    "Macro regime classifier says mild-bull (SPY>200SMA, VIX<20, breadth positive).",
    "Long broad-market or pro-cyclical sector ETF; exit on regime flip to neutral or risk-off.",
    "ETF asset_class only — block stocks/crypto leakage from raw category column.",
],
```
```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('config/model_persona_mapping.json'); d = json.loads(p.read_text())
for m in ('claude_opus','ring_261T'):
    b = d.setdefault(m, {}).setdefault('ETF', [])
    pid = 'strategy_persona__etf_regime_bull'
    if pid not in b: b.append(pid)
p.write_text(json.dumps(d, indent=2) + "\n")
PY
```

### Verification
```sql
SELECT asset_class, COUNT(*) FROM tournament_picks
WHERE model_id LIKE 'strategy_persona__etf_regime_bull%'
  AND created_at >= NOW() - INTERVAL 24 HOUR GROUP BY asset_class;
-- Pass: 100% asset_class='ETF'
```

### Rollback
`git checkout HEAD -- tools/populate_picks.py config/model_persona_mapping.json`.

### Re-promote gate
n ≥ 30 ETF closed AND PF ≥ 1.5 (shadow mandatory at current n=2).

---

## 5. BOND — `strategy_persona__bond_futures_momentum_zn` (5 steps)

**Wraps:** `futures_momentum` whitelisted to `ZN=F` · **Live ZN=F:** n=5 (artifact PF 362.6)

### Pre-flight
```bash
grep -n "futures_momentum\b" alpha_engine/auto_tuner.py   # confirm futures_momentum (NOT futures_ema_stack_momentum) is clean
mysql ... -e "SELECT category, COUNT(*) n, ROUND(AVG(pnl_pct),3) avg
  FROM trading_picks WHERE strategy='futures_momentum' AND closed_at IS NOT NULL
  GROUP BY category;"
# Confirms commodity n=597 PF 0.45 dominates without symbol whitelist
```

### Activation gate
> **CRITICAL — DO NOT activate without symbol whitelist.** The persona MUST enforce `symbol_whitelist=['ZN=F']` at emit time. Without it, the commodity branch (n=597, PF 0.45) overwhelms the bond branch and destroys the persona.

### Diff targets
1. `tools/populate_picks.py:405` — PERSONA_STRATEGIES.
2. `tools/populate_picks.py:456` — PERSONA_THESIS_MAP.
3. `config/model_persona_mapping.json` — `claude_opus.BOND`.
4. Persona emit path: `symbol_whitelist=['ZN=F']` hardcoded.

### Apply commands
```python
# tools/populate_picks.py:405
"strategy_persona__bond_futures_momentum_zn": "ZN=F (10Y Treasury futures) trend-following — symbol-whitelisted",
```
```python
# tools/populate_picks.py:456
"strategy_persona__bond_futures_momentum_zn": [
    "Trend-follow ZN=F only — 10Y Treasury futures momentum filter.",
    "Long when ZN=F above 50d SMA with positive 20d slope; short on reverse.",
    "Hard symbol whitelist [ZN=F]; do NOT emit on ES/CL/GC/NQ even if signal fires.",
],
```
```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('config/model_persona_mapping.json'); d = json.loads(p.read_text())
b = d.setdefault('claude_opus', {}).setdefault('BOND', [])
pid = 'strategy_persona__bond_futures_momentum_zn'
if pid not in b: b.append(pid)
p.write_text(json.dumps(d, indent=2) + "\n")
PY
```

### Verification
```sql
SELECT symbol, COUNT(*) FROM tournament_picks
WHERE model_id LIKE 'strategy_persona__bond_futures_momentum_zn%'
  AND created_at >= NOW() - INTERVAL 24 HOUR GROUP BY symbol;
-- Pass: 100% symbol='ZN=F'
```

### Rollback
Remove persona from `claude_opus.BOND`; revert populate_picks.py.

### Re-promote gate
n ≥ 30 ZN=F closed AND PF ≥ 1.5. The current 5-pick PF 362.6 is a 1-trade artifact; ignore.

---

## 6. COMMODITY — `strategy_persona__commodity_non_cot_research` (5 steps)

**Wraps:** NONE (research scaffold) · **Live:** n=0 (no signal source exists)

### Activation gate
> **DO NOT activate until** non-COT signal source pipeline lands. This persona is a SCAFFOLD with no emitter; activating it without signals produces zero picks but pollutes the model_persona_mapping namespace.

### Dependency on upstream work (DEFERRED — out of scope of PR #219)
| Required signal source | Owner | ETA |
|---|---|---|
| EIA weekly inventory delta scraper | TBD | TBD |
| NOAA seasonal anomaly index | TBD | TBD |
| USDA WASDE surprise scorer | TBD | TBD |

This depends on a future operator wave (not PR #232). Mark as **DEFERRED**; do not include in current activation rollout.

### Diff targets (deferred — for reference only)
1. `tools/scrapers/eia_inventory.py` — NEW.
2. `tools/scrapers/noaa_seasonal.py` — NEW.
3. `tools/scrapers/usda_wasde.py` — NEW.
4. `tools/populate_picks.py:405` + `:456` — PERSONA_STRATEGIES + PERSONA_THESIS_MAP.
5. `config/model_persona_mapping.json` — COMMODITY slots in 2-3 models (replacing existing `cta_trend` / `seasonal_pattern` mappings).

### Apply commands (placeholder — do not run yet)
```python
# tools/populate_picks.py:405 (deferred)
"strategy_persona__commodity_non_cot_research": "Non-COT commodity signals (EIA/NOAA/USDA) — research-only",
```

### Verification (post-pipeline-build)
```sql
SELECT COUNT(*) FROM tournament_picks
WHERE model_id LIKE 'strategy_persona__commodity_non_cot_research%'
  AND created_at >= NOW() - INTERVAL 24 HOUR;
-- After signal pipeline lands, expect non-zero forward-only shadow picks
```

### Rollback
Revert scraper modules; remove persona from model_persona_mapping COMMODITY arrays.

### Re-promote gate
n ≥ 100 forward-only closed shadow picks AND PF ≥ 1.5 AND `CT=F` concentration < 30%.

---

## Cross-class dependency summary

| Persona | Depends on | Block? |
|---|---|---|
| equity_rsi2_pullback | None (clean go) | NO — safe to activate |
| forex_carry_trade_momentum | Per-symbol cap implementation | SOFT — wire cap then go |
| **crypto_trust7_promoter** | **Phase 11 resolver TIME_EXIT fix + plan #198 blocklist wiring** | **HARD BLOCK** |
| etf_regime_bull | asset_class whitelist (not raw category) | SOFT — wire whitelist then go |
| bond_futures_momentum_zn | ZN=F symbol whitelist enforcement | SOFT — wire whitelist then go |
| commodity_non_cot_research | EIA/NOAA/USDA scraper pipeline (NEW work) | HARD BLOCK (deferred wave) |

**Recommended rollout order:**
1. EQUITY (lowest friction, best Phase-3 MC of T2 candidates).
2. FOREX (after per-symbol cap wired).
3. ETF + BOND in parallel (after their respective whitelists wired).
4. CRYPTO (only after Phase 11 resolver wave).
5. COMMODITY (after scraper pipeline wave — separate operator item).

---

## Step coverage tally

| Class | Steps in source persona JSON | Covered in this doc |
|---|---|---|
| EQUITY | 7 | 7 |
| FOREX | 6 | 6 |
| CRYPTO | 5 | 5 |
| ETF | 5 | 5 |
| BOND | 5 | 5 |
| COMMODITY | 5 | 5 |
| **TOTAL** | **33** | **33** |

## Return
`PERSONA_ACTIVATION_DIFFS: classes=6 steps_covered=33`
