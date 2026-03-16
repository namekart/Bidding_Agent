"""
Pydantic data models for the Domain Auction Strategy Agent
"""
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator
from typing_extensions import TypedDict


class BidderAnalysis(TypedDict):
    """Analysis of bidder behavior and types"""
    bot_detected: bool
    corporate_buyer: bool
    aggression_score: float  # 0-10
    reaction_time_avg: float  # seconds


class AuctionContext(BaseModel):
    """Input context for auction decision making"""
    domain: str = Field(..., description="Domain name being auctioned")
    platform: Literal["godaddy", "namejet", "dynadot"] = Field(..., description="Auction platform")
    estimated_value: float = Field(..., gt=0, description="External valuation estimate")
    current_bid: float = Field(..., ge=0, description="Current highest bid")
    num_bidders: int = Field(..., ge=0, description="Number of active bidders")
    hours_remaining: float = Field(..., ge=0, description="Hours until auction ends")
    your_current_proxy: float = Field(..., ge=0, description="Your current proxy bid max (0 if none)")
    budget_available: float = Field(..., ge=0, description="Remaining global budget")
    bidder_analysis: BidderAnalysis = Field(..., description="Analysis of bidder behavior")
    thread_id: Optional[str] = None

    @validator('estimated_value', 'current_bid', 'budget_available')
    def validate_positive_floats(cls, v):
        if v < 0:
            raise ValueError('Value must be non-negative')
        return v

    @validator('hours_remaining')
    def validate_hours(cls, v):
        if v < 0:
            raise ValueError('Hours remaining cannot be negative')
        return v


class StrategyDecision(BaseModel):
    """Output from strategy selection (LLM or rules-based)"""
    strategy: Literal[
        "proxy_max",
        "last_minute_snipe",
        "incremental_test",
        "wait_for_closeout",
        "aggressive_early",
        "do_not_bid"
    ] = Field(..., description="Selected bidding strategy")

    recommended_bid_amount: float = Field(..., ge=0, description="Recommended proxy max amount")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in decision (0-1)")
    risk_level: Literal["low", "medium", "high"] = Field(..., description="Risk assessment")
    reasoning: str = Field(..., min_length=50, description="Detailed human-readable reasoning")

    should_increase_proxy: Optional[bool] = Field(None, description="Whether to increase current proxy")
    next_bid_amount: Optional[float] = Field(None, description="Next visible bid amount if proxy increased")
    max_budget_for_domain: float = Field(..., ge=0, description="Maximum budget allocated for this domain")


class ProxyDecision(BaseModel):
    """Decision about proxy bidding adjustments"""
    current_proxy: float = Field(..., ge=0, description="Current proxy bid max")
    current_bid: float = Field(..., ge=0, description="Current highest bid")
    safe_max: float = Field(..., ge=0, description="Safe maximum bid (100% of value / max budget)")
    should_increase_proxy: bool = Field(..., description="Whether to increase proxy")
    new_proxy_max: Optional[float] = Field(None, description="New proxy max if increasing")
    next_bid_amount: Optional[float] = Field(None, description="Next visible bid amount")
    max_budget_for_domain: float = Field(..., ge=0, description="Maximum budget for domain")
    proxy_action: Literal["accept_loss", "increase_proxy", "maintain_proxy"] = Field(
        ..., description="Action to take with proxy"
    )
    explanation: str = Field(..., description="Explanation of proxy decision")


class FinalDecision(BaseModel):
    """Complete final decision combining strategy and proxy logic"""
    strategy: str = Field(..., description="Selected strategy")
    recommended_bid_amount: float = Field(..., description="Recommended proxy max")
    should_increase_proxy: bool = Field(..., description="Whether to increase proxy")
    next_bid_amount: Optional[float] = Field(None, description="Next bid amount")
    max_budget_for_domain: float = Field(..., description="Max budget for domain")
    risk_level: str = Field(..., description="Risk level")
    confidence: float = Field(..., description="Confidence score")
    reasoning: str = Field(..., description="Combined reasoning")
    proxy_decision: Optional[ProxyDecision] = Field(None, description="Proxy bidding details")
    decision_source: Literal["llm", "rules_fallback", "safety_block", "system_error"] = Field(
        ..., description="Source of the decision"
    )


class AuctionState(TypedDict):
    """LangGraph state for the auction strategy workflow"""
    # Input
    auction_context: AuctionContext
    market_intelligence: Optional[Dict[str, Any]]
    historical_context: Optional[Dict[str, Any]]

    # Pre-filter outputs
    blocked: bool
    block_reason: Optional[str]

    # LLM decision
    llm_decision: Optional[Dict[str, Any]]
    llm_valid: bool
    llm_validation_reason: Optional[str]

    # Rule-based fallback decision
    rule_decision: Optional[Dict[str, Any]]

    # Proxy/outbid logic
    proxy_analysis: Optional[Dict[str, Any]]

    # Final output
    final_decision: Optional[Dict[str, Any]]
    decision_source: Optional[Literal["llm", "rules_fallback", "safety_block"]]
