# kimi - strategic fork

### 1. Are These Mutually Exclusive?

These options are not mutually exclusive but rather represent different strategic directions. However, given the constraints of a small team and modest budget, it is advisable to focus on one at a time to maintain efficiency and avoid diluting efforts.

**Option 1 (New Input Class)** and **Option 3 (Structure Alpha)** are particularly distinct and could potentially be pursued concurrently if the team can effectively segment their efforts. However, **Option 2 (Research-Sandbox)** is more of a pause or a fallback strategy that could be implemented at any time without conflicting with the other two.

### 2. Sequencing

#### 90-Day Plan

**Day 1-30:**
- **Research-Sandbox (Option 2)**: Begin with a paper-only approach to ensure that any new strategies are vetted thoroughly before any capital is at risk. This includes setting up the harness for new candidates and defining clear criteria for what constitutes an admissible edge.

**Day 31-60:**
- **New Input Class (Option 1)**: Concurrently, start acquiring and integrating new data sources. Begin with a pilot program for order-flow microstructure and options-implied signals. This phase will involve data procurement, cleaning, and initial feature engineering.

**Day 61-90:**
- **Structure Alpha (Option 3)**: If the new data shows promise, begin exploring structural alpha strategies. Focus on market-making or funding-rate arbitrage, which are more capital-intensive but offer a clear path to structural advantage.

**Gating Criteria:**
- For **Option 1**, the gating criteria would be the successful integration of new data and the identification of at least one promising signal that passes the initial in-sample tests.
- For **Option 3**, the gating criteria would be the development of a viable structural strategy that can be backtested and shown to have a positive expected value.

**Kill-Criterion:**
- If after 90 days, neither new data nor structural strategies show promise in backtesting, the project should be reassessed, and further spending should be halted.

### 3. Base Rates

Given the constraints and the historical failure of similar efforts, the base rates for each option are low but not zero.

1. **New Input Class (Option 1)**: *Probability: 10-20%* - Acquiring new data is promising but comes with high costs and implementation challenges.
2. **Research-Sandbox (Option 2)**: *Probability: 5-10%* - This is a conservative approach with low risk but also low potential for breakthroughs.
3. **Structure Alpha (Option 3)**: *Probability: 15-25%* - This approach has a higher probability due to the potential for structural advantages but requires significant capital and expertise.

### 4. Structure Alpha

Yes, Structure Alpha is genuinely different from directional signal hunting. It focuses on market inefficiencies that provide a consistent return regardless of market direction. A concrete strategy could be **Statistical Arbitrage**, which involves identifying and exploiting temporary mispricings between correlated securities.

- **Data Requirements**: High-frequency trading data, order book data.
- **Capital Requirements**: Moderate to high, as this strategy may require significant capital to manage risk and capture opportunities.
- **Risk**: High, as it involves leverage and the risk of rapid price movements.

### 5. The Single Highest-EV Move

Given the constraints and the low base rates, the single highest-EV move this quarter would be to **focus on the Research-Sandbox (Option 2)**. This approach allows the team to continue exploring without risking capital and can serve as a foundation for either new data integration or structural strategies.

**Concrete Acceptance Test**: Develop a paper trading model that can consistently demonstrate a positive Sharpe ratio over a variety of market conditions using the existing harness as the admission gate.

**Reasoning**: This approach is the most conservative and aligns with the team's current posture of being paper-only. It allows for continued learning and exploration without the risk of capital loss, which is crucial given the historical challenges and the team's modest resources.
