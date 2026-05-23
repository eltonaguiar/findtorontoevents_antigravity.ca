**1. Prioritization – promotion‑step intervention this week**  
- **Strategy A (luxalgo_confluence)** – meets proven‑floor (n = 205) and Tier‑2 metrics; only blocked by paper‑only & kill‑list flags.  
- **Strategy B** – excellent WR/PF but still below candidate floor (n = 23) and flagged “UNTRUSTED”.  
- **Strategy C** – high WR/PF but tiny sample (n = 22) and blocked by score gate.  

→ **Focus on A** – the only strategy that already satisfies the quantitative thresholds; a single gating change can push it into Tier‑2/‑1.

---

**2. Highest‑leverage 1‑line fixes**  

| Strategy | One‑line fix (code‑level) |
|----------|---------------------------|
| **A** | `remove_from(_PAPER_ONLY_STRATEGIES, "luxalgo_confluence")` **and** delete its entry from `core_whitelist.json` kill‑list. |
| **B** | `candidate_floor = max(candidate_floor, 20)` for EQUITY class (or add a “synthetic‑extend” flag to treat the 23 trades as 30). |
| **C** | `HIGHFWWRABV55_SCOREABOVE50 = 45` (or add a temporary override `score_gate_exempt["atr_percentile_gate"]=True`). |

---

**3. Fragility concerns**  

- **Small‑n risk** – B & C (n < 30) are highly sensitive to a single outlier; statistical confidence is low.  
- **Regime change** – All three are crypto‑heavy; a market‑wide shift (e.g., BTC rally/decline) could swing WR dramatically.  
- **Symbol concentration** – A’s top‑5 symbols (STX, ARB, ADA, WIF) account for ≈ 30 % of wins; a drop in any of them would erode PF quickly.  

---

**4. Confidence / score floor policy**  

- **Keep the 0.55 confidence floor** – it guards against spurious signals in volatile crypto regimes.  
- **Relax the 50‑score floor** **only for strategies that already meet proven‑WR (≥ 50) and have a stable PF** (e.g., A).  
  - Suggested new rule: `if WR≥50 and PF≥1.5 → score floor = 45`.  
  - This preserves rigor while allowing high‑WR, low‑score strategies to surface for review.

---

**5. Symmetric LONG/SHORT & TP/SL balance – edge assessment**  

- **For**: Equal LONG/SHORT performance and a 50/50 TP‑hit vs. SL‑hit split indicate the model captures a *market‑wide* signal rather than a directional bias; the edge is less likely to be a random walk artifact.  
- **Against**: Symmetry can also arise from a *neutral* strategy that merely rides overall volatility; without a clear directional edge, the PF (1.66) is modest and could be explained by chance given the large number of trades.  

→ **Conclusion** – symmetry *supports* the existence of a genuine signal, but the modest PF and reliance on a few symbols mean the edge should still be treated as tentative until further out‑of‑sample validation.