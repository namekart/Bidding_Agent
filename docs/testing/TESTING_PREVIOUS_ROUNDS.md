# Testing "Previous Rounds for This Auction"

This describes how to test the thread_id + same_auction_attempts integration.

## Prerequisites

1. **Supabase**: Create the `auction_rounds` table by running the full `supabase_tables.sql` in the Supabase SQL Editor (you already have the table if you ran it).
2. **Env**: Set `SUPABASE_URL` and `SUPABASE_KEY` in `.env` (or environment).

## 1. Run the automated test script

```bash
python test_previous_rounds.py
```

- **With Supabase configured**: All three tests should report `[OK]`.
- **Without Supabase**: You will see `[SKIP]` for storage/selector tests; the learning structure test may still run. No errors means the code paths are wired.

## 2. Manual end-to-end test (same auction, two rounds)

Use one thread_id for the same “auction” and call the selector twice: once for round 1, then record outbid and call again for round 2. The second call should see “Previous attempts in THIS auction” in the prompt and can choose a different strategy.

### Step 1: Create context with a stable `thread_id`

```python
from models import AuctionContext, BidderAnalysis

bidder_analysis = BidderAnalysis(
    bot_detected=False,
    corporate_buyer=False,
    aggression_score=4.0,
    reaction_time_avg=45.0,
)

thread_id = "my-auction-001"  # Same for all rounds of this domain auction

ctx = AuctionContext(
    domain="example.com",
    platform="godaddy",
    estimated_value=800.0,
    current_bid=300.0,
    num_bidders=2,
    hours_remaining=3.0,
    your_current_proxy=0.0,
    budget_available=5000.0,
    bidder_analysis=bidder_analysis,
    thread_id=thread_id,
)
```

### Step 2: First decision (round 1)

```python
from hybrid_strategy_selector import HybridStrategySelector

selector = HybridStrategySelector()
decision1 = selector.select_strategy(ctx)
print(decision1.strategy, decision1.recommended_bid_amount)
# e.g. proxy_max, 560.0
```

### Step 3: Simulate “got outbid” and record the round

```python
# You got outbid; record this round so the next decision knows we already tried this strategy.
selector.record_round_outcome(ctx, decision1, "outbid")
```

### Step 4: Update context for round 2 (e.g. higher current_bid, same thread_id)

```python
ctx_round2 = AuctionContext(
    domain="example.com",
    platform="godaddy",
    estimated_value=800.0,
    current_bid=400.0,   # Someone outbid us
    num_bidders=2,
    hours_remaining=2.5,
    your_current_proxy=560.0,  # Our previous proxy
    budget_available=5000.0,
    bidder_analysis=bidder_analysis,
    thread_id=thread_id,  # Same thread!
)
decision2 = selector.select_strategy(ctx_round2)
print(decision2.strategy, decision2.reasoning)
# The LLM should see "Previous attempts in THIS auction: Round 1: strategy=proxy_max, result=outbid"
# and may suggest a different strategy (e.g. aggressive_early or last_minute_snipe).
```

### Step 5: When the auction ends (won or lost)

```python
# Only when the auction is over:
selector.record_outcome(ctx_round2, decision2, "won", final_price=450.0)
# or: selector.record_outcome(..., "lost", final_price=500.0)
```

## 3. What to check

- **Round 1**: `select_strategy(ctx)` returns a decision; no “previous attempts” in the prompt.
- **After `record_round_outcome(ctx, decision1, "outbid")`**: Supabase table `auction_rounds` has one row for that `thread_id`.
- **Round 2**: `select_strategy(ctx_round2)` receives `historical_context["same_auction_attempts"]` with one entry (Round 1: proxy_max, outbid). The user prompt should contain “Previous attempts in THIS auction” and the model may choose a different strategy.
- **After auction ends**: Call `record_outcome(...)` once; `auction_outcomes` has the final outcome; you can keep using `record_round_outcome` for the last round too if you want that round in `auction_rounds`.

## 4. Optional: Inspect what the LLM sees

In `llm_strategy.py`, the prompt is built with `same_auction_section` when `same_auction_attempts` is non-empty. You can add a temporary print before the LLM call:

```python
# In get_strategy_decision, before _call_llm:
if same_auction_attempts:
    print("[DEBUG] Same-auction attempts sent to LLM:", same_auction_attempts)
```

Run the two-round flow above and confirm the second call prints the first round.
