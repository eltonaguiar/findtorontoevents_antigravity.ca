# Claude Integration & Debugging Guide

> **Date**: 2026-05-03  
> **Purpose**: Prompt for Claude to review, integrate, and debug all remediation changes  
> **Repo**: findtorontoevents_antigravity.ca

---

## Part 1: Review & Integration Prompt

You are reviewing and fixing the findtorontoevents_antigravity.ca trading platform. Multiple commits were made to main on 2026-05-03 to fix dead asset classes (FOREX, BOND, COMMODITY, ETF). Your job: verify correctness, wire everything into the live pipeline, and debug any asset class with poor performance.

### Files on Main (verify they exist)

| File | What it does |
|------|-------------|
| `audit_trail/quality_gates.py` | Score floors lowered, strategy overrides added, bond/ETF elite_grade exemption |
| `alpha_engine/strategy_blocklist.py` | 10 strategies unblocked, 1 toxic commodity banned |
| `alpha_engine/etf_scanner.py` | 4 ETF strategies, outputs to `active_picks_etf.json` |
| `alpha_engine/bond_scanner.py` | 3 bond strategies + FRED data, outputs to `active_picks_bond.json` |
| `alpha_engine/data_validator.py` | Signal/OHLCV/FRED validation, direction normalization |
| `alpha_engine/non_crypto_boosters.py` | Session-aware FX, COT commodity, momentum ETF, yield curve BOND boosters |
| `FOREX_COMMODITIES_BONDS.MD` | Full remediation plan (17 sections) |
| `ROOT_CAUSE_ANALYSIS_NON_CRYPTO.md` | 9 root causes identified |

### Verification Checklist

1. `python -m pytest tests/test_quality_gates.py -v` — no regressions on crypto
2. `from alpha_engine.etf_scanner import run_etf_scanner` — import works
3. `from alpha_engine.bond_scanner import run_bond_scanner` — import works
4. Verify `cta_commodity_momentum_term` IS in `_RETIRED_STRATEGIES`
5. Verify `bond_credit_spread` is NOT in `_RETIRED_STRATEGIES`
6. Verify BOND picks with `elite_grade="F"` pass `passes_active_gate()`

### Integration Needed

These new modules exist but aren't wired into the live pipeline yet:

- `non_crypto_boosters.py`: `compute_non_crypto_boost()` needs to be called from `elite_scorer.py` or `forward_validator.py`
- `get_effective_min_score()` in `quality_gates.py` needs to be called by `passes_smart_gate()` instead of the class-level constant
- `etf_scanner.py` and `bond_scanner.py` need cron jobs or workflow activation
- `yfinance` needs to be in `requirements.txt` if not already

---

## Part 2: Debugging Playbook — Fix Any Underperforming Asset Class

When an asset class has poor WR, PF, or zero active picks, follow this chain **IN ORDER**. Don't skip steps.

### STEP 1: Is it emitting signals?

```bash
# Check if strategies exist and are callable
grep -r "def.*signal\|def.*generate" alpha_engine/*strategies*.py | grep -i <ASSET_CLASS>

# Check if any active picks exist
python -c "
import json
picks = json.load(open('alpha_engine/data/active_picks.json'))
class_picks = [p for p in picks if p.get('asset_class','').upper() == '<ASSET_CLASS>']
print(f'Active picks: {len(class_picks)}')
for p in class_picks[:5]:
    print(f'  {p.get(\"strategy\")}: {p.get(\"symbol\")} {p.get(\"direction\")} score={p.get(\"elite_score\")}')
"
```

**If 0 picks**: the emitter pipeline is dead. Check:
- Is there a cron job running the scanner? (`crontab -l` or `.github/workflows/`)
- Does the scanner import the strategies correctly?
- Are the strategies in the blocklist? (`grep -i "<strategy_name>" alpha_engine/strategy_blocklist.py`)

### STEP 2: Are signals being killed by gates?

```bash
python -c "
from audit_trail.quality_gates import passes_active_gate
import json

picks = json.load(open('alpha_engine/data/scanner_output/active_picks_<class>.json'))
if isinstance(picks, dict): picks = picks.get('picks', [])

for p in picks[:10]:
    result = passes_active_gate(p)
    if not result:
        score = p.get('elite_score', 0)
        ac = p.get('asset_class', '')
        strategy = p.get('strategy', '')
        print(f'REJECTED: {strategy} {p.get(\"symbol\")} score={score} ac={ac}')
"
```

**Gate killers** (most to least likely):

| # | Gate | How to check | Fix |
|---|------|-------------|-----|
| 1 | Score floor too high | `score < SMART_PICKS_MIN_SCORE_<CLASS>` | Lower floor or add boosters |
| 2 | Elite grade D/F | `elite_grade in ("D", "F")` | Add class exemption |
| 3 | Forward WR floor | `forward_wr < class threshold` | Lower threshold |
| 4 | Strategy blocklist | `strategy in _RETIRED_STRATEGIES` | Unblock or replace |
| 5 | Symbol blocklist | `symbol in BLOCKED_SYMBOLS` | Fix symbol classification |
| 6 | Confidence dead zone | `0.65 < confidence < 0.75` | This band is anti-predictive |
| 7 | Matrix/symbol gate | Specific combo blocked | Check `matrix_symbol_gates.py` |

### STEP 3: Score diagnosis — why is the score so low?

```bash
python -c "
from alpha_engine.elite_scorer import compute_elite_score
import json

pick = {
    'symbol': 'TLT',
    'direction': 'LONG',
    'asset_class': 'BOND',
    'strategy': 'bond_yield_momentum',
    'confidence': 0.65,
    'entry_price': 90.0,
    'take_profit': 93.0,
    'stop_loss': 88.0,
}
score, breakdown = compute_elite_score(pick)
print(f'Total score: {score}')
print(json.dumps(breakdown, indent=2, default=str))
```

**If score < 40**, check which components are zeroed or negative:

| Component | Crypto | Non-Crypto | Impact |
|-----------|--------|-----------|--------|
| Regime bonus | 0–15 pts (dynamic) | Flat 10 pts (neutral) | Non-crypto gets less enrichment |
| Technical alignment | -30 to +5 | Same | #1 score killer if misaligned |
| Score booster (MTF/ensemble) | +0 to +25 | +0 (none) | Structural gap |
| Copy trader edge | -6 to +12 | N/A | Only for copy-sourced picks |
| Risk warning penalty | -3 | -3 | For flagged symbols |

**FIX**: Either lower the score floor OR add asset-class-specific boosters (`non_crypto_boosters.py`).

### STEP 4: Is the data actually there?

```bash
python -c "
import yfinance as yf

symbols = ['TLT', 'IEF', 'SHY', 'LQD', 'HYG']  # Bond example
for s in symbols:
    df = yf.download(s, period='1mo', progress=False)
    print(f'{s}: {len(df)} bars, last={df.index[-1].date()}, close={df[\"Close\"].iloc[-1]:.2f}')
"
```

**Common data issues:**

| Issue | Symptom | Fix |
|-------|---------|-----|
| Wrong ticker | `yfinance` returns empty | Fix symbol (e.g., `EURUSD=X` vs `EURUSD`) |
| FRED API key missing | Bond strategies fail | Set `FRED_API_KEY` env var |
| Stale data | Last bar > 3 days | Check market holiday or data feed |
| NaN in Close | Strategy skips symbol | Illiquid ETF, remove from universe |
| Missing columns | `KeyError: 'Close'` | yfinance column case changed |

### STEP 5: Is the strategy actually profitable in isolation?

```bash
python -c "
from alpha_engine.bond_strategies import bond_yield_momentum
import yfinance as yf

symbols = ['TLT', 'IEF', 'SHY', 'LQD', 'HYG', 'AGG', 'BND']
data = {}
for s in symbols:
    df = yf.download(s, period='2y', progress=False)
    if len(df) > 60:
        data[s] = df

signals = bond_yield_momentum(data)
print(f'Signals generated: {len(signals)}')
for s in signals:
    print(f'  {s[\"symbol\"]} {s[\"signal_type\"]} conf={s[\"confidence\"]} RR={s[\"risk_reward\"]}')
"
```

**If 0 signals**: the strategy logic is broken or the data format doesn't match. Check:
- Does the strategy iterate over `BOND_SYMBOLS` dict keys?
- Does it expect `df["Close"]` or `df["close"]`? (case matters)
- Does it need `fred_data` parameter?

### STEP 6: Transaction cost reality check

```python
COST_MODEL = {
    "CRYPTO":     0.0023,  # 0.23% round-trip
    "FOREX":      0.0003,  # 0.03% round-trip
    "COMMODITY":  0.0005,  # 0.05% round-trip
    "FUTURES":    0.0005,  # 0.05% round-trip
    "ETF":        0.0003,  # 0.03% round-trip
    "BOND":       0.0005,  # 0.05% round-trip
    "EQUITY":     0.0003,  # 0.03% round-trip
}

# Apply to closed picks
for pick in closed_picks:
    gross_pnl = pick['pnl_pct']
    cost = COST_MODEL[pick['asset_class']]
    net_pnl = gross_pnl - (cost * 2)
    pick['net_pnl'] = net_pnl
```

**If net PF < 1.0 but gross PF > 1.0**: the strategy's edge is smaller than transaction costs. Raise the R:R floor or find tighter-spread instruments.

### STEP 7: Tracking window

72.7% of picks never hit TP/SL within 24h. Forex and bonds need 5–14 days to resolve.

```bash
# Check resolution rate by asset class
python -c "
import json
from datetime import datetime, timedelta

picks = json.load(open('alpha_engine/data/closed_picks.json'))
for ac in ['CRYPTO', 'FOREX', 'BOND', 'COMMODITY', 'ETF']:
    ac_picks = [p for p in picks if p.get('asset_class') == ac]
    resolved_24h = sum(1 for p in ac_picks if _resolved_within(p, 24))
    print(f'{ac}: {resolved_24h}/{len(ac_picks)} resolved in 24h ({resolved_24h/len(ac_picks)*100:.0f}%)')
"
```

**FIX**: Extend tracking window from 24h to 120h minimum in `forward_validator.py`.

### STEP 8: The fix decision tree

```
IF 0 picks emitted:
  → Fix pipeline (cron, imports, scanner)

IF picks emitted but 0 reach dashboard:
  → Fix the specific gate (debug output tells you which)

IF score too low:
  → Option A: Lower score floor (quick fix)
  → Option B: Add score boosters (proper fix)
  → Option C: Add strategy-specific override (surgical fix)

IF data missing:
  → Fix data pipeline (ticker, API key, freshness)

IF strategy unprofitable:
  → Option A: Ban strategy, deploy replacement
  → Option B: Add filters (regime, session, R:R band)
  → Option C: Paper-trade until enough data

IF transaction costs kill edge:
  → Raise R:R floor, use limit orders, tighter-spread instruments

IF tracking window too short:
  → Extend from 24h to 120h in forward_validator.py
```

### STEP 9: Verify crypto didn't break

After ANY gate change:

```bash
python -m pytest tests/test_quality_gates.py -v

python -c "
from audit_trail.quality_gates import passes_active_gate
crypto_pick = {
    'symbol': 'BTCUSDT', 'direction': 'LONG', 'asset_class': 'CRYPTO',
    'strategy': 'fear_greed_contrarian', 'confidence': 0.80,
    'elite_score': 55, 'elite_grade': 'B',
    'entry_price': 84000, 'take_profit': 88000, 'stop_loss': 82000,
}
assert passes_active_gate(crypto_pick), 'CRYPTO pick should still pass!'
print('✅ Crypto regression check passed')
"
```

### STEP 10: Document what you found

After fixing, add a comment in the code explaining WHY:

```python
# 2026-05-03: Bond strategies were blocked by three independent gates:
# 1. Strategy blocklist (blanket-blocked by PR #256) — unblocked
# 2. Score floor 60 (unachievable without boosters) — lowered to 35
# 3. Elite grade D/F (low scores get graded D) — exempted BOND/ETF
# See ROOT_CAUSE_ANALYSIS_NON_CRYPTO.md for full analysis.
```

**NEVER** just change a threshold without documenting WHY. The next person (or AI) reviewing this code needs to understand the reasoning or they'll revert your change.

---

## Part 3: Key Principles

1. **Every change must be**: hypothesized → tested → measured → rolled back if failed
2. **Paper-trade** new strategies for 2 weeks before live capital
3. **Crypto is the dominant class** — never break it while fixing others
4. **Score floors were raised before boosters existed** — that's why non-crypto died
5. **The strategy blocklist was a blanket kill** — surgical unblock, not wholesale restore
6. **Transaction costs matter more** for low-vol classes (forex, bonds)
7. **24h tracking window biases** against slow markets (forex/bonds need 5–14 days)
8. **Document everything** — undocumented changes get reverted

---

## Part 4: 7 Diagnostic Questions

Ask these for EVERY underperforming asset class:

| # | Question | If NO |
|---|----------|-------|
| 1 | Is it emitting signals? | Fix pipeline (cron, imports, scanner) |
| 2 | Is it being killed by gates? | Fix the specific gate |
| 3 | Is the score too low? | Lower floor or add boosters |
| 4 | Is the data there? | Fix data pipeline |
| 5 | Is the strategy profitable in isolation? | Ban or replace strategy |
| 6 | Do transaction costs kill the edge? | Raise R:R floor, tighter spreads |
| 7 | Is the tracking window long enough? | Extend to 120h |

---

## Part 5: Root Cause Summary (Already Fixed)

| Root Cause | Status | Commit |
|-----------|--------|--------|
| Score floor gap (55-65 vs achievable 30-45) | ✅ Fixed | `e079f98` |
| Emitter pipeline not wired (ETF/BOND) | ✅ Fixed | `5a126e8`, `4a0a1c2` |
| 13 strategies blanket-blocked | ✅ Fixed | `5a4c852` |
| cta_commodity_momentum_term toxic (PF 0.02) | ✅ Banned | `5a4c852` |
| Bond/ETF elite_grade D/F blocking | ✅ Fixed | `9c7c0f3` |
| Non-crypto score boosters missing | ✅ Created | `06a41a8` |
| Data validator missing | ✅ Created | `673f998` |

## Part 6: Root Cause Summary (Still Needs Work)

| Root Cause | Status | What's Needed |
|-----------|--------|---------------|
| non_crypto_boosters not wired into scoring | 🔜 | Call from elite_scorer.py |
| get_effective_min_score() not used by smart gate | 🔜 | Wire into passes_smart_gate() |
| Transaction cost model not deployed | 🔜 | Add to config.py, apply to all P&L |
| Tracking window too short (24h) | 🔜 | Extend to 120h in forward_validator.py |
| R:R ceiling missing (>2.0 catastrophic) | 🔜 | Add max_risk_reward = 2.0 gate |
| ETF/BOND scanners need cron activation | 🔜 | Move workflow to .github/workflows/ |

---

*Generated 2026-05-03. See FOREX_COMMODITIES_BONDS.MD for full remediation plan and ROOT_CAUSE_ANALYSIS_NON_CRYPTO.md for root cause details.*
