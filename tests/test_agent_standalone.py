"""
Standalone test that bypasses MySQL storage entirely
Tests multiple real-world scenarios with different domains and bidder profiles.
Analyzes buyer types and strategy selection.
"""
from app.core.models import AuctionContext, BidderAnalysis
from app.services.market_intelligence import MarketIntelligenceLoader
from app.core.safety_filters import SafetyPreFilters
from app.agent.rule_based_strategy import RuleBasedStrategySelector
from app.agent.llm_strategy import LLMStrategySelector
from app.agent.proxy_logic import ProxyLogicHandler
from app.core.validation import StrategyValidator

def analyze_bidder_type(bidder_intel):
    """Analyze and classify bidder type based on intelligence."""
    if not bidder_intel.get('found'):
        return "Unknown (No Profile)"
    
    characteristics = []
    bidder_type = []
    
    if bidder_intel.get('is_aggressive', False):
        characteristics.append("Aggressive")
        bidder_type.append("High-Risk Competitor")
    
    if bidder_intel.get('is_sniper', False):
        characteristics.append("Sniper")
        bidder_type.append("Late-Bid Specialist")
    
    if bidder_intel.get('is_proxy_heavy', False):
        characteristics.append("Proxy-Heavy")
        bidder_type.append("Auto-Bid User")
    
    win_rate = bidder_intel.get('win_rate', 0)
    if win_rate > 0.5:
        characteristics.append("High Win Rate")
        bidder_type.append("Successful Buyer")
    elif win_rate < 0.2:
        characteristics.append("Low Win Rate")
        bidder_type.append("Casual Bidder")
    
    if not characteristics:
        characteristics.append("Balanced")
        bidder_type.append("Standard Bidder")
    
    return f"{', '.join(bidder_type)} ({', '.join(characteristics)})"

def test_single_scenario(market_intel, domain, bidder_id, scenario_name, context_params):
    """Test a single scenario with specific domain and bidder."""
    print("\n" + "="*80)
    print(f"SCENARIO: {scenario_name}")
    print("="*80)
    
    # Create context
    context = AuctionContext(
        domain=domain,
        **context_params
    )
    
    # Get market intelligence
    market_intel_signals = market_intel.enrich_context(context, last_bidder_id=bidder_id)
    
    # Analyze bidder
    bidder_intel = market_intel_signals['bidder_intelligence']
    domain_intel = market_intel_signals['domain_intelligence']
    archetype = market_intel_signals['auction_archetype']
    
    print(f"\n[OPPONENT ANALYSIS]")
    print(f"   Bidder ID: {bidder_id if bidder_id else 'Unknown'}")
    if bidder_intel.get('found'):
        bidder_type = analyze_bidder_type(bidder_intel)
        print(f"   Bidder Type: {bidder_type}")
        print(f"   - Total Auctions: {bidder_intel.get('total_auctions_participated', 0):.0f}")
        print(f"   - Win Rate: {bidder_intel.get('win_rate', 0):.2%}")
        print(f"   - Avg Bid Increase: ${bidder_intel.get('average_bid_increase', 0):.2f}")
        print(f"   - Highest Bid: ${bidder_intel.get('highest_ever_bid', 0):.2f}")
        print(f"   - Late Bid Ratio: {bidder_intel.get('late_bid_ratio', 0):.2%}")
        print(f"   - Proxy Usage: {bidder_intel.get('proxy_bid_usage_ratio', 0):.2%}")
        print(f"   - Reaction Time: {bidder_intel.get('average_reaction_time', 0):.1f}s")
    else:
        print(f"   Bidder Type: Unknown (No profile in database)")
    
    print(f"\n[DOMAIN ANALYSIS]")
    print(f"   Domain: {domain}")
    if domain_intel.get('found'):
        print(f"   - Avg Final Price: ${domain_intel.get('average_final_price', 0):.2f}")
        print(f"   - Volatility: {domain_intel.get('price_volatility', 0):.2f}")
        print(f"   - Is Volatile: {domain_intel.get('is_volatile', False)}")
        print(f"   - Has History: {domain_intel.get('has_history', False)}")
    else:
        print(f"   - No historical data available")
    
    print(f"\n[PLATFORM ARCHETYPE]")
    if archetype.get('found'):
        print(f"   - Escalation: {archetype.get('escalation_speed', 'unknown')}")
        print(f"   - Sniper Dominated: {archetype.get('sniper_dominated', False)}")
        print(f"   - Proxy Driven: {archetype.get('proxy_driven', False)}")
        print(f"   - Avg Late Bid Ratio: {archetype.get('avg_late_bid_ratio', 0):.2%}")
    
    # Safety check
    safety_result = SafetyPreFilters.run_all_checks(context)
    if safety_result['blocked']:
        print(f"\n[SAFETY BLOCK] {safety_result.get('reason')}")
        return
    
    # Try LLM first, fallback to rules if LLM fails
    print(f"\n[STRATEGY SELECTION]")
    print(f"   Attempting LLM-based strategy selection...")
    
    decision_source = "llm"
    strategy_decision = None
    
    try:
        # Initialize LLM selector
        llm_selector = LLMStrategySelector(provider="openrouter", model="openai/gpt-5.1")
        
        # Get LLM decision with market intelligence
        llm_decision = llm_selector.get_strategy_decision(context, market_intelligence=market_intel_signals)
        
        if llm_decision:
            strategy_decision = llm_decision
            print(f"   [SUCCESS] LLM generated strategy decision")
        else:
            raise Exception("LLM returned None")
            
    except Exception as e:
        # LLM failed - use rule-based fallback
        print(f"   [FALLBACK] LLM failed ({str(e)[:50]}...), using rule-based strategy")
        decision_source = "rules_fallback"
        strategy_decision = RuleBasedStrategySelector.get_strategy_decision(
            context, 
            market_intelligence=market_intel_signals
        )
    
    # Validate
    is_valid, error = StrategyValidator.validate_all(strategy_decision, context)
    
    if not is_valid:
        print(f"   [WARNING] Strategy validation failed: {error}")
        # Still proceed, but note the validation issue
    
    # Proxy logic
    proxy_result = ProxyLogicHandler.apply_proxy_logic_to_decision(context, strategy_decision)
    proxy_decision = proxy_result['proxy_decision']
    
    print(f"\n[STRATEGY DECISION]")
    print(f"   Source: {decision_source.upper()}")
    print(f"   Strategy: {strategy_decision.strategy.upper()}")
    print(f"   Recommended Bid: ${strategy_decision.recommended_bid_amount:.2f}")
    print(f"   Confidence: {strategy_decision.confidence:.2f}")
    print(f"   Risk Level: {strategy_decision.risk_level.upper()}")
    print(f"   Valid: {is_valid}")
    
    print(f"\n[PROXY ACTION]")
    print(f"   Action: {proxy_decision.proxy_action.upper().replace('_', ' ')}")
    print(f"   Current Proxy: ${context.your_current_proxy:.2f}")
    print(f"   Current Bid: ${context.current_bid:.2f}")
    if proxy_decision.should_increase_proxy:
        print(f"   New Proxy Max: ${proxy_decision.new_proxy_max:.2f}")
        if proxy_decision.next_bid_amount:
            print(f"   Next Visible Bid: ${proxy_decision.next_bid_amount:.2f}")
    
    print(f"\n[REASONING]")
    # Handle Unicode characters for Windows console
    try:
        reasoning_text = strategy_decision.reasoning.encode('ascii', 'replace').decode('ascii')
        print(f"   {reasoning_text}")
    except:
        # Fallback: print first 200 chars if encoding fails
        print(f"   {strategy_decision.reasoning[:200]}...")
    
    return {
        "scenario": scenario_name,
        "domain": domain,
        "bidder": bidder_id,
        "bidder_type": analyze_bidder_type(bidder_intel),
        "strategy": strategy_decision.strategy,
        "bid_amount": strategy_decision.recommended_bid_amount,
        "confidence": strategy_decision.confidence,
        "decision_source": decision_source
    }

def test_standalone_agent():
    """Test multiple real-world scenarios with different domains and bidders"""
    
    print("="*80)
    print("COMPREHENSIVE AGENT TEST - REAL-WORLD SCENARIOS")
    print("Testing with multiple domains and bidder profiles")
    print("="*80)
    
    # Initialize market intelligence
    market_intel = MarketIntelligenceLoader(data_dir=".")
    
    # Get multiple real domains and bidders from parquet
    domains = []
    bidders = []
    
    if len(market_intel.domain_stats) > 0:
        # Get 5 different domains
        num_domains = min(5, len(market_intel.domain_stats))
        for i in range(num_domains):
            domains.append(market_intel.domain_stats.iloc[i]["domain"])
    
    if len(market_intel.bidder_profiles) > 0:
        # Get 5 different bidders with varying characteristics
        num_bidders = min(5, len(market_intel.bidder_profiles))
        for i in range(num_bidders):
            bidders.append(market_intel.bidder_profiles.iloc[i]["bidder_name"])
    
    if not domains:
        domains = ["PremiumDomain.com", "TestDomain.net", "ExampleDomain.io"]
    if not bidders:
        bidders = [None, None, None]
    
    print(f"\nLoaded {len(domains)} domains and {len(bidders)} bidders from parquet data")
    
    # Define test scenarios
    scenarios = []
    
    # Scenario 1: High-value domain with aggressive bidder
    scenarios.append({
        "name": "High-Value Domain vs Aggressive Bidder",
        "domain": domains[0] if len(domains) > 0 else "PremiumDomain.com",
        "bidder_id": bidders[0] if len(bidders) > 0 else None,
        "params": {
            "platform": "godaddy",
            "estimated_value": 3000.0,
            "current_bid": 1200.0,
            "num_bidders": 3,
            "hours_remaining": 2.0,
            "your_current_proxy": 1100.0,
            "budget_available": 8000.0,
            "bidder_analysis": BidderAnalysis(
                bot_detected=True,
                corporate_buyer=False,
                aggression_score=9.0,
                reaction_time_avg=1.2
            )
        }
    })
    
    # Scenario 2: Medium-value domain with sniper bidder
    scenarios.append({
        "name": "Medium-Value Domain vs Sniper Bidder",
        "domain": domains[1] if len(domains) > 1 else "MediumDomain.net",
        "bidder_id": bidders[1] if len(bidders) > 1 else None,
        "params": {
            "platform": "namejet",
            "estimated_value": 500.0,
            "current_bid": 200.0,
            "num_bidders": 2,
            "hours_remaining": 0.3,  # Late stage
            "your_current_proxy": 180.0,
            "budget_available": 3000.0,
            "bidder_analysis": BidderAnalysis(
                bot_detected=False,
                corporate_buyer=False,
                aggression_score=6.0,
                reaction_time_avg=45.0
            )
        }
    })
    
    # Scenario 3: Low-value domain with proxy-heavy bidder
    scenarios.append({
        "name": "Low-Value Domain vs Proxy-Heavy Bidder",
        "domain": domains[2] if len(domains) > 2 else "LowDomain.io",
        "bidder_id": bidders[2] if len(bidders) > 2 else None,
        "params": {
            "platform": "dynadot",
            "estimated_value": 150.0,
            "current_bid": 60.0,
            "num_bidders": 1,
            "hours_remaining": 4.0,
            "your_current_proxy": 50.0,
            "budget_available": 2000.0,
            "bidder_analysis": BidderAnalysis(
                bot_detected=False,
                corporate_buyer=True,
                aggression_score=4.0,
                reaction_time_avg=120.0
            )
        } 
    })
    
    # Scenario 4: High-value volatile domain
    scenarios.append({
        "name": "High-Value Volatile Domain",
        "domain": domains[3] if len(domains) > 3 else domains[0] if len(domains) > 0 else "VolatileDomain.com",
        "bidder_id": bidders[3] if len(bidders) > 3 else bidders[0] if len(bidders) > 0 else None,
        "params": {
            "platform": "godaddy",
            "estimated_value": 2500.0,
            "current_bid": 900.0,
            "num_bidders": 5,
            "hours_remaining": 1.5,
            "your_current_proxy": 800.0,
            "budget_available": 6000.0,
            "bidder_analysis": BidderAnalysis(
                bot_detected=True,
                corporate_buyer=True,
                aggression_score=7.5,
                reaction_time_avg=2.5
            ) 
        }
    })  
    
    # Scenario 5: Early stage with no competition
    scenarios.append({
        "name": "Early Stage - No Competition",
        "domain": domains[4] if len(domains) > 4 else domains[0] if len(domains) > 0 else "EarlyDomain.biz",
        "bidder_id": None,  # No bidder yet
        "params": {
            "platform": "namejet",
            "estimated_value": 800.0,
            "current_bid": 50.0,
            "num_bidders": 0,
            "hours_remaining": 12.0,
            "your_current_proxy": 0.0,
            "budget_available": 4000.0,
            "bidder_analysis": BidderAnalysis(
                bot_detected=False,
                corporate_buyer=False,
                aggression_score=1.0,
                reaction_time_avg=300.0
            )
        }
    })
    
    # Run all scenarios
    results = []
    for scenario in scenarios:
        try:
            result = test_single_scenario(
                market_intel,
                scenario["domain"],
                scenario["bidder_id"],
                scenario["name"],
                scenario["params"]
            )
            if result:
                results.append(result)
        except Exception as e:
            print(f"\n[ERROR] in scenario '{scenario['name']}': {e}")
            import traceback
            traceback.print_exc()
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"\nTotal Scenarios Tested: {len(results)}")
    print("\nStrategy Distribution:")
    strategy_counts = {}
    for result in results:
        strategy = result["strategy" ]
        strategy_counts[strategy]  = strategy_counts.get(strategy, 0) + 1
    
    for strategy, count in strategy_counts.items():
        print(f"  - {strategy}: {count} scenario(s)")
    
    print("\nBidder Types Encountered:")
    bidder_types = {}
    for result in results:
        bidder_type = result["bidder_type"]
        bidder_types[bidder_type d] = bidder_types.get(bidder_type, 0) + 1
    
    for bidder_type, count in bidder_types.items():
        print(f"  - {bidder_type}: {count} scenario(s)")
    
    print("\n" + "="*80)
    print("ALL SCENARIOS COMPLETE")
    print("="*80   )

if __name__ == "__main__":
    test_standalone_agent()