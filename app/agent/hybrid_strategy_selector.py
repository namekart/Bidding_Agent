"""
Hybrid Strategy Selector - Main Interface
Production-grade multi-agent system for domain auction bidding strategy.
"""
import os
from datetime import datetime
from typing import Dict, Any, Optional
from ..core.models import AuctionContext, FinalDecision
from ..history.storage import AuctionHistoryStorage
from ..history.learning import HistoricalLearning
from ..history.models import AuctionOutcome, AuctionRoundRecord
from .strategy_graph import create_strategy_graph
from ..services.market_intelligence import MarketIntelligenceLoader


class HybridStrategySelector:
    """
    Hybrid strategy selector combining safety filters, LLM reasoning, validation,
    rule-based fallbacks, and proxy logic in a LangGraph multi-agent system.

    Provides a single select_strategy() method that orchestrates the entire decision pipeline.
    """

    def __init__(
        self,
        llm_provider: str = "openrouter",
        model: str = "openai/gpt-5.1",
        enable_fallback: bool = True,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        data_dir: str = "."
    ):
        """
        Initialize the strategy selector.

        Args:
            llm_provider: "anthropic" or "openai"
            model: Specific model name
            enable_fallback: Whether to use rule-based fallback if LLM fails
            supabase_url: Supabase project URL (e.g. https://xxx.supabase.co)
            supabase_key: Supabase service role key (for server-side access)
                         If None, will use environment variables SUPABASE_URL and SUPABASE_KEY
        """
        self.llm_provider = llm_provider
        self.model = model
        self.enable_fallback = enable_fallback

        # Set environment variables for LLM access
        self._configure_llm_access()

        # Compile the LangGraph
        self.strategy_graph = create_strategy_graph()


        # Initialize historical learning with Supabase
        try:
            self.history_storage = AuctionHistoryStorage(
                supabase_url=supabase_url,
                supabase_key=supabase_key
            )
        except ValueError as e:
            print(f"Warning: Could not initialize history storage: {e}")
            print("History features will not be available. Set SUPABASE_URL and SUPABASE_KEY environment variables.")
            self.history_storage = None

        # Initialize learning only if storage is available
        if self.history_storage:
            self.learning = HistoricalLearning(self.history_storage)
        else:
            self.learning = None

        self.market_intelligence = MarketIntelligenceLoader(data_dir=data_dir)


        # Performance tracking
        self.total_decisions = 0
        self.llm_success_count = 0
        self.fallback_count = 0
        self.safety_block_count = 0

    def _configure_llm_access(self):
        """Configure LLM API access."""
        # Set up API keys from environment
        if self.llm_provider == "anthropic":
            if not os.getenv("ANTHROPIC_API_KEY"):
                print("Warning: ANTHROPIC_API_KEY not set. LLM features will fail.")
        elif self.llm_provider == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                print("Warning: OPENAI_API_KEY not set. LLM features will fail.")

    def select_strategy(self, auction_context: AuctionContext) -> FinalDecision:
        """
        Main entry point: Select optimal bidding strategy for domain auction.

        Args:
            auction_context: Complete auction context information

        Returns:
            FinalDecision: Structured decision with strategy, reasoning, and proxy details
        """

        last_bidder_id = None 

        market_intel = self.market_intelligence.enrich_context(
            auction_context,
            last_bidder_id=last_bidder_id
        )

        # Get historical context if learning is available
        if self.learning:
            historical_context = self.learning.get_historical_context(auction_context)
        else:
            historical_context = {}
        # Validate input
        if not isinstance(auction_context, AuctionContext):
            raise ValueError("auction_context must be an AuctionContext instance")

        

        # Prepare initial state with LLM configuration
        initial_state = {
            "auction_context": auction_context.dict(),
            "llm_provider": self.llm_provider,  # Add provider to state
            "llm_model": self.model,   
            
            "historical_context": historical_context,
            "market_intelligence": market_intel,        # Add model to state

            # Pre-filter outputs
            "blocked": False,
            "block_reason": None,

            # LLM decision
            "llm_decision": None,
            "llm_valid": False,
            "llm_validation_reason": None,

            # Rule-based fallback
            "rule_decision": None,

            # Proxy analysis
            "proxy_analysis": None,

            # Final output
            "final_decision": None,
            "decision_source": None
        }

        # Execute the strategy graph
        try:
            result_state = self.strategy_graph.invoke(initial_state)

            # Update performance metrics
            self.total_decisions += 1
            decision_source = result_state.get("decision_source")
            if decision_source == "llm":
                self.llm_success_count += 1
            elif decision_source == "rules_fallback":
                self.fallback_count += 1
            elif decision_source == "safety_block":
                self.safety_block_count += 1

            # Extract and validate final decision
            final_decision_dict = result_state.get("final_decision")
            if not final_decision_dict:
                raise ValueError("No final decision produced by strategy graph")

            # Convert to FinalDecision object
            final_decision = FinalDecision(**final_decision_dict)

            return final_decision
 
        except Exception as e:
            # Emergency fallback: safe do_not_bid decision
            print(f"Strategy selection failed: {e}")
            return FinalDecision(
                strategy="do_not_bid",
                recommended_bid_amount=0.0,
                should_increase_proxy=False,
                next_bid_amount=None,
                max_budget_for_domain=0.0,
                risk_level="high",
                confidence=0.0,
                reasoning=f"System error: {str(e)}. Emergency safe decision: do not bid.",
                proxy_decision=None,
                decision_source="system_error"
            )

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for monitoring."""
        if self.total_decisions == 0:
            return {"message": "No decisions made yet"}

        return {
            "total_decisions": self.total_decisions,
            "llm_success_rate": self.llm_success_count / self.total_decisions,
            "fallback_rate": self.fallback_count / self.total_decisions,
            "safety_block_rate": self.safety_block_count / self.total_decisions,
            "llm_success_count": self.llm_success_count,
            "fallback_count": self.fallback_count,
            "safety_block_count": self.safety_block_count
        }

    def reset_performance_stats(self):
        """Reset performance tracking counters."""
        self.total_decisions = 0
        self.llm_success_count = 0
        self.fallback_count = 0
        self.safety_block_count = 0

    
    def record_outcome(self, auction_context: AuctionContext, decision: FinalDecision, result: str, final_price: float):
        """ Call this method AFTER auction completes. Thsi enables learning from results."""

        profit_margin = None
        if result == "won":
            profit_margin = (auction_context.estimated_value - final_price) / auction_context.estimated_value

        outcome = AuctionOutcome(
            auction_id=f"{auction_context.domain}_{datetime.utcnow().isoformat()}",
            domain=auction_context.domain,
            platform=auction_context.platform,
            estimated_value=auction_context.estimated_value,
            current_bid_at_decision=auction_context.current_bid,
            final_price=final_price,
            num_bidders=auction_context.num_bidders,
            hours_remaining_at_decision=auction_context.hours_remaining,
            bot_detected=auction_context.bidder_analysis.get("bot_detected", False),
            strategy_used=decision.strategy,
            recommended_bid=decision.recommended_bid_amount,
            decision_source=decision.decision_source,
            confidence=decision.confidence,
            result=result,
            profit_margin=profit_margin,
            opponent_hash=None,
            raw_data=None
        )

        self.history_storage.record_outcome(outcome)

    def record_round_outcome(
        self,
        auction_context: AuctionContext,
        decision: FinalDecision,
        result_round: str,
    ) -> None:
        """Call when you get outbid (or end a round). Use result_round='outbid' for mid-auction."""
        if not self.history_storage or not getattr(auction_context, "thread_id", None):
            return
        thread_id = auction_context.thread_id
        existing = self.history_storage.get_rounds_for_thread(thread_id)
        round_number = len(existing) + 1
        record = AuctionRoundRecord(
            thread_id=thread_id,
            round_number=round_number,
            domain=auction_context.domain,
            platform=auction_context.platform,
            estimated_value=auction_context.estimated_value,
            current_bid_at_decision=auction_context.current_bid,
            strategy_used=decision.strategy,
            recommended_bid=decision.recommended_bid_amount,
            decision_source=decision.decision_source,
            confidence=decision.confidence,
            result_round=result_round,
        )
        self.history_storage.record_round(record)


