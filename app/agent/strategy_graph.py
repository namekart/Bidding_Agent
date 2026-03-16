"""
LangGraph Strategy Graph
Wires together all decision nodes with conditional flow control.
"""
from typing import Literal
from langgraph.graph import StateGraph, END
from ..core.models import AuctionState
from .graph_nodes import (
    safety_prefilter_node,
    llm_strategy_node,
    llm_validation_node,
    rule_fallback_node,
    proxy_logic_node,
    finalize_node
)


def create_strategy_graph():
    """
    Create and configure the LangGraph for domain auction strategy selection.

    Flow:
    safety_prefilter_node -> (if blocked) -> finalize_node -> END
                          -> (if not blocked) -> llm_strategy_node -> llm_validation_node
                                                                   -> (if valid) -> proxy_logic_node
                                                                   -> (if invalid) -> rule_fallback_node -> proxy_logic_node
                                                                                  -> finalize_node -> END
    """

    # Initialize the StateGraph
    workflow = StateGraph(AuctionState)

    # Add all nodes
    workflow.add_node("safety_prefilter", safety_prefilter_node)
    workflow.add_node("llm_strategy", llm_strategy_node)
    workflow.add_node("llm_validation", llm_validation_node)
    workflow.add_node("rule_fallback", rule_fallback_node)
    workflow.add_node("proxy_logic", proxy_logic_node)
    workflow.add_node("finalize", finalize_node)

    # Define conditional routing functions
    def safety_check_router(state: AuctionState) -> Literal["finalize", "llm_strategy"]:
        """Route based on safety pre-filter result."""
        return "finalize" if state.get("blocked", False) else "llm_strategy"

    def validation_router(state: AuctionState) -> Literal["proxy_logic", "rule_fallback"]:
        """Route based on LLM validation result."""
        return "proxy_logic" if state.get("llm_valid", False) else "rule_fallback"

    # Add conditional edges
    workflow.add_conditional_edges(
        "safety_prefilter",
        safety_check_router,
        {
            "finalize": "finalize",
            "llm_strategy": "llm_strategy"
        }
    )

    workflow.add_edge("llm_strategy", "llm_validation")

    workflow.add_conditional_edges(
        "llm_validation",
        validation_router,
        {
            "proxy_logic": "proxy_logic",
            "rule_fallback": "rule_fallback"
        }
    )

    workflow.add_edge("rule_fallback", "proxy_logic")
    workflow.add_edge("proxy_logic", "finalize")
    workflow.add_edge("finalize", END)

    # Set entry point
    workflow.set_entry_point("safety_prefilter")

    # Compile the graph
    return workflow.compile()

