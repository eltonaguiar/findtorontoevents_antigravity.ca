# FOREX Edge Hunt — 2026-06-05

**Goal:** Real-money edge without multi-month forward wait.  
**Sources:** `pf_registry.json` (2026-06-05T13:54Z), `money_ready_verdict.json`, `forex_carry_backtest_20260605.json`, `non_crypto_policy.py`, `quality_gates.py`, tournament JSON.

---

## Verdict: No live edge; two probation sleeves + one backtest shortcut

| Layer | n | WR | PF | Status |
|-------|---:|---:|---:|--------|
| Policy-clean FOREX | 22 | 22.7% | 11.22* | `INSUFFICIENT_DATA`, frozen |
| `multi_asset_scanner` | 11 | **9.1%** | 0.21 | Dominant leak — block |
| AI tournament (closed) | 257 | 57.6% | 0.57 | Not production; avg PnL −0.37% |
| `forex_carry_g10` backtest | 13 | 69.2% | 2.11 | LOCKED; n&lt;30 |

\*PF skewed by one `regime_strong_bear` outlier (+61%); bootstrap CI crosses zero.

`FOREX_HARD_DISABLE=1` default blocks all live emissions.

---

## 1. pf_registry sleeves

**`multi_asset_scanner`:** n=11, 1W/10L, WR 9.1%, PF 0.21 — 50% of class picks, AUDUSD 27% share. Not on `_FOREX_ALLOWED` but still in resolved history.

**`cta_replicator`:** n=6, 0W/6L. **`multi_asset_copytrader`:** n=3, 3W/0L (noise); banned at `("FOREX","multi_asset_copytrader")` — terminal hist USDJPY 3.0% WR, EURJPY 1.9% WR.

**`cta_cross_asset_tsmom` / `forex_carry`:** Zero pf_registry rows. Policy cites prior SHORT sleeve 57.6% WR (USDJPY-heavy) before LONG kill (0/86 WR).

## 2. Carry backtest + allowlist

`forex_carry_backtest_20260605.json`: G10 basket, monthly 2023–2024, PF 2.11, Sharpe 0.87, MDD −3.5%, `production_eligible: false`.

`non_crypto_policy.py` allowlist: **`cta_cross_asset_tsmom`** (SHORT-only) + **`forex_carry`**. Re-enable: extend backtest n≥30 → 30-day paper → `FOREX_HARD_DISABLE=0` per `docs/FOREX_HARD_DISABLE_RATIONALE.md`.

## 3. Copy-trader FOREX

`forex_copy_trader` and `multi_asset_copytrader` blocked for FOREX (`quality_gates.py:2546–2547`). Consensus still reads 14 copy-trader picks / 9 consensus rows — sidecar only, cannot reach Smart Picks.

## 4. AI tournament

454 picks, 257 closed, WR 57.6%, **PF 0.57**, `profitable_gate: false`. Latest file: 189 resolved, 54.5% WR. Best small-n: `kimi_direct` 87.5% (n=8); worst: `deepseek_v3` 12.5% (n=8). Separate DB — do not size from tournament.

## 5. Academic replication (fast validation)

| Factor | Target | Repo hook |
|--------|--------|-----------|
| Carry | Lustig-Verdelhan (2011) | `forex_carry_g10` — extend to 2010–2025 |
| FX momentum | Moskowitz (2012) TSMOM | `cta_cross_asset_tsmom` SHORT-only |
| DXY overlay | Dollar regime | `dxy_trend_filter` probation |

External checks: AQR carry factsheet, QuantConnect carry template, MyFXBook SHORT-JPY forward test vs our slippage model.

---

## 30-day path

1. Keep `FOREX_HARD_DISABLE=1` for legacy emitters.
2. Paper pilot: `forex_carry` + `cta_cross_asset_tsmom` SHORT, session gate, TP 1.5%/SL 1.0%.
3. Extend carry backtest; unlock only if n≥30 and PF&gt;1.5.
4. Tournament theses = research only until audit PF&gt;1.0.

T2 gate: n≥100, WR&gt;50%, PF&gt;1.5. FOREX at n=22 / WR 23% — not close.

*Reproduce: `python3 tools/build_pf_registry.py`; `python3 alpha_engine/money_ready_verdict.py --json`.*
