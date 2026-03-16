"""
Layer 1: Hardcoded Safety Pre-Filters
Pure Python logic that blocks unsafe auctions before LLM processing.
"""
from typing import Dict, Any, Optional
from .models import AuctionContext


class SafetyPreFilters:
    """
    Non-negotiable safety checks that cannot be overridden by LLM.
    These filters prevent catastrophic bidding decisions.
    """

    @staticmethod
    def check_overpayment_protection(context: AuctionContext) -> Optional[Dict[str, Any]]:
        """
        HARD RULE: If current_bid > estimated_value * 1.30, block auction.
        This prevents "winner's curse" where we pay way above value.
        """
        threshold = context.estimated_value * 1.30
        if context.current_bid > threshold:
            return {
                'blocked': True,
                'reason': (
                    f"OVERPAYMENT PROTECTION: Current bid (${context.current_bid:.2f}) "
                    f"exceeds 130% of estimated value (${context.estimated_value:.2f}). "
                    f"This enters 'winner's curse' territory where profit is impossible. "
                    f"Strategy: do_not_bid"
                ),
                'strategy': 'do_not_bid' ,
                'recommended_bid_amount': 0.0,
                'risk_level': 'high',
                'confidence': 0.95
            }
        return None

    @staticmethod
    def check_portfolio_concentration(context: AuctionContext) -> Optional[Dict[str, Any]]:
        """
        HARD RULE: No single domain can consume >50% of remaining budget.
        This prevents portfolio concentration risk.
        """
        max_domain_budget = context.budget_available * 0.50
        if context.estimated_value > max_domain_budget:
            return {
                'blocked': True,
                'reason': (
                    f"PORTFOLIO CONCENTRATION: Domain value (${context.estimated_value:.2f}) "
                    f"would consume >50% of remaining budget (${context.budget_available:.2f}). "
                    f"Maximum allowed: ${max_domain_budget:.2f}. "
                    f"This violates diversification principles. Strategy: do_not_bid"
                ),
                'strategy': 'do_not_bid',
                'recommended_bid_amount': 0.0,
                'risk_level': 'high',
                'confidence': 0.95
            }
        return None

    @staticmethod
    def check_minimum_budget(context: AuctionContext) -> Optional[Dict[str, Any]]:
        """
        HARD RULE: Require minimum $100 budget for meaningful participation.
        Small budgets lead to poor decisions and margin compression.
        """
        if context.budget_available < 100.0:
            return {
                'blocked': True,
                'reason': (
                    f"MINIMUM BUDGET: Insufficient budget (${context.budget_available:.2f}) "
                    f"for meaningful auction participation. "
                    f"Minimum required: $100. "
                    f"Strategy: do_not_bid"
                ),
                'strategy': 'do_not_bid',
                'recommended_bid_amount': 0.0,
                'risk_level': 'high',
                'confidence': 0.95
            }
        return None

    @staticmethod
    def check_valuation_validity(context: AuctionContext) -> Optional[Dict[str, Any]]:
        """
        HARD RULE: Invalid or missing valuation prevents rational decisions.
        Cannot make profit calculations without knowing domain value.
        """
        if context.estimated_value <= 0:
            return {
                'blocked': True,
                'reason': (
                    f"VALUATION INVALID: Estimated value (${context.estimated_value:.2f}) "
                    f"is invalid or missing. Cannot calculate profit margins. "
                    f"Strategy: do_not_bid"
                ),
                'strategy': 'do_not_bid',
                'recommended_bid_amount': 0.0,
                'risk_level': 'high',
                'confidence': 0.95
            }
        return None

    @classmethod
    def run_all_checks(cls, context: AuctionContext) -> Dict[str, Any]:
        """
        Run all safety pre-filters in priority order.
        Returns block decision if any filter triggers, otherwise allows auction.
        """
        # Run checks in order of priority (most critical first)
        checks = [
            cls.check_valuation_validity,
            cls.check_minimum_budget,
            cls.check_overpayment_protection,
            cls.check_portfolio_concentration,
        ]

        for check_func in checks:
            result = check_func(context)
            if result:
                return result

        # All checks passed
        return {
            'blocked': False,
            'reason': 'All safety checks passed. Proceeding to strategy analysis.',
            'strategy': None,
            'recommended_bid_amount': None,
            'risk_level': None,
            'confidence': None
        }

