import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from ..core.models import AuctionContext

class MarketIntelligenceLoader:
    """ Load 0 Market Intelligence - Read-only memory from offline preprocessing.
        Loads parquet files once at startup and provides fast lookups during runtime.
    """

    def __init__(self, data_dir:str = "."):
        """ Load all parquet files at initialization."""
        data_path = Path(__file__).resolve().parents[1] / "data" / "parquet"

        # Load Layer 0 intelligence files 
        self.bidder_profiles = pd.read_parquet(data_path / "layer0_bidder_profiles.parquet")
        self.domain_stats = pd.read_parquet(data_path / "layer0_domain_stats.parquet")
        self.auction_archetypes = pd.read_parquet(data_path / "layer0_auction_archetypes.parquet")

        # Create lookup indexes for fast access
        self._index_bidder_profiles()
        self._index_domain_stats()

    def _index_bidder_profiles(self):
        """Create lookup index for bidder profiles."""

        if 'bidder_id' in self.bidder_profiles.columns:
            self.bidder_profiles_indexed = self.bidder_profiles.set_index('bidder_id')

        elif 'bidder_name' in self.bidder_profiles.columns:
            self.bidder_profiles_indexed = self.bidder_profiles.set_index('bidder_name')

        else:
            self.bidder_profiles_indexed = self.bidder_profiles.set_index(self.bidder_profiles.columns[0])

    
    def _index_domain_stats(self):
        """Create lookup index for domain stats."""
        if 'domain' in self.domain_stats.columns:
            self.domain_stats_indexed = self.domain_stats.set_index('domain')
        else :
            self.domain_stats_indexed = self.domain_stats.set_index(self.domain_stats.columns[0])
    
    def get_bidder_intelligence(self, bidder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Lookup bidder behavioral intelligence.
        Returns compact signals for decision-making.
        """

        if not bidder_id:
            return {"found": False}

        try:
            bidder_data = self.bidder_profiles_indexed.loc[bidder_id]

            return {
                "found": True,
                "total_auctions_participated": bidder_data.get("total_auctions", 0),
                "bids_per_auction": bidder_data.get("total_bids", 0) / max(bidder_data.get("total_auctions", 1), 1),
                "average_bid_increase": bidder_data.get("avg_bid_increase", 0),
                "highest_ever_bid": bidder_data.get("max_bid", 0),
                "win_rate": bidder_data.get("win_rate", 0),
                "late_bid_ratio": bidder_data.get("late_bid_ratio", 0),
                "average_reaction_time": bidder_data.get("avg_reaction_time", 0),
                "proxy_bid_usage_ratio": bidder_data.get("proxy_usage", 0),

                # Derived Signals
                "is_aggressive": bidder_data.get("avg_bid_increase", 0) > 50,
                "is_sniper": bidder_data.get("late_bid_ratio", 0) > 0.7,
                "is_proxy_heavy": bidder_data.get("proxy_usage", 0) > 0.8

            }
        except (KeyError, AttributeError):
            return {"found": False}
    
    def get_domain_intelligence(self, domain:str, estimated_value: float = None) -> Dict[str, Any]:
        """
        Multi-tier domain intelligence with pattern-based fallback.

        Tier 1: Exact domain match
        Tier 2: TLD pattern
        Tier 3: Value tier pattern
        Tier 4: Platform average
        """
        try:
            domain_data = self.domain_stats_indexed.loc[domain]
            
            return {
                "found": True,
                "match_type": "exact",
                "average_final_price": domain_data.get("avg_final_price", 0),
                "price_volatility": domain_data.get("volatility", 0),
                "number_of_auctions": domain_data.get("avg_bids", 0),
                "is_volatile": domain_data.get("volatility", 0) > 0.3,
                "has_history": True,
                "confidence": 0.95
            }
        except (KeyError, AttributeError):
            pass

        # tier 2: TLD pattern
        tld_pattern = self.get_tld_pattern(domain)
        if tld_pattern.get("found"):
            return {
                "found": True,
                "match_type": "tld_pattern",
                "average_final_price": tld_pattern["avg_final_price"],
                "price_volatility": tld_pattern["avg_volatility"],
                "tld_sample_size": tld_pattern["sample_size"],
                "is_premium_tld": tld_pattern["is_premium_tld"],
                "is_budget_tld": tld_pattern["is_budget_tld"],
                "price_percentiles": tld_pattern["price_percentiles"],
                "has_history": False,
                "confidence": min(0.75, tld_pattern["sample_size"]/50)
            }

        if estimated_value:
            value_pattern = self.get_value_tier_pattern(estimated_value)
            if value_pattern.get("found"):
                return {
                    "found": True,
                    "match_type": "value_tier",
                    "average_final_price": value_pattern["avg_final_price"],
                    "recommended_max_bid": value_pattern["recommended_max_bid"],
                    "value_tier_sample_size": value_pattern["sample_size"],
                    "has_history": False,
                    "confidence": value_pattern["confidence"]
                }

        # Tier 4: Platform average( last resort)
        if len(self.domain_stats) >0:
            platform_avg = self.domain_stats['avg_final_price'].mean()
            return {
                "found": True,
                "match_type": "platform_average",
                "average_final_price": float(platform_avg),
                "has_history": False,
                "confidence": 0.30,
                "warning": "Using platform-wide average. Low confidence."

            }
        return {"found": False, "match_type": "none"}                      
    def get_tld_pattern(self, domain:str) ->Dict[str, Any]:
        """
        Extract TLD Patterns when exact domain is not found.
        Example: BudgetGone.xyz -> analyze all .xyz domains
        """
        try:
            #Extract TLD from domain
            if '.' not in domain:
                return {"found": False, "reason": "No TLD in  domain"}
            tld = '.' + domain.split('.')[-1]

            # Filter domains with same TLD
            if 'domain' not in self.domain_stats.columns:
                return {"found": False, "reason": "No domain column"}

            tld_domains = self.domain_stats[
                self.domain_stats['domain'].str.endswith(tld, na=False)
            ]
            if len(tld_domains)==0:
                return {"found": False, "reason": f"No {tld} domains in history"}

            #Calculate TLD statistics
            avg_final_price = tld_domains['avg_final_price'].mean()
            median_final_price = tld_domains['avg_final_price'].median()
            price_std = tld_domains['avg_final_price'].std()
            count = len(tld_domains)
            avg_volatility = tld_domains['volatility'].mean() if 'volatility' in tld_domains.columns else 0

            return {
                "found": True,
                "tld": tld,
                "sample_size": int(count),
                "avg_final_price": float(avg_final_price),
                "medium_final_price": float(median_final_price),
                "price_std": float(price_std),
                "avg_volatility": float(avg_volatility),
                "is_premium_tld": tld in ['.com','.net', '.org'],
                "is_budget_tld": tld in['.xyz', '.online', '.site','.club'],
                "price_percentiles":{
                    "p25": float(tld_domains['avg_final_price'].quantile(0.25)),
                    "p50": float(tld_domains['avg_final_price'].quantile(0.50)),
                    "p75": float(tld_domains['avg_final_price'].quantile(0.75)),
                    "p90":float(tld_domains['avg_final_price'].quantile(0.90))
                }
            }
        except Exception as e:
            return {"found": False, "error": str(e)}

    def get_value_tier_pattern(self, estimated_value: float) -> Dict[str, Any]:
        """
        Find domains with similar estimate value to detect pricing patterns.
        Example: $200-400 range domains typically sell at 68% of estimate
        """
        try:
            if len(self.domain_stats) ==0:
                return {"found":False, "reason": "No domain stats"}

            # Define value tier range(+/- 30%)
            lower_bound = estimated_value * 0.70
            upper_bound = estimated_value* 1.30

            #This assumes you have estimated value in your parquet
            # If not , use avg_final_price as proxy

            if 'avg_final_price' in self.domain_stats.columns:
                tier_domains = self.domain_stats[
                    (self.domain_stats['avg_final_price'] >= lower_bound) &
                    (self.domain_stats['avg_final_price'] <= upper_bound)
                ]
            else:
                return {"found": False, "reason": "No price data"}
            
            if len(tier_domains) ==0:
                return {"found": False, "reason": f"No domains in ${lower_bound:.0f}-${upper_bound:.0f} range"}

            # Calculate Statictics
            avg_price = tier_domains['avg_final_price'].mean()
            median_price = tier_domains['avg_final_price'].median()
            count = len(tier_domains)

            return {
                "found": True,
                "value_range": f"${lower_bound:.0f}-${upper_bound:.0f}",
                "sample_size": int(count),
                "avg_final_price": float(avg_price),
                "median_final_price": float(median_price),
                "recommended_max_bid": float(median_price * 0.85),
                "confidence": min(0.9, count/100)


            }
        except Exception as e:
            return {"found": False,"error": str(e)}

    def get_bidder_behavioral_pattern(self, live_aggression: float,live_reaction_time: float)-> Dict[str,Any]:
        """
        Find bidders with similar behavior patterns when exact bidder ID not found.
        Example: Low agggression(1.5) + slow reaction (150s) -> match to casual bidder cluster
        """
        try:
            if len(self.bidder_profiles) == 0:
                return {"found": False, "reason": "No bidder profiles"}
            
            # Define behavioral similarity thresholds
            aggression_tolerance = 2.0
            reaction_tolerance = 60.0

            # Normalize aggression score(live is 0-10, parquet might be avg_bid_increase)
            # Map avg_bid_increase to 0-10 scale (0-100 -> 0-10)

            if 'avg_bid_increase' in self.bidder_profiles.columns:
                self.bidder_profiles['aggression_normalized'] = (
                    self.bidder_profiles['avg_bid_increase'] / 10
                ).clip(0,10)
            else:
                return {"found": False, "reason": "No aggression data"}

            # Find similar bidders
            similar_bidders = self.bidder_profiles[
                (abs(self.bidder_profiles['aggression_normalized'] -live_aggression)<=aggression_tolerance) &
                (abs(self.bidder_profiles.get('avg_reaction_time',999) -live_reaction_time) <= reaction_tolerance)

            ]

            if len(similar_bidders) ==0:
                # Fallback to just aggression-based matching
                similar_bidders = self.bidder_profiles[
                    abs(self.bidder_profiles['aggression_normalized'] - live_aggression) <= aggression_tolerance
                ]

            if len(similar_bidders) ==0:
                return {"found": False, "reason": "No similar behavioral patterns"}

            # Calculate cluster statistics
            avg_win_rate = similar_bidders['win_rate'].mean() if 'win_rate' in similar_bidders.columns else 0
            avg_late_bid_ratio =similar_bidders['late_bid_ratio'].mean() if 'late_bid_ratio' in similar_bidders.columns else 0
            count = len(similar_bidders)

            # Classify behavior type
            behavior_type = "unknown"
            if avg_win_rate > 0.6:
                behavior_type = "professional"
            elif avg_win_rate < 0.15:
                behavior_type = "casual"
            elif avg_late_bid_ratio > 0.7:
                behavior_type = "sniper"
            else:
                behavior_type = "regular"

            # Calculate fold Probability (inverse of winrate)
            fold_probability = 1 - avg_win_rate

            return {
                "found": True,
                "behavior_cluster": behavior_type,
                "sample_size": int(count),
                "avg_win_rate": float(avg_win_rate),
                "fold_probability": float(fold_probability),
                "avg_late_bid_ratio": float(avg_late_bid_ratio),
                "is_aggressive_cluster": live_aggression > 6.0,
                "is_passive_cluster": live_aggression < 3.0,
                "strategic_recommendation": self._get_counter_strategy(behavior_type, fold_probability)
            }
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    def _get_counter_strategy(self, behavior_type: str, fold_prob: float) ->str:
        """ Helper to recommend counter-strategy based on opponent behavior."""
        if behavior_type == "professional":
            return "Avoid escalation. Set firm cap and be prepared to walk away."
        elif behavior_type =="casual" or fold_prob > 0.85:
            return "Opponent likely to fold. Set moderate cap and bid confidently."
        elif behavior_type =="sniper":
            return "Counter-snipe in final seconds or use early proxy to discourage."
    
        else:
            return "Standard competitive approach.Monitor and adjust dynamically."
    
    def _estimate_win_probability(
        self, 
        context: AuctionContext, 
        bidder_intel: Dict[str, Any], 
        domain_intel: Dict[str, Any], 
        archetype: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estimate probability of winning based on multiple signals.
        Uses Bayesian-style combination of evidence.
        """
        # Base probability from competition level
        if context.num_bidders == 0:
            base_prob = 0.95
        elif context.num_bidders == 1:
            base_prob = 0.70
        elif context.num_bidders == 2:
            base_prob = 0.50
        else:
            base_prob = 0.30
        
        # Adjust for bidder behavior
        if bidder_intel.get("found"):
            opponent_win_rate = bidder_intel.get("win_rate", 0.5)
            # Your win prob inversely related to opponent's
            base_prob *= (1 - opponent_win_rate * 0.5)   # Moderate adjustment
        
        # Check behavioral pattern
        behavioral_pattern = bidder_intel.get("behavioral_pattern", {})
        if behavioral_pattern.get("found"):
            fold_prob = behavioral_pattern.get("fold_probability", 0.5)
            base_prob += (fold_prob - 0.5) * 0.2  # Adjust by fold tendency
        
        # Adjust for budget constraints (100% = max budget)
        safe_max = context.estimated_value * 1.0
        if context.budget_available < safe_max:
            # Budget constraint reduces win probability
            budget_ratio = context.budget_available / safe_max
            base_prob *= (0.5 + 0.5 * budget_ratio)  # Scale down if insufficient budget
        
        # Adjust for domain volatility
        if domain_intel.get("found"):
            volatility = domain_intel.get("price_volatility", 0)
            if volatility > 0.3:
                base_prob *= 0.90  # Volatile domains are harder to predict
        
        # Cap between 0.05 and 0.95
        final_prob = max(0.05, min(0.95, base_prob))
        
        return {
            "win_probability": float(final_prob),
            "confidence_level": "high" if final_prob > 0.7 else "medium" if final_prob > 0.4 else "low",
            "factors": {
                "competition_level": context.num_bidders,
                "opponent_strength": 1 - bidder_intel.get("win_rate", 0.5) if bidder_intel.get("found") else 0.5,
                "budget_adequacy": context.budget_available / (context.estimated_value * 1.0),
                "domain_predictability": 1 - domain_intel.get("price_volatility", 0.5) if domain_intel.get("found") else 0.5
            }
        }

    def _calculate_expected_value(
        self,
        context: AuctionContext,
        win_prob_data: Dict[str, Any],
        domain_intel: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate expected value of bidding to guide resource allocation.
        
        Expected Value = (Win Probability × Profit if Win) - (Bid Amount × Risk)
        """
        win_prob = win_prob_data["win_probability"]
        
        # Estimate expected final price
        if domain_intel.get("found") and domain_intel.get("average_final_price", 0) > 0:
            expected_final_price = domain_intel["average_final_price"]
        else:
            # Fallback: assume 65% of estimated value
            expected_final_price = context.estimated_value * 0.65
        
        # Calculate expected profit
        expected_profit = context.estimated_value - expected_final_price
        expected_margin = expected_profit / context.estimated_value if context.estimated_value > 0 else 0
        
        # Expected value calculation
        ev = win_prob * expected_profit
        
        # Risk-adjusted EV (account for volatility)
        volatility_factor = domain_intel.get("price_volatility", 0.3) if domain_intel.get("found") else 0.3
        risk_adjusted_ev = ev * (1 - volatility_factor * 0.5)
        
        # ROI calculation
        roi = risk_adjusted_ev / expected_final_price if expected_final_price > 0 else 0
        
        return {
            "expected_final_price": float(expected_final_price),
            "expected_profit": float(expected_profit),
            "expected_margin": float(expected_margin),
            "expected_value": float(ev),
            "risk_adjusted_ev": float(risk_adjusted_ev),
            "roi": float(roi),
            "recommendation": "STRONG_BID" if roi > 1.5 else "MODERATE_BID" if roi > 0.8 else "WEAK_BID"
        }

    def _calculate_resource_score(
        self,
        win_prob_data: Dict[str, Any],
        ev_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate resource optimization score to prioritize auctions.
        Higher score = better opportunity for resource allocation.
        
        Score = (Win Probability × Expected Margin) / Bid Amount
        """
        win_prob = win_prob_data["win_probability"]
        expected_margin = ev_data["expected_margin"]
        roi = ev_data["roi"]
        
        # Combined score
        resource_score = win_prob * expected_margin * (1 + roi)
        
        # Priority classification
        if resource_score > 1.0:
            priority = "HIGH"
            action = "Allocate maximum safe budget"
        elif resource_score > 0.5:
            priority = "MEDIUM"
            action = "Allocate moderate budget"
        else:
            priority = "LOW"
            action = "Minimal bid or skip"
        
        return {
            "score": float(resource_score),
            "priority": priority,
            "action_recommendation": action,
            "explanation": f"Win prob {win_prob:.1%} × Margin {expected_margin:.1%} × ROI {roi:.2f} = {resource_score:.3f}"
        }




    
    def get_auction_archetype(self, platform: str, category: Optional[str]= None) -> Dict[str, Any]:
        """
        Lookup auction archetype patterns for platform/category.
        Returns macro behavior pattern.
        Note: Current parquet doesn't have platform column, so we return general archetype stats.
        """
        try:
            # Since platform column doesn't exist, return aggregate stats
            if len(self.auction_archetypes) == 0:
                return {"found": False}
            
            # Get average archetype stats across all auctions
            avg_late_bid_ratio = self.auction_archetypes["late_bid_ratio"].mean()
            avg_bid_jump = self.auction_archetypes["avg_bid_jump"].mean()
            avg_duration = self.auction_archetypes["duration_sec"].mean()

            return {
                "found": True,
                "escalation_speed": "fast" if avg_bid_jump > 50 else "slow",
                "bot_ratio": 0.0,  # Not in current schema
                "sniper_dominated": avg_late_bid_ratio > 0.7,
                "proxy_driven": avg_late_bid_ratio < 0.3,
                "avg_late_bid_ratio": float(avg_late_bid_ratio),
                "avg_bid_jump": float(avg_bid_jump),
                "avg_duration_sec": float(avg_duration)
            }  

        except Exception as e:
            return {"found": False, "error": str(e)}

    
    def enrich_context(self, context: AuctionContext, last_bidder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all market intelligence signals with pattern-based fallbacks.
        This is the main method called during live bidding.
        """
        # Try exact bidder match first
        bidder_intel = self.get_bidder_intelligence(last_bidder_id)
        
        # If no exact match, try behavioral pattern matching
        if not bidder_intel.get("found") and last_bidder_id:
            # Use live bidder analysis to find similar patterns
            live_aggression = context.bidder_analysis.get('aggression_score', 5.0)
            live_reaction_time = context.bidder_analysis.get('reaction_time_avg', 60.0)
            
            behavioral_pattern = self.get_bidder_behavioral_pattern(
                live_aggression, 
                live_reaction_time
            )
            bidder_intel["behavioral_pattern"] = behavioral_pattern
        
        # Get domain intelligence with fallback (pass estimated_value for pattern matching)
        domain_intel = self.get_domain_intelligence(
            context.domain,
            estimated_value=context.estimated_value
        )
        
        # Get auction archetype
        archetype = self.get_auction_archetype(context.platform)
        
        # Calculate win probability and expected value
        win_probability = self._estimate_win_probability(
            context, bidder_intel, domain_intel, archetype
        )
        
        expected_value_analysis = self._calculate_expected_value(
            context, win_probability, domain_intel
        )
        
        return {
            "bidder_intelligence": bidder_intel,
            "domain_intelligence": domain_intel,
            "auction_archetype": archetype,
            "win_probability": win_probability,
            "expected_value_analysis": expected_value_analysis,
            "resource_optimization_score": self._calculate_resource_score(
                win_probability, expected_value_analysis
            )
        }