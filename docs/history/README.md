# History Module - Historical Learning System

## 📚 Overview

The **History Module** is the learning and memory system for the Domain Auction Bidding Agent. It enables the agent to:

1. **Remember Past Auctions** - Store complete records of every auction decision and outcome
2. **Learn from Experience** - Analyze what strategies worked and what didn't
3. **Provide Context** - Give the LLM historical insights before making decisions
4. **Adapt Thresholds** - Dynamically adjust bidding limits based on market patterns

---

## 🗂️ Module Structure

```
history/
├── README.md           ← This file (overview)
├── models.py          ← Data models (what we store)
├── models_README.md   ← Detailed explanation of models
├── storage.py         ← Database operations (SQLite)
├── storage_README.md  ← Detailed explanation of storage
├── learning.py       ← Learning algorithms & insights
└── learning_README.md ← Detailed explanation of learning
```

---

## 🎯 Core Concept: Learning Loop

```
┌─────────────────────────────────────────────────────────┐
│                    BEFORE AUCTION                       │
│                                                         │
│  1. Agent receives new auction context                 │
│  2. Learning module queries historical data            │
│  3. Finds similar past auctions                        │
│  4. Calculates strategy performance stats              │
│  5. Generates insights (win rates, price patterns)    │
│  6. Passes insights to LLM for informed decision       │
│                                                         │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                    DURING AUCTION                       │
│                                                         │
│  Agent makes decision using historical context         │
│                                                         │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                    AFTER AUCTION                       │
│                                                         │
│  1. Auction completes (won/lost/abandoned)             │
│  2. Record outcome with all details                    │
│  3. Update strategy performance statistics             │
│  4. Update opponent profiles (if identifiable)        │
│  5. Store for future learning                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 💾 Data Storage Location

**Database File:** `data/auction_history.db` (SQLite)

This is a **local file-based database** that stores:
- All auction outcomes
- Strategy performance metrics
- Opponent profiles (future feature)

**Why SQLite?**
- ✅ No server required - works locally
- ✅ Single file - easy to backup
- ✅ Fast queries for small-medium datasets
- ✅ SQL support for complex queries
- ✅ Can migrate to PostgreSQL later if needed

---

## 🔄 Data Flow

### 1. **Recording Outcomes** (After Auction)

```python
# In hybrid_strategy_selector.py or your main script
from history.storage import AuctionHistoryStorage
from history.models import AuctionOutcome

storage = AuctionHistoryStorage()

# After auction completes
outcome = AuctionOutcome(
    auction_id="example.com_2025-12-05",
    domain="example.com",
    platform="godaddy",
    estimated_value=2500.0,
    final_price=1850.0,
    result="won",
    strategy_used="last_minute_snipe",
    # ... other fields
)

storage.record_outcome(outcome)
```

**What Happens:**
1. Outcome saved to `auction_outcomes` table
2. Strategy performance automatically updated
3. Data available for future queries

---

### 2. **Getting Historical Context** (Before Auction)

```python
# In hybrid_strategy_selector.py
from history.learning import HistoricalLearning
from history.storage import AuctionHistoryStorage

storage = AuctionHistoryStorage()
learning = HistoricalLearning(storage)

# Before making decision
historical_context = learning.get_historical_context(auction_context)

# historical_context contains:
# {
#     "similar_auctions_count": 5,
#     "insights": {
#         "win_rate": 0.65,
#         "avg_final_price_ratio": 0.72,
#         "winning_strategies": {"proxy_max": 3, "last_minute_snipe": 2}
#     },
#     "strategy_performance": {
#         "proxy_max": {"win_rate": 0.70, "total_uses": 20},
#         "last_minute_snipe": {"win_rate": 0.55, "total_uses": 15}
#     },
#     "historically_best_strategy": "proxy_max",
#     "value_tier": "high"
# }
```

**What Happens:**
1. Finds similar past auctions (same platform, similar value)
2. Calculates win rates and price patterns
3. Gets strategy performance stats
4. Identifies best historical strategy
5. Returns insights for LLM to use

---

## 📊 Database Schema

### Table 1: `auction_outcomes`
Stores complete records of every auction.

| Column | Type | Description |
|--------|------|-------------|
| `auction_id` | TEXT | Unique identifier |
| `domain` | TEXT | Domain name |
| `platform` | TEXT | godaddy/namejet/dynadot |
| `timestamp` | TEXT | When auction happened |
| `estimated_value` | REAL | Domain valuation |
| `final_price` | REAL | What it actually sold for |
| `strategy_used` | TEXT | Which strategy we used |
| `result` | TEXT | won/lost/abandoned |
| `profit_margin` | REAL | Profit % if won |
| `raw_data` | TEXT | Complete JSON record |

### Table 2: `strategy_performance`
Aggregated stats per strategy/platform/value_tier.

| Column | Type | Description |
|--------|------|-------------|
| `strategy` | TEXT | Strategy name |
| `platform` | TEXT | Platform name |
| `value_tier` | TEXT | high/medium/low |
| `total_uses` | INTEGER | How many times used |
| `wins` | INTEGER | How many wins |
| `total_profit` | REAL | Cumulative profit |

### Table 3: `opponent_profiles` (Future)
Track recurring bidders across auctions.

---

## 🎓 Learning Capabilities

### 1. **Strategy Performance Tracking**
- Which strategies win most often?
- Which work best on GoDaddy vs NameJet?
- Which work for high-value vs low-value domains?

### 2. **Market Pattern Recognition**
- What % of estimated value do domains typically sell for?
- Are prices trending up or down?
- Is competition increasing?

### 3. **Dynamic Threshold Adjustment**
- If we're losing too much → increase safe_max ratio
- If we're winning easily → decrease safe_max ratio
- Adapt to market conditions automatically

### 4. **Context-Aware Recommendations**
- "Similar auctions had 65% win rate with proxy_max"
- "Domains in this range typically sell for 72% of value"
- "This strategy worked 3/4 times in similar situations"

---

## 🔧 Integration Points

### In `hybrid_strategy_selector.py`:

```python
class HybridStrategySelector:
    def __init__(self, ...):
        # ... existing code ...
        self.history_storage = AuctionHistoryStorage()
        self.learning = HistoricalLearning(self.history_storage)
    
    def select_strategy(self, context):
        # Get historical insights
        historical = self.learning.get_historical_context(context)
        
        # Pass to LLM or use in decision
        # ... rest of logic ...
    
    def record_outcome(self, context, decision, result, final_price):
        # Call this after auction completes
        outcome = AuctionOutcome(...)
        self.history_storage.record_outcome(outcome)
```

---

## 📈 Example: How Learning Improves Decisions

### Without History:
```
LLM: "I'll use last_minute_snipe because it's a high-value domain"
Result: Lost (strategy didn't work well for this context)
```

### With History:
```
Learning: "Similar high-value domains on GoDaddy had 70% win rate 
          with proxy_max, but only 45% with last_minute_snipe"

LLM: "Based on historical data, proxy_max is more successful here. 
      I'll use that instead."
Result: Won (using data-driven strategy)
```

---

## 🚀 Future Enhancements

1. **Opponent Tracking** - Identify recurring bidders and their patterns
2. **Time-Based Learning** - Different strategies for different times/seasons
3. **Category Learning** - Learn patterns by domain category (.com, .io, etc.)
4. **A/B Testing** - Compare strategy variations
5. **Predictive Models** - ML models for price prediction

---

## 📝 Next Steps

1. Read `models_README.md` - Understand data structures
2. Read `storage_README.md` - Understand database operations
3. Read `learning_README.md` - Understand learning algorithms
4. Integrate into `hybrid_strategy_selector.py`
5. Start recording outcomes after each auction

---

## ⚠️ Important Notes

- **Database is created automatically** on first use
- **Data persists** between runs (stored in `data/` folder)
- **No data = No learning** - System works without history, but improves with it
- **Privacy** - All data stored locally, never sent externally





