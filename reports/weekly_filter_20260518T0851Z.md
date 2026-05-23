# Weekly Real-Money Filter — 2026-05-18 08:51 UTC

**Dashboard:** 2026-05-18T06:32:45Z (2.3h stale — numbers reliable, next refresh ~09:00)  
**Evidence:** `alpha_engine/money_ready_verdict.py` + `audit_dashboard/data/pf_registry.json` (32 sources)  
**Walk-forward gate:** `risk_reward` only admitted signal (negative sign) — RR > 1.5 → `_rr_high_flag=True`

---

## MONEY-READY Asset Classes

| Class | Verdict | WR | PF | n (clean) | Status |
|-------|---------|----|----|-----------|--------|
| COMMODITY | **MONEY_READY** | 71.4% | 3.533 | 359 | ✅ Size up |
| CRYPTO | **MONEY_READY** | 70.8% | 2.873 | 475 | ✅ Size up |
| EQUITY | INSUFFICIENT_DATA | 35.5% | 0.718 | 44 | ⏳ MySQL unlock needed for n≥100 |
| ETF | INSUFFICIENT_DATA | — | — | <50 | ⏳ n accumulating |
| FOREX | NOT_READY | 23.2% | 0.349 | 938 | ❌ No edge |
| BOND | INSUFFICIENT_DATA | — | — | <20 | ⏳ Low frequency |
| FUTURES | INSUFFICIENT_DATA | 16.7% | 0.956 | 221 | 🔍 Monitor mode (review 2026-07-18) |

---

## COMMODITY Top Filter

**Strategy:** `cftc_cot_commercial_signal` (CT=F / Cotton Futures — ICE)

| Metric | Value |
|--------|-------|
| n (resolved, clean) | 132 |
| WR | 74% |
| PF | 4.33 |
| Quarter-Kelly per pick | **15.8% of account** |
| USD per pick at $10k | **$1,582** |
| Full Kelly (cap at 25%) | 25% max |

**Filter criteria:**
- `asset_class = COMMODITY`
- `strategy = cftc_cot_commercial_signal`
- `status = OPEN`
- `risk_reward ≤ 1.5` (M-109 gate: RR > 1.5 → `_rr_high_flag = True`, avoid)

**Empirical RR rule** (walk-forward admissible, negative sign):

| RR bucket | Historical WR | Verdict |
|-----------|--------------|---------|
| RR = 1.0 | 53.7% | ✅ Take |
| RR = 1.5 | ~45% | ⚠ Marginal |
| RR = 2.0 | 30.9% | ❌ Avoid |
| RR = 3.5 | 5.7% | ❌ Skip |

---

## CRYPTO Top Filter

**Primary strategy:** `st_fear_greed_contrarian` + `kimi_riseoftheclaw`

| Metric | Value |
|--------|-------|
| n (clean, post ml_enhanced block) | 475 |
| WR | 70.8% |
| PF | 2.873 |
| Quarter-Kelly per pick | **15.2% of account** |
| USD per pick at $10k | **$1,515** |
| Max position (DD-halt guard) | 25% of account |

**Filter criteria:**
- `asset_class = CRYPTO`
- `strategy NOT IN ml_enhanced_* variants` (except B_lightgbm, PF≥2.0)
- `status = OPEN`
- `risk_reward ≤ 1.5` (M-109 gate applies)
- `confidence ≤ 1.0` (percent-as-integer encoded picks excluded)

**Top confirmed CRYPTO strategies (clean, n≥20):**
- `st_fear_greed_contrarian` — WR=74.7%, PF~3.0, n=91 (FORWARD ONLY — needs 10-week forward)
- `kimi_riseoftheclaw` — passthrough source (external WR verified), zero sizing until n≥30 live

---

## Kelly Sizing Reference

| Scenario | Fraction | $10k account | Cap rule |
|----------|---------|-------------|---------|
| COMMODITY single pick | 15.8% | $1,582 | Max 25% per pick |
| CRYPTO single pick | 15.2% | $1,515 | Max 25% per pick |
| Max concurrent positions | — | — | DD-halt: −30% rolling 30d → pause sizing |

**Conservative approach for live capital:** Start with 5–10% per pick while forward WR tracks historical. Ramp to quarter-Kelly once 20+ live picks confirmed at WR≥65%.

---

## Risk Controls

1. **Per-pick max:** 25% of account (Kelly cap)
2. **M-109 RR gate:** `risk_reward > 1.5` → `_rr_high_flag=True` → downsize or avoid
3. **Daily soft-stop:** −2% total PnL triggers review pause
4. **DD halt:** rolling 30d drawdown > 30% → pause all sizing (Hyro overlay)
5. **Confidence filter:** exclude picks with raw confidence > 1.0 (encoding bug)
6. **Strategy concentration:** no single strategy > 40% of active positions

---

## How to Apply

1. Go to [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit)
2. Filter `#f-asset` → **COMMODITY** → look for `cftc_cot_commercial_signal` OPEN picks
3. Filter `#f-asset` → **CRYPTO** → exclude `ml_enhanced_*` (except B_lightgbm)
4. Cross-check `risk_reward` field — skip any pick with RR > 1.5
5. Size per table above (start conservative: 5–10% while live WR validates)

---

## Open Questions for Next Session

- [ ] **EQUITY unlock:** MySQL purge of stale `picks` rows (PA console ~2026-05-24) → n from 44 to 100+ expected
- [ ] **M-109 promote to enforce:** `RR_HIGH_GATE_ENFORCE=1` — ready when? (currently shadow)
- [ ] **COMMODITY CT=F concentration cap:** 84% CT=F still exceeds 85% hard-limit; `COMMODITY_CTF_CAP=1` needed
- [ ] **st_fear_greed_contrarian:** 10-week forward still accumulating — check again 2026-07-01

---

*Source: `alpha_engine/money_ready_verdict.py` + `audit_dashboard/data/pf_registry.json` + `tools/edge_stability_harness.py`*  
*Kelly formula: full_kelly = WR − (1−WR)/PF; position size = account × min(quarter_kelly, 0.25)*
