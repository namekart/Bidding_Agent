# Models Module - Data Structures for Historical Learning

## 📋 Overview

The `models.py` file defines **Pydantic data models** that represent the structure of historical auction data. These models ensure type safety, validation, and consistent data format throughout the learning system.

---

## 🎯 Purpose

**What it does:**
- Defines the shape of data we store (auction outcomes, opponent profiles, strategy stats)
- Validates data before saving to database
- Provides type hints for better code quality
- Ensures consistency across the system

**Why Pydantic?**
- ✅ Automatic validation (catches errors early)
- ✅ Type safety (prevents bugs)
- ✅ Easy serialization (convert to/from JSON)
- ✅ Clear documentation (models are self-documenting)

---

## 📦 Models Explained

### 1. `AuctionOutcome` - Complete Auction Record

**Purpose:** Stores everything about a single auction decision and its outcome.

```python
class AuctionOutcome(BaseModel):
    auction_id: str                    # Unique identifier
    domain: str                       # Domain name
    platform: str                     # godaddy/namejet/dynadot
    timestamp: datetime               # When auction happened
```

#### Context at Decision Time
```python
    estimated_value: float            # Domain valuation ($)
    current_bid_at_decision: float   # Bid when we made decision
    final_price: float                # What it actually sold for
    num_bidders: int                  # How many bidders
    hours_remaining_at_decision: float # Time left when we decided
    bot_detected: bool                # Was bot detected?
```

**Why store this?**
- We need to know the **context** when we made the decision
- Helps find "similar auctions" later
- Enables pattern recognition

#### Agent's Decision
```python
    strategy_used: str                # Which strategy we chose
    recommended_bid: float           # What we recommended
    decision_source: str             # "llm" or "rules_fallback"
    confidence: float                # How confident we were (0-1)
```

**Why store this?**
- Track which strategies we actually used
- Compare LLM vs rule-based performance
- Learn from confidence calibration

#### Outcome
```python
    result: str                      # "won", "lost", "abandoned"
    profit_margin: Optional[float]   # Profit % if won (None if lost)
    opponent_hash: Optional[str]     # Opponent ID if identifiable
```

**Why store this?**
- **Result** tells us if strategy worked
- **Profit margin** measures success quality
- **Opponent hash** enables opponent tracking (future feature)

---

### 2. `OpponentProfile` - Recurring Bidder Profile

**Purpose:** Track patterns of recurring opponents across multiple auctions.

```python
class OpponentProfile(BaseModel):
    opponent_id: str                 # Unique opponent identifier
    first_seen: datetime              # When we first encountered them
    last_seen: datetime               # Most recent encounter
    encounter_count: int = 0          # How many times we've seen them
```

**Why track opponents?**
- Some bidders are bots (fast reactions, predictable)
- Some are aggressive humans (emotional bidding)
- Learning their patterns helps us counter them

#### Behavior Patterns
```python
    is_likely_bot: bool = False       # Bot detection flag
    avg_reaction_time: float = 60.0   # Average time to respond (seconds)
    aggression_scores: List[float]    # History of aggression scores
    platforms: List[str]              # Which platforms they use
```

**How we learn:**
- Track reaction times → identify bots
- Track aggression → predict behavior
- Track platforms → know where they're active

#### Win/Loss Record
```python
    wins: int = 0                     # Times we beat them
    losses: int = 0                   # Times they beat us
```

**Why track this?**
- If we always lose to them → avoid or change strategy
- If we usually win → continue current approach

**Note:** This model is defined but not yet fully implemented in storage. It's prepared for future opponent tracking features.

---

### 3. `StrategyPerformance` - Performance Metrics

**Purpose:** Aggregated statistics showing how well each strategy performs.

```python
class StrategyPerformance(BaseModel):
    strategy: str                     # Strategy name
    platform: str                     # Platform name
    value_tier: str                   # "high", "medium", "low"
```

**Why group by platform + value_tier?**
- `proxy_max` might work great on GoDaddy but poorly on NameJet
- High-value domains need different strategies than low-value
- Context matters!

#### Performance Metrics
```python
    total_uses: int = 0               # How many times we used it
    wins: int = 0                     # How many times it won
    total_profit: float = 0.0         # Cumulative profit from wins
```

**What we calculate:**
```python
    @property
    def win_rate(self) -> float:
        return self.wins / max(1, self.total_uses)
    
    @property
    def avg_profit_per_win(self) -> float:
        return self.total_profit / max(1, self.wins)
```

**Example:**
```python
# Strategy: proxy_max
# Platform: godaddy
# Value tier: high
# total_uses: 20
# wins: 14
# total_profit: 3500.0

# win_rate = 14/20 = 0.70 (70%)
# avg_profit_per_win = 3500/14 = $250 per win
```

---

## 🔄 Data Flow: Model → Database

### Step 1: Create Model Instance
```python
outcome = AuctionOutcome(
    auction_id="example.com_2025-12-05",
    domain="example.com",
    platform="godaddy",
    estimated_value=2500.0,
    # ... other fields
)
```

**Pydantic validates:**
- ✅ All required fields present
- ✅ Types are correct (float is float, not string)
- ✅ Values are reasonable (no negative prices)

### Step 2: Convert to Dict/JSON
```python
outcome_dict = outcome.dict()  # Python dict
outcome_json = outcome.json()  # JSON string
```

### Step 3: Store in Database
```python
storage.record_outcome(outcome)  # storage.py handles conversion
```

**What happens:**
- Model → Dict → SQLite INSERT
- Database stores as columns
- Can reconstruct model from database later

---

## 📊 Example: Complete Data Flow

### Scenario: Auction Completed

```python
# 1. Create outcome model
outcome = AuctionOutcome(
    auction_id="premium.com_2025-12-05T10:30:00",
    domain="premium.com",
    platform="godaddy",
    timestamp=datetime.utcnow(),
    
    # Context when we decided
    estimated_value=2500.0,
    current_bid_at_decision=800.0,
    final_price=1850.0,
    num_bidders=4,
    hours_remaining_at_decision=2.5,
    bot_detected=True,
    
    # Our decision
    strategy_used="last_minute_snipe",
    recommended_bid=1750.0,
    decision_source="llm",
    confidence=0.75,
    
    # Outcome
    result="won",
    profit_margin=0.26,  # (2500-1850)/2500
    opponent_hash=None
)

# 2. Validate (automatic with Pydantic)
# ✅ All fields valid

# 3. Store
storage.record_outcome(outcome)

# 4. Later: Query similar auctions
similar = storage.get_similar_auctions(
    platform="godaddy",
    value_min=2000.0,
    value_max=3000.0
)
# Returns list of AuctionOutcome dicts
```

---

## 🎯 Key Design Decisions

### Why Optional Fields?
```python
profit_margin: Optional[float] = None
opponent_hash: Optional[str] = None
```

**Reason:**
- `profit_margin` only exists if we won
- `opponent_hash` only exists if we can identify opponent
- Optional prevents errors when data isn't available

### Why Store `raw_data` in Database?
```python
# In storage.py, we store:
raw_data TEXT  # Complete JSON of the outcome
```

**Reason:**
- Easy to reconstruct full model later
- Can add new fields without migration
- Backup/restore is simple

### Why Separate Models?
- **AuctionOutcome** = Individual records
- **StrategyPerformance** = Aggregated stats
- **OpponentProfile** = Cross-auction patterns

**Reason:**
- Different query patterns
- Different update frequencies
- Different use cases

---

## 🔍 Validation Rules

Pydantic automatically validates:

1. **Type Checking**
   ```python
   estimated_value: float  # Must be float, not string
   num_bidders: int        # Must be int, not float
   ```

2. **Required Fields**
   ```python
   domain: str  # Must be provided (no default)
   ```

3. **Default Values**
   ```python
   encounter_count: int = 0  # Defaults to 0 if not provided
   ```

4. **Optional Fields**
   ```python
   profit_margin: Optional[float] = None  # Can be None
   ```

---

## 📝 Usage Examples

### Creating an Outcome
```python
from history.models import AuctionOutcome
from datetime import datetime

outcome = AuctionOutcome(
    auction_id="test.com_2025-12-05",
    domain="test.com",
    platform="godaddy",
    timestamp=datetime.utcnow(),
    estimated_value=1000.0,
    current_bid_at_decision=500.0,
    final_price=750.0,
    num_bidders=2,
    hours_remaining_at_decision=1.5,
    bot_detected=False,
    strategy_used="proxy_max",
    recommended_bid=700.0,
    decision_source="llm",
    confidence=0.80,
    result="won",
    profit_margin=0.25  # 25% profit
)
```

### Accessing Properties
```python
# Direct access
print(outcome.domain)  # "test.com"
print(outcome.profit_margin)  # 0.25

# Convert to dict
outcome_dict = outcome.dict()

# Convert to JSON
outcome_json = outcome.json()
```

### Strategy Performance Properties
```python
from history.models import StrategyPerformance

perf = StrategyPerformance(
    strategy="proxy_max",
    platform="godaddy",
    value_tier="high",
    total_uses=20,
    wins=14,
    total_profit=3500.0
)

print(perf.win_rate)  # 0.70 (property calculates automatically)
print(perf.avg_profit_per_win)  # 250.0
```

---

## 🚀 Integration with Other Modules

### Used By:
- **`storage.py`** - Converts models to database rows
- **`learning.py`** - Uses models to structure insights
- **`hybrid_strategy_selector.py`** - Creates outcomes after auctions

### Data Flow:
```
Auction Completes
    ↓
Create AuctionOutcome model
    ↓
storage.record_outcome(outcome)
    ↓
Stored in SQLite database
    ↓
learning.get_historical_context()
    ↓
Queries database, returns insights
    ↓
Used in next auction decision
```

---

## ⚠️ Important Notes

1. **All timestamps use UTC** - Prevents timezone issues
2. **Floats for money** - In production, consider Decimal for precision
3. **Optional fields** - Always check if None before using
4. **Validation happens automatically** - Pydantic catches errors early

---

## 🔮 Future Enhancements

1. **Add more fields** as we learn what's useful
2. **Add validation rules** (e.g., profit_margin must be 0-1)
3. **Add computed fields** (e.g., ROI, efficiency metrics)
4. **Add relationships** (e.g., link outcomes to opponents)





