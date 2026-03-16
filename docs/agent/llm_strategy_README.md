# llm_strategy.py - LLM-Based Strategy Reasoning

## Purpose
This file implements Layer 2 of the decision pipeline: intelligent strategy selection using LLMs. It provides the "brain" of the system by leveraging large language models to analyze auction contexts and recommend optimal bidding strategies.

## Core Logic Approach
**Hybrid Intelligence**: Combines AI reasoning with structured constraints. Uses detailed prompts to guide LLM toward safe, profitable decisions while respecting platform mechanics and bidder psychology.

**Structured Output**: Forces LLM to produce parseable JSON rather than free-form text, ensuring reliable integration with the decision pipeline.

## Key Components

### LLMStrategySelector Class
**Purpose**: Manages LLM interactions and strategy generation.

**Configuration Options**:
- `provider`: "anthropic" or "openai"
- `model`: Specific model name (e.g., "claude-3-5-sonnet-20241022")

**Initialization Logic**:
- Validates API key availability
- Creates appropriate client (Anthropic or OpenAI)
- Stores configuration for reuse

## LLM Integration Methods

### _initialize_client()
**Input**: provider and API key from environment
**Output**: Configured LLM client object

**Logic**:
- Checks for ANTHROPIC_API_KEY or OPENAI_API_KEY
- Initializes appropriate SDK client
- Handles import errors gracefully

**Approach**: Environment-based configuration allows deployment flexibility without code changes.

### _get_system_prompt()
**Input**: None
**Output**: Comprehensive system prompt string

**Contains**:
1. **Role Definition**: "Strategist" with domain auction expertise
2. **Core Principles**: Profit-first, safety ceilings, platform awareness
3. **Strategy Framework**: 6 available strategies with clear definitions
4. **Platform Rules**: GoDaddy extensions, NameJet speed, Dynadot increments
5. **Decision Framework**: Step-by-step reasoning process

**Why Detailed Prompt?**: Guides LLM toward domain-specific reasoning rather than generic advice. Prevents hallucinations about bidding strategies.

### _get_user_prompt()
**Input**: AuctionContext object
**Output**: Formatted user prompt with auction data

**Dynamic Content**:
- **Value Tier Analysis**: High/Medium/Low classification with implications
- **Financial Boundaries**: Safe max (70%), hard ceiling (80%)
- **Platform-Specific Rules**: Tailored to godaddy/namejet/dynadot
- **Bidder Analysis**: Bot detection, corporate flags, aggression scores
- **Structured Output Schema**: JSON format specification

**Logic**: Transforms structured data into narrative format that LLM can understand while preserving all quantitative details.

## Strategy Selection Process

### get_strategy_decision()
**Input**: AuctionContext object
**Output**: StrategyDecision object or None (if LLM fails)

**Execution Flow**:
1. **Generate Prompts**: System + user prompts with auction context
2. **API Call**: Send to Claude/OpenAI with JSON response format
3. **Parse Response**: Extract JSON from LLM output
4. **Validate & Enrich**: Create StrategyDecision with computed fields
5. **Error Handling**: Return None on failure (triggers fallback)

**Why JSON Response Format?**: Ensures structured, parseable output rather than natural language. Prevents ambiguity in strategy selection.

## LLM Prompt Engineering Strategy

### System Prompt Structure
**PHASE 1: Threat Assessment**
- Time-based urgency (10min discovery, 5min war phase)
- Opponent analysis framework

**PHASE 2: Counter-Measures**
- Bot detection: "Piercing Bid" for proxy bots
- Human handling: "Bully Anchor" for aggressive humans
- Crowd management: "Dark Mode" waiting

**PHASE 3: Execution Timing**
- "90-Second Rule" for final bids
- Platform-aware timing adjustments

### Safety Constraints in Prompt
- **Hard Ceilings**: Never exceed 80% of estimated value
- **Profit Focus**: Target 60-70% for 30%+ margins
- **Platform Respect**: Acknowledge GoDaddy extensions, NameJet speed

## Error Handling Strategy

### API Failure Scenarios
- **Network Issues**: Return None, trigger fallback
- **Rate Limits**: Graceful degradation to rules
- **Invalid JSON**: Parse errors trigger fallback
- **Model Errors**: Exception handling prevents crashes

### Validation Integration
- LLM output validated by Layer 3 (validation.py)
- Invalid decisions trigger rule-based fallback
- Maintains system robustness

## Performance Optimization

### Prompt Efficiency
- **Structured Input**: Clear data format reduces token usage
- **Focused Context**: Only relevant auction data included
- **Schema Guidance**: JSON format reduces parsing errors

### Cost Management
- **Early Filtering**: Safety layer prevents unnecessary LLM calls
- **Fallback Ready**: Rule-based system handles LLM failures
- **Caching Potential**: Could cache similar auction decisions

## Integration with Decision Pipeline

### Input Dependencies
- Requires AuctionContext with complete auction state
- Depends on safety filters passing (no blocked auctions reach LLM)

### Output Usage
- StrategyDecision fed to validation layer
- If valid, used for proxy analysis
- If invalid, triggers rule-based fallback

## Testing Strategy

### LLM Response Validation
- **Schema Compliance**: JSON structure matches StrategyDecision
- **Value Ranges**: Confidence 0-1, amounts positive
- **Strategy Validity**: One of 6 allowed strategies
- **Reasoning Quality**: Minimum length and content checks

### Edge Case Testing
- **Extreme Values**: Very high/low bids, time pressure
- **Bot Scenarios**: Fast reaction times, round number patterns
- **Platform Differences**: Extension handling, increment variations

## Design Trade-offs

### Why Claude/GPT vs Custom ML?
- **General Intelligence**: Handles complex bidder psychology
- **Adaptability**: Learns new patterns without retraining
- **Explainability**: Provides reasoning (vs black-box ML)
- **Development Speed**: No training data collection needed

### Why Not Fine-tuned Model?
- **Cost**: Fine-tuning expensive and time-consuming
- **Maintenance**: Requires ongoing training data
- **Flexibility**: General models adapt to new auction dynamics
- **Safety**: Structured prompts provide consistent constraints

This layer provides the intelligent reasoning capability while maintaining safety through structured prompts and validation layers.





