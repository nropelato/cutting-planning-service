import time
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_api_key
from app.core.config import settings
from app.models.schemas import InferenceRequest, OptimizationResponse, MarkerResult
from app.services.inference import optimize_predefined_markers, InferenceConfig

router = APIRouter()

@router.post("/infer-layers", response_model=OptimizationResponse)
async def infer_marker_layers(request: InferenceRequest, api_key: str = Depends(verify_api_key)):
    try:
        start_time = time.time()
        config = InferenceConfig()
        config.MAX_PLY_LIMIT = settings.MAX_PLY_LIMIT
        config.SOLVER_TIME_LIMIT_SECONDS = settings.SOLVER_TIME_LIMIT_SECONDS

        solver_output = optimize_predefined_markers(request.demand_data, request.input_markers, config)
        solve_time_ms = round((time.time() - start_time) * 1000, 2)

        if solver_output["status"] not in ["OPTIMAL", "FEASIBLE"]:
            raise HTTPException(status_code=422, detail="Predefined markers cannot fulfill demand layouts safely.")

        return OptimizationResponse(
            status=solver_output["status"],
            solve_time_ms=solve_time_ms,
            total_financial_waste=solver_output["financial_waste"],
            markers=[MarkerResult(marker_id=f"CAD-MKR-{i+1:03d}", **mkr) for i, mkr in enumerate(solver_output["markers"])]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
