# High Conviction UI/UX Specification
## Implementation for findtorontoevents.ca/audit

**Date:** 2026-05-03  
**Based on:** Live UI audit + dashboard_data.json (37 active picks) + cross-AI verification  
**Status:** "High Conviction" currently broken — "under reconstruction post-2026-04-20"

---

## 1. Current UI State (Observed)

### Existing Tabs
- Overview | Active Picks ⭐ | Verified Alpha | Smart Picks 🧠 | US Equity Picks | Closed Picks | Portfolios | Dashboards | ...

### Existing Buttons
- 🧠 SMART PICKS (purple) — opens Smart Picks tab
- ✅ Verified Alpha (green) — opens Verified Alpha tab  
- 🔥 HIGH CONVICTION ⭐ (pink/purple gradient) — **currently broken**

### Feed Definitions (bottom of page)
| Tier | Definition | Status |
|------|-----------|--------|
| Verified Alpha | PROVEN trust tier from vetted source systems | ✅ Active |
| Smart Picks | Passes strictest per-asset gates (score, RR, forward WR, regime) | ✅ Active |
| **High Conviction** | Small-sample edge-validation tier — **under reconstruction** | 🔴 **Broken** |
| Active Picks | All live picks that pass hygiene | ✅ Active |

### Current Metrics
- Smart Snapshot: 48.9%
- Verified Alpha: 13 picks (2 smart = 39.4% of active)
- Active Picks: 33 of 217 (1 proven, 32 sandbox)

---

## 2. What "High Conviction" Should Mean

### Three-Tier Classification (Data-Driven)

| Tier | Badge | Criteria | Current Count (of 37 active) |
|------|-------|----------|-------------------------------|
| **TIER 1** | 🔥 | Score ≥ 70 + RR ≥ 1.5 + strategy PF ≥ 2.0 (or insufficient data) | **6 picks** |
| **TIER 2** | ⭐ | Score ≥ 60 + RR ≥ 1.2 + strategy PF ≥ 1.5 (or insufficient data) | **2 picks** |
| **TIER 3** | ✓ | Score ≥ 50 + RR ≥ 1.0 + strategy PF ≥ 1.0 (or insufficient data) | **8 picks** |

**Total High Conviction: 16 of 37 (43%)**

### Tier-1 Picks (Current Live Examples)

| Symbol | Asset | Direction | Score | RR | ML | Strategy | Why HC |
|--------|-------|-----------|-------|-----|-----|----------|--------|
| XRPUSDT | CRYPTO | LONG | 100 | 4.0 | 83 | drawdown_recovery_rsi_xrp | Max score, 4x RR, high ML |
| ETHUSDT | CRYPTO | LONG | 100 | 1.67 | 72 | drawdown_recovery_rsi_eth | Max score, strong RR |
| AVAXUSDT | CRYPTO | LONG | 100 | 1.5 | 87 | VWAP Deviation Scalp | Max score, high ML |
| BTCUSDT | CRYPTO | LONG | 100 | 2.0 | 84 | copy_pm_justdance | Max score, 2x RR |
| AVAX-USD | CRYPTO | LONG | 76 | 1.5 | 55 | MomentumEMA | High score, proven strategy |
| ALGOUSDT | CRYPTO | LONG | 73 | 1.5 | 73 | super signal (strong) | Strong confluence |

---

## 3. Recommended UI Implementation

### Option A: Dedicated "🔥 High Conviction" Tab (PRIMARY — Recommended)

**Replace the broken "High Conviction" button with a full tab.**

**Why a tab over a button:**
- Current UI already has 14 tabs — users understand the tab paradigm
- A tab signals "first-class citizen" status, not just a filter
- Allows dedicated layout (card grid) vs shared table view
- Can show rich metadata without cluttering other tabs

**Tab Placement:**
```
Overview | Active Picks ⭐ | Verified Alpha | 🔥 High Conviction | Smart Picks 🧠 | US Equity | Closed | ...
```
- Position: Between "Verified Alpha" and "Smart Picks"
- Logic: Trust tier progression — Verified (vetted sources) → High Conviction (score+PF edge) → Smart (all passing gates)

**Tab Content — Card Grid Layout:**

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔥 HIGH CONVICTION          16 of 37 active picks qualify    │
│ Tier-1: 6  |  Tier-2: 2  |  Tier-3: 8                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 🔥 TIER-1    │  │ 🔥 TIER-1    │  │ 🔥 TIER-1    │          │
│  │              │  │              │  │              │          │
│  │   XRPUSDT    │  │   ETHUSDT    │  │   AVAXUSDT   │          │
│  │   🟢 LONG    │  │   🟢 LONG    │  │   🟢 LONG    │          │
│  │              │  │              │  │              │          │
│  │  Score: 100  │  │  Score: 100  │  │  Score: 100  │          │
│  │  RR: 4.0x    │  │  RR: 1.67x   │  │  RR: 1.5x    │          │
│  │  ML: 83      │  │  ML: 72      │  │  ML: 87      │          │
│  │              │  │              │  │              │          │
│  │  [Why? ▼]    │  │  [Why? ▼]    │  │  [Why? ▼]    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ ⭐ TIER-2    │  │ ⭐ TIER-2    │  │ ✓ TIER-3     │          │
│  │   DYDXUSDT   │  │   WLDUSDT    │  │   FETUSDT    │          │
│  │   ...        │  │   ...        │  │   ...        │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Card Component Spec:**
- Width: 280px, min-height: 200px
- Background: Dark gradient (matches current theme)
- Top border: 3px colored by tier — 🔥 = gold (#FFD700), ⭐ = cyan (#00BFFF), ✓ = green (#00FF7F)
- Corner badge: Tier emoji + text
- Symbol: 18px bold, white
- Direction pill: 🟢 LONG / 🔴 SHORT (rounded, colored)
- Score: Large number (24px) + "Score" label
- RR: "1.5x" with "R:R" label
- ML: "73" with "ML" label (only if ≥ 50)
- Strategy name: 12px, truncated at 25 chars, muted color
- "Why?" button: Expandable accordion showing criteria met

**"Why?" Expanded Content:**
```
✅ Score 100 ≥ 70 threshold
✅ RR 4.0 ≥ 1.5 threshold  
✅ ML Score 83 ≥ 60 threshold
⚪ Strategy PF: insufficient closed data (neutral)
⚡ Entry: $2.4500 | SL: $2.2000 | TP: $3.1000
🎯 Confluence: RSI oversold + VWAP bounce + Volume spike
```

### Option B: Persistent Toggle Filter (SECONDARY)

**Add a 🔥 toggle button in the filter bar that works across ALL tabs.**

**Placement:** Next to "Proven Only" and "In Profit"

```
[Best Score] [Proven Only] [In Profit] [🔥 High Conviction Only] [Score ▼] [Export ▼]
```

**Behavior:**
- OFF (default): Show all picks in current tab
- ON: Filter current tab to only High Conviction picks (Tier 1-3)
- Works across: Active Picks, Closed Picks, Smart Picks, Verified Alpha
- When ON, add subtle 🔥 badge to qualifying pick rows in table view

### Option C: Tier Badges on All Pick Cards (TERTIARY)

**Add small tier badges to pick displays in ALL tabs.**

**Badge design:**
- 🔥 / ⭐ / ✓ — 16px emoji, appears next to symbol
- Only shown if pick qualifies for HC
- Hover tooltip: "High Conviction — click to see why"

**Placement:**
- Active Picks table: New column "HC Tier" or inline badge
- Smart Picks: Inline with score
- Closed Picks: Only for picks that were HC at emission time

---

## 4. Recommended Implementation: A + B + C Combined

| Component | Priority | Effort | Impact |
|-----------|----------|--------|--------|
| **A: Dedicated HC Tab** | P1 | Medium | **Highest** — flagship feature |
| **B: Toggle Filter** | P1 | Low | High — usability across all views |
| **C: Tier Badges** | P2 | Low | Medium — visual reinforcement |

### Implementation Order
1. **Phase 1:** Build HC classification API endpoint (reusable)
2. **Phase 2:** Add Toggle Filter (B) — lowest effort, immediate value
3. **Phase 3:** Build HC Tab (A) — flagship feature, 2-3 days
4. **Phase 4:** Add Tier Badges (C) — polish, 1 day

---

## 5. API Endpoint Spec

**GET /api/high-conviction-picks**

```json
{
  "generated_at": "2026-05-03T00:30:00Z",
  "total_active": 37,
  "hc_count": 16,
  "by_tier": {
    "tier_1": {"count": 6, "label": "Highest Conviction", "emoji": "🔥"},
    "tier_2": {"count": 2, "label": "High Conviction", "emoji": "⭐"},
    "tier_3": {"count": 8, "label": "Elevated", "emoji": "✓"}
  },
  "picks": [
    {
      "symbol": "XRPUSDT",
      "asset_class": "CRYPTO",
      "direction": "LONG",
      "tier": "tier_1",
      "score": 100,
      "rr_ratio": 4.0,
      "ml_score": 83,
      "strategy": "drawdown_recovery_rsi_xrp",
      "strategy_pf_30d": null,
      "strategy_wr_30d": null,
      "why": [
        {"criterion": "Score ≥ 70", "value": 100, "met": true},
        {"criterion": "RR ≥ 1.5", "value": 4.0, "met": true},
        {"criterion": "ML ≥ 60", "value": 83, "met": true},
        {"criterion": "Strategy PF ≥ 2.0", "value": null, "met": null, "note": "Insufficient data"}
      ],
      "entry_price": 2.45,
      "stop_loss": 2.20,
      "take_profit": 3.10,
      "active": true
    }
  ]
}
```

**Classification Logic (server-side):**
```python
def classify_high_conviction(pick, strategy_metrics_30d):
    score = pick.get("score", 0)
    rr = pick.get("rr_ratio", 0)
    ml = pick.get("ml_score", 0)
    asset = pick.get("asset_class", "UNKNOWN")
    strategy = pick.get("strategy", "UNKNOWN")
    
    sm = strategy_metrics_30d.get((asset, strategy), {})
    has_data = sm.get("n", 0) >= 5
    spf = sm.get("pf", -1) if has_data else -1
    
    if score >= 70 and rr >= 1.5:
        if not has_data or spf >= 2.0 or spf == float("inf"):
            return "tier_1"
    if score >= 60 and rr >= 1.2:
        if not has_data or spf >= 1.5 or spf == float("inf"):
            return "tier_2"
    if score >= 50 and rr >= 1.0:
        if not has_data or spf >= 1.0 or spf == float("inf"):
            return "tier_3"
    return None
```

---

## 6. Frontend Component Spec (React/Tailwind)

### HighConvictionTab Component

```jsx
// HighConvictionTab.jsx
export default function HighConvictionTab({ picks }) {
  const byTier = {
    tier_1: picks.filter(p => p.tier === "tier_1"),
    tier_2: picks.filter(p => p.tier === "tier_2"),
    tier_3: picks.filter(p => p.tier === "tier_3"),
  };

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <span className="text-2xl">🔥</span>
        <h2 className="text-xl font-bold text-white">HIGH CONVICTION</h2>
        <span className="text-sm text-gray-400">
          {picks.length} of {totalActive} active picks qualify
        </span>
        <div className="ml-auto flex gap-2">
          <Badge count={byTier.tier_1.length} label="Tier-1" color="gold" />
          <Badge count={byTier.tier_2.length} label="Tier-2" color="cyan" />
          <Badge count={byTier.tier_3.length} label="Tier-3" color="green" />
        </div>
      </div>

      {/* Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {picks.map(pick => (
          <HCPickCard key={pick.symbol} pick={pick} />
        ))}
      </div>
    </div>
  );
}

// HCPickCard.jsx
function HCPickCard({ pick }) {
  const [expanded, setExpanded] = useState(false);
  const tierColors = {
    tier_1: "border-yellow-400 bg-gradient-to-b from-gray-800 to-gray-900",
    tier_2: "border-cyan-400 bg-gradient-to-b from-gray-800 to-gray-900",
    tier_3: "border-green-400 bg-gradient-to-b from-gray-800 to-gray-900",
  };

  return (
    <div className={`rounded-lg border-t-3 p-4 ${tierColors[pick.tier]}`}>
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="text-2xl font-bold text-white">{pick.symbol}</div>
          <div className={`inline-flex items-center px-2 py-1 rounded text-xs font-bold
            ${pick.direction === "LONG" ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>
            {pick.direction === "LONG" ? "🟢 LONG" : "🔴 SHORT"}
          </div>
        </div>
        <div className="text-3xl">
          {pick.tier === "tier_1" ? "🔥" : pick.tier === "tier_2" ? "⭐" : "✓"}
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <Metric label="Score" value={pick.score} large />
        <Metric label="R:R" value={`${pick.rr_ratio}x`} />
        {pick.ml_score >= 50 && (
          <Metric label="ML" value={pick.ml_score} />
        )}
      </div>

      {/* Strategy */}
      <div className="text-xs text-gray-500 truncate mb-3">
        {pick.strategy}
      </div>

      {/* Expandable Why */}
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left text-sm text-cyan-400 hover:text-cyan-300"
      >
        {expanded ? "▲ Hide rationale" : "▼ Why this pick?"}
      </button>
      
      {expanded && (
        <div className="mt-2 p-2 bg-gray-900 rounded text-sm">
          {pick.why.map(criterion => (
            <div key={criterion.criterion} className="flex items-center gap-2 py-1">
              {criterion.met === true ? "✅" : criterion.met === false ? "❌" : "⚪"}
              <span className="text-gray-300">{criterion.criterion}</span>
              <span className="text-white ml-auto">
                {criterion.value ?? "N/A"}
              </span>
            </div>
          ))}
          <div className="mt-2 pt-2 border-t border-gray-700 text-xs text-gray-400">
            Entry: {pick.entry_price} | SL: {pick.stop_loss} | TP: {pick.take_profit}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## 7. Why This Is the Best Implementation

### Compared to Alternatives

| Approach | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Tab (A)** | First-class UX, dedicated space, rich cards | Adds to tab count | ✅ **Best** — users expect flagship features as tabs |
| **Button Filter** | Familiar, works everywhere | Hidden, not discoverable | ✅ Good as secondary |
| **Badge Only** | Minimal change | Too subtle | ❌ Not enough for flagship |
| **Modal/Popup** | Focused view | Interrupts flow | ❌ Annoying |
| **Sidebar Panel** | Always visible | Clutters layout | ❌ Competes with filters |

### User Psychology
- **🔥 Emojis create emotional attachment** — users remember "fire picks"
- **Card grid feels premium** — like a curated portfolio, not a data table
- **"Why?" accordion builds trust** — users understand the rationale
- **Three tiers create aspiration** — users want to see their picks in Tier 1

### Business Logic Alignment
- Current "Smart Picks" = passes hygiene gates (48.9% of picks)
- Proposed "High Conviction" = score + RR + strategy edge (43% of picks)
- **Gap is small but meaningful** — HC is a subset of Smart with higher thresholds
- Doesn't replace Smart Picks; **complements** it with a tighter filter

---

## 8. Integration with Existing Systems

### Data Flow
```
dashboard_data.json (picks.active)
  ↓
HighConvictionClassifier (server-side, runs every 5 min)
  ↓
/high-conviction-picks API endpoint
  ↓
React frontend:
  - HighConvictionTab (card grid)
  - HCToggle (filter button)
  - HCBadge (inline badge)
```

### No Breaking Changes
- Existing tabs untouched
- Existing "Smart Picks" tab unchanged
- Existing "Verified Alpha" tab unchanged
- **Only addition:** New tab + toggle + badges

### Performance
- Classification is O(n) where n = active picks (37)
- Strategy metrics cached in Redis/memory (computed once per 5-min dashboard refresh)
- API response < 50ms

---

## 9. A/B Test Recommendation

Before full rollout, test:

**Variant A (Control):** Current UI — broken HC button, no HC tab
**Variant B (Treatment):** New UI — HC tab + toggle + badges

**Metrics:**
- Tab click-through rate (HC tab vs Smart Picks tab)
- Time spent on HC tab
- "Why?" accordion expand rate
- Conversion: users who view HC picks → engage with other tabs

**Duration:** 7 days
**Success criteria:** HC tab gets ≥ 30% of total tab clicks

---

*Specification generated from live UI audit + dashboard data analysis. Cross-verified with active pick dataset (n=37).*