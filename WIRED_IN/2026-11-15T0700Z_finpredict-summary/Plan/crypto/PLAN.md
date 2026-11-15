# Crypto Plan — BTC sma200 (only wealth-beating candidate)

**Gap:** BTC sma200 beats B&H terminal wealth (1.94 vs 1.67) but fails 0/11 proof-protocol gates. Missing: PF>1.5 w/ bootstrap CI>1.0, Bonferroni across 683 universe, DSR, WFO, Monte Carlo, shuffle control, friction model, forward test.

**Simulation:** `experiments/crypto_sma200_oos_protocol.py` (paper-only):
- Signal sma200 on BTC-USD; daily close, weekly signal shift(1); sma period 180-220.
- Costs: 10bp RT + 0.25% maker-taker Binance.
- Benchmark: BTC B&H (1.672).
- Proof: WFO heatmap, 10k block-bootstrap MC, DSR>0, Bonferroni (~20 configs), shuffle control, pre-registered 90d forward test.

**Deliverables:** proof/wfo_crypto_heatmap.png, proof/monter_crypto_boot.png, proof/shuffle_control_crypto.txt, AUDIT_REPORT.md, STRATEGY_SHORTLIST.md.

**Verdict path:** all gates pass → proven + forward protocol; any fail → document, discard.
