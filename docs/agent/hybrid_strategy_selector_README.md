# hybrid_strategy_selector.py - Main Strategy Selector Interface

## Purpose
This file provides the primary user interface for the Domain Auction Strategy AI system. It encapsulates the entire multi-agent pipeline into a single, easy-to-use class that exposes the `select_strategy()` method, handling all the complexity of LangGraph orchestration, error handling, and performance monitoring.

## Core Logic Approach
**Facade Pattern**: Provides a simple interface that hides the complexity of the 4-layer decision pipeline. Users interact with a single method while the system orchestrates safety checks, AI reasoning, validation, and proxy logic internally.

**Production-Ready Interface**: Includes comprehensive error handling, performance tracking, and graceful degradation when components fail.

## Key Components

### HybridStrategySelector Class
**Purpose**: Main entry point for strategy selection.

**Configuration Parameters**:
- **llm_provider**: "anthropic" or "openai" for AI backend
- **model**: Specific model name (e.g., "claude-3-5-sonnet-20241022")
- **enable_fallback**: Whether to use rule-based backup (always True in production)

## Initialization Logic

### __init__() Constructor
**Input**: Configuration parameters
**Side Effects**: Sets up LLM access, compiles LangGraph

**Logic Flow**:
1. **Store Configuration**: Save provider, model, fallback settings
2. **Configure LLM**: Call _configure_llm_access()
3. **Compile Graph**: Create strategy_graph with compiled workflow
4. **Initialize Metrics**: Set up performance tracking counters

**Why Separate Config Method?**: Allows for different LLM setup logic (API keys, authentication, etc.)

### _configure_llm_access()
**Input**: None (reads from environment)
**Output**: None (sets up API access)

**Logic**:
- Checks for ANTHROPIC_API_KEY or OPENAI_API_KEY
- Prints warnings if keys missing (doesn't fail - allows rule-based fallback)
- Could be extended for OAuth, custom endpoints, etc.

**Approach**: Environment-based configuration for deployment flexibility.

## Main Interface Method

### select_strategy()
**Input**: AuctionContext object
**Output**: FinalDecision object

**Complete Logic Flow**:
1. **Input Validation**: Ensure AuctionContext type
2. **Prepare State**: Create initial AuctionState dict
3. **Execute Graph**: Call self.strategy_graph.invoke(initial_state)
4. **Update Metrics**: Track decision counts and sources
5. **Extract Result**: Parse final_decision from result state
6. **Error Handling**: Return safe fallback on any failure

**Why Comprehensive Error Handling?**: Production systems must never crash. Always provide a valid decision.

## Performance Monitoring

### Built-in Metrics Tracking
**Counters**:
- **total_decisions**: Total auctions processed
- **llm_success_count**: Decisions from validated AI
- **fallback_count**: Decisions from rule-based system
- **safety_block_count**: Auctions blocked by safety rules

**Update Logic**:
```python
decision_source = result_state.get("decision_source")
if decision_source == "llm":
    self.llm_success_count += 1
elif decision_source == "rules_fallback":
    self.fallback_count += 1
# etc
```

### get_performance_stats()
**Input**: None
**Output**: Dict with performance metrics and rates

**Calculated Fields**:
- **llm_success_rate**: AI success percentage
- **fallback_rate**: Rule-based usage percentage
- **safety_block_rate**: Safety intervention rate

**Why Track Performance?**: Enables monitoring system health and AI reliability over time.

### reset_performance_stats()
**Input**: None
**Output**: None (resets all counters)

**Use Case**: Periodic resets for rolling performance windows.

## Error Handling Strategy

### Comprehensive Failure Recovery
**Failure Points**:
- **Input Validation**: Wrong parameter types
- **Graph Execution**: LangGraph internal errors
- **State Parsing**: Missing or malformed result fields
- **Object Creation**: Pydantic validation failures

**Recovery Strategy**:
- **Safe Defaults**: Return do_not_bid with system_error source
- **Logging**: Print errors for monitoring (don't expose to users)
- **Graceful Degradation**: System continues working even with component failures

### Emergency Fallback Decision
When everything fails, returns:
```python
FinalDecision(
    strategy="do_not_bid",
    recommended_bid_amount=0.0,
    confidence=0.0,
    reasoning="System error: [details]",
    decision_source="system_error"
)
```

**Why Conservative?**: Better to skip an auction than make a bad decision.

## Integration with LangGraph

### State Preparation
Converts AuctionContext to AuctionState dict:
```python
initial_state = {
    "auction_context": auction_context.dict(),
    "blocked": False,
    # ... other fields initialized to None
}
```

**Why Dict Format?**: LangGraph expects dictionary-based state objects.

### Result Extraction
Parses final state back to typed objects:
```python
final_decision_dict = result_state.get("final_decision")
final_decision = FinalDecision(**final_decision_dict)
```

**Validation**: Ensures the pipeline produced a valid, complete decision.

## Usage Patterns

### Basic Usage
```python
selector = HybridStrategySelector()
decision = selector.select_strategy(auction_context)
print(f"Strategy: {decision.strategy}")
```

### With Custom Configuration
```python
selector = HybridStrategySelector(
    llm_provider="openai",
    model="gpt-4",
    enable_fallback=True
)
```

### Performance Monitoring
```python
stats = selector.get_performance_stats()
print(f"AI Success Rate: {stats['llm_success_rate']:.1%}")
```

## Deployment Considerations

### Environment Setup
**Required Environment Variables**:
- ANTHROPIC_API_KEY or OPENAI_API_KEY (for AI features)
- Optional: Custom API endpoints, timeouts, etc.

**Why Environment-Based?**: Keeps credentials out of code, enables different environments (dev/staging/prod).

### Resource Management
- **Stateless**: No persistent connections or memory leaks
- **Lightweight**: Minimal resource footprint per request
- **Concurrent Safe**: Can handle multiple simultaneous requests

## Testing Strategy

### Unit Testing
- **Initialization**: Test with/without API keys
- **Input Validation**: Invalid AuctionContext objects
- **Error Handling**: Force various failure modes

### Integration Testing
- **End-to-End**: Full pipeline with real auction data
- **Performance Tracking**: Verify metrics update correctly
- **Error Recovery**: Test fallback behavior

### Load Testing
- **Concurrent Requests**: Multiple simultaneous strategy selections
- **Memory Usage**: Monitor for leaks over time
- **API Limits**: Handle rate limiting gracefully

## Design Philosophy

### Why Single Method Interface?
- **Simplicity**: Users don't need to understand pipeline complexity
- **Consistency**: Same interface regardless of internal changes
- **Abstraction**: Hides implementation details from consumers

### Why Comprehensive Monitoring?
- **Production Readiness**: Real systems need observability
- **Performance Tuning**: Identify bottlenecks and failure patterns
- **Business Metrics**: Track AI vs rule usage for cost optimization

### Why Graceful Degradation?
- **Reliability**: System continues working even with partial failures
- **User Experience**: Never returns errors to end users
- **Operational Safety**: Conservative defaults prevent bad decisions

## Extension Points

### Custom LLM Providers
Override `_configure_llm_access()` for custom authentication or providers.

### Additional Metrics
Extend performance tracking for custom business metrics.

### Configuration Options
Add parameters for timeouts, retry logic, custom safety rules, etc.

## Error Messages & Logging

### User-Facing Errors
- **Never Exposed**: Internal errors don't reach users
- **Safe Fallbacks**: Always return valid decisions
- **Logged Internally**: Errors captured for monitoring

### Debug Information
- **Decision Source**: Tracks which component made the decision
- **Processing Path**: Full audit trail in state object
- **Performance Data**: Execution times and success rates

This interface class provides the clean, reliable API that makes the complex multi-agent system accessible and production-ready for real-world domain auction strategy decisions.





