# Learning Module - Historical Insights and Adaptive Learning

## 📋 Overview

The `learning.py` file contains the **intelligence layer** that uses historical data to improve bidding decisions. It analyzes past auctions, calculates insights, and provides context-aware recommendations to the LLM and decision-making system.

---
 
## 🎯 Purpose

**What it does:**
- Analyzes historical auction data
- Calculates win rates and price patterns
- Identifies best-performing strategies
- Suggests dynamic threshold adjustments
- Provides context for LLM decisions

**Why it matters:**
- Without history: Agent makes decisions in isolation
- With history: Agent learns from past successes/failures
- Result: Better strategy selection over time

---

## 🧠 Core Concept: Learning from Experience

### The Learning Loop

```
Past Auctions → Analysis → Insights → Better Decisions → More Wins → More Data → ...
```

**Example:**
1. **Past:** Used `last_minute_snipe` on 10 high-value GoDaddy auctions, won 4
2. **Analysis:** Win rate = 40% (not great)
3. **Insight:** `proxy_max` had 70% win rate in similar auctions
4. **Decision:** Use `proxy_max` instead
5. **Result:** Win rate improves to 65%

---

## 🔧 Core Methods Explained

### 1. `__init__()` - Initialization

```python
def __init__(self, storage: AuctionHistoryStorage):
    self.storage = storage
```

**What it does:**
- Takes a storage instance (database access)
- Stores it for querying historical data

**Why separate storage?**
- Separation of concerns
- Easy to test (mock storage)
- Can swap storage implementations

---

### 2. `get_historical_context()` - Main Context Generator

**Purpose:** Generate comprehensive historical insights for current auction.

```python
def get_historical_context(self, context: AuctionContext) -> Dict[str, Any]:
    """
    Get relevant historical insights for current auction.
    This data can be passed to the LLM for better decisions.
    """
```

**Step-by-Step Process:**

#### Step 1: Determine Value Tier
```python
if context.estimated_value >= 1000:
    value_tier = "high"
elif context.estimated_value >= 100:
    value_tier = "medium"
else:
    value_tier = "low"
```

**Why value tiers?**
- High-value domains need different strategies
- Aggregating by tier gives better insights
- More statistically significant samples

#### Step 2: Find Similar Past Auctions
```python
value_range = context.estimated_value * 0.3  # ±30% range
similar_auctions = self.storage.get_similar_auctions(
    platform=context.platform,
    value_min=context.estimated_value - value_range,
    value_max=context.estimated_value + value_range,
    limit=10
)
```

**Query Logic:**
- Same platform (GoDaddy, NameJet, etc.)
- Similar value (±30% range)
- Most recent 10 auctions

**Why ±30%?**
- Too narrow (5%) → Not enough data
- Too wide (100%) → Not relevant
- 30% is a good balance

#### Step 3: Calculate Insights from Similar Auctions
```python
insights = self._calculate_insights(similar_auctions)
```

**What insights?**
- Win rate in similar auctions
- Average final price vs estimated value
- Which strategies won most often

#### Step 4: Get Strategy Performance Stats
```python
strategy_stats = {}
for strategy in ["proxy_max", "last_minute_snipe", "incremental_test",
                 "wait_for_closeout", "aggressive_early"]:
    stats = self.storage.get_strategy_performance(
        strategy=strategy,
        platform=context.platform,
        value_tier=value_tier
    )
    if stats["total_uses"] > 0:
        strategy_stats[strategy] = stats
```

**What this does:**
- Queries performance for each strategy
- Filters by platform and value tier
- Only includes strategies with data

**Example Output:**
```python
{
    "proxy_max": {
        "win_rate": 0.70,
        "total_uses": 20,
        "wins": 14
    },
    "last_minute_snipe": {
        "win_rate": 0.55,
        "total_uses": 15,
        "wins": 8
    }
}
```

#### Step 5: Find Best Historical Strategy
```python
best_strategy = self.storage.get_best_strategy_for_context(
    platform=context.platform,
    value_tier=value_tier
)
```

**What this does:**
- Queries database for best win_rate
- Only considers strategies with ≥5 uses (statistical significance)
- Returns strategy name or None

#### Step 6: Return Complete Context
```python
return {
    "similar_auctions_count": len(similar_auctions),
    "insights": insights,
    "strategy_performance": strategy_stats,
    "historically_best_strategy": best_strategy,
    "value_tier": value_tier
}
```

**Complete Example Output:**
```python
{
    "similar_auctions_count": 8,
    "insights": {
        "has_data": True,
        "total_similar": 8,
        "win_rate": 0.625,
        "avg_final_price_ratio": 0.72,
        "price_ratio_insight": "Similar domains typically sold for 72% of estimated value",
        "winning_strategies": {
            "proxy_max": 4,
            "last_minute_snipe": 1 
        }
    },
    "strategy_performance": {
        "proxy_max": {
            "win_rate": 0.70,
            "total_uses": 20,
            "wins": 14
        },
        "last_minute_snipe": {
            "win_rate": 0.55,
            "total_uses": 15,
            "wins": 8
        }
    },
    "historically_best_strategy": "proxy_max",
    "value_tier": "high"
}
```

---

### 3. `_calculate_insights()` - Insight Calculator

**Purpose:** Analyze similar auctions and extract meaningful patterns.

```python
def _calculate_insights(self, auctions: List[Dict]) -> Dict[str, Any]:
    """Calculate insights from similar auctions."""
```

#### Step 1: Handle Empty Data
```python
if not auctions:
    return {"has_data": False}
```

**Why?**
- No data = no insights
- Prevents division by zero
- Clear signal to caller

#### Step 2: Separate Wins and Losses
```python
wins = [a for a in auctions if a.get("result") == "won"]
losses = [a for a in auctions if a.get("result") == "lost"]
```

**What this does:**
- Filters auctions by outcome
- Enables win rate calculation
- Enables separate analysis

#### Step 3: Calculate Basic Stats
```python
insights = {
    "has_data": True,
    "total_similar": len(auctions),
    "win_rate": len(wins) / len(auctions) if auctions else 0,
}
```

**Win Rate Calculation:**
- `wins / total` = win rate
- Example: 5 wins / 8 total = 0.625 (62.5%)

#### Step 4: Calculate Price Patterns
```python
price_ratios = [
    a["final_price"] / a["estimated_value"]
    for a in auctions
    if a.get("final_price") and a.get("estimated_value")
]

if price_ratios:
    insights["avg_final_price_ratio"] = sum(price_ratios) / len(price_ratios)
    insights["price_ratio_insight"] = (
        f"Similar domains typically sold for {insights['avg_final_price_ratio']:.0%} of estimated value"
    )
```

**What this calculates:**
- Final price / Estimated value = Price ratio
- Average across all similar auctions
- Example: 0.72 = domains sell for 72% of estimated value

**Why this matters:**
- If domains typically sell for 60% → Market is soft, be conservative
- If domains typically sell for 80% → Market is hot, need to bid higher

#### Step 5: Identify Winning Strategies
```python
if wins:
    strategy_counts = {}
    for w in wins:
        s = w.get("strategy_used", "unknown")
        strategy_counts[s] = strategy_counts.get(s, 0) + 1
    insights["winning_strategies"] = strategy_counts
```

**What this does:**
- Counts which strategies won
- Example: `{"proxy_max": 4, "last_minute_snipe": 1}`
- Shows which strategies are most successful

**Example Output:**
```python
{
    "has_data": True,
    "total_similar": 8,
    "win_rate": 0.625,
    "avg_final_price_ratio": 0.72,
    "price_ratio_insight": "Similar domains typically sold for 72% of estimated value",
    "winning_strategies": {
        "proxy_max": 4,
        "last_minute_snipe": 1
    }
}
```

---

### 4. `suggest_dynamic_threshold()` - Adaptive Thresholds

**Purpose:** Adjust safe_max ratio based on historical performance.

```python
def suggest_dynamic_threshold(
    self,
    context: AuctionContext,
    base_safe_max_ratio: float = 0.70
) -> float:
    """
    Suggest a dynamic safe_max ratio based on historical data.
    Returns adjusted ratio (e.g., 0.65, 0.70, 0.75).
    """
```

**Base Logic:**
- Default: 70% of estimated value (30% profit margin)
- Adjusts up/down based on market conditions
- Clamps to reasonable range (55% - 80%)

#### Step 1: Get Historical Context
```python
historical = self.get_historical_context(context)
```

#### Step 2: Adjust Based on Price Patterns
```python
ratio = base_safe_max_ratio  # Start at 0.70

if historical["insights"].get("avg_final_price_ratio"):
    avg_ratio = historical["insights"]["avg_final_price_ratio"]
    
    if avg_ratio < 0.60:
        ratio -= 0.05  # Market is soft, be more conservative (0.65)
    elif avg_ratio > 0.75:
        ratio += 0.03  # Market is hot, slightly more aggressive (0.73)
```

**Adjustment Logic:**
- **If domains sell for <60% of value:**
  - Market is soft (low competition)
  - Can be more conservative
  - Lower safe_max to 65%

- **If domains sell for >75% of value:**
  - Market is hot (high competition)
  - Need to bid higher to win
  - Raise safe_max to 73%

#### Step 3: Adjust Based on Win Rate
```python
if historical["insights"].get("win_rate", 0.5) < 0.3:
    ratio += 0.05  # We're losing too much, bid higher
elif historical["insights"].get("win_rate", 0.5) > 0.8:
    ratio -= 0.03  # We're winning easily, can be more conservative
```

**Adjustment Logic:**
- **If win rate <30%:**
  - We're losing too often
  - Need to bid higher to compete
  - Increase safe_max by 5%

- **If win rate >80%:**
  - We're winning too easily
  - Might be overbidding
  - Decrease safe_max by 3%

#### Step 4: Clamp to Safe Range
```python
return max(0.55, min(0.80, ratio))
```

**Why clamp?**
- Prevents extreme values (e.g., 0.90 = too risky)
- Ensures minimum 20% profit margin (0.80 max)
- Ensures maximum 45% profit margin (0.55 min)

**Example Scenarios:**

**Scenario 1: Soft Market, High Win Rate**
```python
avg_ratio = 0.55  # Domains sell for 55% of value
win_rate = 0.85   # We win 85% of the time

# Adjustments:
ratio = 0.70 - 0.05  # Soft market: 0.65
ratio = 0.65 - 0.03  # High win rate: 0.62
return 0.62  # Clamped to 0.62 (more conservative)
```

**Scenario 2: Hot Market, Low Win Rate**
```python
avg_ratio = 0.78  # Domains sell for 78% of value
win_rate = 0.25   # We win only 25% of the time

# Adjustments:
ratio = 0.70 + 0.03  # Hot market: 0.73
ratio = 0.73 + 0.05  # Low win rate: 0.78
return 0.78  # Clamped to 0.78 (more aggressive)
```

---

## 🔄 Complete Usage Flow

### Before Auction: Get Context

```python
from history.learning import HistoricalLearning
from history.storage import AuctionHistoryStorage
from models import AuctionContext

# Initialize
storage = AuctionHistoryStorage()
learning = HistoricalLearning(storage)

# Get context for current auction
context = AuctionContext(
    domain="example.com",
    platform="godaddy",
    estimated_value=2500.0,
    # ... other fields
)

historical_context = learning.get_historical_context(context)
```

**Output:**
```python
{
    "similar_auctions_count": 8,
    "insights": {
        "win_rate": 0.625,
        "avg_final_price_ratio": 0.72,
        "winning_strategies": {"proxy_max": 4}
    },
    "strategy_performance": {
        "proxy_max": {"win_rate": 0.70, "total_uses": 20}
    },
    "historically_best_strategy": "proxy_max",
    "value_tier": "high"
}
```

**Use in LLM Prompt:**
```python
# Add to LLM prompt
prompt = f"""
Historical Context:
- Similar auctions had {historical_context['insights']['win_rate']:.0%} win rate
- Best strategy historically: {historical_context['historically_best_strategy']}
- proxy_max has {historical_context['strategy_performance']['proxy_max']['win_rate']:.0%} win rate
"""
```

### After Auction: Record Outcome

```python
# After auction completes
from history.models import AuctionOutcome

outcome = AuctionOutcome(
    auction_id="example.com_2025-12-05",
    domain="example.com",
    platform="godaddy",
    estimated_value=2500.0,
    final_price=1850.0,
    result="won",
    strategy_used="proxy_max",
    # ... other fields
)

storage.record_outcome(outcome)
```

**What happens:**
- Outcome saved to database
- Strategy performance updated
- Available for future queries

---

## 📊 Example: Learning in Action

### Initial State (No History)
```python
historical_context = learning.get_historical_context(context)
# Returns: {"similar_auctions_count": 0, "insights": {"has_data": False}}
# Agent makes decision without historical context
```

### After 10 Auctions
```python
historical_context = learning.get_historical_context(context)
# Returns:
# {
#     "similar_auctions_count": 8,
#     "insights": {"win_rate": 0.50, "avg_final_price_ratio": 0.68},
#     "historically_best_strategy": "proxy_max"
# }
# Agent uses proxy_max because it has best historical performance
```

### After 50 Auctions
```python
historical_context = learning.get_historical_context(context)
# Returns:
# {
#     "similar_auctions_count": 12,
#     "insights": {"win_rate": 0.65, "avg_final_price_ratio": 0.72},
#     "historically_best_strategy": "proxy_max",
#     "strategy_performance": {
#         "proxy_max": {"win_rate": 0.70, "total_uses": 25}
#     }
# }
# Agent has strong statistical confidence in proxy_max
```

---

## 🎯 Key Design Decisions

### Why ±30% Value Range?
- Too narrow → Not enough data
- Too wide → Not relevant
- 30% balances relevance and sample size

### Why Minimum 5 Samples?
- Statistical significance
- Prevents recommendations from 1-2 lucky wins
- Ensures reliable patterns

### Why Separate Insights and Performance?
- **Insights:** From similar auctions (contextual)
- **Performance:** From all auctions (aggregate)
- Both provide different value

---

## ⚠️ Important Notes

1. **No Data = No Learning**
   - System works without history
   - But improves significantly with data
   - Start recording outcomes immediately

2. **Statistical Significance**
   - Small samples (<5) are unreliable
   - Large samples (>20) are more trustworthy
   - Always check `total_uses` before trusting stats

3. **Context Matters**
   - Same strategy can work differently on different platforms
   - High-value vs low-value domains need different approaches
   - Always filter by platform + value_tier

---

## 🚀 Future Enhancements

1. **Time-Based Learning** - Different strategies for different times/seasons
2. **Opponent-Specific Learning** - Adjust strategy based on opponent profile
3. **Category Learning** - Learn patterns by domain category (.com, .io, etc.)
4. **Predictive Models** - ML models for price prediction
5. **A/B Testing** - Compare strategy variations

---

## 📝 Integration Checklist

- [ ] Initialize `HistoricalLearning` with storage
- [ ] Call `get_historical_context()` before each decision
- [ ] Pass insights to LLM prompt
- [ ] Use `suggest_dynamic_threshold()` for adaptive limits
- [ ] Record outcomes after each auction
- [ ] Monitor learning progress over time





