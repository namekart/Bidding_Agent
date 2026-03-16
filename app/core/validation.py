"""
Layer 3: Hardcoded Post-Validation
Validates LLM strategy decisions against safety rules and logical consistency.
Uses tiered validation: HARD errors block, SOFT errors warn but allow.
"""
from typing import Dict, Any, Tuple, Optional, List
from .models import AuctionContext, StrategyDecision


class ValidationResult:
    """Container for validation results with severity levels."""
    def __init__(self):
        self.errors: List[str] = []      # Hard failures - block the decision
        self.warnings: List[str] = []    # Soft issues - log but allow
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
    
    @property
    def combined_message(self) -> Optional[str]:
        if self.errors:
            return " | ".join(self.errors)
        return None


class StrategyValidator:
    """
    Validates LLM-generated strategy decisions against hard constraints.
    Uses tiered validation: critical errors block, minor issues warn.
    """

    @staticmethod
    def validate_bid_ceiling(decision: StrategyDecision, context: AuctionContext) -> Optional[str]:
        """
        HARD RULE: Bid amount cannot exceed 100% of estimated value (max budget / APR).
        This is the absolute maximum allowed.
        """
        hard_ceiling = context.estimated_value * 1.0
        if decision.recommended_bid_amount > hard_ceiling:
            return (
                f"BID CEILING VIOLATION: Recommended bid (${decision.recommended_bid_amount:.2f}) "
                f"exceeds 100% of estimated value / max budget (${hard_ceiling:.2f}). "
                f"Maximum allowed: ${hard_ceiling:.2f}"
            )
        return None

    @staticmethod
    def validate_budget_check(decision: StrategyDecision, context: AuctionContext) -> Optional[str]:
        """
        HARD RULE: Cannot recommend bids exceeding available budget.
        Prevents impossible bidding scenarios.
        """
        if decision.recommended_bid_amount > context.budget_available:
            return (
                f"BUDGET VIOLATION: Recommended bid (${decision.recommended_bid_amount:.2f}) "
                f"exceeds available budget (${context.budget_available:.2f}). "
                f"Cannot execute this strategy."
            )
        return None

    @staticmethod
    def validate_do_not_bid_consistency(decision: StrategyDecision) -> Optional[str]:
        """
        HARD RULE: If strategy is do_not_bid, bid amount must be 0.
        This is a logical contradiction that cannot be allowed.
        """
        if decision.strategy == "do_not_bid" and decision.recommended_bid_amount > 0:
            return (
                "LOGICAL INCONSISTENCY: Strategy is 'do_not_bid' but recommended_bid_amount > 0. "
                "Cannot bid if strategy is to not participate."
            )
        return None

    @staticmethod
    def validate_confidence_risk_alignment(decision: StrategyDecision) -> Tuple[Optional[str], Optional[str]]:
        """
        SOFT RULE: Confidence should roughly match risk level.
        Returns (hard_error, soft_warning) tuple.
        
        - Minor misalignment: Warning only (LLMs aren't perfect calibrators)
        - Severe misalignment: Hard error (indicates broken reasoning)
        """
        # Expanded acceptable ranges (more lenient)
        acceptable_ranges = {
            "low": (0.50, 1.0),     # Low risk: confidence 50-100%
            "medium": (0.35, 0.95), # Medium risk: confidence 35-95%
            "high": (0.0, 0.80)     # High risk: confidence 0-80%
        }
        
        # Severe mismatch thresholds (these trigger hard errors)
        severe_mismatch_threshold = 0.3  # More than 30% outside range
        
        min_conf, max_conf = acceptable_ranges.get(decision.risk_level, (0.0, 1.0))
        
        # Check if within acceptable range
        if min_conf <= decision.confidence <= max_conf:
            return None, None  # All good
        
        # Calculate how far outside the range
        if decision.confidence < min_conf:
            deviation = min_conf - decision.confidence
        else:
            deviation = decision.confidence - max_conf
        
        # Severe mismatch - hard error
        if deviation > severe_mismatch_threshold:
            return (
                f"SEVERE CONFIDENCE MISMATCH: Risk '{decision.risk_level}' with confidence "
                f"{decision.confidence:.2f} is severely misaligned (deviation: {deviation:.2f}). "
                f"This indicates broken reasoning."
            ), None
        
        # Minor mismatch - warning only
        return None, (
            f"CONFIDENCE NOTE: Risk '{decision.risk_level}' with confidence {decision.confidence:.2f} "
            f"is slightly outside typical range ({min_conf:.1f}-{max_conf:.1f}). Allowing decision."
        )

    @staticmethod
    def validate_reasoning_quality(decision: StrategyDecision) -> Tuple[Optional[str], Optional[str]]:
        """
        SOFT RULE: Reasoning should be substantive.
        Returns (hard_error, soft_warning) tuple.
        
        - Very short reasoning: Hard error (< 50 chars)
        - Somewhat short: Warning (50-100 chars)
        - Missing key concepts: Warning only (keywords are imperfect)
        """
        reasoning_length = len(decision.reasoning)
        
        # Very short - hard error (likely broken LLM response)
        if reasoning_length < 50:
            return (
                f"REASONING TOO SHORT: Only {reasoning_length} characters. "
                f"Minimum 50 required for valid strategy explanation."
            ), None
        
        # Somewhat short - warning
        warning = None
        if reasoning_length < 100:
            warning = f"REASONING BRIEF: {reasoning_length} chars (recommended: 100+)"
        
        # Check for meaningful content with expanded keyword list
        reasoning_lower = decision.reasoning.lower()
        keyword_groups = [
            ["profit", "margin", "value", "cost", "price"],     # Financial terms
            ["risk", "safe", "danger", "careful", "conservative"],  # Risk terms
            ["competition", "bidder", "opponent", "competitor"],    # Competition terms
            ["strategy", "approach", "tactic", "plan", "decision"]  # Strategy terms
        ]
        
        # Count how many keyword groups have at least one match
        groups_matched = sum(
            1 for group in keyword_groups 
            if any(keyword in reasoning_lower for keyword in group)
        )
        
        # Need at least 2 out of 4 groups
        if groups_matched < 2:
            if warning:
                warning += f" | Also lacks depth (only {groups_matched}/4 concept areas covered)"
            else:
                warning = f"REASONING SHALLOW: Only {groups_matched}/4 key concept areas discussed"
        
        return None, warning

    @staticmethod
    def validate_strategy_context_fit(
        decision: StrategyDecision, 
        context: AuctionContext
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        MIXED RULE: Strategy should fit context.
        Returns (hard_error, soft_warning) tuple.
        
        Some mismatches are hard errors, others are warnings.
        """
        # HARD: aggressive_early on very low value domains is likely an error
        if decision.strategy == "aggressive_early" and context.estimated_value < 200:
            return (
                f"STRATEGY ERROR: 'aggressive_early' on ${context.estimated_value:.2f} domain. "
                f"This strategy is reserved for high-value must-have domains (>$500)."
            ), None
        
        # SOFT: wait_for_closeout with some competition - might be valid
        if decision.strategy == "wait_for_closeout" and context.num_bidders > 3:
            return None, (
                f"STRATEGY NOTE: 'wait_for_closeout' with {context.num_bidders} bidders "
                f"may not succeed. Consider alternative strategies."
            )
        
        # SOFT: aggressive_early on medium value - unusual but allow
        if decision.strategy == "aggressive_early" and context.estimated_value < 500:
            return None, (
                f"STRATEGY NOTE: 'aggressive_early' on ${context.estimated_value:.2f} domain "
                f"is unusual. Typically reserved for >$500 domains."
            )
        
        # SOFT: sniping with lots of time remaining
        if decision.strategy == "last_minute_snipe" and context.hours_remaining > 4:
            return None, (
                f"TIMING NOTE: 'last_minute_snipe' selected with {context.hours_remaining:.1f} hours "
                f"remaining. May be valid for bot avoidance."
            )
        
        return None, None

    @classmethod
    def validate_all(cls, decision: StrategyDecision, context: AuctionContext) -> Tuple[bool, Optional[str]]:
        """
        Run all validation checks on a strategy decision.
        
        Validation tiers:
        1. HARD checks (bid ceiling, budget, do_not_bid logic) - must pass
        2. SOFT checks (confidence, reasoning, context fit) - warnings only unless severe
        
        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        result = ValidationResult()
        
        # === HARD CHECKS (Always block on failure) ===
        hard_checks = [
            lambda: cls.validate_bid_ceiling(decision, context),
            lambda: cls.validate_budget_check(decision, context),
            lambda: cls.validate_do_not_bid_consistency(decision),
        ]
        
        for check_func in hard_checks:
            error = check_func()
            if error:
                result.errors.append(error)
        
        # If hard checks failed, return immediately
        if not result.is_valid:
            return False, result.combined_message
        
        # === SOFT CHECKS (Warnings unless severe) ===
        soft_checks = [
            lambda: cls.validate_confidence_risk_alignment(decision),
            lambda: cls.validate_reasoning_quality(decision),
            lambda: cls.validate_strategy_context_fit(decision, context),
        ]
        
        for check_func in soft_checks:
            hard_error, warning = check_func()
            if hard_error:
                result.errors.append(hard_error)
            if warning:
                result.warnings.append(warning)
                print(f"VALIDATION WARNING: {warning}")  # Log warnings
        
        # Log all warnings for monitoring
        if result.warnings:
            print(f"LLM Decision passed with {len(result.warnings)} warning(s)")
        
        return result.is_valid, result.combined_message




