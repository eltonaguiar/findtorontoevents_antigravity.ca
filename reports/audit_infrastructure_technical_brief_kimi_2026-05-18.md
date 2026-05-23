# Technical Brief: Pick Tracking & Audit Infrastructure
## Repository: findtorontoevents_antigravity.ca
## Analysis Date: Current Session
## Analyst: Senior Quantitative Trading Systems Engineer

---

## Executive Summary

The system uses a multi-layered quality gate architecture in `quality_gates.py` (1669+ lines) with a centralized dashboard generator in `dashboard_generator.py` (17405+ lines). Picks flow from 30+ JSON source files across 16+ subsystems through progressive gates (active gate, smart gate, HF gate, PCG5 gate) before reaching the audit dashboard. Pick rejection reasons are logged to an SQLite `filter_log` table. A shadow-mode system exists for new strategies. Full pick lifecycle traceability is partially implemented but has significant gaps, particularly in the filter-to-close causal chain.

---

## 1. PICK LIFECYCLE: GENERATION TO CLOSE

### Data Flow Architecture

```
[Pick Sources: 30+ JSON files]
    ↓ (dashboard_generator.py::collect_all_picks, line 8193)
[Normalize + Extract]
    ↓ (_normalize_pick, _extract_picks)
[Active Pick Pool] ──[score penalty]──> [Filtered Out (penalized, still shown)]
    ↓
[External Source Gate] ──[hard-remove]──> [Killed Picks]
    ↓
[Kill List Enforcement] ──[score -40]──> [Killed Strategy Picks]
    ↓
[Entry Drift Guard] ──[score -20]──> [Drift-Flagged Picks]
    ↓
[Freshness Gate] ──[skip system]──> [Stale System Skipped]
    ↓
[Quality Gates: quality_gates.py]
    ├── passes_active_gate() → hard reject (bool)
    ├── passes_smart_gate() → hard reject + score calculation
    ├── HF Strict Gate → high-frequency filtering
    └── PCG5 Portfolio Gate → portfolio-level constraints
    ↓
[Smart Score Calculation (0-100)]
    ↓
[Audit Dashboard: generate() → payload JSON → template.html]
    ↓
[Resolution / Close]
    ├── Outcome recorded in closed_picks.json per system
    ├── MySQL/MariaDB: at_pick_features table (status → CLOSED, pnl_pct set)
    └── audit_trail.db: strategy_stats updated
```

### Source Systems (JSON_PICK_SOURCES)

**File:** `audit_trail/dashboard_generator.py:3587+`

At least 30 systems feed picks:

| System | Active File | Closed File |
|--------|------------|-------------|
| alpha_engine | `alpha_engine/data/active_picks.json` | `alpha_engine/data/closed_picks.json` |
| battleground | `battleground/data/active_picks.json` | `battleground/data/closed_picks.json` |
| mercury2 | `mercury2/data/active_picks.json` | `mercury2/data/closed_picks.json` |
| paper_trading | `paper_trading/data/active_picks.json` | `paper_trading/data/closed_picks.json` |
| ml_bg_system_a-f | `ml_battleground/system_*/data/active_picks.json` | `ml_battleground/system_*/data/closed_picks.json` |
| ml_bg_ensemble | `ml_battleground/ensemble_data/active_picks.json` | `ml_battleground/ensemble_data/closed_picks.json` |
| rapid_fire | `rapid_fire/data/active_picks.json` | `rapid_fire/data/now_picks.json` |
| super_signals | `cross_aggregation/data/super_signals.json` | (same file mixed) |
| contrarian systems | `contrarian/data/active_picks.json` | `contrarian/data/closed_picks.json` |
| genome | `genetic_programmer/data/genome_picks.json` | `genetic_programmer/data/closed_picks.json` |
| KIMI RiseOfTheClaw | `KIMI_RISEOFTHECLAW/data/active_picks.json` | (via competition JSON) |
| STOCKS competition | `STOCKS/competition/forward_picks.json` | (picks array with status) |
| claude_gainer | `claude_gainer_ml/tracker/claude_live_picks.json` | (picks dict) |
| bond_agent | `bond_futures_agent/data/active_picks.json` | `bond_futures_agent/data/closed_picks.json` |
| forex_futures | `forex_futures_agent/data/active_picks.json` | `forex_futures_agent/data/closed_picks.json` |
| orphan_emitter_* | Various | Various |

### Special Sources (non-standard formats)

From `dashboard_generator.py:8193-8400`:

- **KIMI RiseOfTheClaw**: object with `activePicks` array (line ~8290)
- **STOCKS Competition**: object with `picks` array + status field (line ~8298)
- **Mercury2 Fast**: object with `picks` array, entry price validation >500000 skipped (line ~8318)
- **Claude Gainer ML**: object with `picks` dict, remaps `tp1_price`→`take_profit`, `sl_price`→`stop_loss` (line ~8338)
- **Cross-Aggregation Consensus**: object with `active`/`closed` arrays, source field mapping (line ~8378)

### Pick Normalization

**Function:** `_normalize_pick()` in `dashboard_generator.py`

Maps every incoming pick to a canonical schema:
- `symbol`, `direction`, `strategy`, `source_system`
- `entry_price`, `take_profit`, `stop_loss`
- `asset_class` (derived via `_derive_asset_class()`)
- `status` (OPEN/CLOSED)
- `score`, `confidence`
- `created_at`, `closed_at`, `pnl_pct`
- `id` (auto-generated if missing: `{symbol}_{strategy}_{timestamp}`)

### Gate Summary Statistics

From `dashboard_generator.py::collect_all_picks()`:
```python
_gate_killed, _gate_stale, _gate_low_rr = 0, 0, 0
_ghost_skipped = 0
```

External source gate actions (`_apply_external_source_gate`):
- `action == "killed"` → hard-remove + count `_gate_killed`
- `action == "tagged"` → `_stale` tag + `_low_rr` tag + score penalty

---

## 2. QUALITY GATES: ALL FILTERS IN quality_gates.py

### 2.1 Main Gate Functions

| Function | Line | Purpose |
|----------|------|---------|
| `passes_active_gate()` | ~5939 | Dashboard visibility gate — hard-rejects catastrophic picks |
| `passes_smart_gate()` | ~7830 | Smart pick eligibility — score-based + ML composite |
| `passes_hf_strict_gate()` | ~8343 | High-frequency trading gate (env HF_STRICT=1) |
| `passes_pcg5_gate()` | ~8494 | Portfolio construction gate level 5 |
| `meta_label_gate()` | ~3103 | ML-based WOULD_REJECT classifier (shadow by default) |
| `concept_gate_shadow_audit()` | ~9084 | Concept-family metadata for explainability (read-only) |

### 2.2 BLOCKED_* Sets / Blacklists

#### BLOCKED_SYMBOLS (line ~1700)
- `EQUITY_BLOCKED_SYMBOLS` (~97 symbols): `"CXAI"`, `"SOXS"`, `"LABD"`, `"SQQQ"`, `"UVXY"`, `"TQQQ"`, `"SPXS"`, `"FAZ"`, `"YANG"`, `"WEBS"`, `"CWEB"`, etc.
- `ETF_BLACKLIST` (~167 symbols): `"XLRE"`, `"XLC"`, `"PAVE"`, `"ARKK"`, etc.
- `COMMODITY_BLACKLIST` (~52 symbols): `"KC=F"`, `"ZO=F"`, `"ZR=F"`, `"QO=F"`, `"GC=F"`, `"SI=F"`, `"CL=F"`, etc.
- `BLOCKED_ASSET_CLASSES`: `frozenset({"OPTION", "SPREAD", "SWAP"})`
- `BLOCKED_SYMBOLS`: Union of all above + deduped

#### BLOCKED_STRATEGIES (line ~1987)
Complete set of ~49 permanently blocked strategy names:
```python
BLOCKED_STRATEGIES = {
    "crypto_divergent_stretch",
    "crypto_divergent_stretch_doge",
    "crypto_divergent_stretch_doge_v1",
    "crypto_funding_spike",
    "crypto_funding_spike_doge",
    "crypto_hlc_break_reversal",
    "crypto_hlc_break_reversal_doge",
    "crypto_ema_regime_adaptive",
    "crypto_ema_regime_adaptive_doge",
    "crypto_hybrid_trend_capture",
    "crypto_hybrid_trend_capture_doge",
    "crypto_hybrid_trend_capture_doge_v1",
    "crypto_hybrid_trend_capture_btc_v1",
    "crypto_vwap_premium_divergence",
    "crypto_vwap_premium_divergence_doge",
    "crypto_volume_profile_break",
    "crypto_volume_profile_break_doge",
    "crypto_social_volume_surge",
    "crypto_social_volume_surge_doge",
    "crypto_social_volume_surge_doge_v1",
    "crypto_social_volume_surge_btc_v1",
    "crypto_multi_tf_agreement",
    "crypto_multi_tf_agreement_doge",
    "crypto_multi_tf_agreement_btc_v1",
    "crypto_institutional_flow",
    "crypto_institutional_flow_doge",
    "crypto_institutional_flow_doge_v1",
    "crypto_institutional_flow_btc_v1",
    "crypto_rsi_divergence",
    "crypto_rsi_divergence_doge",
    "crypto_rsi_divergence_btc_v1",
    "crypto_soc_delta_divergence_a03_v1",  # also in KILLED
    "crypto_soc_dynamic_risk_heat_a02_v1", # also in KILLED
    "crypto_soc_dynamic_risk_heat_a03_v1", # also in KILLED
    "crypto_soc_mtf_orb_pivots_a02_v1",
    "crypto_soc_proxy_decoupling_a03_v1",
    "crypto_soc_regime_filters_a01_v1",
    "crypto_soc_regime_filters_a02_v1",
    "crypto_soc_regime_filters_a03_v1",
    "crypto_soc_vol_expansion_index_a08_v1",
    "yahoo_analyst_consensus",  # also in KILLED
    "hl_funding_fade",  # also in KILLED
    "binance_smart_money",  # also in KILLED
    "ema_cloud_scalp",
    "soc_regime_momentum_doge",
    "crypto_soc_mtf_orb_pivots_a03_v1",
    "crypto_soc_proxy_decoupling_a06_v1",
    "crypto_soc_regime_filters_a06_v1",
    "crypto_soc_regime_filters_a07_v1",
    "crypto_soc_regime_filters_a08_v1",
    "crypto_soc_regime_filters_a10_v1",
}
```

#### BLOCKED_STRATEGY_SYMBOL_PAIRS (line ~2257)
Per-symbol exclusions for specific strategies. Sample:
```python
BLOCKED_STRATEGY_SYMBOL_PAIRS = {
    ("battleground_vwap_1h_mut", "LINK-USD"),
    ("battleground_vwap_1h_mut", "DOGE-USD"),
    ("claude_gainer_st", "NFLX"),
    ("claude_gainer_st", "ARM"),
    ("ml_crypto_predictor", "BTC-USD"),  # LONG killed, SHORT retained
}
```

#### BLOCKED_ASSET_SOURCE_PAIRS (line ~2282)
Asset class + source system exclusions:
```python
BLOCKED_ASSET_SOURCE_PAIRS = {
    ("CRYPTO", "yahoo_finance"),
    ("CRYPTO", "yahoo_trend"),
    ("CRYPTO", "yahoo_analyst"),
    ("FOREX", "yahoo_finance"),
    ("FOREX", "yahoo_trend"),
    ("BOND", "yahoo_finance"),
    ("COMMODITY", "yahoo_finance"),
}
```

#### BLOCKED_ACTIVE_TRUST_LABELS / BLOCKED_ACTIVE_TRUST_TIERS (line ~1290)
- `BLOCKED_ACTIVE_TRUST_LABELS = {"Unknown", "Unverified"}`
- `BLOCKED_ACTIVE_TRUST_TIERS = frozenset({0})` (tier 0 = no trust)

#### PERMANENTLY_KILLED_STRATEGIES (line ~1326)

**85+ strategies** in the kill list with detailed audit comments. Notable entries:
- `claude_gainer_st` — 778/790 PROVEN picks, 26.5% WR, -355% total PnL
- `quan_engine_scalp` — 25% WR, 1793 trades, -352.88% PnL (worst by total loss)
- `copy_hl_lb_none` — 32% WR, 278 trades, -806.4% PnL (2nd worst)
- `ml_crypto_predictor` — LONG only killed, SHORT retained (direction-specific)
- `forex_rsi2_mean_reversion` — re-blocked 2026-05-13 (post-resolver-v2)
- `macd_crossover` — 25-31% WR, 139 leaked picks
- `st_rsi_momentum_confluence` — 10% WR LONG (10W/95L, -296.5% PnL) — WORST in system
- `crypto_soc_*` family — extensive 0% WR bleeders (20+ variants)
- `st_bb_squeeze_expansion` — 31.7% WR, PF 0.33
- `Value + Quality` — n=51 WR 7.8% PF 0.15

Kill list has **auto-expiry safety valve** (21-day default): `metadata.last_kill_run` older than `kill_list_max_age_days` → kill list ignored entirely.

### 2.3 Gate Logic Summary

#### passes_active_gate (~5939)

Rejection conditions (hard `return False`):
1. **Meta-labeler gate** (M-049): `META_LABEL_GATE_ENFORCE=1` + WOULD_REJECT verdict
2. **Safety halt gate**: `SAFETY_HALT_GATE_ENABLED=1` + safety_status=STOP
3. **FOREX directional gate** (2026-05-17): FOREX LONG with elite<75 or conf<0.75
4. **FOREX symbol gate**: specific symbols (NZDUSD=X, EURJPY=X, USDCHF=X)
5. **DOW gate**: `_passes_dow_gate()` — day-of-week filtering
6. **Empty symbol**: no symbol field
7. **Blocked symbols**: symbol in `BLOCKED_SYMBOLS`
8. **Blocked strategies**: strategy in `BLOCKED_STRATEGIES`
9. **Blocked asset×strategy pairs**: `(strategy, symbol)` in `BLOCKED_STRATEGY_SYMBOL_PAIRS`
10. **Blocked asset×source pairs**: `(asset_class, source_system)` in `BLOCKED_ASSET_SOURCE_PAIRS`
11. **Blocked asset classes**: asset_class in `BLOCKED_ASSET_CLASSES`
12. **Killed strategies**: strategy.lower() in `_KILLED_STRATEGIES_LOWER`
13. **Trust tier 0**: trust_score in `BLOCKED_ACTIVE_TRUST_TIERS`
14. **Non-crypto score floor**: score < 55 for non-crypto (with bypass exceptions)
15. **Stale picks with flat PnL**: old picks with ~0% PnL
16. **Data quality blocks**: delisted/redenomination symbols

#### passes_smart_gate (~7830)

Score calculation (0-100) with component weights:
- Base score (penalty-adjusted): 30 pts
- R:R quality: 15 pts
- Strategy track record: 15 pts
- Trust tier: 12 pts
- Confidence sweet spot: 10 pts
- Technical alignment: 10 pts
- Multi-source consensus: 8 pts

Requires `score >= 55` for non-crypto picks.

#### Shadow/What-If System

**Shadow mode** (`SHADOW_MODE_AUTO_PROMOTE_ENABLED`, default OFF):
- New strategies with ≥10 raw emits in 14 days but 0 closed history
- ONE pick passes as "shadow active" pick
- Sized at 10% of normal (`_SHADOW_SIZE_MULTIPLIER = 0.1`)
- Visible on `/audit` dashboard

**What-if analysis** (line 8660):
```python
# 2026-04-05 what-if: Polymarket direct signals were 2/2 correct (BTC LONG + ETH SHORT)
# while pm_whale BTC SHORT consensus FAILED (BTC drifted +0.30% today). Direct
# Polymarket probability > whale-derived aggregates. Reweighting.
```

---

## 3. SYMBOL UNIVERSES PER ASSET CLASS

### Configuration Location

Symbol universes are **NOT defined in quality_gates.py or dashboard_generator.py**. They are imported from:

| Asset Class | Source File | Import Location |
|-------------|-------------|-----------------|
| FOREX | `alpha_engine.config.FOREX_SYMBOLS` | `quality_gates.py:5687` |
| EQUITY | Hardcoded `_EQUITY_SYMBOLS` (615 symbols) | `dashboard_generator.py:615` |
| BOND | `alpha_engine.config.BOND_SYMBOLS` | `dashboard_generator.py:66` |
| ETF | `alpha_engine.config.ETF_SYMBOLS` | `dashboard_generator.py:67` |

### EQUITY_SYMBOLS (hardcoded, line 615)

```python
_EQUITY_SYMBOLS = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "WMT", "JPM",
    "V", "MA", "UNH", "HD", "PG", "JNJ", "MRK", "LLY", "BAC", "ABBV",
    "PFE", "KO", "PEP", "COST", "TMO", "ABT", "MCD", "ADBE", "CRM", "ACN",
    # ... ~615 symbols total
    "UPS", "NEE", "PM", "TXN", "RTX", "BMY", "COP", "SPGI", "GS", "MS",
}
```

### Asset Class Derivation

**Function:** `_derive_asset_class()` in `dashboard_generator.py`

Derives asset class from symbol using this priority:
1. If `category` or `asset_class` field already set → use it
2. If symbol ends in `USDT`, `USD`, `BTC`, `ETH` → CRYPTO
3. If symbol in `_EQUITY_SYMBOLS` → EQUITY
4. If symbol in `BOND_SYMBOLS` → BOND
5. If symbol in `ETF_SYMBOLS` → ETF
6. If symbol matches `^[A-Z]{6}=X$` pattern → FOREX
7. If symbol contains `=F` or commodity suffix → COMMODITY
8. Otherwise → UNKNOWN

### Known Config Files (not in repo tree)

The following are referenced but not in the analyzed files:
- `alpha_engine/data/core_whitelist.json` — kill list + metadata
- `alpha_engine/config.py` — symbol universes (FOREX, BOND, ETF, COMMODITY)
- `alpha_engine/auto_tuner.py` — `PERMANENTLY_KILLED` auto-generated kills

---

## 4. FILTER LOGGING: WHY PICKS WERE REJECTED

### Filter Log Schema

**Table:** `filter_log` in `audit_trail.db` (SQLite)

**Read by:** `dashboard_generator.py::collect_filter_log()` (line 10396)

```python
def collect_filter_log(limit=50):
    return _safe_sqlite(
        ROOT / "data" / "audit_trail.db",
        "SELECT filter_reason, symbol, direction, source_system, details, timestamp "
        "FROM filter_log ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    )
```

**Schema (inferred from query):**
| Column | Type | Description |
|--------|------|-------------|
| `filter_reason` | TEXT | Human-readable rejection reason |
| `symbol` | TEXT | Symbol that was filtered |
| `direction` | TEXT | LONG/SHORT/BUY/SELL |
| `source_system` | TEXT | Origin system name |
| `details` | TEXT | Detailed rejection context |
| `timestamp` | TEXT | ISO timestamp of filter event |

### What Gets Logged

The `filter_log` table is populated by **individual gate rejections** throughout `quality_gates.py`. Each hard-rejection point logs:
- The specific gate name (e.g., "killed_strategy", "blocked_symbol", "forex_symbol_gate")
- Symbol + direction
- Source system
- Detailed context (e.g., which BLOCKED_* set matched)

### Filter Log Display in Dashboard

From `template.html`:
- **Tab: Filter Rejections** (in the audit interface)
- Shows recent filter events with `filter_reason`, `symbol`, `details`
- Limited to 50 most recent entries

### Gaps in Filter Logging

1. **No structured filter taxonomy** — reasons are human-readable strings, not categorical codes
2. **No pick_id correlation** — filtered picks don't have a persistent pick_id (they're rejected before ID assignment)
3. **Limited retention** — only most recent 50 entries shown (no archive policy)
4. **No score-before/after tracking** — can't trace which penalty contributed how much
5. **SQLite only** — no MySQL mirror for the filter log

---

## 5. WHAT-IF / SIMULATION CAPABILITY

### Current What-If Features

#### 5.1 Score Penalty System (Score-Based Rejection)
Rather than hard-rejecting all picks, the system uses a **score penalty model**:
- Picks start with a base score (0-100)
- Each gate applies score penalties instead of blocking
- Picks with score < threshold get penalized but still appear on dashboard
- Quality floor is configurable

#### 5.2 Shadow Mode
- **Shadow picks**: New strategies bypass normal gates with reduced size (10%)
- **Shadow audit**: `concept_gate_shadow_audit()` tracks concept-family metadata
- Environment-gated: `SHADOW_MODE_AUTO_PROMOTE_ENABLED=0` (default OFF)

#### 5.3 Meta-Label Gate (Shadow Mode)
```python
# META_LABEL_GATE_ENFORCE=0 (default) → shadow only, logs WOULD_REJECT
# META_LABEL_GATE_ENFORCE=1 → actually rejects WOULD_REJECT picks
```

#### 5.4 Polymarket What-If (line 8660)
```python
# 2026-04-05 what-if: Polymarket direct signals were 2/2 correct
# while pm_whale BTC SHORT consensus FAILED
# Reweighting applied to trust tier scores
```

### What-If Gaps

1. **No true counterfactual simulation** — can't replay "what if gate X was disabled?"
2. **No pick-level what-if** — can't ask "would this specific pick pass if..."
3. **No gate sensitivity analysis** — can't measure per-gate impact on portfolio PnL
4. **No A/B testing framework** for gate configurations

---

## 6. DATABASE SCHEMA

### 6.1 Primary Pick Tables (MySQL / MariaDB)

**File:** `audit_trail/pick_feature_store.py`

#### at_pick_features (MySQL)
```sql
CREATE TABLE IF NOT EXISTS `at_pick_features` (
  `pick_id`             VARCHAR(64)  NOT NULL,
  `symbol`              VARCHAR(32)  NOT NULL,
  `strategy`            VARCHAR(128) NOT NULL DEFAULT '',
  `source_system`       VARCHAR(64)  NOT NULL DEFAULT '',
  `asset_class`         VARCHAR(32),
  `direction`           VARCHAR(8),
  `status`              VARCHAR(16)  DEFAULT 'OPEN',
  `pnl_pct`             FLOAT,
  -- ML scores
  `ml_score`            FLOAT,
  `elite_score`         FLOAT,
  `smart_score`         FLOAT,
  `trust_score`         FLOAT,
  `darwin_score_v2`     FLOAT,
  `method_a_score`      FLOAT,
  `ml_composite_score`  FLOAT,
  `wf_verdict`          VARCHAR(16),
  `strat_fwd_wr`        FLOAT,
  `forward_wr`          FLOAT,
  `agreement_count`     SMALLINT,
  `high_conviction`     TINYINT(1)   DEFAULT 0,
  -- Technical features at entry
  `feat_rsi`            FLOAT,
  `feat_volume_ratio`   FLOAT,
  `feat_atr_pct`        FLOAT,
  `feat_vwap_dev`       FLOAT,
  `feat_macd_hist`      FLOAT,
  `feat_btc_corr`       FLOAT,
  `feat_regime`         TINYINT,
  `feat_funding_rate`   FLOAT,
  `feat_cs_momentum`    FLOAT,
  `feat_ob_imbalance`   FLOAT,
  `feat_stoch_k`        FLOAT,
  `feat_cci`            FLOAT,
  `feat_williams_r`     FLOAT,
  `recorded_at`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`pick_id`),
  KEY `idx_apf_sym`    (`symbol`),
  KEY `idx_apf_strat`  (`strategy`),
  KEY `idx_apf_status` (`status`),
  KEY `idx_apf_ml`     (`ml_score`),
  KEY `idx_apf_elite`  (`elite_score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### at_symbol_strategy_stats (MySQL)
```sql
CREATE TABLE IF NOT EXISTS `at_symbol_strategy_stats` (
  `symbol`          VARCHAR(32)  NOT NULL,
  `strategy`        VARCHAR(128) NOT NULL,
  `source_system`   VARCHAR(64)  NOT NULL DEFAULT '',
  `asset_class`     VARCHAR(32),
  `direction`       VARCHAR(8),
  `total_picks`     INT          DEFAULT 0,
  `wins`            INT          DEFAULT 0,
  `losses`          INT          DEFAULT 0,
  `win_rate`        FLOAT        DEFAULT 0.0,
  `avg_pnl_pct`     FLOAT        DEFAULT 0.0,
  `best_pnl`        FLOAT        DEFAULT 0.0,
  `worst_pnl`       FLOAT        DEFAULT 0.0,
  `avg_rr`          FLOAT        DEFAULT 0.0,
  `avg_ml_score`    FLOAT,
  `avg_elite_score` FLOAT,
  `avg_smart_score` FLOAT,
  `avg_rsi`         FLOAT,
  `avg_volume_ratio` FLOAT,
  `last_updated`    DATETIME,
  PRIMARY KEY (`symbol`, `strategy`, `source_system`, `direction`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 6.2 SQLite Audit Database (audit_trail.db)

**Location:** `audit_trail/data/audit_trail.db`

**Tables (from dashboard_generator.py queries):**

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `audit_events` | General audit trail | event_type, pick_id, symbol, payload, origin, timestamp |
| `filter_log` | Pick rejection log | filter_reason, symbol, direction, source_system, details, timestamp |
| `strategy_stats` | Per-strategy forward performance | strategy, source_system, total_picks, wins, losses, win_rate, avg_pnl_pct |
| `bt_backtest_runs` | Backtest results | strategy, total_trades, wins, losses, win_rate, total_return, sharpe |

### 6.3 Other Databases Referenced

| Database | Location | Tables |
|----------|----------|--------|
| `paper_trading.db` | `paper_trading/data/paper_trading.db` | positions, signals |
| `coinglass.db` | `coinglass_strategies/data/coinglass.db` | positions, signals |
| `kimi_competition` | `riseoftheclaw/data/live_competition.json` | algorithms array |
| `pick_feature_store` | `audit_trail/pick_feature_store.py` | symbol_strategy_stats, feature_edge_snapshots |

---

## 7. AUDIT DASHBOARD DISPLAY

### Architecture

```
dashboard_generator.py::generate()
    ↓
Builds JSON payload (~14000+ lines of data collection)
    ↓
Writes to audit_dashboard/data/dashboard_payload.json
    ↓
template.html renders with JavaScript
```

### Dashboard Tabs / Sections

**File:** `audit_dashboard/template.html`

1. **Systems Grid** — per-system active/closed counts, WR, PF
2. **Portfolio Overview** — allocation, PnL, drawdown
3. **Active Picks** — score-sorted pick table with live prices
4. **Closed Picks** — resolved trades with PnL analysis
5. **Strategy Leaderboard** — ranked by forward WR
6. **Consensus Analysis** — cross-system agreement
7. **Volatility Tracking** — per-pick volatility metrics
8. **BtVsFwd** — backtest vs forward comparison
9. **Audit Events** — recent audit trail events
10. **Filter Rejections** — recent filter log entries
11. **Cross-Asset Correlation** — concentration/diversification matrix
12. **Tier-2 Hero Cards** — promoted high-edge strategies
13. **Sidecar Promotion Status** — promotion-gate readiness

### Key Metrics Displayed

```python
# From dashboard_generator.py::generate():
systems = collect_system_stats(active, closed_for_systems, all_closed_including_expired)
portfolios = collect_portfolios()
audit_events = collect_audit_events(50)
filter_events = collect_filter_log(50)
bt_vs_fwd = collect_backtest_vs_forward()
hf_decay_watchlist = _compute_hf_decay_watchlist(bt_vs_fwd)
leaderboard = collect_strategy_leaderboard(active, closed)
consensus = collect_consensus_analysis(active, closed)
volatility = collect_volatility_tracking(active, closed)
cross_asset_correlation = _compute_cross_asset_correlation(closed)
sidecar_promotion_status = _compute_sidecar_promotion_status(closed)
tier2_proven_strategies = _compute_tier2_proven_strategies(systems, closed)
```

### Pick Display Schema (in payload)

Each active pick includes:
- `symbol`, `direction`, `strategy`, `source_system`, `asset_class`
- `entry_price`, `current_price`, `pnl_pct`, `unrealized_pnl`
- `score`, `confidence`, `trust_tier`, `elite_score`, `smart_score`
- `take_profit`, `stop_loss`, `risk_reward`
- `_flag` (non_active_status, no_tradeable_entry, killed_strategy)
- `_penalties` (list of applied score penalties)
- `_entry_drift_pct` (if >15%)

---

## 8. GAPS & RECOMMENDATIONS FOR FULL LIFECYCLE TRACEABILITY

### 8.1 Current State: Partial Traceability

```
[Generation] ✓ Tracked (source_system, timestamp, raw emit count)
    ↓
[Normalization] ✓ Tracked (_normalize_pick creates canonical form)
    ↓
[Gate Decisions] △ Partial (filter_log has reason, but no pick_id)
    ↓
[Score Calculation] ✗ Not traced (penalties applied but not logged per-pick)
    ↓
[Promotion/Rejection] △ Partial (shadow mode tracks concept metadata)
    ↓
[Active Period] ✓ Tracked (live price enrichment, PnL tracking)
    ↓
[Resolution/Close] ✓ Tracked (status → CLOSED, pnl_pct recorded)
    ↓
[Post-Close Analysis] ✓ Tracked (strategy_stats, bt_backtest_runs)
```

### 8.2 Critical Gaps

| Gap | Severity | Description |
|-----|----------|-------------|
| **No pick_id for rejected picks** | HIGH | Filtered picks never get an ID — can't correlate filter→close events |
| **No per-gate attribution** | HIGH | Can't answer "which gate rejected this pick?" for post-hoc analysis |
| **No filter score impact trace** | HIGH | Score penalties are applied but the chain of penalty causes is lost |
| **No structured filter taxonomy** | MEDIUM | filter_reason is free text, not categorical — hard to aggregate |
| **SQLite-only filter log** | MEDIUM | No MySQL replication, risk of data loss |
| **No pick lineage/parentage** | MEDIUM | Can't trace mutation/evolution of strategies |
| **No what-if replay capability** | MEDIUM | Can't simulate "pass if gate X disabled" |
| **Limited retention** | LOW | Only 50 most recent filter events shown |

### 8.3 What Would Be Needed for Full Traceability

#### A. Pre-Assignment Pick IDs
Generate deterministic pick_ids at normalization time (before gates), so rejected picks can be tracked end-to-end:
```python
pick["id"] = f"{symbol}_{strategy}_{timestamp}_{emit_counter}"
```

#### B. Structured Gate Decision Log
Create a new table `pick_gate_decisions`:
```sql
CREATE TABLE pick_gate_decisions (
    decision_id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    pick_id           VARCHAR(64) NOT NULL,
    gate_name         VARCHAR(32) NOT NULL,   -- 'active', 'smart', 'hf', 'pcg5', 'meta_label'
    gate_verdict      VARCHAR(16) NOT NULL,   -- 'PASS', 'REJECT', 'SHADOW', 'PENALTY'
    score_before      FLOAT,
    score_after       FLOAT,
    penalty_applied   FLOAT DEFAULT 0,
    rejection_reason  VARCHAR(64),             -- categorical code
    rejection_detail  TEXT,
    source_system     VARCHAR(64),
    symbol            VARCHAR(32),
    strategy          VARCHAR(128),
    asset_class       VARCHAR(32),
    direction         VARCHAR(8),
    timestamp         DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX (pick_id),
    INDEX (gate_name, gate_verdict),
    INDEX (source_system, timestamp)
);
```

#### C. Pick Lifecycle State Machine
Track all state transitions:
```sql
CREATE TABLE pick_lifecycle_events (
    event_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
    pick_id     VARCHAR(64) NOT NULL,
    from_state  VARCHAR(16),  -- 'EMITTED', 'NORMALIZED', 'GATED', 'ACTIVE', 'SHADOW', 'REJECTED', 'CLOSED'
    to_state    VARCHAR(16) NOT NULL,
    event_type  VARCHAR(32),  -- 'gate_pass', 'gate_reject', 'score_penalty', 'promotion', 'resolution'
    metadata    JSON,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX (pick_id, timestamp)
);
```

#### D. What-If Replay Framework
Add a `replay_gates(pick, gate_config_override)` function that:
1. Takes a historical pick (or hypothetical)
2. Re-runs it through gates with modified parameters
3. Returns differential outcome

#### E. Gate Impact Attribution
Track PnL attribution per gate:
```sql
CREATE TABLE gate_impact_attribution (
    gate_name       VARCHAR(32) NOT NULL,
    picks_passed    INT,
    picks_rejected  INT,
    passed_pnl_sum  FLOAT,
    would_be_pnl_sum FLOAT,  -- simulated if rejected picks had passed
    period_start    DATE,
    period_end      DATE,
    PRIMARY KEY (gate_name, period_start)
);
```

---

## Appendix A: File Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `audit_trail/quality_gates.py` | 1669+ | Main gate/filter system |
| `audit_trail/dashboard_generator.py` | 17405+ | Central dashboard data aggregator |
| `audit_trail/pick_feature_store.py` | 500+ | MySQL schema + SQLite migrations |
| `audit_dashboard/template.html` | 2000+ | Audit dashboard HTML/JS renderer |
| `audit_trail/pick_sanity.py` | — | Pick sanity validation |
| `audit_trail/hf_policy_thresholds.py` | — | HF policy config |
| `audit_trail/forward_degradation_tracker.py` | — | Forward performance tracking |
| `audit_trail/hf_strict_smart_gate.py` | — | HF strict gating |
| `audit_trail/portfolio_gates.py` | — | Portfolio-level gates (PCG5) |
| `audit_trail/pcg5_gates.py` | — | PCG5 shadow evaluation |
| `audit_trail/vix_regime_gate.py` | — | VIX regime-based filtering |
| `audit_trail/kill_gate.py` | — | Kill list evaluation |
| `audit_trail/regime_filter.py` | — | Market regime filtering |
| `audit_trail/meta_label_gate.py` | — | ML-based meta-labeling |
| `audit_trail/concept_scorer.py` | — | Concept-family scoring |
| `audit_trail/hf_gate_telemetry.py` | — | HF gate telemetry logging |
| `audit_trail/transaction_cost_model.py` | — | Cost-adjusted PnL |
| `audit_trail/trade_geometry.py` | — | Trade geometry validation |
| `audit_trail/safety_status.py` | — | Safety halt status |
| `cross_aggregation/timeframe_classifier.py` | — | Trade timeframe classification |
| `cross_aggregation/performance_alerts.py` | — | Performance alert system |

## Appendix B: Key Configuration Files (Runtime Dependencies)

| File | Purpose |
|------|---------|
| `alpha_engine/data/core_whitelist.json` | Kill list + auto-tuner kills + metadata |
| `alpha_engine/config.py` | Symbol universes (FOREX, BOND, ETF, COMMODITY) |
| `alpha_engine/auto_tuner.py` | `PERMANENTLY_KILLED` auto-generated |
| `audit_trail/data/system_concentration.json` | Per-system concentration limits |
| `audit_trail/data/hf_gate_telemetry.json` | HF gate telemetry (200-pick attribution) |
| `audit_dashboard/data/dashboard_payload.json` | Generated dashboard data |

---

*End of Technical Brief*
