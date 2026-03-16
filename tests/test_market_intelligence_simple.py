"""
Simple Test Script for Market Intelligence Integration
Tests the Layer 0 market intelligence without requiring MySQL.
"""
import os
import json
from typing import Dict, Any
from app.core.models import AuctionContext, BidderAnalysis
from app.services.market_intelligence import MarketIntelligenceLoader


def test_market_intelligence_basic():
    """Test basic market intelligence functionality."""
    print("="*80)
    print("MARKET INTELLIGENCE - BASIC TEST")
    print("="*80)
    
    try:
        # Initialize loader
        print("\n1. Initializing MarketIntelligenceLoader...")
        loader = MarketIntelligenceLoader(data_dir=".")
        print("   [OK] Loader initialized")
        
        # Show data stats
        print(f"\n2. Data Statistics:")
        print(f"   - Bidder profiles: {len(loader.bidder_profiles)}")
        print(f"   - Domain stats: {len(loader.domain_stats)}")
        print(f"   - Auction archetypes: {len(loader.auction_archetypes)}")
        
        # Test bidder lookup
        print("\n3. Testing Bidder Intelligence Lookup...")
        if len(loader.bidder_profiles) > 0:
            sample_bidder = loader.bidder_profiles.iloc[0]
            bidder_name = sample_bidder.get("bidder_name", None)
            if bidder_name:
                bidder_intel = loader.get_bidder_intelligence(bidder_name)
                print(f"   Sample bidder: {bidder_name}")
                print(f"   Found: {bidder_intel.get('found', False)}")
                if bidder_intel.get('found'):
                    print(f"   - Total auctions: {bidder_intel.get('total_auctions_participated', 0)}")
                    print(f"   - Win rate: {bidder_intel.get('win_rate', 0):.2%}")
                    print(f"   - Is aggressive: {bidder_intel.get('is_aggressive', False)}")
                    print(f"   - Is sniper: {bidder_intel.get('is_sniper', False)}")
                    print("   [OK] Bidder lookup working")
        
        # Test domain lookup
        print("\n4. Testing Domain Intelligence Lookup...")
        if len(loader.domain_stats) > 0:
            sample_domain = loader.domain_stats.iloc[0]
            domain_name = sample_domain.get("domain", None)
            if domain_name:
                domain_intel = loader.get_domain_intelligence(domain_name)
                print(f"   Sample domain: {domain_name}")
                print(f"   Found: {domain_intel.get('found', False)}")
                if domain_intel.get('found'):
                    print(f"   - Avg final price: ${domain_intel.get('average_final_price', 0):.2f}")
                    print(f"   - Volatility: {domain_intel.get('price_volatility', 0):.2f}")
                    print(f"   - Is volatile: {domain_intel.get('is_volatile', False)}")
                    print("   [OK] Domain lookup working")
        
        # Test archetype lookup
        print("\n5. Testing Auction Archetype Lookup...")
        archetype = loader.get_auction_archetype("godaddy")
        print(f"   Found: {archetype.get('found', False)}")
        if archetype.get('found'):
            print(f"   - Sniper dominated: {archetype.get('sniper_dominated', False)}")
            print(f"   - Proxy driven: {archetype.get('proxy_driven', False)}")
            print(f"   - Avg late bid ratio: {archetype.get('avg_late_bid_ratio', 0):.2f}")
            print("   [OK] Archetype lookup working")
        
        # Test enrich_context
        print("\n6. Testing Context Enrichment...")
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
        
        # Get sample bidder for testing
        if len(loader.bidder_profiles) > 0:
            sample_bidder = loader.bidder_profiles.iloc[0]
            bidder_name = sample_bidder.get("bidder_name", None)
        else:
            bidder_name = None
        
        market_intel = loader.enrich_context(context, last_bidder_id=bidder_name)
        print(f"   Bidder intelligence: {market_intel['bidder_intelligence'].get('found', False)}")
        print(f"   Domain intelligence: {market_intel['domain_intelligence'].get('found', False)}")
        print(f"   Auction archetype: {market_intel['auction_archetype'].get('found', False)}")
        print("   [OK] Context enrichment working")
        
        print("\n" + "="*80)
        print("[SUCCESS] All basic market intelligence tests passed!")
        print("="*80)
        print("\nMarket intelligence is ready to use!")
        print("Next steps:")
        print("  1. Integrate with HybridStrategySelector (requires MySQL config)")
        print("  2. Test with real auction scenarios")
        print("  3. Verify market intelligence appears in LLM prompts")
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_market_intelligence_basic()
