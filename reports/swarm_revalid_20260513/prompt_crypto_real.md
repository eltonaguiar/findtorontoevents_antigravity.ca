# Re-validate CRYPTO asset-class edge against REAL backtest data

## Context

Live `/audit` CRYPTO class: PF 1.25 / WR 44.6% / n=8067 (sub-T2 PF).

Two Edge candidates measured this session:
- **Edge #10** (CRYPTO UTC death-zone backtest, `tools/backtest_btc_utc_hour_filter.py`): memory claim FALSIFIED. Memory said "22 UTC = 61.2% WR peak". Real backtest: 22 UTC = 42.9% WR. Real death zone is **6 UTC at 23.1% WR / PF 0.06**. Actual filter lift on excluding 6 UTC entries: +1.11pp WR, marginal.
- **Edge #11** (BTC 4h regime filter — not yet backtested this session, but `feedback_long_source_bias.md` says 7 sources are 99-100% LONG-only and reject their LONGs on red BTC 4h)

`ml_crypto_pred` autopsy (`reports/aa1_ml_crypto_pred_autopsy_20260513.md`): LONG WR 12% vs SHORT WR 85.7% on resolved sub-strategy. Direction-asymmetric.

## Question to engines

You are a quant researcher reviewing CRYPTO asset class for hedge-fund-level edge.

**Your job:** propose 3-5 concrete signal/gate changes that lift live CRYPTO PF 1.25 → 1.5+ (TIER-2 floor). Focus on:
1. Direction-aware gating (LONG vs SHORT asymmetry per ml_crypto_pred autopsy)
2. Hour-of-day filter (Edge #10 — real death zone is 6 UTC, not 22 UTC as memory claimed)
3. BTC 4h regime filter (Edge #11 — reject LONG-only-emitter LONGs when BTC 4h red)
4. Per-source volume cap (per_source_volume_cap.py already wired)

Return strict JSON ONLY:

```json
{
  "strategies": [
    {
      "name": "<short_identifier>",
      "thesis": "<1-sentence>",
      "signal_construction": "<exact rule>",
      "universe_or_filter": "<which crypto symbols or pick subset>",
      "expected_pf": <number>,
      "expected_wr_pct": <number>,
      "differentiation_from_existing": "<vs current live gates>",
      "implementation_hours": <integer>,
      "wire_target": "<file in alpha_engine/ or audit_trail/quality_gates.py>",
      "data_source": "<binance / coingecko / glassnode / internal>",
      "fail_mode": "<most likely failure>"
    }
  ],
  "edge10_corrections": ["<concrete hour-filter rule given 6 UTC is the real death zone, not 22 UTC>"],
  "edge11_proposals": ["<BTC 4h regime rule definition (above/below 10MA, vol band, etc.)>"],
  "direction_gates": ["<LONG-only vs SHORT-only gating per source-system>"],
  "killers": ["<existing live CRYPTO emitter to retire>"],
  "tier2_attainability_pct": <0-100>,
  "single_most_important_finding": "<one sentence>"
}
```

## Constraints

- Universe: liquid USDT pairs (BTC/ETH/SOL/BNB/XRP/DOGE/LINK/AVAX/ADA/MATIC)
- Use Binance/CoinGecko free tier; Glassnode noted but not required
- Reject expected_pf below 1.5 (TIER-2 floor)
- Must address the MATIC ghost-rows artifact (660 zero-pnl rows flipping correlation; see `project_confidence_rho_matic_artifact.md`)
- Hour filter must use UTC explicitly
