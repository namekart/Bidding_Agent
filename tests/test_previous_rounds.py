"""
Test script for "previous rounds for this auction" (thread_id + same_auction_attempts).

Run:
  python test_previous_rounds.py

Requires SUPABASE_URL and SUPABASE_KEY in .env for storage tests.
Without Supabase, only the learning logic (with mocked empty rounds) is exercised.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from app.core.models import AuctionContext, BidderAnalysis, FinalDecision


def _make_context(thread_id=None, **kwargs):
    base = {
        "domain": "test-domain.com",
        "platform": "godaddy",
        "estimated_value": 500.0,
        "current_bid": 200.0,
        "num_bidders": 2,
        "hours_remaining": 5.0,
        "your_current_proxy": 0.0,
        "budget_available": 10000.0,
        "bidder_analysis": BidderAnalysis(
            bot_detected=False,
            corporate_buyer=False,
            aggression_score=3.0,
            reaction_time_avg=60.0,
        ),
    }
    base.update(kwargs)
    if thread_id is not None:
        base["thread_id"] = thread_id
    return AuctionContext(**base)


def test_learning_returns_same_auction_attempts():
    """Learning.get_historical_context with thread_id returns same_auction_attempts (list)."""
    from app.history.learning import HistoricalLearning
    from app.history.storage import AuctionHistoryStorage

    try:
        storage = AuctionHistoryStorage()
    except ValueError:
        print("  [SKIP] SUPABASE_URL/SUPABASE_KEY not set; using mock storage to check return structure.")
        # Mock: get_rounds_for_thread returns []
        class MockStorage:
            def get_similar_auctions(self, *a, **k): return []
            def get_strategy_performance(self, *a, **k): return {"total_uses": 0}
            def get_best_strategy_for_context(self, *a, **k): return None
            def get_rounds_for_thread(self, thread_id): return []
        storage = MockStorage()

    learning = HistoricalLearning(storage)
    ctx = _make_context(thread_id="test-thread-123")
    out = learning.get_historical_context(ctx)
    assert "same_auction_attempts" in out, "historical_context must include same_auction_attempts"
    assert isinstance(out["same_auction_attempts"], list), "same_auction_attempts must be a list"
    print("  [OK] get_historical_context returns same_auction_attempts (list).")


def test_storage_rounds():
    """With Supabase: record_round and get_rounds_for_thread."""
    from app.history.models import AuctionRoundRecord
    from app.history.storage import AuctionHistoryStorage

    try:
        storage = AuctionHistoryStorage()
    except ValueError as e:
        print(f"  [SKIP] Storage not available: {e}")
        return

    thread_id = "test-thread-" + str(os.getpid())
    # Record one round
    r1 = AuctionRoundRecord(
        thread_id=thread_id,
        round_number=1,
        domain="test-domain.com",
        platform="godaddy",
        estimated_value=500.0,
        current_bid_at_decision=200.0,
        strategy_used="proxy_max",
        recommended_bid=400.0,
        decision_source="llm",
        confidence=0.8,
        result_round="outbid",
    )
    storage.record_round(r1)
    rounds = storage.get_rounds_for_thread(thread_id)
    assert len(rounds) >= 1, "get_rounds_for_thread should return at least the round we just recorded"
    assert rounds[0]["strategy_used"] == "proxy_max" and rounds[0]["result_round"] == "outbid"
    print("  [OK] record_round + get_rounds_for_thread work.")

    # Record second round (same thread)
    r2 = AuctionRoundRecord(
        thread_id=thread_id,
        round_number=2,
        domain="test-domain.com",
        platform="godaddy",
        estimated_value=500.0,
        current_bid_at_decision=350.0,
        strategy_used="aggressive_early",
        recommended_bid=450.0,
        decision_source="llm",
        confidence=0.7,
        result_round="outbid",
    )
    storage.record_round(r2)
    rounds = storage.get_rounds_for_thread(thread_id)
    assert len(rounds) >= 2
    print("  [OK] Multiple rounds for same thread_id stored and retrieved.")


def test_selector_record_round_outcome():
    """With Supabase: HybridStrategySelector.record_round_outcome then get_historical_context has attempts."""
    from app.history.learning import HistoricalLearning
    from app.history.storage import AuctionHistoryStorage
    from app.agent.hybrid_strategy_selector import HybridStrategySelector

    try:
        selector = HybridStrategySelector()
    except Exception as e:
        print(f"  [SKIP] Selector init failed (e.g. no Supabase): {e}")
        return

    if not selector.history_storage:
        print("  [SKIP] No history_storage (Supabase not configured).")
        return

    thread_id = "test-selector-thread-" + str(os.getpid())
    ctx = _make_context(thread_id=thread_id)
    # Fake a decision we would have got from select_strategy
    decision = FinalDecision(
        strategy="proxy_max",
        recommended_bid_amount=400.0,
        should_increase_proxy=True,
        next_bid_amount=210.0,
        max_budget_for_domain=500.0,
        risk_level="medium",
        confidence=0.75,
        reasoning="Test round 1.",
        proxy_decision=None,
        decision_source="llm",
    )
    selector.record_round_outcome(ctx, decision, "outbid")
    # Now historical context for same thread should include this attempt
    hist = selector.learning.get_historical_context(ctx)
    attempts = hist.get("same_auction_attempts", [])
    assert len(attempts) >= 1, "same_auction_attempts should include the round we just recorded"
    assert attempts[0]["strategy_used"] == "proxy_max" and attempts[0]["result_round"] == "outbid"
    print("  [OK] record_round_outcome + get_historical_context: same_auction_attempts populated.")


def main():
    print("Testing previous-rounds integration (thread_id + same_auction_attempts)\n")
    print("1. Learning returns same_auction_attempts")
    test_learning_returns_same_auction_attempts()
    print("\n2. Storage record_round / get_rounds_for_thread")
    test_storage_rounds()
    print("\n3. Selector record_round_outcome and historical context")
    test_selector_record_round_outcome()
    print("\nDone. If all [OK] or [SKIP] (when Supabase not set), integration is in place.")


if __name__ == "__main__":
    main()
