# safety_filters.py - Hardcoded Safety Pre-Filters

## Purpose
This file implements Layer 1 of the decision pipeline: non-negotiable safety checks that prevent catastrophic bidding decisions. These filters run before any AI processing and can block auctions entirely if safety conditions are violated.

## Core Logic Approach
**"Safety First" Philosophy**: LLM cannot override these hardcoded rules. They protect against:
- Financial loss from overpayment
- Portfolio concentration risk
- Insufficient budget scenarios
- Invalid valuation data

## Key Classes

### SafetyPreFilters (Static Methods Class)
**Purpose**: Collection of independent safety checks that can be run individually or together.

**Approach**: Static methods for stateless, deterministic validation. Each check returns either success or a detailed block reason.

## Safety Check Methods

### check_overpayment_protection()
**Input**: AuctionContext object
**Output**: Dict with 'blocked' boolean and reason, or None if safe

**Logic**:
```python
threshold = estimated_value * 1.30  # 130% overpayment zone
if current_bid > threshold:
    return BLOCK_DECISION
```

**Why 130% threshold?**: Represents "winner's curse" zone where winning guarantees a loss. Based on auction theory that emotional escalation leads to overpayment.

**Reasoning**: Prevents bidding wars where final price exceeds domain's intrinsic value.

### check_portfolio_concentration()
**Input**: AuctionContext object
**Output**: Block decision or None

**Logic**:
```python
max_domain_budget = budget_available * 0.50  # 50% limit
if estimated_value > max_domain_budget:
    return BLOCK_DECISION
```

**Why 50% limit?**: Prevents single domain from consuming entire remaining budget. Ensures portfolio diversification and risk management.

**Approach**: Conservative risk management - no single asset dominates capital allocation.

### check_minimum_budget()
**Input**: AuctionContext object
**Output**: Block decision or None

**Logic**:
```python
if budget_available < 100.0:
    return BLOCK_DECISION
```

**Why $100 minimum?**: Prevents participation with insufficient funds for meaningful bidding. Low budgets lead to poor decisions and compressed margins.

**Reasoning**: Quality over quantity - better to skip auctions than participate poorly.

### check_valuation_validity()
**Input**: AuctionContext object
**Output**: Block decision or None

**Logic**:
```python
if estimated_value <= 0:
    return BLOCK_DECISION
```

**Why zero check?**: Cannot calculate profit margins without knowing domain value. Invalid data leads to random bidding.

**Approach**: Fail-fast on bad data rather than making assumptions.

### run_all_checks() - Main Entry Point
**Input**: AuctionContext object
**Output**: Complete safety decision dict

**Execution Order**:
1. Valuation validity (most critical - cannot proceed without value)
2. Minimum budget (prerequisite for participation)
3. Overpayment protection (immediate financial risk)
4. Portfolio concentration (strategic risk)

**Why ordered execution?**: Prioritizes most critical checks first. If valuation is invalid, no point checking other rules.

## Block Decision Structure
When a check fails, returns:
```python
{
    'blocked': True,
    'reason': "Detailed explanation of why blocked",
    'strategy': 'do_not_bid',
    'recommended_bid_amount': 0.0,
    'risk_level': 'high',
    'confidence': 0.95  # High confidence in safety blocks
}
```

## Design Philosophy

**Why Hardcoded Rules?**
- **Deterministic**: No AI hallucinations can override safety
- **Fast**: No API calls or complex computation
- **Transparent**: Clear, auditable logic
- **Conservative**: Bias toward safety over opportunity

**Why Static Methods?**
- **Stateless**: No side effects or persistent state
- **Testable**: Easy to unit test individual checks
- **Composable**: Can be combined or run independently

## Integration with LangGraph
- Runs first in the decision pipeline
- If blocked, immediately routes to finalization
- LLM and other expensive processing skipped entirely
- Provides immediate safety guarantees

## Failure Scenarios Handled
1. **Overpayment**: Current bid > 130% of value
2. **Concentration**: Domain > 50% of remaining budget
3. **Insolvency**: Budget < $100
4. **Bad Data**: Invalid or missing valuation

## Performance Benefits
- **Early Exit**: Blocks unsafe auctions before expensive LLM calls
- **Cost Savings**: Reduces API usage for obviously bad auctions
- **Speed**: Instant decisions for safety violations

## Testing Strategy
- **Unit Tests**: Each check tested independently
- **Edge Cases**: Boundary values (exactly 130%, exactly $100)
- **Integration**: Full pipeline testing with safety blocks

This layer ensures the system never makes financially dangerous decisions, regardless of what the AI might suggest.





