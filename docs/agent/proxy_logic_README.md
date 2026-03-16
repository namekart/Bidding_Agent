# proxy_logic.py - Proxy Bidding Logic & Outbid Analysis

## Purpose
This file implements the proxy bidding intelligence that handles the critical question: "Should I increase my proxy bid when outbid, and if so, by how much?" It analyzes current proxy positions against bid progression and makes mathematically sound decisions about proxy adjustments.

## Core Logic Approach
**Mathematical Precision**: Uses safe maximum calculations (70% of value) to determine profitable bidding limits. Makes proxy decisions based on whether current competition allows maintaining profit margins.

**Scenario-Based Logic**: Handles three key proxy situations:
1. No current proxy (initial bid setup)
2. Current bid exceeds safe maximum (accept loss)
3. Safe maximum above current bid (strategic increase)

## Key Components

### ProxyLogicHandler Class
**Purpose**: Central coordinator for all proxy bidding decisions.

**Approach**: Static methods for stateless computation. Clean separation between analysis and application logic.

## Platform Increment Logic

### get_platform_increment()
**Input**: platform (string), current_bid (float)
**Output**: Increment amount (float)

**Logic**:
```python
increments = {
    "godaddy": 5.0,
    "namejet": 5.0,
    "dynadot": max(5.0, current_bid * 0.05)  # 5% for higher bids
}
return increments.get(platform.lower(), 5.0)
```

**Why Platform-Specific?**
- **GoDaddy/NameJet**: Fixed $5 increments standard
- **Dynadot**: Percentage-based for higher-value auctions
- **Fallback**: $5 default for unknown platforms

**Approach**: Reflects actual platform mechanics to avoid bid calculation errors.

## Core Decision Logic

### calculate_safe_max()
**Input**: estimated_value (float)
**Output**: Safe maximum bid (float)

**Logic**:
```python
return estimated_value * 0.70  # 70% rule
```

**Why 70%?**: Provides 30% profit margin buffer. Conservative enough to avoid winner's curse while competitive enough for participation.

**Mathematical Basis**: Based on auction theory that winners often overpay by 20-40% due to emotional escalation.

## Proxy Analysis Engine

### analyze_proxy_situation()
**Input**: AuctionContext + StrategyDecision
**Output**: ProxyDecision object with full analysis

**Three Scenario Handlers**:

#### Scenario 1: No Current Proxy (Initial Setup)
**Logic**:
```python
new_proxy_max = min(safe_max, budget_available, estimated_value * 0.80)
next_bid = current_bid + increment
```

**Decision**: Always set initial proxy to safe maximum within constraints.

**Why?**: Establishes maximum willingness to pay upfront. Platform handles incremental bidding automatically.

#### Scenario 2: Current Bid Exceeds Safe Max (Loss Zone)
**Logic**:
```python
if safe_max <= current_bid:
    return ProxyDecision(should_increase_proxy=False, proxy_action="accept_loss")
```

**Example**: Value $150, Safe max $105, Current bid $120
**Decision**: Accept loss - cannot profitably continue

**Why?**: Mathematical impossibility. Continuing would guarantee loss.

#### Scenario 3: Safe Max Above Current Bid (Increase Zone)
**Logic**:
```python
potential_new_proxy = min(safe_max, budget_available, estimated_value * 0.80)
min_increase_threshold = increment * 3  # At least 3 increments

if potential_new_proxy > current_proxy + min_increase_threshold:
    return ProxyDecision(should_increase_proxy=True, new_proxy_max=potential_new_proxy)
```

**Example**: Safe max $700, Current proxy $600, Increment $5
**Decision**: Increase to $700 (worth the headroom)

**Why Minimum Threshold?**: Avoids tiny increases that don't provide meaningful bidding advantage.

## Proxy Decision Structure

**Complete ProxyDecision Contains**:
- **Current State**: current_proxy, current_bid, safe_max
- **Decision**: should_increase_proxy, new_proxy_max
- **Next Action**: next_bid_amount (what platform will show)
- **Constraints**: max_budget_for_domain (capped amount)
- **Action Type**: "accept_loss", "increase_proxy", "maintain_proxy"
- **Explanation**: Detailed reasoning with calculations

## Integration with Strategy Decisions

### apply_proxy_logic_to_decision()
**Input**: AuctionContext + StrategyDecision
**Output**: Enhanced decision dict with proxy analysis

**Logic Flow**:
1. **Run Proxy Analysis**: Get ProxyDecision for current situation
2. **Strategy Override**: If proxy says "accept_loss", force strategy to "do_not_bid"
3. **Field Updates**: Add proxy fields to strategy decision
4. **Combined Output**: Return strategy + proxy analysis

**Why Integration?**: Proxy logic can override strategy if mathematically unsound. Safety trumps strategy preference.

## Detailed Scenario Examples

### Example 1: Profitable Increase
```
Domain Value: $1000
Safe Max: $700 (70%)
Current Proxy: $600
Current Bid: $550
Increment: $5
Decision: Increase proxy to $700
Next Bid: $555 ($550 + $5)
Explanation: Safe max allows $100 headroom, worth increasing
```

### Example 2: Accept Loss
```
Domain Value: $150
Safe Max: $105 (70%)
Current Proxy: $100
Current Bid: $120
Decision: Accept loss
Explanation: Safe max $105 < current bid $120, cannot profit
```

### Example 3: Initial Proxy Setup
```
Domain Value: $500
Safe Max: $350
Current Proxy: $0 (none)
Current Bid: $50
Decision: Set proxy to $350
Next Bid: $55 ($50 + $5)
Explanation: Establish maximum willingness at safe level
```

## Mathematical Foundations

### Safe Maximum Formula
**safe_max = estimated_value × 0.70**

**Derivation**:
- Target profit margin: 30% minimum
- Auction dynamics add 20-40% winner's premium
- 70% provides buffer against escalation
- Conservative enough to avoid systematic losses

### Minimum Increase Threshold
**threshold = increment × 3**

**Why 3 Increments?**
- Provides meaningful bidding headroom
- Justifies API call/transaction cost
- Avoids micro-adjustments that confuse strategy

## Platform Mechanic Integration

### GoDaddy Extension Awareness
- Proxy increases timed to avoid triggering 5-minute extensions
- Sniping strategies coordinated with proxy decisions

### Increment Accuracy
- Uses correct increment for next bid calculations
- Prevents bid amount errors that could lose auctions

## Error Handling & Edge Cases

### Budget Constraints
- Proxy never exceeds available budget
- Hard ceiling (80%) always respected
- Prevents impossible bidding scenarios

### Zero/Invalid Values
- Handles cases where safe_max = 0
- Validates all monetary calculations
- Prevents division by zero or negative values

## Performance & Efficiency

### Computation Speed
- **Pure Math**: No API calls or complex operations
- **Instant Results**: Sub-millisecond execution
- **Stateless**: No persistent state or memory usage

### Scalability
- **Concurrent Safe**: Can analyze multiple auctions simultaneously
- **Resource Light**: Minimal CPU and memory footprint
- **No External Dependencies**: Self-contained logic

## Testing Strategy

### Scenario Coverage
- **All Three Scenarios**: Initial setup, loss acceptance, profitable increase
- **Platform Variations**: Different increment schemes
- **Edge Values**: Exactly at safe max, budget limits, increment boundaries
- **Value Tiers**: High, medium, low dollar amounts

### Mathematical Validation
- **Formula Accuracy**: Safe max calculations correct
- **Increment Logic**: Next bid amounts match platform rules
- **Threshold Logic**: Minimum increase rules applied correctly

## Integration Testing
- **Full Pipeline**: Proxy logic works with strategy decisions
- **Override Behavior**: Loss acceptance properly forces do_not_bid
- **Field Propagation**: All proxy fields correctly added to final decision

## Decision Transparency

### Detailed Explanations
Every ProxyDecision includes comprehensive reasoning:
```
"Safe max is $700, current bid is $600; set proxy to $700,
platform will next bid $605, and we will never pay more than $700"
```

**Why Verbose?**: Enables human oversight and debugging. Users can understand exactly why proxy decisions were made.

## Design Philosophy

### Why Separate from Strategy?
- **Mathematical Focus**: Pure calculation vs strategic reasoning
- **Reusable Logic**: Proxy decisions independent of strategy selection
- **Override Capability**: Math can override strategy when profit impossible

### Why Conservative Approach?
- **Loss Prevention**: Never risk systematic losses
- **Margin Protection**: 30% minimum profit buffer
- **Escalation Control**: Prevents emotional bidding wars

This proxy logic layer provides the mathematical precision needed to make sound bidding decisions in dynamic auction environments.





