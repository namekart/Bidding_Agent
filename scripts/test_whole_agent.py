"""
Test the whole Domain Auction Strategy Agent end-to-end.

Tests:
1. Full pipeline via LangGraph (no MySQL): market intel -> safety -> LLM/fallback -> validation -> proxy -> finalize.
2. Full pipeline via HybridStrategySelector (requires MySQL for history).

Run: python test_whole_agent.py
Set MYSQL_CONFIG or pass --mysql to test with HybridStrategySelector; otherwise tests via graph only.
"""
import os
import sys
from typing import Optional, Dict, Any

from app.core.models import AuctionContext, BidderAnalysis, FinalDecision
from app.services.market_intelligence import MarketIntelligenceLoader
from app.agent.strategy_graph import create_strategy_graph
from app.core.models import AuctionState


def make_context(
    domain: str = "BudgetGone.xyz",
    platform: str = "dynadot",
    estimated_value: float = 300.0,
    current_bid: float = 60.0,
    num_bidders: int = 1,
    hours_remaining: float = 10.0,
    your_current_proxy: float = 0.0,
    budget_available: float = 75.0,
    aggression_score: float = 1.5,
    reaction_time_avg: float = 150.0,
    bot_detected: bool = False,
    corporate_buyer: bool = False,
) -> AuctionContext:
    """Build an AuctionContext for testing."""
    return AuctionContext(
        domain=domain,
        platform=platform,
        estimated_value=estimated_value,
        current_bid=current_bid,
        num_bidders=num_bidders,
        hours_remaining=hours_remaining,
        your_current_proxy=your_current_proxy,
        budget_available=budget_available,
        bidder_analysis=BidderAnalysis(
            bot_detected=bot_detected,
            corporate_buyer=corporate_buyer,
            aggression_score=aggression_score,
            reaction_time_avg=reaction_time_avg,
        ),
    )


def test_whole_agent_via_graph(
    data_dir: str = ".",
    llm_provider: str = "openrouter",
    llm_model: str = "openai/gpt-5.1",
    context: Optional[AuctionContext] = None,
) -> Dict[str, Any]:
    """
    Test the full agent by running the LangGraph with pre-built state (no MySQL).
    Uses market intelligence enrichment and empty historical_context.
    """
    context = context or make_context()
    loader = MarketIntelligenceLoader(data_dir=data_dir)
    last_bidder_id = None

    # Enrich context (market intel with pattern fallbacks)
    market_intel = loader.enrich_context(context, last_bidder_id=last_bidder_id)
    historical_context = {}  # No MySQL

    initial_state: AuctionState = {
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
    decision_source = result_state.get("decision_source")
    blocked = result_state.get("blocked", False)

    if not final_decision_dict:
        return {
            "ok": False,
            "error": "No final_decision in state",
            "state": result_state,
        }

    try:
        final_decision = FinalDecision(**final_decision_dict)
    except Exception as e:
        return {
            "ok": False,
            "error": f"Invalid final_decision: {e}",
            "final_decision_dict": final_decision_dict,
        }

    return {
        "ok": True,
        "blocked": blocked,
        "decision_source": decision_source,
        "final_decision": final_decision,
        "market_intel_keys": list(market_intel.keys()),
    }


def test_whole_agent_via_selector(
    context: AuctionContext,
    mysql_config: Dict[str, Any],
    data_dir: str = ".",
    llm_provider: str = "openrouter",
    model: str = "openai/gpt-5.1",
) -> FinalDecision:
    """Test the full agent via HybridStrategySelector.select_strategy (requires MySQL)."""
    from app.agent.hybrid_strategy_selector import HybridStrategySelector

    selector = HybridStrategySelector(
        llm_provider=llm_provider,
        model=model,
        enable_fallback=True,
        mysql_config=mysql_config,
        data_dir=data_dir,
    )
    return selector.select_strategy(context)


def run_tests():
    """Run whole-agent tests and print results."""
    print("=" * 80)
    print("WHOLE AGENT TEST - Domain Auction Strategy Agent")
    print("=" * 80)

    data_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(data_dir, "layer0_domain_stats.parquet")):
        print("[WARN] Parquet files not found in current directory. Use data_dir=... if needed.")
    else:
        print("[OK] Parquet data directory:", data_dir)

    # --- Test 1: Full pipeline via graph (no MySQL) ---
    print("\n" + "-" * 80)
    print("TEST 1: Full pipeline via LangGraph (market intel -> safety -> LLM/fallback -> proxy -> finalize)")
    print("-" * 80)

    # Use budget >= safety minimum so pipeline reaches LLM (safety rule is in agent, not hardcoded here)
    try:
        result = test_whole_agent_via_graph(
            data_dir=data_dir,
            context=make_context(budget_available=150.0),
        )
        if not result.get("ok"):
            print("[FAIL]", result.get("error", "Unknown error"))
            if "state" in result:
                print("  state keys:", list(result["state"].keys()) if result["state"] else None)
            if "final_decision_dict" in result:
                print("  final_decision_dict:", result["final_decision_dict"])
        else:
            fd = result["final_decision"]
            print("[OK] Final decision produced")
            print("  Strategy:", fd.strategy)
            print("  Recommended bid:", fd.recommended_bid_amount)
            print("  Decision source:", fd.decision_source)
            print("  Confidence:", fd.confidence)
            print("  Risk level:", fd.risk_level)
            print("  Market intel keys in state:", result.get("market_intel_keys", []))
            if fd.reasoning:
                print("  Reasoning (first 200 chars):", (fd.reasoning or "")[:200] + "...")
    except Exception as e:
        print("[FAIL] Exception:", e)
        import traceback
        traceback.print_exc()

    # --- Test 2: Multiple scenarios via graph ---
    print("\n" + "-" * 80)
    print("TEST 2: Multiple scenarios (unknown domain, unknown bidder, different platforms)")
    print("-" * 80)

    # Scenarios use budget >= safety minimum so LLM path is exercised (no hardcoding of agent rules)
    scenarios = [
        ("BudgetGone.xyz", make_context(domain="BudgetGone.xyz", budget_available=150.0)),
        ("PremiumDomain.com, high value", make_context(domain="PremiumDomain.com", estimated_value=3000.0, budget_available=8000.0)),
        ("Early stage, 1 bidder", make_context(num_bidders=1, current_bid=50.0, hours_remaining=12.0, budget_available=500.0)),
    ]
    for name, ctx in scenarios:
        try:
            r = test_whole_agent_via_graph(data_dir=data_dir, context=ctx)
            status = "[OK]" if r.get("ok") else "[FAIL]"
            fd = r.get("final_decision")
            src = getattr(fd, "decision_source", None) if fd else r.get("error", "?")
            print(f"  {name}: {status} source={src}")
        except Exception as e:
            print(f"  {name}: [FAIL] {e}")

    # --- Test 3: Via HybridStrategySelector (only if MySQL config available) ---
    mysql_config = None
    if os.getenv("MYSQL_HOST") and os.getenv("MYSQL_DATABASE"):
        mysql_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE"),
        }
    if mysql_config:
        print("\n" + "-" * 80)
        print("TEST 3: Full pipeline via HybridStrategySelector (MySQL)")
        print("-" * 80)
        try:
            decision = test_whole_agent_via_selector(make_context(), mysql_config=mysql_config, data_dir=data_dir)
            print("[OK] select_strategy returned:", decision.strategy, decision.recommended_bid_amount, decision.decision_source)
        except Exception as e:
            print("[FAIL]", e)
    else:
        print("\n[SKIP] TEST 3 (HybridStrategySelector): Set MYSQL_HOST, MYSQL_DATABASE, etc. to run.")

    print("\n" + "=" * 80)
    print("WHOLE AGENT TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()