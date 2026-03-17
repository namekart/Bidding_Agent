import logging
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

logger = logging.getLogger(__name__)


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
        logger.info(
            "Incoming strategy request: domain=%s platform=%s current_bid=%s estimated_value=%s num_bidders=%s hours_remaining=%s",
            request.context.domain,
            request.context.platform,
            request.context.current_bid,
            request.context.estimated_value,
            request.context.num_bidders,
            request.context.hours_remaining,
        )
        selector = get_strategy_selector()
        # The selector.select_strategy method automatically invokes the LangGraph workflow
        decision = selector.select_strategy(request.context)

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "Strategy response sent: domain=%s strategy=%s recommended_bid_amount=%s risk_level=%s confidence=%s latency_ms=%s",
            request.context.domain,
            decision.strategy,
            decision.recommended_bid_amount,
            decision.risk_level,
            decision.confidence,
            latency_ms,
        )
        
        return StrategyResponse(
            status="success",
            decision=decision
        )

    except RuntimeError as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.warning(
            "Strategy request failed with runtime error: domain=%s latency_ms=%s error=%s",
            getattr(request.context, "domain", "unknown"),
            latency_ms,
            _truncate(e),
        )
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        # In a production environment, you might want more granular error handling here
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.exception(
            "Strategy request failed with unexpected error: domain=%s latency_ms=%s error=%s",
            getattr(request.context, "domain", "unknown"),
            latency_ms,
            _truncate(e),
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
