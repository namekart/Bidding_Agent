# Testing Guide for Market Intelligence Integration

This guide explains how to test your Domain Auction Strategy AI system with the newly integrated Layer 0 market intelligence.

## ✅ Quick Test (No MySQL Required)

The simplest test that verifies market intelligence is working:

```bash
python test_market_intelligence_simple.py
```

This test:
- ✅ Loads all 3 parquet files (bidder profiles, domain stats, auction archetypes)
- ✅ Tests bidder intelligence lookups
- ✅ Tests domain intelligence lookups  
- ✅ Tests auction archetype lookups
- ✅ Tests context enrichment

**Expected Output:**
```
[SUCCESS] All basic market intelligence tests passed!
```

---

## 🧪 Full Integration Test (Requires MySQL)

For full integration testing with the complete system:

### Option 1: With MySQL Configuration

```python
from hybrid_strategy_selector import HybridStrategySelector
from models import AuctionContext, BidderAnalysis

# Configure MySQL
mysql_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'your_user',
    'password': 'your_password',
    'database': 'bidding_auction_db'
}

# Initialize selector
selector = HybridStrategySelector(
    llm_provider="openrouter",
    model="openai/gpt-5.1",
    enable_fallback=True,
    mysql_config=mysql_config,
    data_dir="."  # Directory containing parquet files
)

# Test with a scenario
context = AuctionContext(
    domain="example.com",
    platform="godaddy",
    estimated_value=1000.0,
    current_bid=500.0,
    num_bidders=3,
    hours_remaining=2.0,
    your_current_proxy=450.0,
    budget_available=5000.0,
    bidder_analysis=BidderAnalysis(
        bot_detected=False,
        corporate_buyer=False,
        aggression_score=5.0,
        reaction_time_avg=30.0
    )
)

# Get strategy decision (includes market intelligence)
decision = selector.select_strategy(context)
print(f"Strategy: {decision.strategy}")
print(f"Reasoning: {decision.reasoning}")
```

### Option 2: Test with Existing Test Suite

Use the existing test suite which includes market intelligence:

```bash
python test_strategy_system.py
```

This will test the full system including:
- Safety filters
- LLM strategy selection (with market intelligence)
- Rule-based fallback (with market intelligence)
- Proxy logic

---

## 🔍 What to Verify

### 1. Market Intelligence Loading

Check that parquet files are loaded:
```python
from market_intelligence import MarketIntelligenceLoader

loader = MarketIntelligenceLoader(data_dir=".")
print(f"Bidders: {len(loader.bidder_profiles)}")
print(f"Domains: {len(loader.domain_stats)}")
print(f"Archetypes: {len(loader.auction_archetypes)}")
```

**Expected:**
- Bidder profiles: ~2,230 bidders
- Domain stats: ~5,436 domains
- Auction archetypes: ~5,463 auctions

### 2. Lookup Functionality

Test individual lookups:

```python
# Bidder lookup
bidder_intel = loader.get_bidder_intelligence("bidder_name_here")
print(bidder_intel)

# Domain lookup
domain_intel = loader.get_domain_intelligence("example.com")
print(domain_intel)

# Archetype lookup
archetype = loader.get_auction_archetype("godaddy")
print(archetype)
```

### 3. Context Enrichment

Verify context enrichment works:

```python
from models import AuctionContext, BidderAnalysis

context = AuctionContext(
    domain="example.com",
    platform="godaddy",
    estimated_value=1000.0,
    current_bid=500.0,
    num_bidders=3,
    hours_remaining=2.0,
    your_current_proxy=450.0,
    budget_available=5000.0,
    bidder_analysis=BidderAnalysis(
        bot_detected=False,
        corporate_buyer=False,
        aggression_score=5.0,
        reaction_time_avg=30.0
    )
)

market_intel = loader.enrich_context(context, last_bidder_id="some_bidder")
print(market_intel)
```

### 4. Integration with Strategy Selection

Verify market intelligence is passed through the system:

```python
# Check that market intelligence is in the state
decision = selector.select_strategy(context)

# Market intelligence should influence:
# - LLM reasoning (check decision.reasoning)
# - Rule-based decisions (if LLM fails)
# - Strategy confidence scores
```

---

## 📊 Test Scenarios

### Scenario 1: Domain with Historical Data

```python
# Use a domain that exists in domain_stats.parquet
# Check if domain intelligence is found and influences decision
context = AuctionContext(
    domain="0071.net",  # From your parquet data
    platform="godaddy",
    estimated_value=100.0,
    # ... rest of context
)
```

### Scenario 2: Bidder with Profile

```python
# Use a bidder that exists in bidder_profiles.parquet
# Check if bidder intelligence influences strategy
loader = MarketIntelligenceLoader()
sample_bidder = loader.bidder_profiles.iloc[0]["bidder_name"]

# Pass bidder_id when enriching context
market_intel = loader.enrich_context(context, last_bidder_id=sample_bidder)
```

### Scenario 3: Platform-Specific Archetype

```python
# Test different platforms
for platform in ["godaddy", "namejet", "dynadot"]:
    archetype = loader.get_auction_archetype(platform)
    print(f"{platform}: {archetype}")
```

---

## 🐛 Troubleshooting

### Issue: "MySQL config required" Error

**Solution:** The system requires MySQL for historical learning. You have two options:

1. **Provide MySQL config:**
   ```python
   mysql_config = {
       'host': 'localhost',
       'port': 3306,
       'user': 'your_user',
       'password': 'your_password',
       'database': 'bidding_auction_db'
   }
   selector = HybridStrategySelector(mysql_config=mysql_config)
   ```

2. **Test market intelligence independently:**
   ```bash
   python test_market_intelligence_simple.py
   ```

### Issue: "Parquet file not found"

**Solution:** Ensure parquet files are in the correct location:
- `layer0_bidder_profiles.parquet`
- `layer0_domain_stats.parquet`
- `layer0_auction_archetypes.parquet`

All should be in the same directory as your Python scripts, or specify `data_dir` parameter.

### Issue: "Column not found" errors

**Solution:** The code is already updated to match your parquet schema:
- Bidder profiles: `bidder_name`, `total_auctions`, `avg_bid_increase`, etc.
- Domain stats: `domain`, `avg_final_price`, `volatility`, etc.
- Archetypes: Uses aggregate stats (no platform column in your data)

If you see column errors, check that your parquet files match the expected schema.

---

## ✅ Success Criteria

Your integration is working correctly if:

1. ✅ `test_market_intelligence_simple.py` passes all tests
2. ✅ Parquet files load without errors
3. ✅ Lookups return data (when bidders/domains exist in data)
4. ✅ Context enrichment produces market intelligence signals
5. ✅ Strategy decisions are generated (with or without MySQL)
6. ✅ Market intelligence appears in LLM reasoning (if using LLM)

---

## 🚀 Next Steps

After verifying the integration:

1. **Test with real auction scenarios** using `test_strategy_system.py`
2. **Monitor decision quality** - check if market intelligence improves decisions
3. **Verify LLM prompts** include market intelligence signals
4. **Check rule-based fallback** uses market intelligence when LLM fails
5. **Performance testing** - ensure lookups are fast (should be < 1ms)

---

## 📝 Test Checklist

- [ ] Market intelligence loader initializes
- [ ] Parquet files load successfully
- [ ] Bidder lookups work
- [ ] Domain lookups work
- [ ] Archetype lookups work
- [ ] Context enrichment works
- [ ] Integration with HybridStrategySelector works (if MySQL available)
- [ ] Strategy decisions are generated
- [ ] Market intelligence appears in reasoning (check LLM output)

---

## 💡 Tips

1. **Start simple:** Use `test_market_intelligence_simple.py` first
2. **Check data:** Verify your parquet files have data before testing lookups
3. **Use real domains:** Test with domains that exist in your `domain_stats.parquet`
4. **Monitor performance:** Market intelligence lookups should be very fast (< 1ms)
5. **Read reasoning:** Check `decision.reasoning` to see if market intelligence influenced the decision

---

## 📞 Need Help?

If tests fail:
1. Check error messages carefully
2. Verify parquet files exist and are readable
3. Check column names match between code and parquet files
4. Ensure all dependencies are installed (`pandas`, `pyarrow`)

For MySQL issues, see `test_history_mysql.py` for MySQL configuration examples.
