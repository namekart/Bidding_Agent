# rule_based_strategy.py - Rule-Based Strategy Fallback

## Purpose
This file implements Layer 4's rule-based strategy selector: a deterministic, algorithmic approach to strategy selection that serves as a fallback when LLM validation fails. Provides explainable, rule-driven decisions based on auction conditions and domain value tiers.

## Core Logic Approach
**Deterministic Fallback**: Pure algorithmic logic with no AI involvement. Ensures system always produces a valid strategy decision, even when AI fails. Based on proven auction strategies and value-based tiering.

**Transparency First**: Every decision is fully explainable with clear reasoning based on observable auction conditions.

## Key Components

### RuleBasedStrategySelector Class
**Purpose**: Encapsulates all rule-based decision logic.

**Approach**: Static methods for stateless computation. Clean separation between tier analysis and strategy selection.

## Core Logic Methods

### determine_value_tier()
**Input**: estimated_value (float)
**Output**: String tier ("high", "medium", "low")

**Logic**:
```python
if estimated_value >= 1000: return "high"
elif estimated_value >= 100: return "medium"
else: return "low"
```

**Why These Thresholds?**
- **$1000+ High**: Premium domains needing conservative strategies
- **$100-1000 Medium**: Balanced approach for commercial domains
- **<$100 Low**: Aggressive or opportunistic strategies

**Approach**: Based on domain industry standards and typical auction dynamics.

### calculate_safe_max()
**Input**: estimated_value (float)
**Output**: Safe maximum bid (float)

**Logic**:
```python
return estimated_value * 0.70  # 70% rule
```

**Why 70%?**: Provides 30% profit margin buffer. Conservative approach prevents winner's curse while allowing competitive bidding.

## Strategy Selection by Tier

### High Value Strategy (>=$1000)
**Input**: AuctionContext
**Output**: StrategyDecision

**Decision Tree**:
1. **Early Stage + No Bidders**: Wait for closeout if <1 hour remaining
2. **Bot Detected**: Last-minute snipe to minimize reaction window
3. **Multiple Bidders**: Conservative proxy max
4. **High Competition**: Sniping to avoid escalation

**Logic**: Conservative approach protects premium domain investments. Prioritizes profit preservation over winning at all costs.

### Medium Value Strategy ($100-1000)
**Input**: AuctionContext
**Output**: StrategyDecision

**Decision Tree**:
1. **GoDaddy + Late Stage**: Sniping respects 5-minute extensions
2. **High Competition**: Incremental testing to gauge interest
3. **Standard Case**: Proxy max for steady competition

**Logic**: Balanced approach between aggression and caution. Platform-aware timing prevents extension traps.

### Low Value Strategy (<$100)
**Input**: AuctionContext
**Output**: StrategyDecision

**Decision Tree**:
1. **No Bidders**: Wait for closeout (zero risk)
2. **Competition Present**: Incremental testing (low-value allows experimentation)

**Logic**: Opportunistic for low-value domains. Closeout waiting maximizes profit potential with minimal risk.

## Strategy Decision Structure

Each strategy method returns StrategyDecision with:
- **Strategy**: One of 6 predefined options
- **Bid Amount**: Calculated based on safe_max and strategy
- **Confidence**: Fixed values based on rule certainty (0.7-0.9)
- **Risk Level**: "low", "medium", "high" based on strategy
- **Reasoning**: Detailed explanation of rule application

**Example Structure**:
```python
return StrategyDecision(
    strategy="proxy_max",
    recommended_bid_amount=safe_max,
    confidence=0.85,
    risk_level="medium",
    reasoning=f"HIGH-VALUE BALANCED: {num_bidders} bidders present..."
)
```

## Platform-Specific Logic

### GoDaddy Handling
**Special Case**: Hours remaining < 1.0 triggers sniping
**Reasoning**: Respects 5-minute extension rule. Prevents auto-extensions that could prolong auction.

### Bot Detection Response
**Strategy**: Prefer sniping over proxy
**Reasoning**: Minimizes window for bot reactions. Bots excel at rapid proxy wars but struggle with unpredictable timing.

## Integration with Pipeline

### Fallback Triggering
- Called when LLM validation fails
- Provides deterministic backup to AI
- Always produces valid StrategyDecision

### Output Usage
- Fed directly to proxy logic layer
- No validation needed (rules are inherently safe)
- Maintains full decision traceability

## Decision Rationale Documentation

### Why Specific Strategies?
- **Proxy Max**: Steady competition, platform auto-bidding handles increments
- **Last-Minute Snipe**: Avoids counters, respects platform timing rules
- **Incremental Test**: Gauges competition without full commitment
- **Wait for Closeout**: Zero-risk when no meaningful competition
- **Aggressive Early**: Rare, only for must-have domains
- **Do Not Bid**: When profit impossible or rules dictate caution

### Confidence Calibration
- **High Confidence (0.85-0.9)**: Clear rule matches, obvious strategies
- **Medium Confidence (0.7-0.8)**: Balanced decisions with some uncertainty
- **Lower Confidence**: When rules provide less clear guidance

## Performance Characteristics

### Execution Speed
- **Instant**: Pure Python logic, no API calls
- **Deterministic**: Same input always produces same output
- **Lightweight**: Minimal computation required

### Reliability
- **Always Works**: No external dependencies
- **Predictable**: Behavior fully specified by rules
- **Testable**: Easy to unit test all decision paths

## Testing Strategy

### Coverage Requirements
- **All Tiers**: High, medium, low value domains
- **Platform Variations**: GoDaddy, NameJet, Dynadot
- **Bidder Scenarios**: No bidders, few bidders, many bidders
- **Bot Conditions**: Bot detected vs human behavior
- **Time Pressure**: Various hours remaining values

### Edge Case Testing
- **Tier Boundaries**: Exactly $100, $1000 values
- **Extreme Values**: Very low/high bid amounts
- **Platform Rules**: Extension timing, increment differences

## Rule Evolution

### How to Modify Rules
1. **Identify Pattern**: Observe auction outcomes vs rule predictions
2. **Data-Driven**: Base changes on historical performance
3. **Conservative Updates**: Bias toward safety over aggression
4. **Testing**: Validate changes don't break existing logic

### Rule Philosophy
- **Conservative**: Prefer profit preservation over winning
- **Platform Aware**: Respect mechanics of each auction site
- **Psychology Based**: Account for human vs bot bidder behavior
- **Value Appropriate**: Different strategies for different value tiers

## Comparison with LLM Approach

### Rule-Based Advantages
- **Explainable**: Clear reasoning for every decision
- **Fast**: No API latency or costs
- **Reliable**: No model failures or hallucinations
- **Deterministic**: Consistent behavior

### Rule-Based Limitations
- **Inflexible**: Cannot adapt to novel situations
- **Pattern-Based**: Misses subtle bidder psychology
- **Static**: Requires manual updates for new patterns

### Why Both Approaches?
- **AI for Intelligence**: Handles complex, novel scenarios
- **Rules for Safety**: Provides reliable fallback when AI fails
- **Hybrid Strength**: Best of both deterministic safety and AI adaptability

This rule-based layer ensures the system always has a safe, logical strategy available, even when AI systems encounter issues.





