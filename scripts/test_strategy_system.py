"""
Test Script for Domain Auction Strategy System
Demonstrates the complete multi-agent system with various auction scenarios.

Runs the whole agent WITHOUT MySQL by driving the LangGraph directly
(market intel -> safety -> LLM/fallback -> validation -> proxy -> finalize).
"""
import os
import json
from typing import Dict, Any, Optional, List
from app.core.models import AuctionContext, BidderAnalysis, FinalDecision
from app.services.market_intelligence import MarketIntelligenceLoader
from app.agent.strategy_graph import create_strategy_graph


# Default LLM config (no MySQL required)
DEFAULT_LLM_PROVIDER = "openrouter"
DEFAULT_LLM_MODEL = "openai/gpt-5.1"
DEFAULT_DATA_DIR = "."


def run_agent_via_graph(
    context: AuctionContext,
    data_dir: str = DEFAULT_DATA_DIR,
    llm_provider: str = DEFAULT_LLM_PROVIDER,
    llm_model: str = DEFAULT_LLM_MODEL,
    last_bidder_id: Optional[str] = None,
) -> FinalDecision:
    """
    Run the full agent pipeline via LangGraph without MySQL.
    Uses market intelligence enrichment and empty historical_context.
    Pass last_bidder_id (bidder name or ID from parquet) to look up bidder profile.
    """
    loader = MarketIntelligenceLoader(data_dir=data_dir)
    market_intel = loader.enrich_context(context, last_bidder_id=last_bidder_id)
    historical_context = {}

    initial_state = {
        "auction_context": context.model_dump(),
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "historical_context": historical_context,
        "market_intelligence": market_intel,
        "blocked": False,
        "block_reason": None,
        "llm_decision": None,
        "llm_valid": False,
        "llm_validation_reason": None,
        "rule_decision": None,
        "proxy_analysis": None,
        "final_decision": None,
        "decision_source": None,
    }

    graph = create_strategy_graph()
    result_state = graph.invoke(initial_state)
    final_decision_dict = result_state.get("final_decision")
    if not final_decision_dict:
        raise ValueError("No final_decision in state")
    return FinalDecision(**final_decision_dict)


def get_bidder_ids_from_parquet(data_dir: str = DEFAULT_DATA_DIR, max_bidders: int = 20) -> List[str]:
    """
    Load bidder names/IDs from layer0_bidder_profiles.parquet for use in tests.
    Returns list of bidder identifiers (index = bidder_id or bidder_name from parquet).
    """
    try:
        loader = MarketIntelligenceLoader(data_dir=data_dir)
        index = loader.bidder_profiles_indexed.index
        ids = list(index)[:max_bidders] if len(index) > 0 else []
        return ids
    except Exception:
        return []


def build_scenario_bidders(
    scenario_names: List[str],
    bidder_ids: List[str],
) -> Dict[str, Optional[str]]:
    """
    Build explicit mapping: scenario_name -> bidder_id (from parquet).
    Each scenario gets a real bidder_id so we test bidder profile lookup and LLM decisions.
    """
    if not bidder_ids:
        return {name: None for name in scenario_names}
    return {
        name: bidder_ids[i % len(bidder_ids)]
        for i, name in enumerate(scenario_names)
    }


def create_test_scenarios() -> Dict[str, AuctionContext]:
    """Create test scenarios covering different auction situations."""

    scenarios = {}

    # SCENARIO 1: High-value domain with bot detection
    scenarios["high_value_with_bots"] = AuctionContext(
        domain="PremiumDomain.com",
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

    # SCENARIO 2: Low-value domain with no bidders (closeout opportunity)
    scenarios["low_value_no_bidders"] = AuctionContext(
        domain="CheapDomain.net",
        platform="namejet",
        estimated_value=75.0,
        current_bid=15.0,
        num_bidders=0,
        hours_remaining=0.5,
        your_current_proxy=0.0,
        budget_available=2000.0,
        bidder_analysis=BidderAnalysis(
            bot_detected=False,
            corporate_buyer=False,
            aggression_score=1.0,
            reaction_time_avg=120.0
        )
    )

    # SCENARIO 3: Outbid scenario - safe max below current bid
    scenarios["outbid_scenario_loss"] = AuctionContext(
        domain="ValuableSite.org",
        platform="godaddy",
        estimated_value=200.0,
        current_bid=160.0,  # Safe max = 140, so cannot profitably continue
        num_bidders=3,
        hours_remaining=1.0,
        your_current_proxy=120.0,
        budget_available=1000.0,
        bidder_analysis=BidderAnalysis(
            bot_detected=False,
            corporate_buyer=True,
            aggression_score=6.0,
            reaction_time_avg=25.0
        )
    )

    # SCENARIO 4: Outbid scenario - can increase proxy
    scenarios["outbid_scenario_increase"] = AuctionContext(
        domain="GoodDomain.io",
        platform="dynadot",
        estimated_value=1000.0,
        current_bid=650.0,  # Safe max = 700, so can increase
        num_bidders=2,
        hours_remaining=3.0,
        your_current_proxy=600.0,
        budget_available=3000.0,
        bidder_analysis=BidderAnalysis(
            bot_detected=False,
            corporate_buyer=False,
            aggression_score=5.0,
            reaction_time_avg=45.0
        )
    )

    # SCENARIO 5: Safety block - overpayment protection
    scenarios["safety_block_overpayment"] = AuctionContext(
        domain="ExpensiveDomain.com",
        platform="godaddy",
        estimated_value=1000.0,
        current_bid=1350.0,  # 135% of value - overpayment zone
        num_bidders=5,
        hours_remaining=4.0,
        your_current_proxy=0.0,
        budget_available=5000.0,
        bidder_analysis=BidderAnalysis(
            bot_detected=False,
            corporate_buyer=True,
            aggression_score=9.0,
            reaction_time_avg=15.0
        )
    )

    # SCENARIO 6: Safety block - portfolio concentration
    scenarios["safety_block_concentration"] = AuctionContext(
        domain="MegaDomain.biz",
        platform="namejet",
        estimated_value=4500.0,  # 90% of $5000 budget
        current_bid=500.0,
        num_bidders=1,
        hours_remaining=12.0,
        your_current_proxy=0.0,
        budget_available=5000.0,
        bidder_analysis=BidderAnalysis(
            bot_detected=False,
            corporate_buyer=False,
            aggression_score=3.0,
            reaction_time_avg=180.0
        )
    )
    
    # SCENARIO 7: Medium-value with GoDaddy timing (5-min extension)
    scenarios["medium_godaddy_timing"] = AuctionContext(
        domain="SolidDomain.co",
        platform="godaddy",
        estimated_value=350.0,
        current_bid=120.0,
        num_bidders=3,
        hours_remaining=0.8,  # < 1 hour, GoDaddy extension zone
        your_current_proxy=0.0,
        budget_available=2000.0,
        bidder_analysis=BidderAnalysis(
            bot_detected=False,
            corporate_buyer=False,
            aggression_score=4.0,
            reaction_time_avg=60.0
        )
    )

    scenarios["medium_namejet_timing"] = AuctionContext(
        domain="Thecofffeeshop.com",
        platform= "namejet",
        estimated_value=250.0,
        current_bid=75.0,
        num_bidders=2,
        hours_remaining=0.6,
        your_current_proxy=50.0,
        budget_available=2500.0,
        bidder_analysis=BidderAnalysis(
            bot_detected=False,
            corporate_buyer=False,
            aggression_score=4.0,
            reaction_time_avg=60.0
        )
    )

    scenarios["late_snipe_high_aggression"] = AuctionContext(
        domain="HotDrop.io",
        platform="godaddy",
        estimated_value=1800,
        current_bid=950.0,
        num_bidders=3,
        hours_remaining=0.2,
        your_current_proxy=900.0,
        budget_available=4000.0,
        bidder_analysis=BidderAnalysis(
            bot_detected= True,
            corporate_buyer=False,
            aggression_score=9.2,
            reaction_time_avg=5.0
        )
    )

    scenarios["budget_pinched_premium"]= AuctionContext(
        domain="CategoryLeader.com",
        platform="godaddy",
        estimated_value=6000.0,
        current_bid=3100,
        num_bidders=2,
        hours_remaining=4.0,
        your_current_proxy=0.0,
        budget_available=3600.0,
        bidder_analysis=BidderAnalysis(
            bot_detected=False,
            corporate_buyer=True,
            aggression_score=8.5,
            reaction_time_avg=18.0
        )
    )

    scenarios["dynadot_increment_edge"] = AuctionContext(
        domain="ExactMatch.ai",
        platform="dynadot",
        estimated_value=900.0,
        current_bid=560.0,
        num_bidders=2,
        hours_remaining=6.0,
        your_current_proxy=540.0,
        budget_available=2000.0,
        bidder_analysis=BidderAnalysis(
            bot_detected=False,
            corporate_buyer=False,
            aggression_score=4.5,
            reaction_time_avg=70.0
        )
    )

    scenarios["namejet_flash_close"]=AuctionContext(
        domain="QuickFlip.net",
        platform="namejet",
        estimated_value=450.0,
        current_bid=150.0,
        num_bidders=1,
        hours_remaining=0.05,
        your_current_proxy=140.0,
        budget_available=1500.0,
        bidder_analysis=BidderAnalysis(
            bot_detected=False,
            corporate_buyer=False,
            aggression_score=2.5,
            reaction_time_avg=200.0
        )
    )

    scenarios["safety_block_low_budget"]=AuctionContext(
        domain="BudgetGone.xyz",
        platform="dynadot",
        estimated_value=300.0,
        current_bid=60.0,
        num_bidders=1,
        hours_remaining=10.0,
        your_current_proxy=0.0,
        budget_available=75.0,
        bidder_analysis=BidderAnalysis(
            bot_detected=False,
            corporate_buyer=False,
            aggression_score=1.5,
            reaction_time_avg=150.0
        )
    )
    scenarios["portfolio_concentration_block"] = AuctionContext(
        domain="SingleBet.org",
        platform="godaddy",
        estimated_value=2200.0,
        current_bid=400.0,
        num_bidders=2,
        hours_remaining=11.0,
        your_current_proxy=0.0,
        budget_available=3800.0,
        bidder_analysis=BidderAnalysis(
            bot_detected=False,
            corporate_buyer=True,
            aggression_score=7.0,
            reaction_time_avg=30.0
        )
    )
    scenarios["stagnant_market_probe"] = AuctionContext(
        domain="SlowMover.biz",
        platform="namejet",
        estimated_value=320.0,
        current_bid=35.0,
        num_bidders=0,
        hours_remaining=26.0,
        your_current_proxy=0.0,
        budget_available=1200.0,
        bidder_analysis=BidderAnalysis(
            bot_detected=False,
            corporate_buyer=False,
            aggression_score=0.5,
            reaction_time_avg=400.0
        )
    )

    return scenarios


def print_decision_summary(
    scenario_name: str,
    context: AuctionContext,
    decision: Dict[str, Any],
    opponent_bidder_id: Optional[str] = None,
):
    """Print a formatted summary of the decision."""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario_name.upper()}")
    print(f"{'='*80}")

    if opponent_bidder_id is not None:
        print(f"Opponent bidder_id (from parquet): {opponent_bidder_id}")
    print(f"Domain: {context.domain}")
    print(f"Platform: {context.platform.upper()}")
    print(f"Value: ${context.estimated_value:.2f} | Current Bid: ${context.current_bid:.2f}")
    print(f"Bidders: {context.num_bidders} | Hours Left: {context.hours_remaining:.1f}")
    print(f"Your Proxy: ${context.your_current_proxy:.2f} | Budget: ${context.budget_available:.2f}")
    print(f"Bot Detected: {context.bidder_analysis['bot_detected']}")

    print(f"\nSTRATEGY DECISION:")
    print(f"Strategy: {decision['strategy']}")
    print(f"Recommended Bid: ${decision['recommended_bid_amount']:.2f}")
    print(f"Should Increase Proxy: {decision['should_increase_proxy']}")
    if decision['next_bid_amount']:
        print(f"Next Bid Amount: ${decision['next_bid_amount']:.2f}")
    print(f"Max Budget for Domain: ${decision['max_budget_for_domain']:.2f}")
    print(f"Risk Level: {decision['risk_level']} | Confidence: {decision['confidence']:.2f}")
    print(f"Decision Source: {decision['decision_source']}")

    if decision['proxy_decision']:
        proxy = decision['proxy_decision']
        print(f"\nPROXY ANALYSIS:")
        print(f"Current Proxy: ${proxy['current_proxy']:.2f} | Current Bid: ${proxy['current_bid']:.2f}")
        print(f"Safe Max: ${proxy['safe_max']:.2f}")
        print(f"Proxy Action: {proxy['proxy_action']}")
        if proxy['should_increase_proxy'] and proxy['new_proxy_max']:
            print(f"New Proxy Max: ${proxy['new_proxy_max']:.2f}")
        print(f"Explanation: {proxy['explanation']}")

    print(f"\nREASONING:")
    print(f"{decision['reasoning']}")


def run_performance_test(
    scenarios: Dict[str, AuctionContext],
    data_dir: str = DEFAULT_DATA_DIR,
    scenario_bidders: Optional[Dict[str, Optional[str]]] = None,
):
    """Run performance testing across all scenarios (no MySQL). Uses scenario -> bidder_id mapping for bidder profile lookup."""
    print(f"\n{'='*80}")
    print("PERFORMANCE TEST RESULTS")
    print(f"{'='*80}")

    total = 0
    llm_success = 0
    fallback_count = 0
    safety_block_count = 0
    bidders = scenario_bidders or {}

    for scenario_name, context in scenarios.items():
        last_bidder_id = bidders.get(scenario_name) if bidders else None
        try:
            decision = run_agent_via_graph(
                context, data_dir=data_dir, last_bidder_id=last_bidder_id
            )
            total += 1
            src = decision.decision_source or "unknown"
            if src == "llm":
                llm_success += 1
            elif src == "rules_fallback":
                fallback_count += 1
            elif src == "safety_block":
                safety_block_count += 1
            print(f"{scenario_name}: ✓ SUCCESS (source={src})")
        except Exception as e:
            print(f"{scenario_name}: ✗ FAILED: {e}")

    print(f"\n{'='*80}")
    print("OVERALL PERFORMANCE STATS")
    print(f"{'='*80}")
    print(f"Total Decisions: {total}")
    if total > 0:
        print(f"LLM Success Rate: {llm_success / total:.1%}")
        print(f"Fallback Rate: {fallback_count / total:.1%}")
        print(f"Safety Block Rate: {safety_block_count / total:.1%}")


def main():
    """Main test execution (no MySQL required)."""
    print("DOMAIN AUCTION STRATEGY SYSTEM - TEST SUITE")
    print("Testing multi-agent LangGraph system with hybrid AI decision making")
    print("(Running via graph only - no MySQL required)\n")

    data_dir = DEFAULT_DATA_DIR
    scenarios = create_test_scenarios()
    bidder_ids = get_bidder_ids_from_parquet(data_dir=data_dir, max_bidders=20)
    scenario_bidders = build_scenario_bidders(list(scenarios.keys()), bidder_ids)

    if scenario_bidders and any(scenario_bidders.get(n) for n in scenario_bidders):
        print("Scenario -> Bidder ID (from parquet, for bidder profile lookup):")
        for name, bid in scenario_bidders.items():
            print(f"  {name}: {bid or '(none)'}")
        print()
    else:
        print("No bidders found in parquet; scenarios will run with last_bidder_id=None.\n")

    # Run detailed analysis for each scenario using graph (no selector/MySQL)
    for scenario_name, context in scenarios.items():
        last_bidder_id = scenario_bidders.get(scenario_name)
        try:
            decision = run_agent_via_graph(
                context, data_dir=data_dir, last_bidder_id=last_bidder_id
            )
            print_decision_summary(
                scenario_name, context, decision.model_dump(),
                opponent_bidder_id=last_bidder_id,
            )
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"SCENARIO: {scenario_name.upper()}")
            print(f"{'='*80}")
            print(f"ERROR: {e}")

    # Run performance summary
    run_performance_test(scenarios, data_dir=data_dir, scenario_bidders=scenario_bidders)

    print(f"\n{'='*80}")
    print("TEST SUITE COMPLETED")
    print(f"{'='*80}")
    print("\nKey Features Demonstrated:")
    print("✓ Safety pre-filters (overpayment, concentration, budget)")
    print("✓ LLM-based strategy reasoning with structured prompts")
    print("✓ Validation and rule-based fallback")
    print("✓ Proxy bidding logic for outbid scenarios")
    print("✓ Platform-specific rules (GoDaddy extensions)") 
    print("✓ Multi-agent LangGraph orchestration")
    print("✓ Comprehensive decision explanations")


if __name__ == "__main__":
    main()

