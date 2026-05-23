# Integration & Testing Plan + Timeline

## Objective
Deploy unified gate framework, audit automation, and strategy health monitoring to achieve **Tier-2 minimum across all asset classes** within 14 days, with a path to Tier-1.

---

## Phase 0: Foundation (Days 0-2, 2026-05-03 to 2026-05-04)

### Deliverables
| PR | What | Tests | Owner |
|----|------|-------|-------|
| PR-A | `config/unified_gates.yaml` | Load test, threshold validation | Kimi |
| PR-C | `tools/run_audit.py` | Dashboard snapshot regression test | Kimi |
| #669 | B2 coverage lane grid (rebased) | 12 unit tests | eltonaguiar |
| #676 | Data quality follow-up (rebased) | Data diff symmetry check | eltonaguiar |

### Testing Plan
1. **Config load test:** `python -c "import yaml; yaml.safe_load(open('config/unified_gates.yaml'))"` → must not error
2. **Threshold validation:** All thresholds must be positive, all asset classes must have T1/T2/T3 targets
3. **Audit script regression:** Run `run_audit.py` against known dashboard snapshot → output must match reference JSON
4. **CI integration:** Add GitHub Actions step: `python tools/run_audit.py --output audit.json` → fail if alerts > 0

### Success Criteria
- [ ] All 4 PRs merged to `main`
- [ ] CI passes with new audit step
- [ ] `config/unified_gates.yaml` loads in production without error

---

## Phase 1: Monitoring (Days 3-7, 2026-05-05 to 2026-05-09)

### Deliverables
| PR | What | Tests | Owner |
|----|------|-------|-------|
| PR-B | `tools/strategy_health_monitor.py` | Daily cron simulation | Kimi |
| PR-D | non_crypto_consensus investigation | FORCE_CLOSED root-cause analysis | Claude |

### Testing Plan
1. **Health monitor daily run:** Simulate 7 days of data → verify alerts generated for strategies below PF 0.8
2. **Volume concentration detection:** Inject mock data with `quan_engine` at 25% volume → verify scaling penalty computed
3. **non_crypto_consensus analysis:** Reproduce FORCE_CLOSED pattern → verify copy-trader-source hypothesis

### Success Criteria
- [ ] Strategy health JSON generated daily at 00:00Z
- [ ] Alert issued if any strategy exceeds 20% volume or drops below PF 0.8 for 3 windows
- [ ] Investigation report completed with actionable recommendation

### Expected Performance Impact
- **FOREX 7d:** JPY pre-#687 picks age out → PF improves from 0.43 toward 0.6-0.8
- **EQUITY 7d:** goldmine_6x picks age out → PF improves from 1.07 toward 1.2-1.4
- **CRYPTO 7d:** Volume caps not yet active (config only) → no immediate change

---

## Phase 2: Enforcement (Days 8-14, 2026-05-10 to 2026-05-16)

### Deliverables
| PR | What | Tests | Owner |
|----|------|-------|-------|
| PR-E | Penny stock / meme coin framework | Mock pick generation | Kimi |
| PR-F | Volume cap enforcement in `quality_gates.py` | Mock data exceeding 15% → reject | Kimi |
| PR-G | Mutation review: `stocks_rsi2_pullback` halve notional | Position size test | Kimi |

### Testing Plan
1. **Volume cap enforcement:** Create mock pick stream with `quan_engine` at 20% of CRYPTO volume → verify excess picks rejected
2. **Mutation review trigger:** Simulate `stocks_rsi2_pullback` at PF 0.9 for 2 windows → verify notional halved in third window
3. **Penny stock gate:** Mock AAPL (not penny) vs mock XYZ at $2.50 (penny) → verify different position limits applied
4. **Meme coin rug-pull detection:** Simulate 3 consecutive SL hits on `meme_sentiment_momentum` → verify auto-disable

### Success Criteria
- [ ] No strategy exceeds 15% of asset-class volume (enforced at gate)
- [ ] `stocks_rsi2_pullback` position sizes reduced by 50% (mutation active)
- [ ] First penny stock / meme coin picks emitted (if data sources ready)

### Expected Performance Impact
- **CRYPTO 7d:** Volume cap active → PF improves from 1.33 toward 1.5+ (Tier-2 threshold)
- **EQUITY 7d:** `stocks_rsi2_pullback` mutation → reduced drag, PF improves toward 1.3+
- **FOREX 7d:** If non_crypto_consensus investigation recommends action → implement by Day 14
- **New:** First penny stock / meme coin picks in portfolio

---

## Phase 3: Optimization (Days 15-30, 2026-05-17 to 2026-06-01)

### Focus
- Iterate on Phase 2 learnings
- Expand data sources (Twitter sentiment for meme coins, options flow for EQUITY)
- Fine-tune per-asset-class thresholds based on 2 weeks of enforcement data
- Target: All asset classes at Tier-2 minimum, at least one at Tier-1

### Expected Performance by Asset Class

| Asset | Current (7d) | Day 14 Target | Day 30 Target |
|-------|-------------|---------------|---------------|
| CRYPTO | PF 1.33, WR 45% | PF 1.5+, WR 50%+ (T2) | PF 2.0+, WR 55%+ (T1) |
| EQUITY | PF 1.07, WR 49% | PF 1.3+, WR 50%+ (approaching T2) | PF 1.5+, WR 52%+ (T2) |
| FOREX | PF 0.43, WR 17% | PF 0.8+, WR 35%+ (approaching T3) | PF 1.2+, WR 45%+ (T3) |
| COMMODITY | PF 1.18, WR 20% | PF 1.2+, WR 35%+ (T3) | PF 1.3+, WR 40%+ (T3) |
| ETF | PF 1.57, WR 63% | PF 2.0+, WR 65%+ (T1) | PF 3.0+, WR 70%+ (T1) |
| BOND | No data | No data | First picks if activated |

### Critical Path Assumptions
1. JPY-cross picks age out as expected (5-7 day window)
2. `quan_engine` volume cap reduces dilution (measurable within 7 days)
3. `non_crypto_consensus` investigation yields actionable fix (not kill)
4. Penny stock / meme coin data sources available (Yahoo Finance, CoinGecko APIs)

---

## Testing Infrastructure

### CI Pipeline (GitHub Actions)
```yaml
name: Quality Audit
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  push:
    branches: [main]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pip install pyyaml requests
      - run: python tools/run_audit.py --dashboard audit_dashboard/data/dashboard_data.json --output audit.json
      - run: python -c "import json; a=json.load(open('audit.json')); assert len(a['alerts'])==0, f'ALERTS: {a[\"alerts\"]}'"
```

### Pre-Commit Hooks
```yaml
repos:
  - repo: local
    hooks:
      - id: run-audit
        name: Run quality audit
        entry: python tools/run_audit.py --output /tmp/precommit_audit.json
        language: system
        pass_filenames: false
```

### Local Dev Loop
```bash
# Quick audit
python tools/run_audit.py

# Full health check
python tools/strategy_health_monitor.py --alert

# Mutation analysis
python tools/mutation_analysis.py --strategy stocks_rsi2_pullback --window 7d
```

---

## Risk & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| JPY picks don't age out as expected | Low | FOREX stays broken | Re-audit at Day 3, escalate if PF < 0.5 |
| `quan_engine` cap breaks other strategies | Medium | Reduced volume overall | Gradual cap (20% → 15% → 10% over 3 weeks) |
| non_crypto_consensus is unfixable | Medium | FOREX stays weak | Convert to paper-trade only, don't block |
| Penny/meme data sources unavailable | Medium | Expansion delayed | Fallback: use existing yfinance + CoinGecko free tier |
| CI audit false positives | Low | Build noise | Tolerance: allow 1 alert per window, fail on 2+ |

---

## Rollback Plan

If any Phase 2 enforcement causes unexpected degradation:
1. **Config toggle:** All new gates have `enabled: true` but can be set to `false` in `config/unified_gates.yaml`
2. **Feature flags:** Volume cap and mutation review behind `VOLUME_CAP_ENABLED` and `MUTATION_REVIEW_ENABLED` env vars
3. **One-command rollback:** `git revert <merge-commit>` for any PR
4. **Shadow mode:** Health monitor can run for 7 days in `warn` mode before enabling enforcement

---

## Success Metrics (14-Day Checklist)

- [ ] CRYPTO 7d: PF ≥ 1.5, WR ≥ 50%
- [ ] EQUITY 7d: PF ≥ 1.3, WR ≥ 50%
- [ ] FOREX 7d: PF ≥ 0.8, WR ≥ 35%
- [ ] ETF 7d: PF ≥ 2.0, WR ≥ 60%
- [ ] 0 blocked strategies in active set
- [ ] 0 JPY-cross LONG in active set
- [ ] ≤ 2 alerts per daily health check
- [ ] CI audit passes on every commit to main

---

*Plan generated 2026-05-03 00:25Z. Based on live-data audit + cross-AI verification + 11-PR merge wave.*
