"""
Layer 2: LLM-Based Strategy Reasoning
Uses Claude/GPT to make intelligent bidding strategy decisions.
"""
import json
import logging
import os
import time
from typing import Dict, Any, Optional
from functools import wraps
from ..core.models import AuctionContext, StrategyDecision

logger = logging.getLogger(__name__)


def _truncate(value: Any, limit: int = 3000) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"



def retry_with_backoff(max_retries: int = 3, base_delay: float=1.0, max_delay:float =10.0):
    """Decorator for retry logic with exponential backoff.
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_retries -1:
                        delay = min(base_delay *(2 ** attempt), max_delay)
                        logger.warning(
                            "LLM call attempt failed: attempt=%s max_retries=%s retry_in_s=%.1f error=%s",
                            attempt + 1,
                            max_retries,
                            delay,
                            _truncate(e),
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "LLM call failed after retries: max_retries=%s error=%s",
                            max_retries,
                            _truncate(e),
                        )


            return None
        return wrapper
    return decorator



class LLMStrategySelector:
    """
    LLM-based strategy selection using structured prompts.
    Handles platform-specific rules and bidder analysis.
    """

    def __init__(self, provider: str = "openrouter", model: str = "google/gemini-2.5-flash-preview-09-2025"):
        self.provider = provider
        self.model = model
        self.client = self._initialize_client()

    def _initialize_client(self):
        """Initialize the LLM client based on provider."""
        if self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY environment variable required")
                return Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("anthropic package required for Anthropic models")
        elif self.provider in ["openai", "openrouter"]:
            try:
                from openai import OpenAI
                self._load_env_file()
                api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError(" OPENROUTER_API_KEY or OPENAI_API_KEY environment variable required")

                base_url = None
                if self.provider =="openrouter":
                    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

                return OpenAI(api_key=api_key, base_url=base_url)
            except ImportError:
                raise ImportError("openai package required for OpenAI models")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")


    def _load_env_file(self):
        """ Load environment variables from .env file """
        from pathlib import Path
        env_path = Path(".env")
        if env_path.exists():
            try:
                with env_path.open("r", encoding="utf-8") as env_file:
                    for raw_line in env_file:
                        line = raw_line.strip()
                        if not line or line.startswith("#"):
                            continue

                        if "=" not in line:
                            continue

                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip())
            except UnicodeDecodeError:
                logger.warning(".env file has encoding issues; skipping .env loading")
            except Exception as e:
                logger.warning("Error loading .env file; skipping .env loading: %s", _truncate(e))

    def _get_system_prompt(self) -> str:
        """Get the system prompt that defines the AI's role and reasoning framework."""
        return """# Domain Auction Strategy AI

You are an expert domain auction strategist with deep knowledge of:
- Proxy bidding mechanics across GoDaddy, NameJet, and Dynadot
- Platform-specific rules (GoDaddy's 5-minute extension, minimum increments)
- Bidder psychology and bot detection patterns
- Profit margin optimization and risk management

## Core Principles

1. **Max Budget**: You may bid up to 100% of estimated value (max budget / APR for the domain).
2. **Safety Ceiling**: Do not recommend bids above 100% of estimated value (max budget).
3. **Platform Awareness**: Respect 5-minute extensions and auto-bidding rules
4. **Opponent Analysis**: Adjust strategy based on bot vs human behavior

## Strategy Options

- `proxy_max`: Set maximum proxy bid, let platform auto-bid incrementally
- `last_minute_snipe`: Time bid for final moments to avoid counters
- `incremental_test`: Small bids to test competition without commitment
- `wait_for_closeout`: Wait for auction to end with minimal bids
- `aggressive_early`: Rare, only for must-have domains
- `do_not_bid`: Walk away when profit impossible

## Platform Rules

**GoDaddy**: 5-minute extension on late bids, $5 minimum increment
**NameJet**: No extensions, $5 increment, fast-paced
**Dynadot**: Variable increments, occasional extensions

## Decision Framework

1. **Value Tier Analysis**:
   - High ($1000+): Conservative, avoid escalation
   - Medium ($100-1000): Balanced approach
   - Low (<$100): Aggressive or wait for closeout

2. **Competition Assessment**:
   - 0 bidders: Wait for closeout or proxy max early
   - 1-2 bidders: Proxy max with safe limits
   - 3+ bidders: Consider sniping or incremental testing

3. **Bot Detection Response**:
   - Bots: Prefer sniping to minimize reaction window
   - Humans: More flexible, can use proxy strategies

4. **Time Pressure**:
   - >1 hour: Strategic positioning
   - <1 hour: Execute final strategy
   - <5 minutes: Sniping mode (GoDaddy extension aware)"""

    def _get_user_prompt(
        self,
        context: AuctionContext,
        market_intelligence: Optional[Dict[str, Any]] = None,
        same_auction_attempts: Optional[list] = None,
    ) -> str:
        """Generate the user prompt with auction context."""

        # Calculate financial boundaries (100% = max budget / APR)
        safe_max = context.estimated_value * 1.0
        hard_ceiling = context.estimated_value * 1.0

        # Determine value tier
        if context.estimated_value >= 1000:
            value_tier = "HIGH"
            tier_note = "Conservative approach, avoid emotional escalation"
        elif context.estimated_value >= 100:
            value_tier = "MEDIUM"
            tier_note = "Balanced strategy, test competition"
        else:
            value_tier = "LOW"
            tier_note = "Aggressive or wait for closeout   "

        market_intel_section = ""

        if market_intelligence:
            bidder_intel = market_intelligence.get("bidder_intelligence", {})
            domain_intel = market_intelligence.get("domain_intelligence", {})
            archetype = market_intelligence.get("auction_archetype", {})

            market_intel_section = "\n**Market Intelligence (Layer 0)**:\n"
            
            if bidder_intel.get("found"):
                market_intel_section += f"- Bidder Profile: {bidder_intel.get('total_auctions_participated', 0)} auctions, "
                market_intel_section += f" Win Rate: {bidder_intel.get('win_rate', 0):.1%},"
                market_intel_section += f" Aggressive:{bidder_intel.get('is_aggressive', False)},"
                market_intel_section += f" Sniper:{bidder_intel.get('is_sniper', False)}\n"

            elif bidder_intel.get("behavioral_pattern", {}).get("found"):

                bp = bidder_intel["behavioral_pattern"]
                market_intel_section += f"- Bidder Behavior Pattern: cluster={bp.get('behavior_cluster','unknown')},"
                market_intel_section += f" fold probability={bp.get('fold_probability', 0):.1%},"
                market_intel_section += f"avg_win_rate={bp.get('avg_win_rate', 0):.1%},"
                market_intel_section += f"sample_size={bp.get('sample_size', 0)},"
                market_intel_section += f"Recommendation={bp.get('strategic_recommendation', 'N/A')}\n"

            if domain_intel.get("found"):
                market_intel_section += f"- Domain History: {domain_intel.get('number_of_auctions', 0)} past auctions,"
                market_intel_section += f"Avg Final Price: ${domain_intel.get('average_final_price', 0):.2f},"
                market_intel_section += f"Volatile:{domain_intel.get('is_volatile', False)}\n"

            if archetype.get("found"):
                market_intel_section += f"- Auction Archetype: {archetype.get('escalation_speed', 'unknown')}escalation, "
                market_intel_section += f"Bot Ratio : {archetype.get('bot_ratio', 0):.1%}\n "

        # Debug: Print market intelligence section to verify what's being sent to LLM
        if market_intelligence:
            logger.debug(
                "Market intelligence section for LLM prompt: %s",
                _truncate(market_intel_section),
            )

        # Previous attempts in THIS auction (when thread_id is set and we got outbid before)
        same_auction_section = ""
        if same_auction_attempts:
            lines = [
                f"- Round {a['round']}: strategy={a['strategy_used']}, result={a['result_round']}"
                for a in (same_auction_attempts or [])
            ]
            same_auction_section = (
                "\n**Previous attempts in THIS auction**:\n"
                + "\n".join(lines)
                + "\nConsider trying a different strategy if a previous one did not work (e.g. outbid).\n"
            )

        # Platform-specific notes
        platform_rules = {
            "godaddy": "5-minute extension on late bids. Snipe timing must account for auto-extensions.",
            "namejet": "No extensions, fast-paced. Immediate execution required.",
            "dynadot": "Variable increments, occasional extensions. Monitor closely."
        }

        prompt = f"""## Auction Context

**Domain**: {context.domain}
**Platform**: {context.platform.upper()}
**Platform Rules**: {platform_rules.get(context.platform, "Standard proxy bidding rules")}

**Financials**:
- Estimated Value: ${context.estimated_value:.2f}
- Current Bid: ${context.current_bid:.2f}
- Your Current Proxy: ${context.your_current_proxy:.2f} (0 = none)
- Budget Available: ${context.budget_available:.2f}
- Safe Max (100% max budget): ${safe_max:.2f}
- Hard Ceiling (100% of value): ${hard_ceiling:.2f}

**Competition**:
- Active Bidders: {context.num_bidders}
- Hours Remaining: {context.hours_remaining:.1f}

**Bidder Analysis**:
- Bot Detected: {context.bidder_analysis['bot_detected']}
- Corporate Buyer: {context.bidder_analysis['corporate_buyer']}
- Aggression Score: {context.bidder_analysis['aggression_score']}/10
- Avg Reaction Time: {context.bidder_analysis['reaction_time_avg']:.1f}s

**Value Tier**: {value_tier} - {tier_note}
{market_intel_section}
{same_auction_section}

## Task

Analyze this auction and recommend the optimal bidding strategy. Consider:

1. **Budget**: Stay within estimated value (max budget / APR).
2. **Competition**: How many bidders and their behavior patterns?
3. **Platform Mechanics**: How do {context.platform} rules affect timing?
4. **Risk Assessment**: What's the likelihood of overpaying?
5. **Timing**: When should we act given remaining time?

## Required Output Format

Respond with ONLY a valid JSON object matching this schema:

```json
{{
  "strategy": "proxy_max|last_minute_snipe|incremental_test|wait_for_closeout|aggressive_early|do_not_bid",
  "recommended_bid_amount": <float>,
  "confidence": <0.0-1.0>,
  "risk_level": "low|medium|high",
  "reasoning": "<detailed explanation with strategy rationale and profit calculations>"
}}
```

**Important**:
- recommended_bid_amount = your proxy maximum (what you set, not next visible bid)
- confidence = certainty in your strategy (0.0-1.0)
- reasoning = minimum 100 characters explaining your logic
- Stay within max budget (estimated value)"""

        return prompt

    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    def _call_llm(self,system_prompt: str, user_prompt: str) -> Optional[str]:

        """
        Make the actual LLM API call with retry logic.
        Returns the raw response content or raises an exception.
        """
        if self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.1,
                system=system_prompt,
                messages=[
                    {"role":"user","content":user_prompt}
                ]
            )
            return response.content[0].text
        
        elif self.provider in ["openai", "openrouter"]:
            response= self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role":"system","content":system_prompt},
                    {"role":"user","content":user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            return response.choices[0 ].message.content
        return None

    def get_strategy_decision(
        self,
        context: AuctionContext,
        market_intelligence: Optional[Dict[str, Any]] = None,
        historical_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[StrategyDecision]:
        """
        Get strategy decision from LLM.
        Returns StrategyDecision object or None if LLM call fails.
        """
        try:
            request_started = time.perf_counter()
            logger.info(
                "LLM strategy input received: domain=%s platform=%s estimated_value=%s current_bid=%s num_bidders=%s hours_remaining=%s provider=%s model=%s",
                context.domain,
                context.platform,
                context.estimated_value,
                context.current_bid,
                context.num_bidders,
                context.hours_remaining,
                self.provider,
                self.model,
            )
            same_auction_attempts = (historical_context or {}).get("same_auction_attempts") or []
            system_prompt = self._get_system_prompt()
            user_prompt = self._get_user_prompt(
                context,
                market_intelligence=market_intelligence,
                same_auction_attempts=same_auction_attempts,
            )

            # Initialize content to avoid scope errors
            content = None

            if self.provider == "anthropic":
                logger.debug("Using Anthropic API for domain=%s model=%s", context.domain, self.model)
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    temperature=0.1,  # Low temperature for consistent strategy
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )
                content = response.content[0].text

            elif self.provider in ["openai", "openrouter"]:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
                content = response.choices[0].message.content

            logger.info(
                "LLM raw response received: domain=%s response_preview=%s",
                context.domain,
                _truncate(content),
            )

            # Parse JSON response (only if we got content from API)
            if content is not None:
                try:
                    parsed = json.loads(content.strip())
 
                    # Add missing required fields with defaults
                    parsed.setdefault('should_increase_proxy', None)
                    parsed.setdefault('next_bid_amount', None)
                    parsed.setdefault('max_budget_for_domain', parsed.get('recommended_bid_amount', 0))

                    # Validate and create StrategyDecision object
                    decision = StrategyDecision(**parsed)

                    latency_ms = int((time.perf_counter() - request_started) * 1000)
                    logger.info(
                        "LLM strategy decision ready: domain=%s strategy=%s recommended_bid_amount=%s risk_level=%s confidence=%s latency_ms=%s",
                        context.domain,
                        decision.strategy,
                        decision.recommended_bid_amount,
                        decision.risk_level,
                        decision.confidence,
                        latency_ms,
                    )

                    return decision

                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(
                        "Failed to parse LLM response: domain=%s error=%s raw_content=%s",
                        context.domain,
                        _truncate(e),
                        _truncate(content),
                    )
                    return None
            else:
                # API call failed, content never set
                logger.warning("LLM call returned empty content: domain=%s", context.domain)
                return None

        except Exception as e:
            logger.exception(
                "LLM strategy call failed: domain=%s error=%s",
                getattr(context, "domain", "unknown"),
                _truncate(e),
            )
            return None


