# Hourly Audit — 2026-05-19 10Z

**Audit time:** 2026-05-19T10:09Z  
**Dashboard snapshot:** 2026-05-19T09:17:43.775465Z (FRESH — 09Z cron propagated)  
**Snapshot age:** ~52 min  
**Picks pool:** n=3,500 recent_closed

---

## 1. Dashboard Refresh Status

Snapshot is FRESH (09:17Z). Previous hour (09Z) reported stale 08:28Z data; that data is now superseded.  
Delta from 09Z report is meaningful — numbers below reflect the new 09:17Z snapshot anchored at 10:09Z.

---

## 2. Per-Asset Metrics (24h / 7d / 30d)

| Class | 24h PF | 24h WR | 24h n | 7d PF | 7d WR | 7d n | 30d PF | 30d WR | 30d n |
|-------|--------|--------|-------|-------|-------|------|--------|--------|---------|
| **CRYPTO** | 0.853 | 34.2% | 79 | **0.982** | 37.7% | 491 | 1.297 | 43.3% | 1582 |
| EQUITY | 0.000 | 0.0% | 3 | 0.273 | 15.4% | 13 | 2.146 | 51.8% | 85 |
| FOREX | — | — | 0 | 0.000 | 0.0% | 3 | 6.088 | 34.5% | 29 |
| ETF | 0.000 | 0.0% | 5 | 0.302 | 25.0% | 16 | 1.603 | 60.0% | 45 |
| COMMODITY | — | — | 0 | — | — | 0 | — | — | 0 |
| BOND | — | — | 0 | — | — | 0 | — | — | 0 |
| FUTURES | — | — | 0 | — | — | 0 | — | — | 0 |

### Delta vs documented baselines (CLAUDE.md + issue #686)

| Class | Window | Baseline PF | 10Z PF | Delta | Status |
|-------|--------|-------------|--------|-------|--------|
| CRYPTO | 24h | 3.54 (old) | 0.853 | N/A (stale baseline) | down vs 09Z 1.529 |
| CRYPTO | 7d | 1.33 | **0.982** | **-0.348** | FIRST SUB-1.0 |
| CRYPTO | 30d | 1.33 | 1.297 | -0.033 | stable |
| EQUITY | 7d | 0.87 | 0.273 | worse (n<20) | monitor |
| EQUITY | 30d | 1.41-2.18 | 2.146 | in range | healthy |
| FOREX | 7d | 0.14 pre-#687 | n=3 (dormant) | post-kill | expected |
| FOREX | 30d | 0.97 pre-#687 | 6.088 | +5.12 | post-kill recovery |

### Delta vs 09Z report

| Class | Window | 09Z PF | 10Z PF | Delta |
|-------|--------|--------|--------|-------|
| CRYPTO | 24h | 1.529 | 0.853 | **-0.676** |
| CRYPTO | 7d | 1.081 | 0.982 | **-0.099** |
| CRYPTO | 30d | 1.282 | 1.297 | +0.015 |
| FOREX | 7d | 1.304 | 0.000 (n=3) | post-kill dormancy |
| ETF | 7d | 0.989 | 0.302 | -0.687 (n=16, sub-floor) |

---

## 3. Findings

### FINDING-12 (NEW): CRYPTO 7d PF sub-1.0

- **CRYPTO 7d PF = 0.982** on n=491 — first time below 1.0 in the monitoring period.
- WR 37.7% on 491 trades is statistically significant and well below any tier threshold.
- 24h PF also deteriorated to 0.853 (intraday snapshot shift; n=79 less stable).
- 30d PF 1.297 remains positive — long-run edge intact, suggesting regime/volatility drag rather than structural failure.
- **Action:** Escalate to 3-AI consensus review. Evaluate whether `quan_engine` volume reduction (PR #694 HYPEUSDT block) is sufficient, or whether broader vol-targeting from `reports/deep_dive_crypto_mdd_reduction_2026_04_28.md` should be fast-tracked. Do NOT kill strategies on 7d regression alone.
- Posted to issue #686 comment (2026-05-19T10:09Z).

### FINDING-13 (provisional): ETF 7d PF 0.302

- n=16, below significance floor (n<20). No action per protocol.
- Degraded from 0.989 at 09Z — large shift likely due to anchor-time boundary effect on small sample.
- Monitor to 11Z; if ETF 7d PF remains below 0.5 at n>=20, escalate.

### EQUITY 7d PF 0.273 (ongoing per issue #693)

- n=13, below significance floor. Protocol: monitor only.
- 30d PF 2.146 confirms long-run edge intact.
- `goldmine_6x_consensus` killed in PR #692 — awaiting 7d window to clear.

### FOREX dormancy confirmed (post-kill, expected)

- 7d n=3 — near-zero FOREX output post-#687+#692 kills. Expected outcome.
- 30d PF 6.088 on n=29: legacy profitable picks; not actionable alone.

### Ongoing from prior hours (no change)

| Finding | Strategy | Status |
|---------|----------|--------|
| FINDING-1 (5th hr) | `ensemble` CRYPTO | 7d PF ~0.288 / WR ~20% — awaiting 3-AI consensus |
| FINDING-9 (4th hr, ESCALATE) | `crypto_mtf_ema_slope_alignment_v1` | 7d PF ~0.375 / WR ~22.7% / n=22 — awaiting consensus |
| FINDING-10 (3rd hr) | `luxalgo_confluence` LONG direction | regime-driven; monitor |
| FINDING-11 (2nd hr) | `keltner_compression_expansion_eth_v1` | Axis-4 candidate; monitor |

---

## 4. PR Triage

### Open PRs at 10Z

| PR | Title | CI | Mergeable | Reviews | Action |
|----|-------|-----|-----------|---------|--------|
| #1249 | audit: 09Z hourly report | all green | clean | COMMENTED (greptile only) | **MERGED** |
| #1246 | audit: 08Z hourly report | all green | unknown | COMMENTED (greptile only) | **HOLD** (unknown state) |
| #1247 | feat(ai): model grill sequential | test(3.11) FAILED | — | — | **HOLD — CI red** |

### HOLD set (#660 #658 #681 #661)
Confirmed closed/merged by 09Z audit. No action.

### Rebase check set (#669 #676 #608 #665 #644 #597 #615 #655)
Confirmed closed/merged by 09Z audit. No action.

### Merged this hour
- **#1249** — squash merged (sha: 9306e00e5efa8391f9f7052eadfb5d5b094c92a1)

---

## 5. Mutation Analysis (`python3 tools/mutation_analysis.py --json`)

No new full-pool PF<0.5 + n>=20 kill candidates. No issue #686 post triggered for new kills.

### Candidates awaiting 3-AI consensus (unchanged from 09Z)

| Candidate | n | WR% | Type |
|-----------|---|-----|------|
| `ig_contrarian_sentiment` LONG | 200 | 16.5% | Axis-1 direction block |
| `myfxbook_retail_contrarian` LONG | 124 | 13.7% | Axis-1 direction block |
| `quan_engine_swing` LONG | 104 | 26.0% | Axis-1 direction block |
| `forex_rsi2_mean_reversion` LONG | 117 | 6.8% | Axis-1 direction block |
| `cta_cross_asset_tsmom` LONG | 85 | 29.4% | Axis-1 monitor |
| `rapid_fire` / UUSDT | 34 | 0.0% | Axis-3 symbol block |
| `cta_replicator` / NG=F | 24 | 0.0% | Axis-3 symbol block |

All require 3-AI sign-off before actioning.

---

## 6. Issue Status

| Issue | Status | 10Z Action |
|-------|--------|------------|
| #685 | Open — resolver done, no action | No change |
| #686 | Open — live quality tracking | FINDING-12 posted as comment |
| #693 | Closed 2026-05-13 — EQUITY monitor protocol active | Protocol followed (n<20 — monitor) |

---

## 7. Summary

- **Merged:** #1249
- **New findings:** FINDING-12 (CRYPTO 7d sub-1.0, n=491, posted to #686)
- **Held:** #1246 (mergeable_state=unknown), #1247 (CI red)
- **Mutation analysis:** no new kills triggered
- **Next check (11Z):** verify ETF 7d n, check if CRYPTO 24h/7d recovers, confirm #1246 mergeable_state resolves

---

_Generated by Claude Code | 2026-05-19T10:09Z_
