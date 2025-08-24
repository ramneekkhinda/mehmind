"""MeshMind Referee Service - FastAPI Application."""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .schemas import (
    Intent, Decision, HoldRequest, HoldResponse,
    BudgetStart, BudgetConsume, BudgetResponse,
    EffectRequest, EffectResponse
)
from .decider import Decider
from .locks import LockManager
from .holds import HoldManager
from .budget import BudgetManager
from .policy import PolicyManager
from .store import Store
from .otel import setup_otel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    app.state.store = Store()
    await app.state.store.connect()
    
    app.state.lock_manager = LockManager()
    await app.state.lock_manager.connect()
    
    app.state.hold_manager = HoldManager()
    await app.state.hold_manager.connect()
    
    app.state.budget_manager = BudgetManager()
    await app.state.budget_manager.connect()
    
    app.state.policy_manager = PolicyManager()
    await app.state.policy_manager.load_policy()
    
    app.state.decider = Decider(
        lock_manager=app.state.lock_manager,
        hold_manager=app.state.hold_manager,
        budget_manager=app.state.budget_manager,
        policy_manager=app.state.policy_manager,
        store=app.state.store
    )
    
    yield
    
    # Shutdown
    await app.state.store.disconnect()
    await app.state.lock_manager.disconnect()
    await app.state.hold_manager.disconnect()
    await app.state.budget_manager.disconnect()


app = FastAPI(
    title="MeshMind Referee Service",
    description="Runtime safety and cost control for LangGraph agents",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenTelemetry setup
setup_otel(app)


def get_decider() -> Decider:
    """Dependency to get the decider instance."""
    return app.state.decider


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "meshmind-referee"}


@app.post("/v1/intents", response_model=Decision)
async def preflight_intent(
    intent: Intent,
    decider: Decider = Depends(get_decider)
) -> Decision:
    """Preflight an intent and get a decision."""
    try:
        return await decider.decide(intent)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/holds/request", response_model=HoldResponse)
async def request_hold(
    request: HoldRequest,
    decider: Decider = Depends(get_decider)
) -> HoldResponse:
    """Request a hold on a resource."""
    try:
        return await decider.hold_manager.request_hold(
            resource=request.resource,
            ttl_s=request.ttl_s,
            author=request.author,
            correlation=request.correlation
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/holds/confirm")
async def confirm_hold(
    hold_id: str,
    decider: Decider = Depends(get_decider)
) -> Dict[str, Any]:
    """Confirm a hold."""
    try:
        success = await decider.hold_manager.confirm_hold(hold_id)
        return {"ok": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/holds/release")
async def release_hold(
    hold_id: str,
    decider: Decider = Depends(get_decider)
) -> Dict[str, Any]:
    """Release a hold."""
    try:
        success = await decider.hold_manager.release_hold(hold_id)
        return {"ok": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/budgets/start", response_model=BudgetResponse)
async def start_budget(
    budget_req: BudgetStart,
    decider: Decider = Depends(get_decider)
) -> BudgetResponse:
    """Start a budget session."""
    try:
        return await decider.budget_manager.start_budget(
            usd_cap=budget_req.usd_cap,
            rpm=budget_req.rpm,
            tags=budget_req.tags
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/budgets/consume", response_model=BudgetResponse)
async def consume_budget(
    consume_req: BudgetConsume,
    decider: Decider = Depends(get_decider)
) -> BudgetResponse:
    """Consume from a budget."""
    try:
        return await decider.budget_manager.consume_budget(
            budget_id=consume_req.budget_id,
            tokens=consume_req.tokens,
            usd=consume_req.usd
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/budgets/stop")
async def stop_budget(
    budget_id: str,
    decider: Decider = Depends(get_decider)
) -> Dict[str, Any]:
    """Stop a budget session."""
    try:
        success = await decider.budget_manager.stop_budget(budget_id)
        return {"ok": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/metrics")
async def get_metrics(
    decider: Decider = Depends(get_decider)
) -> Dict[str, Any]:
    """Get service metrics."""
    try:
        return await decider.store.get_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
