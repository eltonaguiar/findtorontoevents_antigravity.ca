# Prompt critique

## Summary verdict
NEEDS_REWRITE

## Suggested rewrites
* Original: "Answer each with brevity (target 800 words total)" 
  Proposed fix: "Answer each question concisely, aiming for a total response of 800 words or less, with a focus on clarity and precision."
* Original: "Phase 1 — quality verdict on each shipped item. Pick top 3 strongest + bottom 3 weakest. Justify (1 line each)"
  Proposed fix: "For Phase 1, evaluate the quality of each shipped item and rank them. Identify the top 3 strongest and bottom 3 weakest items, providing a brief justification (approximately 1 sentence each) for each ranking."
* Original: "Phase 2 — re-rank AA-1 through AA-5 + NS-A + NS-D by ROI"
  Proposed fix: "For Phase 2, re-rank the action items (AA-1 through AA-5, NS-A, and NS-D) based on their expected Return on Investment (ROI), calculated as the product of the expected PF lift, probability of success, and effort hours required. Provide a clear and concise ranking with brief explanations."

## Overlooked topics (consider adding)
* A clear definition of the evaluation criteria for the quality verdict in Phase 1
* Specific guidelines for calculating the ROI in Phase 2
* A detailed explanation of the supreme action plan in Phase 3, including potential risks and mitigation strategies
* Consideration of potential biases in the evaluation process and strategies for minimizing them

## Ambiguities flagged
* The term "breach" is not defined in the context of the trading dashboard
* The phrase "COMMODITY edge is real" is ambiguous and requires clarification
* The calculation of ROI in Phase 2 is not clearly defined
* The term "Tier-1 candidate" is not explicitly defined

## Estimated variance reduction
MEDIUM (10-30%)

## Best engine for THIS prompt
ollama_cloud, due to its ability to handle complex, multi-part prompts and provide detailed, well-structured responses.

---

# The prompt to critique

... (rest of the prompt remains the same)

Note: The suggested rewrites aim to improve the clarity and precision of the prompt, while the overlooked topics and ambiguities flagged sections highlight areas that require additional attention to ensure the prompt is well-defined and unambiguous. The estimated variance reduction is medium, as the suggested changes are expected to reduce the variability in responses, but may not completely eliminate it. The recommended engine, ollama_cloud, is chosen for its ability to handle complex prompts and provide detailed responses.