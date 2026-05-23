# openrouter - strategic fork

### **1. ARE THESE MUTUALLY EXCLUSIVE?**  
No, but **parallel execution is lethal for a small team**.  

- **Option 1 (New Input Class)** requires deep vendor evaluation, API integration, and latency testing. It’s a data engineering slog.  
- **Option 2 (Research Sandbox)** is passive but demands strict discipline—no "just one more backtest" without the harness.  
- **Option 3 (Structure Alpha)** is operationally distinct: it needs execution infrastructure (e.g., broker connectivity for market-making) and real-time risk monitoring.  

**Concurrency Rule:**  
- **Run 1 OR 3, with 2 as the default fallback.**  
- If you pick 1, freeze all other research until the new data is fully ingested and tested.  
- If you pick 3, you’re committing to building execution ops—no halfway.  

---

### **2. SEQUENCING — 90-Day Plan**  

#### **Option 1 (New Input Class) — High Risk, High Drag**  
- **Days 1-30:**  
  - Buy ONE paid dataset (e.g., L2 order flow for E-mini futures). No "evaluations"—pick the most liquid instrument you trade.  
  - Build the minimal pipeline to ingest it. No "research" until it’s production-ready.  
- **Days 31-60:**  
  - Run the harness on ONE signal (e.g., book imbalance reversal). If it fails, kill the dataset. No tweaking.  
- **Days 61-90:**  
  - Either: (a) scale to other assets if the edge holds, or (b) admit defeat and revert to Option 2.  

#### **Option 3 (Structure Alpha) — Boring but Higher Base Rate**  
- **Days 1-30:**  
  - Implement ONE structural strategy: **futures calendar spread arbitrage** (e.g., capture roll yield in commodities).  
  - Required: Broker with low commissions, historical roll data, and live execution.  
- **Days 31-60:**  
  - Test live with paper trading. Measure fill slippage vs. backtest.  
- **Days 61-90:**  
  - Either: (a) allocate capital if Sharpe > 1.5 after costs, or (b) kill if spreads are too thin.  

#### **Option 2 (Research Sandbox) — Default if Unsure**  
- **Immediate action:**  
  - Archive all failed signals. No revisiting unless new data arrives.  
  - Set a 6-month timer. If no harness-passing edge emerges by then, disband the effort.  

---

### **3. BASE RATES — Probability of Success in 6-12 Months**  
Ranked:  

1. **Option 3 (Structure Alpha) — 40%**  
   - Why: Market-making and arb have higher base rates because they’re not prediction games. But execution costs kill many small players.  
2. **Option 2 (Research Sandbox) — 10%**  
   - Why: The harness is brutal. If past signals failed, future ones likely will too without new data.  
3. **Option 1 (New Input Class) — 5%**  
   - Why: Most paid data is either (a) garbage, or (b) already arbitraged by faster players.  

---

### **4. STRUCTURE ALPHA — Is It Different?**  
Yes, but only if you **avoid the prediction trap**.  

- **Example Strategy:** Treasury futures basis trading (cash-futures arbitrage).  
  - **Data Needed:** CTD bond prices, repo rates, futures order books.  
  - **Capital Needed:** Enough to hold positions to delivery ($$$).  
  - **Risk:** Funding risk, margin calls.  

**Key Difference:**  
- Directional signals try to predict. Structural strategies try to **get paid for a service** (liquidity, financing, risk transfer).  

---

### **5. THE SINGLE HIGHEST-EV MOVE**  
**Option 3: Implement Treasury futures basis trading (or another simple structural arb).**  

**Why?**  
- Your edge isn’t in prediction—it’s in **being the counterparty to lazy capital**.  
- Acceptance Test: After 60 days of paper trading, net P&L > $0 after conservative cost estimates.  

**If that fails:**  
- Admit this isn’t working. Revert to Option 2 (Research Sandbox) and **stop wasting time**.  

---

### **Final Note: The Hard Truth**  
The harness is telling you something: **your current approach doesn’t work.** Option 1 is a Hail Mary. Option 3 is the only plausible pivot. If you can’t execute it cleanly, **walk away**.  

**"The market is a ruthless examiner. It never forgives hope."** — Your next 90 days decide whether you’re a quant or a gambler.
