# EAGLE Quick Wins — Executable PRs
**Model/Provider**: Cursor Composer  
**Date/Time**: 2026-05-27T02:25:00 EST  
**Parent**: `reports/EAGLE-2026-05-27T02-25-00_EST-cursor-composer-strategy-audit.md`

---

## Status Legend
- ✅ Done (in repo)
- 🔧 Done this session
- ⏳ Ready to implement
- 🚫 Blocked (needs approval/data)

---

## P0 — Do First (< 1 hour each)

| PR | Title | Status | Files | Effort |
|---|---|---|---|---|
| QW-07 | Clamp FOREX extreme pnl_pct rows | ⏳ | SQL one-shot | 5 min |
| QW-05 | Add `signal_time` to smart picks feed builder | ⏳ | `dashboard_generator.py` | 15 min |
| QW-01 | Invert CRYPTO confidence in ranker | 🔧 | `alpha_engine/smart_picks_engine.py` | Done — enable with `CONFIDENCE_INVERT_CRYPTO=1` in GHA |
| QW-04 | Fix `summary_picks.json` stale timestamps | ⏳ | `dashboard_generator.py` | 30 min |

### QW-01 Implementation (this session)

```python
# alpha_engine/smart_picks_engine.py
# _effective_confidence_for_ranking() — inverts conf for CRYPTO when:
#   CONFIDENCE_INVERT_CRYPTO=1
# Default OFF — zero production change until operator enables.
```

**Rollout**: Set in `.github/workflows/crypto-smart-picks.yml`:
```yaml
env:
  CONFIDENCE_INVERT_CRYPTO: "1"
```

**Verify**: `python3 tools/score_pnl_calibration.py --asset-class CRYPTO --before-after`

---

## P1 — Edge Recovery (1–2 hours each)

| PR | Title | Status | Files | Expected lift |
|---|---|---|---|---|
| QW-03 | Enable ETF sector rotation emitter | ✅ | `alpha-engine-etf.yml` | PF 2+ when regime aligns |
| QW-09 | FOREX LONG hard block | ✅ | `quality_gates.py` passes_smart_gate | SHORT-only surface |
| QW-02 | Promote pead_equity shadow→probation | 🚫 | `production_scanner.py` | Blocked until 2026-06-14 review gate |
| QW-06 | Wire VIX<22 EQUITY momentum gate | ⏳ | `quality_gates.py`, `vix_regime_gate.py` | WR→75% backtest band |
| QW-08 | Quarantine penny/meme from prod EQUITY | ⏳ | `config.py`, `scanner.py` | PF +0.1–0.3 EQUITY |
| QW-10 | IPO tab honest caveat | ⏳ | `audit_dashboard/template.html` | Removes false advertising |

---

## P2 — Wiring (2–4 hours)

| PR | Title | Files |
|---|---|---|
| QW-11 | `alpha_engine/active_picks_sync.py` | New module + forward_validator hook |
| QW-12 | M-001 BTC UTC hour filter | `score_booster.py` |
| QW-13 | ADV gate in production scanner | `scanner.py`, `quality_gates.py` |
| QW-14 | Seed `audit_roadmap_items` table | `tools/audit_roadmap_seed.py` + SQL migration |
| QW-15 | Range oscillator gate (opt-in) | `alpha_engine/range_oscillator_gate.py` |

---

## Execute Now — Copy/Paste Commands

### Enable confidence invert in local test
```bash
export CONFIDENCE_INVERT_CRYPTO=1
python3 -c "from alpha_engine.smart_picks_engine import _effective_confidence_for_ranking; \
  p={'asset_class':'CRYPTO','confidence':0.9}; \
  print(_effective_confidence_for_ranking(p, 0.9))"  # expect 0.1
```

### Dedup user's 90-day plan path list
```bash
python3 tools/dedup_md_files.py --from-file /tmp/paths.txt
```

### Clamp FOREX pnl (QW-07 — run once on DB)
```sql
UPDATE trading_picks SET pnl_pct = -100
WHERE category = 'FOREX' AND pnl_pct < -100;
```

---

## Incident Dashboard Mapping

Each quick win closes or advances these incidents:

| QW | Closes Incident |
|---|---|
| QW-01 | INC-17 (confidence ranker inversion) |
| QW-04, QW-05 | Display staleness P1s |
| QW-07 | FOREX metric distortion |
| QW-02 | pead_equity shadow stall |
| QW-06 | EQUITY VIX false negatives |
| QW-08 | PENNY/MEME class drag |
| QW-11 | INC-15 (forward coverage 0.09%) |

---

*Cursor Composer — EAGLE quick wins 2026-05-27 EST*
