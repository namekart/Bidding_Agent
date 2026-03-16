# Storage Module - Database Operations for Historical Data

## 📋 Overview

The `storage.py` file handles **all database operations** for storing and retrieving historical auction data. It uses **SQLite** as the database engine and provides a clean Python interface for saving outcomes, querying similar auctions, and tracking strategy performance.

---

## 🎯 Purpose

**What it does:**
- Creates and manages SQLite database
- Saves auction outcomes to database
- Queries historical data for learning
- Tracks strategy performance metrics
- Provides data for decision-making

**Why SQLite?**
- ✅ **No server required** - Single file database
- ✅ **Fast for small-medium datasets** - Perfect for learning phase
- ✅ **Easy to backup** - Just copy the `.db` file
- ✅ **SQL support** - Powerful querying capabilities
- ✅ **Can migrate later** - Easy to move to PostgreSQL if needed

---

## 🗄️ Database Structure

### Database File Location
```
data/
└── auction_history.db  ← SQLite database file (created automatically)
```

**First Run:**
- Database file doesn't exist
- `_init_database()` creates it
- Tables are created automatically

---

## 📊 Database Tables

### Table 1: `auction_outcomes`

**Purpose:** Stores complete records of every auction decision and outcome.

**Schema:**
```sql
CREATE TABLE auction_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_id TEXT UNIQUE,              -- Unique identifier
    domain TEXT,                          -- Domain name
    platform TEXT,                        -- godaddy/namejet/dynadot
    timestamp TEXT,                       -- ISO format datetime
    estimated_value REAL,                 -- Domain valuation
    current_bid_at_decision REAL,        -- Bid when decision made
    final_price REAL,                     -- Actual selling price
    num_bidders INTEGER,                  -- Number of bidders
    hours_remaining REAL,                 -- Time left at decision
    bot_detected INTEGER,                 -- 0 or 1 (boolean)
    strategy_used TEXT,                   -- Strategy name
    recommended_bid REAL,                 -- What we recommended
    decision_source TEXT,                 -- "llm" or "rules_fallback"
    confidence REAL,                      -- Confidence score (0-1)
    result TEXT,                          -- "won", "lost", "abandoned"
    profit_margin REAL,                   -- Profit % if won
    opponent_hash TEXT,                   -- Opponent identifier (future)
    raw_data TEXT                         -- Complete JSON backup
)
```

**Key Features:**
- `auction_id` is UNIQUE - Prevents duplicates
- `raw_data` stores full JSON - Easy reconstruction
- All timestamps as TEXT (ISO format) - SQLite datetime handling

---

### Table 2: `strategy_performance`

**Purpose:** Aggregated statistics showing strategy performance by context.

**Schema:**
```sql
CREATE TABLE strategy_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy TEXT,                        -- Strategy name
    platform TEXT,                        -- Platform name
    value_tier TEXT,                      -- "high", "medium", "low"
    total_uses INTEGER,                   -- How many times used
    wins INTEGER,                         -- How many wins
    total_profit REAL,                    -- Cumulative profit
    UNIQUE(strategy, platform, value_tier) -- One row per combination
)
```

**Why UNIQUE constraint?**
- One row per strategy+platform+value_tier combination
- Prevents duplicate stats
- Easy to UPDATE existing stats

**Example Rows:**
```
strategy        | platform  | value_tier | total_uses | wins | total_profit
----------------|-----------|------------|------------|------|-------------
proxy_max       | godaddy   | high       | 20         | 14   | 3500.0
last_minute_snipe | godaddy | high       | 15         | 8    | 1200.0
proxy_max       | namejet   | medium     | 12         | 9    | 800.0
```

---

### Table 3: `opponent_profiles` (Prepared for Future)

**Purpose:** Track recurring bidders across multiple auctions.

**Schema:**
```sql
CREATE TABLE opponent_profiles (
    opponent_id TEXT PRIMARY KEY,
    first_seen TEXT,
    last_seen TEXT,
    encounter_count INTEGER,
    is_likely_bot INTEGER,
    avg_reaction_time REAL,
    aggression_scores TEXT,              -- JSON array
    platforms TEXT,                       -- JSON array
    wins INTEGER,
    losses INTEGER
)
```

**Note:** This table is created but not yet fully used. Prepared for future opponent tracking features.

---

## 🔧 Core Methods Explained

### 1. `__init__()` - Initialization

```python
def __init__(self, db_path: str = "data/auction_history.db"):
    self.db_path = Path(db_path)
    self.db_path.parent.mkdir(parents=True, exist_ok=True)  # Create data/ folder
    self._init_database()  # Create tables
```

**What happens:**
1. Sets database file path
2. Creates `data/` folder if it doesn't exist
3. Calls `_init_database()` to create tables

**First Run:**
- Creates `data/` directory
- Creates `auction_history.db` file
- Creates all three tables

---

### 2. `_init_database()` - Table Creation

```python
def _init_database(self):
    """Create tables if they don't exist."""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    # Create auction_outcomes table
    cursor.execute("""CREATE TABLE IF NOT EXISTS auction_outcomes (...)""")
    
    # Create opponent_profiles table
    cursor.execute("""CREATE TABLE IF NOT EXISTS opponent_profiles (...)""")
    
    # Create strategy_performance table
    cursor.execute("""CREATE TABLE IF NOT EXISTS strategy_performance (...)""")
    
    conn.commit()
    conn.close()
```

**Key Points:**
- `IF NOT EXISTS` - Safe to call multiple times
- Creates all tables in one go
- Commits and closes connection

**SQL Query Breakdown:**
```sql
CREATE TABLE IF NOT EXISTS auction_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Auto-incrementing ID
    auction_id TEXT UNIQUE,                -- Must be unique
    domain TEXT,                           -- Domain name
    -- ... other columns
)
```

---

### 3. `record_outcome()` - Save Auction Result

**Purpose:** Save a completed auction outcome to the database.

```python
def record_outcome(self, outcome: AuctionOutcome):
    """Save an auction outcome."""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO auction_outcomes
        (auction_id, domain, platform, ...)
        VALUES (?, ?, ?, ...)
    """, (outcome.auction_id, outcome.domain, ...))
    
    conn.commit()
    conn.close()
    
    # Update strategy performance
    self._update_strategy_performance(outcome)
```

**What happens:**
1. Opens database connection
2. Inserts outcome record (or replaces if `auction_id` exists)
3. Commits transaction
4. Closes connection
5. Updates strategy performance stats

**SQL Query Explained:**
```sql
INSERT OR REPLACE INTO auction_outcomes
```
- `INSERT OR REPLACE` - If `auction_id` exists, update it; otherwise insert
- Prevents duplicate records
- Useful for re-running same auction

**Parameter Binding:**
```python
VALUES (?, ?, ?, ...)  -- Placeholders
(outcome.auction_id, outcome.domain, ...)  -- Actual values
```
- **Why `?` placeholders?** - Prevents SQL injection
- Safe way to insert data

---

### 4. `_update_strategy_performance()` - Update Stats

**Purpose:** Automatically update strategy performance metrics when outcome is recorded.

```python
def _update_strategy_performance(self, outcome: AuctionOutcome):
    # Determine value tier
    if outcome.estimated_value >= 1000:
        value_tier = "high"
    elif outcome.estimated_value >= 100:
        value_tier = "medium"
    else:
        value_tier = "low"
```

**Value Tier Logic:**
- High: ≥ $1000
- Medium: $100 - $999
- Low: < $100

**Query Existing Stats:**
```python
cursor.execute("""
    SELECT total_uses, wins, total_profit 
    FROM strategy_performance
    WHERE strategy = ? AND platform = ? AND value_tier = ?
""", (outcome.strategy_used, outcome.platform, value_tier))

row = cursor.fetchone()
if row:
    total_uses, wins, total_profit = row  # Existing stats
else:
    total_uses, wins, total_profit = 0, 0, 0.0  # New entry
```

**Update Stats:**
```python
total_uses += 1  # Increment usage count

if outcome.result == "won":
    wins += 1
    if outcome.profit_margin:
        total_profit += outcome.profit_margin * outcome.final_price

cursor.execute("""
    INSERT OR REPLACE INTO strategy_performance
    (strategy, platform, value_tier, total_uses, wins, total_profit)
    VALUES (?, ?, ?, ?, ?, ?)
""", (outcome.strategy_used, outcome.platform, value_tier, 
      total_uses, wins, total_profit))
```

**What this does:**
- Increments `total_uses` for every outcome
- Increments `wins` only if result is "won"
- Adds profit to `total_profit` if we won
- Updates or creates the performance row

---

### 5. `get_similar_auctions()` - Find Similar Past Auctions

**Purpose:** Find past auctions similar to current context for learning.

```python
def get_similar_auctions(
    self,
    platform: str,
    value_min: float,
    value_max: float,
    limit: int = 10
) -> List[Dict[str, Any]]:
```

**SQL Query:**
```sql
SELECT raw_data FROM auction_outcomes
WHERE platform = ?
AND estimated_value BETWEEN ? AND ?
ORDER BY timestamp DESC
LIMIT ?
```

**Query Breakdown:**
- `WHERE platform = ?` - Same platform (GoDaddy, NameJet, etc.)
- `AND estimated_value BETWEEN ? AND ?` - Similar value range
- `ORDER BY timestamp DESC` - Most recent first
- `LIMIT ?` - Return top N results

**Example Usage:**
```python
# Find auctions similar to $2500 domain on GoDaddy
similar = storage.get_similar_auctions(
    platform="godaddy",
    value_min=2000.0,  # 2500 - 500 (20% range)
    value_max=3000.0,  # 2500 + 500
    limit=10
)

# Returns list of dicts with full auction data
for auction in similar:
    print(auction["domain"])
    print(auction["strategy_used"])
    print(auction["result"])
```

**Why `raw_data`?**
- Stores complete JSON of the outcome
- Easy to reconstruct full model
- Contains all fields, even if schema changes

---

### 6. `get_strategy_performance()` - Get Strategy Stats

**Purpose:** Get performance metrics for a specific strategy.

```python
def get_strategy_performance(
    self,
    strategy: str,
    platform: str = None,
    value_tier: str = None
) -> Dict[str, Any]:
```

**Dynamic Query Building:**
```python
query = "SELECT * FROM strategy_performance WHERE strategy = ?"
params = [strategy]

if platform:
    query += " AND platform = ?"
    params.append(platform)

if value_tier:
    query += " AND value_tier = ?"
    params.append(value_tier)
```

**Why Dynamic?**
- Can query by strategy only
- Can query by strategy + platform
- Can query by strategy + platform + value_tier
- Flexible filtering

**Aggregation:**
```python
# If multiple rows match (e.g., different value_tiers)
total_uses = sum(r[4] for r in rows)  # Sum all uses
wins = sum(r[5] for r in rows)         # Sum all wins
total_profit = sum(r[6] for r in rows) # Sum all profit
```

**Returns:**
```python
{
    "strategy": "proxy_max",
    "total_uses": 32,
    "wins": 22,
    "win_rate": 0.6875,  # 22/32
    "total_profit": 4500.0,
    "avg_profit_per_win": 204.55  # 4500/22
}
```

---

### 7. `get_best_strategy_for_context()` - Find Best Strategy

**Purpose:** Find the historically best-performing strategy for a given context.

```python
def get_best_strategy_for_context(
    self,
    platform: str,
    value_tier: str,
    min_samples: int = 5
) -> Optional[str]:
```

**SQL Query:**
```sql
SELECT strategy, total_uses, wins, 
       CAST(wins AS FLOAT) / total_uses as win_rate
FROM strategy_performance
WHERE platform = ? AND value_tier = ? AND total_uses >= ?
ORDER BY win_rate DESC
LIMIT 1
```

**Query Breakdown:**
- `WHERE platform = ? AND value_tier = ?` - Match context
- `AND total_uses >= ?` - Only strategies with enough data (default: 5)
- `CAST(wins AS FLOAT) / total_uses` - Calculate win_rate in SQL
- `ORDER BY win_rate DESC` - Best first
- `LIMIT 1` - Return only the best

**Why `min_samples`?**
- Prevents recommending strategies with only 1-2 uses
- Ensures statistical significance
- Default: 5 auctions minimum

**Example:**
```python
best = storage.get_best_strategy_for_context(
    platform="godaddy",
    value_tier="high",
    min_samples=5
)

# Returns: "proxy_max" (if it has highest win_rate with ≥5 uses)
```

---

## 🔄 Complete Data Flow Example

### Step 1: Record Outcome
```python
from history.storage import AuctionHistoryStorage
from history.models import AuctionOutcome

storage = AuctionHistoryStorage()

outcome = AuctionOutcome(
    auction_id="test.com_2025-12-05",
    domain="test.com",
    platform="godaddy",
    estimated_value=2500.0,
    strategy_used="proxy_max",
    result="won",
    # ... other fields
)

storage.record_outcome(outcome)
```

**What happens:**
1. Outcome saved to `auction_outcomes` table
2. `_update_strategy_performance()` called automatically
3. Strategy stats updated in `strategy_performance` table

### Step 2: Query Similar Auctions
```python
similar = storage.get_similar_auctions(
    platform="godaddy",
    value_min=2000.0,
    value_max=3000.0,
    limit=10
)
# Returns: List of 10 similar auction records
```

### Step 3: Get Strategy Performance
```python
stats = storage.get_strategy_performance(
    strategy="proxy_max",
    platform="godaddy",
    value_tier="high"
)
# Returns: {"win_rate": 0.70, "total_uses": 20, ...}
```

### Step 4: Find Best Strategy
```python
best = storage.get_best_strategy_for_context(
    platform="godaddy",
    value_tier="high"
)
# Returns: "proxy_max" (if it's the best)
```

---

## 🔍 SQL Query Patterns

### Pattern 1: Find Recent Auctions
```sql
SELECT * FROM auction_outcomes
ORDER BY timestamp DESC
LIMIT 10
```

### Pattern 2: Count Wins by Strategy
```sql
SELECT strategy_used, COUNT(*) as wins
FROM auction_outcomes
WHERE result = 'won'
GROUP BY strategy_used
```

### Pattern 3: Average Profit Margin
```sql
SELECT AVG(profit_margin) as avg_profit
FROM auction_outcomes
WHERE result = 'won' AND profit_margin IS NOT NULL
```

### Pattern 4: Win Rate by Platform
```sql
SELECT 
    platform,
    COUNT(*) as total,
    SUM(CASE WHEN result = 'won' THEN 1 ELSE 0 END) as wins,
    CAST(SUM(CASE WHEN result = 'won' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as win_rate
FROM auction_outcomes
GROUP BY platform
```

---

## ⚠️ Important Notes

1. **Connection Management**
   - Always close connections after use
   - Use `conn.commit()` to save changes
   - SQLite handles concurrent reads, but writes need care

2. **Data Types**
   - SQLite stores everything as TEXT, INTEGER, or REAL
   - Booleans stored as INTEGER (0 or 1)
   - Datetimes stored as TEXT (ISO format)

3. **UNIQUE Constraints**
   - `auction_id` must be unique
   - `strategy + platform + value_tier` must be unique
   - `INSERT OR REPLACE` handles conflicts

4. **Performance**
   - SQLite is fast for <100K records
   - Consider indexing if queries slow down
   - `raw_data` JSON parsing adds overhead

---

## 🚀 Future Enhancements

1. **Add Indexes** - Speed up queries on `platform`, `estimated_value`
2. **Add Migrations** - Handle schema changes over time
3. **Add Backup** - Automatic database backups
4. **Add Analytics** - Pre-computed reports and dashboards

---

## 📝 Usage Checklist

- [ ] Database created automatically on first use
- [ ] Call `record_outcome()` after each auction
- [ ] Use `get_similar_auctions()` for context
- [ ] Use `get_strategy_performance()` for insights
- [ ] Use `get_best_strategy_for_context()` for recommendations





