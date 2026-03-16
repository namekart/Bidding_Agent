"""
Layer 4: Rule-Based Strategy Fallback
Pure algorithmic strategy selection based on value tiers and auction conditions.
Used when LLM fails validation or as baseline for comparison.
"""
from typing import Dict, Any, Optional
from ..core.models import AuctionContext, StrategyDecision


class RuleBasedStrategySelector:
    """
    Rule-based strategy selection using predefined logic trees.
    Provides deterministic, explainable decisions based on auction conditions.
    """

    @staticmethod
    def determine_value_tier(estimated_value: float) -> str:
        """Determine value tier for strategy selection."""
        if estimated_value >= 1000:
            return "high"
        elif estimated_value >= 100:
            return "medium"
        else:
            return "low"

    @staticmethod
    def calculate_safe_max(estimated_value: float) -> float:
        """Calculate maximum bid (100% of estimated value / max budget)."""
        return estimated_value * 1.0

    @staticmethod
    def get_high_value_strategy(context: AuctionContext, market_intelligence: Optional[Dict[str, Any]] = None) -> StrategyDecision:
        """
        Strategy logic for high-value domains ($1000+).
        Conservative approach to avoid escalation and protect margins.
        """
        safe_max = RuleBasedStrategySelector.calculate_safe_max(context.estimated_value)

        # Use market intelligence if available

        if market_intelligence:
            bidder_intel = market_intelligence.get("bidder_intelligence", {})
            if bidder_intel.get("found")and bidder_intel.get("is_aggressive"):

                safe_max = safe_max * 0.95

        # Early stage with no bidders - wait for closeout
        if context.num_bidders == 0 and context.hours_remaining < 1.0:
            return StrategyDecision(
                strategy="wait_for_closeout",
                recommended_bid_amount=safe_max,
                confidence=0.85,
                risk_level="low",
                reasoning=(
                    f"HIGH-VALUE CONSERVATIVE: Domain worth ${context.estimated_value:.2f}. "
                    f"No bidders with <1 hour remaining - wait for closeout to minimize competition. "
                    f"Safe max: ${safe_max:.2f} (100% max budget). "
                    f"This preserves budget cap while avoiding premature bidding that could attract competition."
                ),
                should_increase_proxy=None,
                next_bid_amount=None,
                max_budget_for_domain=safe_max
            )

        # Bot detected - prefer sniping to minimize reaction window
        if context.bidder_analysis.get("bot_detected", False):
            return StrategyDecision(
                strategy="last_minute_snipe",
                recommended_bid_amount=safe_max,
                confidence=0.80,
                risk_level="medium",
                reasoning=(
                    f"HIGH-VALUE BOT COUNTER: Bot detected with aggression score "
                    f"{context.bidder_analysis['aggression_score']}/10. "
                    f"Using last-minute snipe on {context.platform} to minimize bot reaction window. "
                    f"Safe max: ${safe_max:.2f}. "
                    f"Bots excel at rapid proxy wars but struggle with unpredictable timing."
                ),
                should_increase_proxy=None,
                next_bid_amount=None,
                max_budget_for_domain=safe_max
            )

        # Multiple bidders - use conservative proxy max
        if context.num_bidders <= 2:
            return StrategyDecision(
                strategy="proxy_max",
                recommended_bid_amount=safe_max,
                confidence=0.75,
                risk_level="medium",
                reasoning=(
                    f"HIGH-VALUE BALANCED: {context.num_bidders} bidders present. "
                    f"Setting conservative proxy max at ${safe_max:.2f} (100% max budget). "
                    f"This allows participation while protecting against escalation. "
                    f"Platform {context.platform} rules respected for auto-bidding."
                ),
                should_increase_proxy=None,
                next_bid_amount=None,
                max_budget_for_domain=safe_max
            )

        # High competition - sniping to avoid crowd
        return StrategyDecision(
            strategy="last_minute_snipe",
            recommended_bid_amount=safe_max,
            confidence=0.70,
            risk_level="high",
            reasoning=(
                f"HIGH-VALUE COMPETITION: {context.num_bidders} bidders create high risk. "
                f"Using sniping strategy to avoid getting caught in bidding war. "
                f"Safe max: ${safe_max:.2f} ensures profit protection. "
                f"Conservative timing accounts for {context.platform} platform rules."
            ),
            should_increase_proxy=None,
            next_bid_amount=None,
            max_budget_for_domain=safe_max
        )

    @staticmethod
    def get_medium_value_strategy(context: AuctionContext, market_intelligence: Optional[Dict[str, Any]] = None) -> StrategyDecision:
        """
        Strategy logic for medium-value domains ($100-1000).
        Balanced approach with flexibility based on competition.
        """
        safe_max = RuleBasedStrategySelector.calculate_safe_max(context.estimated_value)

        # Use market intelligence if available 
        if market_intelligence:
            bidder_intel = market_intelligence.get("bidder_intelligence", {})
            if bidder_intel.get("found") and bidder_intel.get("is_aggressive"):
                safe_max = safe_max * 0.95

        # GoDaddy late-stage rule - sniping respects 5-minute extension
        if (context.platform == "godaddy" and
            context.hours_remaining < 1.0):
            return StrategyDecision(
                strategy="last_minute_snipe",
                recommended_bid_amount=safe_max,
                confidence=0.80,
                risk_level="medium",
                reasoning=(
                    f"MEDIUM-VALUE GODADDY TIMING: GoDaddy auction with <1 hour remaining. "
                    f"Sniping strategy respects 5-minute extension rule to avoid auto-extensions. "
                    f"Safe max: ${safe_max:.2f}. "
                    f"This timing prevents unnecessary extensions while maintaining profit margin."
                ),
                should_increase_proxy=None,
                next_bid_amount=None,
                max_budget_for_domain=safe_max
            )

        # High competition - incremental testing
        if context.num_bidders > 5:
            return StrategyDecision(
                strategy="incremental_test",
                recommended_bid_amount=safe_max * 0.5,  # Start lower for testing
                confidence=0.65,
                risk_level="medium",
                reasoning=(
                    f"MEDIUM-VALUE COMPETITION: {context.num_bidders} bidders indicate high interest. "
                    f"Using incremental testing starting at ${safe_max * 0.5:.2f} "
                    f"to gauge competition without overcommitting. "    
                    f"Will escalate to full safe max (${safe_max:.2f}) if needed."
                ),
                should_increase_proxy=None,
                next_bid_amount=None,
                max_budget_for_domain=safe_max
            )

        # Moderate competition - proxy max
        return StrategyDecision(
            strategy="proxy_max",
            recommended_bid_amount=safe_max,
            confidence=0.75,
            risk_level="medium",
            reasoning=(
                f"MEDIUM-VALUE BALANCED: {context.num_bidders} bidders, domain worth ${context.estimated_value:.2f}. "
                f"Setting proxy max at ${safe_max:.2f} (max budget). "
                f"Platform {context.platform} auto-bidding will handle incremental competition."
            ),
            should_increase_proxy=None,
            next_bid_amount=None,
            max_budget_for_domain=safe_max
        )

    @staticmethod
    def get_low_value_strategy(context: AuctionContext, market_intelligence: Optional[Dict[str, Any]] = None) -> StrategyDecision:
        """
        Strategy logic for low-value domains (<$100).
        Aggressive or wait-for-closeout approaches.
        """
        safe_max = RuleBasedStrategySelector.calculate_safe_max(context.estimated_value)
        if market_intelligence:
            bidder_intel = market_intelligence.get("bidder_intelligence", {})
            if bidder_intel.get("found") and bidder_intel.get("is_aggressive"):
                safe_max = safe_max * 0.95

        # No bidders - wait for closeout
        if context.num_bidders == 0:
            return StrategyDecision(
                strategy="wait_for_closeout",
                recommended_bid_amount=safe_max,
                confidence=0.90,
                risk_level="low",
                reasoning=(
                    f"LOW-VALUE CLOSEOUT: No bidders on ${context.estimated_value:.2f} domain. "
                    f"Waiting for closeout maximizes profit potential with zero risk. "
                    f"Safe max ready: ${safe_max:.2f} if competition appears. "
                    f"This is optimal for low-value domains with no interest."
                ),
                should_increase_proxy=None,
                next_bid_amount=None,
                max_budget_for_domain=safe_max
            )

        # Some competition - incremental testing
        return StrategyDecision(
            strategy="incremental_test",
            recommended_bid_amount=min(safe_max, 50.0),  # Cap low for testing
            confidence=0.70,
            risk_level="low",
            reasoning=(
                f"LOW-VALUE TESTING: {context.num_bidders} bidders on low-value domain. "
                f"Using incremental testing starting at ${min(safe_max, 50.0):.2f}. "
                f"Safe max: ${safe_max:.2f} (max budget). "
                f"Low-value domains allow aggressive testing to find winning price."
            ),
            should_increase_proxy=None,
            next_bid_amount=None,
            max_budget_for_domain=safe_max
        )

    @classmethod
    def get_strategy_decision(cls, context: AuctionContext, market_intelligence: Optional[Dict[str, Any]] = None) -> StrategyDecision:
        """
        Main entry point for rule-based strategy selection.
        Routes to appropriate tier-specific logic.
        """
        value_tier = cls.determine_value_tier(context.estimated_value)

        if value_tier == "high":
           return cls.get_high_value_strategy(context, market_intelligence=market_intelligence)
        elif value_tier == "medium":
            return cls.get_medium_value_strategy(context, market_intelligence=market_intelligence)
        else:  # low
            return cls.get_low_value_strategy(context, market_intelligence=market_intelligence)
