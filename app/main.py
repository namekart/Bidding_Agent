import os 
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, TYPE_CHECKING, Any

from .core.models import AuctionContext, FinalDecision

if TYPE_CHECKING:
    from .agent.hybrid_strategy_selector import HybridStrategySelector

app = FastAPI(
    title="Bidding Agent API",
    description="API for the LangGraph Bidding Strategy Agent",
    version="1.0"
)

def _truncate(value: Any, limit: int = 3000) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"

# Lazily initialize the selector so API import and docs remain available
# even when model/provider configuration is temporarily invalid.
strategy_selector: Optional[Any] = None
selector_init_error: Optional[str] = None

class StrategyRequest(BaseModel):
    context: AuctionContext

class StrategyResponse(BaseModel):
    status: str
    decision: FinalDecision


def get_strategy_selector() -> Any:
    """Get or initialize the shared strategy selector instance."""
    global strategy_selector, selector_init_error

    if strategy_selector is not None:
        return strategy_selector

    llm_provider = os.getenv("BIDDING_AGENT_LLM_PROVIDER", "openrouter")
    model = os.getenv("BIDDING_AGENT_LLM_MODEL", "openai/gpt-5.1")

    try:
        from .agent.hybrid_strategy_selector import HybridStrategySelector

        strategy_selector = HybridStrategySelector(
            llm_provider=llm_provider,
            model=model,
        )
        selector_init_error = None
        return strategy_selector
    except Exception as e:
        selector_init_error = str(e)
        raise RuntimeError(f"Failed to initialize strategy selector: {e}") from e
    
@app.post("/api/v1/strategy", response_model=StrategyResponse)
async def get_bidding_strategy(request: StrategyRequest):
    """
    Get a bidding strategy decision from the LangGraph agent for a given auction context.
    """
    start_time = time.perf_counter()
    try:
        print(
            "Incoming strategy request: "
            f"domain={request.context.domain} "
            f"platform={request.context.platform} "
            f"current_bid={request.context.current_bid} "
            f"estimated_value={request.context.estimated_value} "
            f"num_bidders={request.context.num_bidders} "
            f"hours_remaining={request.context.hours_remaining}"
        )
        selector = get_strategy_selector()
        # The selector.select_strategy method automatically invokes the LangGraph workflow
        decision = selector.select_strategy(request.context)

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        print(
            "Strategy response sent: "
            f"domain={request.context.domain} "
            f"strategy={decision.strategy} "
            f"recommended_bid_amount={decision.recommended_bid_amount} "
            f"risk_level={decision.risk_level} "
            f"confidence={decision.confidence} "
            f"latency_ms={latency_ms}"
        )
        
        return StrategyResponse(
            status="success",
            decision=decision
        )

    except RuntimeError as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        print(
            "Strategy request failed with runtime error: "
            f"domain={getattr(request.context, 'domain', 'unknown')} "
            f"latency_ms={latency_ms} "
            f"error={_truncate(e)}"
        )
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        # In a production environment, you might want more granular error handling here
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        print(
            "Strategy request failed with unexpected error: "
            f"domain={getattr(request.context, 'domain', 'unknown')} "
            f"latency_ms={latency_ms} "
            f"error={_truncate(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/health")
async def health_check():
    """
    Basic health check endpoint.
    """
    selector_ready = strategy_selector is not None
    return {
        "status": "healthy",
        "selector_ready": selector_ready,
        "selector_init_error": selector_init_error,
    }
