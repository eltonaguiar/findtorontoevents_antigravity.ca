# Using SubQ for Decision Support and Fact-Checking

SubQ provides decision and long-context models (subq-snap, subq-savant). API keys are stored locally (e.g., in dbpasses.txt or environment). Do not commit keys.

## Recommended Uses
1. **Fact-check strategy claims**  
   Feed a claim (e.g., "Hoffman Inventory Retracement has 60%+ win rate across assets") plus primary sources or search results. Ask SubQ to score the claim as supported / weakly supported / contradicted and list the strongest evidence for and against.

2. **Strategy triage**  
   Give SubQ the rules, the test results, and the promotion gates. Ask for a structured decision: promote to forward test / needs more data / kill, with probability and criteria.

3. **Literature and contest result review**  
   Summarize academic papers or TradingView contest write-ups and extract only the verifiable elements (sample size, costs, OOS period).

## Example Decision Call Pattern (conceptual)
- State the hypothesis and the evidence.
- Define clear criteria for "supported."
- Request a noul or choice decision with confidence.

## Guardrails
- SubQ (or any LLM) is an aid, not an oracle. Cross-check important numbers against primary sources.
- Never treat a high-confidence model response as a substitute for clean empirical testing.
- Prefer SubQ for structuring evidence and spotting logical gaps rather than generating new backtest numbers.

Store keys outside the repository. Reference the local path in agent environments only.
