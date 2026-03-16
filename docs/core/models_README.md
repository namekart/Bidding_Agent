# models.py - Data Models & Type Definitions

## Purpose
This file defines the core data models and type definitions used throughout the Domain Auction Strategy AI system. It establishes the structure for all data that flows through the multi-agent system, ensuring type safety and validation.

## Key Components

### AuctionContext (Pydantic Model)
**Purpose**: Represents the complete input context for making auction strategy decisions.

**Input**: Constructor parameters with validation
```python
AuctionContext(
    domain="example.com",
    platform="godaddy",
    estimated_value=1000.0,
    current_bid=500.0,
    num_bidders=3,
    hours_remaining=2.5,
    your_current_proxy=450.0,
    budget_available=5000.0,
    bidder_analysis=BidderAnalysis(...)
)
```

**Output**: Validated AuctionContext object with type checking
- Validates positive values for monetary amounts
- Ensures hours_remaining ≥ 0
- Validates platform is one of: "godaddy", "namejet", "dynadot"

**Logic**: Uses Pydantic for runtime validation and automatic type conversion. Prevents invalid data from entering the decision pipeline.

### BidderAnalysis (TypedDict)
**Purpose**: Captures analysis of bidder behavior patterns.

**Fields**:
- `bot_detected`: Boolean flag for automated bidding detection
- `corporate_buyer`: Indicates institutional vs individual buyer
- `aggression_score`: 1-10 scale of bidding aggressiveness
- `reaction_time_avg`: Average response time in seconds

**Approach**: TypedDict for flexibility while maintaining type hints. Used by LLM for opponent analysis.

### StrategyDecision (Pydantic Model)
**Purpose**: Output from strategy selection (LLM or rules-based).

**Key Fields**:
- `strategy`: One of 6 possible strategies ("proxy_max", "last_minute_snipe", etc.)
- `recommended_bid_amount`: Proxy maximum to set
- `confidence`: 0-1 confidence score
- `risk_level`: "low", "medium", "high"
- `reasoning`: Human-readable explanation (minimum 50 chars)

**Validation Logic**:
- Ensures reasoning length ≥ 50 characters
- Validates strategy is from allowed set
- Checks confidence is within 0-1 range

### ProxyDecision (Pydantic Model)
**Purpose**: Details proxy bidding adjustments and analysis.

**Key Fields**:
- `current_proxy`, `current_bid`, `safe_max`: Current auction state
- `should_increase_proxy`: Boolean decision
- `new_proxy_max`: New proxy amount if increasing
- `proxy_action`: "accept_loss", "increase_proxy", "maintain_proxy"
- `explanation`: Detailed reasoning for proxy decision

**Logic**: Computed fields provide clear proxy adjustment recommendations with full transparency.

### FinalDecision (Pydantic Model)
**Purpose**: Complete decision output combining all analysis layers.

**Contains**:
- All strategy fields from StrategyDecision
- Complete proxy analysis from ProxyDecision
- `decision_source`: "llm", "rules_fallback", "safety_block", "system_error"

**Approach**: Single comprehensive output object that encapsulates the entire decision-making process.

### AuctionState (TypedDict)
**Purpose**: Internal state that flows through the LangGraph workflow.

**Purpose**: Enables stateful processing across graph nodes while maintaining type safety. Tracks processing state through the multi-agent pipeline.

## Design Philosophy

**Why Pydantic Models?**
- Runtime validation prevents invalid data propagation
- Automatic type conversion and serialization
- Clear field descriptions and constraints
- JSON schema generation for API documentation

**Why TypedDict for State?**
- Flexibility for dynamic state updates in LangGraph
- Maintains type hints for development experience
- Allows optional fields for different processing stages

## Dependencies
- `pydantic`: Core validation and model framework
- `typing_extensions`: For TypedDict support

## Usage in System
These models form the "contract" between all components:
1. **Input**: AuctionContext defines required auction data
2. **Processing**: StrategyDecision and ProxyDecision capture intermediate results
3. **Output**: FinalDecision provides complete decision with full traceability

## Validation Rules
- All monetary values must be non-negative
- Platform must be from supported list
- Reasoning fields have minimum length requirements
- Confidence scores constrained to 0-1 range
- Strategy choices limited to predefined safe options

This ensures the entire system operates on validated, well-structured data with clear interfaces between components.





