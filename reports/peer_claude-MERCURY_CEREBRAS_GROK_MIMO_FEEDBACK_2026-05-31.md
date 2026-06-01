# Peer Feedback Synthesis — Mercury / Cerebras / Grok / MiMo

**Date:** 2026-05-31
**Author:** peer_claude
**Brief:** Session wkab9g07u final wave (7-wave portfolio, harness emission for tomorrow 13:30 UTC)
**Fan-out:** 4 external AIs (all returned valid JSON)

| AI | Provider | Model | Status |
|---|---|---|---|
| Mercury | Inception Labs | mercury-2 | OK |
| Cerebras | Cerebras Cloud | gpt-oss-120b | OK |
| Grok | xAI | grok-3-latest | OK |
| MiMo | Xiaomi (token-plan-sgp) | mimo-v2.5-pro | OK |

Raw responses: `/tmp/feedback_{mercury,cerebras,grok,mimo}.json`

---

## Per-AI Verdict Matrix

| Field | Mercury | Cerebras | Grok | MiMo |
|---|---|---|---|---|
| **zoo_verdict** | mixed | flawed | flawed | mixed |
| **edge_paradox_real** | false | false | false | false |
| **confidence** | medium | medium | medium | medium |

## Consensus (>=3 AIs agree)

### 1. `edge_paradox_real = FALSE` — UNANIMOUS (4/4)
All four AIs converge: the SL-floor-drives-edge / TP-cap-kills-edge finding is **selection bias on resolved trades**, not genuine asymmetric edge. MiMo gives the sharpest diagnosis: **"micro-stop survivorship bias — trades that instantly gap in your favor survive, everything else is stopped out, producing artificially inflated win rates on resolved trades with no causal market edge."** Recommended validator: bootstrap on position-hold-time-adjusted returns before treating SL=-0.05% / PF=17 as actionable.

### 2. `zoo_verdict` — split mixed/flawed (4/4 negative-leaning)
- **flawed (2):** Cerebras, Grok — gates lack execution-cost / slippage modeling; 0/8 pass is structurally diagnostic of overfit / under-validation.
- **mixed (2):** Mercury, MiMo — architecture is sound, validation evidence is not. Mercury: "passes conceptually but fails validation." MiMo: "architecturally rigorous but zero validated edge."
- **No AI rated zoo's framework as `sound`.** Net: framework can be emitted as scaffolding, but **must not be marketed as edge-validated**.

### 3. Biggest risk — TWO distinct risks, both raised by 3+ AIs
- **(3/4)** Sec15 infra bugs + 565 simultaneous BTCUSDT LONG picks corrupt paper-pilot data before n>=500 is ever reached (Mercury, Cerebras, MiMo).
- **(3/4)** Deploying 24 unvalidated strategies with EV CI crossing zero + 0/8 gate pass = false-positive emission risk (Cerebras, Grok, MiMo).

### 4. Do-NOT list — UNANIMOUS overlaps
- Do NOT emit at 13:30 without fixing PR #402 sec15 bugs (Mercury, Cerebras, MiMo).
- Do NOT relax the n>=500 gate (Grok, MiMo).
- Do NOT treat framework emission as edge validation (Mercury, Cerebras, MiMo).
- Do NOT trust the edge-paradox for SL/TP tuning (4/4).

## Conflicts / Divergences

| Issue | Position A | Position B |
|---|---|---|
| Emit or hold? | **Mercury/Cerebras/MiMo:** Fix sec15 + BTCUSDT-565 bug BEFORE 13:30. | **Grok:** Emit only after 30d pilot (longer hold). |
| zoo framework label | **mixed** (Mercury, MiMo): architecture salvageable | **flawed** (Cerebras, Grok): structurally under-validated |
| Statistical correction | Mercury reiterates Bonferroni->Holm/FDR still mis-applied; others don't flag | — |

No AI dissented from the "edge_paradox = bias" finding. **Zero disagreement on the falsity of the paradox.**

---

## Net Recommendation for 13:30 UTC

**HOLD the emission until PR #402 sec15 bugs (BTCUSDT 565-simultaneous-pick dedup/sizing failure) are fixed.** Three of four reviewers identify this as the single most likely to **corrupt paper-pilot data irreversibly** before any gate can evaluate it. If sec15 cannot be fixed pre-emission, ship the harness in **shadow-only mode** (write to a quarantined pilot DB; do not feed into pf_registry or money_ready_verdict) and label clearly as "framework scaffolding, not edge-validated."

Explicit pre-emission checklist (synthesized from all 4 responses):

1. [ ] PR #402 sec15 bugs merged + BTCUSDT 565-pick bug resolved
2. [ ] Confirm Bonferroni->Holm/FDR migration is live (PR #401)
3. [ ] Execution-cost + slippage model present in gate evaluator (PR #405 follow-up)
4. [ ] money_ready_verdict.py extended-gate dry-run shows 0/24 strategies promoted (expected at n=0-5)
5. [ ] Bootstrap re-run on SL=-0.05% strategies with hold-time-adjusted returns to refute or confirm paradox
6. [ ] Harness writes to quarantined paper-pilot table, not production pf_registry, until n>=500 + Holm-FDR-significant
7. [ ] Internal comms make explicit that 13:30 emission is **framework go-live, not edge go-live**

---

## Raw provider artifacts

- `/tmp/feedback_mercury.json`
- `/tmp/feedback_cerebras.json`
- `/tmp/feedback_grok.json`
- `/tmp/feedback_mimo.json`

(Available locally on operator machine; not committed to repo to keep peer-feedback noise out of git history.)
