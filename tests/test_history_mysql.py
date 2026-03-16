"""
Test history module with MySQL
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.history.models import AuctionOutcome
from app.history.storage import AuctionHistoryStorage
from app.history.learning import HistoricalLearning
from app.core.models import AuctionContext, BidderAnalysis

def test_mysql_storage():
    """Test MySQL storage operations"""
    print("\n" + "="*60)
    print("TEST: MySQL Storage Operations")
    print("="*60)
    
    # MySQL configuration
    mysql_config = {
        'host': 'localhost',  # Change to your VM IP if remote
        'port': 3306,
        'user': 'root',
        'password': 'S@chname.com',  # ← Change this!
        'database': 'bidding_auction_db'
    }
    
    try:
        # Initialize storage with MySQL
        print("\n1. Initializing MySQL storage...")
        storage = AuctionHistoryStorage(mysql_config=mysql_config)
        print("   ✅ Storage initialized")
        
        # Create test outcome
        print("\n2. Creating test auction outcome...")
        outcome = AuctionOutcome(
            auction_id="mysql_test_001",
            domain="mysqltest.com",
            platform="godaddy",
            timestamp=datetime.utcnow(),
            estimated_value=2500.0,
            current_bid_at_decision=800.0,
            final_price=1850.0,
            num_bidders=4,
            hours_remaining_at_decision=2.5,
            bot_detected=True,
            strategy_used="proxy_max",
            recommended_bid=1750.0,
            decision_source="llm",
            confidence=0.75,
            result="won",
            profit_margin=0.26,
            opponent_hash=None,
            raw_data=None
        )
        print(f"   ✅ Outcome created: {outcome.domain}")
        
        # Record outcome
        print("\n3. Recording outcome to MySQL...")
        storage.record_outcome(outcome)
        print("   ✅ Outcome recorded successfully")
        
        # Query similar auctions
        print("\n4. Querying similar auctions...")
        similar = storage.get_similar_auctions(
            platform="godaddy",
            value_min=2000.0,
            value_max=3000.0,
            limit=5
        )
        print(f"   ✅ Found {len(similar)} similar auctions")
        
        # Get strategy performance
        print("\n5. Getting strategy performance...")
        stats = storage.get_strategy_performance(
            strategy="proxy_max",
            platform="godaddy"
        )
        print(f"   ✅ Strategy stats retrieved")
        print(f"      Total uses: {stats.get('total_uses', 0)}")
        print(f"      Win rate: {stats.get('win_rate', 0):.2%}")
        
        # Get best strategy
        print("\n6. Finding best strategy...")
        best = storage.get_best_strategy_for_context(
            platform="godaddy",
            value_tier="high"
        )
        print(f"   ✅ Best strategy: {best}")
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_learning_with_mysql():
    """Test learning module with MySQL"""
    print("\n" + "="*60)
    print("TEST: Learning Module with MySQL")
    print("="*60)
    
    mysql_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'S@chname.com',  # ← Change this!
        'database': 'bidding_auction_db'
    }
    
    try:
        storage = AuctionHistoryStorage(mysql_config=mysql_config)
        learning = HistoricalLearning(storage)
        
        # Create test context
        context = AuctionContext(
            domain="learningtest.com",
            platform="godaddy",
            estimated_value=2500.0,
            current_bid=800.0,
            num_bidders=4,
            hours_remaining=2.5,
            your_current_proxy=750.0,
            budget_available=5000.0,
            bidder_analysis=BidderAnalysis(
                bot_detected=True,
                corporate_buyer=False,
                aggression_score=8.5,
                reaction_time_avg=0.8
            )
        )
        
        print("\n1. Getting historical context...")
        historical = learning.get_historical_context(context)
        print("   ✅ Historical context retrieved")
        print(f"      Similar auctions: {historical['similar_auctions_count']}")
        print(f"      Value tier: {historical['value_tier']}")
        print(f"      Best strategy: {historical['historically_best_strategy']}")
        
        print("\n2. Getting dynamic threshold...")
        threshold = learning.suggest_dynamic_threshold(context)
        print(f"   ✅ Dynamic threshold: {threshold:.2%}")
        
        print("\n" + "="*60)
        print("✅ LEARNING TESTS PASSED!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_hybrid_selector_with_mysql():
    """Test hybrid selector with MySQL"""
    print("\n" + "="*60)
    print("TEST: Hybrid Selector with MySQL")
    print("="*60)
    
    mysql_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'S@chname.com',  # ← Change this!
        'database': 'bidding_auction_db'
    }
    
    try:
        from app.agent.hybrid_strategy_selector import HybridStrategySelector
        
        print("\n1. Initializing HybridStrategySelector with MySQL...")
        selector = HybridStrategySelector(
            llm_provider="openrouter",
            model="openai/gpt-5.1",
            mysql_config=mysql_config
        )
        print("   ✅ Selector initialized with MySQL")
        
        # Create test context
        context = AuctionContext(
            domain="hybridtest.com",
            platform="godaddy",
            estimated_value=2000.0,
            current_bid=600.0,
            num_bidders=3,
            hours_remaining=2.0,
            your_current_proxy=550.0,
            budget_available=4000.0,
            bidder_analysis=BidderAnalysis(
                bot_detected=False,
                corporate_buyer=False,
                aggression_score=5.0,
                reaction_time_avg=45.0
            )
        )
        
        print("\n2. Getting strategy decision...")
        decision = selector.select_strategy(context)
        print("   ✅ Decision retrieved")
        print(f"      Strategy: {decision.strategy}")
        print(f"      Recommended bid: ${decision.recommended_bid_amount:.2f}")
        print(f"      Decision source: {decision.decision_source}")
        
        print("\n" + "="*60)
        print("✅ HYBRID SELECTOR TEST PASSED!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("MYSQL INTEGRATION - COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("MySQL Storage", test_mysql_storage()))
    results.append(("Learning Module", test_learning_with_mysql()))
    results.append(("Hybrid Selector", test_hybrid_selector_with_mysql()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:20} {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All MySQL tests passed!")
        print("\nNext steps:")
        print("1. Check data in MySQL Workbench")
        print("2. Verify tables were created")
        print("3. Start using in production")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

        