# Lookahead Bias Audit — Python Trading Systems

You are a quantitative researcher with Lopez de Prado level expertise.

## Task
Name 3 specific file/function patterns in a Python trading system that most commonly introduce lookahead bias. For each, explain:
1. The exact code pattern that causes the leak
2. Why it leaks future information into past decisions
3. The correct fix (with corrected pseudocode)

Focus on patterns that appear in ML-based scoring systems where:
- A model score (`ml_score`) is computed and used to gate trade entries
- Walk-forward validation is done across 14-day windows
- Confidence scores are normalized from 0-100 scale

## Output format
For each pattern:
- **Pattern name**: (e.g., "Global StandardScaler fitted on full dataset")
- **Code smell**: (1-2 line pseudocode showing the bug)
- **Why it leaks**: (1 sentence)
- **Correct fix**: (corrected pseudocode)
- **Severity**: HIGH / MEDIUM / LOW

Be specific and concise. Do not pad with preamble.
