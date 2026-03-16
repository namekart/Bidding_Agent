"""
Storage layer for auction history using Supabase (PostgreSQL).
"""

from supabase import create_client, Client
import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from .models import AuctionOutcome, AuctionRoundRecord, OpponentProfile, StrategyPerformance

class AuctionHistoryStorage:
    """Supabase-based storage for auction history"""
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize storage with Supabase connection

        Args:
            supabase_url: Supabase project URL (e.g. https://xxx.supabase.co)
            supabase_key: Supabase service role key (for server-side access)
        """
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL and key required. Set SUPABASE_URL and SUPABASE_KEY env vars or pass directly")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        self._init_database()



    def _init_database(self):
        """
        Verify Supabase tables exist.
        Tables should be created via Supabase dashboard SQL editor.
        See supabase_tables.sql for table creation script.
        """
        try:
            # Check if tables exist by attempting a simple query
            self.client.table('auction_outcomes').select('id').limit(1).execute()
            self.client.table('strategy_performance').select('id').limit(1).execute()
            self.client.table('auction_rounds').select('id').limit(1).execute()
            print("Supabase tables verified successfully")
        except Exception as e:
            print(f"Warning: Could not verify Supabase tables. Please create them via Supabase SQL editor.")
            print(f"See supabase_tables.sql for table creation script. Error: {e}")

    def record_outcome(self, outcome: AuctionOutcome):
        """Save an auction outcome to Supabase."""
        
        # Prepare data for Supabase
        data = {
            "auction_id": outcome.auction_id,
            "domain": outcome.domain,
            "platform": outcome.platform,
            "timestamp": outcome.timestamp.isoformat() if outcome.timestamp else None,
            "estimated_value": float(outcome.estimated_value),
            "current_bid_at_decision": float(outcome.current_bid_at_decision),
            "final_price": float(outcome.final_price),
            "num_bidders": outcome.num_bidders,
            "hours_remaining_at_decision": float(outcome.hours_remaining_at_decision),
            "bot_detected": bool(outcome.bot_detected),
            "strategy_used": outcome.strategy_used,
            "recommended_bid": float(outcome.recommended_bid),
            "decision_source": outcome.decision_source,
            "confidence": float(outcome.confidence),
            "result": outcome.result,
            "profit_margin": float(outcome.profit_margin) if outcome.profit_margin else None,
            "opponent_hash": outcome.opponent_hash,
            "raw_data": outcome.dict()  # Supabase stores dict as JSONB
        }
        
        # Upsert (insert or update if auction_id exists)
        try:
            self.client.table('auction_outcomes').upsert(
                data,
                on_conflict='auction_id'  # PostgreSQL unique constraint
            ).execute()
        except Exception as e:
            print(f"Error recording outcome to Supabase: {e}")
            raise
        
        # Update strategy performance
        self._update_strategy_performance(outcome)

    def _update_strategy_performance(self, outcome: AuctionOutcome):
        """Update strategy performance stats in Supabase."""
        
        # Determine value tier
        if outcome.estimated_value >= 1000:
            value_tier = "high"
        elif outcome.estimated_value >= 100:
            value_tier = "medium"
        else:
            value_tier = "low"
        
        try:
            # Get existing stats
            result = self.client.table('strategy_performance').select('*').match({
                'strategy': outcome.strategy_used,
                'platform': outcome.platform,
                'value_tier': value_tier
            }).execute()
            
            if result.data:
                # Update existing record
                row = result.data[0]
                total_uses = row['total_uses'] + 1
                wins = row['wins'] + (1 if outcome.result == "won" else 0)
                total_profit = row['total_profit']
                if outcome.result == "won" and outcome.profit_margin:
                    total_profit += outcome.profit_margin * outcome.final_price
                
                self.client.table('strategy_performance').update({
                    'total_uses': total_uses,
                    'wins': wins,
                    'total_profit': float(total_profit)
                }).eq('id', row['id']).execute()
            else:
                # Insert new record
                total_uses = 1
                wins = 1 if outcome.result == "won" else 0
                total_profit = 0.0
                if outcome.result == "won" and outcome.profit_margin:
                    total_profit = outcome.profit_margin * outcome.final_price
                
                self.client.table('strategy_performance').insert({
                    'strategy': outcome.strategy_used,
                    'platform': outcome.platform,
                    'value_tier': value_tier,
                    'total_uses': total_uses,
                    'wins': wins,
                    'total_profit': float(total_profit)
                }).execute()
        
        except Exception as e:
            print(f"Error updating strategy performance in Supabase: {e}")

    def get_similar_auctions(self, platform: str, value_min: float, value_max: float, limit: int = 10) -> List[Dict[str, Any]]:
        """Find similar past auctions for context from Supabase."""
        
        try:
            result = self.client.table('auction_outcomes').select('raw_data').match({
                'platform': platform
            }).gte('estimated_value', value_min).lte(' estimated_value', value_max).order(
                'timestamp', desc=True
            ).limit(limit).execute()
            
            # raw_data is already dict (JSONB), no need to json.loads
            return [row['raw_data'] for row in result.data if row.get('raw_data')]
        
        except Exception as e:
            print(f"Error getting similar auctions from Supabase: {e}")
            return []
    
    def get_strategy_performance(self, strategy: str, platform: str = None, value_tier: str = None) -> Dict[str, Any]:
        """Get performance stats for a strategy from Supabase."""
        
        try:
            query = self.client.table('strategy_performance').select('*').eq('strategy', strategy)
            
            if platform:
                query = query.eq('platform', platform)
            if value_tier:
                query = query.eq('value_tier', value_tier)
            
            result = query.execute()
            
            if not result.data:
                return {"strategy": strategy, "total_uses": 0, "win_rate": 0}
            
            # Aggregate across all matching rows
            total_uses = sum(r['total_uses'] for r in result.data)
            wins = sum(r['wins'] for r in result.data)
            total_profit = sum(r['total_profit'] for r in result.data)
            
            return {
                "strategy": strategy,
                "total_uses": total_uses,
                "wins": wins,
                "win_rate": wins / max(1, total_uses),
                "total_profit": total_profit,
                "avg_profit_per_win": total_profit / max(1, wins)
            }
        
        except Exception as e:
            print(f"Error getting strategy performance from Supabase: {e}")
            return {"strategy": strategy, "total_uses": 0, "win_rate": 0}

    
    def get_best_strategy_for_context(self, platform: str, value_tier: str, min_samples: int = 5) -> Optional[str]:
        """Find the best performing strategy for a given context from Supabase."""
        
        try:
            result = self.client.table('strategy_performance').select('*').match({
                'platform': platform,
                'value_tier': value_tier
            }).gte('total_uses', min_samples).execute()
            
            if not result.data:
                return None
            
            # Calculate win rate and find best
            rows_with_rate = [
                {**r, 'win_rate': r['wins'] / max(1, r['total_uses'])}
                for r in result.data
            ]
            best = max(rows_with_rate, key=lambda x: x['win_rate'])
            return best['strategy']
        
        except Exception as e:
            print(f"Error getting best strategy from Supabase: {e}")
            return None

    def record_round(self, record: AuctionRoundRecord) -> None:
        """Save one bid round for the same auction (thread_id)."""
        data = {
            "thread_id": record.thread_id,
            "round_number": record.round_number,
            "domain": record.domain,
            "platform": record.platform,
            "estimated_value": float(record.estimated_value),
            "current_bid_at_decision": float(record.current_bid_at_decision),
            "strategy_used": record.strategy_used,
            "recommended_bid": float(record.recommended_bid),
            "decision_source": record.decision_source,
            "confidence": float(record.confidence),
            "result_round": record.result_round,
            "timestamp": record.timestamp.isoformat() if record.timestamp else None,
        }
        try:
            self.client.table("auction_rounds").upsert(
                data,
                on_conflict="thread_id,round_number",
            ).execute()
        except Exception as e:
            print(f"Error recording round to Supabase: {e}")
            raise

    def get_rounds_for_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """Return all rounds for this auction (thread_id), ordered by round_number."""
        try:
            result = (
                self.client.table("auction_rounds")
                .select("*")
                .eq("thread_id", thread_id)
                .order("round_number")
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error getting rounds from Supabase: {e}")
            return []