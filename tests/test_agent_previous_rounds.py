# save as test_agent_previous_rounds.py and run: python test_agent_previous_rounds.py
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Load .env so Supabase + LLM work
from dotenv import load_dotenv
load_dotenv()

from app.core.models import AuctionContext, BidderAnalysis
from app.agent.hybrid_strategy_selector import HybridStrategySelector

def main():
    bidder_analysis = BidderAnalysis(
        bot_detected=False,
        corporate_buyer=False,
        aggression_score=4.0,
        reaction_time_avg=45.0,
    )
    thread_id = "e2e-test-thread-001"

    # Round 1
    ctx1 = AuctionContext(
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
    selector = HybridStrategySelector()
    print("--- Round 1 ---")
    decision1 = selector.select_strategy(ctx1)
    print(f"Strategy: {decision1.strategy}, Bid: {decision1.recommended_bid_amount}")
    print(f"Reasoning: {decision1.reasoning[:200]}...")

    # Simulate outbid: record round 1
    selector.record_round_outcome(ctx1, decision1, "outbid")
    print("\nRecorded round 1 as 'outbid'.")

    # Round 2 (same thread_id; e.g. higher current bid)
    ctx2 = AuctionContext(
        domain="example.com",
        platform="godaddy",
        estimated_value=800.0,
        current_bid=400.0,
        num_bidders=2,
        hours_remaining=2.5,
        your_current_proxy=decision1.recommended_bid_amount,
        budget_available=5000.0,
        bidder_analysis=bidder_analysis,
        thread_id=thread_id,
    )
    print("--- Round 2 (same auction) ---")
    decision2 = selector.select_strategy(ctx2)
    print(f"Strategy: {decision2.strategy}, Bid: {decision2.recommended_bid_amount}")
    print(f"Reasoning: {decision2.reasoning[:200]}...")

    # Check that round 2 "saw" round 1 (optional)
    hist = selector.learning.get_historical_context(ctx2)
    attempts = hist.get("same_auction_attempts", [])
    print(f"\nSame-auction attempts seen in round 2: {attempts}")
    if attempts:
        print("OK: Agent had access to previous round(s) for this auction.")

if __name__ == "__main__":
    main()