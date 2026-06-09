# Edge Rescue Plan — Summary (2026-06-09)

**Goal #1:** Phenomenal, statistically proven edge per asset class on `findtorontoevents.ca/audit` — Tier-2 minimum (PF>1.5, WR>50%, MDD<20, n≥100 clean) before any real-money sizing.

**Current verdict:** **0/9 asset classes pass Tier-2.** Apparent edges collapse under clean cohort + intrabar replay. Do not size up on dashboard headline numbers without re-verification.

---

## Central finding (independently verified)

| Failure mode | Impact |
|--------------|--------|
| Backfill contamination | 68–100% of historical WON/LOST; 77.8% quarantined in `build_pf_registry.py` |
| Resolver-version selection bias | Same CRYPTO June data: PF 0.51 vs 2.15 depending on resolver |
| TIME_EXPIRED epidemic | 56–94% of closes; no intrabar OHLC replay in production resolver |
| Feed-bug artifacts | CADJPY +428%, NZDUSD ±100% — sane-pnl guard now drops these |

### Clean cohort (2026-06-09, all artifact filters)

| Class | n | WR | PF |
|-------|---|-----|-----|
| CRYPTO | 1773 | 46.6% | 1.25 |
| EQUITY | 358 | 32.4% | 1.30 |
| FOREX | 117 | 8.5% | 0.63 |
| COMMODITY | 46 | 50.0% | 1.04 |

**FOREX 14d clean WR = 5.0%** — refutes session claims of 64.2% / PF 2.43.

**Confirmed money-ready survivors: 0.**

---

## Save-the-system plan (ranked)

### P0 — Measurement integrity (do first; no sizing until done)

| Step | Status | Tool / artifact |
|------|--------|-----------------|
| Backfill quarantine in PF registry | ✅ Shipped | `tools/build_pf_registry.py` |
| Sane-PnL guard (feed bugs) | ✅ Shipped | `build_pf_registry.py`, `picks_now_professional.py` |
| EXPIRED-honest WR in Picks Now | ✅ Shipped | `tools/picks_now_professional.py` |
| Intrabar dry-run tool | ✅ Shipped | `tools/reresolve_intrabar.py` |
| Deep OHLCV backfill (180d, top-80) | ✅ Run 2026-06-09 | `tools/refresh_crypto_ohlcv.py --days 180 --top-symbols 80` |
| Full-book intrabar dry-run | ✅ Run 2026-06-09 | `reports/reresolve_intrabar_latest.json` |
| TP/SL calibration (legacy 80%+ expire) | 🟡 Partial | caps wired; legacy picks still dominate |
| OHLCV full universe (312 symbols) | ⬜ Optional | extend backfill beyond top-80 |
| Production intrabar `--apply` | ⛔ **Gated** | operator greenlight + backup first |

**Intrabar dry-run result (15,021 CRYPTO picks):**

- Orig WR **47.1%** → true WR **39.7%**
- **21.9%** TP→SL reclassification
- **1,177** picks still `no_data` (OHLCV gap)

### P1 — Re-baseline & forward proof

1. Re-run clean + intrabar screen after any `--apply` or resolver fix.
2. Paper-pilot any intrabar survivors ≥4 weeks forward (no sizing until forward WR/PF hold).
3. Candidate sleeves for verification (not promoted): `copy_pm_justdance`, `cg_whale_divergence`, `pm_whale_0xa2f1fe` — require feed-bug audit + concentration check.

### P2 — Academic sleeves (after P0)

TSMOM, residual momentum, carry — coded but dormant. Wire only after measurement layer is trustworthy.

### P3 — Governance

- FOREX: kill or mutate (clean WR 8.5%, 14d 5.0%).
- Ban sizing on unverified surfaces (AI Tournament WR, raw bt_backtest_trades, Copilot session claims).
- Mutate-before-kill per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

---

## Refuted claims — do NOT act on

| Claim | Reality |
|-------|---------|
| FOREX 14d 64.2% / PF 2.43 | Clean 14d WR **5.0%** |
| GBPUSD n=114 WR 58.8% | True ~7% |
| stocks_rsi2_pullback PF 2.68 | 14d WR ~30% |
| mega_mutation T1 without intrabar | Disputed; class true WR **39.7%** post-replay |
| zoocode "Forex is winning" | FOREX WR 24%, PF 0.077 (money_ready verdict) |
| AI Tournament WR/PF as trading edge | Display artifact, not edge |

Sources: `reports/OBS_FINDING_JUNE8.MD`, `reports/UPDATED_MONEY_READY_RECOMMENDATION_2026-06-09.md`, `money_ready_verdict.json`.

---

## Operator greenlight required

```bash
# 1. Review dry-run (read-only)
python3 tools/reresolve_intrabar.py

# 2. Optional: extend OHLCV
python3 tools/refresh_crypto_ohlcv.py --execute --days 180 --top-symbols 80

# 3. Production mutation — ONLY after backup review
python3 tools/reresolve_intrabar.py --apply --i-understand-this-mutates-production
```

---

## Documentation & skills updated

| Artifact | Purpose |
|----------|---------|
| `.claude/skills/money-maker-ready/SKILL.md` | Measurement-first rescue protocol |
| `.claude/skills/money-maker-readyv2/SKILL.md` | Layer A/B snapshots + SAVE THE SYSTEM table |
| `updates/2026-06-09-ohlcv-deep-backfill.md` | OHLCV backfill run log |
| `updates/2026-06-09-session-transcript-strategy-audit.md` | Superseded banner (false FOREX claims) |
| `obsidian-notes/asset-classes/*.md` | 2026-06-09 clean-cohort stamps |
| `obsidian-notes/incidents/resolver-intrabar-blocker.md` | OHLCV partial fix + dry-run stats |

---

## Success criteria (exit from rescue mode)

- [ ] Production resolver replays intrabar OHLC on close (or `--apply` re-baseline complete)
- [ ] ≥1 asset class: clean n≥100, intrabar-true WR≥50%, PF≥1.5, MDD<20
- [ ] 4-week forward paper pilot confirms edge (non-degrading WR/PF)
- [ ] Picks Now / audit dashboard show only verified surfaces
- [ ] No P0 incidents open on measurement integrity

---

*Generated 2026-06-09 — session edge-rescue continuation. Reproduce: `python3 tools/reresolve_intrabar.py`, read `audit_dashboard/data/money_ready_verdict.json`.*
