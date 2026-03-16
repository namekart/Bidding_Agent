# graph_nodes.py - LangGraph Node Implementations

## Purpose
This file implements the individual processing nodes that form the LangGraph workflow. Each node represents a step in the multi-agent decision pipeline, transforming the shared state as it progresses through safety checks, AI reasoning, validation, and proxy analysis.

## Core Logic Approach
**Node-Based Orchestration**: Each function is a self-contained processing step that takes the current state, performs its specific operation, and returns the updated state. This modular design allows for clear separation of concerns and easy testing of individual components.

**State Flow Pattern**: All nodes follow the pattern of receiving AuctionState, performing their specific logic, and returning the modified state. This enables the LangGraph to track the complete decision journey.

## Node Architecture

### Shared State Structure
All nodes operate on the AuctionState TypedDict containing:
- **auction_context**: Input auction data
- **blocked**: Safety filter results
- **llm_decision**: AI strategy output
- **llm_valid**: Validation results
- **rule_decision**: Fallback strategy
- **proxy_analysis**: Bidding calculations
- **final_decision**: Complete output

## Individual Node Implementations

### safety_prefilter_node()
**Input**: AuctionState
**Output**: AuctionState with safety check results

**Logic Flow**:
1. **Extract Context**: Get AuctionContext from state
2. **Run Safety Checks**: Call SafetyPreFilters.run_all_checks()
3. **Update State**: Set blocked, block_reason fields
4. **Early Exit**: If blocked, populate final_decision with safety block

**Conditional Routing**: Determines if auction proceeds to AI processing or exits immediately.

**Why First Node?**: Prevents unsafe auctions from consuming expensive AI resources.

### llm_strategy_node()
**Input**: AuctionState (unblocked)
**Output**: AuctionState with LLM decision

**Logic Flow**:
1. **Skip if Blocked**: Return unchanged if safety blocked
2. **Initialize LLM**: Create LLMStrategySelector instance
3. **Extract Context**: Get auction data for LLM
4. **Call AI**: llm_selector.get_strategy_decision(context)
5. **Handle Failure**: Set llm_decision = None on API errors
6. **Update State**: Store raw LLM response

**Error Handling**: Gracefully handles LLM API failures without crashing the pipeline.

### llm_validation_node()
**Input**: AuctionState with LLM decision
**Output**: AuctionState with validation results

**Logic Flow**:
1. **Skip if Blocked**: Return unchanged if safety blocked
2. **Check LLM Response**: Validate llm_decision exists
3. **Parse Decision**: Convert dict back to StrategyDecision object
4. **Run Validation**: Call StrategyValidator.validate_all()
5. **Update State**: Set llm_valid and validation_reason

**Validation Triggers**: Determines if AI decision is safe enough to use or requires fallback.

### rule_fallback_node()
**Input**: AuctionState (when LLM validation fails)
**Output**: AuctionState with rule-based decision

**Logic Flow**:
1. **Skip if Blocked**: Return unchanged if safety blocked
2. **Extract Context**: Get auction data
3. **Generate Rules**: Call RuleBasedStrategySelector.get_strategy_decision()
4. **Update State**: Store rule_decision as dict

**Deterministic Backup**: Provides reliable strategy when AI fails validation.

### proxy_logic_node()
**Input**: AuctionState with strategy decision
**Output**: AuctionState with proxy analysis

**Logic Flow**:
1. **Skip if Blocked**: Return unchanged if safety blocked
2. **Select Strategy**: Use LLM decision if valid, otherwise rule decision
3. **Extract Context**: Get auction data
4. **Run Proxy Logic**: Call ProxyLogicHandler.apply_proxy_logic_to_decision()
5. **Update State**: Store proxy_analysis and decision_source

**Integration Point**: Combines strategy selection with mathematical bidding logic.

### finalize_node()
**Input**: AuctionState with all processing complete
**Output**: AuctionState with final_decision populated

**Logic Flow**:
1. **Check for Block**: Use safety block if present
2. **Assemble Decision**: Combine strategy + proxy analysis
3. **Error Handling**: Provide safe fallback if processing failed
4. **Update State**: Set final_decision and decision_source

**Output Formatting**: Creates the complete FinalDecision object for user consumption.

## Node Design Patterns

### Error Resilience
Each node includes defensive programming:
- **Null Checks**: Validate required state fields exist
- **Exception Handling**: Catch and log errors without crashing
- **Graceful Degradation**: Provide safe defaults when components fail

### State Immutability
**Functional Approach**: Nodes return new state rather than modifying in-place. Enables debugging and replay capabilities.

### Conditional Processing
**Early Returns**: Skip processing if auction was safety-blocked. Avoids unnecessary computation on invalid auctions.

## Integration with LangGraph

### Node Registration
Each function is registered as a node in the StateGraph:
```python
workflow.add_node("safety_prefilter", safety_prefilter_node)
workflow.add_node("llm_strategy", llm_strategy_node)
# ... etc
```

### State Persistence
The shared AuctionState maintains the complete audit trail:
- **Input Capture**: Original auction context preserved
- **Processing History**: Each step's results stored
- **Decision Traceability**: Full path from input to final decision

## Performance Optimization

### Lazy Evaluation
**Conditional Execution**: Expensive operations (LLM calls) only run when needed. Safety blocks prevent unnecessary processing.

### Resource Management
**Stateless Nodes**: No persistent state or resource leaks. Each call is independent.

### Error Isolation
**Node Containment**: Failures in one node don't crash the entire pipeline. Other nodes can still process with default values.

## Testing Strategy

### Unit Testing
Each node tested independently:
- **Input Variations**: Different auction contexts
- **Error Conditions**: API failures, invalid data
- **State Transitions**: Verify correct state field updates

### Integration Testing
Full pipeline testing:
- **End-to-End**: Input to final decision
- **Branch Coverage**: All conditional paths (blocked/unblocked, valid/invalid)
- **Error Propagation**: Verify error handling throughout pipeline

## Node Communication

### State Field Dependencies
- **safety_prefilter**: Reads auction_context, writes blocked fields
- **llm_strategy**: Reads blocked, writes llm_decision
- **llm_validation**: Reads llm_decision, writes validation fields
- **rule_fallback**: Reads validation results, writes rule_decision
- **proxy_logic**: Reads strategy decisions, writes proxy_analysis
- **finalize**: Reads all processing results, writes final_decision

### Data Flow Guarantees
- **Forward Only**: Each node only depends on previous nodes' outputs
- **No Cycles**: Linear flow prevents circular dependencies
- **Complete Coverage**: Every required field populated by some node

## Debugging Support

### State Inspection
The state object serves as a complete audit log:
- **Step Tracking**: See exactly what each node did
- **Error Context**: Understand why decisions were made
- **Performance Data**: Track processing time per node

### Logging Integration
Each node can emit structured logs:
- **Entry/Exit**: Node execution tracking
- **Errors**: Detailed error information
- **Decisions**: Key decision points with reasoning

## Design Philosophy

### Why Separate Nodes?
- **Modularity**: Each concern isolated for testing and maintenance
- **Composability**: Nodes can be rearranged or replaced independently
- **Transparency**: Clear flow of data transformations

### Why Functional Style?
- **Predictability**: Same inputs always produce same outputs
- **Testability**: Easy to unit test pure functions
- **Debugging**: State snapshots enable replay and inspection

This node-based architecture provides the orchestration framework that coordinates the entire multi-agent decision pipeline, ensuring reliable and traceable auction strategy generation.







