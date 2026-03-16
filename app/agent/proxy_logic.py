"""
Proxy Bidding Logic
Handles outbid scenarios and proxy adjustment decisions.
Core logic for "should I increase my proxy or accept loss?"
"""
from typing import Dict, Any
from ..core.models import AuctionContext, StrategyDecision, ProxyDecision


class ProxyLogicHandler:
    """
    Handles proxy bidding adjustments and outbid scenarios.
    Determines whether to increase proxy, accept loss, or maintain position.
    """

    @staticmethod
    def calculate_safe_max(estimated_value: float) -> float:
        """Calculate maximum bid (100% of estimated value / max budget / APR)."""
        return estimated_value * 1.0

    @staticmethod
    def get_platform_increment(platform: str, current_bid: float) -> float:
        """
        Get minimum increment for the platform.
        Defaults to $5 if platform not recognized.
        """
        # Platform-specific increments (configurable)
        increments = {
            "godaddy": 5.0,
            "namejet": 5.0,
            "dynadot": max(5.0, current_bid * 0.05)  # 5% for higher bids
        }
        return increments.get(platform.lower(), 5.0)

    @staticmethod
    def analyze_proxy_situation(
        context: AuctionContext,
        strategy_decision: StrategyDecision
    ) -> ProxyDecision:
        """
        Analyze current proxy situation and decide on adjustments.

        This handles scenarios like:
        - "I set proxy to $100, current bid is now $120. Should I increase?"
        - "Safe max is $700, current bid $600. What's next bid and max budget?"
        """
        safe_max = ProxyLogicHandler.calculate_safe_max(context.estimated_value)
        increment = ProxyLogicHandler.get_platform_increment(context.platform, context.current_bid)

        current_proxy = context.your_current_proxy
        current_bid = context.current_bid

        # SCENARIO 1: No current proxy set (first bid)
        if current_proxy == 0:
            new_proxy_max = min(safe_max, context.budget_available, context.estimated_value)
            next_bid = current_bid + increment

            return ProxyDecision(
                current_proxy=current_proxy,
                current_bid=current_bid,
                safe_max=safe_max,
                should_increase_proxy=True,
                new_proxy_max=new_proxy_max,
                next_bid_amount=next_bid,
                max_budget_for_domain=new_proxy_max,
                proxy_action="increase_proxy",
                explanation=(
                    f"INITIAL PROXY SETUP: No current proxy set. "
                    f"Safe max calculated as ${safe_max:.2f} (100% of ${context.estimated_value:.2f} max budget). "
                    f"Setting proxy to ${new_proxy_max:.2f}. "
                    f"Next visible bid will be ${next_bid:.2f} (${current_bid:.2f} + ${increment:.2f} increment). "
                    f"Domain will never cost more than ${new_proxy_max:.2f} even if fully contested."
                )
            )

        # SCENARIO 2: Current bid exceeds safe max (cannot profitably continue)
        if safe_max <= current_bid:
            return ProxyDecision(
                current_proxy=current_proxy,
                current_bid=current_bid,
                safe_max=safe_max,
                should_increase_proxy=False,
                new_proxy_max=None,
                next_bid_amount=None,
                max_budget_for_domain=0,
                proxy_action="accept_loss",
                explanation=(
                    f"PROFIT IMPOSSIBLE: Safe max (${safe_max:.2f}) is below current bid (${current_bid:.2f}). "
                    f"Cannot increase proxy above max budget (${safe_max:.2f}). "
                    f"Current proxy (${current_proxy:.2f}) is insufficient. "
                    f"Strategy: Accept loss and do not increase proxy. "
                    f"This prevents winner's curse scenario."
                )
            )

        # SCENARIO 3: Safe max above current bid (can increase proxy)
        # Calculate optimal new proxy
        potential_new_proxy = min(safe_max, context.budget_available, context.estimated_value)

        # Only increase if we gain meaningful headroom
        min_increase_threshold = increment * 3  # At least 3 increments of headroom

        if potential_new_proxy > current_proxy + min_increase_threshold:
            next_bid = current_bid + increment
 
            return ProxyDecision(
                current_proxy=current_proxy,
                current_bid=current_bid,
                safe_max=safe_max,
                should_increase_proxy=True,
                new_proxy_max=potential_new_proxy,
                next_bid_amount=next_bid,
                max_budget_for_domain=potential_new_proxy,
                proxy_action="increase_proxy",
                explanation=(
                    f"PROXY INCREASE OPTIMAL: Safe max (${safe_max:.2f}) exceeds current bid (${current_bid:.2f}). "
                    f"Current proxy (${current_proxy:.2f}) insufficient for profit protection. "
                    f"Increasing proxy to ${potential_new_proxy:.2f}. "
                    f"Next visible bid will be ${next_bid:.2f} (${current_bid:.2f} + ${increment:.2f} increment). "
                    f"Domain cost capped at ${potential_new_proxy:.2f} (max budget)."
                )
            )
        else:
            # Current proxy is adequate
            return ProxyDecision(
                current_proxy=current_proxy,
                current_bid=current_bid,
                safe_max=safe_max,
                should_increase_proxy=False,
                new_proxy_max=None,
                next_bid_amount=None,
                max_budget_for_domain=current_proxy,
                proxy_action="maintain_proxy",
                explanation=(
                    f"PROXY ADEQUATE: Current proxy (${current_proxy:.2f}) provides sufficient protection. "
                    f"Safe max (${safe_max:.2f}) supports current position against bid (${current_bid:.2f}). "
                    f"No proxy increase needed. "
                    f"Domain will not exceed ${current_proxy:.2f} cost (within max budget)."
                ) 
            )

    @staticmethod
    def apply_proxy_logic_to_decision(
        context: AuctionContext,
        strategy_decision: StrategyDecision
    ) -> Dict[str, Any]:
        """
        Apply proxy logic to a strategy decision, updating fields as needed.
        This integrates proxy analysis with the strategy decision.
        """
        proxy_analysis = ProxyLogicHandler.analyze_proxy_situation(context, strategy_decision)

        # Update strategy decision with proxy logic results
        updated_decision = strategy_decision.copy()
        updated_decision.should_increase_proxy = proxy_analysis.should_increase_proxy
        updated_decision.next_bid_amount = proxy_analysis.next_bid_amount
        updated_decision.max_budget_for_domain = proxy_analysis.max_budget_for_domain

        # If proxy logic says accept loss, override strategy to do_not_bid
        if proxy_analysis.proxy_action == "accept_loss":
            updated_decision.strategy = "do_not_bid"
            updated_decision.recommended_bid_amount = 0.0
            updated_decision.confidence = min(updated_decision.confidence, 0.5)  # Reduce confidence
            updated_decision.risk_level = "high"
            updated_decision.reasoning += (
                f" PROXY ANALYSIS OVERRIDE: {proxy_analysis.explanation}"
            )

        return {
            "strategy_decision": updated_decision,
            "proxy_decision": proxy_analysis
        }

