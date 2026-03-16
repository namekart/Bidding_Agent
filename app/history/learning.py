""" Learning algorithms that use historical  data to improve decisions."""
from typing import Dict, Any , Optional, List
from .storage import AuctionHistoryStorage
from ..core.models import AuctionContext

class HistoricalLearning:
    """ Use historical data to improve bidding decisions"""

    def __init__(self, storage: AuctionHistoryStorage):
        self.storage = storage
    
    def get_historical_context(self, context: AuctionContext) -> Dict[str, Any]:
        """
        Get relevant historical insights for current auction.
        This data can be passed to the LLM for better decisions.
        """
        # Determine value tier
        if context.estimated_value >= 1000:
            value_tier = "high"
        
        elif context.estimated_value >= 100:
            value_tier = "medium"
        else:
            value_tier = "low"
        
        # get similar past auctions
        value_range = context.estimated_value * 0.3
        similar_auctions = self.storage.get_similar_auctions(
            platform=context.platform,
            value_min=context.estimated_value - value_range,
            value_max=context.estimated_value + value_range,
            limit=10
        )

        # Calculate insights from similar auctions
        insights = self._calculate_insights(similar_auctions)

        # Get strategy performance for this context
        strategy_stats = {}
        for strategy in ["proxy_max", "last_minute_snipe", "incremental_test",
                         "wait_for_closeout", "aggressive_early"]:
            stats = self.storage.get_strategy_performance(
                strategy=strategy,
                platform=context.platform,
                value_tier=value_tier
            )
            if stats["total_uses"] > 0:
                strategy_stats[strategy] = stats

        # Get best performing strategy
        best_strategy = self.storage.get_best_strategy_for_context(
            platform=context.platform,
            value_tier=value_tier
        )

        # Previous rounds in THIS auction (if thread_id provided)
        same_auction_attempts = []
        thread_id = getattr(context, "thread_id", None)
        if thread_id:
            rounds = self.storage.get_rounds_for_thread(thread_id)
            same_auction_attempts = [
                {
                    "round": r["round_number"],
                    "strategy_used": r["strategy_used"],
                    "result_round": r["result_round"],
                }
                for r in rounds
            ]

        return {
            "similar_auctions_count": len(similar_auctions),
            "insights": insights,
            "strategy_performance": strategy_stats,
            "historically_best_strategy": best_strategy,
            "value_tier": value_tier,
            "same_auction_attempts": same_auction_attempts,
        }

    def _calculate_insights(self, auctions: List[Dict]) -> Dict[str, Any]:
        """ Calculate insights from similar auctions."""
        if not auctions:
            return {"has_data": False}
        
        wins = [a for a in auctions if a.get("result") == "won"]
        losses = [a for a in auctions if a.get("result") == "lost"]

        insights = {
            "has_data": True,
            "total_similar": len(auctions),
            "win_rate": len(wins) / len(auctions) if auctions else 0,
        }
        
        # Average final price vs estimated value
        if auctions:
            price_ratios = [
                a["final_price"] / a["estimated_value"]
                for a in auctions
                if a.get("final_price") and a.get("estimated_value")
            ]
            if price_ratios:
                insights["avg_final_price_ratio"] = sum(price_ratios) / len(price_ratios)
                insights["price_ratio_insight"] = (
                    f"Similar domains typically sold for {insights['avg_final_price_ratio']:.0%} of estimated value."
                )

        if wins:
            strategy_counts = {}
            for w in wins:
                s = w.get("strategy_used", "unknown")
                strategy_counts[s] = strategy_counts.get(s,0) +1
            insights["winning_strategies"] = strategy_counts

        return insights

    def suggest_dynamic_threshold(self, context: AuctionContext, base_safe_max_ratio: float = 1.0) -> float:

        """Suggest a dynamic safe_max ratio based on historical data.
        Returns adjusted ratio up to 1.0 (100% max budget)."""

        historical = self.get_historical_context(context)

        ratio = base_safe_max_ratio

        if historical["insights"].get("avg_final_price_ratio"):
            avg_ratio = historical["insights"]["avg_final_price_ratio"]

            if avg_ratio < 0.60:
                ratio -= 0.05
            elif avg_ratio > 0.75:
                ratio += 0.03

        if historical["insights"].get("win_rate", 0.5) < 0.3:
            ratio += 0.05
        elif historical["insights"].get("win_rate", 0.5) > 0.8:
            ratio -= 0.03

        return max(0.55, min(1.0, ratio))