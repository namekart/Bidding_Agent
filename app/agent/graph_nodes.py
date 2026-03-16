"""
LangGraph Nodes for the Domain Auction Strategy System
Each node represents a processing step in the decision pipeline.
"""
from typing import Dict, Any
from ..core.models import AuctionState, AuctionContext, StrategyDecision
from ..core.safety_filters import SafetyPreFilters
from .llm_strategy import LLMStrategySelector
from ..core.validation import StrategyValidator
from .rule_based_strategy import RuleBasedStrategySelector
from .proxy_logic import ProxyLogicHandler


def safety_prefilter_node(state: AuctionState) -> AuctionState:
    """
    Layer 1: Safety Pre-Filters
    Checks hard constraints before allowing any bidding strategy.
    If blocked, sets final decision and prevents further processing.
    """
    context = AuctionContext(**state["auction_context"])

    # Run all safety checks
    safety_result = SafetyPreFilters.run_all_checks(context)

    # Update state with safety check results
    state["blocked"] = safety_result["blocked"]
    state["block_reason"] = safety_result.get("reason")

    # If blocked, populate final decision and mark as safety block
    if safety_result["blocked"]:
        state["final_decision"] = {
            "strategy": safety_result.get("strategy", "do_not_bid"),
            "recommended_bid_amount": safety_result.get("recommended_bid_amount", 0.0),
            "should_increase_proxy": False,
            "next_bid_amount": None,
            "max_budget_for_domain": 0.0,
            "risk_level": safety_result.get("risk_level", "high"),
            "confidence": safety_result.get("confidence", 0.95),
            "reasoning": safety_result.get("reason", "Safety block activated"),
            "proxy_decision": None,
            "decision_source": "safety_block"
        }
        state["decision_source"] = "safety_block"

    return state


def llm_strategy_node(state: AuctionState) -> AuctionState:
    """
    Layer 2: LLM-Based Strategy Reasoning
    Only runs if not blocked
    Calls LLM with configurable provider
    """
    if state.get("blocked", False):
        return state  # Skip if blocked

    context = AuctionContext(**state["auction_context"])

    # Get provider and model from state, with defaults
    provider = state.get("llm_provider", "openrouter")
    model = state.get("llm_model", "openai/gpt-5.1")

    # Get market intelligence and historical context from state
    market_intelligence = state.get("market_intelligence")
    historical_context = state.get("historical_context") or {}

    # Initialize LLM selector with configurable provider
    llm_selector = LLMStrategySelector(provider=provider, model=model)

    # Get LLM decision (include same-auction previous attempts when thread_id is set)
    llm_decision = llm_selector.get_strategy_decision(
        context,
        market_intelligence=market_intelligence,
        historical_context=historical_context,
    )

    if llm_decision:
        # Convert to dict for state storage
        state["llm_decision"] = llm_decision.dict()
    else:
        # LLM failed - mark as invalid
        state["llm_decision"] = None
        state["llm_valid"] = False
        state["llm_validation_reason"] = "LLM call failed or returned invalid response"

    return state


def llm_validation_node(state: AuctionState) -> AuctionState:
    """
    Layer 3: LLM Decision Validation
    Validates LLM strategy against hard rules.
    If invalid, will trigger fallback to rules.
    """
    if state.get("blocked", False):
        return state  # Skip if blocked

    llm_decision_dict = state.get("llm_decision")
    if not llm_decision_dict:
        state["llm_valid"] = False
        state["llm_validation_reason"] = "No LLM decision available"
        return state

    # Convert back to StrategyDecision object
    try:
        llm_decision = StrategyDecision(**llm_decision_dict)
    except Exception as e:
        state["llm_valid"] = False
        state["llm_validation_reason"] = f"Failed to parse LLM decision: {e}"
        return state

    context = AuctionContext(**state["auction_context"])

    # Validate the decision
    is_valid, error_message = StrategyValidator.validate_all(llm_decision, context)

    state["llm_valid"] = is_valid
    state["llm_validation_reason"] = error_message

    return state


def rule_fallback_node(state: AuctionState) -> AuctionState:
    """
    Rule-Based Fallback Strategy
    Used when LLM validation fails.
    Provides deterministic, rule-based strategy selection.
    """
    if state.get("blocked", False):
        return state  # Skip if blocked

    context = AuctionContext(**state["auction_context"])

    # Get market intelligence from state
    market_intelligence = state.get("market_intelligence")


    # Get rule-based decision
    rule_decision = RuleBasedStrategySelector.get_strategy_decision(context, market_intelligence = market_intelligence)

    # Store as dict
    state["rule_decision"] = rule_decision.dict()

    return state


def proxy_logic_node(state: AuctionState) -> AuctionState:
    """
    Layer 4: Proxy/Outbid Analysis
    Applies proxy bidding logic to the chosen strategy.
    Determines if proxy should be increased, next bid amounts, etc.
    """
    if state.get("blocked", False):
        return state  # Skip if blocked

    context = AuctionContext(**state["auction_context"])

    # Determine which strategy decision to use
    if state.get("llm_valid", False) and state.get("llm_decision"):
        # Use validated LLM decision
        strategy_dict = state["llm_decision"]
        decision_source = "llm"
    elif state.get("rule_decision"):
        # Use rule-based fallback
        strategy_dict = state["rule_decision"]
        decision_source = "rules_fallback"
    else:
        # No valid strategy available - should not happen
        state["proxy_analysis"] = None
        return state

    # Convert to StrategyDecision object
    try:
        strategy_decision = StrategyDecision(**strategy_dict)
    except Exception as e:
        state["proxy_analysis"] = None
        return state

    # Apply proxy logic
    proxy_result = ProxyLogicHandler.apply_proxy_logic_to_decision(context, strategy_decision)

    # Store results
    state["proxy_analysis"] = {
        "strategy_decision": proxy_result["strategy_decision"].dict(),
        "proxy_decision": proxy_result["proxy_decision"].dict()
    }
    state["decision_source"] = decision_source

    return state


def finalize_node(state: AuctionState) -> AuctionState:
    """
    Final Decision Assembly
    Combines all analysis into final decision output.
    Formats the complete response for the user.
    """
    if state.get("blocked", False):
        # Already have final decision from safety node
        return state

    proxy_analysis = state.get("proxy_analysis")
    if not proxy_analysis:
        # Fallback: create a safe do_not_bid decision
        state["final_decision"] = {
            "strategy": "do_not_bid",
            "recommended_bid_amount": 0.0,
            "should_increase_proxy": False,  
            "next_bid_amount": None,
            "max_budget_for_domain": 0.0,
            "risk_level": "high",
            "confidence": 0.0,
            "reasoning": "System error: No valid strategy or proxy analysis available",
            "proxy_decision": None,
            "decision_source": "system_error"
        }
        state["decision_source"] = "system_error"
        return state

    # Extract components
    strategy_decision_dict = proxy_analysis["strategy_decision"]
    proxy_decision_dict = proxy_analysis["proxy_decision"]

    # Build final decision
    final_decision = {
        "strategy": strategy_decision_dict["strategy"],
        "recommended_bid_amount": strategy_decision_dict["recommended_bid_amount"],
        "should_increase_proxy": strategy_decision_dict["should_increase_proxy"],
        "next_bid_amount": strategy_decision_dict["next_bid_amount"],
        "max_budget_for_domain": strategy_decision_dict["max_budget_for_domain"],
        "risk_level": strategy_decision_dict["risk_level"],
        "confidence": strategy_decision_dict["confidence"],
        "reasoning": strategy_decision_dict["reasoning"],
        "proxy_decision": proxy_decision_dict,
        "decision_source": state.get("decision_source", "unknown")
    }

    state["final_decision"] = final_decision

    return state