""" 
Database models for historical auction data.
"""
from datetime import datetime
from typing import Optional,List, Dict, Any
from pydantic import BaseModel, Field

class AuctionOutcome(BaseModel):
    """ Record of a completed auction"""
    auction_id: str
    domain: str
    platform: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Context at decision time
    estimated_value: float
    current_bid_at_decision: float
    final_price: float
    num_bidders: int
    hours_remaining_at_decision: float
    bot_detected: bool

    # Agent's Decision
    strategy_used: str
    recommended_bid: float
    decision_source: str
    confidence: float

    # Outcome
    result:str  #"won", "lost", "abandoned" 
    profit_margin: Optional[float] = None # Only if won

    # Opponent info (if identified)
    opponent_hash:Optional[str] = None

class AuctionRoundRecord(BaseModel):
    """One bid round within a single auction (same thread_id)."""
    thread_id: str
    round_number: int
    domain: str
    platform: str
    estimated_value: float
    current_bid_at_decision: float
    strategy_used: str
    recommended_bid: float
    decision_source: str
    confidence: float
    result_round: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OpponentProfile(BaseModel):
    """ Learned profile of a recurring opponent."""
    opponent_id:str
    first_seen: datetime
    last_seen: datetime
    encounter_count: int = 0

    # Behavior
    is_likely_bot: bool = False
    avg_reaction_time: float= 60.0
    aggression_scores: List[float] = []
    platform: List[str] =[]

    # Our record against them
    wins: int = 0
    losses: int = 0



class StrategyPerformance(BaseModel):
    """ Performance metrices for a strategy."""
    strategy: str
    platform: str
    value_tier: str  # "high", "medium", "low"

    total_uses: int = 0
    wins: int = 0
    total_profit: float= 0.0

    @property
    def win_rate(self) -> float:
        return self.wins/max(1, self.total_uses)
    
    @property
    def avg_profit_per_win(self) ->float:
        return self.total_profit/ max(1, self.wins)
        

